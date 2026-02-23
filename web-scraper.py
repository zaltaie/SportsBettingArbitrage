"""
Legacy entry point — superseded by main.py.

Run the arbitrage scanner via:
    python main.py [--amount AMOUNT] [--sports SPORT ...] [--no-api]

For full usage details:
    python main.py --help
"""
import sys
import subprocess

if __name__ == '__main__':
    print("Note: web-scraper.py is deprecated. Forwarding to main.py…\n")
    result = subprocess.run([sys.executable, 'main.py'] + sys.argv[1:])
    sys.exit(result.returncode)
