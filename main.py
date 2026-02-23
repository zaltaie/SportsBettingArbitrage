"""
Canadian Sports Betting Arbitrage Tool
=======================================
Scans the top 10 Canadian sports betting sites for arbitrage opportunities
and prints guaranteed-profit bets to the console.

Top 10 Canadian sites covered
------------------------------
1.  Bet365            — via OddsChecker (direct probe as fallback)
2.  DraftKings        — via The Odds API + direct DraftKings API
3.  FanDuel           — via The Odds API + direct FanDuel API
4.  BetMGM            — via The Odds API + direct BetMGM API
5.  Sports Interaction — direct API / HTML scraper
6.  Betway            — direct API / HTML scraper
7.  PointsBet         — via The Odds API + direct PointsBet API
8.  theScore Bet      — direct API scraper
9.  BetRivers         — via The Odds API + Kambi (SBTech) API
10. Bodog             — direct Bodog published API

Usage
-----
    python main.py [--amount AMOUNT] [--sports SPORT [SPORT ...]] [--no-api]

Environment variables
---------------------
    ODDS_API_KEY   — Free key from https://the-odds-api.com (optional but recommended)

Quick start without an API key
--------------------------------
    python main.py --no-api

With an API key (broader coverage):
    ODDS_API_KEY=your_key python main.py
"""
import argparse
import sys
import time

from arbitrage import OddsEntry, scan_for_arbitrage, print_summary
from config import DEFAULT_BET_AMOUNT, SPORTS, ODDS_API_KEY
from message import message


def build_scrapers(use_api: bool):
    """Instantiate all scrapers. Import here to defer heavy imports."""
    scrapers = []

    # ------------------------------------------------------------------
    # Primary: The Odds API  (covers DraftKings, FanDuel, BetMGM,
    #                          PointsBet, BetRivers)
    # ------------------------------------------------------------------
    if use_api:
        if not ODDS_API_KEY:
            message.log_warning(
                "ODDS_API_KEY not set. Set it via the environment variable for "
                "best coverage of DraftKings, FanDuel, BetMGM, PointsBet, BetRivers.",
                "main",
            )
        from scrapers.odds_api import OddsAPIScraper
        scrapers.append(OddsAPIScraper())

    # ------------------------------------------------------------------
    # Secondary: OddsChecker  (covers Bet365, Sports Interaction, Betway,
    #                           Bodog, and most of the top 10)
    # ------------------------------------------------------------------
    from scrapers.oddschecker import OddsCheckerScraper
    scrapers.append(OddsCheckerScraper())

    # ------------------------------------------------------------------
    # Direct site scrapers  (supplement OddsChecker; each gracefully
    # returns [] if the site is unreachable or blocks access)
    # ------------------------------------------------------------------
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

    scrapers += [
        SportsInteractionScraper(),
        BodogScraper(),
        TheScoreScraper(),
        BetwayScraper(),
        BetRiversScraper(),
        Bet365Scraper(),
        DraftKingsScraper(),
        FanDuelScraper(),
        BetMGMScraper(),
        PointsBetScraper(),
    ]
    return scrapers


def collect_odds(scrapers, sport_keys):
    """Run every scraper and aggregate all OddsEntry objects."""
    all_odds = []
    for scraper in scrapers:
        message.log_debug("Running scraper: {}".format(scraper.name), "main")
        try:
            entries = scraper.get_odds(sport_keys)
            all_odds.extend(entries)
            message.log_debug(
                "  {} returned {} entries".format(scraper.name, len(entries)), "main"
            )
        except Exception as exc:
            message.log_error(
                "Scraper {} raised an unexpected error: {}".format(scraper.name, exc), "main"
            )
    return all_odds


def parse_args():
    parser = argparse.ArgumentParser(
        description='Canadian Sports Betting Arbitrage Scanner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--amount', '-a',
        type=float,
        default=None,
        help='Total stake in CAD (default: prompt at runtime)',
    )
    parser.add_argument(
        '--sports', '-s',
        nargs='+',
        choices=list(SPORTS.keys()),
        default=None,
        help='Sports to scan (default: all). E.g. --sports icehockey_nhl basketball_nba',
    )
    parser.add_argument(
        '--no-api',
        action='store_true',
        help='Skip The Odds API even if ODDS_API_KEY is set',
    )
    parser.add_argument(
        '--min-profit',
        type=float,
        default=None,
        help='Override minimum profit %% threshold (default from config)',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ---- Stake amount ----
    if args.amount is not None:
        stake = args.amount
    else:
        try:
            raw = input('Enter your total stake in CAD (default {:.0f}): '.format(
                DEFAULT_BET_AMOUNT
            )).strip()
            stake = float(raw) if raw else DEFAULT_BET_AMOUNT
        except (ValueError, KeyboardInterrupt):
            print('\nInvalid amount. Using default: ${:.2f}'.format(DEFAULT_BET_AMOUNT))
            stake = DEFAULT_BET_AMOUNT

    if stake <= 0:
        print('Stake must be positive. Using default: ${:.2f}'.format(DEFAULT_BET_AMOUNT))
        stake = DEFAULT_BET_AMOUNT

    # Override min profit if requested
    if args.min_profit is not None:
        import config as cfg
        cfg.MIN_PROFIT_PCT = args.min_profit

    sport_keys = args.sports  # None → all sports
    use_api = not args.no_api

    print('\n' + '=' * 64)
    print('Canadian Sports Betting Arbitrage Scanner')
    print('Stake: ${:.2f} CAD'.format(stake))
    sport_names = (
        [SPORTS[k] for k in sport_keys if k in SPORTS]
        if sport_keys else list(SPORTS.values())
    )
    print('Sports: {}'.format(', '.join(sport_names)))
    print('Data sources: OddsChecker + 10 direct site scrapers' +
          (' + The Odds API' if use_api else ''))
    print('=' * 64 + '\n')

    # Build scrapers and collect odds
    scrapers = build_scrapers(use_api)
    start = time.time()
    all_odds = collect_odds(scrapers, sport_keys)
    elapsed = time.time() - start

    print('\nCollected {} odds entries from {} scrapers in {:.1f}s'.format(
        len(all_odds), len(scrapers), elapsed
    ))

    if not all_odds:
        print('\nNo odds collected. Check your internet connection or try --no-api '
              'if The Odds API key is invalid.')
        sys.exit(0)

    # Detect arbitrage
    print('\nScanning for arbitrage opportunities…')
    opportunities = scan_for_arbitrage(all_odds, stake)
    print_summary(opportunities)


if __name__ == '__main__':
    main()
