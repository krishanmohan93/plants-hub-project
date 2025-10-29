"""
Database Models for Plants Hub Application
Uses SQLAlchemy ORM for database operations
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize SQLAlchemy instance
db = SQLAlchemy()


class Product(db.Model):
    """
    Product Model - Represents a plant or pot product in the inventory
    
    Fields:
        - id: Primary key (auto-increment)
        - name: Product name (required, max 200 chars)
        - description: Product description (optional, text field)
        - category: Product category (e.g., ceramic_pot, indoor_plant)
        - price: Product price (decimal, required)
        - quantity: Stock quantity (integer, default 0)
        - image_url: Filename or path to product image
        - created_at: Timestamp when product was created
        - updated_at: Timestamp when product was last updated
    """
    
    __tablename__ = 'products'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Product Information
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True, index=True)
    
    # Pricing and Inventory
    price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    
    # Image
    image_url = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        """String representation of Product"""
        return f'<Product {self.id}: {self.name} - ₹{self.price}>'
    
    def to_dict(self):
        """
        Convert Product object to dictionary for easy JSON serialization
        Useful for API responses and template rendering
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': float(self.price),
            'quantity': self.quantity,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
