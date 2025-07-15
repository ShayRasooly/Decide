from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import requests
import os
from requests.exceptions import RequestException
import urllib.parse
import re

# Start Chrome using WebDriver Manager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Go to the Rabbinical Court verdicts page
driver.get("https://www.gov.il/he/Departments/DynamicCollectors/verdict_the_rabbinical_courts?skip=0")

time.sleep(5)  # Wait for the JS to load everything (adjust as needed)

# Find all download links
verdict_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/BlobFolder/']")

if verdict_links:
    url = verdict_links[0].get_attribute("href")
    if url:
        print("Downloading first verdict file:", url)
        # Create downloads directory if it doesn't exist
        download_dir = os.path.join(os.path.dirname(__file__), 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        raw_filename = os.path.basename(url.split('?')[0])
        decoded_filename = urllib.parse.unquote(raw_filename)
        # Remove or replace invalid Windows filename characters
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', decoded_filename)
        file_path = os.path.join(download_dir, safe_filename)
        try:
            session = requests.Session()
            # Transfer cookies from Selenium to requests
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'])
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": driver.current_url
            }
            response = session.get(url, headers=headers)
            response.raise_for_status()
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Saved {file_path}")
        except RequestException as e:
            print(f"Failed to download {url}: {e}")
            if e.response is not None:
                print("Status code:", e.response.status_code)
                print("Response text:", e.response.text)
        except Exception as e:
            print(f"Failed to download {url}: {e}")
    else:
        print("First verdict link does not have a valid href.")
else:
    print("No verdict files found.")

driver.quit()
