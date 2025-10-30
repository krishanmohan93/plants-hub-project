"""
Migration Script: SQLite to Neon PostgreSQL
Transfers all products from local plants.db to Neon cloud database
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from models import Product

def migrate_data():
    """Migrate all products from SQLite to PostgreSQL"""
    
    # Get database URLs
    postgres_url = os.getenv('DATABASE_URL')
    sqlite_path = 'plants.db'
    
    if not postgres_url:
        print("❌ ERROR: DATABASE_URL not found in .env file")
        return False
    
    if not os.path.exists(sqlite_path):
        print(f"❌ ERROR: {sqlite_path} not found")
        return False
    
    # Fix postgres:// to postgresql://
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    # Force psycopg2 driver
    if '+psycopg2' not in postgres_url:
        postgres_url = postgres_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    
    print("=" * 70)
    print("🚀 Starting Migration: SQLite → Neon PostgreSQL")
    print("=" * 70)
    
    # Create engines
    print(f"\n📂 Connecting to SQLite: {sqlite_path}")
    sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
    
    print(f"🐘 Connecting to Neon PostgreSQL...")
    postgres_engine = create_engine(postgres_url)
    
    # Create sessions
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    PostgresSession = sessionmaker(bind=postgres_engine)
    
    sqlite_session = SQLiteSession()
    postgres_session = PostgresSession()
    
    try:
        # Check SQLite data
        print("\n📊 Reading products from SQLite...")
        sqlite_products = sqlite_session.query(Product).all()
        total = len(sqlite_products)
        print(f"   Found {total} products")
        
        if total == 0:
            print("ℹ️  No products to migrate")
            return True
        
        # Check existing PostgreSQL data
        existing = postgres_session.query(Product).count()
        print(f"\n🔍 PostgreSQL currently has {existing} products")
        
        if existing > 0:
            response = input("\n⚠️  PostgreSQL already has data. Clear and migrate? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled")
                return False
            
            print("🗑️  Clearing existing data...")
            postgres_session.query(Product).delete()
            postgres_session.commit()
        
        # Migrate products
        print(f"\n🚚 Migrating {total} products to Neon...")
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
                print(f"   ✓ {migrated}/{total} products migrated...")
        
        # Final commit
        postgres_session.commit()
        
        # Verify
        final_count = postgres_session.query(Product).count()
        
        print("\n" + "=" * 70)
        print("✅ Migration Complete!")
        print("=" * 70)
        print(f"   SQLite products:     {total}")
        print(f"   PostgreSQL products: {final_count}")
        
        if final_count == total:
            print("\n🎉 All products successfully migrated to Neon!")
            return True
        else:
            print("\n⚠️  Count mismatch - please verify")
            return False
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        postgres_session.rollback()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        sqlite_session.close()
        postgres_session.close()
        print("\n🔒 Database connections closed")


if __name__ == '__main__':
    print("\n🌿 Plants Hub - Database Migration Tool\n")
    
    success = migrate_data()
    
    if success:
        print("\n✨ Migration successful!")
        print("   Your products are now in Neon PostgreSQL")
        print("   Render deployment will use this database")
    else:
        print("\n❌ Migration failed")
        sys.exit(1)
