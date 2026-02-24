"""
Abstract base class for all betting site scrapers.
Provides shared HTTP utilities, rate limiting, and retry logic.
"""
import ssl
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

from arbitrage import OddsEntry
from config import DEFAULT_HEADERS, REQUEST_DELAY, MAX_RETRIES, REQUEST_TIMEOUT
from message import message

# Optional cloudscraper — bypasses Cloudflare JS challenges on 403 sites
try:
    import cloudscraper as _cloudscraper_mod
    _CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    _CLOUDSCRAPER_AVAILABLE = False


class _TLSAdapter(HTTPAdapter):
    """
    HTTPAdapter that uses a relaxed TLS context.

    Fixes sites (e.g. FanDuel's sbapi.fanduel.com) that reject the default
    Python TLS handshake with SSLV3_ALERT_HANDSHAKE_FAILURE because they
    require specific cipher suites or enforce TLS 1.2+.

    SECLEVEL=1 enables a wider set of ciphers while still enforcing TLS 1.2+.
    """

    def init_poolmanager(self, *args, **kwargs):
        try:
            ctx = ssl.create_default_context()
            ctx.set_ciphers('DEFAULT@SECLEVEL=1')
            kwargs['ssl_context'] = ctx
        except Exception:
            pass  # Fall back to default if ctx setup fails on older Python
        super().init_poolmanager(*args, **kwargs)


class BaseScraper(ABC):
    """Base class every site-specific scraper inherits from."""

    def __init__(
        self,
        name: str,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        delay: float = REQUEST_DELAY,
        use_cloudscraper: bool = False,
    ):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.delay = delay

        # Prefer cloudscraper for Cloudflare-protected sites when available
        if use_cloudscraper and _CLOUDSCRAPER_AVAILABLE:
            self.session = _cloudscraper_mod.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
            )
        else:
            self.session = requests.Session()
            # Mount the TLS adapter on both schemes to fix SSL handshake errors
            _tls = _TLSAdapter()
            self.session.mount('https://', _tls)
            self.session.mount('http://', _tls)

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
        # Guard against empty body (geo-block or bot-wall returning no content)
        if not resp.content:
            message.log_error("Empty response body for {}".format(url), self.name)
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
