import os
from twilio.rest import Client

# Twilio configuration - use environment variables
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'

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
        print(f"📱 [TEST MODE] WhatsApp to {to_number}:")
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
        
        print(f"✅ Message sent to {to_number}! SID: {message_obj.sid}")
        
        return {
            'status': 'sent',
            'sid': message_obj.sid,
            'to': to_number
        }
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e)
        }

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
            'EN': '📅 End: ',
            'DE': '📅 Ende: ',
            'ES': '📅 Fin: ',
            'FR': '📅 Fin: '
        }
        end_date_line = date_labels.get(language, date_labels['EN']) + kwargs.get('end_date') + '\n'
    
    templates = {
        'invitation': {
            'EN': """🎾 {event_name}

📅 Start: {start_date}
{end_date_line}📍 {location}

{description}

━━━━━━━━━━━━━━━━━━━━━━
Please reply with:
✅ YES - I'm interested
ℹ️ INFO - Send me more details
❌ NO - Not interested

Looking forward to hearing from you!""",
            
            'DE': """🎾 {event_name}

📅 Start: {start_date}
{end_date_line}📍 {location}

{description}

━━━━━━━━━━━━━━━━━━━━━━
Bitte antworte mit:
✅ JA - Ich bin interessiert
ℹ️ INFO - Schick mir mehr Details
❌ NEIN - Nicht interessiert

Wir freuen uns auf deine Antwort!""",
            
            'ES': """🎾 {event_name}

📅 Inicio: {start_date}
{end_date_line}📍 {location}

{description}

━━━━━━━━━━━━━━━━━━━━━━
Por favor responde con:
✅ SÍ - Estoy interesado
ℹ️ INFO - Envíame más detalles
❌ NO - No estoy interesado

¡Esperamos tu respuesta!""",
            
            'FR': """🎾 {event_name}

📅 Début: {start_date}
{end_date_line}📍 {location}

{description}

━━━━━━━━━━━━━━━━━━━━━━
Veuillez répondre avec:
✅ OUI - Je suis intéressé
ℹ️ INFO - Envoyez-moi plus de détails
❌ NON - Pas intéressé

Au plaisir de vous lire!"""
        },
        'reminder': {
            'EN': """⏰ Reminder: {event_name}

📅 Start: {start_date}
{end_date_line}📍 {location}

Don't forget to confirm your participation!

Reply with:
✅ YES - Confirmed
❌ NO - Cancel""",
            
            'DE': """⏰ Erinnerung: {event_name}

📅 Start: {start_date}
{end_date_line}📍 {location}

Vergiss nicht, deine Teilnahme zu bestätigen!

Antworte mit:
✅ JA - Bestätigt
❌ NEIN - Absagen""",
            
            'ES': """⏰ Recordatorio: {event_name}

📅 Inicio: {start_date}
{end_date_line}📍 {location}

¡No olvides confirmar tu participación!

Responde con:
✅ SÍ - Confirmado
❌ NO - Cancelar""",
            
            'FR': """⏰ Rappel: {event_name}

📅 Début: {start_date}
{end_date_line}📍 {location}

N'oubliez pas de confirmer votre participation!

Répondez avec:
✅ OUI - Confirmé
❌ NON - Annuler"""
        },
        'update': {
            'EN': "📢 Update for {event_name}:\n\n{message}",
            'DE': "📢 Update zu {event_name}:\n\n{message}",
            'ES': "📢 Actualización de {event_name}:\n\n{message}",
            'FR': "📢 Mise à jour pour {event_name}:\n\n{message}"
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