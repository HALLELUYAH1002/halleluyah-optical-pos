from flask_login import UserMixin
from datetime import datetime
from . import db


class Branch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    code = db.Column(db.String(30), nullable=False, unique=True)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff')
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='users')


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    product_type = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    sku = db.Column(db.String(80), nullable=True)
    wholesale_price = db.Column(db.Float, default=0)
    retail_price = db.Column(db.Float, default=0)
    stock_qty = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='products')


class LensStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    lens_family = db.Column(db.String(50), nullable=False)
    lens_material = db.Column(db.String(80), nullable=False)
    power = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    wholesale_price = db.Column(db.Float, default=0)
    retail_price = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='lenses')


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50))
    customer_type = db.Column(db.String(30), nullable=False, default='End User')
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branch.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sale_channel = db.Column(db.String(20), nullable=False, default='retail')
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    amount_paid = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    branch = db.relationship('Branch', backref='sales')
    customer = db.relationship('Customer', backref='sales')
    staff = db.relationship('User', backref='sales')


class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    item_kind = db.Column(db.String(20), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    item_details = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, default=0)
    line_total = db.Column(db.Float, default=0)

    sale = db.relationship('Sale', backref='items')


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0)
    payment_note = db.Column(db.String(255))
    received_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sale = db.relationship('Sale', backref='payments')
    received_by = db.relationship('User', backref='received_payments')
