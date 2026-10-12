"""
Unit tests for processor.py covering data cleaning, normalization,
deduplication, statistical calculations, filtering, and sorting.
"""

import pytest
import pandas as pd
import numpy as np
from processor import DataProcessor


@pytest.fixture
def processor():
    return DataProcessor()


@pytest.fixture
def sample_raw_records():
    return [
        {
            "Rank": 1,
            "Title": "The Shawshank Redemption",
            "Year": 1994,
            "Rating": 9.3,
            "Poster_Url": "https://m.media-amazon.com/images/M/sample1.jpg"
        },
        {
            "Rank": 2,
            "Title": "The Godfather",
            "Year": 1972,
            "Rating": 9.2,
            "Poster_Url": "https://m.media-amazon.com/images/M/sample2.jpg"
        },
        {
            "Rank": 3,
            "Title": "The Dark Knight",
            "Year": 2008,
            "Rating": 9.0,
            "Poster_Url": "https://m.media-amazon.com/images/M/sample3.jpg"
        },
        {
            "Rank": 4,
            "Title": "Inception",
            "Year": 2010,
            "Rating": 8.8,
            "Poster_Url": ""
        },
        {
            "Rank": 5,
            "Title": "Parasite",
            "Year": 2019,
            "Rating": 8.5,
            "Poster_Url": ""
        }
    ]


def test_process_records_valid(processor, sample_raw_records):
    df = processor.process_records(sample_raw_records, timestamp="2026-10-09 12:00:00")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert list(df["Rank"]) == [1, 2, 3, 4, 5]
    assert df["Scraped_At"].iloc[0] == "2026-10-09 12:00:00"
    assert "Poster_Url" in df.columns
    assert processor.last_quality_report["cleaned_records_count"] == 5
    assert processor.last_quality_report["duplicates_removed"] == 0


def test_process_records_missing_and_invalid(processor):
    dirty_records = [
        {"Rank": "1", "Title": "  Dirty Movie 1  ", "Year": "1999", "Rating": "8.5"},
        {"Rank": "invalid", "Title": "No Rank", "Year": 2000, "Rating": 8.1},  # Dropped (invalid rank)
        {"Rank": 3, "Title": "", "Year": 2001, "Rating": 8.2},                  # Dropped (empty title)
        {"Rank": 4, "Title": "Valid Movie", "Year": "1800", "Rating": 8.0},    # Year out of range -> NaN
        {"Rank": 5, "Title": "High Rating", "Year": 2020, "Rating": 12.0},     # Rating out of range -> NaN
    ]
    df = processor.process_records(dirty_records)
    assert len(df) == 3
    assert df.loc[df["Rank"] == 1, "Title"].iloc[0] == "Dirty Movie 1"
    assert pd.isna(df.loc[df["Rank"] == 4, "Year"].iloc[0])
    assert pd.isna(df.loc[df["Rank"] == 5, "Rating"].iloc[0])


def test_process_records_deduplication(processor):
    records_with_duplicates = [
        {"Rank": 1, "Title": "The Matrix", "Year": 1999, "Rating": 8.7},
        {"Rank": 1, "Title": "The Matrix Duplicate Rank", "Year": 1999, "Rating": 8.7},
        {"Rank": 2, "Title": "The Matrix", "Year": 1999, "Rating": 8.7}, # Duplicate title
        {"Rank": 3, "Title": "Interstellar", "Year": 2014, "Rating": 8.7},
    ]
    df = processor.process_records(records_with_duplicates)
    assert len(df) == 2
    assert set(df["Title"]) == {"The Matrix", "Interstellar"}
    assert processor.last_quality_report["duplicates_removed"] == 2


def test_process_records_empty(processor):
    df = processor.process_records([])
    assert df.empty
    assert list(df.columns) == ["Rank", "Title", "Year", "Rating", "Poster_Url", "Scraped_At"]
    stats = processor.analyze_dataset(df)
    assert stats["total_movies"] == 0
    assert stats["average_rating"] == 0.0


def test_analyze_dataset_metrics(processor, sample_raw_records):
    df = processor.process_records(sample_raw_records)
    stats = processor.analyze_dataset(df)

    assert stats["total_movies"] == 5
    # (9.3 + 9.2 + 9.0 + 8.8 + 8.5) / 5 = 44.8 / 5 = 8.96
    assert stats["average_rating"] == 8.96
    assert stats["highest_rating"] == 9.3
    assert stats["lowest_rating"] == 8.5
    assert "The Shawshank Redemption" in stats["highest_rated_movie"]
    assert "Parasite" in stats["lowest_rated_movie"]
    assert len(stats["top_10_movies"]) == 5

    # Check decade distribution
    decades = stats["movies_by_decade"]
    assert decades.get("1970s") == 1
    assert decades.get("1990s") == 1
    assert decades.get("2000s") == 1
    assert decades.get("2010s") == 2


def test_filter_and_sort_df_search(processor, sample_raw_records):
    df = processor.process_records(sample_raw_records)

    # Search by title
    filtered = DataProcessor.filter_and_sort_df(df, query="godfather")
    assert len(filtered) == 1
    assert filtered["Title"].iloc[0] == "The Godfather"

    # Search by year
    filtered_year = DataProcessor.filter_and_sort_df(df, query="1994")
    assert len(filtered_year) == 1
    assert filtered_year["Title"].iloc[0] == "The Shawshank Redemption"

    # Search by rank
    filtered_rank = DataProcessor.filter_and_sort_df(df, query="3")
    assert len(filtered_rank) == 1
    assert filtered_rank["Title"].iloc[0] == "The Dark Knight"


def test_filter_and_sort_df_chips(processor, sample_raw_records):
    df = processor.process_records(sample_raw_records)

    # 9.0+ Masterpieces
    rating9 = DataProcessor.filter_and_sort_df(df, chip="rating9")
    assert len(rating9) == 3  # 9.3, 9.2, 9.0
    assert all(r >= 9.0 for r in rating9["Rating"])

    # Modern 2010+
    modern = DataProcessor.filter_and_sort_df(df, chip="modern")
    assert len(modern) == 2  # Inception (2010), Parasite (2019)
    assert all(y >= 2010 for y in modern["Year"])

    # Classics < 1980
    classics = DataProcessor.filter_and_sort_df(df, chip="classics")
    assert len(classics) == 1  # The Godfather (1972)
    assert classics["Title"].iloc[0] == "The Godfather"


def test_filter_and_sort_df_sorting(processor, sample_raw_records):
    df = processor.process_records(sample_raw_records)

    # Sort rating descending
    sorted_rating = DataProcessor.filter_and_sort_df(df, sort_by="rating-desc")
    assert list(sorted_rating["Rating"]) == [9.3, 9.2, 9.0, 8.8, 8.5]

    # Sort year ascending
    sorted_year = DataProcessor.filter_and_sort_df(df, sort_by="year-asc")
    assert list(sorted_year["Year"]) == [1972, 1994, 2008, 2010, 2019]

    # Sort title A-Z
    sorted_title = DataProcessor.filter_and_sort_df(df, sort_by="title-asc")
    assert sorted_title["Title"].iloc[0] == "Inception"
