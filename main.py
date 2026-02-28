"""
Canadian Sports Betting Arbitrage Tool
=======================================
Scans the top 10 Canadian sports betting sites for arbitrage opportunities
and displays guaranteed-profit bet instructions in the terminal.

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
    python main.py [--amount AMOUNT] [--sports SPORT ...] [--watch] [--notify]

Environment variables
---------------------
    ODDS_API_KEY   — Free key from https://the-odds-api.com (optional but recommended)

Quick start:
    python main.py                       # single scan, prompt for stake
    python main.py --amount 250          # single scan, $250 stake
    python main.py --watch               # continuous mode, re-scan every 60s
    python main.py --watch --notify      # continuous mode + desktop alerts
    python main.py --no-api              # skip The Odds API, direct scrapers only
"""
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set

from arbitrage import OddsEntry, scan_for_arbitrage, kelly_stake, rescale_opportunity
from config import DEFAULT_BET_AMOUNT, SPORTS, ODDS_API_KEY, WATCH_INTERVAL
from tracker import Tracker
from display import print_rich_dashboard, print_scraper_health
from message import message


# ---------------------------------------------------------------------------
# Scraper construction
# ---------------------------------------------------------------------------

def build_scrapers(use_api: bool):
    """Instantiate all scrapers. Imports are deferred to keep startup fast."""
    scrapers = []

    # Primary: The Odds API (covers DraftKings, FanDuel, BetMGM, PointsBet, BetRivers)
    if use_api:
        if not ODDS_API_KEY:
            message.log_warning(
                'ODDS_API_KEY not set. Set it via the environment variable for '
                'best coverage of DraftKings, FanDuel, BetMGM, PointsBet, BetRivers.',
                'main',
            )
        from scrapers.odds_api import OddsAPIScraper
        scrapers.append(OddsAPIScraper())

    # Secondary: OddsChecker (covers Bet365, Sports Interaction, Betway, Bodog, top-10)
    from scrapers.oddschecker import OddsCheckerScraper
    scrapers.append(OddsCheckerScraper())

    # Direct site scrapers (supplement OddsChecker; gracefully return [] if blocked)
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


# ---------------------------------------------------------------------------
# Parallel odds collection
# ---------------------------------------------------------------------------

def _run_scraper(scraper, sport_keys):
    """Worker: run one scraper and return (name, entries, error)."""
    try:
        entries = scraper.get_odds(sport_keys)
        return scraper.name, entries, None
    except Exception as exc:
        return scraper.name, [], exc


def collect_odds_parallel(scrapers, sport_keys):
    """
    Run all scrapers concurrently in a thread pool.
    Returns (all_odds, health) where health is a list of dicts:
      [{'name': str, 'count': int, 'error': Exception|None}, ...]

    Using threads (not asyncio) because the scrapers use the blocking
    `requests` library. All scrapers fire at the same time — 5-10x faster
    than sequential collection.
    """
    all_odds = []
    health = []
    with ThreadPoolExecutor(max_workers=len(scrapers)) as pool:
        futures = {
            pool.submit(_run_scraper, scraper, sport_keys): scraper.name
            for scraper in scrapers
        }
        for future in as_completed(futures):
            name, entries, error = future.result()
            health.append({'name': name, 'count': len(entries), 'error': error})
            if error:
                message.log_error(
                    'Scraper {} raised: {}'.format(name, error), 'main'
                )
            else:
                message.log_debug(
                    '{} returned {} entries'.format(name, len(entries)), 'main'
                )
                all_odds.extend(entries)
    # Sort health by name for consistent display
    health.sort(key=lambda h: h['name'])
    return all_odds, health


# ---------------------------------------------------------------------------
# Deduplication across watch-mode scans
# ---------------------------------------------------------------------------

def _opp_key(opp) -> str:
    """Stable string key for an opportunity — used to detect new vs seen."""
    books = '+'.join(sorted(e.bookmaker_id for e in opp.best_offers.values()))
    return '{}:{}:{}:{}'.format(opp.event_name, opp.sport, opp.market_type, books)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

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
    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Continuous mode: re-scan every --interval seconds until Ctrl+C',
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=WATCH_INTERVAL,
        metavar='SECONDS',
        help='Seconds between scans in --watch mode (default: {})'.format(WATCH_INTERVAL),
    )
    parser.add_argument(
        '--notify', '-n',
        action='store_true',
        help='Send desktop/terminal notification when a NEW opportunity is found',
    )
    parser.add_argument(
        '--kelly',
        type=float,
        default=None,
        metavar='FRACTION',
        help=(
            'Kelly criterion fraction (0.0–1.0). Requires --bankroll. '
            'Stake = bankroll × profit_pct × fraction. '
            'Use 0.5 for half-Kelly (recommended). Overrides --amount.'
        ),
    )
    parser.add_argument(
        '--bankroll',
        type=float,
        default=None,
        metavar='AMOUNT',
        help='Total available bankroll in CAD (used with --kelly for dynamic staking)',
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # ---- Stake amount ----
    if args.amount is not None:
        stake = args.amount
    else:
        try:
            raw = input(
                'Enter your total stake in CAD (default {:.0f}): '.format(DEFAULT_BET_AMOUNT)
            ).strip()
            stake = float(raw) if raw else DEFAULT_BET_AMOUNT
        except (ValueError, KeyboardInterrupt):
            print('\nInvalid amount. Using default: ${:.2f}'.format(DEFAULT_BET_AMOUNT))
            stake = DEFAULT_BET_AMOUNT

    if stake <= 0:
        print('Stake must be positive. Using default: ${:.2f}'.format(DEFAULT_BET_AMOUNT))
        stake = DEFAULT_BET_AMOUNT

    # ---- Override min-profit if requested ----
    if args.min_profit is not None:
        import config as cfg
        cfg.MIN_PROFIT_PCT = args.min_profit

    sport_keys = args.sports      # None → all sports
    use_api = not args.no_api

    sport_names = (
        [SPORTS[k] for k in sport_keys if k in SPORTS]
        if sport_keys else list(SPORTS.values())
    )

    # ---- Validate Kelly args ----
    use_kelly = args.kelly is not None
    if use_kelly and args.bankroll is None:
        print('ERROR: --kelly requires --bankroll. Example: --kelly 0.5 --bankroll 10000')
        sys.exit(1)
    if use_kelly and not (0.0 < args.kelly <= 1.0):
        print('ERROR: --kelly must be between 0.0 (exclusive) and 1.0 (inclusive).')
        sys.exit(1)

    print('\n' + '=' * 64)
    print('Canadian Sports Betting Arbitrage Scanner')
    if use_kelly:
        print('Staking    : Kelly {:.0f}%  (bankroll ${:,.2f} CAD)'.format(
            args.kelly * 100, args.bankroll
        ))
    else:
        print('Stake      : ${:.2f} CAD'.format(stake))
    print('Sports     : {}'.format(', '.join(sport_names)))
    print('Markets    : Moneyline + Point Spreads + Totals (Over/Under)')
    print('Sources    : OddsChecker + 10 direct site scrapers' +
          (' + The Odds API' if use_api else ''))
    print('Mode       : {}'.format(
        'WATCH (every {}s)'.format(args.interval) if args.watch else 'Single scan'
    ))
    if args.notify:
        print('Notify     : Desktop alerts ON')
    print('Tracking   : arb_history.db  (python tracker.py --report)')
    print('=' * 64 + '\n')

    # ---- Initialise tracker (always on) ----
    tracker = Tracker()

    # ---- Build scrapers once (reused across watch-mode iterations) ----
    scrapers = build_scrapers(use_api)

    seen_keys: Set[str] = set()
    scan_count = 0

    while True:
        scan_count += 1
        print('\nScanning... ({} scrapers running in parallel)'.format(len(scrapers)))

        start = time.time()
        all_odds, health = collect_odds_parallel(scrapers, sport_keys)
        elapsed = time.time() - start

        message.log_debug(
            'Collected {} odds entries in {:.1f}s'.format(len(all_odds), elapsed), 'main'
        )

        # Always show scraper health so user knows which sources are working
        print_scraper_health(health)

        if not all_odds:
            print('\nNo odds collected. Check your internet connection or try '
                  '--no-api if The Odds API key is invalid.')
            if not args.watch:
                sys.exit(0)
        else:
            # ---- Detect arbitrage ----
            # For Kelly mode: scan with unit stake=1.0, then rescale per opp.
            scan_stake = 1.0 if use_kelly else stake
            opportunities = scan_for_arbitrage(all_odds, scan_stake)

            # ---- Apply Kelly sizing (per-opportunity dynamic stakes) ----
            if use_kelly:
                sized = []
                for opp in opportunities:
                    k_stake = kelly_stake(opp.profit_pct, args.bankroll, args.kelly)
                    sized.append(rescale_opportunity(opp, k_stake))
                opportunities = sized

            # ---- Identify genuinely new opportunities ----
            new_opps = [o for o in opportunities if _opp_key(o) not in seen_keys]
            for o in new_opps:
                seen_keys.add(_opp_key(o))

            # ---- Record new opportunities in the tracker ----
            for o in new_opps:
                tracker.record(o)

            # ---- Desktop / terminal notifications ----
            if args.notify and new_opps:
                from notify import alert_new_opportunity
                for o in new_opps:
                    alert_new_opportunity(o.event_name, o.profit, o.profit_pct, o.sport)

            # ---- Rich dashboard ----
            print_rich_dashboard(
                opportunities,
                scan_count=scan_count,
                elapsed=elapsed,
                total_odds=len(all_odds),
                new_count=len(new_opps),
            )

        # ---- Single-scan mode: exit after one pass ----
        if not args.watch:
            break

        # ---- Watch mode: countdown to next scan ----
        print('\nNext scan in {}s...  (Ctrl+C to stop)\n'.format(args.interval))
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print('\nStopped. Goodbye.')
            break


if __name__ == '__main__':
    main()
