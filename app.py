from datetime import datetime, timedelta
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, session
from models import (
    db, Category, MenuItem, Table, Staff,
    Order, OrderItem, Payment, Voucher,
    Ingredient, MenuIngredient,
    Member, PointTransaction, PointSetting,
    User, ShiftSchedule, SalaryRecord, OrderHistory,
    Area
)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafe.db'
app.config['SECRET_KEY'] = 'cafe-antigravity-secret-key-2024'

db.init_app(app)

# Helper function to format VND currency
def format_vnd(value):
    try:
        return f"{int(value):,} VND".replace(",", ".")
    except Exception:
        return "0 VND"

# ==============================================================================
# AUTHENTICATION & ACCESS CONTROL
# ==============================================================================

# Auth helper
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

def require_login():
    if not get_current_user():
        return redirect('/login')
    return None

def require_role(*roles):
    u = get_current_user()
    if not u or u.role not in roles:
        return jsonify({'success': False, 'message': 'Không có quyền thực hiện thao tác này!'}), 403
    return None

@app.route('/login', methods=['GET'])
def login_page():
    if get_current_user():
        return redirect('/')
    return render_template('login.html')

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    user = User.query.filter_by(username=username, active=True).first()
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'message': 'Tên đăng nhập hoặc mật khẩu không đúng!'})
    session['user_id'] = user.id
    session['user_role'] = user.role
    user.last_login = datetime.now()
    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()})

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/auth/me', methods=['GET'])
def api_me():
    u = get_current_user()
    if not u:
        return jsonify({'logged_in': False})
    return jsonify({'logged_in': True, 'user': u.to_dict()})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    # Only owner can create accounts
    # But for initial setup, allow if no users exist
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'waiter').strip()

    if not username or not password or not full_name:
        return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ thông tin!'})

    # Check if any users exist - if yes, only owner can register
    existing_users = User.query.count()
    if existing_users > 0:
        current_user = get_current_user()
        if not current_user or current_user.role != 'owner':
            return jsonify({'success': False, 'message': 'Chỉ chủ quán mới có thể tạo tài khoản mới!'})

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại!'})

    allowed_roles = ['owner', 'manager', 'cashier', 'barista', 'waiter']
    if role not in allowed_roles:
        role = 'waiter'

    user = User(username=username, full_name=full_name, role=role, active=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Tạo tài khoản thành công! Vai trò: {role}', 'user': user.to_dict()})

@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    u = get_current_user()
    if not u:
        return jsonify({'success': False, 'message': 'Chưa đăng nhập!'})
    data = request.json or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not u.check_password(old_pw):
        return jsonify({'success': False, 'message': 'Mật khẩu cũ không đúng!'})
    u.set_password(new_pw)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Đổi mật khẩu thành công!'})

@app.route('/api/users', methods=['GET'])
def get_users():
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403
    users = User.query.all()
    return jsonify([usr.to_dict() for usr in users])

@app.route('/api/users/<id>', methods=['PUT'])
def update_user(id):
    current = get_current_user()
    if not current or current.role != 'owner':
        return jsonify({'success': False, 'message': 'Chỉ chủ quán mới được thay đổi tài khoản!'}), 403
    user = User.query.get(id)
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy tài khoản!'})
    data = request.json or {}
    if 'full_name' in data: user.full_name = data['full_name']
    if 'role' in data: user.role = data['role']
    if 'active' in data: user.active = bool(data['active'])
    if 'password' in data and data['password']: user.set_password(data['password'])
    db.session.commit()
    return jsonify({'success': True, 'message': 'Cập nhật tài khoản thành công!', 'user': user.to_dict()})

@app.route('/api/users/<id>', methods=['DELETE'])
def delete_user(id):
    current = get_current_user()
    if not current or current.role != 'owner':
        return jsonify({'success': False, 'message': 'Chỉ chủ quán mới được xóa tài khoản!'}), 403
    user = User.query.get(id)
    if not user:
        return jsonify({'success': False, 'message': 'Không tìm thấy!'})
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Đã xóa tài khoản!'})

# ==============================================================================
# SCHEDULE, SALARY, ORDER HISTORY & BARISTA ROUTES
# ==============================================================================

# ── SCHEDULE ──
@app.route('/schedule')
def schedule_page():
    return render_template('schedule.html', active_page='schedule')

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    month = request.args.get('month')  # YYYY-MM
    staff_id = request.args.get('staff_id')
    u = get_current_user()
    q = ShiftSchedule.query
    if month:
        q = q.filter(ShiftSchedule.date.like(f'{month}%'))
    if staff_id:
        q = q.filter_by(staff_id=int(staff_id))
    elif u and u.role in ['waiter', 'cashier', 'barista'] and u.staff_id:
        q = q.filter_by(staff_id=u.staff_id)
    schedules = q.all()
    return jsonify([s.to_dict() for s in schedules])

@app.route('/api/schedule', methods=['POST'])
def add_schedule():
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Chỉ quản lý mới được phân ca!'}), 403
    data = request.json or {}
    s = ShiftSchedule(
        staff_id=int(data['staff_id']), date=data['date'],
        shift=data.get('shift', 'morning'), note=data.get('note', ''),
        created_by=u.id if u else None
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({'success': True, 'schedule': s.to_dict()})

@app.route('/api/schedule/<id>', methods=['PUT'])
def update_schedule(id):
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403
    s = ShiftSchedule.query.get(id)
    if not s:
        return jsonify({'success': False, 'message': 'Không tìm thấy!'}), 404
    data = request.json or {}
    if 'shift' in data: s.shift = data['shift']
    if 'note' in data: s.note = data['note']
    db.session.commit()
    return jsonify({'success': True, 'schedule': s.to_dict()})

@app.route('/api/schedule/<id>', methods=['DELETE'])
def delete_schedule(id):
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403
    s = ShiftSchedule.query.get(id)
    if s:
        db.session.delete(s)
        db.session.commit()
    return jsonify({'success': True})

# ── SALARY ──
@app.route('/salary')
def salary_page():
    return render_template('salary.html', active_page='salary')

@app.route('/api/salary', methods=['GET'])
def get_salary():
    month = request.args.get('month')
    records = SalaryRecord.query
    if month:
        records = records.filter_by(month=month)
    return jsonify([r.to_dict() for r in records.all()])

@app.route('/api/salary', methods=['POST'])
def create_salary():
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403
    data = request.json or {}
    staff_id = int(data.get('staff_id'))
    month = data.get('month')
    # count working days from schedule
    days_worked = ShiftSchedule.query.filter(
        ShiftSchedule.staff_id == staff_id,
        ShiftSchedule.date.like(f'{month}%'),
        ShiftSchedule.shift != 'off'
    ).count()
    base = float(data.get('base_salary', 0))
    bonus = float(data.get('bonus', 0))
    deduction = float(data.get('deduction', 0))
    r = SalaryRecord(
        staff_id=staff_id, month=month,
        base_salary=base, bonus=bonus, deduction=deduction,
        total=base + bonus - deduction,
        days_worked=days_worked,
        note=data.get('note', ''), paid=bool(data.get('paid', False))
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'success': True, 'record': r.to_dict()})

@app.route('/api/salary/<id>', methods=['PUT'])
def update_salary(id):
    u = get_current_user()
    if not u or u.role not in ['owner', 'manager']:
        return jsonify({'success': False, 'message': 'Không có quyền!'}), 403
    r = SalaryRecord.query.get(id)
    if not r: return jsonify({'success': False, 'message': 'Không tìm thấy!'})
    data = request.json or {}
    if 'base_salary' in data: r.base_salary = float(data['base_salary'])
    if 'bonus' in data: r.bonus = float(data['bonus'])
    if 'deduction' in data: r.deduction = float(data['deduction'])
    if 'note' in data: r.note = data['note']
    if 'paid' in data: r.paid = bool(data['paid'])
    r.total = r.base_salary + r.bonus - r.deduction
    db.session.commit()
    return jsonify({'success': True, 'record': r.to_dict()})

# ── ORDER HISTORY ──
@app.route('/api/orders/<id>/history', methods=['GET'])
def get_order_history(id):
    history = OrderHistory.query.filter_by(order_id=id).order_by(OrderHistory.id.desc()).all()
    return jsonify([h.to_dict() for h in history])

# ── BARISTA ──
@app.route('/barista')
def barista_page():
    return render_template('barista.html', active_page='barista')

@app.route('/api/barista/pending', methods=['GET'])
def get_barista_pending():
    """Get all pending order items for barista view (including pending orders and items not yet done)"""
    # Lấy các món thuộc đơn pending hoặc đơn chưa làm xong món
    order_items = OrderItem.query.join(Order).filter(
        Order.status.in_(['pending', 'processing']),
        (OrderItem.status == 'pending') | (OrderItem.status == None)
    ).all()
    
    result = []
    for item in order_items:
        order = item.order
        result.append({
            'order_id': order.id,
            'order_item_id': item.id,
            'table': order.table.number if order.table else 'Mang về',
            'item_name': item.menu_item.name if item.menu_item else 'Món đã xóa',
            'category': item.menu_item.category if item.menu_item else '',
            'quantity': item.quantity,
            'notes': item.notes or '',
            'created_at': order.created_at.strftime('%H:%M') if order.created_at else ''
        })
    return jsonify(result)

@app.route('/api/barista/complete-items', methods=['POST'])
def barista_complete_items():
    try:
        u = get_current_user()
        data = request.json or {}
        raw_item_ids = data.get('item_ids', [])
        raw_order_ids = data.get('order_ids', [])
        item_ids = []
        for x in raw_item_ids:
            try:
                item_ids.append(int(float(x)))
            except (ValueError, TypeError):
                pass
        order_ids = []
        for x in raw_order_ids:
            try:
                order_ids.append(int(float(x)))
            except (ValueError, TypeError):
                pass
        note = data.get('note', 'Pha chế hoàn tất')
        affected_orders = set(order_ids)
        
        if item_ids:
            items = OrderItem.query.filter(OrderItem.id.in_(item_ids)).all()
            for it in items:
                it.status = 'done'
                if it.order_id:
                    affected_orders.add(it.order_id)
                db.session.add(it)
                
        if order_ids:
            items_in_orders = OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()
            for it in items_in_orders:
                it.status = 'done'
                db.session.add(it)
                
        for oid in affected_orders:
            if not oid:
                continue
            try:
                h = OrderHistory(
                    order_id=oid,
                    action='item_changed',
                    description=f'Pha chế: {note}',
                    performed_by=u.id if u else None,
                    performed_by_name=u.full_name if u else 'Pha chế',
                    created_at=datetime.now()
                )
                db.session.add(h)
            except Exception:
                pass
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã cập nhật trạng thái pha chế!'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500



# ==============================================================================
# PAGE ROUTES (HTML Templates)
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html', active_page='dashboard')

@app.route('/menu')
def menu_page():
    return render_template('menu.html', active_page='menu')

@app.route('/orders')
def orders_page():
    return render_template('orders.html', active_page='orders')

@app.route('/tables')
def tables_page():
    return render_template('tables.html', active_page='tables')

@app.route('/staff')
def staff_page():
    return render_template('staff.html', active_page='staff')

@app.route('/vouchers')
def vouchers_page():
    return render_template('vouchers.html', active_page='vouchers')

@app.route('/ingredients')
def ingredients_page():
    return render_template('ingredients.html', active_page='ingredients')

@app.route('/members')
def members_page():
    return render_template('members.html', active_page='members')

# ==============================================================================
# DASHBOARD & REVENUE API
# ==============================================================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # All orders
        all_orders = Order.query.all()
        today_orders = [o for o in all_orders if o.created_at and o.created_at.strftime('%Y-%m-%d') == today_str and o.status != 'cancelled']
        
        today_revenue = sum(o.total for o in today_orders if o.status == 'completed')
        
        tables = Table.query.all()
        active_tables = sum(1 for t in tables if t.status == 'occupied')
        total_tables = len(tables)
        
        ingredients = Ingredient.query.all()
        low_stock_count = sum(1 for ing in ingredients if ing.quantity <= ing.min_quantity)
        
        return jsonify({
            'success': True,
            'today_revenue': float(today_revenue),
            'today_orders': len(today_orders),
            'active_tables': active_tables,
            'total_tables': total_tables,
            'low_stock_count': low_stock_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/revenue', methods=['GET'])
def get_revenue():
    try:
        period = request.args.get('period', '7days')  # 7days, 30days, month, year, custom
        date_from = request.args.get('date_from')     # YYYY-MM-DD
        date_to = request.args.get('date_to')         # YYYY-MM-DD
        month = request.args.get('month')             # YYYY-MM
        year = request.args.get('year')               # YYYY
        now = datetime.now()

        all_orders = Order.query.filter_by(status='completed').all()

        # --- Determine filtered date range ---
        if period == 'custom' and date_from and date_to:
            from_dt = datetime.strptime(date_from, '%Y-%m-%d')
            to_dt = datetime.strptime(date_to, '%Y-%m-%d')
            filtered = [o for o in all_orders if o.created_at and from_dt <= o.created_at <= to_dt.replace(hour=23, minute=59, second=59)]
            # Build daily data for custom range
            delta = (to_dt - from_dt).days + 1
            daily_data = []
            for i in range(min(delta, 60)):
                day = from_dt + timedelta(days=i)
                day_str = day.strftime('%Y-%m-%d')
                day_label = day.strftime('%d/%m')
                day_orders = [o for o in filtered if o.created_at and o.created_at.strftime('%Y-%m-%d') == day_str]
                daily_data.append({'date': day_str, 'label': day_label, 'revenue': float(sum(o.total for o in day_orders)), 'orders_count': len(day_orders)})

        elif period == 'month' and month:
            # e.g. month=2024-11 -> all days in that month
            year_m, month_m = map(int, month.split('-'))
            import calendar
            days_in_month = calendar.monthrange(year_m, month_m)[1]
            filtered = [o for o in all_orders if o.created_at and o.created_at.year == year_m and o.created_at.month == month_m]
            daily_data = []
            for d in range(1, days_in_month + 1):
                day = datetime(year_m, month_m, d)
                day_str = day.strftime('%Y-%m-%d')
                day_label = f"{d}/{month_m}"
                day_orders = [o for o in filtered if o.created_at and o.created_at.strftime('%Y-%m-%d') == day_str]
                daily_data.append({'date': day_str, 'label': day_label, 'revenue': float(sum(o.total for o in day_orders)), 'orders_count': len(day_orders)})

        elif period == 'year' and year:
            year_int = int(year)
            filtered = [o for o in all_orders if o.created_at and o.created_at.year == year_int]
            month_names = ['T1','T2','T3','T4','T5','T6','T7','T8','T9','T10','T11','T12']
            daily_data = []
            for m in range(1, 13):
                m_orders = [o for o in filtered if o.created_at and o.created_at.month == m]
                daily_data.append({'date': f"{year_int}-{m:02d}", 'label': month_names[m-1], 'revenue': float(sum(o.total for o in m_orders)), 'orders_count': len(m_orders)})

        elif period == '30days':
            filtered = [o for o in all_orders if o.created_at and (now - o.created_at).days <= 30]
            daily_data = []
            for i in range(29, -1, -1):
                day = now - timedelta(days=i)
                day_str = day.strftime('%Y-%m-%d')
                day_label = day.strftime('%d/%m')
                day_orders = [o for o in filtered if o.created_at and o.created_at.strftime('%Y-%m-%d') == day_str]
                daily_data.append({'date': day_str, 'label': day_label, 'revenue': float(sum(o.total for o in day_orders)), 'orders_count': len(day_orders)})

        else:  # default: 7days
            weekday_map = {0: 'T2', 1: 'T3', 2: 'T4', 3: 'T5', 4: 'T6', 5: 'T7', 6: 'CN'}
            daily_data = []
            for i in range(6, -1, -1):
                day = now - timedelta(days=i)
                day_str = day.strftime('%Y-%m-%d')
                day_label = f"{weekday_map[day.weekday()]} ({day.strftime('%d/%m')})"
                day_orders = [o for o in all_orders if o.created_at and o.created_at.strftime('%Y-%m-%d') == day_str]
                daily_data.append({'date': day_str, 'label': day_label, 'revenue': float(sum(o.total for o in day_orders)), 'orders_count': len(day_orders)})
            filtered = all_orders

        # Summary stats for the filtered period
        period_revenue = sum(d['revenue'] for d in daily_data)
        period_orders = sum(d['orders_count'] for d in daily_data)

        # 2. Top 5 selling items (all time for reference)
        order_items = OrderItem.query.all()
        item_sales = {}
        for oi in order_items:
            order = Order.query.get(oi.order_id)
            if order and order.status == 'completed':
                m_id = oi.menu_item_id
                if m_id not in item_sales:
                    m_item = MenuItem.query.get(m_id)
                    item_sales[m_id] = {'name': m_item.name if m_item else 'Món khác', 'quantity': 0, 'revenue': 0.0}
                item_sales[m_id]['quantity'] += oi.quantity
                item_sales[m_id]['revenue'] += (oi.price * oi.quantity)
        top_items = sorted(item_sales.values(), key=lambda x: x['quantity'], reverse=True)[:5]

        # 3. Revenue by category (all time)
        category_revenue = {}
        for oi in order_items:
            order = Order.query.get(oi.order_id)
            if order and order.status == 'completed':
                m_item = MenuItem.query.get(oi.menu_item_id)
                cat = m_item.category if m_item else 'Khác'
                category_revenue[cat] = category_revenue.get(cat, 0.0) + (oi.price * oi.quantity)

        # 4. Recent orders (last 8)
        all_orders_all = Order.query.all()
        completed_and_active = sorted(all_orders_all, key=lambda x: x.id, reverse=True)[:8]
        recent_orders = [o.to_dict() for o in completed_and_active]

        return jsonify({
            'success': True,
            'daily_revenue': daily_data,
            'top_items': top_items,
            'category_revenue': category_revenue,
            'recent_orders': recent_orders,
            'period_revenue': float(period_revenue),
            'period_orders': int(period_orders)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# MENU MANAGEMENT API
# ==============================================================================

@app.route('/api/menu', methods=['GET'])
def get_menu():
    try:
        category = request.args.get('category')
        available_only = request.args.get('available')
        search = request.args.get('search', '').lower()

        items = MenuItem.query.all()
        if category and category != 'all':
            items = [item for item in items if item.category == category]
        if available_only is not None and available_only != '':
            is_avail = available_only.lower() in ['true', '1']
            items = [item for item in items if item.available == is_avail]
        if search:
            items = [item for item in items if search in item.name.lower() or search in (item.description or '').lower()]

        return jsonify([item.to_dict() for item in items])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/menu', methods=['POST'])
def add_menu_item():
    try:
        data = request.json or request.form
        if not data.get('name') or not data.get('category') or data.get('price') is None:
            return jsonify({'success': False, 'message': 'Vui lòng điền đầy đủ Tên, Danh mục và Giá món!'}), 400

        item = MenuItem(
            name=data.get('name').strip(),
            category=data.get('category').strip(),
            price=float(data.get('price')),
            description=data.get('description', '').strip(),
            available=bool(data.get('available', True)),
            image_url=data.get('image_url', '').strip() or 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=500&auto=format&fit=crop',
            created_at=datetime.now()
        )
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Thêm món thành công!', 'item': item.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/menu/<id>', methods=['PUT'])
def edit_menu_item(id):
    try:
        item = MenuItem.query.get(id)
        if not item:
            return jsonify({'success': False, 'message': 'Không tìm thấy món ăn!'}), 404

        data = request.json or request.form
        current_user = get_current_user()
        if 'price' in data and current_user and current_user.role not in ['owner', 'manager']:
            return jsonify({'success': False, 'message': 'Nhân viên không được thay đổi giá món!'}), 403

        if 'name' in data: item.name = data['name'].strip()
        if 'category' in data: item.category = data['category'].strip()
        if 'price' in data: item.price = float(data['price'])
        if 'description' in data: item.description = data['description'].strip()
        if 'available' in data: item.available = bool(data['available'])
        if 'image_url' in data: item.image_url = data['image_url'].strip()

        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật món thành công!', 'item': item.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/menu/<id>', methods=['DELETE'])
def delete_menu_item(id):
    try:
        item = MenuItem.query.get(id)
        if not item:
            return jsonify({'success': False, 'message': 'Không tìm thấy món ăn!'}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Xóa món thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
def get_categories():
    try:
        cats = Category.query.all()
        return jsonify([c.to_dict() for c in cats])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def add_category():
    try:
        data = request.json or request.form
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Tên danh mục không được để trống!'}), 400

        existing = Category.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': 'Danh mục này đã tồn tại!'}), 400

        cat = Category(name=name, description=data.get('description', '').strip())
        db.session.add(cat)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Thêm danh mục thành công!', 'category': cat.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# AREA & TABLE MANAGEMENT API
# ==============================================================================

@app.route('/api/areas', methods=['GET'])
def get_areas():
    try:
        areas = Area.query.order_by(Area.id.asc()).all()
        results = []
        for a in areas:
            a_dict = a.to_dict()
            results.append(a_dict)
        return jsonify(results)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/areas', methods=['POST'])
def add_area():
    try:
        data = request.json or request.form
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Tên khu vực không được để trống!'}), 400

        existing = Area.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': f'Khu vực "{name}" đã tồn tại!'}), 400

        area = Area(name=name, description=data.get('description', '').strip())
        db.session.add(area)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Tạo khu vực "{name}" thành công!', 'area': area.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/areas/<id>', methods=['PUT'])
def update_area(id):
    try:
        area = Area.query.get(id)
        if not area:
            return jsonify({'success': False, 'message': 'Không tìm thấy khu vực!'}), 404
        data = request.json or request.form
        name = data.get('name', '').strip()
        if name:
            existing = Area.query.filter(Area.name == name, Area.id != area.id).first()
            if existing:
                return jsonify({'success': False, 'message': f'Tên khu vực "{name}" đã tồn tại!'}), 400
            area.name = name
            for t in area.tables:
                t.area_name = name
        if 'description' in data:
            area.description = data['description'].strip()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật khu vực thành công!', 'area': area.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/areas/<id>', methods=['DELETE'])
def delete_area(id):
    try:
        area = Area.query.get(id)
        if not area:
            return jsonify({'success': False, 'message': 'Không tìm thấy khu vực!'}), 404
        occupied = [t for t in area.tables if t.status == 'occupied']
        if occupied:
            return jsonify({'success': False, 'message': 'Không thể xóa khu vực đang có bàn có khách!'}), 400
        db.session.delete(area)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Xóa khu vực thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tables', methods=['GET'])
def get_tables():
    try:
        tables = Table.query.all()
        results = []
        for t in tables:
            t_data = t.to_dict()
            # If table is occupied, attach current active order info
            if t.status == 'occupied':
                active_order = Order.query.filter_by(table_id=t.id, status='pending').first()
                if active_order:
                    t_data['current_order'] = {
                        'id': active_order.id,
                        'total': active_order.total,
                        'created_at': active_order.created_at.strftime('%H:%M') if active_order.created_at else '',
                        'items_count': len(active_order.items) if active_order.items else 0
                    }
            results.append(t_data)
        return jsonify(results)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tables', methods=['POST'])
def add_table():
    try:
        data = request.json or request.form
        number = data.get('number', '').strip()
        if not number:
            return jsonify({'success': False, 'message': 'Tên/Số bàn không được để trống!'}), 400

        existing = Table.query.filter_by(number=number).first()
        if existing:
            return jsonify({'success': False, 'message': f'Bàn "{number}" đã tồn tại!'}), 400

        area_id = data.get('area_id')
        area_name = data.get('area_name', '').strip()
        floor = int(data.get('floor', 1))

        if area_id:
            area = Area.query.get(int(area_id))
            if area:
                area_name = area.name
                floor = area.id
        elif not area_name:
            first_area = Area.query.first()
            if first_area:
                area_id = first_area.id
                area_name = first_area.name
                floor = first_area.id

        table = Table(
            number=number,
            capacity=int(data.get('capacity', 4)),
            status=data.get('status', 'empty'),
            floor=floor,
            area_id=int(area_id) if area_id else None,
            area_name=area_name if area_name else (f'Tầng {floor}' if floor else 'Khu vực chính')
        )
        db.session.add(table)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Tạo bàn "{number}" thành công!', 'table': table.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tables/<id>', methods=['PUT'])
def update_table(id):
    try:
        table = Table.query.get(id)
        if not table:
            return jsonify({'success': False, 'message': 'Không tìm thấy bàn!'}), 404

        data = request.json or request.form
        if 'number' in data: table.number = data['number'].strip()
        if 'capacity' in data: table.capacity = int(data['capacity'])
        if 'status' in data: table.status = data['status'].strip()
        if 'floor' in data: table.floor = int(data['floor'])
        if 'area_id' in data and data['area_id']:
            area = Area.query.get(int(data['area_id']))
            if area:
                table.area_id = area.id
                table.area_name = area.name
                table.floor = area.id
        elif 'area_name' in data:
            table.area_name = data['area_name'].strip()

        db.session.add(table)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật bàn thành công!', 'table': table.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tables/<id>', methods=['DELETE'])
def delete_table(id):
    try:
        table = Table.query.get(id)
        if not table:
            return jsonify({'success': False, 'message': 'Không tìm thấy bàn!'}), 404

        if table.status == 'occupied':
            return jsonify({'success': False, 'message': 'Không thể xóa bàn đang có khách ngồi!'}), 400

        db.session.delete(table)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Xóa bàn thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# ORDERS / POS API
# ==============================================================================

@app.route('/api/orders', methods=['GET'])
def get_orders():
    try:
        status = request.args.get('status')
        table_id = request.args.get('table_id')
        orders = Order.query.all()
        if status:
            orders = [o for o in orders if o.status == status]
        if table_id:
            orders = [o for o in orders if str(o.table_id) == str(table_id)]

        orders = sorted(orders, key=lambda x: x.id, reverse=True)
        return jsonify([o.to_dict() for o in orders])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.json or {}
        items_data = data.get('items', [])
        if not items_data:
            return jsonify({'success': False, 'message': 'Giỏ hàng đang trống! Vui lòng chọn món.'}), 400

        table_id = data.get('table_id')
        staff_id = data.get('staff_id') or 1
        notes = data.get('notes', '')

        # Calculate total
        total = 0.0
        for item in items_data:
            qty = int(item.get('quantity', 1))
            price = float(item.get('price', 0))
            total += qty * price

        order = Order(
            table_id=table_id,
            staff_id=staff_id,
            status='pending',
            total=total,
            created_at=datetime.now(),
            notes=notes
        )
        db.session.add(order)
        db.session.commit()

        # Add items
        for item in items_data:
            oi = OrderItem(
                order_id=order.id,
                menu_item_id=item['menu_item_id'],
                quantity=int(item.get('quantity', 1)),
                price=float(item.get('price', 0)),
                notes=item.get('notes', '')
            )
            db.session.add(oi)

        # Update table status to occupied if table_id specified
        if table_id:
            t = Table.query.get(table_id)
            if t:
                t.status = 'occupied'
                db.session.add(t)

        db.session.commit()

        # Log order creation history
        u = get_current_user()
        h = OrderHistory(
            order_id=order.id,
            action='created',
            description=f'Tạo đơn hàng #{order.id} cho {order.table.number if order.table else "Mang về"}',
            performed_by=u.id if u else None,
            performed_by_name=u.full_name if u else 'Nhân viên',
            created_at=datetime.now()
        )
        db.session.add(h)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Tạo đơn hàng thành công!', 'order': order.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<id>', methods=['PUT'])
def update_order(id):
    try:
        order = Order.query.get(id)
        if not order:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng!'}), 404

        data = request.json or {}
        if 'notes' in data:
            order.notes = data['notes']
        if 'status' in data:
            order.status = data['status']
            if order.status == 'completed' and order.table_id:
                t = Table.query.get(order.table_id)
                if t:
                    t.status = 'empty'
                    db.session.add(t)

        db.session.add(order)
        db.session.commit()

        # Log order update history
        u = get_current_user()
        desc = 'Cập nhật đơn hàng'
        if 'status' in data: desc += f" - Trạng thái: {data['status']}"
        if 'notes' in data: desc += f" - Ghi chú: {data['notes']}"
        h = OrderHistory(
            order_id=order.id,
            action='item_changed',
            description=desc,
            performed_by=u.id if u else None,
            performed_by_name=u.full_name if u else 'Nhân viên',
            created_at=datetime.now()
        )
        db.session.add(h)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Cập nhật đơn hàng thành công!', 'order': order.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<id>', methods=['DELETE'])
def cancel_order(id):
    try:
        order = Order.query.get(id)
        if not order:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng!'}), 404

        order.status = 'cancelled'
        if order.table_id:
            t = Table.query.get(order.table_id)
            if t:
                t.status = 'empty'
                db.session.add(t)

        u = get_current_user()
        h = OrderHistory(
            order_id=order.id,
            action='cancelled',
            description='Đơn hàng bị hủy',
            performed_by=u.id if u else None,
            performed_by_name=u.full_name if u else 'Nhân viên',
            created_at=datetime.now()
        )
        db.session.add(h)

        db.session.add(order)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Hủy đơn hàng thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<id>/pay', methods=['POST'])
def process_payment(id):
    try:
        order = Order.query.get(id)
        if not order:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng!'}), 404

        if order.status == 'completed':
            return jsonify({'success': False, 'message': 'Đơn hàng này đã được thanh toán trước đó!'}), 400

        data = request.json or {}
        method = data.get('method', 'cash')
        voucher_code = data.get('voucher_code', '').strip().upper()
        
        subtotal = order.total
        discount = 0.0
        voucher_id = None

        # Validate voucher if applied
        if voucher_code:
            voucher = Voucher.query.filter_by(code=voucher_code, active=True).first()
            if voucher:
                if subtotal >= voucher.min_order and voucher.used_count < voucher.max_uses:
                    voucher_id = voucher.id
                    if voucher.type == 'percent':
                        discount = subtotal * (voucher.value / 100.0)
                    else:
                        discount = voucher.value
                    voucher.used_count += 1
                    db.session.add(voucher)

        final_amount = max(0.0, subtotal - discount)
        order.total = final_amount
        order.status = 'completed'

        payment = Payment(
            order_id=order.id,
            method=method,
            amount=final_amount,
            voucher_id=voucher_id,
            discount=discount,
            created_at=datetime.now()
        )
        db.session.add(payment)

        # Free table
        if order.table_id:
            t = Table.query.get(order.table_id)
            if t:
                t.status = 'empty'
                db.session.add(t)

        # Deduct ingredient inventory based on recipe
        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        for oi in order_items:
            recipes = MenuIngredient.query.filter_by(menu_item_id=oi.menu_item_id).all()
            for rec in recipes:
                ing = Ingredient.query.get(rec.ingredient_id)
                if ing:
                    needed = rec.quantity_needed * oi.quantity
                    ing.quantity = max(0.0, ing.quantity - needed)
                    db.session.add(ing)

        # Award member points if member_code provided
        member_code = data.get('member_code', '').strip().upper()
        points_earned = 0
        member_name = None
        if member_code:
            member = Member.query.filter_by(card_code=member_code, active=True).first()
            if member:
                setting = PointSetting.query.first()
                rate = setting.points_per_vnd if setting else 0.001
                min_order_earn = setting.min_order_to_earn if setting else 0.0
                if final_amount >= min_order_earn:
                    points_earned = int(final_amount * rate)
                    member.points += points_earned
                    member.total_spent += final_amount
                    member.update_level()
                    db.session.add(member)
                    if points_earned > 0:
                        txn = PointTransaction(
                            member_id=member.id,
                            order_id=order.id,
                            type='earn',
                            points=points_earned,
                            description=f'Tích điểm đơn #{order.id}',
                            created_at=datetime.now()
                        )
                        db.session.add(txn)
                member_name = member.name

        db.session.add(order)
        db.session.commit()

        # Log order completion history
        u = get_current_user()
        h = OrderHistory(
            order_id=order.id,
            action='completed', 
            description=f'Thanh toán {format_vnd(final_amount)} qua {method}',
            performed_by=u.id if u else None,
            performed_by_name=u.full_name if u else 'Thu ngân',
            created_at=datetime.now()
        )
        db.session.add(h)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Thanh toán thành công!',
            'order': order.to_dict(),
            'payment': payment.to_dict(),
            'points_earned': points_earned,
            'member_name': member_name
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/orders/<id>/bill', methods=['GET'])
def get_bill(id):
    try:
        order = Order.query.get(id)
        if not order:
            return jsonify({'success': False, 'message': 'Không tìm thấy đơn hàng!'}), 404

        order_dict = order.to_dict()
        table_num = order.table.number if order.table else 'Mang về'
        staff_name = order.staff.name if order.staff else 'Thu ngân'

        payment = order.payment
        payment_dict = payment.to_dict() if payment else {
            'method': 'Chưa thanh toán',
            'amount': order.total,
            'discount': 0.0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Subtotal calculation
        subtotal = sum(item['subtotal'] for item in order_dict['items'])

        bill_data = {
            'cafe_name': 'CAFE ANTIGRAVITY',
            'cafe_address': '01 Lê Duẩn, Hải Châu, Đà Nẵng',
            'cafe_phone': '0236 3888 999',
            'cafe_wifi': 'CafeAntigravity (Pass: 88888888)',
            'bill_number': f"HD{order.id:05d}",
            'order_id': order.id,
            'table': table_num,
            'staff': staff_name,
            'created_at': order_dict['created_at'],
            'items': order_dict['items'],
            'subtotal': subtotal,
            'discount': payment_dict.get('discount', 0.0),
            'voucher_code': payment_dict.get('voucher_code'),
            'total': order.total,
            'payment_method': payment_dict.get('method', 'cash'),
            'status': order.status
        }
        return jsonify({'success': True, 'bill': bill_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# STAFF MANAGEMENT API
# ==============================================================================

@app.route('/api/staff', methods=['GET'])
def get_staff():
    try:
        staff_list = Staff.query.all()
        return jsonify([s.to_dict() for s in staff_list])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff', methods=['POST'])
def add_staff():
    try:
        data = request.json or request.form
        name = data.get('name', '').strip()
        role = data.get('role', 'waiter').strip()
        if not name:
            return jsonify({'success': False, 'message': 'Tên nhân viên không được để trống!'}), 400

        staff = Staff(
            name=name,
            role=role,
            phone=data.get('phone', '').strip(),
            email=data.get('email', '').strip(),
            salary=float(data.get('salary', 0)),
            hire_date=data.get('hire_date') or datetime.now().strftime('%Y-%m-%d'),
            active=bool(data.get('active', True))
        )
        db.session.add(staff)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Thêm nhân viên thành công!', 'staff': staff.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/<id>', methods=['PUT'])
def edit_staff(id):
    try:
        staff = Staff.query.get(id)
        if not staff:
            return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên!'}), 404

        data = request.json or request.form
        if 'name' in data: staff.name = data['name'].strip()
        if 'role' in data: staff.role = data['role'].strip()
        if 'phone' in data: staff.phone = data['phone'].strip()
        if 'email' in data: staff.email = data['email'].strip()
        if 'salary' in data: staff.salary = float(data['salary'])
        if 'hire_date' in data: staff.hire_date = data['hire_date'].strip()
        if 'active' in data: staff.active = bool(data['active'])

        db.session.add(staff)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật nhân viên thành công!', 'staff': staff.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/staff/<id>', methods=['DELETE'])
def deactivate_staff(id):
    try:
        staff = Staff.query.get(id)
        if not staff:
            return jsonify({'success': False, 'message': 'Không tìm thấy nhân viên!'}), 404

        staff.active = False
        db.session.add(staff)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã vô hiệu hóa nhân viên!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# VOUCHER MANAGEMENT API
# ==============================================================================

@app.route('/api/vouchers', methods=['GET'])
def get_vouchers():
    try:
        vouchers = Voucher.query.all()
        return jsonify([v.to_dict() for v in vouchers])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vouchers', methods=['POST'])
def create_voucher():
    try:
        data = request.json or request.form
        code = data.get('code', '').strip().upper()
        if not code or data.get('value') is None:
            return jsonify({'success': False, 'message': 'Vui lòng nhập Mã giảm giá và Giá trị!'}), 400

        existing = Voucher.query.filter_by(code=code).first()
        if existing:
            return jsonify({'success': False, 'message': f'Mã voucher "{code}" đã tồn tại!'}), 400

        voucher = Voucher(
            code=code,
            type=data.get('type', 'percent'),
            value=float(data.get('value')),
            min_order=float(data.get('min_order', 0)),
            max_uses=int(data.get('max_uses', 100)),
            used_count=0,
            valid_from=data.get('valid_from') or datetime.now().strftime('%Y-%m-%d'),
            valid_until=data.get('valid_until') or (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
            active=bool(data.get('active', True))
        )
        db.session.add(voucher)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Tạo mã giảm giá thành công!', 'voucher': voucher.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vouchers/<id>', methods=['PUT'])
def edit_voucher(id):
    try:
        voucher = Voucher.query.get(id)
        if not voucher:
            return jsonify({'success': False, 'message': 'Không tìm thấy voucher!'}), 404

        data = request.json or request.form
        if 'code' in data: voucher.code = data['code'].strip().upper()
        if 'type' in data: voucher.type = data['type'].strip()
        if 'value' in data: voucher.value = float(data['value'])
        if 'min_order' in data: voucher.min_order = float(data['min_order'])
        if 'max_uses' in data: voucher.max_uses = int(data['max_uses'])
        if 'valid_from' in data: voucher.valid_from = data['valid_from'].strip()
        if 'valid_until' in data: voucher.valid_until = data['valid_until'].strip()
        if 'active' in data: voucher.active = bool(data['active'])

        db.session.add(voucher)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật voucher thành công!', 'voucher': voucher.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vouchers/<id>', methods=['DELETE'])
def delete_voucher(id):
    try:
        voucher = Voucher.query.get(id)
        if not voucher:
            return jsonify({'success': False, 'message': 'Không tìm thấy voucher!'}), 404

        db.session.delete(voucher)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Xóa voucher thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/vouchers/validate', methods=['POST'])
def validate_voucher():
    try:
        data = request.json or {}
        code = data.get('code', '').strip().upper()
        order_amount = float(data.get('order_amount', 0))

        if not code:
            return jsonify({'valid': False, 'message': 'Vui lòng nhập mã giảm giá!'}), 400

        voucher = Voucher.query.filter_by(code=code).first()
        if not voucher:
            return jsonify({'valid': False, 'message': 'Mã giảm giá không tồn tại!'})

        if not voucher.active:
            return jsonify({'valid': False, 'message': 'Mã giảm giá hiện đang bị khóa!'})

        if voucher.used_count >= voucher.max_uses:
            return jsonify({'valid': False, 'message': 'Mã giảm giá đã hết lượt sử dụng!'})

        today_str = datetime.now().strftime('%Y-%m-%d')
        if voucher.valid_from and today_str < voucher.valid_from:
            return jsonify({'valid': False, 'message': f'Mã giảm giá chỉ có hiệu lực từ ngày {voucher.valid_from}!'})
        if voucher.valid_until and today_str > voucher.valid_until:
            return jsonify({'valid': False, 'message': f'Mã giảm giá đã hết hạn từ ngày {voucher.valid_until}!'})

        if order_amount < voucher.min_order:
            return jsonify({
                'valid': False,
                'message': f'Đơn hàng tối thiểu {format_vnd(voucher.min_order)} để áp dụng mã này!'
            })

        # Calculate discount
        if voucher.type == 'percent':
            discount = order_amount * (voucher.value / 100.0)
            desc_text = f"Giảm {voucher.value}%"
        else:
            discount = min(voucher.value, order_amount)
            desc_text = f"Giảm {format_vnd(voucher.value)}"

        final_amount = max(0.0, order_amount - discount)

        return jsonify({
            'valid': True,
            'message': f'Áp dụng thành công: {desc_text}!',
            'code': voucher.code,
            'type': voucher.type,
            'value': voucher.value,
            'discount': float(discount),
            'final_amount': float(final_amount)
        })
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500

# ==============================================================================
# INGREDIENT & INVENTORY MANAGEMENT API
# ==============================================================================

@app.route('/api/ingredients', methods=['GET'])
def get_ingredients():
    try:
        ingredients = Ingredient.query.all()
        return jsonify([ing.to_dict() for ing in ingredients])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredients', methods=['POST'])
def add_ingredient():
    try:
        data = request.json or request.form
        name = data.get('name', '').strip()
        unit = data.get('unit', '').strip()
        if not name or not unit:
            return jsonify({'success': False, 'message': 'Tên nguyên liệu và Đơn vị tính là bắt buộc!'}), 400

        ing = Ingredient(
            name=name,
            unit=unit,
            quantity=float(data.get('quantity', 0)),
            min_quantity=float(data.get('min_quantity', 10)),
            cost_per_unit=float(data.get('cost_per_unit', 0)),
            supplier=data.get('supplier', '').strip()
        )
        db.session.add(ing)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Thêm nguyên liệu thành công!', 'ingredient': ing.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredients/<id>', methods=['PUT'])
def update_ingredient(id):
    try:
        ing = Ingredient.query.get(id)
        if not ing:
            return jsonify({'success': False, 'message': 'Không tìm thấy nguyên liệu!'}), 404

        data = request.json or request.form
        if 'name' in data: ing.name = data['name'].strip()
        if 'unit' in data: ing.unit = data['unit'].strip()
        if 'quantity' in data: ing.quantity = float(data['quantity'])
        if 'add_quantity' in data: ing.quantity = max(0.0, ing.quantity + float(data['add_quantity']))
        if 'min_quantity' in data: ing.min_quantity = float(data['min_quantity'])
        if 'cost_per_unit' in data: ing.cost_per_unit = float(data['cost_per_unit'])
        if 'supplier' in data: ing.supplier = data['supplier'].strip()

        db.session.add(ing)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật nguyên liệu thành công!', 'ingredient': ing.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ingredients/<id>', methods=['DELETE'])
def delete_ingredient(id):
    try:
        ing = Ingredient.query.get(id)
        if not ing:
            return jsonify({'success': False, 'message': 'Không tìm thấy nguyên liệu!'}), 404

        db.session.delete(ing)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Xóa nguyên liệu thành công!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==============================================================================
# MEMBER & LOYALTY POINTS API
# ==============================================================================

@app.route('/api/point-settings', methods=['GET'])
def get_point_settings():
    try:
        setting = PointSetting.query.first()
        if not setting:
            setting = PointSetting()
            db.session.add(setting)
            db.session.commit()
        return jsonify({'success': True, 'settings': setting.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/point-settings', methods=['PUT'])
def update_point_settings():
    try:
        setting = PointSetting.query.first()
        if not setting:
            setting = PointSetting()
        data = request.json or {}
        if 'points_per_vnd' in data:    setting.points_per_vnd = float(data['points_per_vnd'])
        if 'min_order_to_earn' in data: setting.min_order_to_earn = float(data['min_order_to_earn'])
        if 'points_to_vnd' in data:     setting.points_to_vnd = float(data['points_to_vnd'])
        if 'min_points_redeem' in data: setting.min_points_redeem = int(data['min_points_redeem'])
        setting.updated_at = datetime.now()
        db.session.add(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật cài đặt điểm thành công!', 'settings': setting.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members', methods=['GET'])
def get_members():
    try:
        search = request.args.get('search', '').lower()
        members = Member.query.all()
        if search:
            members = [m for m in members if search in m.name.lower() or search in m.phone or search in m.card_code.lower()]
        members = sorted(members, key=lambda m: m.id, reverse=True)
        return jsonify([m.to_dict() for m in members])
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members', methods=['POST'])
def add_member():
    try:
        data = request.json or {}
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        if not name or not phone:
            return jsonify({'success': False, 'message': 'Họ tên và Số điện thoại là bắt buộc!'}), 400
        if Member.query.filter_by(phone=phone).first():
            return jsonify({'success': False, 'message': 'Số điện thoại này đã được đăng ký!'}), 400

        import random, string
        while True:
            code = 'MBR' + ''.join(random.choices(string.digits, k=6))
            if not Member.query.filter_by(card_code=code).first():
                break

        member = Member(
            name=name, phone=phone,
            email=data.get('email', '').strip(),
            card_code=code,
            points=0, total_spent=0.0, level='Đồng',
            joined_at=datetime.now(),
            notes=data.get('notes', '').strip(),
            active=True
        )
        db.session.add(member)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Tạo thẻ thành viên thành công! Mã thẻ: {code}', 'member': member.to_dict()}), 201
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members/<id>', methods=['GET'])
def get_member(id):
    try:
        member = Member.query.get(id)
        if not member:
            return jsonify({'success': False, 'message': 'Không tìm thấy thành viên!'}), 404
        txns = PointTransaction.query.filter_by(member_id=member.id).order_by(PointTransaction.id.desc()).limit(20).all()
        return jsonify({'success': True, 'member': member.to_dict(), 'transactions': [t.to_dict() for t in txns]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members/<id>', methods=['PUT'])
def edit_member(id):
    try:
        member = Member.query.get(id)
        if not member:
            return jsonify({'success': False, 'message': 'Không tìm thấy thành viên!'}), 404
        data = request.json or {}
        if 'name' in data: member.name = data['name'].strip()
        if 'email' in data: member.email = data['email'].strip()
        if 'notes' in data: member.notes = data['notes'].strip()
        if 'active' in data: member.active = bool(data['active'])
        db.session.add(member)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Cập nhật thông tin thành viên!', 'member': member.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members/<id>/adjust-points', methods=['POST'])
def adjust_member_points(id):
    try:
        member = Member.query.get(id)
        if not member:
            return jsonify({'success': False, 'message': 'Không tìm thấy thành viên!'}), 404
        data = request.json or {}
        points = int(data.get('points', 0))
        reason = data.get('reason', 'Điều chỉnh thủ công').strip()
        txn_type = data.get('type', 'adjust')
        member.points = max(0, member.points + points)
        db.session.add(member)
        txn = PointTransaction(member_id=member.id, order_id=None, type=txn_type, points=points, description=reason, created_at=datetime.now())
        db.session.add(txn)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Đã điều chỉnh {points:+d} điểm cho {member.name}!', 'member': member.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/members/lookup', methods=['POST'])
def lookup_member():
    try:
        data = request.json or {}
        query = data.get('query', '').strip().upper()
        if not query:
            return jsonify({'found': False, 'message': 'Vui lòng nhập mã thẻ hoặc số điện thoại!'})
        member = Member.query.filter_by(card_code=query, active=True).first()
        if not member:
            member = Member.query.filter_by(phone=query, active=True).first()
        if not member:
            return jsonify({'found': False, 'message': 'Không tìm thấy thành viên!'})
        setting = PointSetting.query.first()
        return jsonify({'found': True, 'member': member.to_dict(), 'settings': setting.to_dict() if setting else {}})
    except Exception as e:
        return jsonify({'found': False, 'error': str(e)}), 500

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    with app.app_context():
        db.create_all()
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                cols = [r[1] for r in conn.execute(text("PRAGMA table_info(tables)")).fetchall()]
                if 'area_id' not in cols:
                    conn.execute(text("ALTER TABLE tables ADD COLUMN area_id INTEGER"))
                if 'area_name' not in cols:
                    conn.execute(text("ALTER TABLE tables ADD COLUMN area_name VARCHAR(100)"))
                conn.commit()
        except Exception:
            pass

        if not Area.query.first():
            a1 = Area(name='Tầng 1', description='Khu vực tầng trệt')
            a2 = Area(name='Tầng 2', description='Khu vực tầng 2 thoáng mát')
            db.session.add_all([a1, a2])
            db.session.commit()
            for t in Table.query.filter_by(floor=1).all():
                t.area_id = a1.id
                t.area_name = a1.name
            for t in Table.query.filter_by(floor=2).all():
                t.area_id = a2.id
                t.area_name = a2.name
            db.session.commit()

        if not PointSetting.query.first():
            db.session.add(PointSetting())
            db.session.commit()
        if not User.query.first():
            owner = User(username='admin', full_name='Chu quan', role='owner', active=True)
            owner.set_password('admin123')
            db.session.add(owner)
            db.session.commit()
            print("Default account: admin / admin123")
    print("Cafe Antigravity Starting on http://127.0.0.1:5000")
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

