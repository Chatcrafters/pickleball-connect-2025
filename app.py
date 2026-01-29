import os
from flask import Flask
from flask_migrate import Migrate
from models import db
from routes.main import main
from routes.players import players
from routes.events import events
from routes.messages import messages
from routes.admin import admin
from routes.webhook import webhook
from dotenv import load_dotenv
from routes.pcl import pcl
from routes.auth import auth
from checkin import checkin

# Load environment variables from .env
load_dotenv()

# DEBUG: Check if DATABASE_URL is loaded
database_url = os.environ.get('DATABASE_URL')
print(f"DEBUG: DATABASE_URL loaded = {bool(database_url)}")
if database_url:
    print(f"DEBUG: Database URL starts with: {database_url[:30]}...")

app = Flask(__name__)

# Configuration - SECRET_KEY must be set in environment
secret_key = os.environ.get('SECRET_KEY')
if not secret_key:
    raise RuntimeError(
        "SECRET_KEY environment variable is required! "
        "Set it in your .env file or environment."
    )
app.config['SECRET_KEY'] = secret_key

# Database configuration: SQLite for development, Supabase for production
if os.environ.get('FLASK_ENV') == 'development' or not database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pickleball.db'
else:
    # Fix for SQLAlchemy - needs postgresql:// instead of postgres://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4MB max upload (Vercel limit is 4.5MB)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)
migrate = Migrate(app, db)

# Register blueprints
app.register_blueprint(main)
app.register_blueprint(players, url_prefix='/players')
app.register_blueprint(events, url_prefix='/events')
app.register_blueprint(messages, url_prefix='/messages')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(webhook, url_prefix='/webhook')
app.register_blueprint(pcl, url_prefix='/pcl')
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(checkin)

# Create tables on first run
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Database error: {e}")
        print("Note: Tables may already exist, continuing...")

if __name__ == '__main__':
    # Lokale Entwicklung
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("=" * 60)
    print("Starting Pickleball Connect")
    print(f"WhatsApp Integration: Ready")
    
    if database_url:
        if 'supabase' in database_url:
            print(f"Database: Supabase (PostgreSQL)")
        else:
            print(f"Database: PostgreSQL")
    else:
        print(f"Database: SQLite (Local)")
    
    print(f"Server starting on 0.0.0.0:{port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)