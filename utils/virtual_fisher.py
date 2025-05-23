import re
import os
import asyncio
import json
from pathlib import Path
from typing import Set

from dotenv import load_dotenv
from playwright.async_api import async_playwright, BrowserContext, Route, Request, Page, Locator

from utils.utils import code_logger, fish_logger, env


load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''
user_email: str = os.getenv('user_email') or ''
user_password: str = os.getenv('user_passwrod') or ''
config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

guild_id = int(config['ids']['guild'])
telecom_path = "data/config/telecom.json"
session_path = "data/text/session.txt"
cookies_path = Path("data/config/cookies.json")

with open(telecom_path) as f:
    data = json.load(f)

with open(session_path, 'r') as f:
    session_id = f.read().strip()

browser = str(data['main']['browser'])
browser_path = str(data['main']['path'])
binary_path = str(data['main']['binary'])
debug_port = int(data['main']['port'])
user_agent = data['headers']['base']['User-Agent']
X_Super_Properties = data['headers']['tree']['X-Super-Properties']

fishing_check = bool(config['main']['fishing?'])
if fishing_check:
    fishing_channel = int(config['ids']['fish channel'])
    fish_url = f"https://discord.com/channels/{guild_id}/{fishing_channel}"
    fishing_headers: dict[str, str] = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': user_agent,
        'X-Super-Properties': X_Super_Properties,
        'Referer': f'https://discord.com/channels/{guild_id}/{fishing_channel}',
    }
    paid = bool(config['main']['fishing paid?'])

playwright = None
browser = None
context = None
page = None


async def load_cookies(context: BrowserContext) -> None:
    if cookies_path.exists():
        cookies = json.loads(cookies_path.read_text())
        await context.add_cookies(cookies)


async def save_cookies(context: BrowserContext) -> None:
    cookies = await context.cookies()
    cookies_path.write_text(json.dumps(cookies, indent=2))


async def start_browser(url: str):
    global playwright, browser, context, page

    if browser is not None:
        return

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    await load_cookies(context)
    page = await context.new_page()

    async def route_handler(route: Route, request: Request) -> None:
        headers = request.headers.copy()
        headers.update(fishing_headers)
        await route.continue_(headers=headers)

    await page.route("**/*", route_handler)
    await page.goto(url, wait_until="networkidle")

    try:
        continue_button = page.locator('div.contents__201d5', has_text="Continue in Browser")
        if await continue_button.is_visible():
            code_logger.info("Clicking 'Continue in Browser' button...")
            await continue_button.click()
    except Exception as e:
        code_logger.warning(f"Could not click 'Continue in Browser': {e}")

    try:
        if "discord.com/login" in page.url:
            await page.fill('input[name="email"]', user_email)
            await page.fill('input[name="password"]', user_password)
            await page.click('button[type="submit"]:has-text("Log In")')
    except Exception as e:
        code_logger.warning(f"Could not sign in: {e}")

    try:
        age_restricted_div = page.locator('div.title__7184c', has_text="Age-Restricted")
        if await age_restricted_div.count() > 0:
            button = page.locator('button.button__:has-text("Continue")')
            await button.wait_for(state="visible", timeout=5000)
            await button.click()
    except Exception as e:
        code_logger.warning(f"Failed to leave age restricted warning: {e}")

    await save_cookies(context)


async def ephemeral_messages():
    fish_delay_data = {"delay": 3.0}
    seen_messages: Set[str] = set()

    while True:
        if page is not None:
            ephemeral_messages = page.locator('[class*="ephemeral__"] [id^="message-content-"]')
            count = await ephemeral_messages.count()

            for i in range(count):
                msg = await ephemeral_messages.nth(i).inner_text()
                if msg not in seen_messages:
                    seen_messages.add(msg)
                    fish_logger.info(f"[EPHEMERAL] {msg}")

                    match = re.search(r"Your cooldown:\s*([\d.]+)s", msg)
                    if match:
                        raw_delay = float(match.group(1))
                        fish_delay_data["delay"] = raw_delay + 1.0

            await asyncio.sleep(10)


async def create_emphemeral_watcher():
    asyncio.create_task(ephemeral_messages())


async def get_newest_fish_button(page: Page) -> Locator:
    try:
        locator = page.locator('button:has(div.label__57f77:text("Fish Again"))').last
        await locator.wait_for(timeout=10000)
        return locator
    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get the last fishing message: {e}")
        raise


async def get_newest_sell_button(page: Page) -> Locator:
    try:
        locator = page.locator('button:has(div.label__57f77:text("Sell"))').last
        await locator.wait_for(timeout=10000)
        return locator
    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get the last fishing message: {e}")
        raise


async def get_newest_return_button(page: Page) -> Locator:
    try:
        locator = page.locator('button:has(div.label__57f77:text("Return"))').last
        await locator.wait_for(timeout=10000)
        return locator
    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get the last fishing message: {e}")
        raise


async def send_fish_command():
    if page is None:
        raise RuntimeError("Browser is not initialized.")

    try:
        fish_button = await get_newest_fish_button(page)
        await fish_button.wait_for(state="visible", timeout=5000)
        await fish_button.click()
    except Exception as e:
        fish_logger.warning(f"Failed to click fish button: {e}")


async def send_sell_command():
    if page is None:
        raise RuntimeError("Browser is not initialized.")

    try:
        fish_logger.info("sell fish command called")
        sell_button = await get_newest_sell_button(page)
        await sell_button.wait_for(state="visible", timeout=5000)
        await sell_button.click()
        fish_logger.info("sell button clicked ")
    except Exception as e:
        fish_logger.warning(f"Failed to click fish button: {e}")


async def send_return_command():
    if page is None:
        raise RuntimeError("Browser is not initialized.")

    try:
        return_button = await get_newest_return_button(page)
        await return_button.wait_for(state="visible", timeout=5000)
        await return_button.click()
    except Exception as e:
        fish_logger.warning(f"Failed to click fish button: {e}")


async def fish():
    try:
        await send_fish_command()
    except Exception as e:
        code_logger.error(f"An error has occurred while trying to fish: {e}")


async def sell():
    try:
        fish_logger.info("send command called")
        await send_sell_command()
    except Exception as e:
        code_logger.error(f"An error has occurred while trying to sell: {e}")

'''
async def _return():
    try:
        await send_return_command()
    except Exception as e:
        code_logger.error(f"An error has occurred while trying to return: {e}")
'''


async def send_verify_code(code: str):
    if page is None:
        raise RuntimeError("Browser is not initialized. Call start_browser() first.")

    try:
        chat_input = page.locator('textarea[aria-label*="Message"]')
        await chat_input.fill(f"/verify {code}")
        await chat_input.press("Enter")
        fish_logger.info(f"Sent verification command: /verify {code}")
    except Exception as e:
        fish_logger.error(f"Failed to send verification command: {e}")
