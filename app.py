"""
Plants Hub - Flask Web Application with SQLAlchemy Database
Refactored from CSV storage to proper database using SQLAlchemy ORM
"""

from flask import Flask, render_template, request, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy import or_, and_
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import database and models
from models import db, Product

# ============================================================================
# FLASK APP CONFIGURATION
# ============================================================================

app = Flask(__name__)

# Secret key from environment variable or fallback
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here-change-in-production')

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Configure Database URI
# Automatically uses PostgreSQL on Render (via DATABASE_URL env var)
# Falls back to SQLite for local development
database_url = os.getenv('DATABASE_URL')

if database_url:
    # Production: Use PostgreSQL from environment variable
    # Fix for render.com: convert postgres:// to postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Force psycopg2 driver on Render to avoid missing 'psycopg' module
    # SQLAlchemy 2.x may default to 'psycopg' if available; ensure psycopg2 instead
    if database_url.startswith('postgresql://') and '+psycopg2' not in database_url and '+psycopg' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Development: Use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'

# Disable track modifications (saves resources)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Echo SQL queries only in development
app.config['SQLALCHEMY_ECHO'] = not bool(database_url)

# Initialize SQLAlchemy with app
db.init_app(app)

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Product categories for filtering
CATEGORIES = {
    'ceramic_pot': ['ceramic', 'pottery'],
    'plastic_pot': ['plastic'],
    'terracotta_pot': ['terracotta', 'clay', 'soil'],
    'fiber_pot': ['fiber', 'fibre'],
    'indoor_plant': ['indoor', 'snake plant', 'money plant', 'pothos', 'succulent'],
    'outdoor_plant': ['outdoor', 'garden'],
    'colorful_pot': ['red', 'blue', 'green', 'orange', 'yellow', 'multicolor', 'purple', 'pink']
}

def allowed_file(filename):
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    """
    Home page - Display all products with search and category filtering
    Uses SQLAlchemy queries instead of pandas DataFrame
    """
    try:
        # Start with base query
        query = Product.query
        
        # Get search parameters from request
        search_query = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', '').strip()
        max_price = request.args.get('max_price', '').strip()
        category_filter = request.args.get('category', '').strip()
        
        # Build suggestions (unique product names) for autocomplete
        suggestions = []
        try:
            suggestions = sorted(
                [p.name for p in Product.query.with_entities(Product.name).distinct().all()],
                key=str.casefold
            )
        except Exception:
            suggestions = []
        
        # Apply text search filter (search in name and description)
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                or_(
                    Product.name.ilike(search_pattern),
                    Product.description.ilike(search_pattern)
                )
            )
        
        # Apply category filter
        if category_filter and category_filter != 'all':
            keywords = CATEGORIES.get(category_filter, [])
            if keywords:
                # Build OR conditions for category keywords
                category_conditions = []
                for keyword in keywords:
                    pattern = f'%{keyword}%'
                    category_conditions.append(Product.name.ilike(pattern))
                    category_conditions.append(Product.description.ilike(pattern))
                
                query = query.filter(or_(*category_conditions))
        
        # Apply price range filters
        if min_price:
            try:
                query = query.filter(Product.price >= float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                query = query.filter(Product.price <= float(max_price))
            except ValueError:
                pass
        
        # Execute query and get all matching products
        products = query.order_by(Product.created_at.desc()).all()
        
        # Convert to dictionary format for template
        products_dict = []
        for product in products:
            product_data = {
                'id': product.id,
                'Product_Name': product.name,
                'Description': product.description,
                'Category': product.category,
                'Price': float(product.price),
                'Quantity': product.quantity,
                'Image_File': product.image_url,
                'index': product.id  # Use ID instead of index for edit/delete
            }
            products_dict.append(product_data)
        
        # Define category display names
        category_names = {
            'all': 'All Products',
            'ceramic_pot': 'Ceramic Pots',
            'plastic_pot': 'Plastic Pots',
            'terracotta_pot': 'Terracotta/Soil Pots',
            'fiber_pot': 'Fiber Pots',
            'indoor_plant': 'Indoor Plants',
            'outdoor_plant': 'Outdoor Plants',
            'colorful_pot': 'Colorful Pots'
        }
        
        return render_template('index.html',
                             products=products_dict,
                             search_query=search_query,
                             min_price=min_price,
                             max_price=max_price,
                             category_filter=category_filter,
                             category_names=category_names,
                             total_count=len(products_dict),
                             suggestions=suggestions)
    
    except Exception as e:
        flash(f'Error loading products: {str(e)}', 'danger')
        return render_template('index.html',
                             products=[],
                             search_query='',
                             min_price='',
                             max_price='',
                             category_filter='',
                             category_names={},
                             total_count=0,
                             suggestions=[])


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    """
    Add new product page
    GET: Display add product form
    POST: Process form and add product to database
    """
    # Define category display names for the form
    category_names = {
        'ceramic_pot': 'Ceramic Pot',
        'plastic_pot': 'Plastic Pot',
        'terracotta_pot': 'Terracotta/Soil Pot',
        'fiber_pot': 'Fiber Pot',
        'indoor_plant': 'Indoor Plant',
        'outdoor_plant': 'Outdoor Plant',
        'colorful_pot': 'Colorful Pot',
        'other': 'Other'
    }
    
    if request.method == 'POST':
        try:
            # Get form data
            product_name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            
            # Validate inputs
            if not product_name:
                flash('Product name is required!', 'danger')
                return redirect(url_for('add_product'))
            
            if not price:
                flash('Price is required!', 'danger')
                return redirect(url_for('add_product'))
            
            try:
                price_float = float(price)
                if price_float < 0:
                    flash('Price must be a positive number!', 'danger')
                    return redirect(url_for('add_product'))
            except ValueError:
                flash('Invalid price format!', 'danger')
                return redirect(url_for('add_product'))
            
            try:
                quantity_int = int(quantity)
                if quantity_int < 0:
                    quantity_int = 0
            except ValueError:
                quantity_int = 0
            
            # Handle file upload
            image_filename = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid name conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"
                    
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    image_filename = filename
                elif file and file.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('add_product'))
            
            # Create new Product instance
            new_product = Product(
                name=product_name,
                description=description,
                category=category,
                price=price_float,
                quantity=quantity_int,
                image_url=image_filename
            )
            
            # Add to database session and commit
            db.session.add(new_product)
            db.session.commit()
            
            flash(f'Product "{product_name}" added successfully!', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            # Rollback transaction on error
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            return redirect(url_for('add_product'))
    
    return render_template('add.html', category_names=category_names)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """
    Edit existing product
    GET: Display edit form with current product data
    POST: Update product in database
    """
    # Define category display names for the form
    category_names = {
        'ceramic_pot': 'Ceramic Pot',
        'plastic_pot': 'Plastic Pot',
        'terracotta_pot': 'Terracotta/Soil Pot',
        'fiber_pot': 'Fiber Pot',
        'indoor_plant': 'Indoor Plant',
        'outdoor_plant': 'Outdoor Plant',
        'colorful_pot': 'Colorful Pot',
        'other': 'Other'
    }
    
    # Get product from database
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        try:
            # Get form data
            product_name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            keep_image = request.form.get('keep_image') == 'yes'
            
            # Validate inputs
            if not product_name:
                flash('Product name is required!', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))
            
            if not price:
                flash('Price is required!', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))
            
            try:
                price_float = float(price)
                if price_float < 0:
                    flash('Price must be a positive number!', 'danger')
                    return redirect(url_for('edit_product', product_id=product_id))
            except ValueError:
                flash('Invalid price format!', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))
            
            try:
                quantity_int = int(quantity)
                if quantity_int < 0:
                    quantity_int = 0
            except ValueError:
                quantity_int = 0
            
            # Handle image update
            current_image = product.image_url
            new_image = current_image if keep_image else None
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid name conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    name, ext = os.path.splitext(filename)
                    filename = f"{name}_{timestamp}{ext}"
                    
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    new_image = filename
                    
                    # Delete old image if it exists and is being replaced
                    if current_image and not keep_image:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], current_image)
                        if os.path.exists(old_image_path):
                            try:
                                os.remove(old_image_path)
                            except:
                                pass
                elif file and file.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('edit_product', product_id=product_id))
            
            # Update product fields
            product.name = product_name
            product.description = description
            product.category = category
            product.price = price_float
            product.quantity = quantity_int
            product.image_url = new_image
            product.updated_at = datetime.utcnow()
            
            # Commit changes to database
            db.session.commit()
            
            flash(f'Product "{product_name}" updated successfully!', 'success')
            return redirect(url_for('index'))
        
        except Exception as e:
            # Rollback transaction on error
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
            return redirect(url_for('edit_product', product_id=product_id))
    
    # GET request - display form with current data
    product_dict = {
        'id': product.id,
        'Product_Name': product.name,
        'Description': product.description,
        'Category': product.category,
        'Price': float(product.price),
        'Quantity': product.quantity,
        'Image_File': product.image_url,
        'index': product.id
    }
    
    return render_template('edit.html', product=product_dict, category_names=category_names)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    """
    Delete a product
    POST only to prevent accidental deletion via GET
    """
    try:
        # Get product from database
        product = Product.query.get_or_404(product_id)
        
        # Store product name for flash message
        product_name = product.name
        image_file = product.image_url
        
        # Delete image file if it exists
        if image_file:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_file)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Error deleting image: {e}")
        
        # Delete product from database
        db.session.delete(product)
        db.session.commit()
        
        flash(f'Product "{product_name}" deleted successfully!', 'success')
    
    except Exception as e:
        # Rollback transaction on error
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    
    return redirect(url_for('index'))


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(413)
def file_too_large(e):
    """Handle file upload size limit exceeded"""
    flash('File is too large! Maximum size is 16MB.', 'danger')
    return redirect(url_for('add_product'))


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
        print("✅ Database tables ready!")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
