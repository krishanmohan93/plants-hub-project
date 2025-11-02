"""
Cloudinary Configuration and Helper Functions
Handles image uploads to Cloudinary cloud storage
"""

import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)


def upload_image(file, folder='plants_hub'):
    """
    Upload an image file to Cloudinary
    
    Args:
        file: File object from request.files
        folder: Cloudinary folder name (default: 'plants_hub')
    
    Returns:
        dict: Response from Cloudinary with 'url' and 'public_id'
        None: If upload fails
    """
    try:
        # Upload the file to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='image',
            overwrite=True,
            invalidate=True,
            transformation=[
                {'width': 800, 'height': 600, 'crop': 'limit'},
                {'quality': 'auto:good'},
                {'fetch_format': 'auto'}
            ]
        )
        
        return {
            'url': result.get('secure_url'),
            'public_id': result.get('public_id')
        }
    
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None


def delete_image(public_id):
    """
    Delete an image from Cloudinary
    
    Args:
        public_id: The Cloudinary public ID of the image to delete
    
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        return False


def get_image_url(public_id, transformation=None):
    """
    Generate a Cloudinary URL for an image with optional transformations
    
    Args:
        public_id: The Cloudinary public ID
        transformation: Optional transformation parameters
    
    Returns:
        str: Full URL to the image
    """
    if not public_id:
        return None
    
    try:
        return cloudinary.CloudinaryImage(public_id).build_url(
            transformation=transformation
        )
    except Exception as e:
        print(f"URL generation error: {e}")
        return None


def is_configured():
    """
    Check if Cloudinary is properly configured
    
    Returns:
        bool: True if all required credentials are present
    """
    return all([
        os.getenv('CLOUDINARY_CLOUD_NAME'),
        os.getenv('CLOUDINARY_API_KEY'),
        os.getenv('CLOUDINARY_API_SECRET')
    ])
