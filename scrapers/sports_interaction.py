"""
Sports Interaction scraper  —  https://www.sportsinteraction.com
Canada's oldest licensed online sportsbook.

Sports Interaction serves odds via a JSON API at:
  https://www.sportsinteraction.com/api/sport-events/
Headers required: X-Platform, X-Brand
"""
import hashlib
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


# Sports Interaction internal sport IDs
_SI_SPORT_IDS = {
    'NHL': 'IH',   # Ice Hockey
    'NBA': 'BB',   # Basketball
    'NFL': 'AF',   # American Football
    'MLB': 'BS',   # Baseball
    'MLS': 'SO',   # Soccer
    'CFL': 'CF',   # Canadian Football
}

_SI_BASE = 'https://www.sportsinteraction.com'
_SI_API = 'https://www.sportsinteraction.com/api'


class SportsInteractionScraper(BaseScraper):
    """Scrapes live betting lines from Sports Interaction."""

    def __init__(self):
        super().__init__(
            name='Sports Interaction',
            base_url=_SI_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _SI_BASE + '/',
                'X-Platform': 'WEB',
                'X-Brand': 'si',
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
            else list(_SI_SPORT_IDS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sid = _SI_SPORT_IDS.get(label)
            if not sid:
                continue
            message.log_debug("Fetching {} from Sports Interaction…".format(label), self.name)
            entries = self._fetch_sport(label, sid)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_id: str) -> List[OddsEntry]:
        """Fetch moneyline markets for a sport category."""
        url = '{}/betting-lines/{}/'.format(_SI_BASE, sport_label.lower().replace(' ', '-'))

        # Try JSON API endpoint first
        api_url = '{}/sport-events/?sport={}&market=ML&format=json'.format(_SI_API, sport_id)
        data = self.get_json(api_url)
        if data:
            return self._parse_api_response(data, sport_label)

        # Fallback: parse HTML page
        soup = self.get_soup(url)
        if soup:
            return self._parse_html(soup, sport_label, url)

        message.log_warning("No data from Sports Interaction for {}".format(sport_label), self.name)
        return []

    def _parse_api_response(self, data: dict, sport_label: str) -> List[OddsEntry]:
        """Parse JSON response from the Sports Interaction API."""
        entries: List[OddsEntry] = []
        events = data if isinstance(data, list) else data.get('events', data.get('data', []))

        for event in events:
            event_id = str(event.get('id', event.get('eventId', '')))
            home = event.get('homeTeam', event.get('home', ''))
            away = event.get('awayTeam', event.get('away', ''))
            event_name = '{} vs {}'.format(home, away) if home and away else str(event_id)
            commence_time = str(event.get('startTime', event.get('date', '')))

            markets = event.get('markets', event.get('odds', []))
            for market in markets:
                market_type = market.get('type', market.get('marketType', '')).upper()
                if market_type not in ('ML', 'MONEYLINE', 'H2H', 'WINNER'):
                    continue
                for selection in market.get('selections', market.get('outcomes', [])):
                    name = selection.get('name', selection.get('team', ''))
                    price = self._extract_price(selection)
                    if price and price > 1.0:
                        entries.append(OddsEntry(
                            bookmaker='Sports Interaction',
                            bookmaker_id='sports_interaction',
                            sport=sport_label,
                            event_id='si:' + event_id,
                            event_name=event_name,
                            commence_time=commence_time,
                            outcome=name,
                            decimal_odds=price,
                            url='{}/sports/{}/'.format(_SI_BASE, sport_label.lower()),
                        ))
        return entries

    def _parse_html(self, soup, sport_label: str, page_url: str) -> List[OddsEntry]:
        """Parse HTML betting lines page as fallback."""
        entries: List[OddsEntry] = []
        # Look for event rows — SI uses div.event-row or tr[data-event-id]
        for row in soup.select('[data-event-id], div.event-row, div.game-row'):
            event_id = row.get('data-event-id', '')
            teams = row.select('.team-name, .participant, .competitor')
            if len(teams) < 2:
                continue
            home, away = teams[0].get_text(strip=True), teams[1].get_text(strip=True)
            event_name = '{} vs {}'.format(home, away)

            # Get ML odds
            ml_cells = row.select('.ml-odds, .moneyline, [data-market="ML"]')
            outcomes = [home, away]
            for i, cell in enumerate(ml_cells[:2]):
                price = self._parse_american_or_decimal(cell.get_text(strip=True))
                if price and price > 1.0 and i < len(outcomes):
                    entries.append(OddsEntry(
                        bookmaker='Sports Interaction',
                        bookmaker_id='sports_interaction',
                        sport=sport_label,
                        event_id='si:' + (event_id or hashlib.md5(event_name.encode()).hexdigest()[:8]),
                        event_name=event_name,
                        commence_time='',
                        outcome=outcomes[i],
                        decimal_odds=price,
                        url=page_url,
                    ))
        return entries

    @staticmethod
    def _extract_price(selection: dict) -> Optional[float]:
        for key in ('decimalOdds', 'decimal', 'price', 'odds'):
            val = selection.get(key)
            if val:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    pass
        # Try American odds
        for key in ('americanOdds', 'american', 'moneyline'):
            val = selection.get(key)
            if val:
                try:
                    ml = int(val)
                    return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
                except (ValueError, TypeError):
                    pass
        return None

    @staticmethod
    def _parse_american_or_decimal(text: str) -> Optional[float]:
        text = text.strip()
        if not text or text in ('-', 'N/A', ''):
            return None
        try:
            if text.startswith('+') or (text.startswith('-') and len(text) > 1):
                ml = int(text)
                return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
            return float(text)
        except ValueError:
            return None
