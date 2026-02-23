"""
Betway scraper  —  https://sports.betway.com
Betway is licensed in Ontario and major Canadian provinces.

Betway's web client communicates with a GraphQL / REST backend.
We target the public JSON feed used for the pre-match lobby.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_BETWAY_BASE = 'https://sports.betway.com'
_BETWAY_API = 'https://sports.betway.com/en/sports/api'

_BETWAY_SPORTS = {
    'NHL': 'ice-hockey/north-america/nhl',
    'NBA': 'basketball/north-america/nba',
    'NFL': 'american-football/usa/nfl',
    'MLB': 'baseball/usa/mlb',
    'MLS': 'soccer/usa/major-league-soccer',
    'CFL': 'canadian-football/canada/cfl',
}


class BetwayScraper(BaseScraper):
    """Scrapes moneyline odds from Betway Canada."""

    def __init__(self):
        super().__init__(
            name='Betway',
            base_url=_BETWAY_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _BETWAY_BASE + '/en/sports/',
                'x-bw-client': 'web',
            },
            delay=2.0,
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        sport_labels = (
            [SPORTS[k] for k in sports if k in SPORTS]
            if sports
            else list(_BETWAY_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sport_path = _BETWAY_SPORTS.get(label)
            if not sport_path:
                continue
            message.log_debug("Fetching {} from Betway…".format(label), self.name)
            entries = self._fetch_sport(label, sport_path)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_path: str) -> List[OddsEntry]:
        url = '{}/type/{}/'.format(_BETWAY_API, sport_path)
        data = self.get_json(url)
        if data is None:
            # Fallback: scrape the HTML page
            soup = self.get_soup('{}/en/sports/{}/'.format(_BETWAY_BASE, sport_path))
            if soup:
                return self._parse_html(soup, sport_label, sport_path)
            message.log_warning("No data from Betway for {}".format(sport_label), self.name)
            return []
        return self._parse_json(data, sport_label, sport_path)

    def _parse_json(self, data, sport_label: str, sport_path: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            for key in ('events', 'data', 'items', 'fixtures'):
                if key in data and isinstance(data[key], list):
                    events = data[key]
                    break

        for event in events:
            entries.extend(self._parse_event(event, sport_label, sport_path))
        return entries

    def _parse_event(self, event: dict, sport_label: str, sport_path: str) -> List[OddsEntry]:
        event_id = str(event.get('id', event.get('eventId', '')))
        home = event.get('homeTeam', event.get('home', event.get('teamA', '')))
        away = event.get('awayTeam', event.get('away', event.get('teamB', '')))
        if isinstance(home, dict):
            home = home.get('name', home.get('shortName', ''))
        if isinstance(away, dict):
            away = away.get('name', away.get('shortName', ''))
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(event.get('startTime', event.get('date', event.get('kickoff', ''))))

        entries: List[OddsEntry] = []
        markets = event.get('markets', event.get('betTypes', []))
        for market in markets:
            mtype = str(market.get('type', market.get('name', ''))).upper()
            if not any(k in mtype for k in ('MONEYLINE', 'MATCH WINNER', 'H2H', 'WIN')):
                continue
            for sel in market.get('outcomes', market.get('selections', [])):
                name = sel.get('name', sel.get('label', ''))
                price = self._get_decimal(sel)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='Betway',
                        bookmaker_id='betway',
                        sport=sport_label,
                        event_id='bw:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url='{}/en/sports/{}/'.format(_BETWAY_BASE, sport_path),
                    ))
        return entries

    def _parse_html(self, soup, sport_label: str, sport_path: str) -> List[OddsEntry]:
        """HTML fallback parser."""
        entries: List[OddsEntry] = []
        for row in soup.select('[data-event-id], .event-row, .fixture-row'):
            event_id = row.get('data-event-id', '')
            teams = [t.get_text(strip=True) for t in row.select('.team, .participant, .competitor')]
            if len(teams) < 2:
                continue
            event_name = '{} vs {}'.format(teams[0], teams[1])
            prices = [p.get_text(strip=True) for p in row.select('.price, .odds, [data-odds]')]
            for i, (team, price_str) in enumerate(zip(teams, prices)):
                price = self._parse_price_str(price_str)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='Betway',
                        bookmaker_id='betway',
                        sport=sport_label,
                        event_id='bw:' + (event_id or team + str(i)),
                        event_name=event_name,
                        commence_time='',
                        outcome=team,
                        decimal_odds=price,
                        url='{}/en/sports/{}/'.format(_BETWAY_BASE, sport_path),
                    ))
        return entries

    @staticmethod
    def _get_decimal(sel: dict) -> Optional[float]:
        for key in ('price', 'decimalOdds', 'decimal', 'odds'):
            val = sel.get(key)
            if val is None:
                continue
            if isinstance(val, dict):
                val = val.get('decimal', val.get('d', val.get('dec')))
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def _parse_price_str(text: str) -> Optional[float]:
        text = text.strip()
        if not text or text in ('-', 'N/A'):
            return None
        try:
            if text.startswith(('+', '-')):
                ml = int(text)
                return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
            if '/' in text:
                from fractions import Fraction
                return round(float(Fraction(text)) + 1, 4)
            return float(text)
        except (ValueError, ZeroDivisionError):
            return None
