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