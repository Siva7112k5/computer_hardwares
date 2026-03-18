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

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/uploads/tickets', exist_ok=True)
os.makedirs('static/img/services', exist_ok=True)

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
    service_bookings = db.relationship('ServiceBooking', backref='user', lazy=True)
    support_tickets = db.relationship('SupportTicket', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    specifications = db.Column(db.Text)
    image = db.Column(db.String(200))
    warranty = db.Column(db.String(50))
    featured = db.Column(db.Boolean, default=False)
    discount = db.Column(db.Integer, default=0)
    in_stock = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    variants = db.relationship('ProductVariant', backref='product', cascade='all, delete-orphan')

class ProductVariant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    name = db.Column(db.String(50))
    price = db.Column(db.Integer, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    shipping = db.Column(db.Integer, default=99)
    tax = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    tracking_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100), nullable=False)
    brand = db.Column(db.String(50))
    variant_name = db.Column(db.String(50))
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class Service(db.Model):
    """Service model for PC repair and support services"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.String(50))
    includes = db.Column(db.Text)
    image = db.Column(db.String(200))
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('ServiceBooking', backref='service', lazy=True)

class ServiceBooking(db.Model):
    """Service booking model"""
    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text, nullable=False)
    preferred_date = db.Column(db.String(20))
    preferred_time = db.Column(db.String(20))
    issue_description = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    price = db.Column(db.Integer, nullable=False)
    technician = db.Column(db.String(100))
    completed_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SupportTicket(db.Model):
    """Customer support ticket model"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    attachment = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    
    replies = db.relationship('TicketReply', backref='ticket', cascade='all, delete-orphan')

class TicketReply(db.Model):
    """Replies to support tickets"""
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('support_ticket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_staff = db.Column(db.Boolean, default=False)
    attachment = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])

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
    featured_services = Service.query.filter_by(featured=True).limit(4).all()
    return render_template('index.html', products=featured_products, services=featured_services)

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
    
    products = query.all()
    
    if min_price or max_price:
        filtered_products = []
        for product in products:
            if product.variants:
                min_product_price = min(v.price for v in product.variants)
                if min_price and min_product_price < min_price:
                    continue
                if max_price and min_product_price > max_price:
                    continue
                filtered_products.append(product)
        products = filtered_products
    
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

@app.route('/services')
def services():
    """List all available services"""
    category = request.args.get('category', 'all')
    query = Service.query
    
    if category != 'all':
        query = query.filter_by(category=category)
    
    services = query.all()
    categories = db.session.query(Service.category).distinct().all()
    
    return render_template('services.html', 
                         services=services,
                         categories=[c[0] for c in categories],
                         selected_category=category)

@app.route('/service/<int:service_id>')
def service_detail(service_id):
    """Service detail page"""
    service = Service.query.get_or_404(service_id)
    related_services = Service.query.filter_by(category=service.category).limit(3).all()
    return render_template('service_detail.html', service=service, related=related_services)

@app.route('/book-service/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(service_id):
    """Book a service"""
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        booking_number = f"SRV{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        booking = ServiceBooking(
            booking_number=booking_number,
            user_id=current_user.id,
            service_id=service.id,
            full_name=request.form.get('full_name'),
            phone=request.form.get('phone'),
            email=request.form.get('email'),
            address=request.form.get('address'),
            preferred_date=request.form.get('preferred_date'),
            preferred_time=request.form.get('preferred_time'),
            issue_description=request.form.get('issue_description'),
            price=service.price,
            status='pending'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Service booked successfully! Our team will contact you shortly.', 'success')
        return redirect(url_for('my_bookings'))
    
    # Pass current datetime to template
    now = datetime.now()
    return render_template('book_service.html', service=service, now=now)


@app.route('/my-bookings')
@login_required
def my_bookings():
    """View user's service bookings"""
    bookings = ServiceBooking.query.filter_by(user_id=current_user.id).order_by(ServiceBooking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/support')
def support():
    """Support home page"""
    return render_template('support.html')

@app.route('/support/new-ticket', methods=['GET', 'POST'])
@login_required
def new_ticket():
    """Create a new support ticket"""
    if request.method == 'POST':
        ticket_number = f"TKT{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        attachment = request.files.get('attachment')
        attachment_filename = None
        if attachment and attachment.filename:
            filename = secure_filename(attachment.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            attachment_filename = f"{timestamp}_{filename}"
            attachment.save(os.path.join('static/uploads/tickets', attachment_filename))
        
        ticket = SupportTicket(
            ticket_number=ticket_number,
            user_id=current_user.id,
            subject=request.form.get('subject'),
            category=request.form.get('category'),
            priority=request.form.get('priority', 'medium'),
            message=request.form.get('message'),
            attachment=attachment_filename
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        flash('Support ticket created successfully!', 'success')
        return redirect(url_for('my_tickets'))
    
    return render_template('new_ticket.html')

@app.route('/my-tickets')
@login_required
def my_tickets():
    """View user's support tickets"""
    tickets = SupportTicket.query.filter_by(user_id=current_user.id).order_by(SupportTicket.created_at.desc()).all()
    return render_template('my_tickets.html', tickets=tickets)

@app.route('/ticket/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_detail(ticket_id):
    """View and reply to support ticket"""
    ticket = SupportTicket.query.get_or_404(ticket_id)
    
    if ticket.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied!', 'danger')
        return redirect(url_for('my_tickets'))
    
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            reply = TicketReply(
                ticket_id=ticket.id,
                user_id=current_user.id,
                message=message,
                is_staff=current_user.is_admin
            )
            db.session.add(reply)
            
            if ticket.status == 'open':
                ticket.status = 'in-progress'
            
            db.session.commit()
            flash('Reply added successfully!', 'success')
    
    return render_template('ticket_detail.html', ticket=ticket)

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
        
        order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        shipping = 0 if data['subtotal'] >= 5000 else 99
        tax = round(data['subtotal'] * 0.18)
        total = data['subtotal'] + shipping + tax
        
        order = Order(
            order_number=order_number,
            user_id=current_user.id,
            full_name=data['fullName'],
            phone=data['phoneNumber'],
            email=data.get('email', ''),
            address=data['address'],
            payment_method=data['paymentMethod'],
            subtotal=data['subtotal'],
            shipping=shipping,
            tax=tax,
            total=total
        )
        
        db.session.add(order)
        db.session.flush()
        
        for item in data['items']:
            order_item = OrderItem(
                order_id=order.id,
                product_name=item['name'],
                brand=item.get('brand', ''),
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
    total_services = Service.query.count()
    total_orders = Order.query.count()
    total_tickets = SupportTicket.query.filter_by(status='open').count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_users=total_users,
                         total_products=total_products,
                         total_services=total_services,
                         total_orders=total_orders,
                         total_tickets=total_tickets,
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
        
        image = request.files.get('image')
        image_filename = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
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
        product.description = request.form.get('description', '')
        product.specifications = request.form.get('specifications', '')
        product.warranty = request.form.get('warranty', '')
        product.featured = request.form.get('featured') == 'on'
        product.discount = int(request.form.get('discount', 0))
        
        if not product.brand:
            flash('Brand is required!', 'danger')
            return redirect(url_for('edit_product', product_id=product.id))
        
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            product.image = image_filename
        
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
    
    if product.image:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product.image))
        except:
            pass
    
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

@app.route('/admin/services')
@login_required
@admin_required
def admin_services():
    """Admin: Manage services"""
    services = Service.query.all()
    return render_template('admin/services.html', services=services)

@app.route('/admin/services/add', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_add_service():
    """Admin: Add new service"""
    if request.method == 'POST':
        service = Service(
            name=request.form.get('name'),
            category=request.form.get('category'),
            description=request.form.get('description'),
            price=int(request.form.get('price')),
            duration=request.form.get('duration'),
            includes=request.form.get('includes'),
            featured=request.form.get('featured') == 'on'
        )
        
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join('static/img/services', image_filename))
            service.image = image_filename
        
        db.session.add(service)
        db.session.commit()
        flash('Service added successfully!', 'success')
        return redirect(url_for('admin_services'))
    
    return render_template('admin/add_service.html')

@app.route('/admin/services/edit/<int:service_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_service(service_id):
    """Admin: Edit service"""
    service = Service.query.get_or_404(service_id)
    
    if request.method == 'POST':
        service.name = request.form.get('name')
        service.category = request.form.get('category')
        service.description = request.form.get('description')
        service.price = int(request.form.get('price'))
        service.duration = request.form.get('duration')
        service.includes = request.form.get('includes')
        service.featured = request.form.get('featured') == 'on'
        
        image = request.files.get('image')
        if image and image.filename:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            image_filename = f"{timestamp}_{filename}"
            image.save(os.path.join('static/img/services', image_filename))
            service.image = image_filename
        
        db.session.commit()
        flash('Service updated successfully!', 'success')
        return redirect(url_for('admin_services'))
    
    return render_template('admin/edit_service.html', service=service)

@app.route('/admin/services/delete/<int:service_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_service(service_id):
    """Admin: Delete service"""
    service = Service.query.get_or_404(service_id)
    
    if service.image:
        try:
            os.remove(os.path.join('static/img/services', service.image))
        except:
            pass
    
    db.session.delete(service)
    db.session.commit()
    flash('Service deleted successfully!', 'success')
    return redirect(url_for('admin_services'))

@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    """Admin: View all service bookings"""
    bookings = ServiceBooking.query.order_by(ServiceBooking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/tickets')
@login_required
@admin_required
def admin_tickets():
    """Admin: View all support tickets"""
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template('admin/tickets.html', tickets=tickets)

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
        print('✅ Admin user created - Username: admin, Password: admin123')
    else:
        print('✅ Admin user already exists')

def create_sample_products():
    if Product.query.count() == 0:
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
        
        db.session.commit()
        print('✅ Sample products created successfully')

def create_sample_services():
    """Create sample services for demonstration"""
    if Service.query.count() == 0:
        services = [
            {
                'name': 'PC Diagnostic & Repair',
                'category': 'Repair',
                'description': 'Comprehensive diagnostic and repair service for desktop PCs. Includes hardware testing, software troubleshooting, and component-level repair.',
                'price': 999,
                'duration': '2-3 hours',
                'includes': 'Hardware diagnostics, Software troubleshooting, Virus removal, Performance optimization',
                'featured': True
            },
            {
                'name': 'Laptop Service',
                'category': 'Repair',
                'description': 'Professional laptop repair service including screen replacement, keyboard repair, battery replacement, and motherboard repair.',
                'price': 1499,
                'duration': '24-48 hours',
                'includes': 'Screen repair, Keyboard replacement, Battery service, Motherboard repair, Thermal paste renewal',
                'featured': True
            },
            {
                'name': 'PC Assembly',
                'category': 'Installation',
                'description': 'Expert PC assembly service. We\'ll assemble your components with professional cable management and testing.',
                'price': 1999,
                'duration': '3-4 hours',
                'includes': 'Component assembly, Cable management, BIOS configuration, Stress testing, OS installation',
                'featured': True
            },
            {
                'name': 'Data Recovery',
                'category': 'Repair',
                'description': 'Professional data recovery service for failed hard drives, SSDs, and storage devices.',
                'price': 2999,
                'duration': '3-5 days',
                'includes': 'Drive diagnostics, Data extraction, Recovery to new drive, File verification',
                'featured': False
            },
            {
                'name': 'PC Consultation',
                'category': 'Consultation',
                'description': 'One-on-one consultation for PC builds, upgrades, and optimization. Get expert advice tailored to your needs.',
                'price': 499,
                'duration': '1 hour',
                'includes': 'Build planning, Component selection, Compatibility check, Performance optimization tips',
                'featured': True
            },
            {
                'name': 'Annual Maintenance',
                'category': 'Maintenance',
                'description': 'Comprehensive annual maintenance contract for businesses. Regular checkups and priority support.',
                'price': 9999,
                'duration': '1 year',
                'includes': 'Quarterly cleaning, Software updates, Priority support, 20% off on repairs',
                'featured': False
            }
        ]
        
        for s in services:
            service = Service(
                name=s['name'],
                category=s['category'],
                description=s['description'],
                price=s['price'],
                duration=s['duration'],
                includes=s['includes'],
                featured=s['featured']
            )
            db.session.add(service)
        
        db.session.commit()
        print('✅ Sample services created successfully')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin_user()
        create_sample_products()
        create_sample_services()
    app.run(debug=True, host='127.0.0.1', port=5000)