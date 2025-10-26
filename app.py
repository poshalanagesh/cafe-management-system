from flask import Flask, render_template, request, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import logging
# import mysql.connector
# from weasyprint import HTML, CSS

# Update the logging configuration at the top after imports
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
logger.debug("Initializing Flask app...")

# Add debug logging for template directory
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
logger.debug(f"Template directory: {template_dir}")
logger.debug(f"Static directory: {static_dir}")
app.template_folder = template_dir
app.static_folder = static_dir

# Test database connection before configuring
# try:
#     conn = mysql.connector.connect(
#         host="localhost",
#         user="root",
#         password="391490"
#     )
#     logger.debug("Successfully connected to MySQL server")
    
#     # Create database if it doesn't exist
#     cursor = conn.cursor()
#     cursor.execute("CREATE DATABASE IF NOT EXISTS cafe_db")
#     cursor.close()
#     conn.close()
#     logger.debug("cafe_db database created/verified")
# except Exception as e:
#     logger.error(f"Failed to connect to MySQL: {str(e)}")
#     raise

app.config['SECRET_KEY'] = '391490'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cafe.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logger.debug("Initializing database connection...")
try:
    db = SQLAlchemy(app)
    logger.debug("SQLAlchemy database connection successful!")
except Exception as e:
    logger.error(f"Database connection failed: {str(e)}")
    raise

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))

class Order(db.Model):
    __tablename__ = 'order'  # Explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date_ordered = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')
    total_amount = db.Column(db.Float, nullable=False)
    user = db.relationship('User', backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    menu_item = db.relationship('MenuItem', backref='cart_items')

class OrderItem(db.Model):
    __tablename__ = 'order_items'  # Explicitly set table name
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    menu_item = db.relationship('MenuItem')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    coffees = MenuItem.query.filter_by(category='Coffee').all()
    snacks = MenuItem.query.filter_by(category='Snacks').all()
    cart_items = []
    cart_total = 0
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_total = sum(item.menu_item.price * item.quantity for item in cart_items)
    return render_template('home.html', coffees=coffees, snacks=snacks, cart_items=cart_items, cart_total=cart_total)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password or not confirm_password:
            flash('All fields are required', 'error')
            return redirect(url_for('register'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
            
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('home'))
    menu_items = MenuItem.query.all()
    return render_template('admin.html', menu_items=menu_items)

@app.route('/admin/add_item', methods=['POST'])
@login_required
def admin_add_item():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('home'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    price = float(request.form.get('price'))
    category = request.form.get('category')
    
    item = MenuItem(name=name, description=description, price=price, category=category)
    db.session.add(item)
    db.session.commit()
    
    flash('Menu item added successfully!')
    return redirect(url_for('admin'))

@app.route('/admin/delete_item/<int:item_id>', methods=['POST'])
@login_required
def admin_delete_item(item_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('home'))
    
    item = MenuItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    
    flash('Menu item deleted successfully!')
    return redirect(url_for('admin'))

@app.route('/orders')
@login_required
def orders():
    if current_user.is_admin:
        # Admin sees all orders
        orders = Order.query.order_by(Order.date_ordered.desc()).all()
    else:
        # Users see only their orders
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('orders.html', orders=orders)

@app.route('/update_order_status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('orders'))
    
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    if new_status in ['pending', 'completed', 'cancelled']:
        order.status = new_status
        db.session.commit()
        flash(f'Order #{order_id} status updated to {new_status}', 'success')
    else:
        flash('Invalid status', 'error')
    
    return redirect(url_for('orders'))

@app.route('/place_order', methods=['POST'])
@login_required
def place_order():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('home'))
    
    # Calculate total amount
    total_amount = sum(item.menu_item.price * item.quantity for item in cart_items)
    
    # Create new order
    order = Order(
        user_id=current_user.id,
        total_amount=total_amount,
        status='pending'
    )
    db.session.add(order)
    
    # Create order items
    for cart_item in cart_items:
        order_item = OrderItem(
            order=order,
            menu_item_id=cart_item.menu_item_id,
            quantity=cart_item.quantity
        )
        db.session.add(order_item)
        db.session.delete(cart_item)  # Remove item from cart
    
    try:
        db.session.commit()
        flash('Order placed successfully!', 'success')
        return redirect(url_for('order_receipt', order_id=order.id))
    except Exception as e:
        db.session.rollback()
        flash('Error placing order. Please try again.', 'error')
        logger.error(f"Error placing order: {str(e)}")
        return redirect(url_for('orders'))

@app.route('/order_receipt/<int:order_id>')
@login_required
def order_receipt(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'error')
        return redirect(url_for('home'))

    discount_percentage = 5
    discount = (order.total_amount * discount_percentage) / 100
    final_amount = order.total_amount - discount

    return render_template(
        'order_receipt.html',
        order=order,
        discount=discount,
        final_amount=final_amount,
        discount_percentage=discount_percentage
    )

@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    quantity = int(request.form.get('quantity', 1))
    cart_item = CartItem.query.filter_by(user_id=current_user.id, menu_item_id=item_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, menu_item_id=item_id, quantity=quantity)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Item added to cart!')
    return redirect(url_for('home'))

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, menu_item_id=item_id).first()
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    # Get user's orders
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    
    # Calculate statistics
    total_orders = len(user_orders)
    total_spent = sum(order.total_amount for order in user_orders)
    recent_orders = user_orders[:5]  # Last 5 orders
    
    # Calculate favorite items
    item_counts = {}
    for order in user_orders:
        for item in order.items:
            key = item.menu_item.name
            if key not in item_counts:
                item_counts[key] = {
                    'count': 0,
                    'total': 0,
                    'category': item.menu_item.category
                }
            item_counts[key]['count'] += item.quantity
            item_counts[key]['total'] += item.menu_item.price * item.quantity
    
    # Sort items by count to get favorites
    favorite_items = sorted(
        [{'name': k, **v} for k, v in item_counts.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:5]  # Top 5 items
    
    # Calculate order status counts
    status_counts = {
        'pending': sum(1 for order in user_orders if order.status == 'pending'),
        'completed': sum(1 for order in user_orders if order.status == 'completed'),
        'cancelled': sum(1 for order in user_orders if order.status == 'cancelled')
    }
    
    # Calculate category preferences
    category_totals = {}
    for order in user_orders:
        for item in order.items:
            category = item.menu_item.category
            if category not in category_totals:
                category_totals[category] = 0
            category_totals[category] += item.quantity
    
    return render_template(
        'user_dashboard.html',
        total_orders=total_orders,
        total_spent=total_spent,
        recent_orders=recent_orders,
        favorite_items=favorite_items,
        status_counts=status_counts,
        category_totals=category_totals
    )

@app.template_filter('inr')
def inr_format(value):
    return f"₹{value:.2f}"  # Price is already in INR

def create_tables():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        logger.debug("All database tables created successfully")

def init_db():
    with app.app_context():
        # Create tables first
        create_tables()
        
        # Create admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
        
        # Add sample menu items
        sample_items = [
            MenuItem(
                name='Espresso',
                description='Strong brewed coffee',
                price=180.00,
                category='Coffee'
            ),
            MenuItem(
                name='Cappuccino',
                description='Espresso with steamed milk foam',
                price=220.00,
                category='Coffee'
            ),
            MenuItem(
                name='Samosa',
                description='Crispy pastry with spiced potato filling',
                price=40.00,
                category='Snacks'
            ),
            MenuItem(
                name='Cookies',
                description='Fresh baked cookies',
                price=80.00,
                category='Snacks'
            )
        ]
        
        for item in sample_items:
            existing = MenuItem.query.filter_by(name=item.name).first()
            if not existing:
                db.session.add(item)
        
        try:
            db.session.commit()
            logger.debug("Database initialized with sample data")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing database: {str(e)}")
            raise

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    # Get all users (except admin)
    users = User.query.filter_by(is_admin=False).all()
    user_stats = []
    
    total_revenue = 0
    total_orders = 0
    pending_orders = 0
    
    for user in users:
        # Get user's orders
        orders = Order.query.filter_by(user_id=user.id).all()
        total_spent = sum(order.total_amount for order in orders)
        last_order = Order.query.filter_by(user_id=user.id).order_by(Order.date_ordered.desc()).first()
        
        # Calculate item statistics
        items_dict = {}
        total_items = 0
        
        for order in orders:
            total_orders += 1
            if order.status == 'pending':
                pending_orders += 1
            total_revenue += order.total_amount
            
            for item in order.items:
                total_items += item.quantity
                key = (item.menu_item.name, item.menu_item.category)
                if key not in items_dict:
                    items_dict[key] = {
                        'name': item.menu_item.name,
                        'category': item.menu_item.category,
                        'quantity': 0,
                        'total': 0
                    }
                items_dict[key]['quantity'] += item.quantity
                items_dict[key]['total'] += item.menu_item.price * item.quantity
        
        user_stat = {
            'id': user.id,
            'username': user.username,
            'total_orders': len(orders),
            'total_items': total_items,
            'total_spent': total_spent,
            'last_order_date': last_order.date_ordered if last_order else None,
            'items': list(items_dict.values()),
            'orders': orders
        }
        user_stats.append(user_stat)
    
    total_users = len(users)
    
    return render_template(
        'admin_dashboard.html',
        user_stats=user_stats,
        total_users=total_users,
        total_orders=total_orders,
        pending_orders=pending_orders,
        total_revenue=total_revenue
    )

@app.route('/hours')
def hours():
    logger.debug("Hours route called")
    operating_hours = {
        'Regular Hours': {
            'Monday': {'open': '7:00 AM', 'close': '9:00 PM'},
            'Tuesday': {'open': '7:00 AM', 'close': '9:00 PM'},
            'Wednesday': {'open': '7:00 AM', 'close': '9:00 PM'},
            'Thursday': {'open': '7:00 AM', 'close': '9:00 PM'},
            'Friday': {'open': '7:00 AM', 'close': '9:00 PM'},
            'Saturday': {'open': '8:00 AM', 'close': '10:00 PM'},
            'Sunday': {'open': '8:00 AM', 'close': '8:00 PM'}
        },
        'Holiday Hours': {
            'New Year\'s Day': {'open': '9:00 AM', 'close': '6:00 PM'},
            'Christmas Eve': {'open': '7:00 AM', 'close': '6:00 PM'},
            'Christmas Day': 'Closed',
            'Thanksgiving': 'Closed',
            'New Year\'s Eve': {'open': '7:00 AM', 'close': '6:00 PM'}
        },
        'Special Services': {
            'Happy Hour': 'Monday - Friday, 3:00 PM - 6:00 PM',
            'Breakfast Special': 'Daily, 7:00 AM - 11:00 AM',
            'Student Discount': 'Monday - Thursday, All Day (Valid ID required)'
        }
    }
    
    # Add days list for weekday matching
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    logger.debug("Rendering hours template with operating_hours data")
    return render_template('hours.html', operating_hours=operating_hours, days=days)

@app.context_processor
def utility_processor():
    return {
        'now': datetime.now
    }

if __name__ == '__main__':
    try:
        init_db()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    app.run(debug=True) 