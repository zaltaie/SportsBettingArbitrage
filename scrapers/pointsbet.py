"""
PointsBet scraper  —  https://ca.pointsbet.com
PointsBet is licensed in Ontario and multiple Canadian provinces.

PointsBet exposes a public JSON API used by their web client.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_PB_BASE = 'https://ca.pointsbet.com'
_PB_API = 'https://api.ca.pointsbet.com'

# PointsBet sport keys
_PB_SPORTS = {
    'NHL':  'ice-hockey',
    'NBA':  'basketball',
    'NFL':  'american-football',
    'MLB':  'baseball',
    'MLS':  'soccer',
    'CFL':  'canadian-football',
}

# PointsBet league slugs
_PB_LEAGUES = {
    'NHL': 'nhl',
    'NBA': 'nba',
    'NFL': 'nfl',
    'MLB': 'mlb',
    'MLS': 'mls',
    'CFL': 'cfl',
}


class PointsBetScraper(BaseScraper):
    """Scrapes moneyline odds from PointsBet Canada."""

    def __init__(self):
        super().__init__(
            name='PointsBet',
            base_url=_PB_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _PB_BASE + '/',
                'x-pb-client': 'web',
                'x-pb-country': 'CA',
            },
            delay=1.5,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        sport_labels = (
            [SPORTS[k] for k in sports if k in SPORTS]
            if sports
            else list(_PB_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sport_slug = _PB_SPORTS.get(label)
            league_slug = _PB_LEAGUES.get(label)
            if not sport_slug:
                continue
            message.log_debug("Fetching {} from PointsBet…".format(label), self.name)
            entries = self._fetch_sport(label, sport_slug, league_slug)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(
        self, sport_label: str, sport_slug: str, league_slug: Optional[str]
    ) -> List[OddsEntry]:
        # PointsBet league events endpoint
        url = '{}/v2/sports/{}/leagues/{}/events'.format(_PB_API, sport_slug, league_slug or sport_slug)
        data = self.get_json(url)
        if data is None:
            url2 = '{}/v2/sports/{}/events?type=Fixed'.format(_PB_API, sport_slug)
            data = self.get_json(url2)
        if data is None:
            message.log_warning("No data from PointsBet for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label, sport_slug, league_slug)

    def _parse(self, data, sport_label: str, sport_slug: str, league_slug: Optional[str]) -> List[OddsEntry]:
        events = data if isinstance(data, list) else data.get('events', data.get('fixtures', []))
        return [
            entry
            for event in events
            for entry in self._parse_event(event, sport_label, sport_slug, league_slug)
        ]

    def _parse_event(
        self, event: dict, sport_label: str, sport_slug: str, league_slug: Optional[str]
    ) -> List[OddsEntry]:
        event_id = str(event.get('id', event.get('eventId', '')))
        home = event.get('homeTeam', event.get('home', event.get('homeName', '')))
        away = event.get('awayTeam', event.get('away', event.get('awayName', '')))
        if isinstance(home, dict):
            home = home.get('name', '')
        if isinstance(away, dict):
            away = away.get('name', '')
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(event.get('startsAt', event.get('startTime', event.get('date', ''))))

        entries: List[OddsEntry] = []
        for market in event.get('markets', event.get('betTypes', [])):
            mtype = str(market.get('typeName', market.get('type', market.get('name', '')))).upper()
            if not any(k in mtype for k in ('MONEYLINE', 'MATCH WINNER', 'HEAD TO HEAD', 'H2H')):
                continue
            for outcome in market.get('outcomes', market.get('selections', [])):
                name = outcome.get('name', outcome.get('label', outcome.get('teamName', '')))
                price = self._get_price(outcome)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='PointsBet',
                        bookmaker_id='pointsbet',
                        sport=sport_label,
                        event_id='pb:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url='{}/{}/{}'.format(_PB_BASE, sport_slug, league_slug or ''),
                    ))
        return entries

    @staticmethod
    def _get_price(outcome: dict) -> Optional[float]:
        for key in ('decimalOdds', 'decimal', 'price', 'odds'):
            val = outcome.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        # American format
        for key in ('americanOdds', 'american', 'moneylineOdds'):
            val = outcome.get(key)
            if val is not None:
                try:
                    ml = int(val)
                    return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
                except (ValueError, TypeError):
                    pass
        return None
