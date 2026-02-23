"""
Bodog scraper  —  https://www.bodog.eu/sports/
Bodog is one of Canada's most popular offshore sportsbooks.

Bodog exposes a public JSON API used by their web client:
  https://www.bodog.eu/publishedapi/en/v2/sports/{sport}/events/
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_BODOG_BASE = 'https://www.bodog.eu'
_BODOG_API = 'https://www.bodog.eu/publishedapi/en/v2'

# Bodog sport codes
_BODOG_SPORTS = {
    'NHL': 'icehockey',
    'NBA': 'basketball',
    'NFL': 'football',
    'MLB': 'baseball',
    'MLS': 'soccer',
    'CFL': 'canadianfootball',
}


class BodogScraper(BaseScraper):
    """Scrapes moneyline odds from Bodog Canada."""

    def __init__(self):
        super().__init__(
            name='Bodog',
            base_url=_BODOG_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _BODOG_BASE + '/sports/',
                'Origin': _BODOG_BASE,
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
            else list(_BODOG_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            code = _BODOG_SPORTS.get(label)
            if not code:
                continue
            message.log_debug("Fetching {} from Bodog…".format(label), self.name)
            entries = self._fetch_sport(label, code)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_code: str) -> List[OddsEntry]:
        url = '{}/sports/{}/events/'.format(_BODOG_API, sport_code)
        data = self.get_json(url)
        if data is None:
            # Try alternate endpoint format
            url2 = '{}/sports/{}/'.format(_BODOG_API, sport_code)
            data = self.get_json(url2)
        if data is None:
            message.log_warning("No data from Bodog for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label)

    def _parse(self, data, sport_label: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        # Bodog API returns either a list or a dict with a 'categories' or 'events' key
        events = []
        if isinstance(data, list):
            events = data
        elif isinstance(data, dict):
            for key in ('events', 'data', 'categories', 'leagues'):
                if key in data:
                    val = data[key]
                    if isinstance(val, list):
                        events = val
                        break
                    # Some endpoints nest events under league
                    for item in val if isinstance(val, list) else [val]:
                        if isinstance(item, dict):
                            events.extend(item.get('events', []))

        for event in events:
            parsed = self._parse_event(event, sport_label)
            entries.extend(parsed)
        return entries

    def _parse_event(self, event: dict, sport_label: str) -> List[OddsEntry]:
        event_id = str(event.get('id', event.get('eventId', '')))
        competitors = event.get('competitors', event.get('participants', []))
        if len(competitors) >= 2:
            home = competitors[0].get('name', competitors[0].get('shortName', ''))
            away = competitors[1].get('name', competitors[1].get('shortName', ''))
        else:
            home = event.get('homeTeamName', event.get('home', ''))
            away = event.get('awayTeamName', event.get('away', ''))
        event_name = '{} vs {}'.format(home, away) if (home and away) else event_id
        commence_time = str(event.get('startTime', event.get('gameTime', event.get('date', ''))))

        entries: List[OddsEntry] = []
        # Look for moneyline / winner market
        markets = event.get('markets', event.get('displayGroups', []))
        for market in markets:
            market_desc = str(market.get('description', market.get('type', ''))).upper()
            if not any(k in market_desc for k in ('MONEYLINE', 'WINNER', 'ML', 'GAME LINES')):
                continue
            outcomes = market.get('outcomes', market.get('selections', []))
            for sel in outcomes:
                name = sel.get('description', sel.get('name', ''))
                price = self._get_price(sel)
                if price and price > 1.0:
                    entries.append(OddsEntry(
                        bookmaker='Bodog',
                        bookmaker_id='bodog',
                        sport=sport_label,
                        event_id='bodog:' + event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=name,
                        decimal_odds=price,
                        url=_BODOG_BASE + '/sports/',
                    ))
        return entries

    @staticmethod
    def _get_price(sel: dict) -> Optional[float]:
        for key in ('price', 'decimal', 'decimalOdds', 'odds'):
            val = sel.get(key)
            if val is not None:
                price_val = val if not isinstance(val, dict) else val.get('decimal', val.get('d'))
                try:
                    return float(price_val)
                except (ValueError, TypeError):
                    pass
        return None
