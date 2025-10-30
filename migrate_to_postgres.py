"""
Migration Script: SQLite to Neon PostgreSQL
Transfers all products from local plants.db to Neon cloud database
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Fix Windows UTF-8 encoding for emoji support
if sys.platform == 'win32':
    # Set UTF-8 encoding for stdout/stderr
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
load_dotenv()

# Import models
from models import Product

def safe_print(text):
    """Print text with emoji fallback for Windows terminals"""
    try:
        print(text)
    except UnicodeEncodeError:
        # Remove emojis if terminal doesn't support them
        import re
        text_no_emoji = re.sub(r'[^\x00-\x7F]+', '', text)
        print(text_no_emoji)

def migrate_data():
    """Migrate all products from SQLite to PostgreSQL"""
    
    # Get database URLs
    postgres_url = os.getenv('DATABASE_URL')
    sqlite_path = 'plants.db'
    
    if not postgres_url:
        safe_print("ERROR: DATABASE_URL not found in .env file")
        return False
    
    if not os.path.exists(sqlite_path):
        safe_print(f"ERROR: {sqlite_path} not found")
        return False
    
    # Fix postgres:// to postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    # Force psycopg2 driver
    if '+psycopg2' not in postgres_url:
        postgres_url = postgres_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    safe_print("=" * 70)
    safe_print("🚀 Starting Migration: SQLite → Neon PostgreSQL")
    safe_print("=" * 70)
    
    # Create engines
    safe_print(f"\n📂 Connecting to SQLite: {sqlite_path}")
    sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
    
    safe_print(f"🐘 Connecting to Neon PostgreSQL...")
    postgres_engine = create_engine(postgres_url)
    
    # Create sessions
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()
    
    try:
        # Create tables in PostgreSQL if they don't exist
        safe_print("🔧 Creating database tables in PostgreSQL...")
        from models import db
        # Create all tables defined in models
        Product.__table__.create(postgres_engine, checkfirst=True)
        safe_print("   ✓ Tables ready")
        
        # Check SQLite data
        safe_print("\n📊 Reading products from SQLite...")
        sqlite_products = sqlite_session.query(Product).all()
        total = len(sqlite_products)
        safe_print(f"   Found {total} products")
        
        if total == 0:
            safe_print("ℹ️  No products to migrate")
            return True
        
        # Check existing PostgreSQL data
        existing = postgres_session.query(Product).count()
        safe_print(f"\n🔍 PostgreSQL currently has {existing} products")
        
        if existing > 0:
            response = input("\n⚠️  PostgreSQL already has data. Clear and migrate? (yes/no): ")
            if response.lower() != 'yes':
                safe_print("❌ Migration cancelled")
                return False
            
            safe_print("🗑️  Clearing existing data...")
            postgres_session.query(Product).delete()
            postgres_session.commit()
        
        # Migrate products
        safe_print(f"\n🚚 Migrating {total} products to Neon...")
        migrated = 0
        
        for product in sqlite_products:
            # Create new product for PostgreSQL
            new_product = Product(
                name=product.name,
                description=product.description,
                category=product.category,
                price=product.price,
                quantity=product.quantity,
                image_url=product.image_url,
                created_at=product.created_at,
                updated_at=product.updated_at
            )
            
            postgres_session.add(new_product)
            migrated += 1
            
            # Commit in batches
            if migrated % 50 == 0:
                postgres_session.commit()
                safe_print(f"   ✓ {migrated}/{total} products migrated...")
        
        # Final commit
        postgres_session.commit()
        
        # Verify
        final_count = postgres_session.query(Product).count()
        
        safe_print("\n" + "=" * 70)
        safe_print("✅ Migration Complete!")
        safe_print("=" * 70)
        safe_print(f"   SQLite products:     {total}")
        safe_print(f"   PostgreSQL products: {final_count}")
        
        if final_count == total:
            safe_print("\n🎉 All products successfully migrated to Neon!")
            return True
        else:
            safe_print("\n⚠️  Count mismatch - please verify")
            return False
    
    except Exception as e:
        safe_print(f"\n❌ ERROR: {e}")
        postgres_session.rollback()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        sqlite_session.close()
        postgres_session.close()
        safe_print("\n🔒 Database connections closed")


if __name__ == '__main__':
    safe_print("\n🌿 Plants Hub - Database Migration Tool\n")
    
    success = migrate_data()
    
    if success:
        safe_print("\n✨ Migration successful!")
        safe_print("   Your products are now in Neon PostgreSQL")
        safe_print("   Render deployment will use this database")
    else:
        safe_print("\n❌ Migration failed")
        sys.exit(1)
