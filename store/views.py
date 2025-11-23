from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from carts.views import _cart_id
from carts.models import CartItem

from .models import Product, Variation, ProductVariant
from .forms import ProductForm, VariationForm, ProductVariantForm

from category.models import Category
from .models import Category

def staff_category_list(request):
    categories = Category.objects.all()
    return render(request, "store/staff_category_list.html", {"categories": categories})


# ===============================
# STORE – TRANG KHÁCH HÀNG
# ===============================
def store(request, category_slug=None):
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=category, is_available=True)
    else:
        products = Product.objects.filter(is_available=True).order_by("id")

    paginator = Paginator(products, 10)
    page = request.GET.get("page")
    page_products = paginator.get_page(page)

    return render(request, "store/store.html", {
        "products": page_products,
        "product_count": products.count(),
    })


def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(Product, category__slug=category_slug, slug=product_slug)

    # Lấy combo (ProductVariant)
    variants = ProductVariant.objects.filter(product=product)

    # Lấy list màu và size từ combo
    colors = variants.values_list("color", flat=True).distinct()
    sizes  = variants.values_list("size",  flat=True).distinct()

    # Tổng stock
    total_stock = sum(v.stock for v in variants)

    return render(request, "store/product_detail.html", {
        "single_product": product,
        "colors": colors,
        "sizes": sizes,
        "total_stock": total_stock,
    })


def search(request):
    keyword = request.GET.get("keyword", "")
    if keyword:
        products = Product.objects.filter(
            Q(description__icontains=keyword) | Q(product_name__icontains=keyword)
        )
    else:
        products = Product.objects.all()

    return render(request, "store/store.html", {
        "products": products,
        "product_count": len(products),
    })


# ===============================
# STAFF – QUẢN LÝ SẢN PHẨM
# ===============================
@login_required(login_url="login")
def staff_product_list(request):
    categories = Category.objects.all().order_by('category_name')
    category_filter = request.GET.get('category', 'all')

    if category_filter == "all":
        products = Product.objects.all().order_by('-id')
    else:
        products = Product.objects.filter(category__id=category_filter).order_by('-id')

    return render(request, 'store/staff_product_list.html', {
        'products': products,
        'categories': categories,
        'category_filter': category_filter,
    })



@login_required(login_url="login")
def staff_product_create(request):
    if not request.user.is_staff:
        return redirect("dashboard")

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã thêm sản phẩm.")
            return redirect("staff_product_list")
    else:
        form = ProductForm()

    return render(request, "store/staff_product_form.html", {
        "form": form,
        "title": "Thêm sản phẩm",
    })


@login_required(login_url="login")
def staff_product_update(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")

    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật sản phẩm.")
            return redirect("staff_product_list")
    else:
        form = ProductForm(instance=product)

    return render(request, "store/staff_product_form.html", {
        "form": form,
        "title": "Sửa sản phẩm",
    })


@login_required(login_url="login")
def staff_product_delete(request, pk):
    if not request.user.is_staff:
        return redirect("dashboard")

    product = get_object_or_404(Product, pk=pk)
    product.delete()
    messages.success(request, "Đã xoá sản phẩm.")
    return redirect("staff_product_list")


# ===============================
# STAFF – QUẢN LÝ BIẾN THỂ (COLOR / SIZE)
# ===============================
@login_required(login_url='login')
def staff_variation_by_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    variations = Variation.objects.filter(product=product)

    return render(request, "store/staff_variation_by_product.html", {
        "product": product,
        "colors": variations.filter(variation_category="color"),
        "sizes": variations.filter(variation_category="size"),
    })


@login_required(login_url='login')
def staff_variation_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        variation = Variation(
            product=product,
            variation_category=request.POST.get("variation_category"),
            variation_value=request.POST.get("variation_value"),
            is_active=("is_active" in request.POST),
        )
        variation.save()
        messages.success(request, "Đã thêm biến thể.")
        return redirect('staff_variation_by_product', product_id=product.id)

    return render(request, "store/staff_variation_form.html", {
        "title": "Thêm biến thể",
        "product": product,
    })


@login_required(login_url='login')
def staff_variation_update(request, variation_id):
    variation = get_object_or_404(Variation, id=variation_id)
    product = variation.product

    if request.method == "POST":
        form = VariationForm(request.POST, instance=variation)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật biến thể.")
            return redirect('staff_variation_by_product', product_id=product.id)
    else:
        form = VariationForm(instance=variation)

    return render(request, "store/staff_variation_form.html", {
        "form": form,
        "title": "Sửa biến thể",
        "product": product,
    })


@login_required(login_url="login")
def staff_variation_delete(request, variation_id):
    variation = get_object_or_404(Variation, id=variation_id)
    product_id = variation.product.id
    variation.delete()
    messages.success(request, "Đã xoá biến thể.")
    return redirect('staff_variation_by_product', product_id=product_id)


# ===============================
# STAFF – QUẢN LÝ COMBO (COLOR + SIZE)
# ===============================
@login_required(login_url="login")
def staff_variant_by_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    combos = ProductVariant.objects.filter(product=product)

    return render(request, "store/staff_variant_list.html", {
        "product": product,
        "combos": combos,
    })


@login_required(login_url="login")
def staff_variant_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == "POST":
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, "Đã thêm combo.")
            return redirect("staff_variant_by_product", product_id=product.id)
    else:
        form = ProductVariantForm()

    return render(request, "store/staff_variant_form.html", {
        "form": form,
        "title": "Thêm combo",
        "product": product,
    })


@login_required(login_url="login")
def staff_variant_update(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product = variant.product

    if request.method == "POST":
        form = ProductVariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            messages.success(request, "Đã cập nhật combo.")
            return redirect("staff_variant_by_product", product_id=product.id)
    else:
        form = ProductVariantForm(instance=variant)

    return render(request, "store/staff_variant_form.html", {
        "form": form,
        "title": "Sửa combo",
        "product": product,
    })


@login_required(login_url="login")
def staff_variant_delete(request, variant_id):
    variant = get_object_or_404(ProductVariant, id=variant_id)
    product_id = variant.product.id
    variant.delete()
    messages.success(request, "Đã xoá combo.")
    return redirect("staff_variant_by_product", product_id=product_id)


# ===============================
# STAFF – QUẢN LÝ DANH MỤC
# ===============================
@login_required(login_url="login")
def staff_category_list(request):
    categories = Category.objects.all().order_by('id')   # ⬅ ID tăng dần
    # categories = Category.objects.all().order_by('-id')  # ⬅ ID giảm dần (nếu muốn ngược lại)

    context = {
        "categories": categories,
    }
    return render(request, "store/staff_category_list.html", context)



@login_required(login_url="login")
def staff_category_add(request):
    if not request.user.is_staff:
        return redirect("dashboard")

    if request.method == "POST":
        Category.objects.create(
            category_name=request.POST.get("name"),
            slug=request.POST.get("slug"),
        )
        messages.success(request, "Đã thêm danh mục.")
        return redirect("staff_category_list")

    return render(request, "store/staff_category_form.html")


@login_required(login_url="login")
def staff_category_edit(request, id):
    if not request.user.is_staff:
        return redirect("dashboard")

    category = get_object_or_404(Category, id=id)

    if request.method == "POST":
        category.category_name = request.POST.get("name")
        category.slug = request.POST.get("slug")
        category.save()
        messages.success(request, "Đã cập nhật danh mục.")
        return redirect("staff_category_list")

    return render(request, "store/staff_category_form.html", {"category": category})


@login_required(login_url="login")
def staff_category_delete(request, id):
    if not request.user.is_staff:
        return redirect("dashboard")

    category = get_object_or_404(Category, id=id)
    category.delete()
    messages.success(request, "Đã xoá danh mục.")
    return redirect("staff_category_list")

def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)

    # Lấy color + size từ POST
    color = request.POST.get("color")
    size = request.POST.get("size")

    # Tìm combo phù hợp
    try:
        variant = ProductVariant.objects.get(
            product=product,
            color=color,
            size=size
        )
    except ProductVariant.DoesNotExist:
        messages.error(request, "Biến thể không tồn tại.")
        return redirect(request.META.get("HTTP_REFERER"))

    # Lấy hoặc tạo cart session
    try:
        cart = carts.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
        cart.save()

    # Kiểm tra xem biến thể này đã có trong giỏ chưa
    try:
        cart_item = CartItem.objects.get(
            product=product,
            variant=variant,
            cart=cart
        )
        # Tăng số lượng nếu còn hàng
        if cart_item.quantity < variant.stock:
            cart_item.quantity += 1
        else:
            messages.warning(request, "Không đủ hàng tồn kho.")
            return redirect(request.META.get("HTTP_REFERER"))
    except CartItem.DoesNotExist:
        cart_item = CartItem.objects.create(
            product=product,
            variant=variant,
            cart=cart,
            quantity=1
        )

    cart_item.save()
    return redirect("cart")
