from pathlib import Path
import json
import psutil
import smtplib
import os
import time
import requests
import random
import socket
import subprocess
from email.message import EmailMessage
from typing import Any, Dict, Optional

from twocaptcha import TwoCaptcha  # type: ignore[reportMissingTypeStubs]
from dotenv import load_dotenv
from selenium import webdriver
from playwright.async_api import async_playwright, BrowserContext, Route, Request
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # type: ignore[reportMissingTypeStubs]
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver

from utils.utils import code_logger, pokemon_logger, fish_logger, env
from utils.data import verification_link

load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''
user_email: str = os.getenv('user_email') or ''
user_password: str = os.getenv('user_passwrod') or ''
TwoCaptcha_token: str = os.getenv('twocaptcha') or ''
solver = TwoCaptcha(TwoCaptcha_token)
config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

fishing = bool(config['main']['fishing?'])
guild_id = int(config['ids']['guild'])
tree_channel_id = int(config['ids']['tree channel'])
tree_message_id = int(config['ids']['tree'])
tree_id = int(config['ids']['tree id'])
fish_message_id = int(config['ids']['fish message'])
fishing_channel = int(config['ids']['fish channel'])
fish_custom = str(config['ids']['fish custom'])
fish_id = int(config['ids']['fish id'])
telecom_path = str(config['paths']['telecom'])
session_path = str(config['paths']['session'])

with open(telecom_path) as f:
    data = json.load(f)

browser = str(data['main']['browser'])
browser_path = str(data['main']['path'])
binary_path = str(data['main']['binary'])
debug_port = int(data['main']['port'])
user_agent = data['headers']['base']['User-Agent']
X_Super_Properties = data['headers']['tree']['X-Super-Properties']

fish_url = f"https://discord.com/channels/{guild_id}/{fishing_channel}"
cookies_path = Path("data/config/cookies.json")
playwright = None
browser = None
context = None
page = None


def is_browser_debug_running(port: int = debug_port) -> bool:
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            if proc.info['name'] and browser in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']).lower()
                if f'--remote-debugging-port={port}' in cmdline:
                    return True
        return False

    except Exception as e:
        code_logger.error(f"An error has occurred while checking if the browser debug is running, {e}")
        return False


def wait_for_debug_port(host: str = "127.0.0.1", port: int = debug_port, timeout: float = 30.0):

    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.1)
    raise TimeoutError(f"Port {port} not ready after {timeout} seconds.")


def launch_browser_with_debug(url: Optional[str] = None):
    try:
        cmd = [
            binary_path,
            f'--remote-debugging-port={debug_port}',
            f'--user-data-dir={browser_path}'
        ]
        if url:
            cmd.append(url)

        subprocess.Popen(cmd)

        wait_for_debug_port(port=debug_port, timeout=15)

    except TimeoutError as e:
        code_logger.error(f"Failed to open debug port in time: {e}")
        raise
    except Exception as e:
        code_logger.error(f"An error occurred while launching browser with debug: {e}")
        raise


def p2verification() -> Optional[Dict[str, Any]]:
    pokemon_logger.info("p2 verification function called, attempting to bypass verification.")
    launch_browser_with_debug(verification_link)
    wait_for_debug_port(port=debug_port)

    options = webdriver.ChromeOptions()  # type: ignore
    options.binary_location = binary_path
    options.debugger_address = f"127.0.0.1:{debug_port}"

    driver: Optional[ChromeDriver] = None

    try:
        driver = webdriver.Chrome(options=options)
        code_logger.info(f"Attempting to open {verification_link}")
        driver.execute_script(f"window.open('{verification_link}', '_blank');")  # type: ignore
        driver.switch_to.window(driver.window_handles[-1])
        driver.refresh()

        sitekey_recaptcha = "6LfgtMoaAAAAAPB_6kwTMPj9HG_XxRLL7n92jYkD"

        try:
            code_logger.info("trying to get captcha results...")
            result_recaptcha: Dict[str, Any] = solver.recaptcha(sitekey=sitekey_recaptcha, url=verification_link)  # type: ignore
            code_logger.info(f"result from twocaptcha: {result_recaptcha}")
            if not result_recaptcha:
                code_logger.error("2Captcha returned None for recaptcha")
                return None

            driver.execute_script("""document.getElementById("g-recaptcha-response").style.display = "block"; document.getElementById("g-recaptcha-response").value = arguments[0];""", result_recaptcha)  # type: ignore

        except Exception as e:
            code_logger.error(f"Solver error: {e}", exc_info=True)
            return None

    except WebDriverException as e:
        code_logger.error(f"Chrome failed: {e}", exc_info=True)
    except Exception as e:
        code_logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass


def wait_recaptcha_ready(driver: ChromeDriver, timeout: float):
    code_logger.info("Waiting for recaptcha")
    iframe = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe [title='reCAPTCHA']"))
    )
    driver.switch_to.frame(iframe)

    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, "recaptcha-anchor"))
    )

    code_logger.info("Waited for recaptcha, solving.")
    driver.switch_to.default_content()
    return True


texting_check = config['main']['texts?']
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


with open(session_path, 'r') as f:
    session_id = f.read().strip()


tree_headers: dict[str, str] = {
    'Authorization': token,
    'Content-Type': 'application/json',
    'User-Agent': user_agent,
    'X-Super-Properties': X_Super_Properties,
    'Referer': f'https://discord.com/channels/{guild_id}/{tree_channel_id}',
}


tree_payload: dict[str, object] = {
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


def load_cookies_dict():
    with open("data/config/cookies.json", "r") as f:
        cookies_list = json.load(f)
    return {cookie["name"]: cookie["value"] for cookie in cookies_list}


def water():
    cookies = load_cookies_dict()
    r = requests.post(
        "https://discord.com/api/v9/interactions",
        headers=tree_headers,
        cookies=cookies,
        json=tree_payload
    )
    if not r.ok:
        code_logger.error(f"Error: {r.status_code} - {r.text}", exc_info=True)


fishing_headers: dict[str, str] = {
    'Authorization': token,
    'Content-Type': 'application/json',
    'User-Agent': user_agent,
    'X-Super-Properties': X_Super_Properties,
    'Referer': f'https://discord.com/channels/{guild_id}/{fishing_channel}',
}


async def load_cookies(context: BrowserContext) -> None:
    if cookies_path.exists():
        cookies = json.loads(cookies_path.read_text())
        await context.add_cookies(cookies)


async def save_cookies(context: BrowserContext) -> None:
    cookies = await context.cookies()
    cookies_path.write_text(json.dumps(cookies, indent=2))


async def start_browser():
    if fishing:
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


async def send_fish_command():
    if page is None:
        raise RuntimeError("Browser is not initialized. Call start_browser_once() first.")

    await page.evaluate("""
    () => {
        const buttons = Array.from(document.querySelectorAll('button'));
        for (const btn of buttons) {
            const labelDiv = btn.querySelector('div.label__57f77');
            if (labelDiv && labelDiv.textContent.trim() === 'Fish Again') {
                btn.click();
                break;
            }
        }
    }
    """)


async def fish():
    try:
        await send_fish_command()
    except Exception as e:
        code_logger.error(f"An error has occurred while trying to fish: {e}")
