"""
Scrapers for Canadian sports betting sites.

Each scraper implements get_odds(sports) and returns a list of OddsEntry
objects that the arbitrage engine can process.

Data sources
------------
Primary   : The Odds API  — covers DraftKings, FanDuel, BetMGM, PointsBet, BetRivers
Secondary : OddsChecker   — covers Bet365, Sports Interaction, Betway, Bodog
Direct    : Per-site scrapers for Sports Interaction, Bodog, theScore Bet,
            Betway, and BetRivers (used when OddsChecker lacks coverage).
"""

from scrapers.odds_api import OddsAPIScraper
from scrapers.oddschecker import OddsCheckerScraper
from scrapers.sports_interaction import SportsInteractionScraper
from scrapers.bodog import BodogScraper
from scrapers.thescore import TheScoreScraper
from scrapers.betway import BetwayScraper
from scrapers.betrivers import BetRiversScraper
from scrapers.bet365 import Bet365Scraper
from scrapers.draftkings import DraftKingsScraper
from scrapers.fanduel import FanDuelScraper
from scrapers.betmgm import BetMGMScraper
from scrapers.pointsbet import PointsBetScraper

__all__ = [
    'OddsAPIScraper',
    'OddsCheckerScraper',
    'SportsInteractionScraper',
    'BodogScraper',
    'TheScoreScraper',
    'BetwayScraper',
    'BetRiversScraper',
    'Bet365Scraper',
    'DraftKingsScraper',
    'FanDuelScraper',
    'BetMGMScraper',
    'PointsBetScraper',
]
