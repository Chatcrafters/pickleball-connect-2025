# Pickleball Connect

A Flask web application for managing pickleball tournaments, events, and player registrations for the Professional Pickleball League (PCL) European circuit.

## Tech Stack

- **Backend**: Python 3.x, Flask 3.0
- **Database**: PostgreSQL (Supabase) / SQLite (local dev)
- **ORM**: SQLAlchemy
- **Frontend**: Bootstrap 5.3, Jinja2 templates
- **Messaging**: Twilio WhatsApp API
- **Storage**: Supabase Storage (photos)
- **Hosting**: Vercel (serverless)

## Project Structure

```
app.py              # Main Flask entry point
models.py           # SQLAlchemy database models
routes/             # Flask blueprints
  main.py           # Dashboard routes
  players.py        # Player management
  events.py         # Event management
  messages.py       # Message history
  admin.py          # Admin functions
  webhook.py        # Twilio webhooks
  pcl.py            # PCL tournament system (largest module)
templates/          # Jinja2 HTML templates
  pcl/              # PCL-specific templates
static/             # CSS, JS, venue data
utils/              # WhatsApp helpers, Supabase storage
```

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Production (Vercel handles this via vercel.json)
gunicorn app:app
```

## Environment Variables

Required in `.env`:
- `SECRET_KEY` - Flask secret key
- `DATABASE_URL` - PostgreSQL connection string
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` - Twilio config
- `TEMPLATE_CAPTAIN_INVITE_*` - WhatsApp template SIDs

## Key Models

- **Player** - Base player with profile, skills, contact info
- **Event** - Tournaments, workshops, clinics
- **PCLTournament** - PCL tournament events
- **PCLTeam** - National teams with captain tokens
- **PCLRegistration** - Player tournament registrations

## URL Prefixes

- `/` - Dashboard (main)
- `/players` - Player management
- `/events` - Event management
- `/pcl` - PCL tournament system
- `/admin` - Admin functions
- `/webhook` - Twilio webhooks

## Notes

- Multi-language support: EN, DE, ES, FR
- Tokens used for secure access: update_token, profile_token, captain_token
- Photos uploaded to Supabase Storage (5MB max)
- Database auto-creates tables via `db.create_all()` on startup
