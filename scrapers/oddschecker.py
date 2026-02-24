"""
OddsChecker scraper  —  https://www.oddschecker.com
Covers Canadian bookmakers: Bet365, Sports Interaction, Betway, Bodog,
DraftKings, FanDuel, BetMGM, PointsBet, BetRivers, theScore Bet.

OddsChecker renders odds tables server-side for most markets, making
plain requests + BeautifulSoup sufficient for NHL, NBA, NFL, MLB, CFL.

Bookmaker codes used by OddsChecker (data-bk attribute):
  B3=Bet365  SI=Sports Interaction  BW=Betway  BOD=Bodog
  DK=DraftKings  FD=FanDuel  MGM=BetMGM  PB=PointsBet
  BR=BetRivers  SC=theScore Bet
"""
import re
from fractions import Fraction
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

from arbitrage import OddsEntry
from config import ODDSCHECKER_CANADIAN_BOOKMAKERS, ODDSCHECKER_SPORT_URLS, SPORTS
from message import message
from scrapers.base_scraper import BaseScraper


class OddsCheckerScraper(BaseScraper):
    """
    Scrapes OddsChecker for events and odds across Canadian bookmakers.

    Flow:
      1. Fetch the sport listing page (e.g. /ice-hockey/nhl/).
      2. Extract URLs to individual match pages.
      3. For each match page, parse the odds comparison table.
    """

    BASE_URL = 'https://www.oddschecker.com'

    def __init__(self):
        super().__init__(
            name='OddsChecker',
            base_url=self.BASE_URL,
            delay=2.0,              # Be polite — OddsChecker rate-limits aggressive scrapers
            use_cloudscraper=True,  # OddsChecker uses Cloudflare; cloudscraper bypasses 403s
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_odds(self, sports: Optional[List[str]] = None) -> List[OddsEntry]:
        sport_labels = (
            [SPORTS[k] for k in sports if k in SPORTS]
            if sports
            else list(ODDSCHECKER_SPORT_URLS.keys())
        )
        all_entries: List[OddsEntry] = []
        for label in sport_labels:
            if label not in ODDSCHECKER_SPORT_URLS:
                continue
            url = ODDSCHECKER_SPORT_URLS[label]
            message.log_debug("Scanning OddsChecker: {}".format(label), self.name)
            entries = self._scrape_sport(label, url)
            all_entries.extend(entries)
            message.log_debug("  {} entries for {}".format(len(entries), label), self.name)
        return all_entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scrape_sport(self, sport_label: str, listing_url: str) -> List[OddsEntry]:
        soup = self.get_soup(listing_url)
        if soup is None:
            return []

        event_links = self._extract_event_links(soup, listing_url)
        message.log_debug(
            "  Found {} events on {}".format(len(event_links), listing_url), self.name
        )

        entries: List[OddsEntry] = []
        for event_url, event_name in event_links[:20]:  # cap at 20 per sport per scan
            event_entries = self._scrape_event(event_url, event_name, sport_label)
            entries.extend(event_entries)
        return entries

    def _extract_event_links(
        self, soup: BeautifulSoup, base_url: str
    ) -> List[tuple]:
        """
        Return list of (url, event_name) from the sport listing page.
        OddsChecker wraps event links in <a> tags inside rows classed
        'evTabRow' or similar; we also fall back to href pattern matching.
        """
        links = []
        seen = set()

        # Primary: rows in the events table
        for row in soup.select('tr.evTabRow, tr.diff-row'):
            a = row.find('a', href=True)
            if a:
                href = a['href']
                name = a.get_text(strip=True)
                full_url = href if href.startswith('http') else self.BASE_URL + href
                if full_url not in seen and name:
                    seen.add(full_url)
                    links.append((full_url, name))

        # Fallback: any link whose path matches the sport sub-path
        if not links:
            sport_path = base_url.replace(self.BASE_URL, '').rstrip('/')
            for a in soup.find_all('a', href=re.compile(sport_path + r'/.+/winner')):
                href = a['href']
                name = a.get_text(strip=True)
                full_url = href if href.startswith('http') else self.BASE_URL + href
                if full_url not in seen and name:
                    seen.add(full_url)
                    links.append((full_url, name))

        return links

    def _scrape_event(
        self, event_url: str, event_name: str, sport_label: str
    ) -> List[OddsEntry]:
        """Fetch an individual event page and parse its odds table."""
        soup = self.get_soup(event_url)
        if soup is None:
            return []

        # Derive a stable event_id from the URL path
        event_id = 'oc:' + event_url.replace(self.BASE_URL, '').strip('/')

        # Commence time (OddsChecker shows it in a <span> or <td>)
        commence_time = self._extract_commence_time(soup)

        entries: List[OddsEntry] = []

        # The odds table has one row per outcome; bookmakers are columns
        # identified by data-bk attributes on <td> elements.
        odds_table = soup.find('table', id='oddsTableVS') or soup.find(
            'table', class_=re.compile(r'odds')
        )
        if odds_table is None:
            # Try alternate structure: individual bet rows
            entries.extend(
                self._parse_bet_rows(soup, event_id, event_name, commence_time, sport_label, event_url)
            )
            return entries

        for row in odds_table.find_all('tr'):
            outcome_cell = row.find('td', class_=re.compile(r'(bet-type|runner|selec)'))
            if outcome_cell is None:
                continue
            outcome = outcome_cell.get_text(strip=True)
            if not outcome:
                continue

            for td in row.find_all('td', attrs={'data-bk': True}):
                bk_code = td['data-bk']
                if bk_code not in ODDSCHECKER_CANADIAN_BOOKMAKERS:
                    continue
                bk_name = ODDSCHECKER_CANADIAN_BOOKMAKERS[bk_code]
                odds_str = td.get_text(strip=True)
                decimal = self._parse_odds(odds_str)
                if decimal is None:
                    continue
                link = td.find('a')
                bet_url = ''
                if link and link.get('href'):
                    bet_url = link['href']

                entries.append(
                    OddsEntry(
                        bookmaker=bk_name,
                        bookmaker_id=bk_code.lower(),
                        sport=sport_label,
                        event_id=event_id,
                        event_name=event_name,
                        commence_time=commence_time,
                        outcome=outcome,
                        decimal_odds=decimal,
                        url=bet_url or event_url,
                    )
                )
        return entries

    def _parse_bet_rows(
        self,
        soup: BeautifulSoup,
        event_id: str,
        event_name: str,
        commence_time: str,
        sport_label: str,
        event_url: str,
    ) -> List[OddsEntry]:
        """Fallback parser for pages without a standard odds table."""
        entries = []
        for row in soup.find_all(attrs={'data-bk': True}):
            bk_code = row.get('data-bk', '')
            if bk_code not in ODDSCHECKER_CANADIAN_BOOKMAKERS:
                continue
            bk_name = ODDSCHECKER_CANADIAN_BOOKMAKERS[bk_code]
            odds_str = row.get_text(strip=True)
            decimal = self._parse_odds(odds_str)
            if decimal is None:
                continue
            # Try to get outcome from a sibling or parent
            outcome = event_name  # default fallback
            entries.append(
                OddsEntry(
                    bookmaker=bk_name,
                    bookmaker_id=bk_code.lower(),
                    sport=sport_label,
                    event_id=event_id,
                    event_name=event_name,
                    commence_time=commence_time,
                    outcome=outcome,
                    decimal_odds=decimal,
                    url=event_url,
                )
            )
        return entries

    @staticmethod
    def _extract_commence_time(soup: BeautifulSoup) -> str:
        """Try to read the event date/time from the page."""
        for selector in ['span.date-time', 'div.event-date', '[class*="date"]']:
            el = soup.select_one(selector)
            if el:
                return el.get_text(strip=True)
        return ''

    @staticmethod
    def _parse_odds(odds_str: str) -> Optional[float]:
        """
        Convert an odds string to decimal odds.
        Handles fractional (e.g. '5/6', 'EVS'), decimal ('1.85'), and
        moneyline ('+150', '-120') formats.
        """
        odds_str = odds_str.strip().replace(',', '.')
        if not odds_str or odds_str in ('', '-', 'SP', 'N/A'):
            return None

        # Evens
        if odds_str.upper() in ('EVS', 'EVENS', 'EV'):
            return 2.0

        # Fractional: e.g. '5/6', '11/10'
        if '/' in odds_str:
            try:
                frac = Fraction(odds_str)
                return round(float(frac) + 1.0, 4)
            except (ValueError, ZeroDivisionError):
                return None

        # Moneyline American format
        if odds_str.startswith('+') or (odds_str.startswith('-') and odds_str[1:].isdigit()):
            try:
                ml = int(odds_str)
                if ml > 0:
                    return round(ml / 100.0 + 1.0, 4)
                else:
                    return round(100.0 / abs(ml) + 1.0, 4)
            except ValueError:
                return None

        # Decimal
        try:
            val = float(odds_str)
            return val if val > 1.0 else None
        except ValueError:
            return None
