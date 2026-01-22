"""
PCL Helper Functions - WhatsApp messages and utilities
"""
import os
import json
from .constants import CAPTAIN_INVITATION_TEMPLATES


def send_captain_invitation_template(phone, captain_name, team_name, tournament_name, dashboard_url, deadline, language='EN'):
    """Send captain invitation using approved WhatsApp Content Template"""
    from twilio.rest import Client

    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    from_number = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

    content_sid = CAPTAIN_INVITATION_TEMPLATES.get(language.upper(), CAPTAIN_INVITATION_TEMPLATES['EN'])

    phone_clean = phone.strip().replace(' ', '').replace('-', '')
    if not phone_clean.startswith('+'):
        phone_clean = '+' + phone_clean
    to_number = f'whatsapp:{phone_clean}'

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            from_=from_number,
            to=to_number,
            content_sid=content_sid,
            content_variables=json.dumps({
                "1": tournament_name,
                "2": captain_name,
                "3": team_name,
                "4": dashboard_url,
                "5": deadline
            })
        )

        return {'status': 'sent', 'message_sid': message.sid}

    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def get_profile_completion_message(registration, profile_url, lang='EN'):
    """Get WhatsApp message for profile completion in the specified language"""

    team = registration.team
    tournament = team.tournament

    messages = {
        'EN': f"""PCL {tournament.name}

Hi {registration.first_name}!

You've been added to Team {team.country_flag} {team.country_name} ({team.age_category}).

Please complete your profile:
{profile_url}

Required:
- Profile photo
- Shirt name & size
- Short bio

Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Questions? Contact your team captain.

See you on the court!
WPC Series Europe""",

        'DE': f"""PCL {tournament.name}

Hallo {registration.first_name}!

Du wurdest zu Team {team.country_flag} {team.country_name} ({team.age_category}) hinzugefuegt.

Bitte vervollstaendige dein Profil:
{profile_url}

Erforderlich:
- Profilbild
- Shirt-Name & Groesse
- Kurze Bio

Deadline: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Fragen? Kontaktiere deinen Team-Kapitaen.

Bis bald auf dem Court!
WPC Series Europe""",

        'ES': f"""PCL {tournament.name}

Hola {registration.first_name}!

Has sido anadido al equipo {team.country_flag} {team.country_name} ({team.age_category}).

Por favor completa tu perfil:
{profile_url}

Requerido:
- Foto de perfil
- Nombre y talla de camiseta
- Breve biografia

Fecha limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Preguntas? Contacta a tu capitan.

Nos vemos en la cancha!
WPC Series Europe""",

        'FR': f"""PCL {tournament.name}

Bonjour {registration.first_name}!

Vous avez ete ajoute a l'equipe {team.country_flag} {team.country_name} ({team.age_category}).

Veuillez completer votre profil:
{profile_url}

Requis:
- Photo de profil
- Nom et taille du maillot
- Courte bio

Date limite: {tournament.registration_deadline.strftime('%d.%m.%Y')}

Questions? Contactez votre capitaine.

A bientot sur le court!
WPC Series Europe"""
    }

    return messages.get(lang, messages['EN'])


def get_captain_invitation_message(team, captain_name, captain_url, language='EN'):
    """Get captain invitation message for WhatsApp"""
    tournament = team.tournament
    deadline = tournament.registration_deadline.strftime('%d.%m.%Y')

    messages = {
        'EN': f"""PCL {tournament.name}

Hi {captain_name}!

You have been selected as captain for Team {team.country_flag} {team.country_name} ({team.age_category}).

Your captain dashboard:
{captain_url}

From your dashboard you can:
- Add players to your team
- Send profile completion links
- Track team status

Registration deadline: {deadline}

Good luck!
WPC Series Europe""",

        'DE': f"""PCL {tournament.name}

Hallo {captain_name}!

Du wurdest als Kapitaen fuer Team {team.country_flag} {team.country_name} ({team.age_category}) ausgewaehlt.

Dein Kapitaen-Dashboard:
{captain_url}

Von deinem Dashboard aus kannst du:
- Spieler zu deinem Team hinzufuegen
- Profilvervollstaendigungs-Links senden
- Team-Status verfolgen

Anmeldeschluss: {deadline}

Viel Erfolg!
WPC Series Europe""",

        'ES': f"""PCL {tournament.name}

Hola {captain_name}!

Has sido seleccionado como capitan del equipo {team.country_flag} {team.country_name} ({team.age_category}).

Tu panel de capitan:
{captain_url}

Desde tu panel puedes:
- Anadir jugadores a tu equipo
- Enviar enlaces para completar perfiles
- Seguir el estado del equipo

Fecha limite de registro: {deadline}

Buena suerte!
WPC Series Europe""",

        'FR': f"""PCL {tournament.name}

Bonjour {captain_name}!

Vous avez ete selectionne comme capitaine de l'equipe {team.country_flag} {team.country_name} ({team.age_category}).

Votre tableau de bord capitaine:
{captain_url}

Depuis votre tableau de bord vous pouvez:
- Ajouter des joueurs a votre equipe
- Envoyer des liens pour completer les profils
- Suivre le statut de l'equipe

Date limite d'inscription: {deadline}

Bonne chance!
WPC Series Europe"""
    }

    return messages.get(language, messages['EN'])


def get_captain_reminder_message(team, captain_name, captain_url, stats, language='EN'):
    """Get captain reminder message for WhatsApp"""
    tournament = team.tournament
    deadline = tournament.registration_deadline.strftime('%d.%m.%Y')

    messages = {
        'EN': f"""PCL {tournament.name} - Reminder

Hi {captain_name}!

Team {team.country_flag} {team.country_name} Status:
- Players: {stats['total']} ({stats['men']} men, {stats['women']} women)
- Complete profiles: {stats['men_complete'] + stats['women_complete']}
- Missing: {stats['total'] - stats['men_complete'] - stats['women_complete']}

Your dashboard:
{captain_url}

Deadline: {deadline}

Please ensure all players complete their profiles!

WPC Series Europe""",

        'DE': f"""PCL {tournament.name} - Erinnerung

Hallo {captain_name}!

Team {team.country_flag} {team.country_name} Status:
- Spieler: {stats['total']} ({stats['men']} Maenner, {stats['women']} Frauen)
- Vollstaendige Profile: {stats['men_complete'] + stats['women_complete']}
- Fehlend: {stats['total'] - stats['men_complete'] - stats['women_complete']}

Dein Dashboard:
{captain_url}

Deadline: {deadline}

Bitte stelle sicher, dass alle Spieler ihre Profile vervollstaendigen!

WPC Series Europe""",

        'ES': f"""PCL {tournament.name} - Recordatorio

Hola {captain_name}!

Estado del equipo {team.country_flag} {team.country_name}:
- Jugadores: {stats['total']} ({stats['men']} hombres, {stats['women']} mujeres)
- Perfiles completos: {stats['men_complete'] + stats['women_complete']}
- Faltan: {stats['total'] - stats['men_complete'] - stats['women_complete']}

Tu panel:
{captain_url}

Fecha limite: {deadline}

Por favor asegurate de que todos los jugadores completen sus perfiles!

WPC Series Europe""",

        'FR': f"""PCL {tournament.name} - Rappel

Bonjour {captain_name}!

Statut equipe {team.country_flag} {team.country_name}:
- Joueurs: {stats['total']} ({stats['men']} hommes, {stats['women']} femmes)
- Profils complets: {stats['men_complete'] + stats['women_complete']}
- Manquants: {stats['total'] - stats['men_complete'] - stats['women_complete']}

Votre tableau de bord:
{captain_url}

Date limite: {deadline}

Veuillez vous assurer que tous les joueurs completent leurs profils!

WPC Series Europe"""
    }

    return messages.get(language, messages['EN'])
