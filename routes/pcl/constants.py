"""
PCL Constants and Configuration
"""

# File upload configuration
UPLOAD_FOLDER = 'static/uploads/pcl'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Content Template SIDs for Captain Invitations (approved by Meta)
CAPTAIN_INVITATION_TEMPLATES = {
    'EN': 'HX60bacc71dac06f81eff2227151389f6d',
    'DE': 'HX52b9ea2e53c93cec8195d82972a665d4',
    'ES': 'HX97d1eb9aabb2a2c968a47399d5c1689e',
    'FR': 'HX4de0671a9f29e7fa02e3cb3e94839809'
}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
