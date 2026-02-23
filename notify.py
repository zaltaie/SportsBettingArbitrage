"""
Notification helpers for the Canadian Arbitrage Scanner.

Priority order:
  1. plyer desktop notification (cross-platform: Mac, Windows, Linux)
  2. Terminal bell (always available as fallback)

Install plyer for desktop popups:
    pip install plyer
"""
import sys


def send_notification(title: str, body: str) -> bool:
    """
    Send a desktop notification popup.
    Returns True if a desktop notification was sent, False if fell back to bell.
    """
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=body,
            app_name='Arbitrage Scanner',
            timeout=10,
        )
        return True
    except Exception:
        pass

    # Fallback: ring the terminal bell
    sys.stdout.write('\a')
    sys.stdout.flush()
    return False


def alert_new_opportunity(event_name: str, profit: float, profit_pct: float, sport: str) -> None:
    """Fire an alert whenever a new arbitrage opportunity is discovered."""
    title = 'New Arb: {:.2f}% profit'.format(profit_pct)
    body = '[{}] {} | ${:.2f} guaranteed'.format(sport, event_name, profit)
    send_notification(title, body)
