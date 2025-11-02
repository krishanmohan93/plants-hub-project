# Image Storage Issue on Render

## Problem
Render.com uses **ephemeral file storage**, meaning:
- Uploaded images are stored in `static/images/`
- Every deploy or restart **deletes** all uploaded files
- Images disappear after app restarts

## Solutions

### Option 1: Cloud Storage (Recommended for Production)
Use services like:
- **Cloudinary** (Free tier: 25GB storage, 25GB bandwidth)
- **AWS S3**
- **Google Cloud Storage**
- **Imgur API**

### Option 2: Database Storage
Store images as BASE64 in PostgreSQL (works but not ideal for many images)

### Option 3: External URLs
Store only URLs to images hosted elsewhere

## Quick Fix Implemented
- Added robust placeholder handling
- Images show placeholder icon if missing
- No errors when images don't exist

## For Production Deploy
To fix permanently, integrate Cloudinary:

```python
pip install cloudinary
```

Then update image upload to use Cloudinary instead of local storage.
