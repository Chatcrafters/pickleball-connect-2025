# -*- coding: utf-8 -*-
import os
from twilio.rest import Client

# Twilio configuration - loaded from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')


def format_phone_number(phone):
    """
    Format phone number for WhatsApp - fixes 'Invalid From and To pair' error
    """
    if not phone:
        return None

    # Remove any existing whatsapp: prefix
    phone = phone.replace('whatsapp:', '')

    # Remove spaces, dashes, parentheses
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Ensure it starts with +
    if not phone.startswith('+'):
        if phone.startswith('00'):
            phone = '+' + phone[2:]
        else:
            phone = '+' + phone

    return f'whatsapp:{phone}'


def send_whatsapp_message(to_number, message, test_mode=True):
    """
    Send a WhatsApp message using Twilio
    """
    if test_mode or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print(f"\n{'='*60}")
        print(f"[TEST MODE] WhatsApp to {to_number}:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        return {'status': 'test_mode', 'sid': 'test_message_id'}

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Format phone number properly for WhatsApp
        formatted_number = format_phone_number(to_number)
        if not formatted_number:
            print(f"Invalid phone number: {to_number}")
            return {'status': 'error', 'error': 'Invalid phone number'}

        twilio_message = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=formatted_number
        )

        print(f"Message sent! SID: {twilio_message.sid}")
        return {'status': 'sent', 'sid': twilio_message.sid}

    except Exception as e:
        print(f"Error sending message: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def send_profile_completion_link(player, test_mode=True):
    """
    Send profile completion link to a player via WhatsApp
    """
    from flask import url_for, current_app

    # Build the update URL
    with current_app.app_context():
        update_url = url_for('players.update_profile', token=player.update_token, _external=True)

    messages = {
        'EN': f"""Welcome to WPC Series Europe!

Hi {player.first_name}!

Please complete your player profile to participate in our tournaments:

{update_url}

See you on the courts!
WPC Series Europe""",

        'DE': f"""Willkommen bei WPC Series Europe!

Hallo {player.first_name}!

Bitte vervollstaendige dein Spielerprofil, um an unseren Turnieren teilzunehmen:

{update_url}

Wir sehen uns auf dem Platz!
WPC Series Europe""",

        'ES': f"""Bienvenido a WPC Series Europe!

Hola {player.first_name}!

Por favor completa tu perfil de jugador para participar en nuestros torneos:

{update_url}

Nos vemos en las canchas!
WPC Series Europe""",

        'FR': f"""Bienvenue a WPC Series Europe!

Bonjour {player.first_name}!

Veuillez completer votre profil de joueur pour participer a nos tournois:

{update_url}

A bientot sur les courts!
WPC Series Europe"""
    }

    message = messages.get(player.preferred_language, messages['EN'])
    return send_whatsapp_message(player.phone, message, test_mode=test_mode)


def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """
    Get captain invitation message in the specified language
    """
    messages = {
        'EN': f"""PCL {team.tournament.name} - Team Captain Invitation

Hi {captain_name}!

You have been selected as Captain for {team.country_flag} {team.country_name} {team.age_category}!

Your responsibilities:
- Register your team players
- Ensure all profiles are complete
- Coordinate with your team

Your secret Captain Dashboard:
{captain_url}

Keep this link private - only you should have access!

Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Let's go!
WPC Series Europe""",

        'DE': f"""PCL {team.tournament.name} - Team-Kapitaen Einladung

Hallo {captain_name}!

Du wurdest als Kapitaen fuer {team.country_flag} {team.country_name} {team.age_category} ausgewaehlt!

Deine Aufgaben:
- Registriere deine Team-Spieler
- Stelle sicher, dass alle Profile vollstaendig sind
- Koordiniere dich mit deinem Team

Dein geheimes Kapitaen-Dashboard:
{captain_url}

Halte diesen Link privat - nur du solltest Zugang haben!

Anmeldeschluss: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Los geht's!
WPC Series Europe""",

        'ES': f"""PCL {team.tournament.name} - Invitacion de Capitan

Hola {captain_name}!

Has sido seleccionado como Capitan de {team.country_flag} {team.country_name} {team.age_category}!

Tus responsabilidades:
- Registrar a los jugadores de tu equipo
- Asegurar que todos los perfiles esten completos
- Coordinar con tu equipo

Tu Panel de Capitan secreto:
{captain_url}

Manten este enlace privado - solo tu debes tener acceso!

Fecha limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Vamos!
WPC Series Europe""",

        'FR': f"""PCL {team.tournament.name} - Invitation Capitaine

Bonjour {captain_name}!

Vous avez ete selectionne comme Capitaine de {team.country_flag} {team.country_name} {team.age_category}!

Vos responsabilites:
- Inscrire les joueurs de votre equipe
- S'assurer que tous les profils sont complets
- Coordonner avec votre equipe

Votre tableau de bord Capitaine secret:
{captain_url}

Gardez ce lien prive - seul vous devez y avoir acces!

Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

C'est parti!
WPC Series Europe"""
    }

    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """
    Get captain reminder message in the specified language
    """
    from datetime import datetime
    days_left = (team.tournament.registration_deadline - datetime.now()).days

    messages = {
        'EN': f"""PCL Reminder - {team.country_flag} {team.country_name} {team.age_category}

Hi {captain_name}!

Your team registration is incomplete:
Men: {stats['men']}/{team.min_men}-{team.max_men}
Women: {stats['women']}/{team.min_women}-{team.max_women}
Complete profiles: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Only {days_left} days left!

Complete your team now:
{captain_url}

WPC Series Europe""",

        'DE': f"""PCL Erinnerung - {team.country_flag} {team.country_name} {team.age_category}

Hallo {captain_name}!

Deine Team-Registrierung ist unvollstaendig:
Maenner: {stats['men']}/{team.min_men}-{team.max_men}
Frauen: {stats['women']}/{team.min_women}-{team.max_women}
Vollstaendige Profile: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Nur noch {days_left} Tage!

Vervollstaendige dein Team jetzt:
{captain_url}

WPC Series Europe""",

        'ES': f"""Recordatorio PCL - {team.country_flag} {team.country_name} {team.age_category}

Hola {captain_name}!

Tu registro de equipo esta incompleto:
Hombres: {stats['men']}/{team.min_men}-{team.max_men}
Mujeres: {stats['women']}/{team.min_women}-{team.max_women}
Perfiles completos: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Solo quedan {days_left} dias!

Completa tu equipo ahora:
{captain_url}

WPC Series Europe""",

        'FR': f"""Rappel PCL - {team.country_flag} {team.country_name} {team.age_category}

Bonjour {captain_name}!

Votre inscription d'equipe est incomplete:
Hommes: {stats['men']}/{team.min_men}-{team.max_men}
Femmes: {stats['women']}/{team.min_women}-{team.max_women}
Profils complets: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

Plus que {days_left} jours!

Completez votre equipe maintenant:
{captain_url}

WPC Series Europe"""
    }

    return messages.get(language, messages['EN'])


def get_message_template(message_type, language='EN', **kwargs):
    """
    Get a message template in the specified language
    """
    # Prepare end date line if end_date is provided
    end_date_line = ""
    if kwargs.get('end_date'):
        date_labels = {'EN': 'End: ', 'DE': 'Ende: ', 'ES': 'Fin: ', 'FR': 'Fin: '}
        end_date_line = date_labels.get(language, date_labels['EN']) + kwargs.get('end_date') + '\n'

    templates = {
        'invitation': {
            'EN': f"""{kwargs.get('event_name', 'Event')}

Start: {kwargs.get('start_date', '')}
{end_date_line}Location: {kwargs.get('location', '')}

{kwargs.get('description', '')}

----------------------
Please reply with:
YES - I'm interested
INFO - Send me more details
NO - Not this time

WPC Series Europe""",

            'DE': f"""{kwargs.get('event_name', 'Event')}

Start: {kwargs.get('start_date', '')}
{end_date_line}Ort: {kwargs.get('location', '')}

{kwargs.get('description', '')}

----------------------
Bitte antworte mit:
JA - Ich bin interessiert
INFO - Schick mir mehr Details
NEIN - Diesmal nicht

WPC Series Europe""",

            'ES': f"""{kwargs.get('event_name', 'Event')}

Inicio: {kwargs.get('start_date', '')}
{end_date_line}Lugar: {kwargs.get('location', '')}

{kwargs.get('description', '')}

----------------------
Por favor responde con:
SI - Estoy interesado
INFO - Enviame mas detalles
NO - Esta vez no

WPC Series Europe""",

            'FR': f"""{kwargs.get('event_name', 'Event')}

Debut: {kwargs.get('start_date', '')}
{end_date_line}Lieu: {kwargs.get('location', '')}

{kwargs.get('description', '')}

----------------------
Veuillez repondre avec:
OUI - Je suis interesse
INFO - Envoyez-moi plus de details
NON - Pas cette fois

WPC Series Europe"""
        },

        'reminder': {
            'EN': f"""Reminder: {kwargs.get('event_name', 'Event')}

Start: {kwargs.get('start_date', '')}
{end_date_line}Location: {kwargs.get('location', '')}

Don't forget to confirm your participation!

Reply with:
YES - Confirmed
NO - Cannot attend

WPC Series Europe""",

            'DE': f"""Erinnerung: {kwargs.get('event_name', 'Event')}

Start: {kwargs.get('start_date', '')}
{end_date_line}Ort: {kwargs.get('location', '')}

Vergiss nicht, deine Teilnahme zu bestaetigen!

Antworte mit:
JA - Bestaetigt
NEIN - Kann nicht teilnehmen

WPC Series Europe""",

            'ES': f"""Recordatorio: {kwargs.get('event_name', 'Event')}

Inicio: {kwargs.get('start_date', '')}
{end_date_line}Lugar: {kwargs.get('location', '')}

No olvides confirmar tu participacion!

Responde con:
SI - Confirmado
NO - No puedo asistir

WPC Series Europe""",

            'FR': f"""Rappel: {kwargs.get('event_name', 'Event')}

Debut: {kwargs.get('start_date', '')}
{end_date_line}Lieu: {kwargs.get('location', '')}

N'oubliez pas de confirmer votre participation!

Repondez avec:
OUI - Confirme
NON - Ne peut pas assister

WPC Series Europe"""
        },

        'update': {
            'EN': f"""Update: {kwargs.get('event_name', 'Event')}

{kwargs.get('description', 'Important update regarding the event.')}

WPC Series Europe""",

            'DE': f"""Update: {kwargs.get('event_name', 'Event')}

{kwargs.get('description', 'Wichtiges Update zum Event.')}

WPC Series Europe""",

            'ES': f"""Actualizacion: {kwargs.get('event_name', 'Event')}

{kwargs.get('description', 'Actualizacion importante sobre el evento.')}

WPC Series Europe""",

            'FR': f"""Mise a jour: {kwargs.get('event_name', 'Event')}

{kwargs.get('description', 'Mise a jour importante concernant l evenement.')}

WPC Series Europe"""
        }
    }

    # Get template for message type and language
    template_group = templates.get(message_type, templates['invitation'])
    return template_group.get(language, template_group['EN'])