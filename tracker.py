"""
SQLite-backed arbitrage opportunity tracker and daily P&L reporter.

Every new opportunity found by the scanner is automatically logged to
arb_history.db in the project directory.  Use the CLI to view summaries:

    python tracker.py --report            # today's P&L
    python tracker.py --report --days 7   # last 7 days
    python tracker.py --report --days 30  # monthly summary

The report shows opportunities per sport / market type, total profit in CAD,
average margin, and the book pairs generating the most arbs — useful for
deciding where to concentrate capital.
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arbitrage import ArbitrageOpportunity

DB_PATH = Path(__file__).parent / 'arb_history.db'

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS opportunities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    event_name  TEXT    NOT NULL,
    sport       TEXT    NOT NULL,
    market_type TEXT    NOT NULL DEFAULT 'moneyline',
    books       TEXT    NOT NULL,
    profit_pct  REAL    NOT NULL,
    stake       REAL    NOT NULL,
    profit_cad  REAL    NOT NULL
);
"""


class Tracker:
    """Records each new arbitrage opportunity to a local SQLite database."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_CREATE_TABLE)

    def record(self, opp: 'ArbitrageOpportunity') -> None:
        """Persist one opportunity to the database."""
        books = '+'.join(sorted(e.bookmaker_id for e in opp.best_offers.values()))
        market_type = getattr(opp, 'market_type', 'moneyline')
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO opportunities
                   (timestamp, event_name, sport, market_type, books,
                    profit_pct, stake, profit_cad)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    datetime.utcnow().isoformat(),
                    opp.event_name,
                    opp.sport,
                    market_type,
                    books,
                    opp.profit_pct,
                    opp.total_stake,
                    opp.profit,
                ),
            )

    def daily_report(self, days: int = 1) -> None:
        """Print a formatted P&L summary to stdout."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT date(timestamp, 'localtime') as day,
                          sport,
                          market_type,
                          count(*)          as opps,
                          sum(profit_cad)   as total_profit,
                          avg(profit_pct)   as avg_pct,
                          max(profit_pct)   as max_pct,
                          group_concat(DISTINCT books) as book_pairs
                   FROM opportunities
                   WHERE date(timestamp, 'localtime') >= date('now', '-{} days')
                   GROUP BY day, sport, market_type
                   ORDER BY day DESC, total_profit DESC""".format(days)
            ).fetchall()

        if not rows:
            print('No opportunities recorded in the last {} day(s).'.format(days))
            print('Database: {}'.format(self.db_path))
            return

        col = '{:<12} {:<6} {:<12} {:>5} {:>12} {:>8} {:>8}'
        print('\n' + '=' * 72)
        print('Arbitrage P&L Report  —  last {} day(s)'.format(days))
        print('=' * 72)
        print(col.format('Date', 'Sport', 'Market', 'Opps', 'Profit CAD', 'Avg %', 'Max %'))
        print('-' * 72)

        total_profit = 0.0
        total_opps = 0
        for row in rows:
            day, sport, mtype, opps, profit, avg_pct, max_pct, _books = row
            profit = profit or 0.0
            print(col.format(
                day, sport, mtype, opps,
                '${:.2f}'.format(profit),
                '{:.3f}%'.format(avg_pct or 0),
                '{:.3f}%'.format(max_pct or 0),
            ))
            total_profit += profit
            total_opps += opps

        print('-' * 72)
        print(col.format('TOTAL', '', '', total_opps, '${:.2f}'.format(total_profit), '', ''))
        print('=' * 72)
        print('\nDatabase: {}'.format(self.db_path))

    def top_book_pairs(self, days: int = 7, limit: int = 10) -> None:
        """Print the book pairs generating the most arbs over the last *days* days."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT books,
                          count(*)        as opps,
                          sum(profit_cad) as total_profit,
                          avg(profit_pct) as avg_pct
                   FROM opportunities
                   WHERE date(timestamp, 'localtime') >= date('now', '-{} days')
                   GROUP BY books
                   ORDER BY total_profit DESC
                   LIMIT {}""".format(days, limit)
            ).fetchall()

        if not rows:
            print('No data for the last {} days.'.format(days))
            return

        col = '{:<40} {:>5} {:>12} {:>8}'
        print('\n' + '=' * 68)
        print('Top book pairs  —  last {} day(s)'.format(days))
        print('=' * 68)
        print(col.format('Books', 'Opps', 'Profit CAD', 'Avg %'))
        print('-' * 68)
        for books, opps, profit, avg_pct in rows:
            print(col.format(
                books[:40], opps,
                '${:.2f}'.format(profit or 0),
                '{:.3f}%'.format(avg_pct or 0),
            ))
        print('=' * 68 + '\n')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='Arbitrage P&L report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--report', action='store_true',
                   help='Print daily P&L summary')
    p.add_argument('--pairs', action='store_true',
                   help='Print top book-pair rankings')
    p.add_argument('--days', type=int, default=1,
                   help='Number of days to include (default: 1)')
    return p.parse_args()


if __name__ == '__main__':
    args = _parse_args()
    t = Tracker()
    if args.report:
        t.daily_report(args.days)
    elif args.pairs:
        t.top_book_pairs(args.days)
    else:
        print('Usage:')
        print('  python tracker.py --report           # today\'s P&L')
        print('  python tracker.py --report --days 7  # last 7 days')
        print('  python tracker.py --pairs  --days 7  # top book pairs')
