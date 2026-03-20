"""
Multi-channel alert system for new arbitrage opportunities.

Channels supported:
  1. Terminal bet deadline — always printed; shows the 2-minute window clock
  2. Slack webhook        — rich block-kit message with full bet instructions
  3. Email (SMTP)         — plain-text email with step-by-step instructions

Configuration (all via environment variables — never hard-code credentials):

  Channel        Env var            Example
  ----------     -----------------  ---------------------------------
  Slack          SLACK_WEBHOOK_URL  https://hooks.slack.com/services/…
  Email dest     ALERT_EMAIL        ops@hospital.ca,admin@hospital.ca
  SMTP server    SMTP_HOST          smtp.gmail.com
  SMTP port      SMTP_PORT          587
  SMTP login     SMTP_USER          alerts@hospital.ca
  SMTP password  SMTP_PASS          your-app-password

For Gmail, use an App Password (not your main password):
  https://myaccount.google.com/apppasswords

For Slack, create an Incoming Webhook:
  https://api.slack.com/messaging/webhooks
"""
import json
import smtplib
import urllib.request
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from config import (
    SLACK_WEBHOOK_URL,
    ALERT_EMAIL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
)

_MARKET_LABELS = {
    'moneyline': 'Moneyline',
    'spread':    'Point Spread',
    'total':     'Total (O/U)',
}

BET_WINDOW_MINUTES = 2   # Standard window before odds may shift


# ---------------------------------------------------------------------------
# 1. Terminal bet deadline
# ---------------------------------------------------------------------------

def print_bet_deadline(minutes: int = BET_WINDOW_MINUTES) -> None:
    """Print a prominent deadline countdown in the terminal."""
    deadline = datetime.now() + timedelta(minutes=minutes)
    bar = '!' * 64
    print('\n' + bar)
    print('  PLACE ALL BETS BEFORE  {}  ({} min window)'.format(
        deadline.strftime('%H:%M:%S'), minutes
    ))
    print(bar + '\n')


# ---------------------------------------------------------------------------
# 2. Slack webhook
# ---------------------------------------------------------------------------

def send_slack(opp, webhook_url: Optional[str] = None) -> bool:
    """
    POST a rich Slack Block Kit alert for one arbitrage opportunity.

    Returns True if the message was accepted (HTTP 200), False otherwise.
    """
    url = webhook_url or SLACK_WEBHOOK_URL
    if not url:
        return False

    market_label = _MARKET_LABELS.get(opp.market_type, opp.market_type)
    step_lines = []
    for step, (outcome, entry) in enumerate(opp.best_offers.items(), 1):
        stake = opp.stakes[outcome]
        step_lines.append(
            '*STEP {}* — {} | Bet *${:.2f}* on _{}_  @ *{}*'.format(
                step, entry.bookmaker, stake, outcome, entry.decimal_odds
            )
        )
        if entry.url:
            step_lines.append('  <{}|Open {}>'.format(entry.url, entry.bookmaker))

    deadline = datetime.now() + timedelta(minutes=BET_WINDOW_MINUTES)

    payload = {
        'text': ':moneybag: ARB: {} {} — ${:.2f} ({:.3f}%)'.format(
            opp.sport, opp.event_name, opp.profit, opp.profit_pct
        ),
        'blocks': [
            {
                'type': 'header',
                'text': {
                    'type': 'plain_text',
                    'text': ':moneybag: New Arbitrage Opportunity — {} {}'.format(
                        opp.sport, market_label
                    ),
                },
            },
            {
                'type': 'section',
                'fields': [
                    {'type': 'mrkdwn', 'text': '*Event:*\n{}'.format(opp.event_name)},
                    {'type': 'mrkdwn', 'text': '*Market:*\n{}'.format(market_label)},
                    {'type': 'mrkdwn', 'text': '*Guaranteed Profit:*\n${:.2f} ({:.3f}%)'.format(
                        opp.profit, opp.profit_pct
                    )},
                    {'type': 'mrkdwn', 'text': '*Total Stake:*\n${:.2f} CAD'.format(
                        opp.total_stake
                    )},
                ],
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': '\n'.join(step_lines),
                },
            },
            {
                'type': 'context',
                'elements': [
                    {
                        'type': 'mrkdwn',
                        'text': ':warning:  Place ALL bets before *{}* ({} min window)'.format(
                            deadline.strftime('%H:%M:%S'), BET_WINDOW_MINUTES
                        ),
                    }
                ],
            },
        ],
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data, headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as exc:
        print('[alerter] Slack send failed: {}'.format(exc))
        return False


# ---------------------------------------------------------------------------
# 3. Email (SMTP)
# ---------------------------------------------------------------------------

def send_email(
    opp,
    recipients: Optional[list] = None,
    smtp_config: Optional[dict] = None,
) -> bool:
    """
    Send a full bet-instructions email via SMTP (TLS on port 587).

    Parameters
    ----------
    opp        : ArbitrageOpportunity
    recipients : list of email strings (falls back to ALERT_EMAIL env var)
    smtp_config: dict with keys host/port/user/pass (falls back to SMTP_* env vars)
    """
    to_addrs = recipients or [a.strip() for a in ALERT_EMAIL.split(',') if a.strip()]
    if not to_addrs:
        print('[alerter] Email skipped: ALERT_EMAIL not configured.')
        return False

    cfg   = smtp_config or {}
    host  = cfg.get('host', SMTP_HOST) or 'smtp.gmail.com'
    port  = int(cfg.get('port', SMTP_PORT) or 587)
    user  = cfg.get('user', SMTP_USER)
    pwd   = cfg.get('pass', SMTP_PASS)

    if not (user and pwd):
        print('[alerter] Email skipped: SMTP_USER / SMTP_PASS not configured.')
        return False

    market_label = _MARKET_LABELS.get(opp.market_type, opp.market_type)
    subject = '[ARB] {} {} — ${:.2f} guaranteed ({:.3f}%)'.format(
        opp.sport, market_label, opp.profit, opp.profit_pct
    )

    # Plain-text body — readable on any device
    lines = [
        'ARBITRAGE OPPORTUNITY DETECTED',
        '=' * 60,
        'Event  : {}'.format(opp.event_name),
        'Sport  : {}'.format(opp.sport),
        'Market : {}'.format(market_label),
        'Profit : ${:.2f}  ({:.3f}%)'.format(opp.profit, opp.profit_pct),
        'Stake  : ${:.2f} CAD'.format(opp.total_stake),
        '',
    ]
    for step, (outcome, entry) in enumerate(opp.best_offers.items(), 1):
        stake = opp.stakes[outcome]
        lines.append('STEP {} -> {} — Bet ${:.2f} on {} @ {}'.format(
            step, entry.bookmaker, stake, outcome, entry.decimal_odds
        ))
        if entry.url:
            lines.append('         {}'.format(entry.url))
        lines.append('')

    deadline = datetime.now() + timedelta(minutes=BET_WINDOW_MINUTES)
    lines += [
        '=' * 60,
        'PLACE ALL BETS BEFORE {} ({} min window)'.format(
            deadline.strftime('%H:%M:%S'), BET_WINDOW_MINUTES
        ),
        '=' * 60,
        '',
        'Sent by Canadian Sports Betting Arbitrage Scanner',
    ]
    body = '\n'.join(lines)

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = user
    msg['To']      = ', '.join(to_addrs)
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(user, pwd)
            smtp.sendmail(user, to_addrs, msg.as_string())
        return True
    except Exception as exc:
        print('[alerter] Email send failed: {}'.format(exc))
        return False


# ---------------------------------------------------------------------------
# Unified alert dispatcher
# ---------------------------------------------------------------------------

def alert(opp, slack: bool = False, email: bool = False) -> None:
    """
    Dispatch all enabled alerts for one new arbitrage opportunity.

    Always prints the bet deadline in the terminal.
    Slack and email are sent only when the corresponding flag is True
    AND the required credentials are configured.
    """
    print_bet_deadline()

    if slack:
        ok = send_slack(opp)
        print('[alerter] Slack: {}'.format('sent OK' if ok else 'FAILED (check SLACK_WEBHOOK_URL)'))

    if email:
        ok = send_email(opp)
        print('[alerter] Email: {}'.format('sent OK' if ok else 'FAILED (check SMTP_* vars)'))
