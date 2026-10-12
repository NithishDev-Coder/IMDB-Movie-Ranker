"""
Scraper module for IMDb Movie Rating Scraper & Tracker.
Uses Selenium WebDriver to dynamically extract movie rank, title, release year,
and rating from IMDb Top 250 list.
"""

import time
import json
import re
from typing import List, Dict, Any, Callable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import (
    IMDB_TOP_250_URL,
    EXPLICIT_WAIT_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    USER_AGENT,
    DEFAULT_HEADLESS,
)
from logger import get_logger

logger = get_logger("Scraper")


class IMDbScraper:
    """IMDb Top 250 Movie Scraper powered by Selenium Chrome WebDriver."""

    def __init__(self, headless: bool = DEFAULT_HEADLESS):
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None

    def _init_driver(self) -> webdriver.Chrome:
        """Initializes and returns a configured Chrome WebDriver instance."""
        logger.info(f"Initializing Chrome WebDriver (Headless={self.headless})...")
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Anti-bot detection & stability settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"user-agent={USER_AGENT}")
        options.add_argument("accept-language=en-US,en;q=0.9")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Bypass navigator.webdriver detection
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )

        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        return driver

    def scrape_top_250(
        self, status_callback: Optional[Callable[[str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Navigates to IMDb Top 250, waits for elements to render, and extracts movie data.
        
        Args:
            status_callback: Optional function to report progress messages to UI/CLI.
            
        Returns:
            List of dictionaries containing raw scraped movie data.
        """
        def update_status(msg: str):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        movies: List[Dict[str, Any]] = []

        try:
            update_status("Starting Chrome WebDriver...")
            self.driver = self._init_driver()

            update_status(f"Navigating to IMDb Top 250 ({IMDB_TOP_250_URL})...")
            self.driver.get(IMDB_TOP_250_URL)

            update_status("Waiting for dynamic content to load...")
            wait = WebDriverWait(self.driver, EXPLICIT_WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            time.sleep(2)  # Give JS engine a moment to hydrate DOM components

            # Scroll down to ensure all lazy-loaded elements are populated
            update_status("Scrolling page to trigger lazy loading...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")

            # Extraction Strategy 1: HTML DOM elements
            update_status("Locating movie list items in DOM...")
            items = self.driver.find_elements(By.CSS_SELECTOR, "li.ipc-metadata-list-summary-item")
            update_status(f"Detected {len(items)} movie entries in DOM.")

            for idx, item in enumerate(items):
                try:
                    # Title
                    title = ""
                    title_els = item.find_elements(By.CSS_SELECTOR, "h3.ipc-title__text, h4.ipc-title__text, .ipc-title__text, .cli-title a")
                    if title_els:
                        raw_title = title_els[0].text.strip()
                        # Clean leading rank numbers like "1. The Shawshank Redemption"
                        if "." in raw_title:
                            parts = raw_title.split(".", 1)
                            if parts[0].strip().isdigit():
                                raw_title = parts[1].strip()
                        title = raw_title

                    # Rank
                    rank = idx + 1
                    rank_els = item.find_elements(By.CSS_SELECTOR, "div.ipc-signpost__text, [data-testid='title-list-item-ranking']")
                    if rank_els:
                        r_txt = rank_els[0].text.replace("#", "").strip()
                        if r_txt.isdigit():
                            rank = int(r_txt)

                    # Year
                    year = None
                    meta_items = item.find_elements(
                        By.CSS_SELECTOR, ".cli-title-metadata li, .cli-title-metadata span, li.ipc-inline-list__item, span.cli-title-metadata-item"
                    )
                    for span in meta_items:
                        txt = span.text.strip()
                        if re.match(r"^\d{4}$", txt):
                            year = int(txt)
                            break

                    # Fallback Year from poster alt text if span missing
                    if year is None:
                        img_els = item.find_elements(By.CSS_SELECTOR, "img.ipc-image")
                        if img_els:
                            alt = img_els[0].get_attribute("alt") or ""
                            m_yr = re.search(r"\((\d{4})\)", alt)
                            if m_yr:
                                year = int(m_yr.group(1))

                    # Poster URL
                    poster_url = None
                    img_els = item.find_elements(By.CSS_SELECTOR, "img.ipc-image")
                    if img_els:
                        poster_url = img_els[0].get_attribute("src") or img_els[0].get_attribute("data-src")
                        if not poster_url:
                            # Try srcset
                            srcset = img_els[0].get_attribute("srcset")
                            if srcset:
                                # Pick first URL in srcset
                                poster_url = srcset.split(",")[0].strip().split(" ")[0]

                    # Rating
                    rating = None
                    rating_spans = item.find_elements(
                        By.CSS_SELECTOR, "span.ipc-rating-star--rating, span.ipc-rating-star"
                    )
                    if rating_spans:
                        m_rate = re.search(r"(\d+\.\d+)", rating_spans[0].text)
                        if m_rate:
                            rating = float(m_rate.group(1))

                    if title:
                        movies.append({
                            "Rank": rank,
                            "Title": title,
                            "Year": year,
                            "Rating": rating,
                            "Poster_Url": poster_url
                        })

                except Exception as ex:
                    logger.warning(f"Error parsing item index {idx}: {ex}")

            update_status(f"DOM parsing completed. Extracted {len(movies)} movie records.")

            # Extraction Strategy 2: JSON-LD Structured Data Fallback / Enrichment
            update_status("Checking embedded JSON-LD structured data for validation & poster enrichment...")
            json_scripts = self.driver.find_elements(By.XPATH, '//script[@type="application/ld+json"]')
            for script in json_scripts:
                try:
                    raw_json = script.get_attribute("innerHTML")
                    if not raw_json:
                        continue
                    data = json.loads(raw_json)
                    if isinstance(data, dict) and data.get("@type") == "ItemList":
                        items_list = data.get("itemListElement", [])
                        if len(items_list) > 0:
                            update_status(f"Found {len(items_list)} movies in JSON-LD payload.")
                            json_map = {}
                            for idx, entry in enumerate(items_list):
                                if not isinstance(entry, dict):
                                    continue
                                movie_obj = entry.get("item", entry)
                                if not isinstance(movie_obj, dict):
                                    continue

                                m_rank = entry.get("position", idx + 1)
                                m_title = movie_obj.get("name", "").strip()
                                if not m_title:
                                    continue
                                
                                m_year = None
                                if "datePublished" in movie_obj and movie_obj["datePublished"]:
                                    m_year_match = re.search(r"\d{4}", str(movie_obj["datePublished"]))
                                    if m_year_match:
                                        m_year = int(m_year_match.group(0))
                                
                                m_rating = None
                                agg_rating = movie_obj.get("aggregateRating", {})
                                if isinstance(agg_rating, dict) and "ratingValue" in agg_rating:
                                    try:
                                        m_rating = float(agg_rating["ratingValue"])
                                    except (ValueError, TypeError):
                                        m_rating = None

                                m_poster = None
                                if "image" in movie_obj:
                                    if isinstance(movie_obj["image"], str):
                                        m_poster = movie_obj["image"]
                                    elif isinstance(movie_obj["image"], dict) and "url" in movie_obj["image"]:
                                        m_poster = movie_obj["image"]["url"]

                                json_map[m_title.lower()] = {
                                    "Rank": m_rank,
                                    "Title": m_title,
                                    "Year": m_year,
                                    "Rating": m_rating,
                                    "Poster_Url": m_poster
                                }

                            # If DOM extracted movies, enrich any missing year/rating/poster values
                            if movies:
                                for m in movies:
                                    t_key = m["Title"].lower()
                                    if t_key in json_map:
                                        match_entry = json_map[t_key]
                                        if m["Year"] is None and match_entry["Year"] is not None:
                                            m["Year"] = match_entry["Year"]
                                        if m["Rating"] is None and match_entry["Rating"] is not None:
                                            m["Rating"] = match_entry["Rating"]
                                        if not m.get("Poster_Url") and match_entry.get("Poster_Url"):
                                            m["Poster_Url"] = match_entry["Poster_Url"]
                            else:
                                # Fallback completely to JSON-LD if DOM failed
                                movies = list(json_map.values())

                except Exception as json_ex:
                    logger.warning(f"Error parsing JSON-LD script: {json_ex}")

            update_status(f"Scraping finished. Total valid movie entries collected: {len(movies)}.")

        except Exception as e:
            msg = f"Scraping encountered an error: {str(e)}"
            logger.error(msg, exc_info=True)
            if status_callback:
                status_callback(f"Scraping Error: {str(e)}")
            raise

        finally:
            if self.driver:
                try:
                    update_status("Closing Chrome WebDriver...")
                    self.driver.quit()
                except Exception as quit_err:
                    logger.debug(f"Error closing WebDriver: {quit_err}")
                self.driver = None

        return movies
