from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import json
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hardwarehub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/img/products'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # CPU, GPU, RAM, Storage, Motherboard, PSU, Cooling, etc.
    brand = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    specifications = db.Column(db.Text)  # JSON string for tech specs
    image = db.Column(db.String(200))
    warranty = db.Column(db.String(50))  # e.g., "3 Years"
    featured = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Integer, default=0)
    in_stock = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # For products with variants (like RAM with different sizes)
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan')

class ProductVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    name = db.Column(db.String(50))  # e.g., "8GB", "16GB", "512GB", "1TB"
    price = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    delivery_fee = db.Column(db.Integer, default=0)  # Free shipping over ₹5000
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, shipped, delivered, cancelled
    tracking_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    variant_name = db.Column(db.String(50))
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# ==================== DECORATORS ====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES ====================

@app.route('/')
def index():
    featured_products = Product.query.filter_by(featured=True).limit(8).all()
    return render_template('index.html', products=featured_products)

@app.route('/products')
def products():
    category = request.args.get('category', 'all')
    brand = request.args.get('brand', 'all')
    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    
    query = Product.query
    
    if category != 'all':
        query = query.filter_by(category=category)
    if brand != 'all':
        query = query.filter_by(brand=brand)
    if min_price:
        query = query.filter(Product.variants.any(ProductVariant.price >= min_price))
    if max_price:
        query = query.filter(Product.variants.any(ProductVariant.price <= max_price))
    
    products = query.all()
    brands = db.session.query(Product.brand).distinct().all()
    categories = db.session.query(Product.category).distinct().all()
    
    return render_template('products.html', 
                         products=products, 
                         brands=[b[0] for b in brands],
                         categories=[c[0] for c in categories],
                         selected_category=category,
                         selected_brand=brand)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = Product.query.filter_by(category=product.category).limit(4).all()
    return render_template('product_detail.html', product=product, related=related_products)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        phone = request.form.get('phone')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email, phone=phone)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/tracking')
def tracking():
    return render_template('tracking.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

# ==================== API ROUTES ====================

@app.route('/api/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    products_data = []
    for product in products:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'brand': product.brand,
            'description': product.description,
            'specifications': product.specifications,
            'image': product.image,
            'warranty': product.warranty,
            'featured': product.featured,
            'discount': product.discount,
            'in_stock': product.in_stock,
            'variants': [{'name': v.name, 'price': v.price} for v in product.variants]
        })
    return jsonify(products_data)

@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify({
        'id': product.id,
        'name': product.name,
        'category': product.category,
        'brand': product.brand,
        'description': product.description,
        'specifications': product.specifications,
        'image': product.image,
        'warranty': product.warranty,
        'featured': product.featured,
        'discount': product.discount,
        'in_stock': product.in_stock,
        'variants': [{'name': v.name, 'price': v.price} for v in product.variants]
    })

@app.route('/api/place-order', methods=['POST'])
@login_required
def place_order():
    try:
        data = request.json
        
        # Generate order number
        order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate delivery fee (free over ₹5000)
        delivery_fee = 0 if data['subtotal'] >= 5000 else 99
        
        # Create order
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            full_name=data['fullName'],
            phone=data['phoneNumber'],
            address=data['address'],
            payment_method=data['paymentMethod'],
            subtotal=data['subtotal'],
            delivery_fee=delivery_fee,
            total=data['subtotal'] + delivery_fee
        )
        
        db.session.add(order)
        db.session.flush()
        
        # Add order items
        for item in data['items']:
            order_item = OrderItem(
                order_id=order.id,
                product_name=item['name'],
                variant_name=item.get('variantName', ''),
                price=item['price'],
                quantity=item['quantity']
            )
            db.session.add(order_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'order_number': order_number,
            'message': 'Order placed successfully!'
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error placing order: {str(e)}")
        return jsonify({
            'success': False, 
            'message': str(e)
        }), 500

# ==================== ADMIN ROUTES ====================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         recent_orders=recent_orders)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        brand = request.form.get('brand')
        description = request.form.get('description')
        specifications = request.form.get('specifications')
        warranty = request.form.get('warranty')
        featured = request.form.get('featured') == 'on'
        discount = int(request.form.get('discount', 0))
        
        # Handle image upload
        image = request.files.get('image')
        image_filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        # Create product
        product = Product(
            name=name,
            category=category,
            brand=brand,
            description=description,
            specifications=specifications,
            image=image_filename,
            warranty=warranty,
            featured=featured,
            discount=discount
        )
        
        db.session.add(product)
        db.session.flush()
        
        # Add variants
        variant_names = request.form.getlist('variant_name[]')
        variant_prices = request.form.getlist('variant_price[]')
        
        for vname, vprice in zip(variant_names, variant_prices):
            if vname and vprice:
                variant = ProductVariant(
                    product_id=product.id,
                    name=vname,
                    price=int(vprice)
                )
                db.session.add(variant)
        
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/add_product.html')

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.category = request.form.get('category')
        product.brand = request.form.get('brand')
        product.description = request.form.get('description')
        product.specifications = request.form.get('specifications')
        product.warranty = request.form.get('warranty')
        product.featured = request.form.get('featured') == 'on'
        product.discount = int(request.form.get('discount', 0))
        
        # Handle image upload
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            product.image = image_filename
        
        # Update variants
        ProductVariant.query.filter_by(product_id=product.id).delete()
        
        variant_names = request.form.getlist('variant_name[]')
        variant_prices = request.form.getlist('variant_price[]')
        
        for vname, vprice in zip(variant_names, variant_prices):
            if vname and vprice:
                variant = ProductVariant(
                    product_id=product.id,
                    name=vname,
                    price=int(vprice)
                )
                db.session.add(variant)
        
        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/edit_product.html', product=product)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    
    # Delete image file if exists
    if product.image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product.image))
        except:
            pass
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/update-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.json.get('status')
    order.status = status
    db.session.commit()
    return jsonify({'success': True})

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# ==================== INITIALIZATION ====================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin_user():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@hardwarehub.com',
            phone='9876543210',
            address='Admin Office',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created - Username: admin, Password: admin123')

def create_sample_products():
    if Product.query.count() == 0:
        # Sample Processors (CPUs)
        cpu1 = Product(
            name='Intel Core i9-13900K',
            category='CPU',
            brand='Intel',
            description='24-core (8 P-cores + 16 E-cores) desktop processor',
            specifications='Cores: 24, Threads: 32, Max Turbo: 5.8 GHz, Cache: 36MB',
            image='intel_i9.jpg',
            warranty='3 Years',
            featured=True,
            discount=10
        )
        db.session.add(cpu1)
        db.session.flush()
        cpu1.variants.append(ProductVariant(name='Tray', price=45000))
        
        cpu2 = Product(
            name='AMD Ryzen 9 7950X',
            category='CPU',
            brand='AMD',
            description='16-core/32-thread desktop processor',
            specifications='Cores: 16, Threads: 32, Max Boost: 5.7 GHz, Cache: 80MB',
            image='amd_7950x.jpg',
            warranty='3 Years',
            featured=True,
            discount=15
        )
        db.session.add(cpu2)
        db.session.flush()
        cpu2.variants.append(ProductVariant(name='Tray', price=42000))
        
        # Sample Graphics Cards (GPUs)
        gpu1 = Product(
            name='NVIDIA RTX 4090',
            category='GPU',
            brand='NVIDIA',
            description='24GB GDDR6X Graphics Card',
            specifications='CUDA Cores: 16384, Memory: 24GB GDDR6X, Ray Tracing Cores: 3rd Gen',
            image='rtx4090.jpg',
            warranty='3 Years',
            featured=True,
            discount=5
        )
        db.session.add(gpu1)
        db.session.flush()
        gpu1.variants.append(ProductVariant(name='Founders Edition', price=155000))
        gpu1.variants.append(ProductVariant(name='ASUS ROG Strix', price=165000))
        
        gpu2 = Product(
            name='AMD Radeon RX 7900 XTX',
            category='GPU',
            brand='AMD',
            description='24GB GDDR6 Graphics Card',
            specifications='Stream Processors: 6144, Memory: 24GB GDDR6, Ray Accelerators: 96',
            image='rx7900xtx.jpg',
            warranty='3 Years',
            featured=True,
            discount=10
        )
        db.session.add(gpu2)
        db.session.flush()
        gpu2.variants.append(ProductVariant(name='Reference', price=95000))
        
        # Sample RAM
        ram1 = Product(
            name='Corsair Vengeance DDR5',
            category='RAM',
            brand='Corsair',
            description='High-performance DDR5 RAM for gaming and productivity',
            specifications='Speed: 6000MHz, CAS Latency: 36, Voltage: 1.35V',
            image='corsair_ram.jpg',
            warranty='Lifetime',
            featured=True,
            discount=20
        )
        db.session.add(ram1)
        db.session.flush()
        ram1.variants.append(ProductVariant(name='16GB (2x8GB)', price=7500))
        ram1.variants.append(ProductVariant(name='32GB (2x16GB)', price=14000))
        ram1.variants.append(ProductVariant(name='64GB (2x32GB)', price=26000))
        
        # Sample Storage
        ssd1 = Product(
            name='Samsung 980 Pro',
            category='Storage',
            brand='Samsung',
            description='NVMe M.2 SSD with blazing fast speeds',
            specifications='Read: 7000 MB/s, Write: 5000 MB/s, Interface: PCIe 4.0',
            image='samsung_980.jpg',
            warranty='5 Years',
            featured=True,
            discount=15
        )
        db.session.add(ssd1)
        db.session.flush()
        ssd1.variants.append(ProductVariant(name='500GB', price=5500))
        ssd1.variants.append(ProductVariant(name='1TB', price=9500))
        ssd1.variants.append(ProductVariant(name='2TB', price=16500))
        
        # Sample Motherboards
        mobo1 = Product(
            name='ASUS ROG Maximus Z790 Hero',
            category='Motherboard',
            brand='ASUS',
            description='Premium Intel Z790 motherboard for enthusiasts',
            specifications='Socket: LGA1700, RAM: DDR5, WiFi 6E, PCIe 5.0',
            image='asus_z790.jpg',
            warranty='3 Years',
            featured=True,
            discount=10
        )
        db.session.add(mobo1)
        db.session.flush()
        mobo1.variants.append(ProductVariant(name='Standard', price=42000))
        
        # Sample Power Supplies
        psu1 = Product(
            name='Corsair RM850x',
            category='PSU',
            brand='Corsair',
            description='80+ Gold Fully Modular Power Supply',
            specifications='Wattage: 850W, Efficiency: 80+ Gold, Modular: Full',
            image='corsair_psu.jpg',
            warranty='10 Years',
            featured=True,
            discount=15
        )
        db.session.add(psu1)
        db.session.flush()
        psu1.variants.append(ProductVariant(name='850W', price=12000))
        psu1.variants.append(ProductVariant(name='1000W', price=16500))
        
        # Sample Cooling
        cooler1 = Product(
            name='NZXT Kraken X73',
            category='Cooling',
            brand='NZXT',
            description='360mm AIO Liquid Cooler with RGB',
            specifications='Size: 360mm, Fan Speed: 500-2000 RPM, RGB: Yes',
            image='nzxt_cooler.jpg',
            warranty='6 Years',
            featured=True,
            discount=10
        )
        db.session.add(cooler1)
        db.session.flush()
        cooler1.variants.append(ProductVariant(name='360mm', price=16500))
        
        db.session.commit()
        print('Sample computer hardware products created')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
        create_sample_products()
    app.run(debug=True)