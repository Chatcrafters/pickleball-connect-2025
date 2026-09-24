"""
WhatsApp Messaging Utilities for Pickleball Connect
====================================================
Uses Twilio API with Content Templates for WhatsApp Business messaging.

Content Templates:
- captain_invitation_de/en/es/fr - Team captain invitations with call-to-action button

Template Variables:
- {{1}} = Tournament Name (e.g., "Malaga 2026")
- {{2}} = Captain Name (e.g., "Max")
- {{3}} = Team Name (e.g., "🇩🇪 Germany +50")
- {{4}} = Captain Token (displayed in body)
- {{5}} = Captain Token (used in URL button)
"""

import os
import json
from twilio.rest import Client
from flask import url_for

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Content Template SIDs (set in environment variables)
TEMPLATE_SIDS = {
    'captain_invite': {
        'DE': os.environ.get('TEMPLATE_CAPTAIN_INVITE_DE'),
        'EN': os.environ.get('TEMPLATE_CAPTAIN_INVITE_EN'),
        'ES': os.environ.get('TEMPLATE_CAPTAIN_INVITE_ES'),
        'FR': os.environ.get('TEMPLATE_CAPTAIN_INVITE_FR'),
    },
    # Opt-in request with quick replies OPTIN_YES / OPTIN_NO, {{1}} = first name
    'optin_request': {
        'DE': os.environ.get('TEMPLATE_OPTIN_REQUEST_DE'),
        'EN': os.environ.get('TEMPLATE_OPTIN_REQUEST_EN'),
        'ES': os.environ.get('TEMPLATE_OPTIN_REQUEST_ES'),
        'FR': os.environ.get('TEMPLATE_OPTIN_REQUEST_FR'),
    },
}


def format_phone_number(phone):
    """
    Format phone number for WhatsApp - fixes 'Invalid From and To pair' error
    
    Args:
        phone: Phone number in various formats
    
    Returns:
        str: Properly formatted phone number with whatsapp: prefix
    """
    if not phone:
        return None
    
    # Remove any existing whatsapp: prefix
    phone = str(phone).replace('whatsapp:', '')
    
    # Remove spaces, dashes, parentheses
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Ensure it starts with +
    if not phone.startswith('+'):
        # If it starts with 00, replace with +
        if phone.startswith('00'):
            phone = '+' + phone[2:]
        else:
            # Assume it needs a + prefix
            phone = '+' + phone
    
    # Validate minimum length (country code + number)
    if len(phone) < 10:
        print(f"⚠️ Phone number too short: {phone}")
        return None
    
    return f'whatsapp:{phone}'


def get_twilio_client():
    """Get configured Twilio client"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("❌ Twilio credentials not configured!")
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_message(to_phone, message, test_mode=False):
    """
    Send a regular WhatsApp message (freeform text)
    
    Note: This only works within 24h session window or with pre-approved templates.
    For initial contact, use Content Templates instead.
    
    Args:
        to_phone: Recipient phone number
        message: Message content
        test_mode: If True, only log the message without sending
    
    Returns:
        dict: Status of the send operation
    """
    formatted_phone = format_phone_number(to_phone)
    
    if not formatted_phone:
        return {'status': 'error', 'error': f'Invalid phone number: {to_phone}'}
    
    print(f"\n{'='*60}")
    print(f"📤 WhatsApp Message")
    print(f"{'='*60}")
    print(f"📱 To: {formatted_phone}")
    print(f"📝 Message:\n{message[:200]}...")
    print(f"🧪 Test Mode: {test_mode}")
    print(f"{'='*60}")
    
    if test_mode:
        print("✅ Test mode - message not sent")
        return {'status': 'test_mode', 'message': 'Test mode - not sent'}
    
    try:
        client = get_twilio_client()
        if not client:
            return {'status': 'error', 'error': 'Twilio client not configured'}
        
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=formatted_phone
        )
        
        print(f"✅ Message sent! SID: {msg.sid}")
        return {'status': 'sent', 'sid': msg.sid}
        
    except Exception as e:
        print(f"❌ Error sending message: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def send_captain_invitation_template(team, captain_name, captain_phone, captain_token, language='EN', test_mode=False):
    """
    Send captain invitation using WhatsApp Content Template with call-to-action button.
    
    Template Variables (IMPORTANT - both 4 and 5 need the token!):
    - {{1}} = Tournament Name (e.g., "Malaga 2026")
    - {{2}} = Captain Name (e.g., "Max")
    - {{3}} = Team Name (e.g., "🇩🇪 Germany +50")
    - {{4}} = Captain Token (displayed in body text)
    - {{5}} = Captain Token (used in URL button - THIS IS THE FIX!)
    
    Args:
        team: PCLTeam object
        captain_name: Name of the captain
        captain_phone: Captain's phone number
        captain_token: Team's captain token for dashboard URL
        language: Language code (EN, DE, ES, FR)
        test_mode: If True, only log without sending
    
    Returns:
        dict: Status of the send operation
    """
    formatted_phone = format_phone_number(captain_phone)
    
    if not formatted_phone:
        return {'status': 'error', 'error': f'Invalid phone number: {captain_phone}'}
    
    # Get template SID for the language
    template_sid = TEMPLATE_SIDS.get('captain_invite', {}).get(language.upper())
    
    # Fallback to EN if language not available
    if not template_sid:
        template_sid = TEMPLATE_SIDS.get('captain_invite', {}).get('EN')
        print(f"⚠️ No template for {language}, falling back to EN")
    
    if not template_sid:
        print("❌ No Content Template SID configured!")
        print("   Please set TEMPLATE_CAPTAIN_INVITE_DE/EN/ES/FR in environment variables")
        # Fallback to regular message
        return send_captain_invitation_fallback(team, captain_name, captain_phone, captain_token, language, test_mode)
    
    # Prepare template variables
    # ⚠️ CRITICAL FIX: Both {{4}} and {{5}} need the captain_token!
    # {{4}} = Token displayed in message body
    # {{5}} = Token used in the button URL (https://pickleballconnect.eu/pcl/team/{{5}})
    team_name = f"{team.country_flag} {team.country_name} {team.age_category}"
    
    content_variables = {
        "1": team.tournament.name,      # Tournament Name
        "2": captain_name,               # Captain Name
        "3": team_name,                  # Team Name
        "4": captain_token,              # Token (displayed in body)
        "5": captain_token               # Token (used in button URL) ← THIS IS THE FIX!
    }
    
    print(f"\n{'='*60}")
    print(f"📤 WhatsApp Content Template")
    print(f"{'='*60}")
    print(f"📱 To: {formatted_phone}")
    print(f"📋 Template SID: {template_sid}")
    print(f"🌐 Language: {language}")
    print(f"📝 Variables:")
    print(f"   {{1}} Tournament: {content_variables['1']}")
    print(f"   {{2}} Captain: {content_variables['2']}")
    print(f"   {{3}} Team: {content_variables['3']}")
    print(f"   {{4}} Token (body): {content_variables['4'][:20]}...")
    print(f"   {{5}} Token (URL): {content_variables['5'][:20]}...")
    print(f"🔗 Resulting URL: https://pickleballconnect.eu/pcl/team/{captain_token}")
    print(f"🧪 Test Mode: {test_mode}")
    print(f"{'='*60}")
    
    if test_mode:
        print("✅ Test mode - message not sent")
        return {'status': 'test_mode', 'message': 'Test mode - not sent', 'template_sid': template_sid}
    
    try:
        client = get_twilio_client()
        if not client:
            return {'status': 'error', 'error': 'Twilio client not configured'}
        
        msg = client.messages.create(
            content_sid=template_sid,
            content_variables=json.dumps(content_variables),
            from_=TWILIO_WHATSAPP_NUMBER,
            to=formatted_phone
        )
        
        print(f"✅ Template message sent! SID: {msg.sid}")
        return {'status': 'sent', 'sid': msg.sid, 'template_sid': template_sid}
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error sending template: {error_msg}")
        
        # Check for common errors
        if '63016' in error_msg or 'not approved' in error_msg.lower():
            print("⚠️ Template not yet approved by WhatsApp. Falling back to text message.")
            return send_captain_invitation_fallback(team, captain_name, captain_phone, captain_token, language, test_mode)
        
        return {'status': 'error', 'error': error_msg}


def send_captain_invitation_fallback(team, captain_name, captain_phone, captain_token, language='EN', test_mode=False):
    """
    Fallback: Send captain invitation as regular text message.
    Used when Content Template is not available or not approved.
    
    Note: This only works within 24h session window!
    """
    captain_url = f"https://pickleballconnect.eu/pcl/team/{captain_token}"
    message = get_captain_invitation_message(team, captain_name, captain_url, language)
    
    print("📝 Using fallback text message (requires 24h session)")
    return send_whatsapp_message(captain_phone, message, test_mode=test_mode)


def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """
    Get captain invitation message in the specified language (fallback method)
    
    Args:
        team: PCLTeam object
        captain_name: Name of the captain
        captain_url: URL to captain dashboard
        language: Language code (EN, DE, ES, FR)
    
    Returns:
        str: Formatted invitation message
    """
    messages = {
        'EN': f"""🏆 PCL {team.tournament.name} - Team Captain Invitation

Hi {captain_name}! 👋

You have been selected as Captain for {team.country_flag} {team.country_name} {team.age_category}!

📋 Your responsibilities:
• Register your team players
• Ensure all profiles are complete
• Coordinate with your team

🔗 Your secret Captain Dashboard:
{captain_url}

⚠️ Keep this link private - only you should have access!

📅 Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Let's go! 🎾
WPC Series Europe""",

        'DE': f"""🏆 PCL {team.tournament.name} - Team-Kapitän Einladung

Hallo {captain_name}! 👋

Du wurdest als Kapitän für {team.country_flag} {team.country_name} {team.age_category} ausgewählt!

📋 Deine Aufgaben:
• Registriere deine Team-Spieler
• Stelle sicher, dass alle Profile vollständig sind
• Koordiniere dich mit deinem Team

🔗 Dein geheimes Kapitän-Dashboard:
{captain_url}

⚠️ Teile diesen Link nicht - nur du solltest Zugang haben!

📅 Anmeldeschluss: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Los geht's! 🎾
WPC Series Europe""",

        'ES': f"""🏆 PCL {team.tournament.name} - Invitación Capitán de Equipo

¡Hola {captain_name}! 👋

¡Has sido seleccionado como Capitán de {team.country_flag} {team.country_name} {team.age_category}!

📋 Tus responsabilidades:
• Registrar a los jugadores de tu equipo
• Asegurar que todos los perfiles estén completos
• Coordinar con tu equipo

🔗 Tu panel secreto de Capitán:
{captain_url}

⚠️ ¡Mantén este enlace privado - solo tú deberías tener acceso!

📅 Fecha límite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

¡Vamos! 🎾
WPC Series Europe""",

        'FR': f"""🏆 PCL {team.tournament.name} - Invitation Capitaine d'Équipe

Bonjour {captain_name}! 👋

Vous avez été sélectionné comme Capitaine pour {team.country_flag} {team.country_name} {team.age_category}!

📋 Vos responsabilités:
• Inscrire les joueurs de votre équipe
• S'assurer que tous les profils sont complets
• Coordonner avec votre équipe

🔗 Votre tableau de bord secret de Capitaine:
{captain_url}

⚠️ Gardez ce lien privé - vous seul devriez y avoir accès!

📅 Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

C'est parti! 🎾
WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """
    Get captain reminder message with team status
    
    Args:
        team: PCLTeam object
        captain_name: Name of the captain
        captain_url: URL to captain dashboard
        stats: Team stats dictionary
        language: Language code (EN, DE, ES, FR)
    
    Returns:
        str: Formatted reminder message
    """
    messages = {
        'EN': f"""⏰ PCL {team.tournament.name} - Reminder

Hi {captain_name}!

Your team {team.country_flag} {team.country_name} {team.age_category} is not yet complete!

📊 Current status:
👨 Men: {stats['men']}/{team.min_men}-{team.max_men}
👩 Women: {stats['women']}/{team.min_women}-{team.max_women}
✅ Complete profiles: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

🔗 Complete your team here:
{captain_url}

📅 Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Please ensure all players are registered with complete profiles!

WPC Series Europe""",

        'DE': f"""⏰ PCL {team.tournament.name} - Erinnerung

Hallo {captain_name}!

Dein Team {team.country_flag} {team.country_name} {team.age_category} ist noch nicht vollständig!

📊 Aktueller Status:
👨 Männer: {stats['men']}/{team.min_men}-{team.max_men}
👩 Frauen: {stats['women']}/{team.min_women}-{team.max_women}
✅ Vollständige Profile: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

🔗 Vervollständige dein Team hier:
{captain_url}

📅 Anmeldeschluss: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Bitte stelle sicher, dass alle Spieler mit vollständigen Profilen registriert sind!

WPC Series Europe""",

        'ES': f"""⏰ PCL {team.tournament.name} - Recordatorio

¡Hola {captain_name}!

¡Tu equipo {team.country_flag} {team.country_name} {team.age_category} aún no está completo!

📊 Estado actual:
👨 Hombres: {stats['men']}/{team.min_men}-{team.max_men}
👩 Mujeres: {stats['women']}/{team.min_women}-{team.max_women}
✅ Perfiles completos: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

🔗 Completa tu equipo aquí:
{captain_url}

📅 Fecha límite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

¡Por favor asegúrate de que todos los jugadores estén registrados con perfiles completos!

WPC Series Europe""",

        'FR': f"""⏰ PCL {team.tournament.name} - Rappel

Bonjour {captain_name}!

Votre équipe {team.country_flag} {team.country_name} {team.age_category} n'est pas encore complète!

📊 Statut actuel:
👨 Hommes: {stats['men']}/{team.min_men}-{team.max_men}
👩 Femmes: {stats['women']}/{team.min_women}-{team.max_women}
✅ Profils complets: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

🔗 Complétez votre équipe ici:
{captain_url}

📅 Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Veuillez vous assurer que tous les joueurs sont inscrits avec des profils complets!

WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_message_template(message_type, language, **kwargs):
    """
    Get message template by type and language
    
    Args:
        message_type: Type of message (invitation, reminder, update)
        language: Language code (EN, DE, ES, FR)
        **kwargs: Template variables
    
    Returns:
        str: Formatted message
    """
    templates = {
        'invitation': {
            'EN': """🎾 You're invited to {event_name}!

📅 Date: {start_date}{end_date_text}
📍 Location: {location}

{description}

Reply:
✅ YES - I'm interested!
ℹ️ INFO - Tell me more
❌ NO - Can't make it

WPC Series Europe""",

            'DE': """🎾 Du bist eingeladen zu {event_name}!

📅 Datum: {start_date}{end_date_text}
📍 Ort: {location}

{description}

Antworten:
✅ JA - Ich bin interessiert!
ℹ️ INFO - Mehr erfahren
❌ NEIN - Kann leider nicht

WPC Series Europe""",

            'ES': """🎾 ¡Estás invitado a {event_name}!

📅 Fecha: {start_date}{end_date_text}
📍 Lugar: {location}

{description}

Responde:
✅ SÍ - ¡Me interesa!
ℹ️ INFO - Cuéntame más
❌ NO - No puedo asistir

WPC Series Europe""",

            'FR': """🎾 Vous êtes invité à {event_name}!

📅 Date: {start_date}{end_date_text}
📍 Lieu: {location}

{description}

Répondez:
✅ OUI - Je suis intéressé!
ℹ️ INFO - Dites-m'en plus
❌ NON - Je ne peux pas

WPC Series Europe"""
        },
        
        'reminder': {
            'EN': """⏰ Reminder: {event_name}

📅 Date: {start_date}{end_date_text}
📍 Location: {location}

Don't forget to reply if you haven't already!

✅ YES | ℹ️ INFO | ❌ NO

WPC Series Europe""",

            'DE': """⏰ Erinnerung: {event_name}

📅 Datum: {start_date}{end_date_text}
📍 Ort: {location}

Vergiss nicht zu antworten, falls noch nicht geschehen!

✅ JA | ℹ️ INFO | ❌ NEIN

WPC Series Europe""",

            'ES': """⏰ Recordatorio: {event_name}

📅 Fecha: {start_date}{end_date_text}
📍 Lugar: {location}

¡No olvides responder si aún no lo has hecho!

✅ SÍ | ℹ️ INFO | ❌ NO

WPC Series Europe""",

            'FR': """⏰ Rappel: {event_name}

📅 Date: {start_date}{end_date_text}
📍 Lieu: {location}

N'oubliez pas de répondre si vous ne l'avez pas encore fait!

✅ OUI | ℹ️ INFO | ❌ NON

WPC Series Europe"""
        },
        
        'update': {
            'EN': """📢 Update: {event_name}

{description}

📅 Date: {start_date}{end_date_text}
📍 Location: {location}

WPC Series Europe""",

            'DE': """📢 Update: {event_name}

{description}

📅 Datum: {start_date}{end_date_text}
📍 Ort: {location}

WPC Series Europe""",

            'ES': """📢 Actualización: {event_name}

{description}

📅 Fecha: {start_date}{end_date_text}
📍 Lugar: {location}

WPC Series Europe""",

            'FR': """📢 Mise à jour: {event_name}

{description}

📅 Date: {start_date}{end_date_text}
📍 Lieu: {location}

WPC Series Europe"""
        }
    }
    
    # Get template
    template = templates.get(message_type, templates['invitation']).get(language, templates[message_type]['EN'])
    
    # Format end date text
    end_date_text = f" - {kwargs.get('end_date')}" if kwargs.get('end_date') else ""
    kwargs['end_date_text'] = end_date_text
    
    # Format message
    return template.format(**kwargs)


def send_profile_completion_link(player, test_mode=False):
    """
    Send profile completion link to a player
    
    Args:
        player: Player object with update_token
        test_mode: If True, only log without sending
    
    Returns:
        dict: Status of the send operation
    """
    if not player.update_token:
        return {'status': 'error', 'error': 'Player has no update token'}
    
    messages = {
        'EN': f"""👋 Hi {player.first_name}!

Please complete your player profile for WPC Series Europe.

🔗 Click here to update your profile:
{{profile_url}}

This helps us send you personalized invitations!

WPC Series Europe""",

        'DE': f"""👋 Hallo {player.first_name}!

Bitte vervollständige dein Spielerprofil für die WPC Series Europe.

🔗 Klicke hier, um dein Profil zu aktualisieren:
{{profile_url}}

Das hilft uns, dir personalisierte Einladungen zu senden!

WPC Series Europe""",

        'ES': f"""👋 ¡Hola {player.first_name}!

Por favor completa tu perfil de jugador para WPC Series Europe.

🔗 Haz clic aquí para actualizar tu perfil:
{{profile_url}}

¡Esto nos ayuda a enviarte invitaciones personalizadas!

WPC Series Europe""",

        'FR': f"""👋 Bonjour {player.first_name}!

Veuillez compléter votre profil de joueur pour WPC Series Europe.

🔗 Cliquez ici pour mettre à jour votre profil:
{{profile_url}}

Cela nous aide à vous envoyer des invitations personnalisées!

WPC Series Europe"""
    }
    
    # Build profile URL
    profile_url = f"https://pickleballconnect.eu/player/update/{player.update_token}"
    
    message = messages.get(player.preferred_language, messages['EN'])
    message = message.format(profile_url=profile_url)

    return send_whatsapp_message(player.phone, message, test_mode=test_mode)


def send_optin_request_template(player, test_mode=False):
    """
    Ask a player for WhatsApp consent using the approved opt-in template.

    Template Variables:
    - {{1}} = First name
    Quick replies carry the payloads OPTIN_YES / OPTIN_NO (see routes/webhook.py).

    Returns:
        dict: Status of the send operation
    """
    formatted_phone = format_phone_number(player.phone)
    if not formatted_phone:
        return {'status': 'error', 'error': f'Invalid phone number: {player.phone}'}

    language = (player.preferred_language or 'EN').upper()
    templates = TEMPLATE_SIDS['optin_request']
    template_sid = templates.get(language) or templates.get('EN')
    if not template_sid:
        return {'status': 'error',
                'error': 'Set TEMPLATE_OPTIN_REQUEST_DE/EN/ES/FR in environment variables'}

    content_variables = {'1': player.first_name}

    if test_mode:
        print(f"🧪 Test mode - opt-in template {template_sid} to {formatted_phone} not sent")
        return {'status': 'test_mode', 'template_sid': template_sid}

    try:
        client = get_twilio_client()
        if not client:
            return {'status': 'error', 'error': 'Twilio client not configured'}

        msg = client.messages.create(
            content_sid=template_sid,
            content_variables=json.dumps(content_variables),
            from_=TWILIO_WHATSAPP_NUMBER,
            to=formatted_phone
        )
        return {'status': 'sent', 'sid': msg.sid, 'template_sid': template_sid}

    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def get_optin_confirmation_message(language, accepted):
    """Reply to an opt-in answer (sent inside the 24h window opened by the player)."""
    messages = {
        True: {
            'EN': "✅ Thank you! You will receive information and your invitation to WPC Hannover (26–29 Nov 2026) here on WhatsApp. Reply STOP at any time to unsubscribe.",
            'DE': "✅ Danke! Du erhältst Infos und deine Einladung zur WPC Hannover (26.–29.11.2026) hier per WhatsApp. Antworte jederzeit mit STOP, um dich abzumelden.",
            'ES': "✅ ¡Gracias! Recibirás información y tu invitación a la WPC Hannover (26–29/11/2026) aquí por WhatsApp. Responde STOP en cualquier momento para darte de baja.",
            'FR': "✅ Merci ! Tu recevras les infos et ton invitation pour la WPC Hannover (26–29/11/2026) ici sur WhatsApp. Réponds STOP à tout moment pour te désinscrire.",
        },
        False: {
            'EN': "👍 No problem - we won't send you any more messages.",
            'DE': "👍 Kein Problem - wir schicken dir keine weiteren Nachrichten.",
            'ES': "👍 Sin problema, no te enviaremos más mensajes.",
            'FR': "👍 Pas de souci, nous ne t'enverrons plus de messages.",
        },
    }
    return messages[accepted].get((language or 'EN').upper(), messages[accepted]['EN'])