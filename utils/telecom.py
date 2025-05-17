from pathlib import Path
import json
import smtplib
import os
import time
import requests
import random
from email.message import EmailMessage
from typing import Any, Dict

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc  # type: ignore[reportMissingTypeStubs]
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeDriver

from utils.utils import code_logger, env

config_path = Path("data/config/config.json")
config_path.parent.mkdir(parents=True, exist_ok=True)


load_dotenv(dotenv_path=Path(env))
token: str = os.getenv('discord_token') or ''


with open(config_path) as f:
    config = json.load(f)


guild_id = int(config['ids']['guild'])
tree_channel_id = int(config['ids']['tree channel'])
tree_message_id = int(config['ids']['tree'])
tree_id = int(config['ids']['tree id'])
telecom_path = str(config['paths']['telecom'])


with open(telecom_path) as f:
    data = json.load(f)

cookies = data['cookies']
user_agent = data['headers']['User-Agent']
X_Super_Properties = data['headers']['X-Super-Properties']

headers: dict[str, str] = {
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
    "session_id": "YOUR_SESSION_ID",
    "data": {
        "component_type": 2,
        "custom_id": "grow"
    }
}


def water():
    r = requests.post(
        "https://discord.com/api/v9/interactions",
        headers=headers,
        cookies=cookies,
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


def p2verification():
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run --no-service-autorun --password-store=basic")  # type: ignore
    options.add_argument("--disable-blink-features=AutomationControlled")  # type: ignore

    try:
        driver: ChromeDriver = uc.Chrome(options=options)
    except WebDriverException as e:
        code_logger.error(f'Failed to launch undetected_chromedriver: {e}', exc_info=True)
        return

    try:
        driver.get("https://verify.poketwo.net/captcha/944666961743343639")
    except Exception as e:
        code_logger.error(f'Failed to load CAPTCHA page: {e}', exc_info=True)
        driver.quit()
        return

    try:
        WebDriverWait(driver, 60).until(recaptcha_is_ready)

        token = str(driver.execute_script(  # type: ignore
            "return document.getElementById('g-recaptcha-response').value"
        ))

        code_logger.info(f"Extracted reCAPTCHA token: {token}")

    except TimeoutException:
        code_logger.warning("CAPTCHA token wait timed out after 5 minutes.")
    except Exception as e:
        code_logger.error(f'Error extracting CAPTCHA token: {e}', exc_info=True)
    finally:
        driver.quit()


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


def recaptcha_is_ready(driver: ChromeDriver) -> bool:
    result: bool = bool(driver.execute_script(  # type: ignore
        "return document.getElementById('g-recaptcha-response')?.value?.length > 0"
    ))
    return result


def text(body: str) -> None:
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
