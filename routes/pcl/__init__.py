"""
PCL Routes Package

This package contains all PCL-related code organized into modules:
- constants.py: Configuration, file upload settings, template IDs
- translations.py: Multilingual UI strings (EN, DE, ES, FR)
- helpers.py: WhatsApp message templates and utility functions
"""

from .constants import (
    UPLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    CAPTAIN_INVITATION_TEMPLATES,
    allowed_file
)

from .translations import (
    TRANSLATIONS,
    get_translations
)

from .helpers import (
    send_captain_invitation_template,
    get_profile_completion_message,
    get_captain_invitation_message,
    get_captain_reminder_message
)
