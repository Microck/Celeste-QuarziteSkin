import re
import requests
from bs4 import BeautifulSoup
import sys
import os

# --- Configuration ---
GAMEBANANA_URL = "https://gamebanana.com/mods/486547" # Your mod URL
README_PATH = "README.md"
USER_AGENT = "GitHubActionsReadmeStatsUpdater/1.0 (Python)" # Be polite

# Placeholders must match the comments in your README.md
PLACEHOLDERS = {
    "downloads": "<!-- GB_DOWNLOADS -->",
    "views": "<!-- GB_VIEWS -->",
    "likes": "<!-- GB_LIKES -->",
}
# --- End Configuration ---

def scrape_stats(url):
    """Fetches the Gamebanana page and extracts stats."""
    print(f"Fetching stats from: {url}")
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    stats = {}

    # --- Updated HTML Parsing Logic based on NEW Inspector Screenshot ---
    try:
        # Find the main stats module container
        stats_module = soup.find('module', id='StatsModule')

        if stats_module:
            print("Found StatsModule container.")
            # Find the list items within the stats module and extract text from <itemcount> tag

            # Likes
            like_li = stats_module.find('li', class_='LikeCount') # Find li with LikeCount class
            if like_li:
                itemcount_tag = like_li.find('itemcount') # Find the <itemcount> tag within it
                if itemcount_tag:
                    stats['likes'] = itemcount_tag.text # Get the text content
                else:
                    print("Could not find <itemcount> tag within LikeCount li.", file=sys.stderr)
            else:
                 print("Could not find LikeCount li element.", file=sys.stderr)

            # Downloads
            download_li = stats_module.find('li', class_='DownloadCount')
            if download_li:
                itemcount_tag = download_li.find('itemcount')
                if itemcount_tag:
                    stats['downloads'] = itemcount_tag.text
                else:
                    print("Could not find <itemcount> tag within DownloadCount li.", file=sys.stderr)
            else:
                 print("Could not find DownloadCount li element.", file=sys.stderr)

            # Views
            view_li = stats_module.find('li', class_='ViewCount')
            if view_li:
                itemcount_tag = view_li.find('itemcount')
                if itemcount_tag:
                    stats['views'] = itemcount_tag.text
                else:
                    print("Could not find <itemcount> tag within ViewCount li.", file=sys.stderr)
            else:
                 print("Could not find ViewCount li element.", file=sys.stderr)

        else:
            # This was the error before, keep the message just in case
            print("Could not find the main stats module (id='StatsModule').", file=sys.stderr)

    except Exception as e:
        print(f"Error parsing HTML: {e}", file=sys.stderr)

    # Clean up stats (remove potential extra whitespace)
    for key in stats:
        if isinstance(stats[key], str):
            stats[key] = stats[key].strip()

    print(f"Scraped stats: {stats}")
    # Ensure we return None if no stats were found or not all stats were found
    if not stats or not all(k in stats for k in PLACEHOLDERS.keys()):
         print("Failed to find all required stats. Check selectors.", file=sys.stderr)
         return None
    return stats


def update_readme(readme_path, stats):
    """Reads the README, replaces placeholders, and writes back if changed."""
    print(f"Updating README: {readme_path}")
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"Error: README file not found at {readme_path}", file=sys.stderr)
        return False # Indicate failure

    original_content = readme_content # Keep a copy for comparison
    changes_made = False

    for key, placeholder in PLACEHOLDERS.items():
        if key in stats and stats[key] is not None:
            # Regex to find the placeholder and the text immediately following it (until newline or <)
            # This replaces the "N/A" or the old value.
            pattern = re.compile(f"({re.escape(placeholder)})\\s*([^\\n<]+)")
            new_text = f"{placeholder} {stats[key]}"

            # Perform substitution
            readme_content, num_subs = pattern.subn(new_text, readme_content)
            if num_subs > 0:
                print(f"  Updated {key} to {stats[key]}")
                changes_made = True
            else:
                print(f"  Placeholder {placeholder} not found or pattern mismatch.")
        else:
            print(f"  Stat '{key}' not found in scraped data.")


    if changes_made and readme_content != original_content:
        print("Changes detected, writing updated README...")
        try:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print("README update successful.")
            return True # Indicate success
        except IOError as e:
            print(f"Error writing updated README: {e}", file=sys.stderr)
            return False # Indicate failure
    elif not changes_made:
        print("No changes needed in README.")
        return False # Indicate no changes were made
    else:
        print("Content comparison indicates no effective change, skipping write.")
        return False


if __name__ == "__main__":
    print("Starting README stats update process...")
    scraped_data = scrape_stats(GAMEBANANA_URL)
    if scraped_data:
        made_changes = update_readme(README_PATH, scraped_data)
        # Exit with success code 0 regardless of whether changes were made
        # The commit step in the Action handles whether to actually commit
        sys.exit(0)
    else:
        print("Failed to scrape stats, README not updated.", file=sys.stderr)
        sys.exit(1) # Exit with error code 1 to signal failure to Actions

    # This line is technically unreachable due to sys.exit() calls above
    # print("README stats update process finished.")
