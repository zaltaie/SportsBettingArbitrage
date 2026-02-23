"""
Core arbitrage detection engine.

Arbitrage in sports betting occurs when the combined implied probabilities
across bookmakers sum to less than 1.0, guaranteeing a risk-free profit
regardless of the outcome.

Condition:  sum(1 / odds_i  for each outcome i) < 1.0
Profit %:   (1 - sum_of_implied_probs) * 100
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from config import MIN_PROFIT_PCT, MAX_PROFIT_PCT
from message import message


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class OddsEntry:
    """A single odds offering from one bookmaker for one outcome."""
    bookmaker: str        # e.g. "Bet365"
    bookmaker_id: str     # e.g. "bet365"
    sport: str            # e.g. "NHL"
    event_id: str         # Unique event identifier
    event_name: str       # e.g. "Toronto Maple Leafs vs Montreal Canadiens"
    commence_time: str    # ISO-8601 string
    outcome: str          # e.g. "Toronto Maple Leafs"
    decimal_odds: float   # e.g. 1.85
    url: str = ''


@dataclass
class ArbitrageOpportunity:
    """A confirmed arbitrage opportunity across multiple bookmakers."""
    event_name: str
    sport: str
    commence_time: str
    best_offers: Dict[str, OddsEntry]   # outcome -> best OddsEntry
    total_stake: float
    profit: float
    profit_pct: float
    stakes: Dict[str, float]            # outcome -> stake amount
    returns: Dict[str, float]           # outcome -> guaranteed return


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _implied_prob(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 1.0:
        return 1.0
    return 1.0 / decimal_odds


def find_arbitrage(
    event_name: str,
    sport: str,
    commence_time: str,
    outcomes: Dict[str, List[OddsEntry]],
    total_stake: float,
) -> Optional[ArbitrageOpportunity]:
    """
    Check a single event for an arbitrage opportunity.

    Parameters
    ----------
    outcomes : {outcome_label: [OddsEntry, ...]}
        All available odds grouped by outcome label.
    total_stake : float
        Total amount to wager in CAD.

    Returns
    -------
    ArbitrageOpportunity if one exists, otherwise None.
    """
    if len(outcomes) < 2:
        return None

    # Pick the best (highest) odds for each outcome
    best: Dict[str, OddsEntry] = {}
    for label, entries in outcomes.items():
        if not entries:
            continue
        best[label] = max(entries, key=lambda e: e.decimal_odds)

    if len(best) < 2:
        return None

    # Arbitrage condition
    total_implied = sum(_implied_prob(e.decimal_odds) for e in best.values())
    if total_implied >= 1.0:
        return None

    profit_pct = (1.0 - total_implied) * 100.0

    # Sanity check — very high profit % usually means data error
    if profit_pct < MIN_PROFIT_PCT or profit_pct > MAX_PROFIT_PCT:
        if profit_pct > MAX_PROFIT_PCT:
            message.log_warning(
                "Skipping apparent arb of {:.1f}% — likely bad data ({})".format(
                    profit_pct, event_name
                )
            )
        return None

    # Optimal stakes: stake_i = total * (implied_i / total_implied)
    stakes: Dict[str, float] = {}
    returns: Dict[str, float] = {}
    for label, entry in best.items():
        imp = _implied_prob(entry.decimal_odds)
        stake = total_stake * (imp / total_implied)
        stakes[label] = round(stake, 2)
        returns[label] = round(stake * entry.decimal_odds, 2)

    profit = round(total_stake * (1.0 - total_implied), 2)

    return ArbitrageOpportunity(
        event_name=event_name,
        sport=sport,
        commence_time=commence_time,
        best_offers=best,
        total_stake=total_stake,
        profit=profit,
        profit_pct=round(profit_pct, 3),
        stakes=stakes,
        returns=returns,
    )


def scan_for_arbitrage(
    all_odds: List[OddsEntry],
    total_stake: float,
) -> List[ArbitrageOpportunity]:
    """
    Group all collected odds by event, then scan each event for arb.

    Events from different scrapers are matched on event_id first; if both
    scrapers agree on the same event_id (e.g. from The Odds API), matching
    is exact. OddsChecker-sourced entries use the event name as the key.

    Returns a list of ArbitrageOpportunity objects sorted by profit %.
    """
    # Group: event_id -> outcome -> [OddsEntry]
    event_map: Dict[str, Dict[str, List[OddsEntry]]] = {}
    event_meta: Dict[str, tuple] = {}  # event_id -> (name, sport, time)

    for entry in all_odds:
        if entry.decimal_odds <= 1.0:
            continue
        eid = entry.event_id
        if eid not in event_map:
            event_map[eid] = {}
            event_meta[eid] = (entry.event_name, entry.sport, entry.commence_time)
        outcome_map = event_map[eid]
        if entry.outcome not in outcome_map:
            outcome_map[entry.outcome] = []
        outcome_map[entry.outcome].append(entry)

    opportunities: List[ArbitrageOpportunity] = []
    for eid, outcomes in event_map.items():
        name, sport, time = event_meta[eid]
        opp = find_arbitrage(name, sport, time, outcomes, total_stake)
        if opp:
            opportunities.append(opp)
            message.log_result("ARB FOUND: {} — {:.3f}%".format(name, opp.profit_pct))

    opportunities.sort(key=lambda o: o.profit_pct, reverse=True)
    return opportunities


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_opportunity(opp: ArbitrageOpportunity) -> str:
    """Return a human-readable string describing the opportunity."""
    sep = '=' * 64
    lines = [
        '',
        sep,
        'ARBITRAGE OPPORTUNITY',
        'Event  : {}'.format(opp.event_name),
        'Sport  : {}'.format(opp.sport),
        'Time   : {}'.format(opp.commence_time),
        'Profit : ${:.2f}  ({:.3f}%)'.format(opp.profit, opp.profit_pct),
        'Stake  : ${:.2f} total'.format(opp.total_stake),
        '',
        'Bets to place:',
    ]
    for outcome, entry in opp.best_offers.items():
        stake = opp.stakes[outcome]
        ret = opp.returns[outcome]
        lines.append(
            '  [{bk}] {out} @ {odds}  —  stake ${stake:.2f}  →  return ${ret:.2f}'.format(
                bk=entry.bookmaker,
                out=outcome,
                odds=entry.decimal_odds,
                stake=stake,
                ret=ret,
            )
        )
        if entry.url:
            lines.append('    {}'.format(entry.url))
    lines.append(sep)
    return '\n'.join(lines)


def print_summary(opportunities: List[ArbitrageOpportunity]) -> None:
    """Print all found opportunities to stdout."""
    if not opportunities:
        print('\nNo arbitrage opportunities found in this scan.')
        return
    print('\nFound {} arbitrage opportunity/ies:\n'.format(len(opportunities)))
    for opp in opportunities:
        print(format_opportunity(opp))
