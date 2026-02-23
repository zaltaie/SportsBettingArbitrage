"""
The Odds API scraper  —  https://the-odds-api.com
Free tier: 500 requests/month. Set ODDS_API_KEY in your environment.

Covers these Canadian bookmakers:
  draftkings, fanduel, betmgm, pointsbetus, betrivers
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import (
    ODDS_API_KEY,
    ODDS_API_BASE_URL,
    ODDS_API_CANADIAN_BOOKMAKERS,
    SPORTS,
)
from message import message
from scrapers.base_scraper import BaseScraper


class OddsAPIScraper(BaseScraper):
    """Fetches odds for multiple Canadian bookmakers via The Odds API."""

    def __init__(self):
        super().__init__(
            name='OddsAPI',
            base_url=ODDS_API_BASE_URL,
            delay=0.5,   # API-backed, lighter throttle needed
        )
        self.api_key = ODDS_API_KEY

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        if not self.api_key:
            message.log_warning(
                "ODDS_API_KEY not set — skipping The Odds API. "
                "Get a free key at https://the-odds-api.com",
                self.name,
            )
            return []

        target_sports = sports or list(SPORTS.keys())
        all_entries: List[OddsEntry] = []

        for sport_key in target_sports:
            sport_label = SPORTS.get(sport_key, sport_key)
            message.log_debug("Fetching {} odds via Odds API…".format(sport_label), self.name)
            entries = self._fetch_sport(sport_key, sport_label)
            all_entries.extend(entries)
            message.log_debug(
                "  {} entries collected for {}".format(len(entries), sport_label), self.name
            )

        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_key: str, sport_label: str) -> List[OddsEntry]:
        url = '{}/sports/{}/odds/'.format(self.base_url, sport_key)
        params = {
            'apiKey': self.api_key,
            'regions': 'us',          # 'us' region includes Canadian operators
            'markets': 'h2h',         # head-to-head (moneyline) markets
            'oddsFormat': 'decimal',
            'bookmakers': ','.join(ODDS_API_CANADIAN_BOOKMAKERS),
        }
        data = self.get_json(url, params)
        if not data:
            return []

        entries: List[OddsEntry] = []
        for event in data:
            entries.extend(self._parse_event(event, sport_label))
        return entries

    def _parse_event(self, event: dict, sport_label: str) -> List[OddsEntry]:
        event_id = event.get('id', '')
        event_name = '{} vs {}'.format(
            event.get('home_team', ''), event.get('away_team', '')
        )
        commence_time = event.get('commence_time', '')
        sport_key = event.get('sport_key', sport_label)

        entries: List[OddsEntry] = []
        for bm in event.get('bookmakers', []):
            bm_key = bm.get('key', '')
            bm_title = bm.get('title', bm_key)
            for market in bm.get('markets', []):
                if market.get('key') != 'h2h':
                    continue
                for outcome in market.get('outcomes', []):
                    price = float(outcome.get('price', 0))
                    if price <= 1.0:
                        continue
                    entries.append(
                        OddsEntry(
                            bookmaker=bm_title,
                            bookmaker_id=bm_key,
                            sport=sport_label,
                            event_id=event_id,
                            event_name=event_name,
                            commence_time=commence_time,
                            outcome=outcome.get('name', ''),
                            decimal_odds=price,
                            url='{}/sports'.format(
                                'https://sportsbook.draftkings.com'
                                if 'draftkings' in bm_key else
                                'https://www.fanduel.com/sports'
                                if 'fanduel' in bm_key else
                                'https://sports.on.betmgm.ca'
                                if 'betmgm' in bm_key else
                                'https://ca.pointsbet.com'
                                if 'pointsbetus' in bm_key else
                                'https://on.betrivers.com'
                            ),
                        )
                    )
        return entries
