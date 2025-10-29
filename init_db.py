"""
Database Initialization and CSV Migration Script
Run this script once to create database tables and migrate existing CSV data
"""

import os
import sys
import pandas as pd
from app import app, db
from models import Product

def init_database():
    """
    Initialize database by creating all tables defined in models.py
    """
    print("🔧 Creating database tables...")
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully!")

def migrate_csv_to_db():
    """
    Migrate existing products.csv data to the database
    Only runs if products.csv exists and database is empty
    """
    csv_file = 'products.csv'
    
    if not os.path.exists(csv_file):
        print(f"ℹ️  No {csv_file} found. Skipping CSV migration.")
        return
    
    with app.app_context():
        # Check if database already has products
        existing_count = Product.query.count()
        if existing_count > 0:
            print(f"ℹ️  Database already contains {existing_count} products. Skipping migration.")
            return
        
        print(f"📦 Reading data from {csv_file}...")
        try:
            # Read CSV file
            df = pd.read_csv(csv_file)
            print(f"   Found {len(df)} products in CSV")
            
            # Migrate each row to database
            migrated_count = 0
            for idx, row in df.iterrows():
                try:
                    # Create Product instance
                    product = Product(
                        name=str(row.get('Product_Name', '')).strip(),
                        description=str(row.get('Description', '')).strip(),
                        category=str(row.get('Category', '')).strip() or None,
                        price=float(row.get('Price', 0)),
                        quantity=int(row.get('Quantity', 0)) if 'Quantity' in df.columns else 0,
                        image_url=str(row.get('Image_File', '')).strip() or None
                    )
                    
                    # Add to session
                    db.session.add(product)
                    migrated_count += 1
                    
                    # Commit in batches of 50 for better performance
                    if migrated_count % 50 == 0:
                        db.session.commit()
                        print(f"   Migrated {migrated_count}/{len(df)} products...")
                
                except Exception as e:
                    print(f"   ⚠️  Error migrating row {idx}: {e}")
                    continue
            
            # Final commit for remaining products
            db.session.commit()
            print(f"✅ Successfully migrated {migrated_count} products to database!")
            
            # Create backup of CSV file
            backup_file = csv_file.replace('.csv', '_backup.csv')
            if not os.path.exists(backup_file):
                df.to_csv(backup_file, index=False)
                print(f"💾 Backup created: {backup_file}")
        
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error during migration: {e}")
            raise

def seed_sample_data():
    """
    Add sample products if database is empty (for testing)
    """
    with app.app_context():
        if Product.query.count() > 0:
            print("ℹ️  Database already has products. Skipping sample data.")
            return
        
        print("🌱 Adding sample products...")
        sample_products = [
            Product(
                name="Ceramic Blue Planter",
                description="Beautiful blue ceramic pot, quantity: 10",
                category="ceramic_pot",
                price=165.00,
                quantity=10,
                image_url="sample_ceramic.jpg"
            ),
            Product(
                name="Indoor Snake Plant",
                description="Low maintenance indoor plant",
                category="indoor_plant",
                price=299.00,
                quantity=15,
                image_url="sample_snake_plant.jpg"
            ),
            Product(
                name="Terracotta Pot Set",
                description="Set of 3 terracotta pots",
                category="terracotta_pot",
                price=450.00,
                quantity=8,
                image_url="sample_terracotta.jpg"
            )
        ]
        
        db.session.bulk_save_objects(sample_products)
        db.session.commit()
        print(f"✅ Added {len(sample_products)} sample products!")

if __name__ == '__main__':
    print("=" * 60)
    print("🌿 Plants Hub - Database Initialization")
    print("=" * 60)
    
    # Step 1: Create database tables
    init_database()
    
    # Step 2: Migrate CSV data (if exists)
    migrate_csv_to_db()
    
    # Step 3: Add sample data if database is still empty
    seed_sample_data()
    
    print("\n" + "=" * 60)
    print("✅ Database setup complete!")
    print("=" * 60)
    print("\n📝 Summary:")
    with app.app_context():
        total_products = Product.query.count()
        print(f"   Total products in database: {total_products}")
    
    print("\n🚀 You can now run: python app.py")
