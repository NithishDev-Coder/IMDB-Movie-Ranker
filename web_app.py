"""
Web Application API server for IMDb Movie Rating Scraper & Tracker.
Uses FastAPI to expose REST endpoints and serve the cinema dashboard UI.
"""

import os
import io
import threading
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pandas as pd

from config import CSV_PATH, HISTORICAL_CSV_PATH, OUTPUT_DIR, BASE_DIR
from scraper import IMDbScraper
from processor import DataProcessor
from exporter import DataExporter
from logger import get_logger

logger = get_logger("WebApp")

app = FastAPI(
    title="IMDb Movie Rating Scraper & Tracker API",
    description="Backend API supporting dynamic scraping, filtering, and analysis for IMDb Top 250 Movies.",
    version="2.0.0"
)

# Mount output directory for static chart image serving
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# Thread-Safe In-Memory Scraping Task State
scrape_state: Dict[str, Any] = {
    "status": "idle",       # "idle", "scraping", "completed", "failed"
    "phase": "idle",        # "init", "fetch", "parse", "process", "export", "idle"
    "message": "System ready",
    "record_count": 0,
    "last_scraped": None,
    "error_details": None
}
state_lock = threading.Lock()


class ScrapeRequest(BaseModel):
    headless: bool = True


def set_status(status: str, message: str, phase: str = "idle", count: int = 0, error: Optional[str] = None):
    """Thread-safe state update helper."""
    with state_lock:
        scrape_state["status"] = status
        scrape_state["message"] = message
        scrape_state["phase"] = phase
        scrape_state["record_count"] = count
        scrape_state["error_details"] = error
        if status == "completed":
            scrape_state["last_scraped"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_scraping_job(headless: bool):
    """Background worker function executing the scraping pipeline."""
    set_status("scraping", "Starting Chrome WebDriver...", phase="init")

    def status_callback(msg: str):
        with state_lock:
            scrape_state["message"] = msg
            if "Navigating" in msg or "Waiting" in msg:
                scrape_state["phase"] = "fetch"
            elif "parsing" in msg or "DOM" in msg or "JSON-LD" in msg:
                scrape_state["phase"] = "parse"
            elif "Processing" in msg or "Validating" in msg:
                scrape_state["phase"] = "process"

    try:
        scraper = IMDbScraper(headless=headless)
        raw_movies = scraper.scrape_top_250(status_callback=status_callback)

        if not raw_movies:
            set_status("failed", "Failed to extract movie records from IMDb page. Check network or anti-bot blocks.", error="Empty record set extracted")
            return

        set_status("scraping", f"Validating & cleaning {len(raw_movies)} extracted records with Pandas...", phase="process", count=len(raw_movies))
        processor = DataProcessor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cleaned_df = processor.process_records(raw_movies, timestamp=timestamp)

        if cleaned_df.empty:
            set_status("failed", "Validation yielded zero valid records.", error="Data cleaning dropped all rows")
            return

        set_status("scraping", "Saving dataset and generating analytical charts...", phase="export", count=len(cleaned_df))
        exporter = DataExporter()
        exporter.save_to_csv(cleaned_df)
        stats = processor.analyze_dataset(cleaned_df)
        exporter.generate_charts(cleaned_df, stats)

        set_status(
            "completed",
            f"Scraping completed successfully! {len(cleaned_df)} movies validated and saved.",
            phase="idle",
            count=len(cleaned_df)
        )

    except Exception as e:
        logger.error(f"Scraping background task error: {e}", exc_info=True)
        set_status("failed", f"Scraping failed: {str(e)}", error=str(e))


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the main cinema dashboard HTML UI."""
    template_path = os.path.join(BASE_DIR, "templates", "index.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Dashboard Template Not Found</h1>", status_code=404)


@app.post("/api/scrape")
def trigger_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    """Triggers scraping session in background thread, preventing concurrent duplicate jobs."""
    with state_lock:
        if scrape_state["status"] == "scraping":
            return {"status": "error", "message": "Scraping task is already in progress."}
        scrape_state["status"] = "scraping"
        scrape_state["message"] = "Initiating scrape request..."
        scrape_state["phase"] = "init"
        scrape_state["error_details"] = None

    background_tasks.add_task(run_scraping_job, req.headless)
    return {"status": "started", "message": "Scraping task initiated in background."}


@app.get("/api/status")
def get_status():
    """Returns real-time scraping progress and state."""
    with state_lock:
        return dict(scrape_state)


@app.get("/api/data")
def get_data():
    """Returns processed movie dataset, stats, chart paths, and historical log."""
    processor = DataProcessor()
    movies_list = []
    stats = {
        "total_movies": 0,
        "average_rating": 0.0,
        "median_rating": 0.0,
        "highest_rating": 0.0,
        "lowest_rating": 0.0,
        "highest_rated_movie": "N/A",
        "lowest_rated_movie": "N/A",
        "top_10_movies": [],
        "movies_by_decade": {},
        "rating_distribution": {},
        "data_quality": {
            "raw_records_count": 0,
            "cleaned_records_count": 0,
            "duplicates_removed": 0,
            "missing_ratings": 0,
            "missing_years": 0,
            "missing_posters": 0
        }
    }
    last_scraped = None

    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            if not df.empty:
                # Ensure Poster_Url column exists for backward compatibility
                if "Poster_Url" not in df.columns:
                    df["Poster_Url"] = ""
                else:
                    df["Poster_Url"] = df["Poster_Url"].fillna("")

                # Clean NaN representations for JSON serialization
                df_clean = df.copy()
                df_clean["Year"] = df_clean["Year"].fillna("").astype(str).replace("<NA>", "")
                df_clean["Rating"] = df_clean["Rating"].fillna(0.0)

                movies_list = df_clean.to_dict(orient="records")
                # Format Year back to int or None in dictionary for frontend
                for m in movies_list:
                    if m.get("Year") and str(m["Year"]).isdigit():
                        m["Year"] = int(m["Year"])
                    else:
                        m["Year"] = None

                stats = processor.analyze_dataset(df)
                if "Scraped_At" in df.columns and pd.notna(df["Scraped_At"].iloc[0]):
                    last_scraped = str(df["Scraped_At"].iloc[0])
        except Exception as e:
            logger.error(f"Error reading CSV dataset: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Unable to read the saved movie dataset. Check data/imdb_top_250.csv and logs/scraper.log.",
            ) from e

    # Chart paths check
    charts = {
        "rating_distribution": "/output/rating_distribution.png" if os.path.exists(os.path.join(OUTPUT_DIR, "rating_distribution.png")) else None,
        "movies_by_decade": "/output/movies_by_decade.png" if os.path.exists(os.path.join(OUTPUT_DIR, "movies_by_decade.png")) else None,
        "top_10_movies": "/output/top_10_movies.png" if os.path.exists(os.path.join(OUTPUT_DIR, "top_10_movies.png")) else None
    }

    # Historical Sessions Parsing
    history = []
    if os.path.exists(HISTORICAL_CSV_PATH):
        try:
            h_df = pd.read_csv(HISTORICAL_CSV_PATH)
            if "Scraped_At" in h_df.columns:
                grouped = h_df.groupby("Scraped_At")
                for timestamp, group in grouped:
                    top_row = group.sort_values(by="Rank").iloc[0] if not group.empty else None
                    top_m_str = f"#{top_row['Rank']} {top_row['Title']}" if top_row is not None else "N/A"
                    avg_r = float(group["Rating"].mean()) if "Rating" in group.columns else 0.0
                    history.append({
                        "timestamp": str(timestamp),
                        "total_records": len(group),
                        "avg_rating": round(avg_r, 2),
                        "top_movie": top_m_str
                    })
                history.sort(key=lambda x: x["timestamp"], reverse=True)
        except Exception as e:
            logger.error(f"Error parsing historical CSV: {e}")

    return {
        "movies": movies_list,
        "stats": stats,
        "charts": charts,
        "last_scraped": last_scraped,
        "history": history
    }


@app.get("/api/export/csv")
def export_csv(
    scope: str = Query("all", description="Export scope: 'all' or 'filtered'"),
    query: Optional[str] = Query(None, description="Search term filter"),
    chip: Optional[str] = Query("all", description="Filter chip: all, top10, rating9, modern, classics"),
    sort_by: Optional[str] = Query("rank-asc", description="Sort order key")
):
    """
    Serves the dataset CSV file for download.
    Can export the full dataset or filtered view based on user selection.
    """
    if not os.path.exists(CSV_PATH):
        return Response(
            content="CSV file has not been generated yet. Please run a scrape session first.",
            media_type="text/plain",
            status_code=404
        )

    try:
        df = pd.read_csv(CSV_PATH)
        if df.empty:
            return FileResponse(path=CSV_PATH, filename="imdb_top_250_empty.csv", media_type="text/csv")

        if scope == "filtered":
            filtered_df = DataProcessor.filter_and_sort_df(
                df, query=query or "", chip=chip or "all", sort_by=sort_by or "rank-asc"
            )
            csv_buffer = io.StringIO()
            cols = ["Rank", "Title", "Year", "Rating", "Poster_Url", "Scraped_At"]
            export_cols = [c for c in cols if c in filtered_df.columns]
            filtered_df[export_cols].to_csv(csv_buffer, index=False, encoding="utf-8-sig")

            csv_bytes = csv_buffer.getvalue().encode("utf-8-sig")
            filename = f"imdb_top_250_filtered_{len(filtered_df)}_records.csv"
            return Response(
                content=csv_bytes,
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )

        # Full export
        return FileResponse(
            path=CSV_PATH,
            filename="imdb_top_250_full.csv",
            media_type="text/csv"
        )
    except Exception as e:
        logger.error(f"Error serving CSV export: {e}")
        return Response(content=f"Error exporting CSV: {str(e)}", media_type="text/plain", status_code=500)
