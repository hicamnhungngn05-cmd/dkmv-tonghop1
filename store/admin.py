from django.contrib import admin
from .models import (
    Product,
    Variation,
    ProductVariant,        # nếu bạn còn giữ
    VariationCombination    # 👉 QUAN TRỌNG: thêm SKU combo màu+size
)

# ===========================
# PRODUCT
# ===========================
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'category', 'modified_date', 'is_available')
    prepopulated_fields = {'slug': ('product_name',)}


# ===========================
# VARIATION (màu, size)
# ===========================
@admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    list_display = ('product', 'variation_category', 'variation_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('product', 'variation_category', 'variation_value')


# ===========================
# PRODUCT VARIANT (cái cũ — nếu còn dùng)
# ===========================
@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "color", "size", "stock")
    list_filter = ("product", "color", "size")


# ===========================
# VARIATION COMBINATION (SKU thật)
# ===========================
@admin.register(VariationCombination)
class VariationCombinationAdmin(admin.ModelAdmin):
    list_display = ("product", "color", "size", "stock")
    list_filter = ("product", "color", "size")
    search_fields = ("product__product_name", "color__variation_value", "size__variation_value")
