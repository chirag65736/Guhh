"""
UPI payment handling — multipart form parsing, screenshot saving, UPI ID.
"""

import os
import re
import secrets

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'screenshots')
UPI_ID = 'gk29052005@ptaxis'
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def parse_multipart(body, boundary):
    """Parse multipart/form-data body. Returns (fields, files)."""
    fields = {}
    files = {}
    boundary_bytes = ('--' + boundary).encode()
    parts = body.split(boundary_bytes)

    for part in parts:
        part = part.strip(b'\r\n')
        if not part or part == b'--':
            continue
        if b'\r\n\r\n' not in part:
            continue

        header_section, content = part.split(b'\r\n\r\n', 1)
        if content.endswith(b'\r\n'):
            content = content[:-2]

        headers = header_section.decode('utf-8', errors='replace')
        name = None
        filename = None

        for line in headers.split('\r\n'):
            if 'Content-Disposition' in line:
                for param in line.split(';'):
                    param = param.strip()
                    if param.startswith('name='):
                        name = param[5:].strip('"')
                    elif param.startswith('filename='):
                        filename = param[9:].strip('"')

        if name is None:
            continue

        if filename is not None:
            files[name] = {'filename': filename, 'data': content}
        else:
            fields[name] = content.decode('utf-8', errors='replace')

    return fields, files


def save_screenshot(file_data, original_filename, user_id):
    """Save screenshot privately to disk. Returns the filename only."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower() if ext.lower() in ALLOWED_EXTENSIONS else '.png'
    filename = f"ss_{user_id}_{secrets.token_hex(8)}{ext}"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    with open(filepath, 'wb') as f:
        f.write(file_data)
    return filename


def get_screenshot_path(filename):
    """Return absolute path for a screenshot filename (admin serving)."""
    safe = os.path.basename(filename)
    return os.path.join(SCREENSHOT_DIR, safe)


def validate_utr(utr):
    """Validate UTR format. Returns (is_valid, error_message)."""
    if not utr:
        return False, 'UTR number is required.'
    utr = utr.strip()
    if not re.match(r'^\d{10,22}$', utr):
        return False, 'UTR must be 10-22 digits (transaction reference number).'
    return True, None
