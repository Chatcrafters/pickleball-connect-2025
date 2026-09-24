"""
One-off migration: wpc_player -> player (Option B)

Copies WPC players WITH a phone number into the general `player` table so they
show up under /players/ and in the event invite screen.

    python migrate_wpc_to_players.py            # dry run (default): report only, no writes
    python migrate_wpc_to_players.py --execute  # write to the database (one transaction)

Idempotent: every WPC player is matched against `player` by phone (fallback:
email). A match is updated, otherwise a new player is created.

On update, only name, email, country, date_of_birth and skill_level are
synced from WPC; the report lists how many values would actually change.
preferred_language is set on create only, so a language edited later in
/players/ is not overwritten by a re-run.

Phones are normalized to E.164: a national trunk "0" after the country code
is dropped (+44 07... -> +44 7...), implausible numbers are skipped.
The production table also has a legacy NOT NULL `phone_number` column, which
is written with the same value as `phone`.

No consent is written: WPC players have not opted in to WhatsApp or marketing
messages, so whatsapp_optin keeps its default (false).
"""
import os
import re
import sys
import argparse
from collections import Counter

from dotenv import load_dotenv
from flask import Flask

from models import db, Player, WPCPlayer

# Language codes as used by the app (filters, message templates): EN/DE/ES/FR
COUNTRY_LANGUAGE = {
    'Spain': 'ES',
    'Germany': 'DE',
    'France': 'FR',
}
DEFAULT_LANGUAGE = 'EN'

SKILL_MIN, SKILL_MAX = 2.0, 5.0

# Countries whose national trunk "0" must be dropped in international format.
# Italy (39) is deliberately missing: Italian landlines keep their leading 0.
TRUNK_ZERO_CODES = ('44', '49', '33', '31', '32', '41', '43', '46', '353', '358')

# National number length (digits after the country code) and allowed first
# digits for the countries in this data set; all others only get the generic
# E.164 check (8-15 digits in total).
NATIONAL_RULES = {
    '34': (9, 9, '6789'),         # Spain
    '33': (9, 9, '123456789'),    # France
    '351': (9, 9, '29'),          # Portugal
    '31': (9, 9, '123456789'),    # Netherlands
    '44': (10, 10, '123578'),     # United Kingdom
    '49': (7, 12, '123456789'),   # Germany
    '39': (6, 11, '0123'),        # Italy (mobiles 3..., landlines 0...)
    '1': (10, 10, '23456789'),    # US / Canada
}


def create_app():
    load_dotenv()
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


def has_phone(phone):
    return bool(phone and phone.strip() and phone.strip() != '-')


def normalize_phone(phone):
    """E.164 without spaces - the webhook matches Player.phone exactly against
    Twilio's 'From' number (+4915...).

    Returns (phone, fix note or None).
    """
    phone = ''.join(c for c in phone.strip() if c.isdigit() or c == '+')
    if phone.startswith('00'):
        phone = '+' + phone[2:]
    elif not phone.startswith('+'):
        phone = '+' + phone
    for code in TRUNK_ZERO_CODES:
        if phone.startswith(f'+{code}0'):
            fixed = f'+{code}{phone[len(code) + 2:]}'
            return fixed, f'{phone} -> {fixed}'
    return phone, None


def phone_problem(phone):
    """E.164 plausibility check. Returns a reason, or None if plausible."""
    digits = phone[1:]
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        return f'{len(digits)} digits, E.164 needs 8-15'
    for code in sorted(NATIONAL_RULES, key=len, reverse=True):
        if digits.startswith(code):
            min_len, max_len, first_digits = NATIONAL_RULES[code]
            national = digits[len(code):]
            if not min_len <= len(national) <= max_len:
                return f'+{code}: national number has {len(national)} digits, expected {min_len}-{max_len}'
            if national[0] not in first_digits:
                return f'+{code}: national number cannot start with {national[0]}'
            return None
    return None


def parse_skill_level(rating):
    """'Intermediate Plus (3.5)' -> '3.5', 'Novice (2.0 - 2.5)' -> '2.0'.

    Ranges use their lower bound. Values below 2.0 (Beginner) are left empty,
    values above 5.0 are capped at 5.0.
    Returns (skill_level or None, note or None).
    """
    if not rating:
        return None, 'empty'
    numbers = re.findall(r'\d+(?:[.,]\d+)?', rating)
    if not numbers:
        return None, 'unparseable'
    value = float(numbers[0].replace(',', '.'))
    rounded = round(value * 2) / 2
    if rounded < SKILL_MIN:
        return None, f'below {SKILL_MIN:.1f}'
    if rounded > SKILL_MAX:
        return f'{SKILL_MAX:.1f}', f'capped {rounded:.1f} -> {SKILL_MAX:.1f}'
    return f'{rounded:.1f}', None


def map_language(wpc):
    # Checked-in players chose their language themselves - keep it.
    if wpc.checked_in and wpc.preferred_language:
        return wpc.preferred_language.upper()
    return COUNTRY_LANGUAGE.get((wpc.country or '').strip(), DEFAULT_LANGUAGE)


def fmt_player(wpc):
    return f'#{wpc.id} {wpc.first_name} {wpc.last_name} <{wpc.email or "-"}> {wpc.phone}'


def run(execute):
    report = {
        'create': [],
        'update': [],
        'skip_no_phone': [],
        'skip_invalid_phone': [],   # (wpc, reason)
        'skip_duplicate': [],       # (skipped wpc, kept wpc)
        'errors': [],               # (wpc, reason)
        'skill_notes': [],          # (wpc, rating, note)
        'phone_fixes': [],          # (wpc, note)
        'empty_last_name': [],
    }
    languages = Counter()
    field_changes = Counter()  # field -> number of updated players where the value changes

    existing = Player.query.all()
    by_phone = {p.phone: p for p in existing}
    by_email = {p.email.lower(): p for p in existing if p.email}

    seen_phones = {}  # normalized phone -> first wpc player with it
    wpc_players = WPCPlayer.query.order_by(WPCPlayer.id).all()

    for wpc in wpc_players:
        if not has_phone(wpc.phone):
            report['skip_no_phone'].append(wpc)
            continue

        phone, phone_fix = normalize_phone(wpc.phone)
        problem = phone_problem(phone)
        if problem:
            report['skip_invalid_phone'].append((wpc, f'{phone}: {problem}'))
            continue

        if phone in seen_phones:
            report['skip_duplicate'].append((wpc, seen_phones[phone]))
            continue
        seen_phones[phone] = wpc

        if len(phone) > 20:
            report['errors'].append((wpc, f'phone longer than 20 chars: {phone}'))
            continue
        if not (wpc.first_name or '').strip():
            report['errors'].append((wpc, 'empty first name'))
            continue
        email = (wpc.email or '').strip() or None
        if not email:
            report['errors'].append((wpc, 'no email (player.email is NOT NULL in production)'))
            continue

        if phone_fix:
            report['phone_fixes'].append((wpc, phone_fix))
        skill_level, skill_note = parse_skill_level(wpc.dupr_rating)
        if skill_note:
            report['skill_notes'].append((wpc, wpc.dupr_rating, skill_note))
        if not (wpc.last_name or '').strip():
            report['empty_last_name'].append(wpc)

        player = by_phone.get(phone) or by_email.get(email.lower())

        # Email is unique per player: never assign one that belongs to someone else
        owner = by_email.get(email.lower())
        if owner is not None and owner is not player:
            report['errors'].append((wpc, f'email already used by player #{owner.id}'))
            continue

        if player is None:
            language = map_language(wpc)
            player = Player(
                first_name=wpc.first_name.strip(),
                last_name=(wpc.last_name or '').strip(),
                phone=phone,
                phone_number=phone,
                email=email,
                skill_level=skill_level,
                city=None,
                country=wpc.country,
                date_of_birth=wpc.date_of_birth,
                preferred_language=language,
            )
            player.generate_update_token()
            report['create'].append((wpc, player))
            if execute:
                db.session.add(player)
        else:
            # Matched by email with a different phone: only take the WPC phone if it is free
            if player.phone != phone:
                if phone in by_phone:
                    report['errors'].append((wpc, f'phone already used by player #{by_phone[phone].id}'))
                    continue
                by_phone.pop(player.phone, None)
                if execute:
                    player.phone = phone
                    player.phone_number = phone
            language = player.preferred_language or map_language(wpc)
            target = {
                'first_name': wpc.first_name.strip(),
                'last_name': (wpc.last_name or '').strip(),
                'email': email,
                'phone_number': player.phone_number or phone,
                'country': wpc.country or player.country,
                'date_of_birth': wpc.date_of_birth or player.date_of_birth,
                'skill_level': skill_level or player.skill_level,
                'preferred_language': language,
            }
            for field, value in target.items():
                if getattr(player, field) != value:
                    field_changes[field] += 1
                    if execute:
                        setattr(player, field, value)
            report['update'].append((wpc, player))

        languages[language] += 1
        by_phone[phone] = player
        by_email[email.lower()] = player

    if execute:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    else:
        db.session.rollback()

    print_report(report, languages, field_changes, len(wpc_players), execute)


def print_list(title, rows, fmt):
    print(f'\n{title}')
    for row in rows:
        print(fmt(row))
    if not rows:
        print('  none')


def print_report(r, languages, field_changes, total, execute):
    line = '=' * 70
    print(line)
    print('EXECUTE - changes committed' if execute else 'DRY RUN - nothing was written')
    print(line)
    print(f'wpc_player rows read:          {total}')
    print(f'  to create:                   {len(r["create"])}')
    print(f'  to update:                   {len(r["update"])}')
    print(f'  skipped (no phone):          {len(r["skip_no_phone"])}')
    print(f'  skipped (invalid phone):     {len(r["skip_invalid_phone"])}')
    print(f'  skipped (duplicate phone):   {len(r["skip_duplicate"])}')
    print(f'  skipped (error):             {len(r["errors"])}')

    if r['update']:
        print('\nValues changed on update (field: players):')
        for field, count in sorted(field_changes.items()):
            print(f'  {field}: {count}')
        if not field_changes:
            print('  none - all updated players are already in sync')

    print('\nLanguage distribution (created + updated):')
    for lang, count in languages.most_common():
        print(f'  {lang}: {count}')

    print_list('Skipped invalid phone numbers:', r['skip_invalid_phone'],
               lambda x: f'  {fmt_player(x[0])}: {x[1]}')
    print_list('Corrected phone numbers (trunk 0 after country code removed):', r['phone_fixes'],
               lambda x: f'  {fmt_player(x[0])}: {x[1]}')
    print_list('Skipped duplicates (first record by id is kept):', r['skip_duplicate'],
               lambda x: f'  SKIP {fmt_player(x[0])}\n       kept: {fmt_player(x[1])}')
    print_list('Errors:', r['errors'],
               lambda x: f'  {fmt_player(x[0])}: {x[1]}')
    print_list('skill_level left empty or capped (empty / unparseable / below 2.0):', r['skill_notes'],
               lambda x: f'  {fmt_player(x[0])}: "{x[1]}" -> {x[2]}')

    if r['empty_last_name']:
        print_list(f'Empty last name (imported with last_name=""): {len(r["empty_last_name"])}',
                   r['empty_last_name'], lambda wpc: f'  {fmt_player(wpc)}')

    print('\nSample rows (first 5 to create):')
    print(f'  {"wpc":>5}  {"name":<28} {"phone":<16} {"country":<16} {"lang":<4} {"level":<5} rating')
    for wpc, p in r['create'][:5]:
        name = f'{p.first_name} {p.last_name}'[:28]
        print(f'  {wpc.id:>5}  {name:<28} {p.phone:<16} {(p.country or "-")[:16]:<16} '
              f'{p.preferred_language:<4} {(p.skill_level or "-"):<5} {wpc.dupr_rating or "-"}')
    print(line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Migrate wpc_player rows into player.')
    parser.add_argument('--execute', action='store_true',
                        help='write to the database (default is a dry run)')
    args = parser.parse_args()

    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    app = create_app()
    with app.app_context():
        run(execute=args.execute)
