import os
from flask import Flask
from models import db
from routes.main import main
from routes.players import players
from routes.events import events
from routes.messages import messages
from routes.admin import admin
from routes.webhook import webhook
from dotenv import load_dotenv
from routes.pcl import pcl

# Load environment variables from .env
load_dotenv()

# DEBUG: Check if DATABASE_URL is loaded
database_url = os.environ.get('DATABASE_URL')
print(f"🔍 DEBUG: DATABASE_URL loaded = {bool(database_url)}")
if database_url:
    print(f"🔍 DEBUG: Database URL starts with: {database_url[:30]}...")

app = Flask(__name__)

# Configuration for Supabase
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Supabase PostgreSQL Database URL
if database_url and database_url.startswith('postgres://'):
    # Fix for SQLAlchemy - needs postgresql:// instead of postgres://
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///pickleball_connect.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(main)
app.register_blueprint(players, url_prefix='/players')
app.register_blueprint(events, url_prefix='/events')
app.register_blueprint(messages, url_prefix='/messages')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(webhook, url_prefix='/webhook')
app.register_blueprint(pcl, url_prefix='/pcl')

# Create tables on first run
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"⚠️  Database error: {e}")
        print("Note: Tables may already exist, continuing...")

if __name__ == '__main__':
    # Lokale Entwicklung
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("=" * 60)
    print("🚀 Starting Pickleball Connect")
    print(f"📱 WhatsApp Integration: Ready")
    
    if database_url:
        if 'supabase' in database_url:
            print(f"🗄️  Database: Supabase (PostgreSQL) ✅")
        else:
            print(f"🗄️  Database: PostgreSQL")
    else:
        print(f"🗄️  Database: SQLite (Local) ⚠️")
    
    print(f"🌐 Server starting on 0.0.0.0:{port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)