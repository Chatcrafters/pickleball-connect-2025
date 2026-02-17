"""
Apple Wallet Pass Generator for WPC Tournament Check-in
"""

import os
import json
import hashlib
import zipfile
import io
from datetime import datetime

def is_apple_wallet_available():
    """Check if Apple Wallet certificates are configured"""
    required_vars = [
        'APPLE_PASS_CERT',
        'APPLE_PASS_KEY', 
        'APPLE_WWDR_CERT',
        'APPLE_PASS_TYPE_ID',
        'APPLE_TEAM_ID'
    ]
    return all(os.environ.get(var) for var in required_vars)


def create_pkpass(registration, team, tournament):
    """Create an Apple Wallet .pkpass file"""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.serialization import pkcs7
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("cryptography library not installed")
        return None
    
    if not is_apple_wallet_available():
        print("Apple Wallet not configured")
        return None
    
    try:
        import base64
        
        pass_type_id = os.environ.get('APPLE_PASS_TYPE_ID')
        team_id = os.environ.get('APPLE_TEAM_ID')
        
        cert_pem = base64.b64decode(os.environ.get('APPLE_PASS_CERT', ''))
        key_pem = base64.b64decode(os.environ.get('APPLE_PASS_KEY', ''))
        wwdr_pem = base64.b64decode(os.environ.get('APPLE_WWDR_CERT', ''))
        
        certificate = x509.load_pem_x509_certificate(cert_pem, default_backend())
        private_key = serialization.load_pem_private_key(key_pem, password=None, backend=default_backend())
        wwdr_certificate = x509.load_pem_x509_certificate(wwdr_pem, default_backend())
        
        serial_number = f"wpc-{tournament.id}-{registration.id}-{int(datetime.utcnow().timestamp())}"
        
        pass_json = {
            "formatVersion": 1,
            "passTypeIdentifier": pass_type_id,
            "serialNumber": serial_number,
            "teamIdentifier": team_id,
            "organizationName": "WPC Series Europe",
            "description": f"WPC {tournament.name} Pass",
            "logoText": "WPC",
            "foregroundColor": "rgb(255, 255, 255)",
            "backgroundColor": "rgb(46, 158, 75)",
            "labelColor": "rgb(255, 255, 255)",
            "barcode": {
                "message": registration.profile_token,
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1"
            },
            "barcodes": [{
                "message": registration.profile_token,
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1"
            }],
            "eventTicket": {
                "primaryFields": [{
                    "key": "player",
                    "label": "PLAYER",
                    "value": f"{registration.first_name} {registration.last_name}"
                }],
                "secondaryFields": [{
                    "key": "team",
                    "label": "TEAM",
                    "value": f"{team.country_flag} {team.country_name}"
                }, {
                    "key": "category",
                    "label": "CATEGORY",
                    "value": team.age_category
                }],
                "auxiliaryFields": [{
                    "key": "shirt",
                    "label": "SHIRT",
                    "value": registration.shirt_name or registration.last_name.upper()
                }, {
                    "key": "size",
                    "label": "SIZE",
                    "value": registration.shirt_size or "-"
                }]
            }
        }
        
        pass_files = {}
        pass_json_bytes = json.dumps(pass_json, indent=2).encode('utf-8')
        pass_files['pass.json'] = pass_json_bytes
        
        green_pixel = create_green_png()
        pass_files['icon.png'] = green_pixel
        pass_files['icon@2x.png'] = green_pixel
        pass_files['logo.png'] = green_pixel
        pass_files['logo@2x.png'] = green_pixel
        
        manifest = {}
        for filename, content in pass_files.items():
            manifest[filename] = hashlib.sha1(content).hexdigest()
        
        manifest_bytes = json.dumps(manifest, indent=2).encode('utf-8')
        pass_files['manifest.json'] = manifest_bytes
        
        signature = pkcs7.PKCS7SignatureBuilder().set_data(
            manifest_bytes
        ).add_signer(
            certificate, private_key, hashes.SHA256()
        ).add_certificate(
            wwdr_certificate
        ).sign(
            serialization.Encoding.DER, 
            [pkcs7.PKCS7Options.DetachedSignature]
        )
        pass_files['signature'] = signature
        
        pkpass_buffer = io.BytesIO()
        with zipfile.ZipFile(pkpass_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filename, content in pass_files.items():
                zf.writestr(filename, content)
        
        pkpass_buffer.seek(0)
        return pkpass_buffer.getvalue()
        
    except Exception as e:
        print(f"Error creating pkpass: {str(e)}")
        return None


def create_green_png():
    """Create a simple green PNG image"""
    import struct
    import zlib
    
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc
    
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', 29, 29, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    raw_data = b''
    for y in range(29):
        raw_data += b'\x00'
        for x in range(29):
            raw_data += b'\x2e\x9e\x4b'
    
    compressed = zlib.compress(raw_data)
    idat = png_chunk(b'IDAT', compressed)
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend
