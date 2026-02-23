"""
Legacy compatibility shim.
The OddsChecker scraper has been moved to scrapers/oddschecker.py.
This file re-exports the new class so any code referencing the old
module path continues to work.
"""
from scrapers.oddschecker import OddsCheckerScraper as CWebsite  # noqa: F401

__all__ = ['CWebsite']
