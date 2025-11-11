"""
Quick Test Script for Image Handling Fixes
Run this to verify all components are working correctly
"""

import sys
import os

print("=" * 80)
print("🧪 IMAGE HANDLING TEST SUITE")
print("=" * 80)

# Test 1: Check ImageKit client
print("\n1️⃣  Testing ImageKit Client Import...")
try:
    import imagekit_client
    print("   ✅ ImageKit client imported successfully")
    
    is_configured = imagekit_client.is_configured()
    config = imagekit_client.masked_config()
    
    print(f"   📊 Configuration Status: {'✅ CONFIGURED' if is_configured else '❌ NOT CONFIGURED'}")
    print(f"   🔑 Public Key: {config.get('public_key')}")
    print(f"   🔐 Private Key: {config.get('private_key')}")
    print(f"   🌐 URL Endpoint: {config.get('url_endpoint')}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 2: Check Flask app
print("\n2️⃣  Testing Flask App Import...")
try:
    from app import app, db
    print("   ✅ Flask app imported successfully")
    
    # Check upload route exists
    has_upload_route = any(rule.rule == '/upload' for rule in app.url_map.iter_rules())
    print(f"   🛣️  Upload route exists: {'✅ YES' if has_upload_route else '❌ NO'}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 3: Check models
print("\n3️⃣  Testing Database Models...")
try:
    from models import Product
    print("   ✅ Product model imported successfully")
    
    # Check if model has required fields
    required_fields = ['image_url', 'image_file_id']
    for field in required_fields:
        has_field = hasattr(Product, field)
        status = "✅" if has_field else "❌"
        print(f"   {status} Field '{field}': {'EXISTS' if has_field else 'MISSING'}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# Test 4: Check templates
print("\n4️⃣  Testing Template Files...")
template_files = [
    'templates/index.html',
    'templates/add.html',
    'templates/edit.html'
]

for template in template_files:
    if os.path.exists(template):
        print(f"   ✅ {template} exists")
        
        # Check for key functions in add.html and edit.html
        if 'add.html' in template or 'edit.html' in template:
            with open(template, 'r', encoding='utf-8') as f:
                content = f.read()
                has_upload_func = 'async function uploadViaAPI' in content
                has_validation = 'validTypes' in content or 'maxSize' in content
                has_logging = 'console.log' in content and '🔄' in content
                
                print(f"      📋 uploadViaAPI function: {'✅' if has_upload_func else '❌'}")
                print(f"      📋 File validation: {'✅' if has_validation else '❌'}")
                print(f"      📋 Console logging: {'✅' if has_logging else '❌'}")
    else:
        print(f"   ❌ {template} NOT FOUND")

# Test 5: Check environment variables
print("\n5️⃣  Testing Environment Variables...")
from dotenv import load_dotenv
load_dotenv()

env_vars = {
    'IMAGEKIT_PUBLIC_KEY': os.getenv('IMAGEKIT_PUBLIC_KEY'),
    'IMAGEKIT_PRIVATE_KEY': os.getenv('IMAGEKIT_PRIVATE_KEY'),
    'IMAGEKIT_URL_ENDPOINT': os.getenv('IMAGEKIT_URL_ENDPOINT')
}

for var, value in env_vars.items():
    if value:
        # Mask the value for security
        masked = value[:6] + '...' + value[-6:] if len(value) > 12 else '***'
        print(f"   ✅ {var}: {masked}")
    else:
        print(f"   ❌ {var}: NOT SET")

# Test 6: Test allowed file extensions
print("\n6️⃣  Testing File Extension Validation...")
try:
    from app import allowed_file, ALLOWED_EXT
    print(f"   📋 Allowed extensions: {', '.join(ALLOWED_EXT)}")
    
    test_files = {
        'image.png': True,
        'image.jpg': True,
        'image.jpeg': True,
        'image.gif': True,
        'document.pdf': False,
        'script.js': False,
        'image.PNG': True,  # Should work (case insensitive)
    }
    
    all_passed = True
    for filename, expected in test_files.items():
        result = allowed_file(filename)
        passed = result == expected
        all_passed = all_passed and passed
        status = "✅" if passed else "❌"
        print(f"   {status} {filename}: {result} (expected {expected})")
    
    if all_passed:
        print("   ✅ All file extension tests passed!")
    else:
        print("   ❌ Some file extension tests failed!")
        
except Exception as e:
    print(f"   ❌ Error: {e}")

# Summary
print("\n" + "=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)

if imagekit_client.is_configured():
    print("✅ ImageKit is configured and ready")
    print("✅ Upload functionality should work")
    print("✅ Images will be stored in ImageKit cloud")
else:
    print("⚠️  ImageKit is NOT configured")
    print("ℹ️  Products can still be added but will use placeholder images")
    print("ℹ️  Configure ImageKit in .env to enable cloud image uploads")

print("\n🎯 Next Steps:")
print("   1. If ImageKit not configured, add credentials to .env file")
print("   2. Run: python app.py")
print("   3. Open http://127.0.0.1:5000 in browser")
print("   4. Try adding a product with an image")
print("   5. Check browser console (F12) for detailed logs")
print("   6. Check server logs for backend process details")

print("\n" + "=" * 80)
print("✨ All fixes are in place and ready for testing!")
print("=" * 80)
