from app import app

print('App imported successfully')
print('Running test request...')

with app.test_client() as client:
    try:
        resp = client.get('/')
        print(f'Status: {resp.status_code}')
        print(f'Content length: {len(resp.data)}')
        
        # Check if images have static paths
        content = resp.data.decode('utf-8')
        if '/static/images/' in content:
            print('✅ Static image paths found!')
            import re
            matches = re.findall(r'src="([^"]*static/images/[^"]*)"', content)
            print(f'Found {len(matches)} static image references')
            if matches:
                print(f'Example: {matches[0]}')
        else:
            print('❌ No static image paths found')
            # Check for plain filenames
            import re
            matches = re.findall(r'src="(IMG-[^"]*)"', content)
            if matches:
                print(f'⚠️ Found {len(matches)} plain filename references')
                print(f'Example: {matches[0]}')
        
    except Exception as e:
        print(f'❌ Error: {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()
