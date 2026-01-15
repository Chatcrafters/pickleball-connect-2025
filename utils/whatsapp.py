"""
WhatsApp Utility Module with Twilio Content Templates Support
For Pickleball Connect - WPC Series Europe
"""

import os
from twilio.rest import Client

# Twilio credentials from environment
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

# Content Template SIDs - Add your actual SIDs here after creating templates
CONTENT_TEMPLATES = {
    'captain_invitation': {
        'DE': os.getenv('TEMPLATE_CAPTAIN_INVITE_DE', 'HX52b9ea2e53c93cec8195d82972a665d4'),
        'EN': os.getenv('TEMPLATE_CAPTAIN_INVITE_EN', ''),  # Add your EN template SID
        'ES': os.getenv('TEMPLATE_CAPTAIN_INVITE_ES', ''),  # Add your ES template SID
        'FR': os.getenv('TEMPLATE_CAPTAIN_INVITE_FR', ''),  # Add your FR template SID
    },
    'captain_reminder': {
        'DE': os.getenv('TEMPLATE_CAPTAIN_REMINDER_DE', ''),
        'EN': os.getenv('TEMPLATE_CAPTAIN_REMINDER_EN', ''),
        'ES': os.getenv('TEMPLATE_CAPTAIN_REMINDER_ES', ''),
        'FR': os.getenv('TEMPLATE_CAPTAIN_REMINDER_FR', ''),
    }
}


def get_twilio_client():
    """Get Twilio client instance"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("⚠️ Twilio credentials not configured!")
        return None
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_message(to_number, message, test_mode=False):
    """
    Send a simple WhatsApp message (free-form text)
    
    Args:
        to_number: Phone number with country code (e.g., +491234567890)
        message: Message text to send
        test_mode: If True, only print to console without sending
    
    Returns:
        dict with status and details
    """
    # Clean phone number
    to_number = to_number.strip()
    if not to_number.startswith('+'):
        to_number = '+' + to_number
    
    # Format for WhatsApp
    whatsapp_to = f"whatsapp:{to_number}"
    
    if test_mode:
        print(f"\n📱 [TEST MODE] WhatsApp Message:")
        print(f"   To: {to_number}")
        print(f"   Message: {message[:100]}...")
        return {'status': 'test_mode', 'to': to_number}
    
    try:
        client = get_twilio_client()
        if not client:
            return {'status': 'error', 'error': 'Twilio not configured'}
        
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=whatsapp_to
        )
        
        print(f"✅ Message sent to {to_number}: {msg.sid}")
        return {'status': 'sent', 'sid': msg.sid, 'to': to_number}
        
    except Exception as e:
        print(f"❌ Error sending to {to_number}: {str(e)}")
        return {'status': 'error', 'error': str(e), 'to': to_number}


def send_content_template(to_number, template_name, language, variables, test_mode=False):
    """
    Send a WhatsApp message using a Content Template
    
    Args:
        to_number: Phone number with country code
        template_name: Name of the template (e.g., 'captain_invitation')
        language: Language code (DE, EN, ES, FR)
        variables: Dict with variable values (e.g., {'1': 'Malaga 2026', '2': 'Max', ...})
        test_mode: If True, only print to console
    
    Returns:
        dict with status and details
    """
    # Clean phone number
    to_number = to_number.strip()
    if not to_number.startswith('+'):
        to_number = '+' + to_number
    
    whatsapp_to = f"whatsapp:{to_number}"
    
    # Get template SID for language
    template_sid = CONTENT_TEMPLATES.get(template_name, {}).get(language.upper())
    
    if not template_sid:
        print(f"⚠️ No template found for {template_name} in {language}, falling back to EN")
        template_sid = CONTENT_TEMPLATES.get(template_name, {}).get('EN')
    
    if not template_sid:
        print(f"❌ No template SID configured for {template_name}")
        return {'status': 'error', 'error': f'Template {template_name} not configured'}
    
    if test_mode:
        print(f"\n📱 [TEST MODE] Content Template Message:")
        print(f"   To: {to_number}")
        print(f"   Template: {template_name} ({language})")
        print(f"   Template SID: {template_sid}")
        print(f"   Variables: {variables}")
        return {'status': 'test_mode', 'to': to_number, 'template': template_name}
    
    try:
        client = get_twilio_client()
        if not client:
            return {'status': 'error', 'error': 'Twilio not configured'}
        
        # Send using content template
        msg = client.messages.create(
            content_sid=template_sid,
            content_variables=variables,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=whatsapp_to
        )
        
        print(f"✅ Template message sent to {to_number}: {msg.sid}")
        return {'status': 'sent', 'sid': msg.sid, 'to': to_number, 'template': template_name}
        
    except Exception as e:
        print(f"❌ Error sending template to {to_number}: {str(e)}")
        return {'status': 'error', 'error': str(e), 'to': to_number}


def send_captain_invitation_template(team, captain_name, captain_phone, captain_token, language='EN', test_mode=False):
    """
    Send captain invitation using Content Template
    
    Args:
        team: PCLTeam object
        captain_name: Captain's first name
        captain_phone: Captain's phone number
        captain_token: Team's captain token for URL
        language: Language code (DE, EN, ES, FR)
        test_mode: If True, only print to console
    
    Returns:
        dict with status and details
    """
    # Format deadline
    deadline = team.tournament.registration_deadline.strftime('%d.%m.%Y')
    
    # Team display name
    team_display = f"{team.country_flag} {team.country_name} {team.age_category}"
    
    # Variables for template
    # {{1}} = Tournament Name
    # {{2}} = Captain Name
    # {{3}} = Team Name
    # {{4}} = Captain Token (for URL)
    # {{5}} = Deadline
    variables = {
        "1": team.tournament.name,
        "2": captain_name,
        "3": team_display,
        "4": captain_token,
        "5": deadline
    }
    
    return send_content_template(
        to_number=captain_phone,
        template_name='captain_invitation',
        language=language,
        variables=variables,
        test_mode=test_mode
    )


# ============================================================================
# LEGACY FUNCTIONS (for backward compatibility)
# ============================================================================

def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """
    Legacy function - Generate captain invitation message text
    Used as fallback if Content Templates are not configured
    """
    messages = {
        'EN': f"""🏆 PCL {team.tournament.name} - Team Captain Invitation

Hello {captain_name}! 👋

You have been selected as Captain for {team.country_flag} {team.country_name} {team.age_category}!

📋 Your tasks:
• Register your team players
• Make sure all profiles are complete
• Coordinate with your team

🔗 Your secret Captain Dashboard:
{captain_url}

⚠️ Keep this link private!

📅 Deadline: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Let's go! 🎾
Sergio Ruiz Caro
WPC Series & PCL Europe""",

        'DE': f"""🏆 PCL {team.tournament.name} - Team-Kapitän Einladung

Hallo {captain_name}! 👋

Du wurdest als Kapitän für {team.country_flag} {team.country_name} {team.age_category} ausgewählt!

📋 Deine Aufgaben:
• Registriere deine Team-Spieler
• Stelle sicher, dass alle Profile vollständig sind
• Koordiniere dich mit deinem Team

🔗 Dein geheimes Kapitän-Dashboard:
{captain_url}

⚠️ Teile diesen Link nicht!

📅 Anmeldeschluss: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Los geht's! 🎾
Sergio Ruiz Caro
WPC Series & PCL Europe""",

        'ES': f"""🏆 PCL {team.tournament.name} - Invitación Capitán de Equipo

¡Hola {captain_name}! 👋

¡Has sido seleccionado como Capitán de {team.country_flag} {team.country_name} {team.age_category}!

📋 Tus tareas:
• Registrar a los jugadores de tu equipo
• Asegurar que todos los perfiles estén completos
• Coordinarte con tu equipo

🔗 Tu panel secreto de Capitán:
{captain_url}

⚠️ ¡No compartas este enlace!

📅 Fecha límite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

¡Vamos! 🎾
Sergio Ruiz Caro
WPC Series & PCL Europe""",

        'FR': f"""🏆 PCL {team.tournament.name} - Invitation Capitaine d'Équipe

Bonjour {captain_name}! 👋

Vous avez été sélectionné comme Capitaine de {team.country_flag} {team.country_name} {team.age_category}!

📋 Vos tâches:
• Inscrire les joueurs de votre équipe
• Vérifier que tous les profils sont complets
• Coordonner avec votre équipe

🔗 Votre tableau de bord Capitaine:
{captain_url}

⚠️ Ne partagez pas ce lien!

📅 Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

C'est parti! 🎾
Sergio Ruiz Caro
WPC Series & PCL Europe"""
    }
    
    return messages.get(language.upper(), messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """
    Legacy function - Generate captain reminder message text
    """
    days_left = (team.tournament.registration_deadline - __import__('datetime').datetime.now()).days
    
    messages = {
        'EN': f"""⏰ PCL {team.tournament.name} - Reminder!

Hi {captain_name}!

Your team {team.country_flag} {team.country_name} {team.age_category} is not complete yet!

📊 Current status:
• Men: {stats['men']}/{team.min_men}-{team.max_men}
• Women: {stats['women']}/{team.min_women}-{team.max_women}
• Complete profiles: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Only {days_left} days left!

🔗 Complete your team now:
{captain_url}

WPC Series & PCL Europe""",

        'DE': f"""⏰ PCL {team.tournament.name} - Erinnerung!

Hallo {captain_name}!

Dein Team {team.country_flag} {team.country_name} {team.age_category} ist noch nicht vollständig!

📊 Aktueller Status:
• Männer: {stats['men']}/{team.min_men}-{team.max_men}
• Frauen: {stats['women']}/{team.min_women}-{team.max_women}
• Vollständige Profile: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Nur noch {days_left} Tage!

🔗 Vervollständige dein Team jetzt:
{captain_url}

WPC Series & PCL Europe""",

        'ES': f"""⏰ PCL {team.tournament.name} - ¡Recordatorio!

¡Hola {captain_name}!

Tu equipo {team.country_flag} {team.country_name} {team.age_category} aún no está completo!

📊 Estado actual:
• Hombres: {stats['men']}/{team.min_men}-{team.max_men}
• Mujeres: {stats['women']}/{team.min_women}-{team.max_women}
• Perfiles completos: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ ¡Solo quedan {days_left} días!

🔗 Completa tu equipo ahora:
{captain_url}

WPC Series & PCL Europe""",

        'FR': f"""⏰ PCL {team.tournament.name} - Rappel!

Bonjour {captain_name}!

Votre équipe {team.country_flag} {team.country_name} {team.age_category} n'est pas encore complète!

📊 Statut actuel:
• Hommes: {stats['men']}/{team.min_men}-{team.max_men}
• Femmes: {stats['women']}/{team.min_women}-{team.max_women}
• Profils complets: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Plus que {days_left} jours!

🔗 Complétez votre équipe maintenant:
{captain_url}

WPC Series & PCL Europe"""
    }
    
    return messages.get(language.upper(), messages['EN'])


def get_message_template(message_type, language, **kwargs):
    """
    Legacy function - Get message template for events
    """
    templates = {
        'invitation': {
            'EN': """🎾 You're invited to {event_name}!

📅 Date: {start_date}
📍 Location: {location}

{description}

Reply:
✅ YES - I'm interested!
ℹ️ INFO - Tell me more
❌ NO - Can't make it

WPC Series Europe""",

            'DE': """🎾 Du bist eingeladen zu {event_name}!

📅 Datum: {start_date}
📍 Ort: {location}

{description}

Antworte mit:
✅ JA - Ich bin dabei!
ℹ️ INFO - Mehr erfahren
❌ NEIN - Kann nicht

WPC Series Europe""",

            'ES': """🎾 ¡Estás invitado a {event_name}!

📅 Fecha: {start_date}
📍 Lugar: {location}

{description}

Responde:
✅ SI - ¡Me interesa!
ℹ️ INFO - Cuéntame más
❌ NO - No puedo

WPC Series Europe""",

            'FR': """🎾 Tu es invité à {event_name}!

📅 Date: {start_date}
📍 Lieu: {location}

{description}

Réponds:
✅ OUI - Je suis intéressé!
ℹ️ INFO - Plus d'infos
❌ NON - Pas possible

WPC Series Europe"""
        }
    }
    
    template = templates.get(message_type, templates['invitation'])
    message = template.get(language.upper(), template['EN'])
    
    return message.format(**kwargs)


def send_profile_completion_link(player, test_mode=False):
    """
    Send profile completion link to a player
    """
    from flask import url_for
    
    messages = {
        'EN': f"""👋 Hi {player.first_name}!

Please complete your player profile for WPC Series Europe.

🔗 Click here to update your profile:
{{profile_url}}

This helps us provide you with personalized event invitations!

WPC Series Europe""",

        'DE': f"""👋 Hallo {player.first_name}!

Bitte vervollständige dein Spielerprofil für die WPC Series Europe.

🔗 Klicke hier um dein Profil zu aktualisieren:
{{profile_url}}

Das hilft uns, dir personalisierte Event-Einladungen zu senden!

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
    
    # Build profile URL (this needs to be called within app context)
    try:
        profile_url = url_for('players.update_profile', token=player.update_token, _external=True)
    except:
        profile_url = f"https://pickleballconnect.eu/player/update/{player.update_token}"
    
    message = messages.get(player.preferred_language, messages['EN'])
    message = message.format(profile_url=profile_url)
    
    return send_whatsapp_message(player.phone, message, test_mode=test_mode)