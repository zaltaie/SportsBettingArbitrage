"""
Bet365 scraper  —  https://www.bet365.com
Bet365 is the world's largest online bookmaker, licensed in Canada.

Bet365 uses heavy Cloudflare protection and a fully JavaScript-rendered
frontend, making HTML scraping unreliable. The recommended approaches are:
  1. Use The Odds API, which sources Bet365 odds (requires 'worldwide' plan).
  2. Use OddsChecker, which always includes Bet365 prices.
  3. Use Selenium with an undetected Chrome driver (see comments below).

This scraper attempts a lightweight JSON-endpoint probe and falls back
gracefully to an empty list, so the rest of the scrapers keep running.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_BET365_BASE = 'https://www.bet365.com'

# Bet365 Canada redirect
_BET365_CA = 'https://www.bet365.com/#/AS/B1/'

_BET365_SPORTS = {
    'NHL': '7',    # Ice Hockey
    'NBA': '7',    # Basketball
    'NFL': '16',   # American Football
    'MLB': '14',   # Baseball
    'MLS': '13',   # Soccer
    'CFL': '16',   # Canadian Football (under American Football)
}


class Bet365Scraper(BaseScraper):
    """
    Bet365 Canada scraper.

    Primary strategy: probe Bet365's internal ODS (Odds Data Service)
    endpoints. These may return HTTP 403 due to Cloudflare — in that case
    we log a warning and return [] so other scrapers are unaffected.

    To enable full Bet365 scraping with Selenium:
        pip install undetected-chromedriver
    Then replace this class body with a Selenium-based implementation.
    """

    def __init__(self):
        super().__init__(
            name='Bet365',
            base_url=_BET365_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _BET365_BASE + '/',
            },
            delay=3.0,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        """
        Attempt to fetch Bet365 odds. Returns [] if Bet365 blocks access.
        Bet365 prices are still captured via OddsCheckerScraper (bookmaker
        code B3), so this scraper is supplementary.
        """
        sport_labels = (
            [SPORTS[k] for k in sports if k in SPORTS]
            if sports
            else list(_BET365_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            message.log_debug("Probing Bet365 for {}…".format(label), self.name)
            entries = self._fetch_sport(label)
            all_entries.extend(entries)

        if not all_entries:
            message.log_debug(
                "Bet365 direct access blocked or unavailable. "
                "Bet365 odds are included via OddsChecker (code B3).",
                self.name,
            )
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str) -> List[OddsEntry]:
        """Probe Bet365 ODS API. Returns [] on any failure."""
        # Bet365 ODS endpoint (may return 403 from outside permitted regions)
        sport_id = _BET365_SPORTS.get(sport_label, '13')
        url = '{}/defaultapi/sports-data/sport/{}/events/'.format(_BET365_BASE, sport_id)
        data = self.get_json(url)
        if not data:
            return []
        return self._parse(data, sport_label)

    def _parse(self, data, sport_label: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        events = data if isinstance(data, list) else data.get('events', data.get('data', []))
        for event in events:
            entries.extend(self._parse_event(event, sport_label))
        return entries

    def _parse_event(self, event: dict, sport_label: str) -> List[OddsEntry]:
        event_id = str(event.get('id', ''))
        home = event.get('home', event.get('homeTeam', ''))
        away = event.get('away', event.get('awayTeam', ''))
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(event.get('startTime', event.get('date', '')))

        entries: List[OddsEntry] = []
        for market in event.get('markets', []):
            if 'winner' not in str(market.get('type', '')).lower():
                continue
            for sel in market.get('selections', []):
                name = sel.get('name', '')
                price = sel.get('decimalOdds', sel.get('price', 0))
                try:
                    price = float(price)
                except (ValueError, TypeError):
                    continue
                if price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='Bet365',
                        bookmaker_id='bet365',
                        sport=sport_label,
                        event_id='b3:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url=_BET365_CA,
                    ))
        return entries
