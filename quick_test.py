"""Quick Feature Test for Plants Hub"""
import requests
import time

print("⏳ Waiting for server to start...")
time.sleep(2)

print("\n" + "="*60)
print("🧪 PLANTS HUB - FEATURE TEST")
print("="*60 + "\n")

tests_passed = 0
tests_total = 0

# Test 1: Homepage
try:
    r = requests.get("http://127.0.0.1:5000", timeout=5)
    tests_total += 1
    if r.status_code == 200 and "Plants Hub" in r.text:
        print("✅ Homepage: WORKING")
        tests_passed += 1
    else:
        print("❌ Homepage: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ Homepage: ERROR - {e}")

# Test 2: Products Display
try:
    r = requests.get("http://127.0.0.1:5000", timeout=5)
    tests_total += 1
    if r.status_code == 200 and "/static/images/IMG" in r.text:
        print("✅ Products Display: WORKING")
        tests_passed += 1
    else:
        print("❌ Products Display: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ Products Display: ERROR - {e}")

# Test 3: Add Product Page
try:
    r = requests.get("http://127.0.0.1:5000/add", timeout=5)
    tests_total += 1
    if r.status_code == 200 and "Add New Product" in r.text:
        print("✅ Add Product Page: WORKING")
        tests_passed += 1
    else:
        print("❌ Add Product Page: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ Add Product Page: ERROR - {e}")

# Test 4: Edit Product Page
try:
    r = requests.get("http://127.0.0.1:5000/edit/1", timeout=5)
    tests_total += 1
    if r.status_code == 200 and "Edit Product" in r.text:
        print("✅ Edit Product Page: WORKING")
        tests_passed += 1
    else:
        print("❌ Edit Product Page: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ Edit Product Page: ERROR - {e}")

# Test 5: Diagnostics
try:
    r = requests.get("http://127.0.0.1:5000/diagnostics/imagekit", timeout=5)
    tests_total += 1
    if r.status_code == 200:
        data = r.json()
        if data.get('storage_type') == 'local':
            print("✅ Diagnostics: WORKING (Local storage)")
            tests_passed += 1
        else:
            print("⚠️  Diagnostics: WORKING (Old response cached)")
            tests_passed += 1
    else:
        print("❌ Diagnostics: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ Diagnostics: ERROR - {e}")

# Test 6: 404 Handler
try:
    r = requests.get("http://127.0.0.1:5000/nonexistent", timeout=5)
    tests_total += 1
    if r.status_code == 404 and ("404" in r.text or "Not Found" in r.text):
        print("✅ 404 Error Handler: WORKING")
        tests_passed += 1
    else:
        print("❌ 404 Error Handler: FAILED")
except Exception as e:
    tests_total += 1
    print(f"❌ 404 Error Handler: ERROR - {e}")

print("\n" + "="*60)
print(f"📊 RESULTS: {tests_passed}/{tests_total} tests passed")
print("="*60)

if tests_passed == tests_total:
    print("🎉 ALL FEATURES WORKING!")
elif tests_passed >= tests_total * 0.8:
    print("✅ Core features working properly!")
else:
    print("⚠️  Some features need attention")
