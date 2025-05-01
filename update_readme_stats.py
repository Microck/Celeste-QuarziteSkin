import re
import requests # Still useful for potentially fetching other things if needed, but not for main scraping
from bs4 import BeautifulSoup
import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
import time # Added for potential waits
from datetime import datetime # Import datetime

# --- Configuration ---
GAMEBANANA_URL = "https://gamebanana.com/mods/486547" # Your mod URL
README_PATH = "README.md"
# User agent for Selenium (less critical than for requests, but good practice)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

# Placeholders must match the comments in your README.md
PLACEHOLDERS = {
    "downloads": "<!-- GB_DOWNLOADS -->",
    "views": "<!-- GB_VIEWS -->",
    "likes": "<!-- GB_LIKES -->",
    "timestamp": "<!-- LAST_UPDATED -->", # <<< ADDED TIMESTAMP PLACEHOLDER
}
# --- End Configuration ---

def scrape_stats(url):
    """Fetches the Gamebanana page using Selenium and extracts stats."""
    print(f"Fetching stats from: {url} using Selenium")

    # Set up Selenium WebDriver Options
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--headless") # Run in headless mode (no browser UI)
    chrome_options.add_argument("--no-sandbox") # Required for running as root/in containers
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    chrome_options.add_argument("--disable-gpu") # Often necessary for headless
    chrome_options.add_argument("--window-size=1920,1080") # Specify window size

driver = None # Initialize driver to None
    try:
        # Initialize WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        print("WebDriver initialized successfully.")
        # <<< ADD THIS LINE >>>
        time.sleep(2) # Add a small pause to allow driver to fully initialize
        # <<< END ADDED LINE >>>

        # Load the page
        print(f"Loading page: {url}")
        driver.get(url)
        time.sleep(5) # Wait 5 seconds for JS loading
        print("Page loaded. Getting page source...")

        # Get the page source after JS execution
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        stats = {}

        # --- HTML Parsing Logic ---
        stats_module = soup.find('module', id='StatsModule')

        if stats_module:
            print("Found StatsModule container.")
            # Likes
            like_li = stats_module.find('li', class_='LikeCount')
            if like_li:
                itemcount_tag = like_li.find('itemcount')
                if itemcount_tag: stats['likes'] = itemcount_tag.text.strip()
                else: print("Could not find <itemcount> tag within LikeCount li.", file=sys.stderr)
            else: print("Could not find LikeCount li element.", file=sys.stderr)

            # Downloads
            download_li = stats_module.find('li', class_='DownloadCount')
            if download_li:
                itemcount_tag = download_li.find('itemcount')
                if itemcount_tag: stats['downloads'] = itemcount_tag.text.strip()
                else: print("Could not find <itemcount> tag within DownloadCount li.", file=sys.stderr)
            else: print("Could not find DownloadCount li element.", file=sys.stderr)

            # Views
            view_li = stats_module.find('li', class_='ViewCount')
            if view_li:
                itemcount_tag = view_li.find('itemcount')
                if itemcount_tag: stats['views'] = itemcount_tag.text.strip()
                else: print("Could not find <itemcount> tag within ViewCount li.", file=sys.stderr)
            else: print("Could not find ViewCount li element.", file=sys.stderr)

        else:
            print("Could not find the main stats module (id='StatsModule') even with Selenium.", file=sys.stderr)

    except TimeoutException:
        print("Error: Page load timed out.", file=sys.stderr)
        return None
    except WebDriverException as e:
        print(f"Error: WebDriverException occurred: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error during Selenium scraping: {e}", file=sys.stderr)
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

    print(f"Scraped stats: {stats}")
    # Check if all *original* stats were found (don't require timestamp here)
    if not stats or not all(k in stats for k in ["downloads", "views", "likes"]):
         print("Failed to find all required stats (downloads, views, likes). Check selectors or page structure.", file=sys.stderr)
         return None
    return stats


def update_readme(readme_path, stats_data):
    """Reads the README, replaces placeholders, and writes back if changed."""
    print(f"Updating README: {readme_path}")
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"Error: README file not found at {readme_path}", file=sys.stderr)
        return False

    original_content = readme_content
    changes_made = False

    # The stats_data dictionary now includes the timestamp if scraping was successful
    for key, placeholder in PLACEHOLDERS.items():
        if key in stats_data and stats_data[key] is not None:
            # Regex to find the placeholder and the text immediately following it (until newline or <)
            pattern = re.compile(f"({re.escape(placeholder)})\\s*([^\\n<]+)")
            # Use the value from the stats_data dictionary (which includes the timestamp string)
            new_text = f"{placeholder} {stats_data[key]}"

            # Perform substitution
            readme_content, num_subs = pattern.subn(new_text, readme_content)
            if num_subs > 0:
                print(f"  Updated {key} to {stats_data[key]}")
                changes_made = True
            else:
                # Don't print error if timestamp placeholder wasn't found initially
                if key != 'timestamp':
                    print(f"  Placeholder {placeholder} not found or pattern mismatch.")
        # Don't print error if timestamp key is missing (it's added later)
        elif key != 'timestamp':
            print(f"  Stat '{key}' not found in scraped data.")


    if changes_made and readme_content != original_content:
        print("Changes detected, writing updated README...")
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print("README update successful.")
            return True
        except IOError as e:
            print(f"Error writing updated README: {e}", file=sys.stderr)
            return False
    elif not changes_made:
        print("No changes needed in README.")
        return False
    else:
        print("Content comparison indicates no effective change, skipping write.")
        return False


if __name__ == "__main__":
    print("Starting README stats update process...")
    scraped_data = scrape_stats(GAMEBANANA_URL)

    if scraped_data:
        # <<< GET CURRENT TIME AND ADD TO DATA >>>
        # Get current time in UTC for consistency
        now_utc = datetime.utcnow()
        # Format it (example: 2025-05-01 23:59:59 UTC) - Adjust format if desired
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        # Add the timestamp to the data dictionary to be updated
        scraped_data['timestamp'] = timestamp_str
        print(f"Generated timestamp: {timestamp_str}")

        # Pass the dictionary containing stats AND timestamp to update_readme
        made_changes = update_readme(README_PATH, scraped_data)
        sys.exit(0) # Exit success
    else:
        print("Failed to scrape stats, README not updated.", file=sys.stderr)
        sys.exit(1) # Exit error
