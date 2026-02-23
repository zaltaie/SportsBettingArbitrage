"""
Abstract base class for all betting site scrapers.
Provides shared HTTP utilities, rate limiting, and retry logic.
"""
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from arbitrage import OddsEntry
from config import DEFAULT_HEADERS, REQUEST_DELAY, MAX_RETRIES, REQUEST_TIMEOUT
from message import message


class BaseScraper(ABC):
    """Base class every site-specific scraper inherits from."""

    def __init__(
        self,
        name: str,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        delay: float = REQUEST_DELAY,
    ):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(headers or DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, url: str, params: Optional[dict] = None) -> Optional[requests.Response]:
        """GET a URL with retry logic and rate limiting."""
        time.sleep(self.delay)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                message.log_warning(
                    "Attempt {}/{} failed for {}: {}".format(attempt, MAX_RETRIES, url, exc),
                    self.name,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(self.delay * attempt)
        message.log_error("All retries exhausted for: {}".format(url), self.name)
        return None

    def get_soup(self, url: str, params: Optional[dict] = None) -> Optional[BeautifulSoup]:
        """Fetch a URL and return a BeautifulSoup object."""
        resp = self._get(url, params)
        if resp is None:
            return None
        return BeautifulSoup(resp.text, 'html.parser')

    def get_json(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Fetch a URL and return parsed JSON."""
        resp = self._get(url, params)
        if resp is None:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            message.log_error("JSON parse error for {}: {}".format(url, exc), self.name)
            return None

    # ------------------------------------------------------------------
    # Interface every scraper must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        """
        Fetch and return a list of OddsEntry objects for the given sports.
        If sports is None, use the default sport list from config.
        """
