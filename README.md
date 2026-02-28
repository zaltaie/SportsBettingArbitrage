# Canadian Sports Betting Arbitrage Scanner

Scans the top 10 Canadian sports betting sites in **parallel** and surfaces
guaranteed-profit opportunities across NHL, NBA, NFL, MLB, MLS, and CFL.

Three market types are scanned simultaneously — **moneyline, point spreads, and
totals (over/under)** — giving 3–5× more opportunities than moneyline alone.

When a match is found you get numbered step-by-step instructions:

```
STEP 1 -> Open Bet365 (tap to open)
          https://www.bet365.com/#/AS/B1/
          Bet $124.50 on Maple Leafs @ 2.10

STEP 2 -> Open FanDuel (tap to open)
          https://www.fanduel.com/sports
          Bet $75.50 on Canucks @ 3.40

Guaranteed profit: $8.34  (4.17%)
Total stake: $200.00 CAD
Place ALL bets within 2 minutes.
```

---

## Realistic daily profit expectations

| Stake | Arbs/day* | Avg margin | Daily profit |
|-------|-----------|------------|--------------|
| $1,000 | 8–30 | 0.7% | $56–$210 |
| $10,000 | 8–30 | 0.7% | $560–$2,100 |
| $50,000 | 8–30 | 0.7% | $2,800–$10,500 |

\* Multi-sport season (NHL + NBA + MLB overlapping), with ODDS_API_KEY set.

**The hard ceiling — account limits.** Bookmakers identify and limit arbers
within 2–6 weeks. Once limited, max bets drop to $2–$10.
- Pinnacle and Bodog rarely limit — concentrate the highest stakes there.
- DraftKings / FanDuel / BetMGM limit aggressively — start small, scale slowly.
- Use separate accounts (different people) to multiply effective capacity.

---

## Covered bookmakers

| # | Site | Region |
|---|------|--------|
| 1 | Bet365 | Canada-wide |
| 2 | DraftKings | ON, AB, BC |
| 3 | FanDuel | Ontario |
| 4 | BetMGM | ON, AB |
| 5 | Sports Interaction | Canada-wide |
| 6 | Betway | Major provinces |
| 7 | PointsBet | ON, AB |
| 8 | theScore Bet | ON, AB |
| 9 | BetRivers | ON, AB |
| 10 | Bodog | Offshore / Canada-wide |
| + | Pinnacle | Offshore (via Odds API) |

---

## Requirements

- Python 3.8 or newer
- `pip install -r requirements.txt`

**Optional but recommended:**

| Package | Purpose |
|---------|---------|
| `rich` | Colour TUI dashboard with tables and bet cards |
| `plyer` | Native desktop popup notifications (`--notify`) |

Both are already listed in `requirements.txt`.

---

## Quick start

### 1. Clone and install

```bash
git clone https://github.com/zaltaie/SportsBettingArbitrage.git
cd SportsBettingArbitrage
pip install -r requirements.txt
```

### 2. Get a free Odds API key (strongly recommended)

Register at <https://the-odds-api.com> — the free tier gives 500 requests/month
and adds Pinnacle, DraftKings, FanDuel, BetMGM, PointsBet, and BetRivers with
**spread and total markets** (3–5× more arb opportunities than moneyline only).

```bash
export ODDS_API_KEY=your_key_here   # Mac / Linux
set    ODDS_API_KEY=your_key_here   # Windows CMD
$env:ODDS_API_KEY="your_key_here"   # Windows PowerShell
```

### 3. Run a single scan

```bash
python main.py
```

You will be prompted for your total stake in CAD (default: $100).

---

## All usage examples

```bash
# Single scan — prompt for stake
python main.py

# Single scan — $500 stake, no prompt
python main.py --amount 500

# Skip The Odds API (no API key needed, moneyline only)
python main.py --no-api

# Scan only NHL and NBA
python main.py --sports icehockey_nhl basketball_nba

# Only show opportunities above 0.5% profit
python main.py --min-profit 0.5

# Continuous watch mode — re-scan every 30 seconds (new default)
python main.py --watch

# Watch mode with a custom interval (15 seconds)
python main.py --watch --interval 15

# Watch mode + desktop notification on every new opportunity
python main.py --watch --notify

# Kelly criterion staking — stake = bankroll × profit% × fraction
# Half-Kelly on a $10,000 bankroll (recommended starting point)
python main.py --kelly 0.5 --bankroll 10000 --watch

# Full Kelly on a $50,000 bankroll (aggressive)
python main.py --kelly 1.0 --bankroll 50000 --watch

# All options combined
python main.py --amount 500 --watch --interval 20 --notify --sports icehockey_nhl basketball_nba

# ---- P&L reporting (tracker.py) ----

# Today's profit summary
python tracker.py --report

# Last 7 days
python tracker.py --report --days 7

# Last 30 days (monthly view)
python tracker.py --report --days 30

# Top book pairs by profit over the last 7 days
python tracker.py --pairs --days 7
```

---

## Command-line reference

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--amount` | `-a` | prompt | Total stake in CAD (ignored when `--kelly` is set) |
| `--sports` | `-s` | all | Space-separated sport keys to scan |
| `--no-api` | | off | Skip The Odds API even if key is set |
| `--min-profit` | | 0.3 | Minimum profit % to report |
| `--watch` | `-w` | off | Continuous scan mode |
| `--interval` | `-i` | 30 | Seconds between scans (watch mode) |
| `--notify` | `-n` | off | Desktop alert on new opportunities |
| `--kelly` | | off | Kelly fraction 0.0–1.0 (requires `--bankroll`) |
| `--bankroll` | | — | Total bankroll in CAD (used with `--kelly`) |

**Valid sport keys** for `--sports`:

| Key | League |
|-----|--------|
| `icehockey_nhl` | NHL |
| `basketball_nba` | NBA |
| `americanfootball_nfl` | NFL |
| `baseball_mlb` | MLB |
| `soccer_usa_mls` | MLS |
| `americanfootball_cfl` | CFL |

---

## How it works

1. **Parallel scraping** — all 10–12 data sources fire simultaneously in a
   thread pool, so a full scan takes ~10s instead of 2+ minutes sequentially.
2. **Multi-market detection** — three market types are scanned per event:
   - **Moneyline** — outright winner (2-way or 3-way for soccer draw)
   - **Spread** — point-spread bets grouped by exact line (e.g. -3.5)
   - **Total** — over/under bets grouped by total line (e.g. 220.5)
3. **Arbitrage detection** — for each event × market × line, the tool picks the
   best (highest) odds for every outcome across all books. If
   `sum(1/odds) < 1.0`, a risk-free profit exists.
4. **Optimal stake allocation** — each leg is sized proportionally so the
   guaranteed return is identical regardless of which outcome wins.
5. **Kelly criterion** (optional) — with `--kelly`, each opportunity's stake is
   computed dynamically: `stake = bankroll × profit_pct × kelly_fraction`,
   growing the bankroll faster than flat staking during productive periods.
6. **Opportunity tracker** — every new arb is logged to `arb_history.db`;
   use `python tracker.py --report` to see daily P&L and top book pairs.
7. **New-opportunity alerts** — in `--watch` mode the scanner tracks which
   opportunities have already been shown; only genuinely new ones trigger a
   notification.

### Arbitrage formula

```
total_implied = sum(1 / best_odds_i  for each outcome i)
profit_pct    = (1 - total_implied) * 100
stake_i       = total_stake * (1/best_odds_i) / total_implied
```

### Kelly formula

```
stake = bankroll * (profit_pct / 100) * kelly_fraction
```

Use `kelly_fraction = 0.5` (half-Kelly) to balance growth against variance.

---

## Data sources

| Source | How | Markets |
|--------|-----|---------|
| The Odds API | JSON API | Moneyline, Spreads, Totals |
| OddsChecker | HTML scraper | Moneyline |
| Direct site APIs | Per-site JSON/REST | Moneyline |

The Odds API covers: DraftKings, FanDuel, BetMGM, PointsBet, BetRivers, Pinnacle.
All three markets (h2h, spreads, totals) are fetched in a single API call.

---

## Profit tracking

All opportunities are automatically saved to `arb_history.db` (SQLite, no setup
required). The `tracker.py` CLI gives you visibility into what's working:

```bash
python tracker.py --report --days 7
# ========================================================================
# Arbitrage P&L Report  —  last 7 day(s)
# ========================================================================
# Date         Sport  Market        Opps   Profit CAD    Avg %    Max %
# ------------------------------------------------------------------------
# 2026-02-28   NHL    moneyline        3      $48.21    0.321%   0.450%
# 2026-02-28   NBA    spread           5      $72.34    0.287%   0.512%
# 2026-02-28   NBA    total            4      $55.80    0.301%   0.398%
# ------------------------------------------------------------------------
# TOTAL                               12     $176.35

python tracker.py --pairs --days 7
# Top book pairs by profit — focus your capital on these combinations
```

---

## Project structure

```
SportsBettingArbitrage/
├── main.py             Entry point — CLI, parallel collection, watch loop
├── arbitrage.py        Arbitrage math, data classes, Kelly staking
├── tracker.py          SQLite P&L tracker and daily report CLI
├── display.py          Rich TUI dashboard and step-by-step bet cards
├── notify.py           Desktop/terminal notifications
├── config.py           Global settings (thresholds, URLs, intervals)
├── message.py          Logging helper (stdout + log.txt)
├── requirements.txt    Python dependencies
├── arb_history.db      Auto-created SQLite database (git-ignored)
├── README.md           This file
└── scrapers/
    ├── base_scraper.py         Abstract base with retry logic
    ├── odds_api.py             The Odds API (moneyline + spreads + totals)
    ├── oddschecker.py          OddsChecker HTML scraper
    ├── bet365.py               Bet365
    ├── draftkings.py           DraftKings
    ├── fanduel.py              FanDuel
    ├── betmgm.py               BetMGM
    ├── pointsbet.py            PointsBet
    ├── betrivers.py            BetRivers
    ├── sports_interaction.py   Sports Interaction
    ├── betway.py               Betway
    ├── bodog.py                Bodog
    └── thescore.py             theScore Bet
```

---

## Tips for maximum profit

1. **Act within 2 minutes** — odds can shift or be suspended at any moment.
   Always place the lower-odds leg first (it closes slower).
2. **Use `--watch --notify`** in the background so you never miss an opportunity.
3. **Keep balances at every book** — you can't place a bet if your account is
   empty. Aim for at least your full stake at each bookmaker.
4. **Prioritise spread and total markets** — there are 3–5× more arbs than
   moneyline, with similar or better margins.
5. **Start with half-Kelly (`--kelly 0.5`)** — it gives ~75% of full-Kelly
   growth while cutting drawdown risk in half.
6. **Check `python tracker.py --pairs --days 7` weekly** — double down on the
   book pairs showing the most profit and reduce exposure where margins are thin.
7. **Pinnacle and Bodog first** — these sharp books rarely limit accounts.
   Use them as the "anchor" leg in every arb and put your largest stakes there.
8. **Ramp up slowly at soft books** — spend 2 weeks placing small recreational
   bets at DraftKings / FanDuel / BetMGM before placing arb-sized stakes.
9. **Run with `--min-profit 0.3`** (the new default) to catch the maximum
   number of genuine opportunities.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No odds collected" | Check internet connection; try `--no-api` |
| Bet365 returns 0 entries | Cloudflare blocks direct access — OddsChecker covers it |
| Very few opportunities | Add `ODDS_API_KEY` for spreads/totals coverage |
| `rich` not found | `pip install rich` — plain text output is used as fallback |
| Desktop notifications not working | `pip install plyer` |
| Scrapers return errors | Some sites geo-block non-Canadian IPs; use a CA VPN |
| No spread/total arbs found | These come only via The Odds API — ensure `ODDS_API_KEY` is set |

---

## Disclaimer

Sports arbitrage is legal in Canada. However, bookmakers may limit or close
accounts that arb consistently. Use responsibly and review each platform's
terms of service.
