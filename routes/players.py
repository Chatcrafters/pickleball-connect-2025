from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Player

players = Blueprint('players', __name__)

@players.route('/')
def player_list():
    """List all players"""
    players = Player.query.order_by(Player.last_name).all()
    return render_template('player_list.html', players=players)

@players.route('/<int:player_id>')
def player_detail(player_id):
    """Show player details"""
    player = Player.query.get_or_404(player_id)
    return render_template('player_detail.html', player=player)

@players.route('/add', methods=['GET', 'POST'])
def add_player():
    """Add a new player"""
    if request.method == 'POST':
        player = Player(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            phone=request.form['phone'],
            email=request.form.get('email'),
            skill_level=request.form.get('skill_level'),
            city=request.form.get('city'),
            country=request.form.get('country'),
            preferred_language=request.form.get('preferred_language', 'EN')
        )
        
        try:
            db.session.add(player)
            db.session.commit()
            flash(f'Player {player.first_name} {player.last_name} added successfully!', 'success')
            return redirect(url_for('players.player_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding player: {str(e)}', 'danger')
    
    return render_template('player_form.html', player=None)

@players.route('/<int:player_id>/edit', methods=['GET', 'POST'])
def edit_player(player_id):
    """Edit a player"""
    player = Player.query.get_or_404(player_id)
    
    if request.method == 'POST':
        player.first_name = request.form['first_name']
        player.last_name = request.form['last_name']
        player.phone = request.form['phone']
        player.email = request.form.get('email')
        player.skill_level = request.form.get('skill_level')
        player.city = request.form.get('city')
        player.country = request.form.get('country')
        player.preferred_language = request.form.get('preferred_language', 'EN')
        
        try:
            db.session.commit()
            flash(f'Player {player.first_name} {player.last_name} updated successfully!', 'success')
            return redirect(url_for('players.player_detail', player_id=player.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating player: {str(e)}', 'danger')
    
    return render_template('player_form.html', player=player)

@players.route('/<int:player_id>/delete', methods=['POST'])
def delete_player(player_id):
    """Delete a player"""
    player = Player.query.get_or_404(player_id)
    
    try:
        db.session.delete(player)
        db.session.commit()
        flash(f'Player {player.first_name} {player.last_name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting player: {str(e)}', 'danger')
    
    return redirect(url_for('players.player_list'))