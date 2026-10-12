# IMDb Top 250 Studio: Movie Rating Scraper & Analytics Dashboard

A reliable, full-stack Python automation and data analytics project that dynamically scrapes movie data from IMDb's official Top 250 Movies chart using Selenium Chrome WebDriver, cleans and validates records with Pandas, exports datasets to CSV, tracks rating trend history, generates high-DPI analytical visualizations with Matplotlib, and presents an interactive editorial cinema dashboard built with FastAPI.

---

## 📌 Problem Statement
IMDb's Top 250 list is updated dynamically based on ratings from millions of users worldwide. Manual recording or simple static HTML scrapers often fail due to dynamic client-side rendering, anti-bot protections, content loading delays, and schema changes. There is a need for an automated tool that robustly extracts, validates, exports, and analyzes movie rankings and rating trends over time.

---

## 🎯 Project Objectives & Core Features
1. **Automated Scraping**: Dynamically scrape movie rank, title, release year, IMDb rating, and poster image URLs from `https://www.imdb.com/chart/top/` using Selenium Chrome WebDriver.
2. **Resilient Extraction**: Selenium waits for IMDb's rendered page, reads chart entries from the DOM, and uses embedded JSON-LD data to enrich missing fields or as a fallback when available. IMDb changes or blocks can still prevent a scrape; failures are reported rather than presented as successful results.
3. **Data Validation & Cleaning**: Process raw extracted data with Pandas to remove duplicates, enforce numeric bounds, standardize nullable data types (`Int64`), and calculate data quality metrics.
4. **Structured CSV Export**: Store records in `data/imdb_top_250.csv` with `utf-8-sig` encoding, support filtered view exports, and update `data/historical_ratings.csv` for multi-session trend tracking.
5. **Data Analytics & High-DPI Visualizations**: Generate Matplotlib charts (Rating Distribution Histogram with Mean line, Movies by Decade, and Top 10 Benchmark comparison).
6. **Editorial Cinema Web Dashboard**: Built with FastAPI and a responsive Midnight Cinema & Gold interface, with poster cards, fallback slates for missing posters, a sortable data table, live search, interactive filter chips, analytics, and session history.
7. **Comprehensive Test Suite**: Automated unit and integration tests using `pytest` covering all processing, exporting, scraping schemas, and FastAPI endpoints.

---

## 🛠️ Technology Stack
- **Programming Language**: Python 3.11
- **Browser Automation**: Selenium WebDriver 4 & `webdriver-manager`
- **Data Manipulation**: Pandas & NumPy
- **Data Visualization**: Matplotlib (Agg headless engine)
- **Web Application & REST API**: FastAPI & Uvicorn
- **Frontend Dashboard**: HTML5, Modern CSS (Glassmorphic, Responsive Grid), Vanilla JavaScript (Fetch API), FontAwesome 6, Google Fonts (`Outfit`, `Inter`, `JetBrains Mono`)
- **Testing & Quality Assurance**: Pytest unit and integration tests
- **Logging**: Python `logging` module with console and file output

---

## 📁 Project Architecture

```
Mini project 2/
│
├── main.py              # Application entrypoint (CLI & Web UI)
├── scraper.py           # Selenium WebDriver scraper module with JSON-LD fallback
├── processor.py         # Pandas data cleaning, validation, quality metrics & analysis
├── exporter.py          # CSV export, historical trend logging & Matplotlib charts
├── config.py            # Central configuration, file paths, and browser settings
├── logger.py            # Stream & file logging setup
├── web_app.py           # FastAPI REST API server
├── requirements.txt     # Python project dependencies
├── README.md            # Comprehensive project documentation
├── .gitignore          # Git exclusion rules
│
├── templates/
│   └── index.html       # Editorial cinema dashboard frontend UI
│
├── data/
│   ├── imdb_top_250.csv       # Cleaned main dataset
│   └── historical_ratings.csv # Historical scrape session log
│
├── logs/
│   └── scraper.log            # Execution and error log file
│
├── output/
│   ├── rating_distribution.png # Rating distribution histogram with mean indicator
│   ├── movies_by_decade.png    # Movie count by decade bar chart
│   └── top_10_movies.png       # Top 10 highest-rated horizontal bar chart
│
└── tests/
    ├── __init__.py            # Test package marker
    ├── test_processor.py      # Tests for cleaning, validation, deduplication & stats
    ├── test_exporter.py       # Tests for CSV exports, Unicode & Matplotlib charts
    ├── test_api.py            # Tests for FastAPI endpoints & concurrency safety
    └── test_scraper.py        # Tests for scraper initialization & JSON-LD parsing
```

---

## Installation (Windows PowerShell)

Prerequisites: Python 3.11 and Google Chrome. Selenium Manager's `webdriver-manager` downloads a compatible ChromeDriver on first scrape, so internet access may be required.

Open PowerShell in the project folder, then run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation in the current terminal, allow it for that terminal only, then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run the Application

### Web dashboard (recommended)

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

The local FastAPI/Uvicorn server runs at `http://127.0.0.1:8000` and opens the dashboard in your default browser. Keep the terminal open while using the dashboard; press `Ctrl+C` there to stop the server. Use the dashboard's Headless Mode switch to choose whether Chrome is visible during scraping.

### Terminal scraper

Run Chrome headlessly (default):

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --cli --headless
```

Show Chrome while scraping to debug browser behavior:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --cli --visible
```

The `--headless` and `--visible` options are mutually exclusive. Both modes use the live IMDb chart; neither provides demo or fabricated records.

## Tests

Run the automated test suite from the project directory with the virtual environment activated:

```powershell
python -m pytest -v
```

The tests cover:
- Data extraction & normalization
- Missing, invalid, and out-of-range value handling
- Duplicate title and rank removal
- Rating and release-year parsing
- Search, filter chips (`top10`, `rating9`, `modern`, `classics`), and multi-field sorting
- Statistical calculations (mean, median, min, max, decade grouping)
- CSV export, Unicode preservation, and special character quoting
- Empty dataset handling without divide-by-zero errors
- FastAPI API endpoints (`/`, `/api/status`, `/api/data`, `/api/export/csv`)
- Scrape concurrency lock protection

## Troubleshooting

- **`ModuleNotFoundError` or import errors:** activate `.venv` and run `python -m pip install -r requirements.txt` again using that same terminal.
- **VS Code shows unresolved imports:** choose the project's `.venv\Scripts\python.exe` through **Python: Select Interpreter** so editor analysis uses the same environment as the application.
- **PowerShell will not activate `.venv`:** use the process-scoped execution-policy commands above, or run `.venv\Scripts\python.exe main.py` without activating.
- **Chrome/ChromeDriver startup error:** install or update Google Chrome and retry while connected to the internet so `webdriver-manager` can obtain a compatible driver. Use `python main.py --cli --visible` to see Chrome's behavior.
- **IMDb timeout, block, or empty extraction:** check network access, wait and retry later, and review `logs\scraper.log`. IMDb may limit automated traffic or change its page structure; the application reports failure and does not create a successful scrape from placeholder data.
- **Port 8000 is already in use:** stop the other local service or change `PORT` in `config.py`, then restart the dashboard.

---

## 📊 Dataset Schema

The generated `data/imdb_top_250.csv` file contains the following structured fields:

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `Rank` | Integer | Movie ranking on IMDb Top 250 (1 to 250) |
| `Title` | String | Official movie title |
| `Year` | Integer | Four-digit movie release year (e.g. 1994) |
| `Rating` | Float | IMDb user rating score (e.g. 9.3) |
| `Poster_Url` | String | Amazon CDN image URL for official movie poster |
| `Scraped_At` | String | ISO Timestamp when data was collected |

---

## 🌐 API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Serves the interactive cinema web dashboard |
| `/api/status` | `GET` | Real-time scraper state, current phase, and messages |
| `/api/scrape` | `POST` | Triggers a background scraping session (prevents concurrent duplicate jobs) |
| `/api/data` | `GET` | Returns movies catalog, statistics, chart paths, and session history |
| `/api/export/csv` | `GET` | Downloads dataset CSV. Supports `scope=all` or `scope=filtered` with query parameters |

---

## Notes & Limitations
- IMDb may rate-limit automated traffic or change the chart structure. A successful scrape depends on the target site and network being available.
- The scraper collects rank, title, year, rating, and poster URL when IMDb exposes those fields. Genres are not collected by this scraper and therefore are not displayed.
- The dashboard uses Google Fonts and Font Awesome from their public CDNs; without internet access the system font and text labels remain available, but remote typography and icons may not load.
