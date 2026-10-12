"""
Data Processing module for IMDb Movie Rating Scraper & Tracker.
Uses Pandas to clean, validate, structure, and analyze extracted movie records.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from logger import get_logger

logger = get_logger("Processor")


class DataProcessor:
    """Processes, cleans, validates, and analyzes movie datasets."""

    def __init__(self):
        self.last_quality_report: Dict[str, Any] = {}

    def process_records(
        self, raw_data: List[Dict[str, Any]], timestamp: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Converts raw scraped movie dictionaries into a validated Pandas DataFrame.

        Args:
            raw_data: List of raw scraped movie dicts.
            timestamp: ISO string timestamp of scraping run.

        Returns:
            Cleaned and validated Pandas DataFrame.
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        raw_count = len(raw_data) if raw_data else 0

        if not raw_data:
            logger.warning("Empty raw data passed to DataProcessor.")
            self.last_quality_report = {
                "raw_records_count": 0,
                "cleaned_records_count": 0,
                "duplicates_removed": 0,
                "missing_ratings": 0,
                "missing_years": 0,
                "missing_posters": 0
            }
            return pd.DataFrame(columns=["Rank", "Title", "Year", "Rating", "Poster_Url", "Scraped_At"])

        df = pd.DataFrame(raw_data)

        # Ensure essential columns exist
        for col in ["Rank", "Title", "Year", "Rating", "Poster_Url"]:
            if col not in df.columns:
                df[col] = np.nan

        # Data Cleaning & Type Formatting
        # 1. Clean Title
        df["Title"] = df["Title"].astype(str).str.strip()
        df = df[df["Title"] != ""].copy()

        # 2. Format Rank
        df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce")
        df = df.dropna(subset=["Rank"]).copy()
        df["Rank"] = df["Rank"].astype(int)

        # 3. Format Year
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        valid_year_mask = (df["Year"] >= 1900) & (df["Year"] <= 2035)
        df.loc[~valid_year_mask, "Year"] = np.nan
        df["Year"] = df["Year"].astype("Int64")

        # 4. Format Rating
        df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
        valid_rating_mask = (df["Rating"] >= 1.0) & (df["Rating"] <= 10.0)
        df.loc[~valid_rating_mask, "Rating"] = np.nan

        # 5. Clean Poster URL
        df["Poster_Url"] = df["Poster_Url"].fillna("").astype(str).str.strip()

        # Deduplicate records
        count_before_dedup = len(df)
        df = df.drop_duplicates(subset=["Rank"]).copy()
        df = df.drop_duplicates(subset=["Title"]).copy()
        duplicates_removed = (raw_count - len(df)) if raw_count >= len(df) else 0

        # Sort by Rank
        df = df.sort_values(by="Rank", ascending=True).reset_index(drop=True)

        # Add Scraping Timestamp
        df["Scraped_At"] = timestamp

        # Record Data Quality Metrics
        missing_ratings = int(df["Rating"].isna().sum())
        missing_years = int(df["Year"].isna().sum())
        missing_posters = int((df["Poster_Url"] == "").sum())

        self.last_quality_report = {
            "raw_records_count": raw_count,
            "cleaned_records_count": len(df),
            "duplicates_removed": duplicates_removed,
            "missing_ratings": missing_ratings,
            "missing_years": missing_years,
            "missing_posters": missing_posters
        }

        logger.info(
            f"Processed {raw_count} raw records -> {len(df)} valid records "
            f"({duplicates_removed} duplicates removed, {missing_ratings} missing ratings)."
        )
        return df

    def analyze_dataset(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates descriptive statistics and metadata analysis for the dataset.

        Args:
            df: Cleaned Pandas DataFrame.

        Returns:
            Dictionary containing analytical summary metrics.
        """
        if df.empty:
            return {
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
                "data_quality": self.last_quality_report or {
                    "raw_records_count": 0,
                    "cleaned_records_count": 0,
                    "duplicates_removed": 0,
                    "missing_ratings": 0,
                    "missing_years": 0,
                    "missing_posters": 0
                }
            }

        total_movies = len(df)
        valid_ratings = df["Rating"].dropna()
        avg_rating = round(float(valid_ratings.mean()), 2) if not valid_ratings.empty else 0.0
        median_rating = round(float(valid_ratings.median()), 2) if not valid_ratings.empty else 0.0
        max_rating = round(float(valid_ratings.max()), 1) if not valid_ratings.empty else 0.0
        min_rating = round(float(valid_ratings.min()), 1) if not valid_ratings.empty else 0.0

        highest_movie_str = "N/A"
        lowest_movie_str = "N/A"

        if not valid_ratings.empty:
            highest_subset = df.loc[df["Rating"] == valid_ratings.max()]
            if not highest_subset.empty:
                h_row = highest_subset.iloc[0]
                h_yr = h_row['Year'] if pd.notna(h_row['Year']) else 'N/A'
                highest_movie_str = f"{h_row['Title']} ({h_yr}) - {h_row['Rating']}"

            lowest_subset = df.loc[df["Rating"] == valid_ratings.min()]
            if not lowest_subset.empty:
                l_row = lowest_subset.iloc[-1]
                l_yr = l_row['Year'] if pd.notna(l_row['Year']) else 'N/A'
                lowest_movie_str = f"{l_row['Title']} ({l_yr}) - {l_row['Rating']}"

        # Top 10 Movies
        top_10_cols = [c for c in ["Rank", "Title", "Year", "Rating", "Poster_Url"] if c in df.columns]
        top_10 = df.head(10)[top_10_cols].to_dict(orient="records")
        for item in top_10:
            item["Year"] = int(item["Year"]) if pd.notna(item.get("Year")) else "N/A"

        # Movies by Decade Analysis
        movies_by_decade = {}
        df_valid_years = df.dropna(subset=["Year"]).copy()
        if not df_valid_years.empty:
            df_valid_years["Decade"] = (df_valid_years["Year"] // 10 * 10).astype(int).astype(str) + "s"
            decade_counts = df_valid_years["Decade"].value_counts().sort_index()
            movies_by_decade = decade_counts.to_dict()

        # Rating Distribution Analysis (inclusive bins spanning entire range)
        bins = [0.0, 8.0, 8.2, 8.4, 8.6, 8.8, 9.0, 10.0]
        labels = ["<8.0", "8.0-8.2", "8.3-8.4", "8.5-8.6", "8.7-8.8", "8.9-9.0", "9.1+"]
        rating_dist = {lbl: 0 for lbl in labels}
        
        if not valid_ratings.empty:
            df_valid_ratings = df.dropna(subset=["Rating"]).copy()
            df_valid_ratings["Rating_Group"] = pd.cut(
                df_valid_ratings["Rating"], bins=bins, labels=labels, include_lowest=True
            )
            dist_counts = df_valid_ratings["Rating_Group"].value_counts().sort_index()
            for k, v in dist_counts.to_dict().items():
                rating_dist[str(k)] = int(v)

        # Fallback quality metrics if not calculated in process_records
        quality_data = self.last_quality_report or {
            "raw_records_count": total_movies,
            "cleaned_records_count": total_movies,
            "duplicates_removed": 0,
            "missing_ratings": int(df["Rating"].isna().sum()),
            "missing_years": int(df["Year"].isna().sum()),
            "missing_posters": int((df["Poster_Url"] == "").sum()) if "Poster_Url" in df.columns else total_movies
        }

        return {
            "total_movies": total_movies,
            "average_rating": avg_rating,
            "median_rating": median_rating,
            "highest_rating": max_rating,
            "lowest_rating": min_rating,
            "highest_rated_movie": highest_movie_str,
            "lowest_rated_movie": lowest_movie_str,
            "top_10_movies": top_10,
            "movies_by_decade": movies_by_decade,
            "rating_distribution": rating_dist,
            "data_quality": quality_data
        }

    @staticmethod
    def filter_and_sort_df(
        df: pd.DataFrame,
        query: str = "",
        chip: str = "all",
        sort_by: str = "rank-asc"
    ) -> pd.DataFrame:
        """
        Pure deterministic filter & sort utility for datasets.
        """
        if df.empty:
            return df.copy()

        filtered = df.copy()

        # 1. Search Query (Title, Year, Rank)
        if query:
            q = query.strip().lower()
            title_match = filtered["Title"].str.lower().str.contains(q, na=False)
            year_match = filtered["Year"].astype(str).str.contains(q, na=False)
            rank_match = filtered["Rank"].astype(str) == q
            filtered = filtered[title_match | year_match | rank_match]

        # 2. Chip Filters
        if chip == "top10":
            filtered = filtered[filtered["Rank"] <= 10]
        elif chip == "rating9":
            filtered = filtered[filtered["Rating"] >= 9.0]
        elif chip == "modern":
            filtered = filtered[filtered["Year"] >= 2010]
        elif chip == "classics":
            filtered = filtered[filtered["Year"] < 1980]

        # 3. Sorting
        if sort_by == "rank-asc":
            filtered = filtered.sort_values(by="Rank", ascending=True)
        elif sort_by == "rank-desc":
            filtered = filtered.sort_values(by="Rank", ascending=False)
        elif sort_by == "rating-desc":
            filtered = filtered.sort_values(by="Rating", ascending=False)
        elif sort_by == "rating-asc":
            filtered = filtered.sort_values(by="Rating", ascending=True)
        elif sort_by == "year-desc":
            filtered = filtered.sort_values(by="Year", ascending=False)
        elif sort_by == "year-asc":
            filtered = filtered.sort_values(by="Year", ascending=True)
        elif sort_by == "title-asc":
            filtered = filtered.sort_values(by="Title", ascending=True)

        return filtered.reset_index(drop=True)
