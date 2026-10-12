"""
Exporter module for IMDb Movie Rating Scraper & Tracker.
Exports dataset to CSV files and generates visual analysis charts using Matplotlib.
"""

import os
from typing import Dict, Any, Optional
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless chart generation
import matplotlib.pyplot as plt

from config import CSV_PATH, HISTORICAL_CSV_PATH, OUTPUT_DIR
from logger import get_logger

logger = get_logger("Exporter")


class DataExporter:
    """Handles CSV exports, historical trend tracking, and visualization chart generation."""

    def __init__(self):
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def save_to_csv(self, df: pd.DataFrame, filepath: Optional[str] = None) -> str:
        """
        Saves DataFrame to CSV with proper headers and utf-8-sig encoding.

        Args:
            df: Cleaned Pandas DataFrame.
            filepath: Target file path (defaults to config.CSV_PATH).

        Returns:
            Path to saved CSV file.
        """
        target_path = filepath or CSV_PATH
        if df.empty:
            logger.warning("Attempted to save empty DataFrame to CSV.")
            # Still write header structure
            empty_df = pd.DataFrame(columns=["Rank", "Title", "Year", "Rating", "Poster_Url", "Scraped_At"])
            empty_df.to_csv(target_path, index=False, encoding="utf-8-sig")
            return target_path

        # Order columns cleanly
        cols = ["Rank", "Title", "Year", "Rating", "Poster_Url", "Scraped_At"]
        available_cols = [c for c in cols if c in df.columns]
        # Include any remaining unexpected columns at the end
        extra_cols = [c for c in df.columns if c not in cols]
        export_df = df[available_cols + extra_cols]

        export_df.to_csv(target_path, index=False, encoding="utf-8-sig")
        logger.info(f"Dataset successfully saved to {target_path} ({len(export_df)} records)")

        # Update Historical Ratings CSV only when writing main dataset
        if target_path == CSV_PATH:
            self._update_historical_csv(export_df)

        return target_path

    def _update_historical_csv(self, df: pd.DataFrame):
        """Appends current scrape dataset to data/historical_ratings.csv for historical tracking."""
        try:
            if os.path.exists(HISTORICAL_CSV_PATH):
                hist_df = pd.read_csv(HISTORICAL_CSV_PATH)
                combined = pd.concat([hist_df, df], ignore_index=True)
                # Deduplicate exact same Rank + Title + Scraped_At entries
                combined = combined.drop_duplicates(subset=["Rank", "Title", "Scraped_At"])
                combined.to_csv(HISTORICAL_CSV_PATH, index=False, encoding="utf-8-sig")
            else:
                df.to_csv(HISTORICAL_CSV_PATH, index=False, encoding="utf-8-sig")
            logger.info(f"Historical ratings dataset updated at {HISTORICAL_CSV_PATH}")
        except Exception as e:
            logger.error(f"Failed to update historical CSV: {e}")

    def generate_charts(self, df: pd.DataFrame, stats: Dict[str, Any]) -> Dict[str, str]:
        """
        Generates clean cinema-themed matplotlib visualization charts.

        Args:
            df: Cleaned Pandas DataFrame.
            stats: Analytical summary dictionary from DataProcessor.

        Returns:
            Dictionary mapping chart keys to saved image file paths.
        """
        chart_paths = {}

        if df.empty:
            return chart_paths

        # Shiny Black & Luxury Gold Studio Palette
        bg_color = "#06070a"
        card_bg = "#0f1118"
        gold_primary = "#FFD700"
        gold_accent = "#FFE082"
        highlight_color = "#FFA000"
        mean_accent = "#FFF8E1"
        text_primary = "#FDFCF7"
        text_secondary = "#B3AFA3"
        grid_color = "#24221A"

        plt.rcParams.update({
            "figure.facecolor": bg_color,
            "axes.facecolor": card_bg,
            "axes.edgecolor": grid_color,
            "axes.labelcolor": text_secondary,
            "xtick.color": text_secondary,
            "ytick.color": text_secondary,
            "text.color": text_primary,
            "font.family": "sans-serif",
            "figure.autolayout": True
        })

        # Chart 1: IMDb Rating Distribution
        try:
            fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
            ratings = df["Rating"].dropna()
            
            if not ratings.empty:
                n, bins, patches = ax.hist(
                    ratings, bins=10, color=gold_primary, edgecolor="#3A3010", linewidth=1.2, alpha=0.95
                )
                
                # Highlight peak bin with shining amber gold
                max_bin = max(n) if len(n) > 0 else 0
                for patch in patches:
                    if patch.get_height() == max_bin:
                        patch.set_facecolor(highlight_color)

                # Mean line
                mean_val = ratings.mean()
                ax.axvline(
                    mean_val, color=mean_accent, linestyle="--", linewidth=1.8,
                    label=f"Mean: {mean_val:.2f}"
                )
                ax.legend(loc="upper right", facecolor=card_bg, edgecolor=grid_color, fontsize=9)

            ax.set_title("IMDb Rating Distribution (Top 250)", fontsize=13, pad=12, fontweight="bold", color=gold_primary)
            ax.set_xlabel("IMDb Score", fontsize=10, labelpad=8)
            ax.set_ylabel("Movie Count", fontsize=10, labelpad=8)
            ax.grid(axis="y", color=grid_color, linestyle="--", alpha=0.6)

            path_dist = os.path.join(OUTPUT_DIR, "rating_distribution.png")
            plt.savefig(path_dist, facecolor=bg_color, bbox_inches="tight")
            plt.close(fig)
            chart_paths["rating_distribution"] = path_dist
        except Exception as e:
            logger.error(f"Error generating rating distribution chart: {e}")

        # Chart 2: Movies by Decade
        try:
            movies_by_decade = stats.get("movies_by_decade", {})
            if movies_by_decade:
                fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=120)
                decades = list(movies_by_decade.keys())
                counts = list(movies_by_decade.values())

                bars = ax.bar(decades, counts, color=gold_primary, edgecolor="#3A3010", width=0.65, alpha=0.95)
                
                max_count = max(counts) if counts else 0
                for bar, count in zip(bars, counts):
                    if count == max_count:
                        bar.set_facecolor(highlight_color)
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.6,
                        str(count),
                        ha="center",
                        va="bottom",
                        fontsize=8.5,
                        color=text_primary,
                        fontweight="bold"
                    )

                ax.set_title("IMDb Top 250 Movies by Decade", fontsize=13, pad=12, fontweight="bold", color=gold_primary)
                ax.set_xlabel("Decade", fontsize=10, labelpad=8)
                ax.set_ylabel("Movie Count", fontsize=10, labelpad=8)
                ax.grid(axis="y", color=grid_color, linestyle="--", alpha=0.6)

                path_decade = os.path.join(OUTPUT_DIR, "movies_by_decade.png")
                plt.savefig(path_decade, facecolor=bg_color, bbox_inches="tight")
                plt.close(fig)
                chart_paths["movies_by_decade"] = path_decade
        except Exception as e:
            logger.error(f"Error generating movies by decade chart: {e}")

        # Chart 3: Top 10 Highest Rated Movies
        try:
            top_10 = stats.get("top_10_movies", [])
            if top_10:
                fig, ax = plt.subplots(figsize=(9.5, 5), dpi=120)
                chart_titles = []
                for m in reversed(top_10):
                    raw_t = m['Title']
                    # Clean title string for standard sans-serif font rendering
                    ascii_t = raw_t.encode('ascii', 'replace').decode('ascii').replace('?', '')
                    display_t = ascii_t.strip() if ascii_t.strip() else raw_t
                    chart_titles.append(f"#{m['Rank']} {display_t[:25]}")
                titles = chart_titles
                ratings_10 = [m["Rating"] for m in reversed(top_10)]

                bars = ax.barh(titles, ratings_10, color=gold_primary, height=0.62, alpha=0.95, edgecolor="#3A3010")
                bars[-1].set_facecolor(highlight_color)  # Highlight #1 movie

                for bar, rate in zip(bars, ratings_10):
                    ax.text(
                        rate - 0.25,
                        bar.get_y() + bar.get_height() / 2,
                        f"{rate:.1f}",
                        ha="center",
                        va="center",
                        fontsize=9,
                        color="#050608",
                        fontweight="bold"
                    )

                min_x = max(7.5, min(ratings_10) - 0.5)
                ax.set_xlim(min_x, 10.0)
                ax.set_title("Top 10 Highest Rated IMDb Movies", fontsize=13, pad=12, fontweight="bold", color=gold_primary)
                ax.set_xlabel("IMDb Rating", fontsize=10, labelpad=8)
                ax.grid(axis="x", color=grid_color, linestyle="--", alpha=0.6)

                path_top10 = os.path.join(OUTPUT_DIR, "top_10_movies.png")
                plt.savefig(path_top10, facecolor=bg_color, bbox_inches="tight")
                plt.close(fig)
                chart_paths["top_10_movies"] = path_top10
        except Exception as e:
            logger.error(f"Error generating top 10 movies chart: {e}")

        logger.info(f"Visual analysis charts generated in {OUTPUT_DIR}")
        return chart_paths
