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
    outcome: str          # e.g. "Toronto Maple Leafs" / "Lakers -3.5" / "Over 220.5"
    decimal_odds: float   # e.g. 1.85
    url: str = ''
    market_type: str = 'moneyline'   # 'moneyline' | 'spread' | 'total'
    line: Optional[float] = None     # Point spread or total line number (None for moneyline)


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
    market_type: str = 'moneyline'      # 'moneyline' | 'spread' | 'total'


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
    market_type: str = 'moneyline',
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
        market_type=market_type,
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
    # Group: composite_key -> outcome -> [OddsEntry]
    # Key = "{event_id}:{market_type}:{abs_line}" so spread/total arbs are
    # checked independently from moneyline, and different lines don't cross.
    event_map: Dict[str, Dict[str, List[OddsEntry]]] = {}
    event_meta: Dict[str, tuple] = {}  # key -> (name, sport, time, market_type)

    for entry in all_odds:
        if entry.decimal_odds <= 1.0:
            continue
        line_key = '{:.1f}'.format(abs(entry.line)) if entry.line is not None else ''
        eid = '{}:{}:{}'.format(entry.event_id, entry.market_type, line_key)
        if eid not in event_map:
            event_map[eid] = {}
            event_meta[eid] = (
                entry.event_name, entry.sport, entry.commence_time, entry.market_type
            )
        outcome_map = event_map[eid]
        if entry.outcome not in outcome_map:
            outcome_map[entry.outcome] = []
        outcome_map[entry.outcome].append(entry)

    opportunities: List[ArbitrageOpportunity] = []
    for eid, outcomes in event_map.items():
        name, sport, time, mtype = event_meta[eid]
        opp = find_arbitrage(name, sport, time, outcomes, total_stake, mtype)
        if opp:
            opportunities.append(opp)
            message.log_result("ARB FOUND: {} — {:.3f}%".format(name, opp.profit_pct))

    opportunities.sort(key=lambda o: o.profit_pct, reverse=True)
    return opportunities


# ---------------------------------------------------------------------------
# Kelly criterion staking
# ---------------------------------------------------------------------------

def kelly_stake(profit_pct: float, bankroll: float, fraction: float = 1.0) -> float:
    """
    Compute the optimal Kelly stake for a guaranteed-profit arbitrage.

    For arbs the 'win probability' is 1.0, so Kelly reduces to:
        stake = bankroll * (profit_pct / 100) * fraction

    Parameters
    ----------
    profit_pct : float
        The arbitrage profit percentage (e.g. 0.8 for 0.8%).
    bankroll : float
        Total available capital in CAD.
    fraction : float
        Kelly fraction — 1.0 = full Kelly, 0.5 = half-Kelly (more conservative).

    Returns
    -------
    Optimal stake in CAD (always positive; floored at 0).
    """
    return max(0.0, round(bankroll * (profit_pct / 100.0) * fraction, 2))


def rescale_opportunity(opp: ArbitrageOpportunity, new_stake: float) -> ArbitrageOpportunity:
    """Return a copy of *opp* with all dollar amounts scaled to *new_stake*."""
    if opp.total_stake == 0:
        return opp
    factor = new_stake / opp.total_stake
    return ArbitrageOpportunity(
        event_name=opp.event_name,
        sport=opp.sport,
        commence_time=opp.commence_time,
        best_offers=opp.best_offers,
        total_stake=round(new_stake, 2),
        profit=round(opp.profit * factor, 2),
        profit_pct=opp.profit_pct,
        stakes={k: round(v * factor, 2) for k, v in opp.stakes.items()},
        returns={k: round(v * factor, 2) for k, v in opp.returns.items()},
        market_type=opp.market_type,
    )


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_opportunity(opp: ArbitrageOpportunity) -> str:
    """Return a step-by-step plain-text string for one opportunity."""
    from display import format_step_instructions
    return format_step_instructions(opp)


def print_summary(opportunities: List[ArbitrageOpportunity]) -> None:
    """Print all found opportunities using the rich dashboard (or plain fallback)."""
    from display import print_rich_dashboard
    print_rich_dashboard(opportunities)
