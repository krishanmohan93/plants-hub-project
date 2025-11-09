"""
Plants Hub - Flask application with ImageKit cloud image storage
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

# Database config
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
        if category_filter != 'all':
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
        products_dict = [
            {
                'id': p.id,
                'Product_Name': p.name,
                'Description': p.description,
                'Category': p.category,
                'Price': float(p.price),
                'Quantity': p.quantity,
                'Image_File': p.image_url,
                'index': p.id,
            }
            for p in products
        ]
        suggestions = sorted([r.name for r in Product.query.with_entities(Product.name).distinct().all()], key=str.casefold)
        category_names = {
            'all': 'All Products',
            'ceramic_pot': 'Ceramic Pots',
            'plastic_pot': 'Plastic Pots',
            'terracotta_pot': 'Terracotta/Soil Pots',
            'fiber_pot': 'Fiber Pots',
            'indoor_plant': 'Indoor Plants',
            'outdoor_plant': 'Outdoor Plants',
            'colorful_pot': 'Colorful Pots',
        }
        return render_template('index.html', products=products_dict, search_query=search_query, min_price=min_price, max_price=max_price, category_filter=category_filter, category_names=category_names, total_count=len(products_dict), suggestions=suggestions)
    except Exception as e:
        logger.exception('Index load failed')
        flash(f'Error loading products: {e}', 'danger')
        return render_template('index.html', products=[], search_query='', min_price='', max_price='', category_filter='', category_names={}, total_count=0, suggestions=[])


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
        'other': 'Other',
    }
    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            uploaded_image_url = request.form.get('uploaded_image_url', '').strip()
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
            image_url = uploaded_image_url if uploaded_image_url else None
            if not image_url and 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    if imagekit_client.is_configured():
                        try:
                            result = imagekit_client.upload_image(file)
                            if result and result.get('url'):
                                image_url = result['url']
                                logger.info(f"ImageKit upload success for '{product_name}' -> {image_url}")
                                flash('Image uploaded successfully!', 'success')
                            else:
                                logger.error(f"ImageKit upload failed for '{product_name}'")
                                flash('Cloud upload failed. Product saved without image.', 'danger')
                        except Exception as ex:
                            logger.exception('ImageKit upload error')
                            flash(f'Cloud upload error: {ex}', 'danger')
                    else:
                        logger.warning('ImageKit not configured')
                        flash('ImageKit not configured. Image ignored.', 'warning')
                elif file and file.filename:
                    flash('Invalid file type! Please upload PNG, JPG, JPEG, or GIF.', 'danger')
                    return redirect(url_for('add_product'))
            new_product = Product(name=product_name, description=description, category=category, price=price_float, quantity=quantity_int, image_url=image_url)
            db.session.add(new_product)
            db.session.commit()
            flash(f'Product "{product_name}" added successfully' + (' with image' if image_url else ''), 'success' if image_url else 'warning')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Add product failed')
            flash(f'Error adding product: {e}', 'danger')
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
        'other': 'Other',
    }
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        try:
            product_name = request.form.get('product_name', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', 'other').strip()
            quantity = request.form.get('quantity', '0').strip()
            keep_image = request.form.get('keep_image') == 'yes'
            uploaded_image_url = request.form.get('uploaded_image_url', '').strip()
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
            current_image = product.image_url
            new_image = current_image if keep_image else None
            cloud_used = False
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
                                logger.info(f"ImageKit upload success (edit) for '{product_name}' -> {new_image}")
                            else:
                                logger.error(f"ImageKit upload failed on edit for '{product_name}'")
                                flash('Cloud upload failed. Image unchanged.', 'danger')
                        except Exception as ex:
                            logger.exception('Edit upload error')
                            flash(f'Cloud upload error: {ex}. Image unchanged.', 'danger')
                    else:
                        logger.warning('ImageKit not configured on edit')
                        flash('ImageKit not configured. Cannot change image.', 'warning')
                elif file and file.filename:
                    flash('Invalid file type!', 'danger')
                    return redirect(url_for('edit_product', product_id=product_id))
            product.name = product_name
            product.description = description
            product.category = category
            product.price = price_float
            product.quantity = quantity_int
            product.image_url = new_image
            product.updated_at = datetime.utcnow()
            db.session.commit()
            flash(f'Product "{product_name}" updated successfully' + (' with cloud image' if cloud_used else ''), 'success' if cloud_used else 'info')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            logger.exception('Edit product failed')
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
        'index': product.id,
    }
    return render_template('edit.html', product=product_dict, category_names=category_names)


@app.route('/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        product_name = product.name
        image_url = product.image_url
        if image_url and not str(image_url).startswith('http'):
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], image_url)
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception:
                    logger.warning('Failed to remove local image')
        db.session.delete(product)
        db.session.commit()
        flash(f'Product "{product_name}" deleted successfully!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback()
        logger.exception('Delete failed')
        flash(f'Error deleting product: {e}', 'danger')
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def api_upload_image():
    if not imagekit_client.is_configured():
        return jsonify({'error': 'ImageKit not configured'}), 500
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
            return jsonify({'error': 'Upload failed'}), 500
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
        logger.exception('Diagnostic failed')
        return jsonify({'imagekit_configured': True, 'test_upload_status': 'error', 'error': str(ex)}), 200


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def file_too_large(e):
    flash('File too large! Maximum 16MB.', 'danger')
    return redirect(url_for('add_product'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Database ready')
    app.run(debug=True, host='0.0.0.0', port=5000)
