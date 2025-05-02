import re
import sys
import os
import subprocess # To run Git commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone # Import timezone for UTC

# --- Configuration ---
GAMEBANANA_URL = "https://gamebanana.com/mods/486547"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = SCRIPT_DIR
README_PATH = os.path.join(REPO_DIR, "README.md")
GITHUB_PAT = os.environ.get('GITHUB_PAT')
REPO_URL_WITH_PAT = f"https://{GITHUB_PAT}@github.com/Microck/Celeste-QuarziteSkin.git"
GIT_USER_NAME = "StatsUpdaterBot"
GIT_USER_EMAIL = "stats-updater@local.pc"
GIT_BRANCH = "main"
CHROMEDRIVER_PATH = None
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
PLACEHOLDERS = {
    "downloads": "<!-- GB_DOWNLOADS -->",
    "views": "<!-- GB_VIEWS -->",
    "likes": "<!-- GB_LIKES -->",
    "timestamp": "<!-- LAST_UPDATED -->",
}
# --- End Configuration ---

# --- Helper Function for Git Commands ---
def run_git_command(command, working_dir):
    """Runs a Git command in the specified directory."""
    print(f"Running Git: {' '.join(command)}")
    if not os.path.exists(working_dir):
         print(f"Error: Git working directory '{working_dir}' does not exist.", file=sys.stderr)
         return False
    try:
        result = subprocess.run(command, cwd=working_dir, check=True, capture_output=True, text=True, env=os.environ, shell=True)
        print(f"Git stdout:\n{result.stdout}")
        if result.stderr: print(f"Git stderr:\n{result.stderr}", file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running Git command {' '.join(command)}:", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        print(f"Stderr:\n{e.stderr}", file=sys.stderr); print(f"Stdout:\n{e.stdout}", file=sys.stderr)
        return False
    except FileNotFoundError: print("Error: 'git' command not found.", file=sys.stderr); return False
    except Exception as e: print(f"An unexpected error occurred running git: {e}", file=sys.stderr); return False
# --- End Helper Function ---

def scrape_stats(url):
    """Fetches the Gamebanana page using Selenium and extracts stats."""
    print(f"Fetching stats from: {url} using Selenium")
    chrome_options = Options()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--headless"); chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage"); chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080"); chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--log-level=3')
    driver = None
    try:
        if CHROMEDRIVER_PATH and os.path.exists(CHROMEDRIVER_PATH):
             service = Service(executable_path=CHROMEDRIVER_PATH)
             driver = webdriver.Chrome(service=service, options=chrome_options)
             print(f"WebDriver initialized using path: {CHROMEDRIVER_PATH}")
        else:
             driver = webdriver.Chrome(options=chrome_options)
             print("WebDriver initialized using system PATH.")
        time.sleep(2)
        print(f"Loading page: {url}"); driver.get(url); time.sleep(5)
        print("Page loaded. Getting page source...")
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        stats = {}
        stats_module = soup.find('module', id='StatsModule')
        if stats_module:
            print("Found StatsModule container.")
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
        else: print("Could not find the main stats module (id='StatsModule').", file=sys.stderr)
    except TimeoutException: print("Error: Page load timed out.", file=sys.stderr); return None
    except WebDriverException as e: print(f"Error: WebDriverException occurred: {e}", file=sys.stderr); print("Ensure Chrome/ChromeDriver setup is correct.", file=sys.stderr); return None
    except Exception as e: print(f"Error during Selenium scraping: {e}", file=sys.stderr); return None
    finally:
        if driver: print("Quitting WebDriver."); driver.quit()
    print(f"Scraped stats: {stats}")
    if not stats or not all(k in stats for k in ["downloads", "views", "likes"]):
         print("Failed to find all required stats.", file=sys.stderr); return None
    return stats

def update_readme(readme_path, stats_data):
    """Reads the README, replaces placeholders, and writes back if changed."""
    print(f"Updating README: {readme_path}")
    if not os.path.exists(readme_path): print(f"Error: README file not found at {readme_path}", file=sys.stderr); return False
    try:
        with open(readme_path, 'r', encoding='utf-8') as f: readme_content = f.read()
    except Exception as e: print(f"Error reading README file: {e}", file=sys.stderr); return False
    original_content = readme_content; changes_made = False
    for key, placeholder in PLACEHOLDERS.items():
        if key in stats_data and stats_data[key] is not None:
            pattern = re.compile(f"({re.escape(placeholder)})\\s*([^\\n<]+)")
            new_text = f"{placeholder} {stats_data[key]}"
            readme_content, num_subs = pattern.subn(new_text, readme_content)
            if num_subs > 0: print(f"  Updated {key} to {stats_data[key]}"); changes_made = True
            elif key != 'timestamp': print(f"  Placeholder {placeholder} not found or pattern mismatch.")
        elif key != 'timestamp': print(f"  Stat '{key}' not found in scraped data.")
    if changes_made and readme_content != original_content:
        print("Changes detected, writing updated README...")
        try:
            with open(readme_path, 'w', encoding='utf-8') as f: f.write(readme_content)
            print("README update successful."); return True
        except IOError as e: print(f"Error writing updated README: {e}", file=sys.stderr); return False
    else: print("No changes needed in README."); return False

# --- Main Execution Block ---
if __name__ == "__main__":
    print(f"Starting README stats update process locally at {datetime.now()}...")
    if not GITHUB_PAT:
        print("CRITICAL ERROR: GITHUB_PAT environment variable not set.", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(os.path.join(REPO_DIR, '.git')):
        print(f"Error: Git repository not found at '{REPO_DIR}'. Please clone it first.", file=sys.stderr)
        sys.exit(1)
    print("Configuring Git user info...")
    if not run_git_command(['git', 'config', 'user.name', GIT_USER_NAME], REPO_DIR): sys.exit(1)
    if not run_git_command(['git', 'config', 'user.email', GIT_USER_EMAIL], REPO_DIR): sys.exit(1)
    print("Setting remote URL with PAT...")
    if not run_git_command(['git', 'remote', 'set-url', 'origin', REPO_URL_WITH_PAT], REPO_DIR): sys.exit(1)
    print(f"Pulling latest changes from origin/{GIT_BRANCH}...")
    if not run_git_command(['git', 'pull', 'origin', GIT_BRANCH], REPO_DIR):
        print("Failed to pull latest changes.", file=sys.stderr); sys.exit(1)
    print("Pull successful or already up-to-date.")

    scraped_data = scrape_stats(GAMEBANANA_URL)

    # --- This is the block that needed indentation ---
    if scraped_data:
        # Indent these lines
        now_utc = datetime.now(timezone.utc) # Use timezone-aware datetime
        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        scraped_data['timestamp'] = timestamp_str
        print(f"Generated timestamp: {timestamp_str}")

        # Indent this line
        readme_changed = update_readme(README_PATH, scraped_data)

        # Indent this block
        if readme_changed and GITHUB_PAT:
            print("README changed, attempting to commit and push...")
            if not run_git_command(['git', 'add', README_PATH], REPO_DIR): sys.exit(1)
            status_result = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO_DIR, capture_output=True, text=True)
            if os.path.basename(README_PATH) in status_result.stdout:
                 print("Staged changes detected, attempting commit...")
                 if not run_git_command(['git', 'commit', '-m', 'Automated update of Gamebanana stats'], REPO_DIR): sys.exit(1)
                 print("Commit successful, attempting push...")
                 if not run_git_command(['git', 'push', 'origin', GIT_BRANCH], REPO_DIR): sys.exit(1)
                 print("Changes pushed successfully to GitHub.")
            else: print("No actual changes staged for commit after add, skipping commit/push.")
        elif readme_changed and not GITHUB_PAT: print("README changed locally, but skipping commit/push because GITHUB_PAT is not set.")
        else: print("No changes written to README, skipping commit/push.")

        sys.exit(0) # Success
    # --- End of the block that needed indentation ---
    else:
        # This else corresponds to 'if scraped_data:' and should be at the same level
        print("Failed to scrape stats, README not updated.", file=sys.stderr)
        sys.exit(1) # Error
