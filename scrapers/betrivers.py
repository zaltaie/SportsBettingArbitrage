"""
BetRivers scraper  —  https://on.betrivers.com  (Ontario)
BetRivers (Rush Street Gaming) is licensed in Ontario, Alberta, and more.

BetRivers uses the SBTech platform, which exposes a clean REST API.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_BETRIVERS_BASE = 'https://on.betrivers.com'
# SBTech API used by BetRivers
_BETRIVERS_API = 'https://eu-offering.kambicdn.org/offering/v2018/rsicanon'

_BETRIVERS_SPORTS = {
    'NHL':  'icehockey',
    'NBA':  'basketball',
    'NFL':  'americanfootball',
    'MLB':  'baseball',
    'MLS':  'football',     # Soccer = football in SBTech
    'CFL':  'canadianfootball',
}

# Betrivers/Kambi event group IDs for major North American leagues
_BETRIVERS_LEAGUE_IDS = {
    'NHL': 1000093187,
    'NBA': 1000093190,
    'NFL': 1000093167,
    'MLB': 1000093184,
    'MLS': 1000094985,
    'CFL': 1000094897,
}


class BetRiversScraper(BaseScraper):
    """Scrapes moneyline odds from BetRivers Canada (Ontario)."""

    def __init__(self):
        super().__init__(
            name='BetRivers',
            base_url=_BETRIVERS_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _BETRIVERS_BASE + '/',
                'Origin': _BETRIVERS_BASE,
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
            else list(_BETRIVERS_SPORTS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            league_id = _BETRIVERS_LEAGUE_IDS.get(label)
            sport_code = _BETRIVERS_SPORTS.get(label)
            if not sport_code:
                continue
            message.log_debug("Fetching {} from BetRivers…".format(label), self.name)
            entries = self._fetch_sport(label, sport_code, league_id)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_sport(
        self, sport_label: str, sport_code: str, league_id: Optional[int]
    ) -> List[OddsEntry]:
        # Kambi (SBTech) offering API — lists events for a league
        if league_id:
            url = '{}/listView/event/group/{}.json'.format(_BETRIVERS_API, league_id)
        else:
            url = '{}/listView/sport/{}.json'.format(_BETRIVERS_API, sport_code)

        params = {
            'lang': 'en_US',
            'market': 'CA',
            'client_id': '2',
            'channel_id': '1',
        }
        data = self.get_json(url, params)
        if data is None:
            message.log_warning("No data from BetRivers for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label)

    def _parse(self, data: dict, sport_label: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        events = data.get('events', [])
        for ev_wrap in events:
            event = ev_wrap.get('event', ev_wrap)
            entries.extend(self._parse_event(event, sport_label))
        return entries

    def _parse_event(self, event: dict, sport_label: str) -> List[OddsEntry]:
        event_id = str(event.get('id', ''))
        # Kambi format: homeName / awayName
        home = event.get('homeName', event.get('home', ''))
        away = event.get('awayName', event.get('away', ''))
        event_name = '{} vs {}'.format(home, away) if home and away else str(event_id)
        commence_time = str(event.get('start', event.get('startTime', '')))

        entries: List[OddsEntry] = []
        # Betoffers in Kambi format
        for betoffer in event.get('betOffers', []):
            criterion = betoffer.get('criterion', {})
            label = criterion.get('label', betoffer.get('betOfferType', {}).get('name', ''))
            if 'Full Time' not in label and 'Moneyline' not in label and 'Winner' not in label:
                continue
            for outcome in betoffer.get('outcomes', []):
                label_out = outcome.get('label', outcome.get('englishLabel', ''))
                # Kambi stores decimal odds as integer × 1000 (milliodds)
                odds_raw = outcome.get('odds', outcome.get('decimalOdds', 0))
                if isinstance(odds_raw, (int, float)) and odds_raw > 0:
                    decimal = odds_raw / 1000.0 if odds_raw > 100 else float(odds_raw)
                    if decimal > 1.0:
                        entries.append(OddsEntry(
                            bookmaker='BetRivers',
                            bookmaker_id='betrivers',
                            sport=sport_label,
                            event_id='br:' + event_id,
                            event_name=event_name,
                            commence_time=commence_time,
                            outcome=label_out,
                            decimal_odds=round(decimal, 4),
                            url=_BETRIVERS_BASE + '/#/sports/event/' + event_id,
                        ))
        return entries
