import sqlite3

conn = sqlite3.connect('plants.db')
cursor = conn.cursor()

# Check products without images
cursor.execute("SELECT id, name, image_url FROM products LIMIT 10")
rows = cursor.fetchall()

print("\nFirst 10 products in database:")
print("-" * 80)
for row in rows:
    img_status = row[2] if row[2] else "NO IMAGE"
    print(f"ID: {row[0]:3d} | Name: {row[1]:30s} | Image: {img_status}")

conn.close()
