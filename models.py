from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class PointSetting(db.Model):
    """Cài đặt tích điểm - chỉ có 1 bản ghi duy nhất"""
    __tablename__ = 'point_settings'

    id = db.Column(db.Integer, primary_key=True)
    points_per_vnd = db.Column(db.Float, default=0.001)   # 1000 VND = 1 điểm mặc định
    min_order_to_earn = db.Column(db.Float, default=0.0)   # Đơn tối thiểu để tích điểm
    points_to_vnd = db.Column(db.Float, default=1000.0)    # 1 điểm = 1000 VND khi đổi
    min_points_redeem = db.Column(db.Integer, default=10)  # Số điểm tối thiểu để đổi
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'points_per_vnd': float(self.points_per_vnd),
            'min_order_to_earn': float(self.min_order_to_earn),
            'points_to_vnd': float(self.points_to_vnd),
            'min_points_redeem': int(self.min_points_redeem),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else ''
        }

class Member(db.Model):
    """Thẻ thành viên"""
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    card_code = db.Column(db.String(20), unique=True, nullable=False)
    points = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0.0)
    level = db.Column(db.String(20), default='Đồng')  # Đồng, Bạc, Vàng, Kim Cương
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text, nullable=True)

    transactions = db.relationship('PointTransaction', backref='member', lazy=True, cascade='all, delete-orphan')

    def update_level(self):
        if self.total_spent >= 10_000_000:
            self.level = 'Kim Cương'
        elif self.total_spent >= 5_000_000:
            self.level = 'Vàng'
        elif self.total_spent >= 2_000_000:
            self.level = 'Bạc'
        else:
            self.level = 'Đồng'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email or '',
            'card_code': self.card_code,
            'points': int(self.points),
            'total_spent': float(self.total_spent),
            'level': self.level,
            'joined_at': self.joined_at.strftime('%Y-%m-%d') if self.joined_at else '',
            'active': bool(self.active),
            'notes': self.notes or ''
        }

class PointTransaction(db.Model):
    """Lịch sử giao dịch điểm"""
    __tablename__ = 'point_transactions'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    type = db.Column(db.String(10), default='earn')  # earn, redeem, adjust
    points = db.Column(db.Integer, nullable=False)   # dương = cộng, âm = trừ
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'order_id': self.order_id,
            'type': self.type,
            'points': int(self.points),
            'description': self.description or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or ''
        }

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': float(self.price),
            'description': self.description or '',
            'available': bool(self.available),
            'image_url': self.image_url or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Table(db.Model):
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), nullable=False, unique=True)
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default='empty')  # empty, occupied, reserved
    floor = db.Column(db.Integer, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'number': self.number,
            'capacity': self.capacity,
            'status': self.status,
            'floor': self.floor
        }

class Staff(db.Model):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, cashier, waiter
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    salary = db.Column(db.Float, default=0.0)
    hire_date = db.Column(db.String(20), nullable=True)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'phone': self.phone or '',
            'email': self.email or '',
            'salary': float(self.salary or 0),
            'hire_date': self.hire_date or '',
            'active': bool(self.active)
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('tables.id'), nullable=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan', lazy=True)
    payment = db.relationship('Payment', backref='order', uselist=False, lazy=True)
    table = db.relationship('Table', backref='orders', lazy=True)
    staff = db.relationship('Staff', backref='orders', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'table_id': self.table_id,
            'table_number': self.table.number if self.table else None,
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else None,
            'status': self.status,
            'total': float(self.total or 0),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'notes': self.notes or '',
            'items': [item.to_dict() for item in self.items] if self.items else [],
            'payment': self.payment.to_dict() if self.payment else None
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, done

    menu_item = db.relationship('MenuItem', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_item_id': self.menu_item_id,
            'item_name': self.menu_item.name if self.menu_item else 'Món đã xóa',
            'quantity': self.quantity,
            'price': float(self.price),
            'subtotal': float(self.price * self.quantity),
            'notes': self.notes or '',
            'status': self.status or 'pending'
        }

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    method = db.Column(db.String(50), default='cash')  # cash, card, transfer
    amount = db.Column(db.Float, nullable=False)
    voucher_id = db.Column(db.Integer, db.ForeignKey('vouchers.id'), nullable=True)
    discount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    voucher = db.relationship('Voucher', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'method': self.method,
            'amount': float(self.amount),
            'voucher_id': self.voucher_id,
            'voucher_code': self.voucher.code if self.voucher else None,
            'discount': float(self.discount or 0),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class Voucher(db.Model):
    __tablename__ = 'vouchers'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(20), default='percent')  # percent, fixed
    value = db.Column(db.Float, nullable=False)
    min_order = db.Column(db.Float, default=0.0)
    max_uses = db.Column(db.Integer, default=100)
    used_count = db.Column(db.Integer, default=0)
    valid_from = db.Column(db.String(20), nullable=True)
    valid_until = db.Column(db.String(20), nullable=True)
    active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'type': self.type,
            'value': float(self.value),
            'min_order': float(self.min_order or 0),
            'max_uses': self.max_uses,
            'used_count': self.used_count,
            'valid_from': self.valid_from or '',
            'valid_until': self.valid_until or '',
            'active': bool(self.active)
        }

class Ingredient(db.Model):
    __tablename__ = 'ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False)  # g, ml, kg, hộp, túi...
    quantity = db.Column(db.Float, default=0.0)
    min_quantity = db.Column(db.Float, default=10.0)
    cost_per_unit = db.Column(db.Float, default=0.0)
    supplier = db.Column(db.String(100), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'unit': self.unit,
            'quantity': float(self.quantity),
            'min_quantity': float(self.min_quantity),
            'cost_per_unit': float(self.cost_per_unit or 0),
            'supplier': self.supplier or '',
            'is_low_stock': bool(self.quantity <= self.min_quantity)
        }

class MenuIngredient(db.Model):
    __tablename__ = 'menu_ingredients'
    
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredients.id'), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False)

    menu_item = db.relationship('MenuItem', lazy=True)
    ingredient = db.relationship('Ingredient', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'menu_item_id': self.menu_item_id,
            'ingredient_id': self.ingredient_id,
            'ingredient_name': self.ingredient.name if self.ingredient else '',
            'ingredient_unit': self.ingredient.unit if self.ingredient else '',
            'quantity_needed': float(self.quantity_needed)
        }

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # owner, manager, cashier, barista, waiter
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=True)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    staff = db.relationship('Staff', lazy=True)

    def set_password(self, password):
        import hashlib
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        import hashlib
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'staff_id': self.staff_id,
            'active': bool(self.active),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'last_login': self.last_login.strftime('%Y-%m-%d %H:%M:%S') if self.last_login else ''
        }

class ShiftSchedule(db.Model):
    __tablename__ = 'shift_schedules'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    shift = db.Column(db.String(20), nullable=False)  # morning, afternoon, evening, fullday, off
    note = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('Staff', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else '',
            'date': self.date,
            'shift': self.shift,
            'note': self.note or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class SalaryRecord(db.Model):
    __tablename__ = 'salary_records'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    month = db.Column(db.String(7), nullable=False)  # YYYY-MM
    base_salary = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    deduction = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    days_worked = db.Column(db.Integer, default=0)
    note = db.Column(db.String(255), nullable=True)
    paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    staff = db.relationship('Staff', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'staff_id': self.staff_id,
            'staff_name': self.staff.name if self.staff else '',
            'staff_role': self.staff.role if self.staff else '',
            'month': self.month,
            'base_salary': float(self.base_salary),
            'bonus': float(self.bonus),
            'deduction': float(self.deduction),
            'total': float(self.total),
            'days_worked': self.days_worked,
            'note': self.note or '',
            'paid': bool(self.paid),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

class OrderHistory(db.Model):
    __tablename__ = 'order_history'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # created, item_added, item_removed, item_changed, cancelled, completed, price_changed
    description = db.Column(db.Text, nullable=False)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    performed_by_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'action': self.action,
            'description': self.description,
            'performed_by_name': self.performed_by_name or 'Hệ thống',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else ''
        }

