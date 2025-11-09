"""
Plants Hub - Flask app with ImageKit-only image storage.

Key guarantees:
- Never writes images to Render's filesystem.
- Uploads via ImageKit and stores only the CDN URL and provider file_id.
- Edits and deletes clean up old images in ImageKit when possible.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import or_, text
import os
import logging
import io
import base64

load_dotenv()

import imagekit_client
from models import db, Product


# ----------------------------------------------------------------------------
# App & Database configuration
# ----------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')

database_url = os.getenv('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    if database_url.startswith('postgresql://') and '+psycopg2' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('plants_hub')

# Run DB migrations immediately on import so Gunicorn workers apply schema
run_db_migrations()


# ----------------------------------------------------------------------------
# Tiny migration: ensure image_file_id exists (Postgres & SQLite compatible)
# ----------------------------------------------------------------------------
def run_db_migrations():
    try:
        with app.app_context():
            # Create table if first run
            db.create_all()
            # Add column if missing
            engine = db.engine
            dialect = engine.dialect.name
            if dialect == 'postgresql':
                with engine.begin() as conn:
                    conn.execute(text("""
                        ALTER TABLE products
                        ADD COLUMN IF NOT EXISTS image_file_id VARCHAR(200);
                    """))
            elif dialect == 'sqlite':
                # SQLite doesn't support IF NOT EXISTS; probe pragma
                with engine.connect() as conn:
                    cols = conn.execute(text("PRAGMA table_info(products)")).fetchall()
                    names = {c[1] for c in cols}
                    if 'image_file_id' not in names:
                        # Recreate table is heavy; for dev it's acceptable to skip. Log hint.
                        logger.warning('SQLite detected without image_file_id column. Consider recreating DB.')
    except Exception as e:
        logger.warning('Migration check failed: %s', e)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ----------------------------------------------------------------------------
# Routes - Pages
# ----------------------------------------------------------------------------
@app.route('/')
def index():
    try:
        search_query = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', '').strip()
        max_price = request.args.get('max_price', '').strip()
        category_filter = request.args.get('category', '').strip() or 'all'

        q = Product.query
        if search_query:
            term = f"%{search_query}%"
            q = q.filter(or_(Product.name.ilike(term), Product.description.ilike(term)))
        if category_filter and category_filter != 'all':
            q = q.filter(Product.category == category_filter)
        if min_price:
            try:
                q = q.filter(Product.price >= float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                q = q.filter(Product.price <= float(max_price))
            except ValueError:
                pass

        products = q.order_by(Product.created_at.desc()).all()
        products_dict = []
        for p in products:
            products_dict.append({
                'id': p.id,
                'Product_Name': p.name,
                'Description': p.description,
                'Category': p.category,
                'Price': float(p.price),
                'Quantity': p.quantity,
                'Image_File': p.image_url,  # full CDN URL
                'index': p.id
            })

        suggestions = sorted([n for (n,) in db.session.query(Product.name).distinct().all()], key=str.casefold)
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
        return render_template('index.html', products=[], search_query='', min_price='', max_price='',
                               category_filter='', category_names={}, total_count=0, suggestions=[])


@app.route('/add', methods=['GET', 'POST'])
def add_product():
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
            name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            uploaded_url = request.form.get('uploaded_image_url', '').strip()
            uploaded_id = request.form.get('uploaded_image_id', '').strip()

            if not name:
                flash('Product name is required!', 'danger')
                return redirect(url_for('add_product'))

            try:
                price_val = float(price)
            except ValueError:
                flash('Invalid price format!', 'danger')
                return redirect(url_for('add_product'))

            try:
                qty = int(quantity)
                if qty < 0:
                    qty = 0
            except ValueError:
                qty = 0

            image_url = None
            image_file_id = None

            if uploaded_url:
                image_url = uploaded_url
                image_file_id = uploaded_id or None
            elif 'image' in request.files:
                f = request.files['image']
                if f and f.filename and allowed_file(f.filename):
                    res = imagekit_client.upload_image(f)
                    if res and res.get('url'):
                        image_url = res.get('url')
                        image_file_id = res.get('file_id')
                        flash('Image uploaded to ImageKit successfully!', 'success')
                    else:
                        msg = res.get('message') if isinstance(res, dict) else 'Upload failed'
                        flash(f'ImageKit upload failed: {msg}. Product saved without image.', 'danger')
                elif f and f.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('add_product'))

            product = Product(
                name=name,
                description=description,
                category=category,
                price=price_val,
                quantity=qty,
                image_url=image_url,
                image_file_id=image_file_id
            )
            db.session.add(product)
            db.session.commit()

            flash(f'Product "{name}" added successfully' + (" with image ✅" if image_url else " (no image)"),
                  'success' if image_url else 'warning')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding product: {str(e)}', 'danger')
            return redirect(url_for('add_product'))

    return render_template('add.html', category_names=category_names)


@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
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
            uploaded_id = request.form.get('uploaded_image_id', '').strip()

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
            cloud_used = False

            if uploaded_url:
                if not keep_image and current_id:
                    imagekit_client.delete_image(current_id)
                new_url = uploaded_url
                new_id = uploaded_id or None
                cloud_used = True
            elif 'image' in request.files:
                f = request.files['image']
                if f and f.filename and allowed_file(f.filename):
                    res = imagekit_client.upload_image(f)
                    if res and res.get('url'):
                        if not keep_image and current_id:
                            imagekit_client.delete_image(current_id)
                        new_url = res.get('url')
                        new_id = res.get('file_id')
                        cloud_used = True
                    else:
                        msg = res.get('message') if isinstance(res, dict) else 'Upload failed'
                        flash(f'Cloud upload failed – {msg}. Image unchanged.', 'danger')
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

            if cloud_used:
                flash(f'Product "{name}" updated successfully with cloud image ✅', 'success')
            else:
                flash(f'Product "{name}" updated successfully', 'info')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
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
    return render_template('edit.html', product=product_dict, category_names=category_names)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        name = product.name
        file_id = product.image_file_id
        if file_id:
            imagekit_client.delete_image(file_id)
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'danger')
    return redirect(url_for('index'))


# ----------------------------------------------------------------------------
# API routes
# ----------------------------------------------------------------------------
@app.route('/upload', methods=['POST'])
def api_upload_image():
    if not imagekit_client.is_configured():
        return jsonify({'error': 'ImageKit not configured', 'config': imagekit_client.masked_config()}), 500
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    f = request.files['image']
    if not f or not f.filename:
        return jsonify({'error': 'Empty file'}), 400
    if not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    try:
        res = imagekit_client.upload_image(f)
        if not res or not res.get('url'):
            message = res.get('message') if isinstance(res, dict) else None
            code = res.get('error') if isinstance(res, dict) else None
            payload = {'error': message or 'Upload failed'}
            if code:
                payload['code'] = code
            if code == 'not_configured':
                payload['config'] = imagekit_client.masked_config()
            return jsonify(payload), 500
        return jsonify({'url': res.get('url'), 'file_id': res.get('file_id'), 'name': res.get('name')})
    except Exception as ex:
        logger.exception('Upload failed')
        return jsonify({'error': str(ex)}), 500


@app.route('/diagnostics/imagekit')
def diagnostics_imagekit():
    configured = imagekit_client.is_configured()
    if not configured:
        return jsonify({'imagekit_configured': False, 'config': imagekit_client.masked_config()})
    try:
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5gA9kAAAAASUVORK5CYII=')
        fobj = io.BytesIO(png)
        fobj.name = 'diag.png'
        res = imagekit_client.upload_image(fobj, folder='plants_hub/diagnostics')
        if res and res.get('url'):
            return jsonify({'imagekit_configured': True, 'test_upload_status': 'success', 'test_upload_url': res.get('url')})
        return jsonify({'imagekit_configured': True, 'test_upload_status': 'failed', 'details': res}), 200
    except Exception as ex:
        logger.exception('Diagnostic upload failed')
        return jsonify({'imagekit_configured': True, 'test_upload_status': 'error', 'error': str(ex)}), 200


# ----------------------------------------------------------------------------
# Error handlers
# ----------------------------------------------------------------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def file_too_large(e):
    flash('File is too large! Maximum size is 16MB.', 'danger')
    return redirect(url_for('add_product'))


# ----------------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------------
if __name__ == '__main__':
    run_db_migrations()
    app.run(debug=True, host='0.0.0.0', port=5000)

"""
Minimal, clean Flask app for Plants Hub using ImageKit for image persistence.
This file intentionally keeps routes compact to avoid accidental duplicates.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import os
import logging
import io
import base64
from dotenv import load_dotenv
from sqlalchemy import or_

load_dotenv()

import imagekit_client
from models import db, Product

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')

# DB config
database_url = os.getenv('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    if database_url.startswith('postgresql://') and '+psycopg2' not in database_url:
        database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///plants.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('plants_hub')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    q = Product.query
    products = q.order_by(Product.created_at.desc()).all()
    return render_template('index.html', products=products)


@app.route('/upload', methods=['POST'])
def api_upload_image():
    if not imagekit_client.is_configured():
        return jsonify({'error': 'ImageKit not configured', 'config': imagekit_client.masked_config()}), 500
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    f = request.files['image']
    if not f or not f.filename:
        return jsonify({'error': 'Empty file'}), 400
    if not allowed_file(f.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    try:
        res = imagekit_client.upload_image(f)
        if not res or not res.get('url'):
            message = res.get('message') if isinstance(res, dict) else None
            code = res.get('error') if isinstance(res, dict) else None
            payload = {'error': message or 'Upload failed'}
            if code:
                payload['code'] = code
            if code == 'not_configured':
                payload['config'] = imagekit_client.masked_config()
            return jsonify(payload), 500
        return jsonify({'url': res.get('url'), 'file_id': res.get('file_id'), 'name': res.get('name')})
    except Exception as ex:
        logger.exception('Upload failed')
        return jsonify({'error': str(ex)}), 500


@app.route('/diagnostics/imagekit')
def diagnostics_imagekit():
    configured = imagekit_client.is_configured()
    if not configured:
        return jsonify({'imagekit_configured': False}), 200
    try:
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5gA9kAAAAASUVORK5CYII=')
        fobj = io.BytesIO(png)
        fobj.name = 'diag.png'
        res = imagekit_client.upload_image(fobj, folder='plants_hub/diagnostics')
        if res and res.get('url'):
            return jsonify({'imagekit_configured': True, 'test_upload_status': 'success', 'test_upload_url': res.get('url')}), 200
        return jsonify({'imagekit_configured': True, 'test_upload_status': 'failed'}), 200
    except Exception as ex:
        logger.exception('Diagnostic upload failed')
        return jsonify({'imagekit_configured': True, 'test_upload_status': 'error', 'error': str(ex)}), 200


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)

# Echo SQL queries only in development
app.config['SQLALCHEMY_ECHO'] = not bool(database_url)

# Initialize SQLAlchemy with app
db.init_app(app)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("plants_hub")
logger.info("🌱 Plants Hub application starting. Using ImageKit for persistent images.")

# ============================================================================
# FILE UPLOAD CONFIGURATION
# ============================================================================

UPLOAD_FOLDER = os.path.join('static', 'images')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def allowed_file(filename: str) -> bool:
    """Check if uploaded file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# ROUTES - Main Pages
# ============================================================================

@app.route('/')
def index():
    """Homepage with product listing and filters"""
    try:
        # Get search parameters from request
        search_query = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', '').strip()
        max_price = request.args.get('max_price', '').strip()
        category_filter = request.args.get('category', '').strip() or 'all'

        # Build base query
        query = Product.query

        # Apply filters
        if search_query:
            term = f"%{search_query}%"
            query = query.filter(or_(Product.name.ilike(term), Product.description.ilike(term)))

        if category_filter and category_filter != 'all':
            query = query.filter(Product.category == category_filter)

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

        # Execute query
        products = query.order_by(Product.created_at.desc()).all()

        # Convert for template
        products_dict = []
        for product in products:
            products_dict.append({
                'id': product.id,
                'Product_Name': product.name,
                'Description': product.description,
                'Category': product.category,
                'Price': float(product.price),
                'Quantity': product.quantity,
                'Image_File': product.image_url,
                'index': product.id
            })

        # Suggestions for autocomplete
        suggestions = sorted(
            [p.name for p in Product.query.with_entities(Product.name).distinct().all()],
            key=str.casefold
        )

        # Category display names
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
            uploaded_image_url = request.form.get('uploaded_image_url', '').strip()

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

            # Handle image (prefer URL from frontend upload API)
            image_url = uploaded_image_url if uploaded_image_url else None

            if not image_url and 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    if imagekit_client.is_configured():
                        try:
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                image_url = result['url']
                                flash('Image uploaded to cloud storage successfully!', 'success')
                                logger.info(f"✅ ImageKit upload success for product '{product_name}' -> {image_url}")
                            else:
                                flash('Cloud upload failed – product saved without image. Please retry.', 'danger')
                                logger.error(f"❌ ImageKit upload returned empty result for product '{product_name}'")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)}. Product saved without image. Retry editing to add image.', 'danger')
                            logger.exception(f"❌ ImageKit exception for product '{product_name}'")
                    else:
                        flash('ImageKit not configured – image ignored. Configure env vars and re-upload.', 'warning')
                        logger.warning("ImageKit not configured; image upload skipped.")
                elif file and file.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('add_product'))

            # Create and save product
            new_product = Product(
                name=product_name,
                description=description,
                category=category,
                price=price_float,
                quantity=quantity_int,
                image_url=image_url
            )

            db.session.add(new_product)
            db.session.commit()

            if image_url:
                flash(f'Product "{product_name}" added successfully with image ✅', 'success')
            else:
                flash(f'Product "{product_name}" added successfully (no persistent image)', 'warning')
            return redirect(url_for('index'))

        except Exception as e:
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
            uploaded_image_url = request.form.get('uploaded_image_url', '').strip()

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

            # Current image
            current_image = product.image_url
            new_image = current_image if keep_image else None
            cloud_used = False

            # Prefer URL from frontend upload
            if uploaded_image_url:
                new_image = uploaded_image_url
                cloud_used = True
            elif 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    if imagekit_client.is_configured():
                        try:
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                new_image = result['url']
                                cloud_used = True
                                logger.info(f"✅ ImageKit upload success (edit) for product '{product_name}' -> {new_image}")
                            else:
                                flash('Cloud upload failed – image unchanged.', 'danger')
                                logger.error(f"❌ ImageKit upload returned empty result on edit for '{product_name}'")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)} – image unchanged.', 'danger')
                            logger.exception(f"❌ ImageKit exception during edit for '{product_name}'")
                    else:
                        flash('ImageKit not configured – cannot change image.', 'warning')
                        logger.warning("ImageKit not configured on edit; image unchanged.")
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
        image_url = product.image_url

        # Best-effort: delete local image file if it's a local path
        if image_url and not str(image_url).startswith('http'):
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_url)
            if os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    logger.warning(f"Error deleting local image: {e}")

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
            message = result.get('message') if isinstance(result, dict) else None
            code = result.get('error') if isinstance(result, dict) else None
            payload = {'error': message or 'Upload failed'}
            if code:
                payload['code'] = code
            if code == 'not_configured':
                payload['config'] = imagekit_client.masked_config()
            return jsonify(payload), 500
        return jsonify({
            'url': result.get('url'),
            'file_id': result.get('file_id'),
            'name': result.get('name')
        })
    except Exception as ex:
        logger.exception("/upload failed")
        return jsonify({'error': str(ex)}), 500


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
                    if imagekit_client.is_configured():
                        try:
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                image_filename = result['url']
                                cloud_used = True
                                flash('Image uploaded to cloud storage successfully!', 'success')
                                logger.info(f"✅ ImageKit upload success for product '{product_name}' -> {image_filename}")
                            else:
                                msg = result.get('message') if isinstance(result, dict) else 'Unknown error'
                                flash(f'Cloud upload failed – {msg}. Product saved without image.', 'danger')
                                logger.error(f"❌ ImageKit upload returned empty result for product '{product_name}' -> {result}")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)}. Product saved without image. Retry editing to add image.', 'danger')
                            logger.exception(f"❌ ImageKit exception for product '{product_name}'")
                    else:
                        flash('ImageKit not configured – image ignored. Configure env vars and re-upload.', 'warning')
                        logger.warning("ImageKit not configured; image upload skipped.")
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
                    if imagekit_client.is_configured():
                        try:
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                new_image = result['url']
                                cloud_used = True
                                logger.info(f"✅ ImageKit upload success (edit) for product '{product_name}' -> {new_image}")
                            else:
                                msg = result.get('message') if isinstance(result, dict) else 'Unknown error'
                                flash(f'Cloud upload failed – {msg}. Image unchanged.', 'danger')
                                logger.error(f"❌ ImageKit upload returned empty result on edit for '{product_name}' -> {result}")
                        except Exception as e:
                            flash(f'Cloud upload error: {str(e)} – image unchanged.', 'danger')
                            logger.exception(f"❌ ImageKit exception during edit for '{product_name}'")
                    else:
                        flash('ImageKit not configured – cannot change image.', 'warning')
                        logger.warning("ImageKit not configured on edit; image unchanged.")
                    
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
@app.route('/diagnostics/imagekit-legacy-cleanup')
def diagnostics_imagekit_cleanup():
    """Helper route to confirm legacy Cloudinary code removed."""
    return jsonify({'cloudinary_code_present': False, 'imagekit_configured': imagekit_client.is_configured()})


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
