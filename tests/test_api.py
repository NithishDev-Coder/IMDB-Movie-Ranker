"""
Integration tests for FastAPI web endpoints in web_app.py using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from web_app import app, scrape_state


@pytest.fixture
def client():
    return TestClient(app)


def test_get_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "IMDb Top 250 Studio" in response.text


def test_get_status_endpoint(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "phase" in data
    assert "message" in data


def test_get_data_endpoint(client):
    response = client.get("/api/data")
    assert response.status_code == 200
    data = response.json()
    assert "movies" in data
    assert "stats" in data
    assert "charts" in data
    assert "history" in data
    assert isinstance(data["movies"], list)


def test_get_data_reports_dataset_read_errors(client, monkeypatch):
    def fail_read(*args, **kwargs):
        raise OSError("dataset is unavailable")

    monkeypatch.setattr("web_app.pd.read_csv", fail_read)

    response = client.get("/api/data")

    assert response.status_code == 500
    assert "Unable to read the saved movie dataset" in response.json()["detail"]


def test_export_csv_all(client):
    response = client.get("/api/export/csv?scope=all")
    # Should either return 200 (if file exists) or 404 with clear message
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert "text/csv" in response.headers["content-type"]
        assert len(response.text) > 0
        assert response.headers["content-disposition"] == 'attachment; filename="imdb_top_250_full.csv"'
        assert response.content.startswith(b"\xef\xbb\xbfRank,Title,Year,Rating")
        assert len(response.text.splitlines()) == 251


def test_export_csv_filtered(client):
    response = client.get("/api/export/csv?scope=filtered&chip=top10")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert "text/csv" in response.headers["content-type"]
        assert 'filename="imdb_top_250_filtered_10_records.csv"' in response.headers["content-disposition"]
        assert response.content.startswith(b"\xef\xbb\xbfRank,Title,Year,Rating")
        assert len(response.text.splitlines()) == 11


def test_scrape_concurrency_protection(client):
    # Set status to scraping manually to test collision prevention
    from web_app import state_lock
    with state_lock:
        original_status = scrape_state["status"]
        scrape_state["status"] = "scraping"

    try:
        response = client.post("/api/scrape", json={"headless": True})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "already in progress" in data["message"]
    finally:
        with state_lock:
            scrape_state["status"] = original_status


def test_scrape_job_surfaces_scraper_errors(client, monkeypatch):
    from web_app import run_scraping_job, set_status

    class FailingScraper:
        def __init__(self, headless):
            self.headless = headless

        def scrape_top_250(self, status_callback=None):
            raise RuntimeError("IMDb blocked the request")

    monkeypatch.setattr("web_app.IMDbScraper", FailingScraper)

    try:
        run_scraping_job(headless=True)
        response = client.get("/api/status")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert "IMDb blocked the request" in response.json()["message"]
        assert response.json()["error_details"] == "IMDb blocked the request"
    finally:
        set_status("idle", "System ready", phase="idle")
