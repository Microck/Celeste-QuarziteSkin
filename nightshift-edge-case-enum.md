# Edge-Case Enumeration — Celeste-QuarziteSkin

**Task:** edge-case-enum  
**Category:** options  
**Date:** 2026-04-06  
**Scanner:** Nightshift v3 (GLM 5.1)

---

## 1. Python Scraper (`update_readme_stats.py`)

### P2 — Selenium WebDriver Leaks on Early Timeout

**File:** `update_readme_stats.py:59-64`  
**Issue:** If `driver.get()` succeeds but `WebDriverWait` times out, the `except TimeoutException` block returns `None` before the `finally` block runs (in CPython, `finally` always runs after `except`, but the return value is already set). The driver is properly cleaned in `finally`, but if `webdriver.Chrome()` itself raises (e.g., Chrome binary not installed), the driver variable is still `None` — the `finally` handles this correctly. However, there's no retry logic at all: a single transient Gamebanana timeout causes the entire CI job to fail.

**Recommendation:** Add a simple retry loop (1-2 attempts) around the Selenium scrape to handle transient network issues.

### P2 — README Placeholder Pattern Assumes Single-Line Format

**File:** `update_readme_stats.py:113-114`  
**Issue:** The regex `({PLACEHOLDER})\\s*([^\\n<]+)` only matches content on the same line as the placeholder. If the README format changes to put the value on the next line or wraps it in additional HTML tags, the pattern silently fails without error.

**Recommendation:** Document the expected README format or use a more robust replacement strategy (e.g., named HTML comments with start/end markers).

### P3 — No Selenium Dependency Pinned

**File:** `.github/workflows/update-readme-stats.yml:28`  
**Issue:** `pip install beautifulsoup4 selenium` installs the latest version. A breaking selenium update could silently break the scraper. The workflow already failed to install Chrome correctly in some GitHub Actions runner updates.

**Recommendation:** Pin `selenium>=4.0,<5` and `beautifulsoup4>=4.12,<5` in a `requirements.txt`.

### P3 — No Rate-Limit or Bot Detection Handling

**File:** `update_readme_stats.py:43-55`  
**Issue:** The scraper uses a fixed `USER_AGENT` string and makes no attempt to handle Cloudflare/bot protection that Gamebanana may deploy. The `30s` page load timeout and `20s` element wait are reasonable but the script provides no fallback (e.g., API endpoint or cached stats).

**Recommendation:** Consider adding a fallback to the Gamebanana API (if available) or cache the last known stats as a degradation path.

---

## 2. Sprite Animation Definitions (`Graphics/Sprites.xml`)

### P3 — `bigFallRecover` Uses Frame Multiplication Without Documented Bounds

**File:** `Graphics/Sprites.xml:62`  
**Issue:** `frames="5*5,6*4,7*3,8,8,9,9,10,10,10"` uses Celeste's frame multiplication syntax (frame `N*M` = repeat frame N, M times). This is valid Celeste syntax but the animation is 5+4+3+1+1+1+1+1+1+1 = 18 frames at 0.08s delay = 1.44s total. If the sprite sheet doesn't have frames up to index 10, this will crash or show blank frames in-game.

**Recommendation:** Verify the `bigFall` sprite sheet has at least 11 frames (0-10). Add a comment documenting the expected frame count.

### P3 — Playback Sprite Overrides Only `idleC`

**File:** `Graphics/Microck/Quarzite_Playback/Sprites.xml`  
**Issue:** The playback (silhouette) variant only overrides `idleC` animation, inheriting everything else from the main Quarzite sprite via `copy="Microck_Quarzite"`. If the main sprite adds new animations, the playback variant will automatically use the base sprite's frames (not silhouettes) for those new animations. This could cause visual inconsistencies if new animations are added later.

**Recommendation:** Add a comment noting that any new animations added to the main sprite need corresponding silhouette frames in the playback variant.

---

## 3. Mod Configuration (`everest.yaml`)

### P3 — Hardcoded Everest Version Dependency

**File:** `everest.yaml:3-4`  
**Issue:** `Version: 1.4465.0` for Everest is pinned. When Everest updates with breaking API changes, this skin may fail to load or crash the game. No compatibility matrix is documented.

**Recommendation:** Test with newer Everest versions and update the dependency version. Consider using a minimum version bound if Everest supports it.

### P3 — SkinModHelperPlus Version 0.10.4 — Potential Breaking Changes

**File:** `everest.yaml:5-6`  
**Issue:** `SkinModHelperPlus` at `0.10.4` is a community mod with frequent updates. The `SkinModHelperConfig.yaml` uses features (`Silhouette_List`, `Character_ID`) that may have API changes across versions.

**Recommendation:** Document the tested configuration and test with newer SkinModHelperPlus versions.

---

## 4. GitHub Actions Workflow

### P2 — Monthly Cron Schedule May Miss Stats Updates

**File:** `.github/workflows/update-readme-stats.yml:4`  
**Issue:** `cron: '0 0 1 * *'` runs monthly. Stats (downloads, views, likes) can change significantly in a month. Users viewing the repo see stale data for up to 30 days.

**Recommendation:** Consider changing to weekly (`0 0 * * 0`) for more frequent updates. The scraper is lightweight enough that weekly runs are reasonable.

### P3 — No Concurrency Control

**File:** `.github/workflows/update-readme-stats.yml`  
**Issue:** If `workflow_dispatch` is triggered while a scheduled run is in progress, both runs may attempt to commit and push simultaneously, causing a git push conflict.

**Recommendation:** Add `concurrency: update-stats-group` with `cancel-in-progress: true` to prevent parallel runs.

### P3 — PAT Token Scoped to Entire Repository

**File:** `.github/workflows/update-readme-stats.yml:12`  
**Issue:** The workflow uses `${{ secrets.PAT }}` with `contents: write` permission. If the PAT is over-scoped (e.g., has org-wide access), a compromised workflow could affect other repos.

**Recommendation:** Use a fine-grained PAT scoped to only this repository with only `contents: write` permission.

---

## 5. Dialog Text Files

### P3 — Inconsistent Character Names Between Languages

**Files:** `Dialog/English.txt`, `Dialog/Spanish.txt`  
**Issue:** Both files define `SkinModHelper_Player__Microck_Quarzite` as "Quarzite" and `SkinModHelper_Player__Microck_Quarzite_Playback` as "Quarzite Silhouette". The Spanish file uses the English name "Quarzite Silhouette" instead of a Spanish translation (e.g., "Quarzite Silueta"). While this is technically correct (character names are often untranslated), it should be intentional.

**Recommendation:** If "Silhouette" should be translated for Spanish players, update `Dialog/Spanish.txt`.

---

## Summary

| Severity | Count | Areas |
|----------|-------|-------|
| P0 (Critical) | 0 | — |
| P1 (High) | 0 | — |
| P2 (Medium) | 3 | Scraper retry, placeholder pattern, cron schedule |
| P3 (Low) | 7 | Dependencies, sprite bounds, workflow concurrency, PAT scope, naming |

No critical issues found. The repo is a well-structured Celeste skin mod. The main areas for improvement are in the Python scraper's resilience and the CI workflow's robustness.
