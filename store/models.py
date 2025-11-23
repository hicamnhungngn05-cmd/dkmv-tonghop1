from django.db import models
from category.models import Category
from django.urls import reverse
from django.db.models import Sum   # 👈 THÊM IMPORT NÀY


class Product(models.Model):
    product_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    price = models.IntegerField()
    images = models.ImageField(upload_to='photos/products')
    stock = models.IntegerField()
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)

    def get_url(self):
        return reverse('product_detail', args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

    def total_stock(self):
        from .models import ProductVariant
        variants = ProductVariant.objects.filter(product=self)
        return sum(v.stock for v in variants)


class Variation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variation_category = models.CharField(max_length=50, choices=[
        ('color', 'color'),
        ('size', 'size'),
    ])
    variation_value = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.variation_value


class ProductVariant(models.Model):
    """Tạm thời KHÔNG dùng. Có thể xoá trong tương lai nếu muốn clean DB."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )
    color = models.CharField(max_length=50, blank=True)
    size = models.CharField(max_length=50, blank=True)
    stock = models.IntegerField(default=0)

    class Meta:
        unique_together = ("product", "color", "size")

    def __str__(self):
        return f"{self.product.product_name} - {self.color} / {self.size}"


class VariationCombination(models.Model):
    """
    SKU thật sự: mỗi dòng là 1 combo MÀU + SIZE của 1 sản phẩm,
    có tồn kho riêng.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    color = models.ForeignKey(
        Variation,
        on_delete=models.CASCADE,
        related_name='combo_color',
    )
    size = models.ForeignKey(
        Variation,
        on_delete=models.CASCADE,
        related_name='combo_size',
    )
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.product.product_name} - {self.color.variation_value} / {self.size.variation_value}"

    # 🔁 Mỗi lần lưu / xoá 1 combo → cập nhật lại Product.stock = tổng stock các combo
    def _recalculate_product_stock(self, product=None):
        if product is None:
            product = self.product
        total = VariationCombination.objects.filter(product=product).aggregate(
            total=Sum('stock')
        )['total'] or 0
        product.stock = total
        product.save(update_fields=['stock'])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._recalculate_product_stock()

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        self._recalculate_product_stock(product)
