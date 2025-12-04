import re
import sys
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone

# --- Helper function for debugging ---
def log_and_flush(message):
    """Prints a message and flushes stdout to ensure it appears in logs immediately."""
    print(message)
    sys.stdout.flush()

# --- Configuration ---
GAMEBANANA_URL = "https://gamebanana.com/mods/486547"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = SCRIPT_DIR
README_PATH = os.path.join(REPO_DIR, "README.md")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
PLACEHOLDERS = {
    "downloads": "<!-- GB_DOWNLOADS -->",
    "views": "<!-- GB_VIEWS -->",
    "likes": "<!-- GB_LIKES -->",
    "timestamp": "<!-- LAST_UPDATED -->",
}
# --- End Configuration ---

def scrape_stats(url):
    """Fetches the Gamebanana page using Selenium and extracts stats."""
    log_and_flush(f"--- Starting scrape_stats for URL: {url} ---")
    
    log_and_flush("Configuring Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--log-level=3')
    log_and_flush("Chrome options configured.")
    
    driver = None
    try:
        log_and_flush("Attempting to initialize WebDriver...")
        # THIS IS A LIKELY PLACE TO HANG
        driver = webdriver.Chrome(options=chrome_options)
        log_and_flush("WebDriver initialized successfully.")

        log_and_flush("Setting page load timeout to 30 seconds...")
        driver.set_page_load_timeout(30)
        log_and_flush("Page load timeout set.")

        log_and_flush(f"Sending driver.get() command to: {url}")
        # THIS IS THE SECOND MOST LIKELY PLACE TO HANG
        driver.get(url)
        log_and_flush("driver.get() command completed. Page load initiated.")

        log_and_flush("Waiting up to 20 seconds for the StatsModule to be present...")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "StatsModule"))
        )
        log_and_flush("StatsModule found. Proceeding with scraping.")

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        stats = {}
        stats_module = soup.find('module', id='StatsModule')
        if stats_module:
            log_and_flush("Found StatsModule container.")
            like_li = stats_module.find('li', class_='LikeCount')
            if like_li:
                itemcount_tag = like_li.find('itemcount')
                if itemcount_tag: stats['likes'] = itemcount_tag.text.strip()
            download_li = stats_module.find('li', class_='DownloadCount')
            if download_li:
                itemcount_tag = download_li.find('itemcount')
                if itemcount_tag: stats['downloads'] = itemcount_tag.text.strip()
            view_li = stats_module.find('li', class_='ViewCount')
            if view_li:
                itemcount_tag = view_li.find('itemcount')
                if itemcount_tag: stats['views'] = itemcount_tag.text.strip()
        else:
            log_and_flush("ERROR: Could not find the main stats module (id='StatsModule').")
            return None

    except TimeoutException as e:
        log_and_flush(f"ERROR: A timeout occurred. The page or element did not load in time: {e}")
        return None
    except WebDriverException as e:
        log_and_flush(f"ERROR: WebDriverException occurred: {e}")
        return None
    except Exception as e:
        log_and_flush(f"ERROR: An unexpected error occurred during Selenium scraping: {e}")
        return None
    finally:
        if driver:
            log_and_flush("Quitting WebDriver.")
            driver.quit()

    log_and_flush(f"Scraped stats: {stats}")
    if not stats or not all(k in stats for k in ["downloads", "views", "likes"]):
        log_and_flush("ERROR: Failed to find all required stats.")
        return None
    return stats

def update_readme(readme_path, stats_data):
    """Reads the README, replaces placeholders, and writes back if changed."""
    log_and_flush(f"Updating README: {readme_path}")
    if not os.path.exists(readme_path):
        log_and_flush(f"ERROR: README file not found at {readme_path}")
        return False
    try:
        with open(readme_path, 'r', encoding='utf-8') as f: readme_content = f.read()
    except Exception as e:
        log_and_flush(f"Error reading README file: {e}")
        return False
    original_content = readme_content; changes_made = False
    for key, placeholder in PLACEHOLDERS.items():
        if key in stats_data and stats_data[key] is not None:
            pattern = re.compile(f"({re.escape(placeholder)})\\s*([^\\n<]+)")
            new_text = f"{placeholder} {stats_data[key]}"
            readme_content, num_subs = pattern.subn(new_text, readme_content)
            if num_subs > 0: log_and_flush(f"  Updated {key} to {stats_data[key]}"); changes_made = True
            elif key != 'timestamp': log_and_flush(f"  Placeholder {placeholder} not found or pattern mismatch.")
        elif key != 'timestamp': log_and_flush(f"  Stat '{key}' not found in scraped data.")
    if changes_made and readme_content != original_content:
        log_and_flush("Changes detected, writing updated README...")
        try:
            with open(readme_path, 'w', encoding='utf-8') as f: f.write(readme_content)
            log_and_flush("README update successful."); return True
        except IOError as e: log_and_flush(f"Error writing updated README: {e}"); return False
    else: log_and_flush("No changes needed in README."); return False

# --- Main Execution Block ---
if __name__ == "__main__":
    log_and_flush(f"Starting README stats update process at {datetime.now()}...")
    
    scraped_data = scrape_stats(GAMEBANANA_URL)

    if scraped_data:
        now_utc = datetime.now(timezone.utc)
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        scraped_data['timestamp'] = timestamp_str
        log_and_flush(f"Generated timestamp: {timestamp_str}")

        readme_changed = update_readme(README_PATH, scraped_data)

        if readme_changed:
            log_and_flush("README was updated. The workflow will now commit and push the changes.")
            sys.exit(0) # Success
        else:
            log_and_flush("No changes were made to the README.")
            sys.exit(0) # Success, but nothing to do
    else:
        log_and_flush("Failed to scrape stats, README not updated.")
        sys.exit(1) # Error
