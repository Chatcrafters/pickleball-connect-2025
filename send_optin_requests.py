"""
Send the WhatsApp opt-in template (TEMPLATE_OPTIN_REQUEST_{EN,DE,ES,FR}) to
players who have not been asked yet.

    python send_optin_requests.py                                  # dry run: list recipients
    python send_optin_requests.py --limit 3 --execute              # send to the first 3
    python send_optin_requests.py --phone +4917... --execute       # send to specific numbers only

Recipients: whatsapp_optin = false AND optin_requested_at IS NULL, ordered by id.
optin_requested_at is set (and committed) per player right after a successful
send, so an interrupted run can simply be restarted. The answer is processed
by the webhook (routes/webhook.py).
"""
import os
import sys
import argparse
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()  # before utils.whatsapp reads the Twilio settings

from flask import Flask
from models import db, Player, Message
from utils.whatsapp import send_optin_request_template, TEMPLATE_SIDS


def create_app():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        sys.exit('DATABASE_URL is not set - aborting.')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app


def run(limit, phones, execute):
    query = Player.query.filter(
        Player.whatsapp_optin.is_(False),
        Player.optin_requested_at.is_(None),
    )
    if phones:
        query = query.filter(Player.phone.in_(phones))
    total_pending = query.count()
    recipients = query.order_by(Player.id).limit(limit).all() if limit else query.order_by(Player.id).all()

    missing = [lang for lang, sid in TEMPLATE_SIDS['optin_request'].items() if not sid]
    print('=' * 70)
    print('EXECUTE - sending' if execute else 'DRY RUN - nothing is sent')
    print('=' * 70)
    print(f'Players not yet asked: {total_pending}, selected: {len(recipients)}')
    if missing:
        print(f'WARNING: no template SID for {", ".join(missing)} (falls back to EN)')
    if not TEMPLATE_SIDS['optin_request'].get('EN'):
        print('WARNING: TEMPLATE_OPTIN_REQUEST_EN is not set - sending will fail')

    sent = failed = 0
    for player in recipients:
        label = f'#{player.id} {player.first_name} {player.last_name} {player.phone} [{player.preferred_language}]'
        if not execute:
            print(f'  would send: {label}')
            continue

        result = send_optin_request_template(player)
        if result['status'] == 'sent':
            player.optin_requested_at = datetime.utcnow()
            db.session.add(Message(
                player_id=player.id,
                message_type='optin_request',
                content=f"template {result['template_sid']}",
                status='sent'
            ))
            db.session.commit()
            sent += 1
            print(f'  sent:   {label}  ({result["sid"]})')
        else:
            failed += 1
            print(f'  FAILED: {label}  {result.get("error")}')

    if execute:
        print(f'\nSent: {sent}, failed: {failed}')
    print('=' * 70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Send the WhatsApp opt-in request template.')
    parser.add_argument('--limit', type=int, help='send to at most N players')
    parser.add_argument('--phone', action='append', default=[],
                        help='only this number (E.164, repeatable)')
    parser.add_argument('--execute', action='store_true',
                        help='actually send (default is a dry run)')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    app = create_app()
    with app.app_context():
        run(limit=args.limit, phones=args.phone, execute=args.execute)
