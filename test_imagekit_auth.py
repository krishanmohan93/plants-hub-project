"""Test ImageKit authentication and upload"""
import sys
import os
import io
import base64
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("="*60)
print("🔍 IMAGEKIT AUTHENTICATION DIAGNOSTIC")
print("="*60)

# Step 1: Check credentials
print("\n📋 Step 1: Checking credentials...")
public_key = os.getenv('IMAGEKIT_PUBLIC_KEY')
private_key = os.getenv('IMAGEKIT_PRIVATE_KEY')
url_endpoint = os.getenv('IMAGEKIT_URL_ENDPOINT')

print(f"✅ PUBLIC_KEY: {public_key}")
print(f"✅ PRIVATE_KEY: {private_key[:15]}..." if private_key else "❌ PRIVATE_KEY: Missing")
print(f"✅ URL_ENDPOINT: {url_endpoint}")

if not all([public_key, private_key, url_endpoint]):
    print("\n❌ ERROR: Missing ImageKit credentials in .env file!")
    sys.exit(1)

# Step 2: Import SDK
print("\n📦 Step 2: Importing ImageKit SDK...")
try:
    from imagekitio import ImageKit
    print("✅ ImageKit SDK imported successfully")
except ImportError as e:
    print(f"❌ ERROR: ImageKit SDK not installed: {e}")
    print("Run: pip install imagekitio")
    sys.exit(1)

# Step 3: Initialize client
print("\n🔧 Step 3: Initializing ImageKit client...")
try:
    imagekit = ImageKit(
        public_key=public_key,
        private_key=private_key,
        url_endpoint=url_endpoint
    )
    print("✅ ImageKit client initialized successfully")
except Exception as e:
    print(f"❌ ERROR: Failed to initialize ImageKit client: {e}")
    sys.exit(1)

# Step 4: Test upload
print("\n📤 Step 4: Testing image upload...")
try:
    # Create a tiny 1x1 PNG
    png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='
    img_data = base64.b64decode(png_b64)
    img_file = io.BytesIO(img_data)
    img_file.name = 'test-diagnostic.png'
    
    print(f"   Image size: {len(img_data)} bytes")
    print("   Uploading to ImageKit...")
    
    # Try with UploadFileRequestOptions
    try:
        from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
        options = UploadFileRequestOptions(
            folder='/plants_hub_test/',
            is_private_file=False,
            use_unique_file_name=True
        )
        result = imagekit.upload_file(
            file=img_file,
            file_name='test-diagnostic-' + str(os.urandom(4).hex()) + '.png',
            options=options
        )
    except:
        # Fallback for older SDK
        result = imagekit.upload_file(
            file=img_file,
            file_name='test-diagnostic-' + str(os.urandom(4).hex()) + '.png'
        )
    
    print(f"\n✅ UPLOAD SUCCESSFUL!")
    print(f"   URL: {result.url}")
    print(f"   File ID: {result.file_id}")
    print(f"   Name: {result.name}")
    
    # Try to delete the test image
    try:
        imagekit.delete_file(file_id=result.file_id)
        print(f"   ✅ Test image cleaned up")
    except:
        print(f"   ⚠️ Could not delete test image (not critical)")
    
except Exception as e:
    print(f"\n❌ UPLOAD FAILED!")
    print(f"   Error: {type(e).__name__}: {e}")
    
    # Check for common errors
    if "authenticate" in str(e).lower():
        print("\n🔍 AUTHENTICATION ERROR DETECTED")
        print("   Possible causes:")
        print("   1. Wrong PRIVATE_KEY - double check it matches your dashboard")
        print("   2. Wrong PUBLIC_KEY - verify it's correct")
        print("   3. API keys may be regenerated/revoked in ImageKit dashboard")
        print("   4. Account may have restrictions or billing issues")
    elif "403" in str(e) or "forbidden" in str(e).lower():
        print("\n🔍 PERMISSION ERROR")
        print("   Check your ImageKit account permissions and API key access")
    elif "network" in str(e).lower() or "connection" in str(e).lower():
        print("\n🔍 NETWORK ERROR")
        print("   Check your internet connection")
    
    sys.exit(1)

print("\n" + "="*60)
print("✅ ALL TESTS PASSED - IMAGEKIT IS CONFIGURED CORRECTLY!")
print("="*60)
print("\nYour ImageKit setup is working. The upload error in your app")
print("is likely due to:")
print("1. File format/encoding issue")
print("2. Missing file data")
print("3. Incorrect upload options")
print("\nCheck the server logs when uploading through the app.")
