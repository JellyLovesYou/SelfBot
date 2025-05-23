from pathlib import Path
import json
import os
import asyncio
from dotenv import load_dotenv

from playwright.async_api import async_playwright, BrowserContext, Route, Request, Page, Locator

from utils.utils import code_logger, tree_logger, env


load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''
user_email: str = os.getenv('user_email') or ''
user_password: str = os.getenv('user_passwrod') or ''
config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

user_id = str(config['main']['user id'])
nickname = str(config['main']['nickname'])
guild_id = int(config['ids']['guild'])
telecom_path = "data/config/telecom.json"
session_path = "data/text/session.txt"
cookies_path = Path("data/config/cookies.json")

with open(telecom_path) as f:
    data = json.load(f)

browser = str(data['main']['browser'])
browser_path = str(data['main']['path'])
binary_path = str(data['main']['binary'])
debug_port = int(data['main']['port'])
user_agent = data['headers']['base']['User-Agent']
X_Super_Properties = data['headers']['tree']['X-Super-Properties']

with open(session_path, 'r') as f:
    session_id = f.read().strip()

tree_check = bool(config['main']['tree?'])
if tree_check:
    tree_channel_id = int(config['ids']['tree channel'])
    tree_message_id = int(config['ids']['tree'])
    tree_id = int(config['ids']['tree id'])
    url = str(f"https://discord.com/channels/{guild_id}/{tree_channel_id}")
    tree_headers: dict[str, str] = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': user_agent,
        'X-Super-Properties': X_Super_Properties,
        'Referer': url,
    }


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
        headers.update(tree_headers)
        await route.continue_(headers=headers)

    await page.route("**/*", route_handler)
    await page.goto(url, wait_until="networkidle")

    try:
        continue_button = page.locator('div.contents__201d5', has_text="Continue in Browser")
        if await continue_button.is_visible():
            tree_logger.info("Clicking 'Continue in Browser' button...")
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
            button = page.locator('button.button__201d5:has-text("Continue")')
            await button.wait_for(state="visible", timeout=5000)
            await button.click()
    except Exception as e:
        code_logger.warning(f"Failed to leave age restricted warning: {e}")

    await save_cookies(context)


def get_water_button(page: Page) -> Locator:
    return page.locator('button:has(img[alt="💧"])')


async def water():
    if page is None:
        raise RuntimeError("Browser is not initialized.")

    try:
        water_button = get_water_button(page)
        await water_button.click()
        tree_logger.info("Watered the tree")
    except Exception as e:
        code_logger.warning(f"Failed to click water button: {e}")


def get_catch_button(page: Page) -> Locator:
    return page.locator('button:has(img[alt="bugnet"])')


async def catch():
    if page is None:
        raise RuntimeError("Browser is not initialized.")

    try:
        catch_button = get_catch_button(page)
        await catch_button.click()
        tree_logger.info("Caught successfully")
    except Exception as e:
        code_logger.warning(f"Failed to click catch button: {e}")


async def tree_watcher():
    tree_logger.info("Tree watcher started")
    while True:
        if page is not None:
            try:
                catch_button = get_catch_button(page)

                try:
                    if await catch_button.is_visible(timeout=200):
                        await catch()
                except Exception:
                    pass

                desc_element = await page.query_selector('div.embedDescription__623de.embedMargin__623de')
                if desc_element:
                    desc_text = await desc_element.inner_text()

                    if nickname in desc_text or user_id in desc_text:
                        await asyncio.sleep(1)
                        continue

                    if "Ready to be watered!" in desc_text:
                        tree_logger.info("Watering the tree")
                        await water()
                        await asyncio.sleep(1)

            except Exception as e:
                code_logger.error(f"Error in tree_watcher: {e}", exc_info=True)

        await asyncio.sleep(0.5)


async def create_tree_watcher():
    await start_browser(url)
    asyncio.create_task(tree_watcher())
