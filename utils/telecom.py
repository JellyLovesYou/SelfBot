from pathlib import Path
import json
import smtplib
import os
import time
import requests
import random
from email.message import EmailMessage
from typing import Any, Dict, Optional, cast

from twocaptcha import TwoCaptcha  # type: ignore[reportMissingTypeStubs]
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # type: ignore[reportMissingTypeStubs]
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver

from utils.utils import code_logger, pokemon_logger, env
from utils.decoder import extract_cookies
from utils.data import verification_link

load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''
TwoCaptcha_token: str = os.getenv('twocaptcha') or ''
solver = TwoCaptcha(TwoCaptcha_token)
config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)

with open(config_path) as f:
    config = json.load(f)

guild_id = int(config['ids']['guild'])
tree_channel_id = int(config['ids']['tree channel'])
tree_message_id = int(config['ids']['tree'])
tree_id = int(config['ids']['tree id'])
telecom_path = str(config['paths']['telecom'])
session_path = str(config['paths']['session'])

with open(telecom_path) as f:
    data = json.load(f)

browser = str(data['main']['browser'])
tree_cookies = data['cookies']['tree']
user_agent = data['headers']['base']['User-Agent']
X_Super_Properties = data['headers']['tree']['X-Super-Properties']

with open(session_path, 'r') as f:
    session_id = f.read().strip()

tree_headers: dict[str, str] = {
    'Authorization': token,
    'Content-Type': 'application/json',
    'User-Agent': user_agent,
    'X-Super-Properties': X_Super_Properties,
    'Referer': f'https://discord.com/channels/{guild_id}/{tree_channel_id}',
}


payload: dict[str, object] = {
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


def water():
    r = requests.post(
        "https://discord.com/api/v9/interactions",
        headers=tree_headers,
        cookies=tree_cookies,
        json=payload
    )
    if not r.ok:
        code_logger.error(f"Error: {r.status_code} - {r.text}", exc_info=True)


texting_check = config['main']['texts?']
if texting_check:
    email = os.getenv('email')
    phone = os.getenv('phone')
    app_password = os.getenv('app_password')
    carrier = os.getenv('carrier')


def wait_recaptcha_ready(driver: ChromeDriver, timeout: float):
    code_logger.info("Waiting for recaptcha")
    iframe = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[title='reCAPTCHA']"))
    )
    driver.switch_to.frame(iframe)

    WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.ID, "recaptcha-anchor"))
    )

    code_logger.info("Waited for recaptcha, solving.")
    driver.switch_to.default_content()
    return True


def p2verification() -> Optional[Dict[str, Any]]:
    pokemon_logger.info("p2 verification function called, attempting to bypass verification.")

    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")  # type: ignore
    options.add_argument("--no-service-autorun")  # type: ignore
    options.add_argument("--password-store=basic")  # type: ignore
    options.add_argument("--disable-blink-features=AutomationControlled")  # type: ignore
    options.add_argument(f"user-agent={user_agent}")  # type: ignore

    driver: Optional[ChromeDriver] = None

    try:
        driver = uc.Chrome(options=options)
        driver.get(verification_link)

        cookies = extract_cookies(verification_link)
        for cookie in cookies:
            try:
                driver.add_cookie(cookie)  # type: ignore
            except Exception as e:
                code_logger.error(f"An error has occurred while trying to add a cookie {cookie}, {e}")
                continue

        driver.refresh()

        sitekey_recaptcha = "6LfgtMoaAAAAAPB_6kwTMPj9HG_XxRLL7n92jYkD"

        try:
            wait_recaptcha_ready(driver, timeout=60.0)

            result_recaptcha: Dict[str, Any] = solver.recaptcha(sitekey=sitekey_recaptcha, url=verification_link)  # type: ignore
            if not result_recaptcha:
                code_logger.error("2Captcha returned None for recaptcha")
                return None

            return result_recaptcha

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
                cast(ChromeDriver, driver).quit()
        except Exception:
            pass


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
