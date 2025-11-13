import os
from twilio.rest import Client

# Twilio configuration
TWILIO_ACCOUNT_SID = 'ACa142cbc9a326e0a1af5956eda50c265a'
TWILIO_AUTH_TOKEN = '1314d20bde7c642ded0f133953a8b2f6'
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
        print(f"[TEST MODE] WhatsApp to {to_number}:")
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
        
        print(f"Message sent to {to_number}! SID: {message_obj.sid}")
        
        return {
            'status': 'sent',
            'sid': message_obj.sid,
            'to': to_number
        }
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")
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
            'EN': 'End: ',
            'DE': 'Ende: ',
            'ES': 'Fin: ',
            'FR': 'Fin: '
        }
        end_date_line = date_labels.get(language, date_labels['EN']) + kwargs.get('end_date') + '\n'
    
    templates = {
        'invitation': {
            'EN': """*** {event_name} ***

Date: {start_date}
{end_date_line}Location: {location}

{description}

----------------------------------
Please reply with:

YES - I'm interested
INFO - Send me more details
NO - Not interested

Looking forward to hearing from you!

WPC Series Europe""",
            
            'DE': """*** {event_name} ***

Datum: {start_date}
{end_date_line}Ort: {location}

{description}

----------------------------------
Bitte antworte mit:

JA - Ich bin interessiert
INFO - Schick mir mehr Details
NEIN - Nicht interessiert

Wir freuen uns auf deine Antwort!

WPC Series Europe""",
            
            'ES': """*** {event_name} ***

Fecha: {start_date}
{end_date_line}Lugar: {location}

{description}

----------------------------------
Por favor responde con:

SI - Estoy interesado
INFO - Enviame mas detalles
NO - No estoy interesado

Esperamos tu respuesta!

WPC Series Europe""",
            
            'FR': """*** {event_name} ***

Date: {start_date}
{end_date_line}Lieu: {location}

{description}

----------------------------------
Veuillez repondre avec:

OUI - Je suis interesse
INFO - Envoyez-moi plus de details
NON - Pas interesse

Au plaisir de vous lire!

WPC Series Europe"""
        },
        'reminder': {
            'EN': """*** REMINDER: {event_name} ***

Date: {start_date}
{end_date_line}Location: {location}

Don't forget to confirm your participation!

Reply with:
YES - Confirmed
NO - Cancel

WPC Series Europe""",
            
            'DE': """*** ERINNERUNG: {event_name} ***

Datum: {start_date}
{end_date_line}Ort: {location}

Vergiss nicht, deine Teilnahme zu bestatigen!

Antworte mit:
JA - Bestatigt
NEIN - Absagen

WPC Series Europe""",
            
            'ES': """*** RECORDATORIO: {event_name} ***

Fecha: {start_date}
{end_date_line}Lugar: {location}

No olvides confirmar tu participacion!

Responde con:
SI - Confirmado
NO - Cancelar

WPC Series Europe""",
            
            'FR': """*** RAPPEL: {event_name} ***

Date: {start_date}
{end_date_line}Lieu: {location}

N'oubliez pas de confirmer votre participation!

Repondez avec:
OUI - Confirme
NON - Annuler

WPC Series Europe"""
        },
        'update': {
            'EN': "*** UPDATE: {event_name} ***\n\n{message}\n\nWPC Series Europe",
            'DE': "*** UPDATE: {event_name} ***\n\n{message}\n\nWPC Series Europe",
            'ES': "*** ACTUALIZACION: {event_name} ***\n\n{message}\n\nWPC Series Europe",
            'FR': "*** MISE A JOUR: {event_name} ***\n\n{message}\n\nWPC Series Europe"
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