"""
Main entry point for IMDb Movie Rating Scraper & Tracker.
Supports both Interactive Cinema Web UI mode and Terminal CLI mode.

Usage:
  - Web UI Dashboard:  python main.py
  - CLI Mode:         python main.py --cli [--headless]
"""

import sys
import argparse
import webbrowser
import uvicorn
from datetime import datetime

from config import HOST, PORT, DEFAULT_HEADLESS
from scraper import IMDbScraper
from processor import DataProcessor
from exporter import DataExporter
from logger import get_logger

logger = get_logger("Main")


def run_cli(headless: bool = True):
    """Executes full scraping, processing, exporting, and analysis pipeline in CLI mode."""
    print("\n==================================================")
    print("      IMDb Movie Rating Scraper & Tracker        ")
    print("==================================================\n")

    logger.info("Starting CLI Scraping Session...")

    # 1. Scrape
    scraper = IMDbScraper(headless=headless)
    try:
        raw_records = scraper.scrape_top_250(
            status_callback=lambda msg: print(f"  [->] {msg}")
        )
    except Exception as exc:
        logger.error("CLI scraping failed: %s", exc, exc_info=True)
        print(f"\n[!] Scraping failed: {exc}")
        sys.exit(1)

    if not raw_records:
        print("\n[!] Scraping failed or zero records extracted.")
        sys.exit(1)

    # 2. Process
    print("\n  [->] Processing & validating extracted records...")
    processor = DataProcessor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = processor.process_records(raw_records, timestamp=timestamp)

    if df.empty:
        print("\n[!] Validation produced empty dataset.")
        sys.exit(1)

    # 3. Export
    print("  [->] Exporting dataset CSV and generating charts...")
    exporter = DataExporter()
    csv_file = exporter.save_to_csv(df)
    stats = processor.analyze_dataset(df)
    chart_paths = exporter.generate_charts(df, stats)

    # 4. Report Summary
    print("\n==================================================")
    print("               SCRAPING SUMMARY                   ")
    print("==================================================")
    print(f" Total Movies Extracted: {stats['total_movies']}")
    print(f" Average IMDb Rating:    {stats['average_rating']:.2f}")
    print(f" Highest Rating:         {stats['highest_rating']:.1f}  [{stats['highest_rated_movie']}]")
    print(f" Lowest Rating:          {stats['lowest_rating']:.1f}   [{stats['lowest_rated_movie']}]")
    print(f" Main CSV Dataset:       {csv_file}")
    if chart_paths:
        print(f" Charts Generated:       {len(chart_paths)} visual graphs saved in output/")
    print("==================================================")

    print("\nTop 5 Highest Rated Movies:")
    for m in df.head(5).to_dict(orient="records"):
        print(f"  #{m['Rank']:<3} {m['Title']:<40} ({m['Year']})  Rating: {m['Rating']}")

    print("\n[+] Scraping and analysis session completed successfully.\n")


def run_web_app():
    """Launches the Uvicorn web server and opens the local dashboard UI in browser."""
    url = f"http://{HOST}:{PORT}"
    print("\n==================================================")
    print("      IMDb Movie Rating Scraper & Tracker        ")
    print("==================================================")
    print(f" Launching Local Cinema Dashboard UI at: {url}")
    print(" Press Ctrl+C to terminate the web server.\n")

    # Automatically open default browser after a brief delay
    webbrowser.open(url)

    # Import app lazily to prevent duplicate imports
    from web_app import app
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


def main():
    parser = argparse.ArgumentParser(
        description="IMDb Movie Rating Scraper & Tracker - College Mini Project"
    )
    parser.add_argument(
        "--cli", action="store_true", help="Run scraping pipeline directly in CLI terminal mode."
    )
    browser_mode = parser.add_mutually_exclusive_group()
    browser_mode.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        help="Run Chrome WebDriver without a browser window (the default).",
    )
    browser_mode.add_argument(
        "--visible",
        dest="headless",
        action="store_false",
        help="Show the Chrome browser window while scraping (useful for debugging).",
    )
    parser.set_defaults(headless=DEFAULT_HEADLESS)

    args = parser.parse_args()

    if args.cli:
        run_cli(headless=args.headless)
    else:
        run_web_app()


if __name__ == "__main__":
    main()
