"""
Plants Hub - Clean Flask app with ImageKit-only image storage.

This single-file app guarantees:
- Exactly one Flask app and one SQLAlchemy initialization.
- No local filesystem image storage; ImageKit-only.
- Safe, idempotent DB migration executed once at first request.
"""

import os
import logging
import io
import base64
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy import text
# Cloudinary
import cloudinary
from cloudinary import uploader
# ensure cloudinary is configured via helper
import cloudinary_config

# project modules
from models import db, Product

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plants_hub")

# Create Flask app (single instance)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    # SQLAlchemy 1.4+ requires the psycopg2+ scheme
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg2://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///plants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy exactly once
db.init_app(app)

# Allowed image extensions
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename: str) -> bool:
    if not filename:
        return False
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXT


def run_db_migrations_if_needed():
    """Idempotent, safe migration to add image_file_id if it's missing."""
    try:
        uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        with db.engine.connect() as conn:
            if 'postgres' in uri or 'psql' in uri:
                logger.info('Running DB migration: ensure image_file_id column exists')
                conn.execute(text("""
                    ALTER TABLE products
                    ADD COLUMN IF NOT EXISTS image_file_id VARCHAR(200);
                """))
                conn.commit()
            else:
                try:
                    conn.execute(text("ALTER TABLE products ADD COLUMN image_file_id VARCHAR(200);"))
                    conn.commit()
                except Exception:
                    pass
    except Exception as e:
        logger.exception('DB migration failed: %s', e)


# Flag to ensure migration runs only once (Flask 3.x compat)
_migration_executed = False

def ensure_migration():
    global _migration_executed
    if not _migration_executed:
        _migration_executed = True
        run_db_migrations_if_needed()


@app.route('/')
def index():
    ensure_migration()
    
    # Get filter parameters
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', 'all').strip()
    
    # Query products
    products = Product.query.order_by(Product.id.desc()).all()
    items = []
    for p in products:
        # Handle both ImageKit URLs (full URLs) and local filenames
        image_url = p.image_url or ''
        if image_url and not image_url.startswith('http://') and not image_url.startswith('https://') and not image_url.startswith('/static/'):
            # Local filename without path - construct static URL path
            image_url = f'/static/images/{image_url}'
        
        items.append({
            'id': p.id,
            'Product_Name': p.name,
            'Description': p.description,
            'Category': p.category,
            'Price': float(p.price),
            'Quantity': p.quantity,
            'Image_File': image_url,
            'index': p.id,
        })
    
    # Get product name suggestions for search autocomplete
    suggestions = [p.name for p in products]
    
    # Category names for display
    category_names = {
        'all': 'All Products',
        'ceramic_pot': 'Ceramic Pots',
        'plastic_pot': 'Plastic Pots',
        'terracotta_pot': 'Terracotta/Soil Pots',
        'fiber_pot': 'Fiber Pots',
        'indoor_plant': 'Indoor Plants',
        'outdoor_plant': 'Outdoor Plants',
        'colorful_pot': 'Colorful Pots',
        'other': 'Other'
    }
    
    return render_template('index.html', 
                         products=items,
                         suggestions=suggestions,
                         search_query=search_query,
                         category_filter=category_filter,
                         category_names=category_names,
                         total_count=len(items))


@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('product_name', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'other').strip()
        quantity = request.form.get('quantity', '0').strip()

        if not name:
            flash('Product name is required!', 'danger')
            return redirect(url_for('add_product'))

        try:
            price_val = float(price)
            if price_val < 0:
                raise ValueError('negative')
        except Exception:
            flash('Invalid price format!', 'danger')
            return redirect(url_for('add_product'))

        try:
            qty = int(quantity)
            if qty < 0:
                qty = 0
        except ValueError:
            qty = 0

        # Handle image upload via Cloudinary (preferred)
        image_url = None
        image_file_id = None
        if 'image' in request.files:
            f = request.files['image']
            if f and f.filename and allowed_file(f.filename):
                try:
                    # Upload directly from file storage to Cloudinary
                    res = uploader.upload(f, folder='plants_hub')
                    image_url = res.get('secure_url')
                    image_file_id = res.get('public_id')
                    logger.info('Uploaded image to Cloudinary: %s (public_id=%s)', image_url, image_file_id)
                except Exception as e:
                    logger.exception('Cloudinary upload failed: %s', e)
                    flash('Image upload failed; product saved without image.', 'warning')

        try:
            p = Product(
                name=name,
                description=description,
                category=category,
                price=price_val,
                quantity=qty,
                image_url=image_url,
                image_file_id=image_file_id,
            )
            db.session.add(p)
            db.session.commit()
            flash(f'Product "{name}" added successfully', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Failed to add product: %s', e)
            flash(f'Error adding product: {e}', 'danger')
            return redirect(url_for('add_product'))

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
    return render_template('add.html', category_names=category_names)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        try:
            name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            keep_image = request.form.get('keep_image') == 'yes'
            uploaded_url = request.form.get('uploaded_image_url', '').strip()
            uploaded_id = request.form.get('uploaded_image_id', '').strip() or None

            if not name:
                flash('Product name is required!', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))

            try:
                price_val = float(price)
                if price_val < 0:
                    raise ValueError('negative')
            except Exception:
                flash('Invalid price format!', 'danger')
                return redirect(url_for('edit_product', product_id=product_id))

            try:
                qty = int(quantity)
                if qty < 0:
                    qty = 0
            except ValueError:
                qty = 0

            current_url = product.image_url
            current_id = product.image_file_id

            new_url = current_url if keep_image else None
            new_id = current_id if keep_image else None

            if uploaded_url:
                new_url = uploaded_url
                new_id = uploaded_id
            elif 'image' in request.files:
                f = request.files['image']
                if f and f.filename and allowed_file(f.filename):
                    try:
                        # Upload replacement image to Cloudinary
                        res = uploader.upload(f, folder='plants_hub')
                        new_url = res.get('secure_url')
                        new_id = res.get('public_id')
                        logger.info('Uploaded replacement image to Cloudinary: %s (public_id=%s)', new_url, new_id)
                        # If previously stored in Cloudinary, attempt to delete old image
                        if current_id:
                            try:
                                uploader.destroy(current_id)
                                logger.info('Deleted previous Cloudinary image: %s', current_id)
                            except Exception:
                                logger.warning('Failed to delete previous Cloudinary image: %s', current_id)
                        
                    except Exception as e:
                        logger.error(f'Failed to save image locally: {e}')
                        flash('Image upload failed. Image unchanged.', 'danger')
                elif f and f.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('edit_product', product_id=product_id))

            product.name = name
            product.description = description
            product.category = category
            product.price = price_val
            product.quantity = qty
            product.image_url = new_url
            product.image_file_id = new_id
            product.updated_at = datetime.utcnow()

            db.session.commit()

            flash(f'Product "{name}" updated successfully', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Error updating product: %s', e)
            flash(f'Error updating product: {e}', 'danger')
            return redirect(url_for('edit_product', product_id=product_id))

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
    return render_template('edit.html', product=product_dict, category_names=category_names)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        name = product.name
        # Delete the product from database
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logger.exception('Error deleting product: %s', e)
        flash(f'Error deleting product: {e}', 'danger')
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST', 'OPTIONS'])
def api_upload_image():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response, 200
    
    logger.info('📤 Upload request received from %s', request.remote_addr)
    
    if 'image' not in request.files:
        logger.error('❌ No image field in request.files. Fields: %s', list(request.files.keys()))
        return jsonify({'error': 'No image provided. Expected field name: "image"'}), 400
    
    f = request.files['image']
    if not f or not f.filename:
        logger.error('❌ Empty file or no filename')
        return jsonify({'error': 'Empty file'}), 400
    
    # Check file size without reading entire content into memory
    filename = secure_filename(f.filename)
    logger.info('📁 File received: %s', filename)
    
    if not allowed_file(filename):
        logger.error('❌ Invalid file type: %s', filename)
        return jsonify({'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXT)}'}), 400
    
    try:
        logger.info('📤 Uploading image to Cloudinary...')
        res = uploader.upload(f, folder='plants_hub')
        image_url = res.get('secure_url')
        public_id = res.get('public_id')
        logger.info('✅ Uploaded to Cloudinary: %s (public_id=%s)', image_url, public_id)

        response = jsonify({
            'url': image_url,
            'filename': os.path.basename(image_url) if image_url else None,
            'file_id': public_id
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 200
        
    except Exception as e:
        logger.error('❌ Failed to save image: %s', e)
        return jsonify({
            'error': f'Failed to save image: {str(e)}',
            'type': 'SaveError'
        }), 500


@app.route('/diagnostics/imagekit')
def diagnostics_imagekit():
    """ImageKit diagnostics endpoint - now using local storage"""
    return jsonify({
        'imagekit_configured': False,
        'storage_type': 'local',
        'storage_path': 'static/images/',
        'message': 'Using local file storage instead of ImageKit'
    })


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def file_too_large(e):
    return 'File too large', 413


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=os.getenv('FLASK_DEBUG') == '1')
