from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Sponsor, EventSponsor, Event, PCLTournament, get_whatsapp_sponsor_block

sponsors = Blueprint('sponsors', __name__, url_prefix='/sponsors')


@sponsors.route('/')
def sponsor_list():
    """List all sponsors."""
    all_sponsors = Sponsor.query.order_by(Sponsor.tier, Sponsor.name).all()
    return render_template('sponsors/sponsor_list.html', sponsors=all_sponsors)


@sponsors.route('/new', methods=['GET', 'POST'])
def sponsor_new():
    """Create a new sponsor."""
    if request.method == 'POST':
        sponsor = Sponsor(
            name=request.form.get('name', '').strip(),
            logo_url=request.form.get('logo_url', '').strip() or None,
            website_url=request.form.get('website_url', '').strip() or None,
            tier=request.form.get('tier', 'partner'),
            tracking_url=request.form.get('tracking_url', '').strip() or None,
            tracking_code=request.form.get('tracking_code', '').strip() or None,
            whatsapp_text_en=request.form.get('whatsapp_text_en', '').strip() or None,
            whatsapp_text_de=request.form.get('whatsapp_text_de', '').strip() or None,
            whatsapp_text_es=request.form.get('whatsapp_text_es', '').strip() or None,
            whatsapp_text_fr=request.form.get('whatsapp_text_fr', '').strip() or None,
            show_on_boarding_pass='show_on_boarding_pass' in request.form,
            boarding_pass_text=request.form.get('boarding_pass_text', '').strip() or None,
            revenue_model=request.form.get('revenue_model', '').strip() or None,
            revenue_amount=float(request.form.get('revenue_amount') or 0) or None,
            contact_person=request.form.get('contact_person', '').strip() or None,
            contact_email=request.form.get('contact_email', '').strip() or None,
            notes=request.form.get('notes', '').strip() or None,
        )
        db.session.add(sponsor)
        db.session.commit()
        flash(f'Sponsor "{sponsor.name}" erstellt.', 'success')
        return redirect(url_for('sponsors.sponsor_detail', id=sponsor.id))

    return render_template('sponsors/sponsor_form.html', sponsor=None)


@sponsors.route('/<int:id>')
def sponsor_detail(id):
    """Show sponsor detail with placements."""
    sponsor = Sponsor.query.get_or_404(id)
    placements = EventSponsor.query.filter_by(sponsor_id=sponsor.id).all()
    events = Event.query.order_by(Event.start_date.desc()).all()
    tournaments = PCLTournament.query.order_by(PCLTournament.start_date.desc()).all()
    return render_template('sponsors/sponsor_detail.html',
                           sponsor=sponsor, placements=placements,
                           events=events, tournaments=tournaments)


@sponsors.route('/<int:id>/edit', methods=['GET', 'POST'])
def sponsor_edit(id):
    """Edit an existing sponsor."""
    sponsor = Sponsor.query.get_or_404(id)

    if request.method == 'POST':
        sponsor.name = request.form.get('name', '').strip()
        sponsor.logo_url = request.form.get('logo_url', '').strip() or None
        sponsor.website_url = request.form.get('website_url', '').strip() or None
        sponsor.tier = request.form.get('tier', 'partner')
        sponsor.tracking_url = request.form.get('tracking_url', '').strip() or None
        sponsor.tracking_code = request.form.get('tracking_code', '').strip() or None
        sponsor.whatsapp_text_en = request.form.get('whatsapp_text_en', '').strip() or None
        sponsor.whatsapp_text_de = request.form.get('whatsapp_text_de', '').strip() or None
        sponsor.whatsapp_text_es = request.form.get('whatsapp_text_es', '').strip() or None
        sponsor.whatsapp_text_fr = request.form.get('whatsapp_text_fr', '').strip() or None
        sponsor.show_on_boarding_pass = 'show_on_boarding_pass' in request.form
        sponsor.boarding_pass_text = request.form.get('boarding_pass_text', '').strip() or None
        sponsor.revenue_model = request.form.get('revenue_model', '').strip() or None
        sponsor.revenue_amount = float(request.form.get('revenue_amount') or 0) or None
        sponsor.contact_person = request.form.get('contact_person', '').strip() or None
        sponsor.contact_email = request.form.get('contact_email', '').strip() or None
        sponsor.notes = request.form.get('notes', '').strip() or None
        db.session.commit()
        flash(f'Sponsor "{sponsor.name}" aktualisiert.', 'success')
        return redirect(url_for('sponsors.sponsor_detail', id=sponsor.id))

    return render_template('sponsors/sponsor_form.html', sponsor=sponsor)


@sponsors.route('/<int:id>/delete', methods=['POST'])
def sponsor_delete(id):
    """Delete a sponsor and all placements."""
    sponsor = Sponsor.query.get_or_404(id)
    EventSponsor.query.filter_by(sponsor_id=sponsor.id).delete()
    db.session.delete(sponsor)
    db.session.commit()
    flash(f'Sponsor "{sponsor.name}" geloescht.', 'success')
    return redirect(url_for('sponsors.sponsor_list'))


@sponsors.route('/<int:id>/toggle-active', methods=['POST'])
def sponsor_toggle_active(id):
    """Toggle sponsor active status."""
    sponsor = Sponsor.query.get_or_404(id)
    sponsor.is_active = not sponsor.is_active
    db.session.commit()
    status = 'aktiviert' if sponsor.is_active else 'deaktiviert'
    flash(f'Sponsor "{sponsor.name}" {status}.', 'success')
    return redirect(url_for('sponsors.sponsor_detail', id=sponsor.id))


@sponsors.route('/<int:id>/add-placement', methods=['POST'])
def add_placement(id):
    """Add a new EventSponsor placement."""
    sponsor = Sponsor.query.get_or_404(id)

    event_id = request.form.get('event_id', type=int) or None
    pcl_tournament_id = request.form.get('pcl_tournament_id', type=int) or None

    if not event_id and not pcl_tournament_id:
        flash('Bitte ein Event oder Tournament auswaehlen.', 'danger')
        return redirect(url_for('sponsors.sponsor_detail', id=sponsor.id))

    placement = EventSponsor(
        sponsor_id=sponsor.id,
        event_id=event_id,
        pcl_tournament_id=pcl_tournament_id,
        show_in_whatsapp='show_in_whatsapp' in request.form,
        show_on_boarding_pass='show_on_boarding_pass' in request.form,
        show_on_event_page='show_on_event_page' in request.form,
        display_order=request.form.get('display_order', 0, type=int),
        tier_override=request.form.get('tier_override', '').strip() or None,
    )
    db.session.add(placement)
    db.session.commit()
    flash('Placement hinzugefuegt.', 'success')
    return redirect(url_for('sponsors.sponsor_detail', id=sponsor.id))


@sponsors.route('/placement/<int:id>/delete', methods=['POST'])
def placement_delete(id):
    """Remove a placement."""
    placement = EventSponsor.query.get_or_404(id)
    sponsor_id = placement.sponsor_id
    db.session.delete(placement)
    db.session.commit()
    flash('Placement entfernt.', 'success')
    return redirect(url_for('sponsors.sponsor_detail', id=sponsor_id))


@sponsors.route('/placement/<int:id>/toggle', methods=['POST'])
def placement_toggle(id):
    """Toggle placement active status."""
    placement = EventSponsor.query.get_or_404(id)
    placement.is_active = not placement.is_active
    db.session.commit()
    status = 'aktiviert' if placement.is_active else 'deaktiviert'
    flash(f'Placement {status}.', 'success')
    return redirect(url_for('sponsors.sponsor_detail', id=placement.sponsor_id))


@sponsors.route('/preview-whatsapp')
def preview_whatsapp():
    """WhatsApp preview page with event/language selector."""
    events = Event.query.order_by(Event.start_date.desc()).all()
    tournaments = PCLTournament.query.order_by(PCLTournament.start_date.desc()).all()

    event_id = request.args.get('event_id', type=int)
    pcl_tournament_id = request.args.get('pcl_tournament_id', type=int)
    language = request.args.get('language', 'EN')

    preview_text = ''
    if event_id or pcl_tournament_id:
        preview_text = get_whatsapp_sponsor_block(
            event_id=event_id,
            pcl_tournament_id=pcl_tournament_id,
            language=language
        )

    return render_template('sponsors/preview_whatsapp.html',
                           events=events, tournaments=tournaments,
                           preview_text=preview_text,
                           selected_event_id=event_id,
                           selected_tournament_id=pcl_tournament_id,
                           selected_language=language)
