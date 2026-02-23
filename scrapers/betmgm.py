"""
BetMGM scraper  —  https://sports.on.betmgm.ca  (Ontario)
BetMGM is licensed in Ontario with expansion to other Canadian provinces.

BetMGM uses the Roar Digital (Entain) platform. Their public API returns
event/market data in JSON format.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_BETMGM_BASE = 'https://sports.on.betmgm.ca'
_BETMGM_API = 'https://cds-api.betmgm.ca/bettingoffer/fixtures'

_BETMGM_SPORT_IDS = {
    'NHL': 3,    # Ice Hockey
    'NBA': 7,    # Basketball
    'NFL': 9,    # American Football
    'MLB': 5,    # Baseball
    'MLS': 6,    # Soccer
    'CFL': 34,   # Canadian Football
}


class BetMGMScraper(BaseScraper):
    """Scrapes moneyline odds from BetMGM Canada."""

    def __init__(self):
        super().__init__(
            name='BetMGM',
            base_url=_BETMGM_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _BETMGM_BASE + '/en/sports',
                'x-bwin-brand': 'betmgm',
                'x-bwin-country': 'CA',
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
            else list(_BETMGM_SPORT_IDS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            sport_id = _BETMGM_SPORT_IDS.get(label)
            if not sport_id:
                continue
            message.log_debug("Fetching {} from BetMGM…".format(label), self.name)
            entries = self._fetch_sport(label, sport_id)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(self, sport_label: str, sport_id: int) -> List[OddsEntry]:
        url = _BETMGM_API
        params = {
            'x-bwin-accessid': 'NmFkOWE5NGMtMTNkMi00ZTFmLWI1YTctYjEzYWI0NzZlY2Q1',
            'lang': 'en-ca',
            'country': 'CA',
            'userCountry': 'CA',
            'subdivision': 'CA-ON',
            'fixtureTypes': 'Standard',
            'state': 'Available',
            'sportIds': str(sport_id),
            'regionIds': '102',   # North America
            'offerMapping': 'Filtered',
            'offerCategories': 'Gridable',
            'offerSubCategories': 'All',
            'fixtureCategory': 'Gridable',
            'topCount': '100',
        }
        data = self.get_json(url, params)
        if data is None:
            message.log_warning("No data from BetMGM for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label)

    def _parse(self, data, sport_label: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        fixtures = (
            data if isinstance(data, list)
            else data.get('fixtures', data.get('events', data.get('data', [])))
        )
        for fixture in fixtures:
            entries.extend(self._parse_fixture(fixture, sport_label))
        return entries

    def _parse_fixture(self, fixture: dict, sport_label: str) -> List[OddsEntry]:
        event_id = str(fixture.get('id', fixture.get('fixtureId', '')))
        participants = fixture.get('participants', [])
        teams = [p.get('name', {}).get('value', p.get('name', ''))
                 if isinstance(p.get('name'), dict) else p.get('name', p.get('shortName', ''))
                 for p in participants]
        home = teams[0] if len(teams) > 0 else ''
        away = teams[1] if len(teams) > 1 else ''
        event_name = '{} vs {}'.format(home, away) if home and away else event_id
        commence_time = str(fixture.get('startDate', fixture.get('date', '')))

        entries: List[OddsEntry] = []
        for offer_category in fixture.get('offerCategories', []):
            for offer in offer_category.get('offerGroups', [{}])[0].get('offers', []) \
                    if offer_category.get('offerGroups') else []:
                market_name = offer.get('name', {}).get('value', '') if isinstance(
                    offer.get('name'), dict) else offer.get('name', '')
                if not any(k in market_name.upper() for k in ('MONEYLINE', 'WINNER', 'MATCH')):
                    continue
                for outcome in offer.get('outcomes', []):
                    name_obj = outcome.get('name', {})
                    name = name_obj.get('value', '') if isinstance(name_obj, dict) else str(name_obj)
                    price = outcome.get('odds', {})
                    if isinstance(price, dict):
                        decimal = price.get('decimal', price.get('dec'))
                    else:
                        decimal = price
                    try:
                        decimal = float(decimal)
                    except (ValueError, TypeError):
                        continue
                    if decimal > 1.0:
                        entries.append(OddsEntry(
                            bookmaker='BetMGM',
                            bookmaker_id='betmgm',
                            sport=sport_label,
                            event_id='mgm:' + event_id,
                            event_name=event_name,
                            commence_time=commence_time,
                            outcome=name,
                            decimal_odds=decimal,
                            url=_BETMGM_BASE + '/en/sports',
                        ))
        return entries
