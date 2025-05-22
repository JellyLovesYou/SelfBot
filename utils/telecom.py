from pathlib import Path
import json
import smtplib
import os
import re
import time
import requests
import random
import asyncio
from email.message import EmailMessage
from typing import Any, Dict, Set

from dotenv import load_dotenv
from playwright.async_api import async_playwright, BrowserContext, Route, Request, Page, Locator
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # type: ignore[reportMissingTypeStubs]
from selenium.webdriver.support.ui import WebDriverWait

from utils.utils import code_logger, fish_logger, tree_logger, env  # , pokemon_logger
#  from utils.data import verification_link

load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''
user_email: str = os.getenv('user_email') or ''
user_password: str = os.getenv('user_passwrod') or ''
config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

solving = bool(config['main']['solving?'])
if solving:
    from twocaptcha import TwoCaptcha  # type: ignore[reportMissingTypeStubs]
    TwoCaptcha_token: str = os.getenv('twocaptcha') or ''
    solver = TwoCaptcha(TwoCaptcha_token)

guild_id = int(config['ids']['guild'])
telecom_path = "data/config/telecom.json"
session_path = "data/text/session.txt"
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

cookies_path = Path("data/config/cookies.json")
playwright = None
browser = None
context = None
page = None


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


tree_check = bool(config['main']['tree?'])
if tree_check:
    tree_channel_id = int(config['ids']['tree channel'])
    tree_message_id = int(config['ids']['tree'])
    tree_id = int(config['ids']['tree id'])
    tree_headers: dict[str, str] = {
        'Authorization': token,
        'Content-Type': 'application/json',
        'User-Agent': user_agent,
        'X-Super-Properties': X_Super_Properties,
        'Referer': f'https://discord.com/channels/{guild_id}/{tree_channel_id}',
    }
    watering_payload: dict[str, object] = {
        "type": 3,
        "nonce": str(int(time.time() * 1000 + random.randint(100, 999))),
        "guild_id": guild_id,
        "channel_id": tree_channel_id,
        "message_id": tree_message_id,
        "application_id": tree_id,
        "session_id": session_id,
        "data": {
            "component_type": 2,
            "custom_id": "grow"
        }
    }
    catching_payload: dict[str, object] = {
        "type": 3,
        "nonce": str(int(time.time() * 1000 + random.randint(100, 999))),
        "guild_id": guild_id,
        "channel_id": tree_channel_id,
        "message_id": tree_message_id,
        "application_id": tree_id,
        "session_id": session_id,
        "data": {
            "component_type": 2,
            "custom_id": "bugcatch"
        }
    }


texting_check = bool(config['main']['texts?'])
if texting_check:
    email = os.getenv('email')
    phone = os.getenv('phone')
    app_password = os.getenv('app_password')
    carrier = os.getenv('carrier')


async def text(body: str) -> None:
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = ''
    msg['From'] = email

    actual_carrier = carrier
    if not actual_carrier:
        try:
            lookup = lookup_carrier_info(str(phone))
            if lookup and lookup.get("sms_gateway"):
                actual_carrier = lookup["sms_gateway"].split("@")[1]
            else:
                code_logger.error("Carrier lookup failed or returned no SMS gateway.", exc_info=True)
                return
        except Exception as e:
            code_logger.error(f"Carrier lookup failed: {e}", exc_info=True)
            return

    msg['To'] = f"{phone}@{actual_carrier}"

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(str(email), str(app_password))
            smtp.send_message(msg)
    except Exception as e:
        code_logger.error(f"An error has occurred trying to send a text. {e}", exc_info=True)


def lookup_carrier_info(phone_number: str) -> Dict[str, Any]:
    options: uc.ChromeOptions = uc.ChromeOptions()
    options.add_argument("--headless")  # type: ignore
    options.add_argument("--no-sandbox")  # type: ignore
    options.add_argument("--disable-dev-shm-usage")  # type: ignore

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get("https://freecarrierlookup.com/")
        wait.until(EC.presence_of_element_located((By.NAME, "phonenum")))

        phone_input = driver.find_element(By.NAME, "phonenum")
        phone_input.send_keys(phone_number)
        phone_input.send_keys(Keys.RETURN)

        wait.until(EC.presence_of_element_located((By.ID, "results")))
        time.sleep(2)

        result_block = driver.find_element(By.ID, "results").text
        result: Dict[str, str | bool | None] = {
            "carrier": None,
            "is_wireless": None,
            "sms_gateway": None,
            "mms_gateway": None
        }

        for line in result_block.splitlines():
            if "Carrier:" in line:
                result["carrier"] = line.split("Carrier:")[1].strip()
            elif "Is Wireless:" in line:
                result["is_wireless"] = line.split("Is Wireless:")[1].strip().lower() == "y"
            elif "SMS Gateway Address:" in line:
                result["sms_gateway"] = line.split("SMS Gateway Address:")[1].strip()
            elif "MMS Gateway Address:" in line:
                result["mms_gateway"] = line.split("MMS Gateway Address:")[1].strip()

        return result

    except Exception as e:
        code_logger.error(f"An error has occurred trying to lookup carrier info {e}", exc_info=True)
        return {
            "carrier": None,
            "is_wireless": None,
            "sms_gateway": None,
            "mms_gateway": None
        }

    finally:
        driver.quit()


def load_cookies_dict():
    with open("data/config/cookies.json", "r") as f:
        cookies_list = json.load(f)
    return {cookie["name"]: cookie["value"] for cookie in cookies_list}


def water():
    if tree_check:
        cookies = load_cookies_dict()
        r = requests.post(
            "https://discord.com/api/v9/interactions",
            headers=tree_headers,
            cookies=cookies,
            json=watering_payload
        )
        if r.ok:
            tree_logger.info("Watering payload sent successfully")
        if not r.ok:
            code_logger.error(f"Error: {r.status_code} - {r.text}", exc_info=True)


def catch():
    if tree_check:
        code_logger.info("Attemping to catch bug")
        cookies = load_cookies_dict()
        r = requests.post(
            "https://discord.com/api/v9/interactions",
            headers=tree_headers,
            cookies=cookies,
            json=catching_payload
        )
        if r.ok:
            tree_logger.info("Catching payload sent successfully")
        if not r.ok:
            code_logger.error(f"Error: {r.status_code} - {r.text}", exc_info=True)


async def load_cookies(context: BrowserContext) -> None:
    if cookies_path.exists():
        cookies = json.loads(cookies_path.read_text())
        await context.add_cookies(cookies)


async def save_cookies(context: BrowserContext) -> None:
    cookies = await context.cookies()
    cookies_path.write_text(json.dumps(cookies, indent=2))


async def start_browser():
    if fishing_check:
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
        await page.goto(fish_url, wait_until="networkidle")

        try:
            continue_button = page.locator('div.contents__201d5', has_text="Continue in Browser")
            if await continue_button.is_visible():
                fish_logger.info("Clicking 'Continue in Browser' button...")
                await continue_button.click()
        except Exception as e:
            fish_logger.warning(f"Could not click 'Continue in Browser': {e}")

        try:
            if "discord.com/login" in page.url:
                await page.fill('input[name="email"]', user_email)
                await page.fill('input[name="password"]', user_password)
                await page.click('button[type="submit"]:has-text("Log In")')
        except Exception as e:
            fish_logger.warning(f"Could not sign in: {e}")

        try:
            age_restricted_div = page.locator('div.title__7184c', has_text="Age-Restricted")
            if await age_restricted_div.count() > 0:
                button = page.locator('button.button__201d5:has-text("Continue")')
                await button.wait_for(state="visible", timeout=5000)
                await button.click()
        except Exception as e:
            fish_logger.warning(f"Failed to leave age restricted warning: {e}")

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

        asyncio.create_task(ephemeral_messages())


async def get_newest_message_button(page: Page) -> Locator:
    try:
        locator = page.locator('button:has(div.label__57f77:text("Fish Again"))').last
        await locator.wait_for(timeout=10000)
        return locator
    except Exception as e:
        code_logger.error(f"An exception occurred while trying to get the last fishing message: {e}")
        raise


async def send_fish_command():
    if page is None:
        raise RuntimeError("Browser is not initialized. Call start_browser_once() first.")

    try:
        fish_button = await get_newest_message_button(page)
        await fish_button.wait_for(state="visible", timeout=5000)
        await fish_button.click()
    except Exception as e:
        fish_logger.warning(f"Failed to click fish button: {e}")


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


async def fish():
    try:
        await send_fish_command()
    except Exception as e:
        code_logger.error(f"An error has occurred while trying to fish: {e}")
