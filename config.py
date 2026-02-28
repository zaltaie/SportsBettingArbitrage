"""
Central configuration for the Canadian Sports Betting Arbitrage tool.
Set ODDS_API_KEY via environment variable or directly here.
"""
import os

# ---------------------------------------------------------------------------
# The Odds API  (https://the-odds-api.com — free tier: 500 req/month)
# ---------------------------------------------------------------------------
ODDS_API_KEY = os.environ.get('ODDS_API_KEY', '')
ODDS_API_BASE_URL = 'https://api.the-odds-api.com/v4'

# Canadian bookmakers supported by The Odds API
ODDS_API_CANADIAN_BOOKMAKERS = [
    'draftkings',    # DraftKings Canada
    'fanduel',       # FanDuel Canada
    'betmgm',        # BetMGM Canada
    'pointsbetus',   # PointsBet Canada
    'betrivers',     # BetRivers Canada
    'pinnacle',      # Pinnacle — sharp book, rarely limits arbers, sets market odds
]

# ---------------------------------------------------------------------------
# OddsChecker bookmaker codes → display names (Canadian operators)
# ---------------------------------------------------------------------------
ODDSCHECKER_CANADIAN_BOOKMAKERS = {
    'B3':  'Bet365',
    'SI':  'Sports Interaction',
    'BW':  'Betway',
    'BOD': 'Bodog',
    'DK':  'DraftKings',
    'FD':  'FanDuel',
    'MGM': 'BetMGM',
    'PB':  'PointsBet',
    'BR':  'BetRivers',
    'SC':  'theScore Bet',
}

# ---------------------------------------------------------------------------
# Top-10 Canadian betting site URLs (used by direct scrapers)
# ---------------------------------------------------------------------------
SITE_URLS = {
    'Bet365':            'https://www.bet365.com/#/AS/B1/',
    'DraftKings':        'https://sportsbook.draftkings.com/featured',
    'FanDuel':           'https://www.fanduel.com/sports',
    'BetMGM':            'https://sports.on.betmgm.ca/en/sports',
    'Sports Interaction': 'https://www.sportsinteraction.com/sports/',
    'Betway':            'https://sports.betway.com/en/sports',
    'PointsBet':         'https://ca.pointsbet.com/',
    'theScore Bet':      'https://bets.thescore.com/',
    'BetRivers':         'https://on.betrivers.com/',
    'Bodog':             'https://www.bodog.eu/sports/',
}

# ---------------------------------------------------------------------------
# Sports to scan
# Odds API keys → human labels
# ---------------------------------------------------------------------------
SPORTS = {
    'icehockey_nhl':             'NHL',
    'basketball_nba':            'NBA',
    'americanfootball_nfl':      'NFL',
    'baseball_mlb':              'MLB',
    'soccer_usa_mls':            'MLS',
    'americanfootball_cfl':      'CFL',
}

# OddsChecker sport listing URLs
ODDSCHECKER_SPORT_URLS = {
    'NHL': 'https://www.oddschecker.com/ice-hockey/nhl/',
    'NBA': 'https://www.oddschecker.com/basketball/nba/',
    'NFL': 'https://www.oddschecker.com/american-football/nfl/',
    'MLB': 'https://www.oddschecker.com/baseball/mlb/',
    'MLS': 'https://www.oddschecker.com/football/us-soccer/mls/',
    'CFL': 'https://www.oddschecker.com/american-football/canadian-football-league/',
}

# ---------------------------------------------------------------------------
# HTTP / scraping settings
# ---------------------------------------------------------------------------
REQUEST_DELAY = 1.5          # Seconds between requests (be polite)
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30         # Seconds

DEFAULT_HEADERS = {
    # Full Chrome 120 browser fingerprint — more convincing to bot-detection systems
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-CA,en;q=0.9,fr-CA;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
    'sec-ch-ua': '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
}

# ---------------------------------------------------------------------------
# Arbitrage detection settings
# ---------------------------------------------------------------------------
MIN_PROFIT_PCT = 0.3    # Only report opportunities above this %
MAX_PROFIT_PCT = 20.0   # Sanity-check cap (above this is likely bad data)
DEFAULT_BET_AMOUNT = 100.0  # Default total stake in CAD

# ---------------------------------------------------------------------------
# Watch / continuous-scan settings
# ---------------------------------------------------------------------------
WATCH_INTERVAL = 30     # Default seconds between scans in --watch mode
