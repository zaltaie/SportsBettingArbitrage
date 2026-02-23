"""
theScore Bet scraper  —  https://bets.thescore.com
theScore Bet is licensed in Ontario and other Canadian provinces.

theScore Bet is powered by Penn Entertainment and uses a REST API
at api.bets.thescore.com (same infrastructure as Barstool/ESPN Bet CA).
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_THESCORE_BASE = 'https://bets.thescore.com'
_THESCORE_API = 'https://api.bets.thescore.com/v1'

_THESCORE_SPORTS = {
    'NHL': 'icehockey/nhl',
    'NBA': 'basketball/nba',
    'NFL': 'americanfootball/nfl',
    'MLB': 'baseball/mlb',
    'MLS': 'soccer/mls',
    'CFL': 'canadianfootball/cfl',
}


class TheScoreScraper(BaseScraper):
    """Scrapes moneyline odds from theScore Bet Canada."""

    def __init__(self):
        super().__init__(
            name='theScore Bet',
            base_url=_THESCORE_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                    'Version/17.0 Mobile/15E148 Safari/604.1'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA',
                'Referer': _THESCORE_BASE + '/',
                'x-app-version': '1.0',
                'x-client': 'web',
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
            else list(_THESCORE_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sport_path = _THESCORE_SPORTS.get(label)
            if not sport_path:
                continue
            message.log_debug("Fetching {} from theScore Bet…".format(label), self.name)
            entries = self._fetch_sport(label, sport_path)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_path: str) -> List[OddsEntry]:
        # Try the public events API
        url = '{}/leagues/{}/events'.format(_THESCORE_API, sport_path)
        data = self.get_json(url)
        if data is None:
            url2 = '{}/sports/{}/events?market=moneyline'.format(_THESCORE_API, sport_path)
            data = self.get_json(url2)
        if data is None:
            message.log_warning("No data from theScore Bet for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label)

    def _parse(self, data, sport_label: str) -> List[OddsEntry]:
        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            for key in ('events', 'data', 'fixtures', 'games'):
                if key in data and isinstance(data[key], list):
                    events = data[key]
                    break
        return [entry for ev in events for entry in self._parse_event(ev, sport_label)]

    def _parse_event(self, event: dict, sport_label: str) -> List[OddsEntry]:
        event_id = str(event.get('id', event.get('eventId', '')))
        home = self._team_name(event.get('homeTeam', event.get('home', {})))
        away = self._team_name(event.get('awayTeam', event.get('away', {})))
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(event.get('startTime', event.get('scheduledStartTime', '')))

        entries: List[OddsEntry] = []
        markets = event.get('markets', event.get('odds', []))
        for market in markets:
            mtype = str(market.get('type', market.get('key', ''))).upper()
            if not any(k in mtype for k in ('MONEYLINE', 'H2H', 'WINNER', 'ML')):
                continue
            for sel in market.get('selections', market.get('outcomes', [])):
                name = sel.get('name', sel.get('label', ''))
                price = self._get_price(sel)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='theScore Bet',
                        bookmaker_id='thescore',
                        sport=sport_label,
                        event_id='sc:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url=_THESCORE_BASE + '/sports/' + sport_label.lower(),
                    ))
        return entries

    @staticmethod
    def _team_name(team) -> str:
        if isinstance(team, str):
            return team
        if isinstance(team, dict):
            return team.get('name', team.get('fullName', team.get('shortName', '')))
        return ''

    @staticmethod
    def _get_price(sel: dict) -> Optional[float]:
        for key in ('decimalOdds', 'decimal', 'price', 'odds', 'americanOdds'):
            val = sel.get(key)
            if val is None:
                continue
            try:
                f = float(val)
                if 'american' in key.lower() or (f > 100 or f < -100):
                    return round(f / 100 + 1, 4) if f > 0 else round(100 / abs(f) + 1, 4)
                return f if f > 1.0 else None
            except (ValueError, TypeError):
                pass
        return None
