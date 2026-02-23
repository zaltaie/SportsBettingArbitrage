# Canadian Sports Betting Arbitrage Scanner

Scans the top 10 Canadian sports betting sites in **parallel** and surfaces
guaranteed-profit opportunities across NHL, NBA, NFL, MLB, MLS, and CFL.

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

### 2. (Optional) Get a free Odds API key

Register at <https://the-odds-api.com> — the free tier gives 500 requests/month
and adds coverage for DraftKings, FanDuel, BetMGM, PointsBet, and BetRivers.

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

# Single scan — $250 stake, no prompt
python main.py --amount 250

# Skip The Odds API (no API key needed)
python main.py --no-api

# Scan only NHL and NBA
python main.py --sports icehockey_nhl basketball_nba

# Only show opps above 1.5% profit
python main.py --min-profit 1.5

# Continuous watch mode — re-scan every 60 seconds
python main.py --watch

# Watch mode with a custom interval (30 seconds)
python main.py --watch --interval 30

# Watch mode + desktop notification on every new opportunity
python main.py --watch --notify

# All options combined
python main.py --amount 500 --watch --interval 45 --notify --sports icehockey_nhl basketball_nba
```

---

## Command-line reference

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--amount` | `-a` | prompt | Total stake in CAD |
| `--sports` | `-s` | all | Space-separated sport keys to scan |
| `--no-api` | | off | Skip The Odds API even if key is set |
| `--min-profit` | | 0.5 | Minimum profit % to report |
| `--watch` | `-w` | off | Continuous scan mode |
| `--interval` | `-i` | 60 | Seconds between scans (watch mode) |
| `--notify` | `-n` | off | Desktop alert on new opportunities |

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
2. **Arbitrage detection** — for each event, the tool finds the single best
   (highest) odds for every outcome across all books. If
   `sum(1/odds) < 1.0`, a risk-free profit exists.
3. **Optimal stake allocation** — each leg is sized proportionally so the
   guaranteed return is identical regardless of which team wins.
4. **Rich dashboard** — results are rendered in a colour table sorted by
   profit %, followed by numbered bet-placement cards for each opportunity.
5. **New-opportunity alerts** — in `--watch` mode the scanner tracks which
   opportunities have already been shown; only genuinely new ones trigger a
   notification.

### Arbitrage formula

```
total_implied = sum(1 / best_odds_i  for each outcome i)
profit_pct    = (1 - total_implied) * 100
stake_i       = total_stake * (1/best_odds_i) / total_implied
```

---

## Data sources

| Source | How | Covers |
|--------|-----|--------|
| The Odds API | JSON API | DraftKings, FanDuel, BetMGM, PointsBet, BetRivers |
| OddsChecker | HTML scraper | Bet365, SI, Betway, Bodog + most of the top 10 |
| Direct site APIs | Per-site JSON/REST | All 10 bookmakers individually |

---

## Project structure

```
SportsBettingArbitrage/
├── main.py             Entry point — CLI, parallel collection, watch loop
├── arbitrage.py        Arbitrage math and data classes
├── display.py          Rich TUI dashboard and step-by-step bet cards
├── notify.py           Desktop/terminal notifications
├── config.py           Global settings (thresholds, URLs, intervals)
├── message.py          Logging helper (stdout + log.txt)
├── requirements.txt    Python dependencies
├── README.md           This file
└── scrapers/
    ├── base_scraper.py         Abstract base with retry logic
    ├── odds_api.py             The Odds API
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
   empty. Aim for at least your full stake amount at each bookmaker.
4. **Start with `--min-profit 1.5`** — very small margins (~0.5%) leave little
   room for error if one leg moves before you place it.
5. **Run with `--amount` equal to your actual bankroll** to see real dollar
   profits and correct stake splits.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No odds collected" | Check internet connection; try `--no-api` |
| Bet365 returns 0 entries | Cloudflare blocks direct access — OddsChecker covers it |
| Very few opportunities | Add `ODDS_API_KEY` for broader coverage |
| `rich` not found | `pip install rich` — plain text output is used as fallback |
| Desktop notifications not working | `pip install plyer` |
| Scrapers return errors | Some sites geo-block non-Canadian IPs; use a CA VPN |

---

## Disclaimer

Sports arbitrage is legal in Canada. However, bookmakers may limit or close
accounts that arb consistently. Use responsibly and review each platform's
terms of service.
