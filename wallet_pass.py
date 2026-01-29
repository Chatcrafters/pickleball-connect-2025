"""
Apple Wallet Pass Generator for WPC Check-in System
Generates .pkpass files for Apple Wallet
"""

import json
import hashlib
import zipfile
import os
import base64
from io import BytesIO
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

# Configuration
TEAM_ID = "22LC4K2G55"
PASS_TYPE_ID = "pass.eu.pickleballconnect.wpc"
ORGANIZATION_NAME = "World Pickleball Championship"

# Paths to certificates (relative to app root) - used in development
CERT_PATH = "certificates/wpc_pass_cert.pem"
KEY_PATH = "certificates/wpc_pass.key"
WWDR_PATH = "certificates/AppleWWDRCAG4.pem"  # Apple WWDR certificate

# Environment variable names for production (Vercel)
ENV_CERT = "APPLE_PASS_CERT"
ENV_KEY = "APPLE_PASS_KEY"
ENV_WWDR = "APPLE_WWDR_CERT"

# Colors
WPC_GREEN = "#2E9E4B"
WPC_ORANGE = "#F5A623"
WPC_WHITE = "#FFFFFF"


def rgb_from_hex(hex_color):
    """Convert hex color to rgb() format"""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"rgb({r}, {g}, {b})"


def create_pass_json(participant, tournament, checkin, serial_number):
    """Create the pass.json content"""

    pass_data = {
        "formatVersion": 1,
        "teamIdentifier": TEAM_ID,
        "passTypeIdentifier": PASS_TYPE_ID,
        "organizationName": ORGANIZATION_NAME,
        "serialNumber": serial_number,
        "description": f"{tournament.name} Check-in Pass",

        # Colors
        "backgroundColor": rgb_from_hex(WPC_GREEN),
        "foregroundColor": rgb_from_hex(WPC_WHITE),
        "labelColor": rgb_from_hex("#E8F5E9"),

        # Barcode
        "barcodes": [{
            "format": "PKBarcodeFormatQR",
            "message": participant.checkin_token,
            "messageEncoding": "iso-8859-1",
            "altText": f"ID: {participant.id}"
        }],

        # Generic pass style (event ticket)
        "eventTicket": {
            "headerFields": [
                {
                    "key": "status",
                    "label": "STATUS",
                    "value": "CHECKED IN",
                    "textAlignment": "PKTextAlignmentRight"
                }
            ],
            "primaryFields": [
                {
                    "key": "name",
                    "label": "PLAYER",
                    "value": f"{participant.first_name} {participant.last_name}"
                }
            ],
            "secondaryFields": [
                {
                    "key": "tournament",
                    "label": "EVENT",
                    "value": tournament.name
                },
                {
                    "key": "location",
                    "label": "LOCATION",
                    "value": tournament.location
                }
            ],
            "auxiliaryFields": [
                {
                    "key": "country",
                    "label": "COUNTRY",
                    "value": participant.country or "International"
                },
                {
                    "key": "tshirt",
                    "label": "T-SHIRT",
                    "value": checkin.tshirt_size or "-"
                },
                {
                    "key": "date",
                    "label": "CHECK-IN",
                    "value": checkin.checked_in_at.strftime("%d %b %Y %H:%M")
                }
            ],
            "backFields": [
                {
                    "key": "participant_id",
                    "label": "Participant ID",
                    "value": str(participant.id)
                },
                {
                    "key": "checkin_id",
                    "label": "Check-in ID",
                    "value": str(checkin.id)
                },
                {
                    "key": "email",
                    "label": "Email",
                    "value": participant.email or "-"
                },
                {
                    "key": "emergency_contact",
                    "label": "Emergency Contact",
                    "value": f"{checkin.emergency_contact_name or '-'} ({checkin.emergency_contact_phone or '-'})"
                },
                {
                    "key": "info",
                    "label": "Info",
                    "value": "Present this pass at the welcome pack station. For support: info@pickleballconnect.eu"
                }
            ]
        },

        # Relevance
        "relevantDate": tournament.start_date.isoformat() if hasattr(tournament.start_date, 'isoformat') else str(tournament.start_date),

        # Voiding
        "voided": False
    }

    return json.dumps(pass_data, indent=2)


def create_manifest(files_dict):
    """Create manifest.json with SHA1 hashes of all files"""
    manifest = {}
    for filename, content in files_dict.items():
        if isinstance(content, str):
            content = content.encode('utf-8')
        manifest[filename] = hashlib.sha1(content).hexdigest()
    # Use compact JSON without newlines to avoid line-ending issues
    return json.dumps(manifest, separators=(',', ':'), sort_keys=True)


def load_certificate_data():
    """
    Load certificate data from environment variables (production) or files (development).
    Returns tuple of (cert_data, key_data, wwdr_data) as bytes.
    """
    # Check for environment variables first (Vercel/production)
    cert_b64 = os.environ.get(ENV_CERT)
    key_b64 = os.environ.get(ENV_KEY)
    wwdr_b64 = os.environ.get(ENV_WWDR)

    if cert_b64 and key_b64:
        # Production: decode from Base64 environment variables
        cert_data = base64.b64decode(cert_b64)
        key_data = base64.b64decode(key_b64)
        wwdr_data = base64.b64decode(wwdr_b64) if wwdr_b64 else None
        return cert_data, key_data, wwdr_data

    # Development: load from files
    app_root = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(app_root, CERT_PATH)
    key_path = os.path.join(app_root, KEY_PATH)
    wwdr_path = os.path.join(app_root, WWDR_PATH)

    with open(cert_path, 'rb') as f:
        cert_data = f.read()
    with open(key_path, 'rb') as f:
        key_data = f.read()

    wwdr_data = None
    if os.path.exists(wwdr_path):
        with open(wwdr_path, 'rb') as f:
            wwdr_data = f.read()

    return cert_data, key_data, wwdr_data


def sign_manifest(manifest_data, cert_path=None, key_path=None, wwdr_path=None):
    """Sign the manifest using PKCS#7 detached signature"""
    try:
        # Load certificate data (from env vars or files)
        cert_data, key_data, wwdr_data = load_certificate_data()

        # Parse certificates
        cert = load_pem_x509_certificate(cert_data, default_backend())
        key = serialization.load_pem_private_key(key_data, password=None, backend=default_backend())

        # Load WWDR certificate if available
        additional_certs = []
        if wwdr_data:
            wwdr_cert = load_pem_x509_certificate(wwdr_data, default_backend())
            additional_certs.append(wwdr_cert)

        # Create PKCS#7 signature
        if isinstance(manifest_data, str):
            manifest_data = manifest_data.encode('utf-8')

        # Build PKCS7 signature
        from cryptography.hazmat.primitives.serialization import pkcs7 as pkcs7_mod

        builder = pkcs7_mod.PKCS7SignatureBuilder().set_data(manifest_data)
        # Use SHA-256 (Apple accepts this for modern passes)
        builder = builder.add_signer(cert, key, hashes.SHA256())

        for additional_cert in additional_certs:
            builder = builder.add_certificate(additional_cert)

        signature = builder.sign(
            serialization.Encoding.DER,
            options=[pkcs7_mod.PKCS7Options.DetachedSignature]
        )

        return signature

    except Exception as e:
        print(f"Error signing manifest: {e}")
        raise


def get_logo_data():
    """Get logo image data (returns None if not found)"""
    logo_paths = [
        "static/images/wpc_logo.png",
        "static/wpc_logo.png",
    ]

    for path in logo_paths:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return f.read()

    return None


def resize_image_for_pass(image_data, max_width, max_height):
    """Resize image to fit within max dimensions, maintaining aspect ratio"""
    try:
        from PIL import Image
        from io import BytesIO

        img = Image.open(BytesIO(image_data))

        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Calculate new size maintaining aspect ratio
        ratio = min(max_width / img.width, max_height / img.height)
        new_size = (int(img.width * ratio), int(img.height * ratio))

        img = img.resize(new_size, Image.LANCZOS)

        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        return image_data  # Return original if PIL not available
    except Exception:
        return image_data


def create_simple_icon():
    """Create a simple green icon if no logo available"""
    # This creates a minimal 1x1 green PNG
    # In production, you'd want proper logo files
    import struct
    import zlib

    def create_png(width, height, color):
        """Create a simple solid color PNG"""
        def png_chunk(chunk_type, data):
            chunk_len = len(data)
            chunk = chunk_type + data
            crc = zlib.crc32(chunk) & 0xffffffff
            return struct.pack('>I', chunk_len) + chunk + struct.pack('>I', crc)

        # PNG signature
        signature = b'\x89PNG\r\n\x1a\n'

        # IHDR chunk
        ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        ihdr = png_chunk(b'IHDR', ihdr_data)

        # IDAT chunk (raw pixel data)
        raw_data = b''
        r, g, b = color
        for y in range(height):
            raw_data += b'\x00'  # filter byte
            for x in range(width):
                raw_data += bytes([r, g, b])

        compressed = zlib.compress(raw_data)
        idat = png_chunk(b'IDAT', compressed)

        # IEND chunk
        iend = png_chunk(b'IEND', b'')

        return signature + ihdr + idat + iend

    # Create green icon (87, 158, 75) = #579E4B close to WPC green
    return create_png(87, 87, (46, 158, 75))


def generate_pkpass(participant, tournament, checkin, base_url="https://pickleballconnect.eu"):
    """
    Generate a .pkpass file for Apple Wallet

    Returns: BytesIO object containing the .pkpass file
    """

    # Serial number (unique per pass)
    serial_number = f"WPC-{tournament.id}-{participant.id}-{checkin.id}"

    # Create pass.json
    pass_json = create_pass_json(participant, tournament, checkin, serial_number)

    # Prepare files dictionary
    files = {
        "pass.json": pass_json
    }

    # Add logo/icon files with proper sizes for Apple Wallet
    logo_data = get_logo_data()
    if logo_data:
        # Icon: 29x29 (1x), 58x58 (2x), 87x87 (3x)
        files["icon.png"] = resize_image_for_pass(logo_data, 29, 29)
        files["icon@2x.png"] = resize_image_for_pass(logo_data, 58, 58)
        # Logo: max 160x50 (1x), 320x100 (2x) - used in pass header
        files["logo.png"] = resize_image_for_pass(logo_data, 160, 50)
        files["logo@2x.png"] = resize_image_for_pass(logo_data, 320, 100)
    else:
        # Create simple icon
        icon_data = create_simple_icon()
        files["icon.png"] = icon_data
        files["icon@2x.png"] = icon_data

    # Create manifest
    manifest_json = create_manifest(files)
    files["manifest.json"] = manifest_json

    # Sign manifest (loads certificates from env vars or files automatically)
    signature = sign_manifest(manifest_json)
    files["signature"] = signature

    # Create ZIP file (.pkpass)
    pkpass_buffer = BytesIO()
    with zipfile.ZipFile(pkpass_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            if isinstance(content, str):
                content = content.encode('utf-8')
            zf.writestr(filename, content)

    pkpass_buffer.seek(0)
    return pkpass_buffer


def is_apple_wallet_available():
    """Check if certificates are available for Apple Wallet pass generation"""
    # Check environment variables first (Vercel/production)
    has_env_cert = bool(os.environ.get(ENV_CERT))
    has_env_key = bool(os.environ.get(ENV_KEY))

    print(f"DEBUG Apple Wallet: ENV_CERT ({ENV_CERT}) present: {has_env_cert}")
    print(f"DEBUG Apple Wallet: ENV_KEY ({ENV_KEY}) present: {has_env_key}")

    if has_env_cert and has_env_key:
        print("DEBUG Apple Wallet: Using environment variables - AVAILABLE")
        return True

    # Check local files (development)
    app_root = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(app_root, CERT_PATH)
    key_path = os.path.join(app_root, KEY_PATH)

    has_cert_file = os.path.exists(cert_path)
    has_key_file = os.path.exists(key_path)

    print(f"DEBUG Apple Wallet: cert file exists: {has_cert_file} ({cert_path})")
    print(f"DEBUG Apple Wallet: key file exists: {has_key_file} ({key_path})")

    available = has_cert_file and has_key_file
    print(f"DEBUG Apple Wallet: Using files - {'AVAILABLE' if available else 'NOT AVAILABLE'}")

    return available
