import os
import uuid
from PIL import Image
import streamlit as st
from typing import Optional

UPLOAD_FOLDER = "data/photos"
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def ensure_upload_folder():
    """Ensure the upload folder exists"""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_photo(uploaded_file) -> Optional[str]:
    """
    Save uploaded photo and return filename
    Returns None if save failed
    """
    if not uploaded_file:
        return None

    if not allowed_file(uploaded_file.name):
        st.error("Only JPG and PNG files are allowed")
        return None

    if uploaded_file.size > MAX_FILE_SIZE:
        st.error("File size must be less than 5MB")
        return None

    ensure_upload_folder()

    # Generate unique filename
    file_extension = uploaded_file.name.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4()}.{file_extension}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    try:
        # Open and optimize image
        image = Image.open(uploaded_file)

        # Convert to RGB if needed (for PNG with transparency)
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = rgb_image

        # Resize if too large (max 1200px on longest side)
        max_size = 1200
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        # Save with optimization
        image.save(filepath, optimize=True, quality=85)
        return filename

    except Exception as e:
        st.error(f"Error saving photo: {str(e)}")
        return None

def get_photo_path(filename: str) -> str:
    """Get full path to photo file"""
    if not filename:
        return ""
    return os.path.join(UPLOAD_FOLDER, filename)

def photo_exists(filename: str) -> bool:
    """Check if photo file exists"""
    if not filename:
        return False
    return os.path.exists(get_photo_path(filename))

def delete_photo(filename: str) -> bool:
    """Delete photo file"""
    if not filename:
        return True

    filepath = get_photo_path(filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception:
        return False