"""
Apple Wallet Pass Generator for WPC Check-in System
Generates .pkpass files for Apple Wallet
"""

import json
import hashlib
import zipfile
import os
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

# Paths to certificates (relative to app root)
CERT_PATH = "certificates/wpc_pass_cert.pem"
KEY_PATH = "certificates/wpc_pass.key"
WWDR_PATH = "certificates/AppleWWDRCAG4.pem"  # Apple WWDR certificate

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
    return json.dumps(manifest, indent=2)


def sign_manifest(manifest_data, cert_path, key_path, wwdr_path):
    """Sign the manifest using PKCS#7 detached signature"""
    try:
        # Load certificate
        with open(cert_path, 'rb') as f:
            cert = load_pem_x509_certificate(f.read(), default_backend())

        # Load private key
        with open(key_path, 'rb') as f:
            key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())

        # Load WWDR certificate (if exists)
        additional_certs = []
        if os.path.exists(wwdr_path):
            with open(wwdr_path, 'rb') as f:
                wwdr_cert = load_pem_x509_certificate(f.read(), default_backend())
                additional_certs.append(wwdr_cert)

        # Create PKCS#7 signature
        if isinstance(manifest_data, str):
            manifest_data = manifest_data.encode('utf-8')

        # Build PKCS7 signature
        from cryptography.hazmat.primitives.serialization import pkcs7 as pkcs7_mod

        builder = pkcs7_mod.PKCS7SignatureBuilder().set_data(manifest_data)
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

    # Add logo/icon files
    logo_data = get_logo_data()
    if logo_data:
        files["icon.png"] = logo_data
        files["icon@2x.png"] = logo_data
        files["logo.png"] = logo_data
        files["logo@2x.png"] = logo_data
    else:
        # Create simple icon
        icon_data = create_simple_icon()
        files["icon.png"] = icon_data
        files["icon@2x.png"] = icon_data

    # Create manifest
    manifest_json = create_manifest(files)
    files["manifest.json"] = manifest_json

    # Sign manifest
    app_root = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(app_root, CERT_PATH)
    key_path = os.path.join(app_root, KEY_PATH)
    wwdr_path = os.path.join(app_root, WWDR_PATH)

    signature = sign_manifest(manifest_json, cert_path, key_path, wwdr_path)
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
    """Check if certificate files exist for Apple Wallet pass generation"""
    app_root = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(app_root, CERT_PATH)
    key_path = os.path.join(app_root, KEY_PATH)

    return os.path.exists(cert_path) and os.path.exists(key_path)
