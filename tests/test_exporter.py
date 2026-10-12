"""
Unit tests for exporter.py covering CSV file exports, special characters handling,
historical tracking updates, and Matplotlib chart generation.
"""

import os
import tempfile
import pytest
import pandas as pd
from exporter import DataExporter
from processor import DataProcessor


@pytest.fixture
def exporter():
    return DataExporter()


@pytest.fixture
def sample_df():
    return pd.DataFrame([
        {
            "Rank": 1,
            "Title": "Dr. Strangelove or: How I Learned to Stop Worrying and Love the Bomb, The",
            "Year": 1964,
            "Rating": 8.4,
            "Poster_Url": "https://example.com/poster1.jpg",
            "Scraped_At": "2026-10-09 10:00:00"
        },
        {
            "Rank": 2,
            "Title": "Lock, Stock and Two Smoking Barrels",
            "Year": 1998,
            "Rating": 8.2,
            "Poster_Url": "",
            "Scraped_At": "2026-10-09 10:00:00"
        },
        {
            "Rank": 3,
            "Title": "Spirited Away (千と千尋の神隠し)",
            "Year": 2001,
            "Rating": 8.6,
            "Poster_Url": "",
            "Scraped_At": "2026-10-09 10:00:00"
        }
    ])


def test_save_to_csv_headers_and_special_chars(exporter, sample_df):
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        saved_path = exporter.save_to_csv(sample_df, filepath=tmp_path)
        assert os.path.exists(saved_path)

        read_df = pd.read_csv(saved_path)
        assert len(read_df) == 3
        # Check column headers
        assert list(read_df.columns[:5]) == ["Rank", "Title", "Year", "Rating", "Poster_Url"]
        # Verify commas and quotes were correctly preserved
        assert "Lock, Stock and Two Smoking Barrels" in list(read_df["Title"])
        # Verify unicode characters preserved
        assert any("千と千尋" in str(t) for t in read_df["Title"])
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_save_to_csv_empty_dataframe(exporter):
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        exporter.save_to_csv(pd.DataFrame(), filepath=tmp_path)
        assert os.path.exists(tmp_path)
        read_df = pd.read_csv(tmp_path)
        assert read_df.empty
        assert "Rank" in read_df.columns
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_generate_charts(exporter, sample_df, tmp_path, monkeypatch):
    monkeypatch.setattr("exporter.OUTPUT_DIR", str(tmp_path))
    processor = DataProcessor()
    stats = processor.analyze_dataset(sample_df)
    chart_paths = exporter.generate_charts(sample_df, stats)

    assert isinstance(chart_paths, dict)
    for key, path in chart_paths.items():
        assert os.path.exists(path)
        assert os.path.getsize(path) > 1000  # Image file is non-empty


def test_generate_charts_empty(exporter):
    chart_paths = exporter.generate_charts(pd.DataFrame(), {})
    assert chart_paths == {}
