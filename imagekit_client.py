"""ImageKit client helper replacing prior Cloudinary integration.

Provides minimal wrapper functions:
 - is_configured(): verify required env vars exist
 - upload_image(file, folder="plants_hub"): uploads a file-like object and returns dict

Relies on environment variables:
 IMAGEKIT_PUBLIC_KEY, IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT
"""

import os
import logging
from dotenv import load_dotenv
try:
    # imagekitio is an optional dependency for cloud uploads. Import safely so
    # the application can still start in environments where the SDK isn't
    # installed (we'll treat missing SDK as "not configured").
    from imagekitio import ImageKit
except Exception:
    ImageKit = None

try:
    from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
except Exception:  # Fallback path for older/newer SDKs
    UploadFileRequestOptions = None

load_dotenv()

logger = logging.getLogger("plants_hub.imagekit")

PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY") or os.getenv("Public key") or os.getenv("PUBLIC_KEY")
PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY") or os.getenv("Private key") or os.getenv("PRIVATE_KEY")
URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT") or os.getenv("URL_ENDPOINT") or os.getenv("URL-endpoint")


def masked_config():
    def redact(v):
        if not v:
            return None
        if len(v) <= 6:
            return '***'
        return v[:3] + '***' + v[-3:]
    return {
        'public_key': redact(PUBLIC_KEY),
        'private_key': redact(PRIVATE_KEY),
        'url_endpoint': URL_ENDPOINT
    }

_client = None
if ImageKit and PUBLIC_KEY and PRIVATE_KEY and URL_ENDPOINT:
    try:
        _client = ImageKit(
            public_key=PUBLIC_KEY,
            private_key=PRIVATE_KEY,
            url_endpoint=URL_ENDPOINT
        )
        logger.info("✅ ImageKit client initialized")
    except Exception as e:
        logger.exception("Failed to initialize ImageKit client: %s", e)
else:
    if not ImageKit:
        logger.info("ImageKit SDK not installed; image uploads are disabled until installed.")
    else:
        logger.info("ImageKit not configured (missing keys or endpoint). %s", masked_config())


def is_configured() -> bool:
    return bool(_client)


def masked_config():
    def redact(v):
        if not v:
            return None
        if len(v) <= 6:
            return '***'
        return v[:3] + '***' + v[-3:]
    return {
        'public_key': redact(PUBLIC_KEY),
        'private_key': redact(PRIVATE_KEY),
        'url_endpoint': URL_ENDPOINT
    }


def upload_image(file, folder: str = "plants_hub"):
    """Upload an image to ImageKit.

    Accepts a Werkzeug FileStorage or file-like object supporting .read().
    Returns on success: {url, file_id, name}
    Returns on failure: {error: <code>, message: <human readable>}
    """
    if not is_configured():
        msg = "ImageKit not configured. Check environment variables."
        logger.warning(msg + " %s", masked_config())
        return {"error": "not_configured", "message": msg}
    
    try:
        filename = getattr(file, 'filename', None) or getattr(file, 'name', 'upload')
        logger.info("📤 Uploading %s to ImageKit folder: %s", filename, folder)
        
        # Check if file has content (for BytesIO objects, check the buffer)
        current_pos = file.tell()
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(current_pos)  # Reset to original position
        
        if file_size == 0:
            logger.error("❌ File is empty: %s", filename)
            return {"error": "empty_file", "message": "The uploaded file is empty"}
        
        logger.info("📏 File size: %.2f KB", file_size / 1024)
        file.seek(0)  # Reset file pointer for ImageKit SDK
        
        if UploadFileRequestOptions:
            logger.info("Using UploadFileRequestOptions for SDK")
            options = UploadFileRequestOptions(
                folder=f"/{folder}",
                use_unique_file_name=True,
                is_private_file=False,
            )
            result = _client.upload_file(file=file, file_name=filename, options=options)
        else:
            # SDK 4.x allows keyword args directly
            logger.info("Using direct keyword args for SDK")
            result = _client.upload_file(
                file=file,
                file_name=filename,
                folder=f"/{folder}",
                use_unique_file_name=True,
                is_private_file=False,
            )
        
        logger.info("📦 ImageKit SDK result type: %s", type(result).__name__)
        logger.info("📦 ImageKit SDK result attributes: %s", dir(result))
        
        if not result:
            logger.error("❌ ImageKit returned None for %s", filename)
            return {"error": "empty_result", "message": "Upload returned no result from ImageKit"}
        
        # Try to get URL from different possible attributes
        url = None
        file_id = None
        name = filename
        
        # Method 1: Direct attributes (newer SDK)
        if hasattr(result, 'url'):
            url = result.url
            file_id = getattr(result, 'file_id', None)
            name = getattr(result, 'name', filename)
            logger.info("✅ Got data from result attributes")
        # Method 2: Response metadata (some SDK versions)
        elif hasattr(result, 'response_metadata'):
            metadata = result.response_metadata
            url = metadata.get('url') if isinstance(metadata, dict) else getattr(metadata, 'url', None)
            file_id = metadata.get('fileId') if isinstance(metadata, dict) else getattr(metadata, 'fileId', None)
            name = metadata.get('name', filename) if isinstance(metadata, dict) else getattr(metadata, 'name', filename)
            logger.info("✅ Got data from response_metadata")
        # Method 3: Dict-like access
        elif isinstance(result, dict):
            url = result.get('url')
            file_id = result.get('fileId') or result.get('file_id')
            name = result.get('name', filename)
            logger.info("✅ Got data from dict")
        
        if not url:
            logger.error("❌ ImageKit result has no URL. Result dir: %s", dir(result))
            logger.error("❌ Result repr: %s", repr(result)[:500])
            return {"error": "no_url", "message": "Upload succeeded but no URL was returned from ImageKit"}
        
        logger.info("✅ Upload successful - URL: %s, File ID: %s", url, file_id)
        
        return {
            'url': url,
            'file_id': file_id,
            'name': name
        }
    except Exception as e:
        logger.exception("❌ ImageKit upload error for %s: %s", filename if 'filename' in locals() else 'unknown', e)
        error_msg = str(e)
        # Extract more specific error info if available
        if hasattr(e, 'response'):
            try:
                error_msg = f"{error_msg} - Response: {e.response}"
            except:
                pass
        return {"error": "exception", "message": f"Upload failed: {error_msg}"}


def delete_image(file_id: str):
    """Delete an image from ImageKit by file_id.

    Returns True on success, or a dict {error, message} on failure.
    """
    if not is_configured():
        msg = "ImageKit not configured. Cannot delete image."
        logger.warning(msg)
        return {"error": "not_configured", "message": msg}
    if not file_id:
        return {"error": "invalid_id", "message": "No file_id provided"}
    try:
        resp = _client.delete_file(file_id)
        # SDK returns dict or object depending on version; treat no exception as success
        logger.info("🗑️ Deleted ImageKit file %s", file_id)
        return True
    except Exception as e:
        logger.exception("ImageKit delete error for %s: %s", file_id, e)
        return {"error": "exception", "message": str(e)}
