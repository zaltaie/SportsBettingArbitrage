"""
FanDuel scraper  —  https://www.fanduel.com/sportsbook
FanDuel is licensed in Ontario and expanding across Canada.

FanDuel's API is also covered by The Odds API (OddsAPIScraper). This
direct scraper provides a fallback and may capture additional markets.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_FD_BASE = 'https://www.fanduel.com'
_FD_API = 'https://sbapi.fanduel.com/api'

# FanDuel sport/competition IDs
_FD_SPORTS = {
    'NHL':  ('ice-hockey', 'nhl'),
    'NBA':  ('basketball', 'nba'),
    'NFL':  ('american-football', 'nfl'),
    'MLB':  ('baseball', 'mlb'),
    'MLS':  ('soccer', 'mls'),
    'CFL':  ('canadian-football', 'cfl'),
}


class FanDuelScraper(BaseScraper):
    """Scrapes moneyline odds from FanDuel Canada."""

    def __init__(self):
        super().__init__(
            name='FanDuel',
            base_url=_FD_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _FD_BASE + '/sports',
                'x-fdos-req-source': 'Web',
            },
            delay=1.0,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        sport_labels = (
            [SPORTS[k] for k in sports if k in SPORTS]
            if sports
            else list(_FD_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sport_info = _FD_SPORTS.get(label)
            if not sport_info:
                continue
            sport_slug, league_slug = sport_info
            message.log_debug("Fetching {} from FanDuel…".format(label), self.name)
            entries = self._fetch_sport(label, sport_slug, league_slug)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_slug: str, league_slug: str) -> List[OddsEntry]:
        # FanDuel content API
        url = '{}/content-managed-page?page=SPORT&project=SPORTSBOOK&country=CA' \
              '&_ak=FhMFpcPWXMeyZxOx&sport={}&competition={}'.format(
                  _FD_API, sport_slug, league_slug
              )
        data = self.get_json(url)
        if data:
            return self._parse(data, sport_label, sport_slug, league_slug)

        # Alternative: event-list endpoint
        url2 = '{}/event-list?sport={}&competition={}&market=MATCH_WINNER'.format(
            _FD_API, sport_slug, league_slug
        )
        data = self.get_json(url2)
        if data:
            return self._parse(data, sport_label, sport_slug, league_slug)

        message.log_warning("No data from FanDuel for {}".format(sport_label), self.name)
        return []

    def _parse(self, data: dict, sport_label: str, sport_slug: str, league_slug: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        # Navigate common FanDuel response structures
        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            # FanDuel wraps events in various keys
            for key in ('attachments', 'events', 'matches', 'fixtures', 'data'):
                val = data.get(key)
                if isinstance(val, list):
                    events = val
                    break
                elif isinstance(val, dict):
                    # e.g. {'attachments': {'events': {...}}}
                    for subkey in ('events', 'fixtures', 'matches'):
                        subval = val.get(subkey, {})
                        if isinstance(subval, dict):
                            events = list(subval.values())
                        elif isinstance(subval, list):
                            events = subval
                        if events:
                            break
                if events:
                    break

        for event in events:
            entries.extend(self._parse_event(event, sport_label, sport_slug, league_slug))
        return entries

    def _parse_event(self, event: dict, sport_label: str, sport_slug: str, league_slug: str) -> List[OddsEntry]:
        event_id = str(event.get('eventId', event.get('id', '')))
        home = self._extract_team(event, 'home')
        away = self._extract_team(event, 'away')
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(event.get('openDate', event.get('startTime', event.get('date', ''))))

        entries: List[OddsEntry] = []
        markets = event.get('markets', event.get('betTypes', []))
        if isinstance(markets, dict):
            markets = list(markets.values())

        for market in markets:
            mtype = str(market.get('marketType', market.get('type', ''))).upper()
            if not any(k in mtype for k in ('MATCH_WINNER', 'MONEYLINE', 'H2H', 'WINNER')):
                continue
            runners = market.get('runners', market.get('outcomes', market.get('selections', [])))
            if isinstance(runners, dict):
                runners = list(runners.values())
            for runner in runners:
                name = runner.get('runnerName', runner.get('name', runner.get('label', '')))
                price = self._extract_price(runner)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='FanDuel',
                        bookmaker_id='fanduel',
                        sport=sport_label,
                        event_id='fd:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url='{}/{}/{}'.format(_FD_BASE, sport_slug, league_slug),
                    ))
        return entries

    @staticmethod
    def _extract_team(event: dict, side: str) -> str:
        for key in (side + 'Team', side + 'Name', side):
            val = event.get(key, '')
            if isinstance(val, str) and val:
                return val
            if isinstance(val, dict):
                return val.get('name', val.get('teamName', ''))
        return ''

    @staticmethod
    def _extract_price(runner: dict) -> Optional[float]:
        for key in ('winRunnerOdds', 'sp', 'handicap', 'decimalOdds', 'price', 'odds'):
            val = runner.get(key)
            if val is None:
                continue
            if isinstance(val, dict):
                val = val.get('decimal', val.get('trueOdds', val.get('decimalOdds')))
            try:
                f = float(val)
                return f if f > 1.0 else None
            except (ValueError, TypeError):
                pass
        # Try American
        for key in ('americanOdds', 'american', 'moneyline'):
            val = runner.get(key)
            if val is not None:
                try:
                    ml = int(val)
                    return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
                except (ValueError, TypeError):
                    pass
        return None
