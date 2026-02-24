"""
Rich terminal display for the Canadian Arbitrage Scanner.

Provides:
  - print_rich_dashboard()  — summary table + step-by-step bet cards
  - format_step_instructions() — plain-text step format (rich fallback)
"""
import sys
from datetime import datetime, timezone
from typing import List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import lazily to avoid circular issues at module level
# (ArbitrageOpportunity is used in type hints only at runtime)

SPORT_EMOJI = {
    'NHL': '\U0001f3d2',   # 🏒
    'NBA': '\U0001f3c0',   # 🏀
    'NFL': '\U0001f3c8',   # 🏈
    'MLB': '\u26be',       # ⚾
    'MLS': '\u26bd',       # ⚽
    'CFL': '\U0001f3c8',   # 🏈
}

_console = Console() if RICH_AVAILABLE else None


# ---------------------------------------------------------------------------
# Plain-text step-by-step format  (used as rich fallback and in arbitrage.py)
# ---------------------------------------------------------------------------

def format_step_instructions(opp) -> str:
    """Return plain-text numbered step instructions for one opportunity."""
    sep = '=' * 64
    sport_icon = SPORT_EMOJI.get(opp.sport, '')
    lines = [
        '',
        sep,
        'ARBITRAGE OPPORTUNITY  --  {} {}'.format(sport_icon, opp.sport),
        'Event  : {}'.format(opp.event_name),
        'Time   : {}'.format(_fmt_time(opp.commence_time)),
        '',
    ]

    for step, (outcome, entry) in enumerate(opp.best_offers.items(), 1):
        stake = opp.stakes[outcome]
        lines.append('STEP {} -> Open {} (tap to open)'.format(step, entry.bookmaker))
        if entry.url:
            lines.append('         {}'.format(entry.url))
        lines.append(
            '         Bet ${:.2f} on {} @ {}'.format(stake, outcome, entry.decimal_odds)
        )
        lines.append('')

    lines += [
        'Guaranteed profit: ${:.2f}  ({:.2f}%)'.format(opp.profit, opp.profit_pct),
        'Total stake: ${:.2f} CAD'.format(opp.total_stake),
        '!! Place ALL bets within 2 minutes !!',
        sep,
    ]
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Rich dashboard
# ---------------------------------------------------------------------------

def print_rich_dashboard(
    opportunities: list,
    scan_count: int = 1,
    elapsed: float = 0.0,
    total_odds: int = 0,
    new_count: int = 0,
) -> None:
    """
    Print the full rich dashboard:
      1. Header panel with scan stats
      2. Summary table of all opportunities
      3. Detailed step-by-step bet cards
    Falls back to plain text when rich is not installed.
    """
    if not RICH_AVAILABLE:
        _plain_dashboard(opportunities, scan_count, elapsed, total_odds, new_count)
        return

    timestamp = datetime.now().strftime('%Y-%m-%d  %H:%M:%S')

    # ---- Header ----
    header = Text()
    header.append('  Canadian Sports Betting Arbitrage Scanner\n', style='bold cyan')
    header.append(
        '  Scan #{} | {} | {:.1f}s | {} odds entries collected'.format(
            scan_count, timestamp, elapsed, total_odds
        ),
        style='dim',
    )
    if new_count > 0:
        header.append(
            '   [{} NEW opportunity{}]'.format(
                new_count, 'ies' if new_count > 1 else ''
            ),
            style='bold bright_green',
        )
    _console.print(Panel(header, box=box.DOUBLE_EDGE, padding=(0, 1)))

    if not opportunities:
        _console.print(
            '\n[yellow]  No arbitrage opportunities found this scan.[/yellow]\n'
        )
        return

    # ---- Summary table ----
    table = Table(
        title='[bold]Opportunities — sorted by profit[/bold]',
        box=box.ROUNDED,
        show_lines=True,
        header_style='bold magenta',
        min_width=80,
    )
    table.add_column('#',        style='dim',           width=3)
    table.add_column('Sport',                           width=7)
    table.add_column('Event',   min_width=28)
    table.add_column('Profit',  justify='right',        width=9,  style='bold green')
    table.add_column('%',       justify='right',        width=7,  style='bold green')
    table.add_column('Books',   min_width=22)
    table.add_column('Starts',                          width=18)

    for i, opp in enumerate(opportunities, 1):
        books_str = ' / '.join(e.bookmaker for e in opp.best_offers.values())
        sport_str = '{} {}'.format(SPORT_EMOJI.get(opp.sport, ''), opp.sport)
        pstyle = 'bold bright_green' if opp.profit_pct >= 2.0 else 'green'
        table.add_row(
            str(i),
            sport_str,
            opp.event_name,
            '[{}]${:.2f}[/{}]'.format(pstyle, opp.profit, pstyle),
            '[{}]{:.2f}%[/{}]'.format(pstyle, opp.profit_pct, pstyle),
            books_str,
            _fmt_time(opp.commence_time),
        )

    _console.print(table)

    # ---- Step-by-step cards ----
    _console.print()
    _console.rule('[bold cyan]Step-by-Step Bet Instructions[/bold cyan]')
    _console.print()
    for i, opp in enumerate(opportunities, 1):
        _print_rich_card(opp, i)


def _print_rich_card(opp, num: int) -> None:
    """Render one opportunity as a rich bet-instruction card."""
    sport_icon = SPORT_EMOJI.get(opp.sport, '')
    pstyle = 'bright_green' if opp.profit_pct >= 2.0 else 'green'
    title = (
        '[bold]#{} — {} {} — '
        '[{}]${:.2f} guaranteed profit  ({:.2f}%)[/{}][/bold]'
    ).format(num, sport_icon, opp.event_name, pstyle, opp.profit, opp.profit_pct, pstyle)

    lines = []
    for step, (outcome, entry) in enumerate(opp.best_offers.items(), 1):
        stake = opp.stakes[outcome]
        lines.append(
            '[bold cyan]STEP {}[/bold cyan] [dim]->[/dim] '
            '[bold white]Open {}[/bold white]  [dim](tap to open)[/dim]'.format(
                step, entry.bookmaker
            )
        )
        if entry.url:
            lines.append(
                '         [link={url}][blue]{url}[/blue][/link]'.format(url=entry.url)
            )
        lines.append(
            '         Bet [bold yellow]${:.2f}[/bold yellow]'
            ' on [italic]{}[/italic]'
            ' @ [bold white]{:.2f}[/bold white]'.format(
                stake, outcome, entry.decimal_odds
            )
        )
        lines.append('')

    lines.append(
        '[bold {}]Guaranteed profit: ${:.2f}  ({:.2f}%)[/bold {}]'.format(
            pstyle, opp.profit, opp.profit_pct, pstyle
        )
    )
    lines.append('[dim]Total stake: ${:.2f} CAD[/dim]'.format(opp.total_stake))
    lines.append('[bold red]Place ALL bets within 2 minutes.[/bold red]')

    border = 'bright_green' if opp.profit_pct >= 2.0 else 'yellow'
    _console.print(
        Panel('\n'.join(lines), title=title, border_style=border, padding=(1, 2))
    )
    _console.print()


# ---------------------------------------------------------------------------
# Scraper health summary
# ---------------------------------------------------------------------------

def print_scraper_health(health: list) -> None:
    """
    Print a compact table showing which scrapers succeeded, returned 0 entries,
    or failed with an error. Helps users understand which data sources are live.

    health: list of {'name': str, 'count': int, 'error': Exception|None}
    """
    if not health:
        return

    if RICH_AVAILABLE:
        table = Table(
            title='[bold]Scraper Health[/bold]',
            box=box.SIMPLE,
            show_header=True,
            header_style='bold dim',
            min_width=52,
        )
        table.add_column('Source',  min_width=20)
        table.add_column('Status',  width=10, justify='center')
        table.add_column('Entries', width=8,  justify='right')
        table.add_column('Note',    min_width=14)

        for h in health:
            err = h['error']
            count = h['count']
            if err is not None:
                err_str = str(err)
                if 'NameResolution' in err_str or 'resolve' in err_str.lower():
                    note = 'DNS fail — geo-blocked?'
                    status = '[bold red]DNS ERR[/bold red]'
                elif 'SSL' in err_str or 'ssl' in err_str:
                    note = 'TLS mismatch'
                    status = '[bold red]SSL ERR[/bold red]'
                elif '403' in err_str:
                    note = 'Bot-blocked (403)'
                    status = '[bold red]BLOCKED[/bold red]'
                else:
                    note = err_str[:30]
                    status = '[bold red]ERROR[/bold red]'
                count_str = '[dim]-[/dim]'
            elif count == 0:
                status = '[yellow]EMPTY[/yellow]'
                note = 'No odds returned'
                count_str = '[yellow]0[/yellow]'
            else:
                status = '[green]OK[/green]'
                note = ''
                count_str = '[green]{}[/green]'.format(count)

            table.add_row(h['name'], status, count_str, note)

        _console.print(table)
    else:
        # Plain fallback
        print('\nScraper Health:')
        for h in health:
            err = h['error']
            if err is not None:
                print('  FAIL  {} — {}'.format(h['name'], str(err)[:60]))
            elif h['count'] == 0:
                print('  EMPTY {}'.format(h['name']))
            else:
                print('  OK    {} ({} entries)'.format(h['name'], h['count']))
        print()


# ---------------------------------------------------------------------------
# Plain-text fallback
# ---------------------------------------------------------------------------

def _plain_dashboard(opportunities, scan_count, elapsed, total_odds, new_count):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print('\n' + '=' * 64)
    print('Canadian Sports Betting Arbitrage Scanner')
    print('Scan #{} | {} | {:.1f}s | {} odds entries'.format(
        scan_count, timestamp, elapsed, total_odds
    ))
    if new_count > 0:
        print('*** {} NEW opportunity/ies ***'.format(new_count))
    print('=' * 64)

    if not opportunities:
        print('\nNo arbitrage opportunities found this scan.\n')
        return

    print('\nFound {} opportunity/ies:\n'.format(len(opportunities)))
    for opp in opportunities:
        print(format_step_instructions(opp))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_time(time_str: str) -> str:
    """Convert ISO-8601 to a short human-readable string."""
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime('%b %d  %I:%M %p')
    except Exception:
        return time_str
