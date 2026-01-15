import os
from twilio.rest import Client

# Twilio configuration - loaded from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

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
    phone = phone.replace('whatsapp:', '')
    
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
    
    return f'whatsapp:{phone}'


def send_whatsapp_message(to_number, message, test_mode=True):
    """
    Send a WhatsApp message using Twilio
    
    Args:
        to_number: Recipient phone number (with country code)
        message: Message content
        test_mode: If True, only print message instead of sending
    
    Returns:
        dict: Status of the message
    """
    if test_mode or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print(f"\n{'='*60}")
        print(f"ðŸ“± [TEST MODE] WhatsApp to {to_number}:")
        print(f"{'='*60}")
        print(message)
        print(f"{'='*60}\n")
        return {'status': 'test_mode', 'sid': 'test_message_id'}
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Format phone number properly for WhatsApp
        formatted_number = format_phone_number(to_number)
        if not formatted_number:
            print(f"❌ Invalid phone number: {to_number}")
            return {
                'status': 'failed',
                'error': 'Invalid phone number'
            }
        
        # Ensure from number is also properly formatted
        from_number = TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith('whatsapp:'):
            from_number = f'whatsapp:{from_number}'
        
        print(f"📤 Sending WhatsApp: FROM={from_number} TO={formatted_number}")
        
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=formatted_number
        )
        
        print(f"✅ Message sent to {formatted_number}! SID: {message_obj.sid}")
        
        return {
            'status': 'sent',
            'sid': message_obj.sid,
            'to': to_number
        }
    except Exception as e:
        print(f"âŒ Error sending WhatsApp message: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }

def send_profile_completion_link(player, test_mode=False):
    """
    Send profile completion link to a player
    
    Args:
        player: Player object
        test_mode: If True, only print message instead of sending
    
    Returns:
        dict: Status of the message
    """
    # Generate token if not exists
    if not player.update_token:
        player.generate_update_token()
    
    update_url = player.get_update_url()
    
    # Messages in different languages
    messages = {
        'EN': f"""ðŸŽ¾ Welcome to WPC Series Europe!

Hi {player.first_name}! ðŸ‘‹

Please complete your player profile to participate in our tournaments:

{update_url}

See you on the courts! ðŸ“
WPC Series Europe""",
        
        'DE': f"""ðŸŽ¾ Willkommen bei WPC Series Europe!

Hallo {player.first_name}! ðŸ‘‹

Bitte vervollstÃ¤ndige dein Spielerprofil, um an unseren Turnieren teilzunehmen:

{update_url}

Wir sehen uns auf dem Platz! ðŸ“
WPC Series Europe""",
        
        'ES': f"""ðŸŽ¾ Â¡Bienvenido a WPC Series Europe!

Â¡Hola {player.first_name}! ðŸ‘‹

Por favor completa tu perfil de jugador para participar en nuestros torneos:

{update_url}

Â¡Nos vemos en las canchas! ðŸ“
WPC Series Europe""",
        
        'FR': f"""ðŸŽ¾ Bienvenue Ã  WPC Series Europe!

Bonjour {player.first_name}! ðŸ‘‹

Veuillez complÃ©ter votre profil de joueur pour participer Ã  nos tournois:

{update_url}

Ã€ bientÃ´t sur les courts! ðŸ“
WPC Series Europe"""
    }
    
    message = messages.get(player.preferred_language, messages['EN'])
    
    return send_whatsapp_message(player.phone, message, test_mode=test_mode)


def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """
    Get captain invitation message in the specified language
    
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

⚠️ Halte diesen Link privat - nur du solltest Zugang haben!

📅 Anmeldeschluss: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

Los geht's! 🎾
WPC Series Europe""",

        'ES': f"""🏆 PCL {team.tournament.name} - Invitación de Capitán

¡Hola {captain_name}! 👋

¡Has sido seleccionado como Capitán de {team.country_flag} {team.country_name} {team.age_category}!

📋 Tus responsabilidades:
• Registrar a los jugadores de tu equipo
• Asegurar que todos los perfiles estén completos
• Coordinar con tu equipo

🔗 Tu Panel de Capitán secreto:
{captain_url}

⚠️ ¡Mantén este enlace privado - solo tú debes tener acceso!

📅 Fecha límite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

¡Vamos! 🎾
WPC Series Europe""",

        'FR': f"""🏆 PCL {team.tournament.name} - Invitation Capitaine

Bonjour {captain_name}! 👋

Vous avez été sélectionné comme Capitaine de {team.country_flag} {team.country_name} {team.age_category}!

📋 Vos responsabilités:
• Inscrire les joueurs de votre équipe
• S'assurer que tous les profils sont complets
• Coordonner avec votre équipe

🔗 Votre tableau de bord Capitaine secret:
{captain_url}

⚠️ Gardez ce lien privé - seul vous devez y avoir accès!

📅 Date limite: {team.tournament.registration_deadline.strftime('%d.%m.%Y %H:%M')}

C'est parti! 🎾
WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """
    Get captain reminder message in the specified language
    
    Args:
        team: PCLTeam object
        captain_name: Name of the captain
        captain_url: URL to captain dashboard
        stats: Team statistics dict
        language: Language code (EN, DE, ES, FR)
    
    Returns:
        str: Formatted reminder message
    """
    days_left = (team.tournament.registration_deadline - __import__('datetime').datetime.now()).days
    
    messages = {
        'EN': f"""⏰ PCL Reminder - {team.country_flag} {team.country_name} {team.age_category}

Hi {captain_name}!

Your team registration is incomplete:
👨 Men: {stats['men']}/{team.min_men}-{team.max_men}
👩 Women: {stats['women']}/{team.min_women}-{team.max_women}
✅ Complete profiles: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Only {days_left} days left!

🔗 Complete your team now:
{captain_url}

WPC Series Europe""",

        'DE': f"""⏰ PCL Erinnerung - {team.country_flag} {team.country_name} {team.age_category}

Hallo {captain_name}!

Deine Team-Registrierung ist unvollständig:
👨 Männer: {stats['men']}/{team.min_men}-{team.max_men}
👩 Frauen: {stats['women']}/{team.min_women}-{team.max_women}
✅ Vollständige Profile: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Nur noch {days_left} Tage!

🔗 Vervollständige dein Team jetzt:
{captain_url}

WPC Series Europe""",

        'ES': f"""⏰ Recordatorio PCL - {team.country_flag} {team.country_name} {team.age_category}

¡Hola {captain_name}!

Tu registro de equipo está incompleto:
👨 Hombres: {stats['men']}/{team.min_men}-{team.max_men}
👩 Mujeres: {stats['women']}/{team.min_women}-{team.max_women}
✅ Perfiles completos: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ ¡Solo quedan {days_left} días!

🔗 Completa tu equipo ahora:
{captain_url}

WPC Series Europe""",

        'FR': f"""⏰ Rappel PCL - {team.country_flag} {team.country_name} {team.age_category}

Bonjour {captain_name}!

Votre inscription d'équipe est incomplète:
👨 Hommes: {stats['men']}/{team.min_men}-{team.max_men}
👩 Femmes: {stats['women']}/{team.min_women}-{team.max_women}
✅ Profils complets: {stats['men_complete'] + stats['women_complete']}/{stats['total']}

⚠️ Plus que {days_left} jours!

🔗 Complétez votre équipe maintenant:
{captain_url}

WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_message_template(message_type, language='EN', **kwargs):
    """
    Get a message template in the specified language
    
    Args:
        message_type: Type of message (invitation, reminder, update, custom)
        language: Language code (EN, DE, ES, FR)
        **kwargs: Variables for the template
    
    Returns:
        str: Formatted message
    """
    # Prepare end date line if end_date is provided
    end_date_line = ""
    if kwargs.get('end_date'):
        date_labels = {
            'EN': 'ðŸ“… End: ',
            'DE': 'ðŸ“… Ende: ',
            'ES': 'ðŸ“… Fin: ',
            'FR': 'ðŸ“… Fin: '
        }
        end_date_line = date_labels.get(language, date_labels['EN']) + kwargs.get('end_date') + '\n'
    
    templates = {
        'invitation': {
            'EN': """ðŸŽ¾ {event_name}

ðŸ“… Start: {start_date}
{end_date_line}ðŸ“ {location}

{description}

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Please reply with:
âœ… YES - I'm interested
â„¹ï¸ INFO - Send me more details
âŒ NO - Not interested

Looking forward to hearing from you!""",
            
            'DE': """ðŸŽ¾ {event_name}

ðŸ“… Start: {start_date}
{end_date_line}ðŸ“ {location}

{description}

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Bitte antworte mit:
âœ… JA - Ich bin interessiert
â„¹ï¸ INFO - Schick mir mehr Details
âŒ NEIN - Nicht interessiert

Wir freuen uns auf deine Antwort!""",
            
            'ES': """ðŸŽ¾ {event_name}

ðŸ“… Inicio: {start_date}
{end_date_line}ðŸ“ {location}

{description}

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Por favor responde con:
âœ… SÃ - Estoy interesado
â„¹ï¸ INFO - EnvÃ­ame mÃ¡s detalles
âŒ NO - No estoy interesado

Â¡Esperamos tu respuesta!""",
            
            'FR': """ðŸŽ¾ {event_name}

ðŸ“… DÃ©but: {start_date}
{end_date_line}ðŸ“ {location}

{description}

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Veuillez rÃ©pondre avec:
âœ… OUI - Je suis intÃ©ressÃ©
â„¹ï¸ INFO - Envoyez-moi plus de dÃ©tails
âŒ NON - Pas intÃ©ressÃ©

Au plaisir de vous lire!"""
        },
        'reminder': {
            'EN': """â° Reminder: {event_name}

ðŸ“… Start: {start_date}
{end_date_line}ðŸ“ {location}

Don't forget to confirm your participation!

Reply with:
âœ… YES - Confirmed
âŒ NO - Cancel""",
            
            'DE': """â° Erinnerung: {event_name}

ðŸ“… Start: {start_date}
{end_date_line}ðŸ“ {location}

Vergiss nicht, deine Teilnahme zu bestÃ¤tigen!

Antworte mit:
âœ… JA - BestÃ¤tigt
âŒ NEIN - Absagen""",
            
            'ES': """â° Recordatorio: {event_name}

ðŸ“… Inicio: {start_date}
{end_date_line}ðŸ“ {location}

Â¡No olvides confirmar tu participaciÃ³n!

Responde con:
âœ… SÃ - Confirmado
âŒ NO - Cancelar""",
            
            'FR': """â° Rappel: {event_name}

ðŸ“… DÃ©but: {start_date}
{end_date_line}ðŸ“ {location}

N'oubliez pas de confirmer votre participation!

RÃ©pondez avec:
âœ… OUI - ConfirmÃ©
âŒ NON - Annuler"""
        },
        'update': {
            'EN': "ðŸ“¢ Update for {event_name}:\n\n{message}",
            'DE': "ðŸ“¢ Update zu {event_name}:\n\n{message}",
            'ES': "ðŸ“¢ ActualizaciÃ³n de {event_name}:\n\n{message}",
            'FR': "ðŸ“¢ Mise Ã  jour pour {event_name}:\n\n{message}"
        }
    }
    
    if message_type == 'custom':
        return kwargs.get('message', '')
    
    template = templates.get(message_type, {}).get(language, templates[message_type]['EN'])
    
    # Format the template with all variables
    return template.format(
        event_name=kwargs.get('event_name', ''),
        start_date=kwargs.get('start_date', ''),
        end_date_line=end_date_line,
        location=kwargs.get('location', ''),
        description=kwargs.get('description', ''),
        message=kwargs.get('message', '')
    )