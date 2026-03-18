from flask import render_template, request, redirect, url_for, flash, send_file, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from io import StringIO, BytesIO
from sqlalchemy import or_
import csv
from . import db
from .models import User, Branch, Product, LensStock, Customer, Sale, SaleItem, Payment


LENS_FAMILIES = ['Single Vision', 'Bifocal', 'Progressive']
LENS_MATERIALS = ['White Lens', 'Photo AR', 'Blue Cut Photo AR']
PRODUCT_CATEGORIES = ['Frame', 'Case', 'Lens Cloth', 'Liquid Lens Cleaner', 'Accessory']
FRAME_TYPES = ['Metal', 'Plastic', 'Rimless', 'Designer Frame']


def manager_required():
    return current_user.is_authenticated and current_user.role == 'manager'


def require_manager():
    if not manager_required():
        abort(403)


def naira(value):
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def get_sale_price(item, sale_channel):
    return item.wholesale_price if sale_channel == 'wholesale' else item.retail_price


def seed_missing_stock_columns():
    # Defensive no-op for SQLite/Postgres created from updated models
    pass


def parse_sale_rows(form):
    rows = []
    item_kinds = form.getlist('item_kind[]')
    item_ids = form.getlist('item_id[]')
    qtys = form.getlist('qty[]')
    prices = form.getlist('price[]')
    for item_kind, item_id, qty, price in zip(item_kinds, item_ids, qtys, prices):
        if not item_kind or not item_id:
            continue
        try:
            qty_val = int(qty or 0)
            price_val = float(price or 0)
            item_id_val = int(item_id)
        except ValueError:
            continue
        if qty_val <= 0:
            continue
        rows.append({
            'item_kind': item_kind,
            'item_id': item_id_val,
            'qty': qty_val,
            'price': price_val,
        })
    return rows


def register_routes(app):
    app.jinja_env.filters['naira'] = naira

    @app.errorhandler(403)
    def forbidden(_e):
        flash('You do not have permission to perform that action.', 'danger')
        return redirect(url_for('dashboard'))

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Invalid username or password.', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        branch_id = current_user.branch_id
        today_sales = Sale.query.filter_by(branch_id=branch_id).order_by(Sale.created_at.desc()).limit(10).all()
        total_today = sum(s.total_amount for s in today_sales)
        ctx = {
            'products': Product.query.filter_by(branch_id=branch_id, is_active=True).count(),
            'lenses': LensStock.query.filter_by(branch_id=branch_id, is_active=True).count(),
            'sales': Sale.query.filter_by(branch_id=branch_id).count(),
            'debtors': Sale.query.filter(Sale.branch_id == branch_id, Sale.balance > 0).count(),
            'branches': Branch.query.count(),
            'stock_alerts': Product.query.filter(Product.branch_id == branch_id, Product.stock_qty <= 5).count() + LensStock.query.filter(LensStock.branch_id == branch_id, LensStock.quantity <= 5).count(),
            'sales_value': total_today,
        }
        return render_template('dashboard.html', ctx=ctx, recent_sales=today_sales)

    @app.route('/branches', methods=['GET', 'POST'])
    @login_required
    def branches():
        if request.method == 'POST':
            require_manager()
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip().upper()
            location = request.form.get('location', '').strip()
            if not name or not code:
                flash('Branch name and code are required.', 'danger')
                return redirect(url_for('branches'))
            if Branch.query.filter(or_(Branch.name == name, Branch.code == code)).first():
                flash('Branch name or code already exists.', 'danger')
                return redirect(url_for('branches'))
            db.session.add(Branch(name=name, code=code, location=location))
            db.session.commit()
            flash('Branch added successfully.', 'success')
            return redirect(url_for('branches'))
        return render_template('branches.html', rows=Branch.query.order_by(Branch.name).all())

    @app.route('/staff', methods=['GET', 'POST'])
    @login_required
    def staff():
        if request.method == 'POST':
            require_manager()
            username = request.form.get('username', '').strip()
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return redirect(url_for('staff'))
            user = User(
                full_name=request.form.get('full_name', '').strip(),
                username=username,
                password_hash=generate_password_hash(request.form.get('password', '')),
                role=request.form.get('role', 'staff'),
                branch_id=int(request.form.get('branch_id')),
            )
            db.session.add(user)
            db.session.commit()
            flash('Staff created successfully.', 'success')
            return redirect(url_for('staff'))
        return render_template('staff.html', rows=User.query.order_by(User.full_name).all(), branches=Branch.query.order_by(Branch.name).all())

    @app.route('/products', methods=['GET', 'POST'])
    @login_required
    def products():
        if request.method == 'POST':
            require_manager()
            item = Product(
                branch_id=int(request.form.get('branch_id')),
                category=request.form.get('category'),
                product_type=request.form.get('product_type'),
                name=request.form.get('name'),
                sku=request.form.get('sku'),
                wholesale_price=float(request.form.get('wholesale_price') or 0),
                retail_price=float(request.form.get('retail_price') or 0),
                stock_qty=int(request.form.get('stock_qty') or 0),
            )
            db.session.add(item)
            db.session.commit()
            flash('Product added successfully.', 'success')
            return redirect(url_for('products'))
        q = request.args.get('q', '').strip()
        rows_query = Product.query.filter_by(branch_id=current_user.branch_id, is_active=True)
        if q:
            rows_query = rows_query.filter(or_(Product.name.ilike(f'%{q}%'), Product.category.ilike(f'%{q}%'), Product.product_type.ilike(f'%{q}%')))
        rows = rows_query.order_by(Product.category, Product.name).all()
        return render_template('products.html', rows=rows, branches=Branch.query.order_by(Branch.name).all(), categories=PRODUCT_CATEGORIES, frame_types=FRAME_TYPES, q=q)

    @app.route('/products/<int:product_id>/adjust', methods=['POST'])
    @login_required
    def adjust_product(product_id):
        require_manager()
        product = Product.query.get_or_404(product_id)
        delta = int(request.form.get('delta') or 0)
        product.stock_qty = max(product.stock_qty + delta, 0)
        db.session.commit()
        flash(f'{product.name} stock adjusted successfully.', 'success')
        return redirect(url_for('products'))

    @app.route('/lenses', methods=['GET', 'POST'])
    @login_required
    def lenses():
        if request.method == 'POST':
            require_manager()
            lens = LensStock(
                branch_id=int(request.form.get('branch_id')),
                lens_family=request.form.get('lens_family'),
                lens_material=request.form.get('lens_material'),
                power=request.form.get('power'),
                quantity=int(request.form.get('quantity') or 0),
                wholesale_price=float(request.form.get('wholesale_price') or 0),
                retail_price=float(request.form.get('retail_price') or 0),
            )
            db.session.add(lens)
            db.session.commit()
            flash('Lens power stock added successfully.', 'success')
            return redirect(url_for('lenses'))
        q = request.args.get('q', '').strip()
        rows_query = LensStock.query.filter_by(branch_id=current_user.branch_id, is_active=True)
        if q:
            rows_query = rows_query.filter(or_(LensStock.lens_family.ilike(f'%{q}%'), LensStock.lens_material.ilike(f'%{q}%'), LensStock.power.ilike(f'%{q}%')))
        rows = rows_query.order_by(LensStock.lens_family, LensStock.lens_material, LensStock.power).all()
        return render_template('lenses.html', rows=rows, branches=Branch.query.order_by(Branch.name).all(), families=LENS_FAMILIES, materials=LENS_MATERIALS, q=q)

    @app.route('/lenses/bulk-add', methods=['POST'])
    @login_required
    def lenses_bulk_add():
        require_manager()
        branch_id = int(request.form.get('branch_id'))
        lens_family = request.form.get('lens_family')
        lens_material = request.form.get('lens_material')
        powers_text = request.form.get('powers_text', '')
        quantity = int(request.form.get('quantity') or 0)
        wholesale_price = float(request.form.get('wholesale_price') or 0)
        retail_price = float(request.form.get('retail_price') or 0)
        powers = [p.strip() for p in powers_text.replace('\n', ',').split(',') if p.strip()]
        created = 0
        for power in powers:
            existing = LensStock.query.filter_by(branch_id=branch_id, lens_family=lens_family, lens_material=lens_material, power=power).first()
            if existing:
                existing.quantity += quantity
                existing.wholesale_price = wholesale_price or existing.wholesale_price
                existing.retail_price = retail_price or existing.retail_price
            else:
                db.session.add(LensStock(branch_id=branch_id, lens_family=lens_family, lens_material=lens_material, power=power, quantity=quantity, wholesale_price=wholesale_price, retail_price=retail_price))
            created += 1
        db.session.commit()
        flash(f'{created} lens power rows processed successfully.', 'success')
        return redirect(url_for('lenses'))

    @app.route('/lenses/<int:lens_id>/adjust', methods=['POST'])
    @login_required
    def adjust_lens(lens_id):
        require_manager()
        lens = LensStock.query.get_or_404(lens_id)
        delta = int(request.form.get('delta') or 0)
        lens.quantity = max(lens.quantity + delta, 0)
        db.session.commit()
        flash('Lens stock adjusted successfully.', 'success')
        return redirect(url_for('lenses'))

    @app.route('/customers', methods=['GET', 'POST'])
    @login_required
    def customers():
        if request.method == 'POST':
            customer = Customer(
                name=request.form.get('name'),
                phone=request.form.get('phone'),
                customer_type=request.form.get('customer_type'),
                address=request.form.get('address'),
            )
            db.session.add(customer)
            db.session.commit()
            flash('Customer saved successfully.', 'success')
            return redirect(url_for('customers'))
        rows = Customer.query.order_by(Customer.name).all()
        return render_template('customers.html', rows=rows)

    @app.route('/sales', methods=['GET', 'POST'])
    @login_required
    def sales():
        branch_id = current_user.branch_id
        if request.method == 'POST':
            customer_id = request.form.get('customer_id') or None
            sale_channel = request.form.get('sale_channel', 'retail')
            rows = parse_sale_rows(request.form)
            if not rows:
                flash('Add at least one item to save a sale.', 'danger')
                return redirect(url_for('sales'))

            sale = Sale(
                branch_id=branch_id,
                customer_id=int(customer_id) if customer_id else None,
                staff_id=current_user.id,
                sale_channel=sale_channel,
                discount=float(request.form.get('discount') or 0),
                amount_paid=float(request.form.get('amount_paid') or 0),
                notes=request.form.get('notes'),
            )
            db.session.add(sale)
            db.session.flush()

            subtotal = 0
            for row in rows:
                if row['item_kind'] == 'product':
                    product = Product.query.get(row['item_id'])
                    if not product or product.branch_id != branch_id:
                        db.session.rollback()
                        flash('A selected product was not found in this branch.', 'danger')
                        return redirect(url_for('sales'))
                    if product.stock_qty < row['qty']:
                        db.session.rollback()
                        flash(f'Not enough stock for {product.name}.', 'danger')
                        return redirect(url_for('sales'))
                    product.stock_qty -= row['qty']
                    name = product.name
                    details = f'{product.category} / {product.product_type}'
                else:
                    lens = LensStock.query.get(row['item_id'])
                    if not lens or lens.branch_id != branch_id:
                        db.session.rollback()
                        flash('A selected lens was not found in this branch.', 'danger')
                        return redirect(url_for('sales'))
                    if lens.quantity < row['qty']:
                        db.session.rollback()
                        flash(f'Not enough lens quantity for {lens.lens_family} {lens.power}.', 'danger')
                        return redirect(url_for('sales'))
                    lens.quantity -= row['qty']
                    name = f'{lens.lens_family} - {lens.lens_material}'
                    details = f'Power {lens.power}'

                line_total = row['qty'] * row['price']
                subtotal += line_total
                db.session.add(SaleItem(
                    sale_id=sale.id,
                    item_kind=row['item_kind'],
                    item_name=name,
                    item_details=details,
                    quantity=row['qty'],
                    unit_price=row['price'],
                    line_total=line_total,
                ))

            sale.subtotal = subtotal
            sale.total_amount = max(subtotal - sale.discount, 0)
            sale.balance = max(sale.total_amount - sale.amount_paid, 0)
            if sale.amount_paid > 0:
                db.session.add(Payment(sale_id=sale.id, amount=sale.amount_paid, payment_note='Initial payment', received_by_id=current_user.id))
            db.session.commit()
            flash('Sale recorded successfully.', 'success')
            return redirect(url_for('sale_detail', sale_id=sale.id))

        products = Product.query.filter_by(branch_id=branch_id, is_active=True).order_by(Product.name).all()
        lenses = LensStock.query.filter_by(branch_id=branch_id, is_active=True).order_by(LensStock.lens_family, LensStock.power).all()
        customers = Customer.query.order_by(Customer.name).all()
        product_catalog = [
            {
                'id': p.id,
                'kind': 'product',
                'label': f'{p.name} | {p.category} | {p.product_type} | Stock {p.stock_qty}',
                'retail_price': p.retail_price,
                'wholesale_price': p.wholesale_price,
            } for p in products
        ]
        lens_catalog = [
            {
                'id': l.id,
                'kind': 'lens',
                'label': f'{l.lens_family} | {l.lens_material} | {l.power} | Qty {l.quantity}',
                'retail_price': l.retail_price,
                'wholesale_price': l.wholesale_price,
            } for l in lenses
        ]
        return render_template('sales.html', products=products, lenses=lenses, customers=customers, product_catalog=product_catalog, lens_catalog=lens_catalog)

    @app.route('/sales-history')
    @login_required
    def sales_history():
        rows = Sale.query.filter_by(branch_id=current_user.branch_id).order_by(Sale.created_at.desc()).all()
        return render_template('sales_history.html', rows=rows)

    @app.route('/sales/<int:sale_id>')
    @login_required
    def sale_detail(sale_id):
        sale = Sale.query.get_or_404(sale_id)
        if sale.branch_id != current_user.branch_id and not manager_required():
            abort(403)
        return render_template('sale_detail.html', sale=sale)

    @app.route('/debtors', methods=['GET'])
    @login_required
    def debtors():
        rows = Sale.query.filter(Sale.branch_id == current_user.branch_id, Sale.balance > 0).order_by(Sale.created_at.desc()).all()
        return render_template('debtors.html', rows=rows)

    @app.route('/sales/<int:sale_id>/payment', methods=['POST'])
    @login_required
    def add_payment(sale_id):
        sale = Sale.query.get_or_404(sale_id)
        if sale.branch_id != current_user.branch_id:
            abort(403)
        amount = float(request.form.get('amount') or 0)
        if amount <= 0:
            flash('Payment amount must be greater than zero.', 'danger')
            return redirect(url_for('debtors'))
        sale.amount_paid += amount
        sale.balance = max(sale.total_amount - sale.amount_paid, 0)
        db.session.add(Payment(sale_id=sale.id, amount=amount, payment_note=request.form.get('payment_note'), received_by_id=current_user.id))
        db.session.commit()
        flash('Debtor payment recorded successfully.', 'success')
        return redirect(url_for('sale_detail', sale_id=sale.id))

    @app.route('/export-data')
    @login_required
    def export_data():
        require_manager()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['SALE ID', 'DATE', 'BRANCH', 'CUSTOMER', 'CHANNEL', 'STAFF', 'SUBTOTAL', 'DISCOUNT', 'TOTAL', 'PAID', 'BALANCE'])
        for s in Sale.query.order_by(Sale.created_at.desc()).all():
            writer.writerow([
                s.id,
                s.created_at.strftime('%Y-%m-%d %H:%M'),
                s.branch.name,
                s.customer.name if s.customer else 'Walk-in Customer',
                s.sale_channel,
                s.staff.full_name,
                s.subtotal,
                s.discount,
                s.total_amount,
                s.amount_paid,
                s.balance,
            ])
        mem = BytesIO(output.getvalue().encode('utf-8'))
        mem.seek(0)
        return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='hol_sales_export.csv')
