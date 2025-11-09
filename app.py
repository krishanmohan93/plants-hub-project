"""
Plants Hub - Flask Web Application with SQLAlchemy Database
Refactored from CSV storage to proper database using SQLAlchemy ORM
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import logging
import io
import base64
import imagekit_client
from datetime import datetime
from sqlalchemy import or_, and_
import cloudinary_config
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

    # Use psycopg2 driver with Python 3.11
    # Explicitly specify psycopg2 to avoid driver detection issues
    if database_url.startswith('postgresql://') and '+psycopg2' not in database_url:
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
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plants_hub")
logger.info("🌱 Plants Hub application starting. Cloudinary required for persistent images.")

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

            if 'image' in request.files or 'uploaded_image_url' in request.form:
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

                    # Upload to ImageKit if not already provided by frontend
                    if not image_filename and imagekit_client.is_configured():

                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                image_filename = result['url']

                                flash('Image uploaded to cloud storage successfully!', 'success')
                                logger.info(f"✅ ImageKit upload success for product '{product_name}' -> {image_filename}")
    'ceramic_pot': ['ceramic', 'pottery'],
    'plastic_pot': ['plastic'],
    'terracotta_pot': ['terracotta', 'clay', 'soil'],
                                logger.error(f"❌ ImageKit upload returned empty result for product '{product_name}'")
    'indoor_plant': ['indoor', 'snake plant', 'money plant', 'pothos', 'succulent'],
    'outdoor_plant': ['outdoor', 'garden'],
                            logger.exception(f"❌ ImageKit exception for product '{product_name}'")
}
                        if not image_filename:
                            flash('ImageKit not configured – image ignored. Configure env vars and re-upload.', 'warning')
                            logger.warning("ImageKit not configured; image upload skipped.")
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# ROUTES - Main Pages
                    # Upload to ImageKit
                    if imagekit_client.is_configured():
@app.route('/')
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                new_image = result['url']
    Uses SQLAlchemy queries instead of pandas DataFrame
                                logger.info(f"✅ ImageKit upload success (edit) for product '{product_name}' -> {new_image}")
        # Get search parameters from request
        search_query = request.args.get('search', '').strip()
                                logger.error(f"❌ ImageKit upload returned empty result on edit for '{product_name}'")
        max_price = request.args.get('max_price', '').strip()
        category_filter = request.args.get('category', '').strip()
                            logger.exception(f"❌ ImageKit exception during edit for '{product_name}'")
        # Build suggestions (unique product names) for autocomplete
                        flash('ImageKit not configured – cannot change image.', 'warning')
                        logger.warning("ImageKit not configured on edit; image unchanged.")
            suggestions = sorted(
                [p.name for p in Product.query.with_entities(Product.name).distinct().all()],
                key=str.casefold
# DIAGNOSTICS + UPLOAD API (ImageKit)
# ============================================================================
@app.route('/diagnostics/imagekit')
def diagnostics_imagekit():
    """Return JSON diagnostics about ImageKit configuration and test upload."""
    configured = imagekit_client.is_configured()
    test_upload_status = None
    test_upload_url = None
    error = None
    if configured:
        try:
            png_base64 = (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5gA9kAAAAASUVORK5CYII='
            )
            data = base64.b64decode(png_base64)
            file_obj = io.BytesIO(data)
            file_obj.name = 'diagnostic.png'
            result = imagekit_client.upload_image(file_obj, folder='plants_hub/diagnostics')
            if result and result.get('url'):
                test_upload_status = 'success'
                test_upload_url = result.get('url')
            else:
                test_upload_status = 'failed'
        except Exception as ex:
            error = str(ex)
            test_upload_status = 'error'
            logger.exception("Diagnostic ImageKit upload failed")
    return jsonify({
        'imagekit_configured': configured,
        'test_upload_status': test_upload_status,
        'test_upload_url': test_upload_url,
        'error': error
    })

@app.route('/upload', methods=['POST'])
def api_upload_image():
    """API endpoint to upload a single image file to ImageKit.
    Expects multipart/form-data with 'image' field. Returns JSON {url, file_id, name}.
    """
    if not imagekit_client.is_configured():
        return jsonify({'error': 'ImageKit is not configured on the server'}), 500
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    file = request.files['image']
    if not file or not file.filename:
        return jsonify({'error': 'Empty file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    try:
        result = imagekit_client.upload_image(file)
        if not result or not result.get('url'):
            return jsonify({'error': 'Upload failed'}), 500
        return jsonify({
            'url': result.get('url'),
            'file_id': result.get('file_id'),
            'name': result.get('name')
        })
    except Exception as ex:
        logger.exception("/upload failed")
        return jsonify({'error': str(ex)}), 500
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
            cloud_used = False
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Try Cloudinary first, fallback to local storage
                    if cloudinary_config.is_configured():
                        try:
                            result = cloudinary_config.upload_image(file)
                            if result:
                                image_filename = result['url']
                                cloud_used = True
                                flash('Image uploaded to cloud storage successfully!', 'success')
                                logger.info(f"✅ Cloudinary upload success for product '{product_name}' -> {image_filename}")
                            else:
                                # Do NOT silently fallback – tell user and keep no image
                                flash('Cloud upload failed – product saved without image. Please retry.', 'danger')
                                logger.error(f"❌ Cloudinary upload returned empty result for product '{product_name}'")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)}. Product saved without image. Retry editing to add image.', 'danger')
                            logger.exception(f"❌ Cloudinary exception for product '{product_name}'")
                    else:
                        flash('Cloudinary not configured – image ignored. Configure env vars and re-upload.', 'warning')
                        logger.warning("Cloudinary not configured; image upload skipped.")
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
            
            if cloud_used:
                flash(f'Product "{product_name}" added successfully with cloud image ✅', 'success')
            else:
                flash(f'Product "{product_name}" added successfully (no persistent image)', 'warning')
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
            
            cloud_used = False
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    # Try Cloudinary first, fallback to local storage
                    if cloudinary_config.is_configured():
                        try:
                            result = cloudinary_config.upload_image(file)
                            if result:
                                new_image = result['url']
                                cloud_used = True
                                # Delete old Cloudinary image if it exists
                                if current_image and current_image.startswith('http') and not keep_image:
                                    # Extract public_id from URL if it's a Cloudinary URL
                                    pass  # Cloudinary handles this automatically
                                logger.info(f"✅ Cloudinary upload success (edit) for product '{product_name}' -> {new_image}")
                            else:
                                flash('Cloud upload failed – image unchanged.', 'danger')
                                logger.error(f"❌ Cloudinary upload returned empty result on edit for '{product_name}'")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)} – image unchanged.', 'danger')
                            logger.exception(f"❌ Cloudinary exception during edit for '{product_name}'")
                    else:
                        flash('Cloudinary not configured – cannot change image.', 'warning')
                        logger.warning("Cloudinary not configured on edit; image unchanged.")
                    
                    # Delete old local image if it exists and is being replaced
                    if current_image and not current_image.startswith('http') and not keep_image:
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
            
            if cloud_used:
                flash(f'Product "{product_name}" updated successfully with cloud image ✅', 'success')
            else:
                flash(f'Product "{product_name}" updated successfully (image unchanged)', 'info')
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
# DIAGNOSTICS ROUTES
# ============================================================================
@app.route('/diagnostics/cloudinary')
def diagnostics_cloudinary():
    """Return JSON diagnostics about Cloudinary configuration and test upload."""
    configured = cloudinary_config.is_configured()
    test_upload_status = None
    test_upload_url = None
    error = None
    if configured:
        try:
            # 1x1 transparent PNG base64
            png_base64 = (
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5gA9kAAAAASUVORK5CYII='
            )
            data = base64.b64decode(png_base64)
            file_obj = io.BytesIO(data)
            file_obj.name = 'diagnostic.png'
            result = cloudinary_config.upload_image(file_obj, folder='plants_hub/diagnostics')
            if result and result.get('url'):
                test_upload_status = 'success'
                test_upload_url = result.get('url')
            else:
                test_upload_status = 'failed'
        except Exception as ex:
            error = str(ex)
            test_upload_status = 'error'
            logger.exception("Diagnostic Cloudinary upload failed")
    return jsonify({
        'cloudinary_configured': configured,
        'test_upload_status': test_upload_status,
        'test_upload_url': test_upload_url,
        'error': error
    })


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
