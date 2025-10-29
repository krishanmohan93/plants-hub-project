"""
Data Migration Script: SQLite to PostgreSQL
Run this once after deploying to Render with Neon PostgreSQL
to transfer all existing product data from local SQLite database.
"""

import os
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Product, db

def migrate_sqlite_to_postgres(sqlite_path='plants.db', postgres_url=None):
    """
    Migrate data from SQLite database to PostgreSQL
    
    Args:
        sqlite_path: Path to local SQLite database file
        postgres_url: PostgreSQL connection URL (from environment or .env)
    """
    
    if not postgres_url:
        postgres_url = os.getenv('DATABASE_URL')
        if not postgres_url:
            print("❌ ERROR: DATABASE_URL environment variable not set!")
            print("   Set it with your Neon PostgreSQL connection string")
            return False
    
    # Fix postgres:// to postgresql:// for SQLAlchemy compatibility
    if postgres_url.startswith('postgres://'):
        postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)
    
    # Don't force a specific driver; allow SQLAlchemy to choose based on installed packages
    
    # Check if SQLite file exists
    if not os.path.exists(sqlite_path):
        print(f"❌ ERROR: SQLite database '{sqlite_path}' not found!")
        return False
    
    print("=" * 70)
    print("🔄 Starting Data Migration: SQLite → PostgreSQL")
    print("=" * 70)
    
    # Create SQLite engine
    print(f"\n📂 Connecting to SQLite: {sqlite_path}")
    sqlite_engine = create_engine(f'sqlite:///{sqlite_path}')
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_session = SQLiteSession()
    
    # Create PostgreSQL engine
    print(f"🐘 Connecting to PostgreSQL...")
    postgres_engine = create_engine(postgres_url)
    PostgresSession = sessionmaker(bind=postgres_engine)
    postgres_session = PostgresSession()
    
    try:
        # Check if products table exists in SQLite
        inspector = inspect(sqlite_engine)
        if 'products' not in inspector.get_table_names():
            print("⚠️  No 'products' table found in SQLite database")
            return False
        
        # Get all products from SQLite
        print("\n📊 Reading products from SQLite...")
        sqlite_products = sqlite_session.query(Product).all()
        total_count = len(sqlite_products)
        print(f"   Found {total_count} products in SQLite")
        
        if total_count == 0:
            print("ℹ️  No products to migrate")
            return True
        
        # Check existing products in PostgreSQL
        existing_count = postgres_session.query(Product).count()
        print(f"\n🔍 PostgreSQL currently has {existing_count} products")
        
        if existing_count > 0:
            response = input("⚠️  PostgreSQL database already contains data. Overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled by user")
                return False
            
            # Clear existing data
            print("🗑️  Clearing existing PostgreSQL data...")
            postgres_session.query(Product).delete()
            postgres_session.commit()
        
        # Migrate products
        print(f"\n🚚 Migrating {total_count} products...")
        migrated_count = 0
        
        for sqlite_product in sqlite_products:
            # Create new product instance for PostgreSQL
            postgres_product = Product(
                name=sqlite_product.name,
                description=sqlite_product.description,
                category=sqlite_product.category,
                price=sqlite_product.price,
                quantity=sqlite_product.quantity,
                image_url=sqlite_product.image_url,
                created_at=sqlite_product.created_at,
                updated_at=sqlite_product.updated_at
            )
            
            postgres_session.add(postgres_product)
            migrated_count += 1
            
            # Commit in batches of 50
            if migrated_count % 50 == 0:
                postgres_session.commit()
                print(f"   ✓ Migrated {migrated_count}/{total_count} products...")
        
        # Final commit
        postgres_session.commit()
        
        # Verify migration
        final_count = postgres_session.query(Product).count()
        
        print("\n" + "=" * 70)
        print("✅ Migration Complete!")
        print("=" * 70)
        print(f"   SQLite products:     {total_count}")
        print(f"   PostgreSQL products: {final_count}")
        
        if final_count == total_count:
            print("   🎉 All products successfully migrated!")
            return True
        else:
            print("   ⚠️  Product count mismatch - please verify data")
            return False
    
    except Exception as e:
        print(f"\n❌ ERROR during migration: {e}")
        postgres_session.rollback()
        return False
    
    finally:
        sqlite_session.close()
        postgres_session.close()
        print("\n🔒 Database connections closed")


def main():
    """Main execution function"""
    print("\n🌿 Plants Hub - Database Migration Tool\n")
    
    # Check if running in production environment
    if os.getenv('DATABASE_URL'):
        print("🚀 Production environment detected (DATABASE_URL set)")
        sqlite_file = input("Enter path to SQLite database file (default: plants.db): ").strip()
        if not sqlite_file:
            sqlite_file = 'plants.db'
        
        success = migrate_sqlite_to_postgres(sqlite_path=sqlite_file)
    else:
        print("💻 Local environment detected (no DATABASE_URL)")
        print("\nTo migrate to PostgreSQL:")
        print("1. Set DATABASE_URL environment variable with your Neon connection string")
        print("2. Run this script again")
        print("\nExample:")
        print('   $env:DATABASE_URL="postgresql://user:pass@host/db"  # Windows')
        print('   export DATABASE_URL="postgresql://user:pass@host/db"  # Linux/Mac')
        return
    
    if success:
        print("\n✨ You can now deploy your app to Render!")
        print("   The PostgreSQL database is ready with all your products.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
