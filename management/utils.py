from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
import datetime
import json

# Import Models
from store.models import Product
from orders.models import Order, OrderProduct
from accounts.models import Account


# --- 1. HÀM PHỤ TRỢ: TÍNH KHOẢNG THỜI GIAN ---
def get_date_range(period):
    now = timezone.now()
    today = now.date()

    if period == 'this_month':
        # Từ ngày 1 tháng này đến hiện tại
        start_date = today.replace(day=1)
        end_date = now
        # Kỳ trước: Tháng trước
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end.replace(day=1)

    elif period == 'this_year':
        # Từ 1/1 năm nay đến hiện tại
        start_date = today.replace(month=1, day=1)
        end_date = now
        # Kỳ trước: Năm ngoái
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end.replace(month=1, day=1)

    elif period == 'last_30_days':
        start_date = today - timedelta(days=30)
        end_date = now
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=30)

    else:  # Mặc định: 7 ngày qua ('7days')
        start_date = today - timedelta(days=6)
        end_date = now
        # Kỳ trước: 7 ngày trước đó nữa
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=6)

    return start_date, end_date, prev_start, prev_end


# --- 2. KPI DATA (CẬP NHẬT ĐỂ NHẬN THAM SỐ PERIOD) ---
def get_kpi_data(period='7days'):
    start_date, end_date, prev_start, prev_end = get_date_range(period)

    # 1. Revenue (Doanh thu trong khoảng chọn)
    rev_current = \
    Order.objects.filter(is_ordered=True, created_at__range=[start_date, end_date]).aggregate(Sum('order_total'))[
        'order_total__sum'] or 0
    rev_prev = \
    Order.objects.filter(is_ordered=True, created_at__range=[prev_start, prev_end]).aggregate(Sum('order_total'))[
        'order_total__sum'] or 0

    # Growth Rate
    if rev_prev > 0:
        growth_rate = ((rev_current - rev_prev) / rev_prev) * 100
    elif rev_current > 0:
        growth_rate = 100.0
    else:
        growth_rate = 0.0

    # 2. Orders
    orders_current = Order.objects.filter(is_ordered=True, created_at__range=[start_date, end_date]).count()
    orders_prev = Order.objects.filter(is_ordered=True, created_at__range=[prev_start, prev_end]).count()

    if orders_prev > 0:
        order_growth = ((orders_current - orders_prev) / orders_prev) * 100
    elif orders_current > 0:
        order_growth = 100.0
    else:
        order_growth = 0.0

    # 3. Customers
    total_customers = Account.objects.count()  # Tổng user trọn đời
    new_customers = Account.objects.filter(date_joined__range=[start_date, end_date]).count()  # User mới trong kỳ

    # 4. Sell Rate
    sold_units = OrderProduct.objects.filter(ordered=True).aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_stock = Product.objects.aggregate(Sum('stock'))['stock__sum'] or 0
    sell_rate = round((sold_units / (total_stock + sold_units) * 100), 1) if (total_stock + sold_units) > 0 else 0

    # 5. Pending & Completed
    count_pending = Order.objects.filter(is_ordered=True, status='New').count()
    count_completed = Order.objects.filter(is_ordered=True, status='Completed').count()

    return {
        'total_revenue': rev_current,  # Trả về doanh thu theo kỳ (không phải trọn đời)
        'growth_rate': round(growth_rate, 1),
        'total_orders': orders_current,
        'order_growth': round(order_growth, 1),
        'total_customers': total_customers,
        'new_customers_this_month': new_customers,
        'sell_rate': sell_rate,
        'count_pending': count_pending,
        'count_completed': count_completed,
    }


# --- 3. CHART DATA (CẬP NHẬT ĐỂ NHẬN THAM SỐ PERIOD) ---
def get_chart_data(period='7days'):
    start_date, end_date, _, _ = get_date_range(period)

    dates_list = []
    revenue_list = []
    orders_count_list = []

    # Tính số ngày cần vẽ
    # Lưu ý: end_date có thể là datetime, start_date có thể là date, cần ép kiểu về date để trừ
    if isinstance(end_date, datetime.datetime): end_date = end_date.date()
    if isinstance(start_date, datetime.datetime): start_date = start_date.date()

    days_range = (end_date - start_date).days + 1

    # Vẽ biểu đồ theo ngày
    for i in range(days_range):
        current_date = start_date + timedelta(days=i)
        dates_list.append(current_date.strftime('%d/%m'))

        daily_data = Order.objects.filter(is_ordered=True, created_at__date=current_date)

        daily_rev = daily_data.aggregate(Sum('order_total'))['order_total__sum'] or 0
        revenue_list.append(float(daily_rev))

        daily_count = daily_data.count()
        orders_count_list.append(daily_count)

    # Chart Growth (Tái sử dụng logic đơn giản hoặc tính kỹ hơn tùy ý)
    chart_growth = 0
    if sum(revenue_list) > 0: chart_growth = 100

    # Pie & Bar Charts (Lọc theo khoảng thời gian đã chọn)
    # Cần convert start_date/end_date về datetime để filter range chính xác nếu cần
    # Ở đây dùng __date__range cho đơn giản

    cat_stats = OrderProduct.objects.filter(ordered=True, created_at__date__range=[start_date, end_date]).values(
        'product__category__category_name').annotate(count=Count('id')).order_by('-count')[:5]
    cat_labels = [x['product__category__category_name'] for x in cat_stats]
    cat_data = [x['count'] for x in cat_stats]

    top_prods = OrderProduct.objects.filter(ordered=True, created_at__date__range=[start_date, end_date]).values(
        'product__product_name').annotate(qty=Sum('quantity')).order_by('-qty')[:5]
    prod_labels = [x['product__product_name'] for x in top_prods]
    prod_data = [x['qty'] for x in top_prods]

    # Customer Retention (Giả lập)
    cust_data = [65, 35]

    return {
        'chart_dates': json.dumps(dates_list),
        'chart_revenue': json.dumps(revenue_list),
        'chart_orders_count': json.dumps(orders_count_list),
        'cat_labels': json.dumps(cat_labels),
        'cat_data': json.dumps(cat_data),
        'prod_labels': json.dumps(prod_labels),
        'prod_data': json.dumps(prod_data),
        'chart_growth': chart_growth,
        'cust_data': json.dumps(cust_data),
    }


# --- CÁC HÀM KHÁC GIỮ NGUYÊN ---
def get_inventory_data():
    inventory_products = Product.objects.all().order_by('stock')[:10]
    data = []
    for p in inventory_products:
        status = 'Stable';
        badge = 'badge-soft-success'
        if p.stock < 5:
            status = 'Low Stock'; badge = 'badge-soft-danger'
        elif p.stock < 20:
            status = 'Slow'; badge = 'badge-soft-warning'
        data.append({'id': p.id, 'name': p.product_name, 'category': p.category.category_name if p.category else 'N/A',
                     'price': p.price, 'stock': p.stock, 'status': status, 'badge': badge,
                     'image': p.images.url if p.images else ''})
    return data


def get_recent_orders_json():
    latest_orders = Order.objects.filter(is_ordered=True).order_by('-created_at')[:5]
    data = []
    for order in latest_orders:
        data.append({'code': order.order_number, 'customer': f"{order.first_name} {order.last_name}",
                     'total': float(order.order_total), 'time': order.created_at.strftime("%H:%M %d/%m"),
                     'status': order.status})
    return json.dumps(data)


def get_notifications():
    notifs = []
    new_orders = Order.objects.filter(is_ordered=True, status='New').order_by('-created_at')[:5]
    for order in new_orders:
        notifs.append({'icon': 'fa-shopping-cart', 'color': 'text-primary', 'message': f"New Order: {order.first_name}",
                       'sub_text': f"${order.order_total} - {order.order_number}", 'time': order.created_at,
                       'url': f"/orders/"})
    return notifs


def get_recent_customers_json():
    """Lấy 5 khách hàng đăng ký gần nhất cho Popup"""
    # Lấy 5 user mới nhất
    latest_users = Account.objects.order_by('-date_joined')[:5]
    data = []
    for user in latest_users:
        # Tạo chữ cái đầu cho avatar (Ví dụ: Huy -> H)
        initial = user.first_name[0].upper() if user.first_name else "?"

        # Kiểm tra role (nếu model có field role)
        role = 'Customer'
        if hasattr(user, 'role'):
            role = user.role

        data.append({
            'name': f"{user.first_name} {user.last_name}",
            'email': user.email,
            'joined': user.date_joined.strftime("%d/%m"),  # Ngày tham gia
            'role': role,
            'initial': initial
        })
    return json.dumps(data)