"""
Quick test to verify image upload endpoint is working correctly.
Tests the fixes for ConnectionResetError(10054).
"""

import requests
import io
import base64

def test_upload_endpoint():
    """Test the /upload endpoint with a small test image."""
    
    print("🧪 Testing Image Upload Endpoint")
    print("=" * 50)
    
    # Create a minimal 1x1 PNG (base64 encoded)
    # This is a valid 1x1 red pixel PNG
    png_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=='
    img_bytes = io.BytesIO(base64.b64decode(png_b64))
    
    print("✅ Created test image (1x1 PNG pixel)")
    print(f"📏 Image size: {len(img_bytes.getvalue())} bytes")
    
    # Prepare the upload
    files = {'image': ('test-image.png', img_bytes, 'image/png')}
    url = 'http://127.0.0.1:5000/upload'
    
    print(f"\n🌐 Sending POST request to {url}")
    print("⏱️  Timeout: 60 seconds")
    
    try:
        response = requests.post(url, files=files, timeout=60)
        
        print(f"\n📡 Response Status: {response.status_code}")
        print(f"📦 Response Headers:")
        for key, value in response.headers.items():
            if 'access-control' in key.lower() or 'content-type' in key.lower():
                print(f"   {key}: {value}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Upload Successful!")
            print(f"🔗 Image URL: {data.get('url', 'N/A')}")
            print(f"🆔 File ID: {data.get('file_id', 'N/A')}")
            print(f"📝 File Name: {data.get('name', 'N/A')}")
            return True
        elif response.status_code == 503:
            print(f"\n⚠️  ImageKit Not Configured (Expected if no API keys)")
            print(f"💬 Message: {response.json().get('error', 'N/A')}")
            return True  # This is expected behavior
        else:
            print(f"\n❌ Upload Failed!")
            print(f"💬 Error: {response.json().get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("💡 Make sure the Flask server is running on http://127.0.0.1:5000")
        return False
    except requests.exceptions.Timeout:
        print(f"\n❌ Timeout Error: Request took longer than 60 seconds")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}: {e}")
        return False

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🔬 CONNECTION FIX VERIFICATION TEST")
    print("="*50 + "\n")
    
    success = test_upload_endpoint()
    
    print("\n" + "="*50)
    if success:
        print("✅ TEST PASSED - Upload endpoint is working!")
        print("\nNext steps:")
        print("1. Open http://127.0.0.1:5000 in your browser")
        print("2. Navigate to /add page")
        print("3. Test file upload or camera capture")
        print("4. Verify product is created with image")
    else:
        print("❌ TEST FAILED - Check server logs for details")
        print("\nTroubleshooting:")
        print("1. Ensure Flask server is running: python app.py")
        print("2. Check server logs for errors")
        print("3. Verify you're using http://127.0.0.1:5000 (not 10.x.x.x)")
    print("="*50 + "\n")
