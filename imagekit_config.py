"""
ImageKit Configuration and Helper Functions
Handles image uploads to ImageKit cloud storage
"""

import os
import logging
from dotenv import load_dotenv
from imagekitio import ImageKit

# Load environment variables
load_dotenv()

# Configure ImageKit
imagekit = ImageKit(
    public_key=os.getenv("IMAGEKIT_PUBLIC_KEY"),
    private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"),
    url_endpoint=os.getenv("IMAGEKIT_URL_ENDPOINT")
)

logger = logging.getLogger("plants_hub.imagekit")


def upload_image(file, folder="plants_hub"):
    """
    Upload an image file to ImageKit.

    Args:
        file: File object from request.files
        folder: Folder name inside ImageKit media library

    Returns:
        dict: { 'url': image_url, 'file_id': imagekit_file_id }
        None: If upload fails
    """
    try:
        # Read file bytes
        content = file.read()

        # Upload to ImageKit
        result = imagekit.upload_file(
            file=content,
            file_name=file.filename,
            options={
                "folder": folder,
                "use_unique_file_name": True,
                "transformation": [
                    {
                        "width": "800",
                        "height": "600",
                        "crop": "maintain_ratio"
                    },
                    {"quality": "80"}
                ]
            }
        )

        return {
            "url": result.url,
            "file_id": result.file_id
        }

    except Exception as e:
        logger.exception(f"ImageKit upload error: {e}")
        return None


def delete_image(file_id):
    """
    Delete an image from ImageKit.

    Args:
        file_id: ImageKit file ID

    Returns:
        bool: True if deletion successful, False otherwise
    """
    try:
        result = imagekit.delete_file(file_id)
        return result is not None and result.raw.get("success", False)
    except Exception as e:
        logger.exception(f"ImageKit delete error: {e}")
        return False


def get_image_url(file_path, transformation=None):
    """
    Generate an ImageKit URL with optional transformations.

    Args:
        file_path: Path returned from upload response (not file_id)
        transformation: List of transformation dicts

    Returns:
        str: CDN URL
    """
    if not file_path:
        return None

    try:
        url = imagekit.url(
            {
                "path": file_path,
                "transformation": transformation or []
            }
        )
        return url
    except Exception as e:
        logger.exception(f"URL generation error: {e}")
        return None


def is_configured():
    """
    Check if ImageKit credentials exist.

    Returns:
        bool
    """
    return all([
        os.getenv("IMAGEKIT_PUBLIC_KEY"),
        os.getenv("IMAGEKIT_PRIVATE_KEY"),
        os.getenv("IMAGEKIT_URL_ENDPOINT")
    ])


def masked_config():
    """Return masked ImageKit config for safe logging."""
    def redact(v):
        if not v:
            return None
        if len(v) <= 6:
            return "***"
        return v[:3] + "***" + v[-3:]

    return {
        "public_key": redact(os.getenv("IMAGEKIT_PUBLIC_KEY")),
        "private_key": redact(os.getenv("IMAGEKIT_PRIVATE_KEY")),
        "url_endpoint": os.getenv("IMAGEKIT_URL_ENDPOINT")
    }
