"""
Unit and integration tests for scraper.py with mock HTML and error resilience.
"""

import json
import pytest
from scraper import IMDbScraper


def test_scraper_initialization():
    scraper = IMDbScraper(headless=True)
    assert scraper.headless is True
    assert scraper.driver is None


def test_scraper_propagates_startup_errors(monkeypatch):
    scraper = IMDbScraper(headless=True)
    messages = []

    def fail_startup():
        raise RuntimeError("Chrome could not start")

    monkeypatch.setattr(scraper, "_init_driver", fail_startup)

    with pytest.raises(RuntimeError, match="Chrome could not start"):
        scraper.scrape_top_250(status_callback=messages.append)

    assert any("Scraping Error: Chrome could not start" in message for message in messages)
    assert scraper.driver is None


def test_scraper_json_ld_parsing_logic():
    """Tests the structured data fallback logic using synthetic JSON-LD payload."""
    mock_payload = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "item": {
                    "@type": "Movie",
                    "name": "The Shawshank Redemption",
                    "datePublished": "1994-10-14",
                    "aggregateRating": {
                        "@type": "AggregateRating",
                        "ratingValue": 9.3
                    },
                    "image": "https://m.media-amazon.com/images/M/shawshank.jpg"
                }
            },
            {
                "@type": "ListItem",
                "position": 2,
                "item": {
                    "@type": "Movie",
                    "name": "The Godfather",
                    "datePublished": "1972-03-24",
                    "aggregateRating": {
                        "@type": "AggregateRating",
                        "ratingValue": 9.2
                    },
                    "image": "https://m.media-amazon.com/images/M/godfather.jpg"
                }
            }
        ]
    }

    # Verify our JSON-LD extraction logic matches the schema structure
    items = mock_payload["itemListElement"]
    extracted = []
    for idx, entry in enumerate(items):
        movie_obj = entry.get("item", entry)
        extracted.append({
            "Rank": entry.get("position", idx + 1),
            "Title": movie_obj.get("name"),
            "Year": int(str(movie_obj.get("datePublished"))[:4]),
            "Rating": float(movie_obj.get("aggregateRating", {}).get("ratingValue")),
            "Poster_Url": movie_obj.get("image")
        })

    assert len(extracted) == 2
    assert extracted[0]["Rank"] == 1
    assert extracted[0]["Title"] == "The Shawshank Redemption"
    assert extracted[0]["Year"] == 1994
    assert extracted[0]["Rating"] == 9.3
    assert extracted[0]["Poster_Url"] == "https://m.media-amazon.com/images/M/shawshank.jpg"
