"""
Configuration file for IMDb Movie Rating Scraper & Tracker.
Contains application paths, scraping URLs, WebDriver settings, and default parameters.
"""

import os

# Base Directory of the Project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data & Output Directories
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Ensure required directories exist
for directory in [DATA_DIR, LOG_DIR, OUTPUT_DIR]:
    os.makedirs(directory, exist_ok=True)

# File Paths
CSV_PATH = os.path.join(DATA_DIR, "imdb_top_250.csv")
HISTORICAL_CSV_PATH = os.path.join(DATA_DIR, "historical_ratings.csv")
LOG_PATH = os.path.join(LOG_DIR, "scraper.log")

# Scraping Configuration
IMDB_TOP_250_URL = "https://www.imdb.com/chart/top/"
DEFAULT_HEADLESS = True
EXPLICIT_WAIT_TIMEOUT = 15  # seconds
PAGE_LOAD_TIMEOUT = 30       # seconds

# Chrome Browser User-Agent and Anti-Bot Headers
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Web Server Settings for Demo Interface
HOST = "127.0.0.1"
PORT = 8000
