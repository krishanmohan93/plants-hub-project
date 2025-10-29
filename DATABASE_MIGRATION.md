# Plants Hub - Database Migration Guide

## 🎉 Successfully Migrated from CSV to Database!

Your Plants Hub application has been successfully refactored to use **SQLAlchemy ORM** with a proper database backend instead of CSV files.

---

## 📦 What Changed

### Before (CSV-based):
- Products stored in `products.csv`
- Data loaded using pandas DataFrame
- No transaction safety
- Data could be lost on errors

### After (Database-based):
- Products stored in SQLite database (`plants.db`)
- Data accessed using SQLAlchemy ORM
- ACID transactions with rollback on errors
- Production-ready with support for MySQL/PostgreSQL

---

## 🗃️ Database Configuration

### Current Setup (SQLite - Development)
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'
```
- **Location**: `plants.db` file in project root
- **Best for**: Local development and testing
- **No setup needed**: Works out of the box

### Switch to MySQL (Production)
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost/plants_db'
```

**Setup MySQL:**
```sql
CREATE DATABASE plants_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'plants_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON plants_db.* TO 'plants_user'@'localhost';
FLUSH PRIVILEGES;
```

Then update `app.py` line 31 with your credentials.

### Switch to PostgreSQL (Production)
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/plants_db'
```

**Setup PostgreSQL:**
```sql
CREATE DATABASE plants_db;
CREATE USER plants_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE plants_db TO plants_user;
```

Then update `app.py` line 34 with your credentials.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database (First Time Only)
```bash
python init_db.py
```

This will:
- ✅ Create database tables
- ✅ Migrate all 207 products from `products.csv` to database
- ✅ Create a backup file (`products_backup.csv`)

### 3. Run the Application
```bash
python app.py
```

Visit: **http://127.0.0.1:5000/**

---

## 📊 Database Schema

### Product Model

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key (auto-increment) |
| `name` | String(200) | Product name (indexed) |
| `description` | Text | Product description |
| `category` | String(50) | Product category (indexed) |
| `price` | Numeric(10,2) | Product price |
| `quantity` | Integer | Stock quantity |
| `image_url` | String(255) | Image filename |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

---

## 🔧 Key Features

### 1. **SQL-Based Search**
```python
# Text search in name and description (case-insensitive)
Product.query.filter(
    or_(
        Product.name.ilike('%keyword%'),
        Product.description.ilike('%keyword%')
    )
)
```

### 2. **Category Filtering**
```python
# Filter by category keywords
category_conditions = [Product.name.ilike(f'%{keyword}%') for keyword in keywords]
Product.query.filter(or_(*category_conditions))
```

### 3. **Price Range Filtering**
```python
# Filter by min/max price
Product.query.filter(Product.price >= min_price, Product.price <= max_price)
```

### 4. **Transaction Safety**
```python
try:
    db.session.add(product)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    # Handle error
```

---

## 📁 File Structure

```
plants_hub_project/
├── app.py                  # Main Flask application (NEW - Database version)
├── app_old_csv.py          # Backup of old CSV-based version
├── models.py               # SQLAlchemy Product model
├── init_db.py              # Database initialization & migration script
├── requirements.txt        # Python dependencies
├── plants.db               # SQLite database file (auto-created)
├── products.csv            # Original CSV data
├── products_backup.csv     # Backup created during migration
├── static/
│   └── images/             # Product images
└── templates/
    ├── index.html          # Home page (works with database)
    ├── add.html            # Add product form
    └── edit.html           # Edit product form
```

---

## 🔄 Migration Summary

### Automatically Migrated:
- ✅ **207 products** from `products.csv` → `plants.db`
- ✅ All product names, descriptions, prices
- ✅ All categories and image references
- ✅ Quantities (defaulted to 0 if not in CSV)

### Data Mapping:
| CSV Column | Database Column |
|------------|-----------------|
| `Product_Name` | `name` |
| `Description` | `description` |
| `Category` | `category` |
| `Price` | `price` |
| `Quantity` | `quantity` |
| `Image_File` | `image_url` |

---

## 🧪 Testing

### Test CRUD Operations:

1. **View All Products**: http://127.0.0.1:5000/
2. **Search**: Enter "planter" in search box
3. **Filter by Category**: Click "Ceramic" button
4. **Filter by Price**: Set min: 100, max: 500
5. **Add Product**: Click "Add Product", fill form, submit
6. **Edit Product**: Click "Edit" on any product
7. **Delete Product**: Click "Delete" (with confirmation)

### Verify Persistence:
1. Stop the server (Ctrl+C)
2. Restart: `python app.py`
3. All changes should persist! ✅

---

## 🆘 Troubleshooting

### Database Not Found Error
```
sqlalchemy.exc.OperationalError: no such table: products
```
**Solution**: Run `python init_db.py` to create tables

### Migration Already Done
```
ℹ️ Database already contains X products. Skipping migration.
```
**Solution**: This is normal. Data already migrated.

### Want to Re-migrate?
1. Delete `plants.db`
2. Run `python init_db.py` again

### Check Database Contents
```python
python
>>> from app import app, db, Product
>>> with app.app_context():
...     print(Product.query.count())
...     print(Product.query.first().name)
```

---

## 🎯 Production Deployment Tips

### 1. **Use Environment Variables**
```python
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///plants.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
```

### 2. **Disable Debug Mode**
```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
```

### 3. **Use Production WSGI Server**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. **Database Connection Pooling**
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

---

## ✅ Summary

| Metric | Status |
|--------|--------|
| Database Type | SQLite (configurable to MySQL/PostgreSQL) |
| Products Migrated | 207 |
| Search Working | ✅ SQL-based, case-insensitive |
| Filters Working | ✅ Category, price range |
| CRUD Operations | ✅ Add, edit, delete with transactions |
| Data Persistence | ✅ Survives server restarts |
| Production Ready | ✅ With MySQL/PostgreSQL setup |

---

## 🎉 You're All Set!

Your Flask app now uses a professional database backend with:
- ✅ SQLAlchemy ORM
- ✅ Transaction safety
- ✅ Efficient SQL queries
- ✅ Production-ready architecture
- ✅ Easy migration to MySQL/PostgreSQL

**Access your app**: http://127.0.0.1:5000/

**Need help?** Check the comments in `app.py` and `models.py` for detailed explanations.
