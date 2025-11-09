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
from imagekitio import ImageKit
try:
    from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
except Exception:  # Fallback path for older/newer SDKs
    UploadFileRequestOptions = None

load_dotenv()

logger = logging.getLogger("plants_hub.imagekit")

PUBLIC_KEY = os.getenv("IMAGEKIT_PUBLIC_KEY") or os.getenv("Public key") or os.getenv("PUBLIC_KEY")
PRIVATE_KEY = os.getenv("IMAGEKIT_PRIVATE_KEY") or os.getenv("Private key") or os.getenv("PRIVATE_KEY")
URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT") or os.getenv("URL_ENDPOINT") or os.getenv("URL-endpoint")

_client = None
if PUBLIC_KEY and PRIVATE_KEY and URL_ENDPOINT:
    try:
        _client = ImageKit(
            public_key=PUBLIC_KEY,
            private_key=PRIVATE_KEY,
            url_endpoint=URL_ENDPOINT
        )
        logger.info("✅ ImageKit client initialized")
    except Exception as e:
        logger.exception("Failed to initialize ImageKit client: %s", e)


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
        if UploadFileRequestOptions:
            options = UploadFileRequestOptions(
                folder=f"/{folder}",
                use_unique_file_name=True,
                is_private_file=False,
            )
            result = _client.upload_file(file=file, file_name=filename, options=options)
        else:
            # SDK 4.x allows keyword args directly
            result = _client.upload_file(
                file=file,
                file_name=filename,
                folder=f"/{folder}",
                use_unique_file_name=True,
                is_private_file=False,
            )
        if not result or not getattr(result, 'url', None):
            logger.error("ImageKit returned empty result for %s", filename)
            return {"error": "empty_result", "message": "Upload returned no URL from ImageKit."}
        return {
            'url': result.url,
            'file_id': getattr(result, 'file_id', None),
            'name': getattr(result, 'name', filename)
        }
    except Exception as e:
        logger.exception("ImageKit upload error: %s", e)
        return {"error": "exception", "message": str(e)}


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
