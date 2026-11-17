from datetime import datetime, timedelta
import random
from models import (
    db, Category, MenuItem, Table, Staff, 
    Order, OrderItem, Payment, Voucher, 
    Ingredient, MenuIngredient
)

def init_database(app=None):
    if app:
        db.init_app(app)
    
    print("Initializing database...")
    db.create_all()

    # Clear existing data
    db.drop_all()
    db.create_all()

    # 1. Categories
    categories_data = [
        ("Cà phê", "Cà phê pha phin truyền thống và phong cách hiện đại"),
        ("Trà", "Trà trái cây, trà sen, trà hoa thanh mát"),
        ("Nước ép", "Nước ép trái cây tươi nguyên chất 100%"),
        ("Sinh tố", "Sinh tố hoa quả tươi mát, bổ dưỡng"),
        ("Bánh ngọt", "Bánh ngọt châu Âu và bánh nướng tươi trong ngày"),
        ("Đồ ăn nhẹ", "Các món ăn nhẹ, bánh mì và đồ ăn vặt")
    ]
    
    category_objs = {}
    for name, desc in categories_data:
        cat = Category(name=name, description=desc)
        db.session.add(cat)
        category_objs[name] = cat
    db.session.commit()
    print("[OK] Categories created")

    # 2. Menu Items
    # High-quality cafe placeholder images (SVGs/Unsplash food URLs)
    items_data = [
        # Cà phê
        ("Cà phê sữa đá", "Cà phê", 29000, "Cà phê phin truyền thống hòa quyện cùng sữa đặc béo ngọt", "https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?w=500&auto=format&fit=crop"),
        ("Cà phê đen đá", "Cà phê", 25000, "Cà phê đen nguyên chất đậm đà thơm ngát hương hoa quả chín", "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500&auto=format&fit=crop"),
        ("Bạc xỉu", "Cà phê", 32000, "Nhiều sữa đặc ngọt dịu với chút cà phê thơm lừng", "https://images.unsplash.com/photo-1541167760496-1628856ab772?w=500&auto=format&fit=crop"),
        ("Cà phê muối", "Cà phê", 35000, "Lớp kem béo mặn nhẹ hòa quyện cà phê đen đậm vị", "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=500&auto=format&fit=crop"),
        ("Cà phê trứng", "Cà phê", 42000, "Lớp kem trứng đánh bông béo ngậy đặc sản Hà Nội", "https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=500&auto=format&fit=crop"),

        # Trà
        ("Trà đào cam sả", "Trà", 39000, "Trà đào thanh ngọt kết hợp vị chua cam tươi và hương sả nồng", "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=500&auto=format&fit=crop"),
        ("Trà sen vàng macchiato", "Trà", 45000, "Trà ô long sen thơm mát, hạt sen bùi béo và lớp kem macchiato", "https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=500&auto=format&fit=crop"),
        ("Trà vải hoa hồng", "Trà", 42000, "Trà hoa hồng dịu nhẹ thơm ngọt cùng trái vải giòn sần sật", "https://images.unsplash.com/photo-1597481499750-3e6b22637e12?w=500&auto=format&fit=crop"),
        ("Matcha Latte đá", "Trà", 48000, "Matcha Uji Nhật Bản kết hợp cùng sữa tươi béo ngậy", "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?w=500&auto=format&fit=crop"),

        # Nước ép
        ("Nước ép cam tươi", "Nước ép", 38000, "Cam sành vắt tươi giàu Vitamin C, vị chua ngọt tự nhiên", "https://images.unsplash.com/photo-1613478223719-2ab802602423?w=500&auto=format&fit=crop"),
        ("Nước ép dưa hấu", "Nước ép", 35000, "Dưa hấu đỏ mọng nước giải nhiệt ngày hè", "https://images.unsplash.com/photo-1589733955941-5eeaf752f6dd?w=500&auto=format&fit=crop"),
        ("Nước ép ổi hồng", "Nước ép", 38000, "Ổi hồng thơm lừng, ít đường, tốt cho sức khỏe", "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=500&auto=format&fit=crop"),

        # Sinh tố
        ("Sinh tố bơ sáp", "Sinh tố", 45000, "Bơ sáp Đắk Lắk dẻo mịn béo ngậy hòa cùng sữa tươi", "https://images.unsplash.com/photo-1553530666-ba11a7da3888?w=500&auto=format&fit=crop"),
        ("Sinh tố xoài cát", "Sinh tố", 42000, "Xoài cát chín vàng ngọt lịm thơm ngon", "https://images.unsplash.com/photo-1623065422902-30a2d299bbe4?w=500&auto=format&fit=crop"),

        # Bánh ngọt
        ("Bánh Tiramisu", "Bánh ngọt", 45000, "Bánh Tiramisu Ý mềm mịn đẫm vị cà phê và mascarpone", "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=500&auto=format&fit=crop"),
        ("Bánh Croissant bơ tỏi", "Bánh ngọt", 35000, "Bánh sừng bò nướng giòn rụm thơm ngậy bơ tỏi", "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=500&auto=format&fit=crop"),
        ("Bánh Phô mai việt quất", "Bánh ngọt", 48000, "Cheesecake thơm béo phủ sốt việt quất chua ngọt đậm đà", "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=500&auto=format&fit=crop"),

        # Đồ ăn nhẹ
        ("Bánh mì chảo đặc biệt", "Đồ ăn nhẹ", 55000, "Trứng ốp la, pate gan, xúc xích và sốt cà chua đậm đà kèm bánh mì nóng", "https://images.unsplash.com/photo-1525351484163-7529414344d8?w=500&auto=format&fit=crop"),
        ("Khoai tây chiên giòn", "Đồ ăn nhẹ", 30000, "Khoai tây chiên vàng giòn lắc phô mai thơm phức", "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=500&auto=format&fit=crop")
    ]

    menu_item_objs = []
    for name, cat, price, desc, img in items_data:
        item = MenuItem(name=name, category=cat, price=price, description=desc, image_url=img, available=True)
        db.session.add(item)
        menu_item_objs.append(item)
    db.session.commit()
    print("[OK] Menu items created (19 items)")

    # 3. Tables (10 tables, 2 floors)
    tables_data = [
        # Tầng 1
        ("Bàn 01", 4, "empty", 1),
        ("Bàn 02", 2, "occupied", 1),
        ("Bàn 03", 4, "empty", 1),
        ("Bàn 04", 6, "reserved", 1),
        ("Bàn 05", 4, "empty", 1),
        # Tầng 2
        ("Bàn 06", 4, "empty", 2),
        ("Bàn 07", 8, "occupied", 2),
        ("Bàn 08", 2, "empty", 2),
        ("Bàn 09", 4, "reserved", 2),
        ("Bàn 10", 6, "empty", 2)
    ]
    table_objs = {}
    for num, cap, status, floor in tables_data:
        t = Table(number=num, capacity=cap, status=status, floor=floor)
        db.session.add(t)
        table_objs[num] = t
    db.session.commit()
    print("[OK] Tables created (10 tables)")

    # 4. Staff members (5 staff)
    staff_data = [
        ("Nguyễn Văn An", "admin", "0901234567", "an.nguyen@cafeantigravity.vn", 15000000, "2024-01-15", True),
        ("Trần Thị Mai", "cashier", "0912345678", "mai.tran@cafeantigravity.vn", 9000000, "2024-03-01", True),
        ("Lê Hoàng Nam", "waiter", "0923456789", "nam.le@cafeantigravity.vn", 7500000, "2024-05-10", True),
        ("Phạm Thu Hà", "cashier", "0934567890", "ha.pham@cafeantigravity.vn", 8500000, "2024-06-20", True),
        ("Đỗ Minh Tuấn", "waiter", "0945678901", "tuan.do@cafeantigravity.vn", 7500000, "2024-08-01", True)
    ]
    staff_objs = []
    for name, role, phone, email, salary, hdate, act in staff_data:
        s = Staff(name=name, role=role, phone=phone, email=email, salary=salary, hire_date=hdate, active=act)
        db.session.add(s)
        staff_objs.append(s)
    db.session.commit()
    print("[OK] Staff members created (5 staff)")

    # 5. Vouchers (3 vouchers)
    vouchers_data = [
        ("WELCOME10", "percent", 10, 50000, 200, 18, "2024-01-01", "2027-12-31", True),
        ("CAFE20K", "fixed", 20000, 100000, 100, 35, "2024-01-01", "2027-12-31", True),
        ("VIP15", "percent", 15, 150000, 50, 12, "2024-01-01", "2027-12-31", True)
    ]
    voucher_objs = {}
    for code, vtype, val, min_o, max_u, used_c, v_from, v_until, act in vouchers_data:
        v = Voucher(
            code=code, type=vtype, value=val, min_order=min_o, 
            max_uses=max_u, used_count=used_c, valid_from=v_from, 
            valid_until=v_until, active=act
        )
        db.session.add(v)
        voucher_objs[code] = v
    db.session.commit()
    print("[OK] Vouchers created (3 vouchers)")

    # 6. Ingredients (12 ingredients, with 2 low-stock for alerts)
    ingredients_data = [
        ("Hạt Cà phê Robusta", "g", 15000, 5000, 180, "Nông trại Đắk Lắk"),
        ("Hạt Cà phê Arabica", "g", 8000, 3000, 250, "Nông trại Cầu Đất"),
        ("Sữa đặc Ông Thọ", "hộp", 45, 20, 24000, "Vinamilk"),
        ("Sữa tươi thanh trùng", "hộp 1L", 30, 15, 36000, "Dalat Milk"),
        ("Trà đen thượng hạng", "g", 5000, 2000, 150, "Phúc Long Tea"),
        ("Trà sen Tây Hồ", "g", 3000, 1500, 280, "Trà Sen Bảo Phương"),
        ("Siro đào Pháp Teisseire", "chai 700ml", 8, 5, 185000, "Cty Cung Ứng Pha Chế"),
        ("Đường cát trắng", "kg", 40, 15, 22000, "Đường Biên Hòa"),
        ("Kem béo thực vật Rich's", "hộp", 4, 10, 32000, "Rich Products"),       # Low stock!
        ("Bột Matcha Nhật Bản", "g", 800, 1000, 600, "Uji Matcha Import"),         # Low stock!
        ("Cam sành Tiền Giang", "kg", 25, 10, 28000, "Vựa trái cây Miền Tây"),
        ("Bơ sáp Đắk Lắk", "kg", 12, 8, 45000, "Nông sản Tây Nguyên")
    ]
    ingredient_objs = []
    for name, unit, qty, min_qty, cost, supp in ingredients_data:
        ing = Ingredient(name=name, unit=unit, quantity=qty, min_quantity=min_qty, cost_per_unit=cost, supplier=supp)
        db.session.add(ing)
        ingredient_objs.append(ing)
    db.session.commit()
    print("[OK] Ingredients created (12 ingredients, 2 low stock)")

    # 7. Menu Ingredients mapping
    # e.g. Cà phê sữa đá needs Robusta (20g), Sữa đặc (1 hộp/10 = 0.1), Đường (10g)
    menu_ing_data = [
        (menu_item_objs[0].id, ingredient_objs[0].id, 20),   # Cà phê sữa đá -> Robusta 20g
        (menu_item_objs[0].id, ingredient_objs[2].id, 0.1),  # Cà phê sữa đá -> Sữa đặc 0.1 hộp
        (menu_item_objs[1].id, ingredient_objs[0].id, 25),   # Cà phê đen đá -> Robusta 25g
        (menu_item_objs[2].id, ingredient_objs[0].id, 15),   # Bạc xỉu -> Robusta 15g
        (menu_item_objs[2].id, ingredient_objs[2].id, 0.15), # Bạc xỉu -> Sữa đặc 0.15 hộp
        (menu_item_objs[2].id, ingredient_objs[3].id, 0.05), # Bạc xỉu -> Sữa tươi 0.05 hộp
        (menu_item_objs[5].id, ingredient_objs[4].id, 15),   # Trà đào -> Trà đen 15g
        (menu_item_objs[5].id, ingredient_objs[6].id, 0.04), # Trà đào -> Siro đào 0.04 chai
        (menu_item_objs[8].id, ingredient_objs[9].id, 10),   # Matcha latte -> Matcha 10g
        (menu_item_objs[8].id, ingredient_objs[3].id, 0.2),  # Matcha latte -> Sữa tươi 0.2 hộp
        (menu_item_objs[9].id, ingredient_objs[10].id, 0.3), # Nước cam -> Cam tươi 0.3kg
        (menu_item_objs[12].id, ingredient_objs[11].id, 0.25)# Sinh tố bơ -> Bơ 0.25kg
    ]
    for m_id, i_id, qty in menu_ing_data:
        mi = MenuIngredient(menu_item_id=m_id, ingredient_id=i_id, quantity_needed=qty)
        db.session.add(mi)
    db.session.commit()
    print("[OK] Menu-Ingredient recipes linked")

    # 8. Sample Orders & Payments for the last 7 days (25 completed orders + 2 pending)
    now = datetime.now()
    payment_methods = ["cash", "card", "transfer"]
    
    # Generate past 7 days completed orders
    order_count = 0
    total_sales = 0
    
    # Let's create 3-5 orders per day for days 6, 5, 4, 3, 2, 1, 0 (today)
    for day_offset in range(6, -1, -1):
        order_date = now - timedelta(days=day_offset)
        num_orders_today = random.randint(3, 5) if day_offset > 0 else 4
        
        for o_idx in range(num_orders_today):
            hour = random.randint(8, 21)
            minute = random.randint(0, 59)
            created_at = order_date.replace(hour=hour, minute=minute, second=0)
            
            # Select table & staff
            table = random.choice(list(table_objs.values()))
            staff = random.choice(staff_objs)
            
            # Select 1 to 4 random menu items
            items_sample = random.sample(menu_item_objs, random.randint(1, 4))
            subtotal = 0
            order_items_to_add = []
            
            for m_item in items_sample:
                qty = random.randint(1, 3)
                price = m_item.price
                subtotal += price * qty
                order_items_to_add.append((m_item.id, qty, price))
            
            # Possible discount voucher
            discount = 0
            voucher_id = None
            if random.random() < 0.35:
                v_choice = random.choice(list(voucher_objs.values()))
                if subtotal >= v_choice.min_order:
                    voucher_id = v_choice.id
                    if v_choice.type == 'percent':
                        discount = subtotal * (v_choice.value / 100.0)
                    else:
                        discount = v_choice.value
            
            final_total = max(0, subtotal - discount)
            
            order = Order(
                table_id=table.id,
                staff_id=staff.id,
                status="completed",
                total=final_total,
                created_at=created_at,
                notes="Khách quen" if random.random() < 0.2 else ""
            )
            db.session.add(order)
            db.session.commit()
            
            for m_id, qty, price in order_items_to_add:
                oi = OrderItem(order_id=order.id, menu_item_id=m_id, quantity=qty, price=price, notes="")
                db.session.add(oi)
            
            pmethod = random.choice(payment_methods)
            payment = Payment(
                order_id=order.id,
                method=pmethod,
                amount=final_total,
                voucher_id=voucher_id,
                discount=discount,
                created_at=created_at + timedelta(minutes=random.randint(15, 45))
            )
            db.session.add(payment)
            db.session.commit()
            
            order_count += 1
            total_sales += final_total

    # Create 2 active pending orders for the occupied tables (Bàn 02 and Bàn 07)
    table_02 = table_objs["Bàn 02"]
    order_02 = Order(
        table_id=table_02.id,
        staff_id=staff_objs[1].id,
        status="pending",
        total=64000,
        created_at=now - timedelta(minutes=25),
        notes="Ít đá, ít ngọt"
    )
    db.session.add(order_02)
    db.session.commit()
    db.session.add(OrderItem(order_id=order_02.id, menu_item_id=menu_item_objs[0].id, quantity=1, price=29000, notes="Ít ngọt"))
    db.session.add(OrderItem(order_id=order_02.id, menu_item_id=menu_item_objs[15].id, quantity=1, price=35000, notes="Làm nóng giòn"))
    db.session.commit()

    table_07 = table_objs["Bàn 07"]
    order_07 = Order(
        table_id=table_07.id,
        staff_id=staff_objs[2].id,
        status="pending",
        total=186000,
        created_at=now - timedelta(minutes=15),
        notes="Nhóm bạn công ty"
    )
    db.session.add(order_07)
    db.session.commit()
    db.session.add(OrderItem(order_id=order_07.id, menu_item_id=menu_item_objs[3].id, quantity=2, price=35000, notes=""))
    db.session.add(OrderItem(order_id=order_07.id, menu_item_id=menu_item_objs[5].id, quantity=1, price=39000, notes="Nhiều đào"))
    db.session.add(OrderItem(order_id=order_07.id, menu_item_id=menu_item_objs[14].id, quantity=1, price=45000, notes=""))
    db.session.add(OrderItem(order_id=order_07.id, menu_item_id=menu_item_objs[18].id, quantity=1, price=30000, notes=""))
    db.session.commit()

    print(f"[OK] Sample orders created ({order_count} completed orders, 2 active pending orders)")
    print(f"[OK] Total revenue in sample orders: {total_sales:,.0f} VND")
    print("Database initialization complete successfully!")

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafe.db'
    with open('models.py', 'r') as _:
        pass
    init_database(app)
