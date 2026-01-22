from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Message, Player
from utils.whatsapp import send_whatsapp_message

messages = Blueprint('messages', __name__)

@messages.route('/')
def message_history():
    """Show message history with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)  # Max 100 per page

    pagination = Message.query.order_by(Message.sent_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return render_template('message_history.html',
                          messages=pagination.items,
                          pagination=pagination)

@messages.route('/send-bulk', methods=['GET', 'POST'])
def send_bulk_message():
    """Send bulk message to selected players"""
    if request.method == 'POST':
        player_ids = request.form.getlist('player_ids')
        message_content = request.form.get('message')
        test_mode = request.form.get('test_mode') == 'on'
        
        if not player_ids:
            flash('No players selected.', 'warning')
            return redirect(request.url)
        
        if not message_content:
            flash('Message content is required.', 'warning')
            return redirect(request.url)
        
        sent_count = 0
        for player_id in player_ids:
            player = Player.query.get(int(player_id))
            if player:
                result = send_whatsapp_message(player.phone, message_content, test_mode=test_mode)
                
                if result['status'] in ['sent', 'test_mode']:
                    # Log message
                    msg = Message(
                        player_id=player.id,
                        message_type='bulk',
                        content=message_content,
                        status='sent' if not test_mode else 'test'
                    )
                    db.session.add(msg)
                    sent_count += 1
        
        try:
            db.session.commit()
            mode_text = " (TEST MODE)" if test_mode else ""
            flash(f'{sent_count} message(s) sent{mode_text}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error sending messages: {str(e)}', 'danger')
        
        return redirect(url_for('messages.message_history'))
    
    # GET request - show form
    players = Player.query.order_by(Player.last_name).all()
    return render_template('send_bulk_message.html', players=players)