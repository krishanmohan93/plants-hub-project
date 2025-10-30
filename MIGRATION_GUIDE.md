# Database Migration Guide

Since local migration is failing due to network restrictions, you can migrate data using Render's Shell feature.

## Option 1: Use Render Shell (Recommended)

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Select your service**: plants-hub-project
3. **Click "Shell" tab** in the top navigation
4. **Run the migration script**:
   ```bash
   python migrate_to_postgres.py
   ```
5. **Type `yes`** when prompted to confirm migration

This will work because Render's servers can directly access Neon database.

## Option 2: Manual CSV Export/Import

If Option 1 doesn't work, use the web interface:

1. Run the app locally: `python app.py`
2. Visit http://localhost:5000
3. Manually copy products OR use the export feature
4. Import into the deployed app at https://plants-hub-project.onrender.com

## Option 3: Export from SQLite

Run this to export your products to CSV:

```bash
python -c "import sqlite3, csv; conn = sqlite3.connect('plants.db'); cursor = conn.cursor(); cursor.execute('SELECT * FROM product'); rows = cursor.fetchall(); writer = csv.writer(open('export_products.csv', 'w', newline='', encoding='utf-8')); writer.writerow([desc[0] for desc in cursor.description]); writer.writerows(rows); print('Exported to export_products.csv')"
```

## Current Status

- ✅ Migration script is ready and committed
- ✅ Code is deployed to Render with PostgreSQL support
- ⏳ Waiting for data migration (207 products in local SQLite)
- 🚀 App is live at: https://plants-hub-project.onrender.com

## Why Local Migration Fails

Your Windows machine cannot resolve the Neon hostname due to network/DNS restrictions. This is normal for some ISPs or corporate networks. Render's servers have no such restrictions.
