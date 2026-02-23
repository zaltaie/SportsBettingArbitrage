"""
DraftKings scraper  —  https://sportsbook.draftkings.com
DraftKings is licensed in Ontario and other Canadian provinces.

DraftKings exposes a public odds API used by their web client:
  https://sportsbook.draftkings.com/api/odds/v1/leagues/{leagueId}/offers/gamelines
Note: odds are also fully covered by The Odds API (use OddsAPIScraper for
reliability). This direct scraper provides a fallback when no API key is set.
"""
from typing import List, Optional

from arbitrage import OddsEntry
from config import SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


_DK_BASE = 'https://sportsbook.draftkings.com'
_DK_API = 'https://sportsbook.draftkings.com/api/odds/v1/leagues'

# DraftKings league IDs for Canadian markets
_DK_LEAGUE_IDS = {
    'NHL': 42133,
    'NBA': 42648,
    'NFL': 88808,
    'MLB': 84240,
    'MLS': 44401,
    'CFL': 88824,
}


class DraftKingsScraper(BaseScraper):
    """Scrapes moneyline odds directly from the DraftKings public API."""

    def __init__(self):
        super().__init__(
            name='DraftKings',
            base_url=_DK_BASE,
            headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'application/json',
                'Accept-Language': 'en-CA,en;q=0.9',
                'Referer': _DK_BASE + '/featured',
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
            else list(_DK_LEAGUE_IDS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            league_id = _DK_LEAGUE_IDS.get(label)
            if not league_id:
                continue
            message.log_debug("Fetching {} from DraftKings…".format(label), self.name)
            entries = self._fetch_league(label, league_id)
            all_entries.extend(entries)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_league(self, sport_label: str, league_id: int) -> List[OddsEntry]:
        url = '{}/{}/offers/gamelines'.format(_DK_API, league_id)
        data = self.get_json(url)
        if data is None:
            message.log_warning("No data from DraftKings for {}".format(sport_label), self.name)
            return []
        return self._parse(data, sport_label)

    def _parse(self, data: dict, sport_label: str) -> List[OddsEntry]:
        entries: List[OddsEntry] = []
        offers = data.get('offers', [])
        for offer_group in offers:
            for offer in offer_group.get('offers', [offer_group]):
                if offer.get('label', '').upper() not in ('MONEYLINE', 'GAME LINES', ''):
                    continue
                outcomes = offer.get('outcomes', [])
                # DraftKings wraps event info in a parallel 'eventGroup' structure;
                # each offer has providerEventGroupId / providerOfferId
                event_name = offer.get('eventGroupName', offer.get('label', ''))
                event_id = str(offer.get('providerOfferId', offer.get('id', '')))
                commence_time = str(offer.get('startDate', ''))

                for outcome in outcomes:
                    participant = outcome.get('participant', outcome.get('label', ''))
                    odds_american = outcome.get('oddsAmerican', outcome.get('odds'))
                    odds_decimal = outcome.get('oddsDecimal', outcome.get('decimal'))

                    decimal = self._to_decimal(odds_decimal, odds_american)
                    if decimal and decimal > 1.0:
                        entries.append(OddsEntry(
                            bookmaker='DraftKings',
                            bookmaker_id='draftkings',
                            sport=sport_label,
                            event_id='dk:' + event_id,
                            event_name=event_name,
                            commence_time=commence_time,
                            outcome=participant,
                            decimal_odds=decimal,
                            url=_DK_BASE + '/featured',
                        ))
        return entries

    @staticmethod
    def _to_decimal(
        decimal_val: Optional[float], american_val: Optional[int]
    ) -> Optional[float]:
        if decimal_val is not None:
            try:
                return float(decimal_val)
            except (ValueError, TypeError):
                pass
        if american_val is not None:
            try:
                ml = int(american_val)
                return round(ml / 100 + 1, 4) if ml > 0 else round(100 / abs(ml) + 1, 4)
            except (ValueError, TypeError):
                pass
        return None
