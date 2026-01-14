import os
from twilio.rest import Client

# Twilio configuration - loaded from environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')

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
        
        # Format phone number for WhatsApp
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
        
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number
        )
        
        print(f"âœ… Message sent to {to_number}! SID: {message_obj.sid}")
        
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
        captain_url: Full URL to captain dashboard
        language: Language code (EN, DE, ES, FR)
    
    Returns:
        str: Formatted message
    """
    tournament = team.tournament
    
    messages = {
        'EN': f"""🏆 PCL {tournament.location} {tournament.start_date.year} - Team Captain Invitation

Hello {captain_name}! 👋

You are the captain of Team {team.country_flag} {team.country_name} {team.age_category} at the Pickleball Champions League!

📅 {tournament.start_date.strftime('%d.%m.')} - {tournament.end_date.strftime('%d.%m.%Y')}
📍 {tournament.location}

🔗 Your Captain Dashboard:
{captain_url}

➡️ What you need to do:
1. Open the link above
2. Register yourself (photo, bio, shirt size)
3. Add your team members
4. Make sure all profiles are complete

👥 Team Requirements:
• Minimum {team.min_men} men + {team.min_women} women
• Everyone needs: Photo, Bio, Shirt Name & Size

⏰ Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Questions? Just reach out!

Good luck! 🎾
WPC Series Europe""",

        'DE': f"""🏆 PCL {tournament.location} {tournament.start_date.year} - Team Captain Einladung

Hallo {captain_name}! 👋

Du bist der Kapitän von Team {team.country_flag} {team.country_name} {team.age_category} bei der Pickleball Champions League!

📅 {tournament.start_date.strftime('%d.%m.')} - {tournament.end_date.strftime('%d.%m.%Y')}
📍 {tournament.location}

🔗 Dein Captain-Dashboard:
{captain_url}

➡️ Was du tun musst:
1. Öffne den Link oben
2. Registriere dich selbst (Foto, Bio, Shirt-Größe)
3. Füge deine Teammitglieder hinzu
4. Stelle sicher, dass alle Profile vollständig sind

👥 Team-Anforderungen:
• Mindestens {team.min_men} Männer + {team.min_women} Frauen
• Jeder braucht: Foto, Bio, Shirt-Name & Größe

⏰ Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Bei Fragen melde dich einfach!

Viel Erfolg! 🎾
WPC Series Europe""",

        'ES': f"""🏆 PCL {tournament.location} {tournament.start_date.year} - Invitación Capitán

¡Hola {captain_name}! 👋

Eres el capitán del Equipo {team.country_flag} {team.country_name} {team.age_category} en la Pickleball Champions League!

📅 {tournament.start_date.strftime('%d.%m.')} - {tournament.end_date.strftime('%d.%m.%Y')}
📍 {tournament.location}

🔗 Tu Panel de Capitán:
{captain_url}

➡️ Lo que debes hacer:
1. Abre el enlace
2. Regístrate (foto, bio, talla de camiseta)
3. Añade a tus compañeros de equipo
4. Asegúrate de que todos los perfiles estén completos

👥 Requisitos del equipo:
• Mínimo {team.min_men} hombres + {team.min_women} mujeres
• Todos necesitan: Foto, Bio, Nombre y Talla de camiseta

⏰ Fecha límite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

¿Preguntas? ¡Escríbeme!

¡Buena suerte! 🎾
WPC Series Europe""",

        'FR': f"""🏆 PCL {tournament.location} {tournament.start_date.year} - Invitation Capitaine

Bonjour {captain_name}! 👋

Tu es le capitaine de l'équipe {team.country_flag} {team.country_name} {team.age_category} à la Pickleball Champions League!

📅 {tournament.start_date.strftime('%d.%m.')} - {tournament.end_date.strftime('%d.%m.%Y')}
📍 {tournament.location}

🔗 Ton tableau de bord Capitaine:
{captain_url}

➡️ Ce que tu dois faire:
1. Ouvre le lien ci-dessus
2. Inscris-toi (photo, bio, taille de maillot)
3. Ajoute tes coéquipiers
4. Assure-toi que tous les profils sont complets

👥 Exigences de l'équipe:
• Minimum {team.min_men} hommes + {team.min_women} femmes
• Chacun a besoin de: Photo, Bio, Nom et Taille de maillot

⏰ Date limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Des questions? Contacte-moi!

Bonne chance! 🎾
WPC Series Europe"""
    }
    
    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """
    Get captain reminder message in the specified language
    
    Args:
        team: PCLTeam object
        captain_name: Name of the captain
        captain_url: Full URL to captain dashboard
        stats: Team statistics dict
        language: Language code (EN, DE, ES, FR)
    
    Returns:
        str: Formatted message
    """
    tournament = team.tournament
    
    # Calculate missing requirements
    men_needed = max(0, team.min_men - stats['men'])
    women_needed = max(0, team.min_women - stats['women'])
    incomplete_profiles = stats['total'] - (stats['men_complete'] + stats['women_complete'])
    
    messages = {
        'EN': f"""⏰ Reminder: PCL {tournament.location} {tournament.start_date.year}

Hello {captain_name}!

Your Team {team.country_flag} {team.country_name} {team.age_category} status:

{"✅ Men: " + str(stats['men']) + "/" + str(team.min_men) if stats['men'] >= team.min_men else "❌ Still need " + str(men_needed) + " more men"}
{"✅ Women: " + str(stats['women']) + "/" + str(team.min_women) if stats['women'] >= team.min_women else "❌ Still need " + str(women_needed) + " more women"}
{"⚠️ " + str(incomplete_profiles) + " profile(s) incomplete" if incomplete_profiles > 0 else "✅ All profiles complete"}

🔗 Your Dashboard:
{captain_url}

⏰ Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Please complete your team as soon as possible!

WPC Series Europe""",

        'DE': f"""⏰ Erinnerung: PCL {tournament.location} {tournament.start_date.year}

Hallo {captain_name}!

Dein Team {team.country_flag} {team.country_name} {team.age_category} Status:

{"✅ Männer: " + str(stats['men']) + "/" + str(team.min_men) if stats['men'] >= team.min_men else "❌ Noch " + str(men_needed) + " Männer benötigt"}
{"✅ Frauen: " + str(stats['women']) + "/" + str(team.min_women) if stats['women'] >= team.min_women else "❌ Noch " + str(women_needed) + " Frauen benötigt"}
{"⚠️ " + str(incomplete_profiles) + " Profil(e) unvollständig" if incomplete_profiles > 0 else "✅ Alle Profile vollständig"}

🔗 Dein Dashboard:
{captain_url}

⏰ Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Bitte vervollständige dein Team so schnell wie möglich!

WPC Series Europe""",

        'ES': f"""⏰ Recordatorio: PCL {tournament.location} {tournament.start_date.year}

¡Hola {captain_name}!

Estado de tu Equipo {team.country_flag} {team.country_name} {team.age_category}:

{"✅ Hombres: " + str(stats['men']) + "/" + str(team.min_men) if stats['men'] >= team.min_men else "❌ Faltan " + str(men_needed) + " hombres"}
{"✅ Mujeres: " + str(stats['women']) + "/" + str(team.min_women) if stats['women'] >= team.min_women else "❌ Faltan " + str(women_needed) + " mujeres"}
{"⚠️ " + str(incomplete_profiles) + " perfil(es) incompleto(s)" if incomplete_profiles > 0 else "✅ Todos los perfiles completos"}

🔗 Tu Dashboard:
{captain_url}

⏰ Fecha límite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

¡Por favor completa tu equipo lo antes posible!

WPC Series Europe""",

        'FR': f"""⏰ Rappel: PCL {tournament.location} {tournament.start_date.year}

Bonjour {captain_name}!

Statut de ton équipe {team.country_flag} {team.country_name} {team.age_category}:

{"✅ Hommes: " + str(stats['men']) + "/" + str(team.min_men) if stats['men'] >= team.min_men else "❌ Il manque encore " + str(men_needed) + " hommes"}
{"✅ Femmes: " + str(stats['women']) + "/" + str(team.min_women) if stats['women'] >= team.min_women else "❌ Il manque encore " + str(women_needed) + " femmes"}
{"⚠️ " + str(incomplete_profiles) + " profil(s) incomplet(s)" if incomplete_profiles > 0 else "✅ Tous les profils sont complets"}

🔗 Ton Dashboard:
{captain_url}

⏰ Date limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Complète ton équipe dès que possible!

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