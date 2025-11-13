from flask import Blueprint, request
from models import db, Player, Event, PlayerResponse, event_players
from datetime import datetime
from utils.whatsapp import send_whatsapp_message

webhook = Blueprint('webhook', __name__)

def send_confirmation_message(player, event, response_type):
    """Send automatic confirmation based on player response"""
    
    # Simplified response messages in different languages
    responses = {
        'interested': {
            'EN': f"""âœ… Great! Thank you for your interest in {event.name}.

We will contact you soon with more details.

WPC Series Europe""",
            
            'DE': f"""âœ… Super! Danke fÃ¼r dein Interesse an {event.name}.

Wir melden uns bald mit weiteren Details.

WPC Series Europe""",
            
            'ES': f"""âœ… Â¡Genial! Gracias por tu interÃ©s en {event.name}.

Te contactaremos pronto con mÃ¡s detalles.

WPC Series Europe""",
            
            'FR': f"""âœ… Super! Merci pour votre intÃ©rÃªt pour {event.name}.

Nous vous contacterons bientÃ´t avec plus de dÃ©tails.

WPC Series Europe"""
        },
        'more_info': {
            'EN': f"""âœ… Great! Thank you for your interest in {event.name}.

We will contact you soon with more details.

WPC Series Europe""",
            
            'DE': f"""âœ… Super! Danke fÃ¼r dein Interesse an {event.name}.

Wir melden uns bald mit weiteren Details.

WPC Series Europe""",
            
            'ES': f"""âœ… Â¡Genial! Gracias por tu interÃ©s en {event.name}.

Te contactaremos pronto con mÃ¡s detalles.

WPC Series Europe""",
            
            'FR': f"""âœ… Super! Merci pour votre intÃ©rÃªt pour {event.name}.

Nous vous contacterons bientÃ´t avec plus de dÃ©tails.

WPC Series Europe"""
        },
        'not_interested': {
            'EN': f"""ðŸ‘‹ Understood. Thank you for your response.

We'll keep you informed about future events.

See you soon!

WPC Series Europe""",
            
            'DE': f"""ðŸ‘‹ Verstanden. Danke fÃ¼r deine RÃ¼ckmeldung.

Wir halten dich Ã¼ber zukÃ¼nftige Events auf dem Laufenden.

Bis bald!

WPC Series Europe""",
            
            'ES': f"""ðŸ‘‹ Entendido. Gracias por tu respuesta.

Te mantendremos informado sobre futuros eventos.

Â¡Hasta pronto!

WPC Series Europe""",
            
            'FR': f"""ðŸ‘‹ Compris. Merci pour votre rÃ©ponse.

Nous vous tiendrons informÃ© des Ã©vÃ©nements futurs.

Ã€ bientÃ´t!

WPC Series Europe"""
        }
    }
    
    # Get message in player's language
    message = responses.get(response_type, {}).get(
        player.preferred_language,
        responses[response_type]['EN']
    )
    
    # Send confirmation (NOT in test mode!)
    result = send_whatsapp_message(player.phone, message, test_mode=False)
    print(f"ðŸ“¤ Confirmation sent to {player.first_name}: {response_type}")
    return result

@webhook.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages from Twilio"""
    
    # Get data from Twilio
    from_number = request.form.get('From', '').replace('whatsapp:', '')
    body = request.form.get('Body', '').strip().upper()
    
    print(f"\n{'='*60}")
    print(f"ðŸ“± Received WhatsApp from {from_number}")
    print(f"ðŸ’¬ Message: {body}")
    print(f"{'='*60}")
    
    # Find player by phone number
    player = Player.query.filter_by(phone=from_number).first()
    
    if not player:
        print(f"âŒ Player not found: {from_number}")
        return '', 200
    
    print(f"ðŸ‘¤ Found player: {player.first_name} {player.last_name}")
    
    # Determine response type - using startswith for flexibility
    response_type = None
    body_clean = body.strip().upper()
    
    # Interested responses
    if (body_clean in ['YES', 'JA', 'SI', 'OUI', 'Y', 'S'] or 
        body_clean.startswith('YES') or body_clean.startswith('JA') or 
        body_clean.startswith('SI') or body_clean.startswith('OUI')):
        response_type = 'interested'
    # More info responses  
    elif (body_clean in ['INFO', 'INFORMATION', 'MORE', 'MEHR', 'I'] or
          body_clean.startswith('INFO') or body_clean.startswith('MORE') or
          body_clean.startswith('MEHR') or body_clean.startswith('MAS')):
        response_type = 'more_info'
    # Not interested responses
    elif (body_clean in ['NO', 'NEIN', 'NON', 'N'] or
          body_clean.startswith('NO') or body_clean.startswith('NEIN')):
        response_type = 'not_interested'
    else:
        print(f"âš ï¸ Unknown response: {body_clean}")
        print(f"   Expected: YES/JA/SI, INFO, or NO/NEIN")
        print(f"   Bytes: {body_clean.encode('utf-8')}")
        return '', 200
    
    print(f"âœ… Response type: {response_type}")
    
    # Find the most recent event invitation for this player
    latest_invitation = db.session.execute(
        db.select(event_players.c.event_id).where(
            event_players.c.player_id == player.id
        ).order_by(event_players.c.event_id.desc())
    ).first()
    
    if not latest_invitation:
        print(f"âŒ No event invitation found for player {player.id}")
        return '', 200
    
    event_id = latest_invitation[0]
    event = Event.query.get(event_id)
    
    print(f"ðŸŽ¾ Event: {event.name}")
    
    # Update response status in event_players table
    db.session.execute(
        db.update(event_players).where(
            event_players.c.player_id == player.id,
            event_players.c.event_id == event_id
        ).values(
            response_status=response_type,
            response_date=datetime.utcnow()
        )
    )
    
    # Log the response
    response_log = PlayerResponse(
        player_id=player.id,
        event_id=event_id,
        response_text=body,
        response_type=response_type,
        processed=True
    )
    db.session.add(response_log)
    
    try:
        db.session.commit()
        print(f"âœ… Response saved to database!")
        
        # Send confirmation message back to player
        send_confirmation_message(player, event, response_type)
        
        print(f"{'='*60}\n")
        
    except Exception as e:
        db.session.rollback()
        print(f"âŒ Error saving response: {str(e)}")
        print(f"{'='*60}\n")
    
    return '', 200