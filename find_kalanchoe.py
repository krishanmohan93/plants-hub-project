import sqlite3

conn = sqlite3.connect('plants.db')
cursor = conn.cursor()

# Search for Kalanchoe
cursor.execute("SELECT id, name, image_url, category FROM products WHERE name LIKE '%Kalanchoe%' OR name LIKE '%kalanchoe%'")
rows = cursor.fetchall()

if rows:
    print("\nKalanchoe products found:")
    print("-" * 80)
    for row in rows:
        img_status = row[2] if row[2] else "NO IMAGE"
        print(f"ID: {row[0]:3d} | Name: {row[1]:30s} | Category: {row[3]:15s} | Image: {img_status}")
else:
    print("\nNo Kalanchoe products found in database")

conn.close()
