"""
Cloudinary configuration helper.

Loads Cloudinary credentials from .env and configures the cloudinary SDK.
Do NOT hardcode secrets in code. Set these values in your `.env` file:

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

"""
from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger("plants_hub.cloudinary")

try:
    import cloudinary
    # Configure from environment variables
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
    api_key = os.getenv('CLOUDINARY_API_KEY')
    api_secret = os.getenv('CLOUDINARY_API_SECRET')

    if not (cloud_name and api_key and api_secret):
        logger.warning('Cloudinary credentials not found in environment. Image uploads will fail until configured.')
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )
except Exception as e:
    logger.exception('Unable to import/configure cloudinary: %s', e)

__all__ = ['cloudinary']
