"""
Market models for digital product sales.
Products: Zoom accounts, future services.
"""
from django.db import models
from django.conf import settings


class Product(models.Model):
    """Digital product available for purchase."""
    
    TYPE_ZOOM = 'zoom'
    TYPE_CHOICES = [
        (TYPE_ZOOM, 'Zoom аккаунт'),
    ]
    
    title = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена (RUB)', max_digits=10, decimal_places=2)
    product_type = models.CharField(
        'Тип продукта',
        max_length=50,
        choices=TYPE_CHOICES,
        default=TYPE_ZOOM
    )
    icon = models.CharField('Иконка (SVG или класс)', max_length=100, blank=True, default='')
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок сортировки', default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['sort_order', 'title']
    
    def __str__(self):
        return f"{self.title} - {self.price} ₽"


class MarketOrder(models.Model):
    """Order for a digital product."""
    
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает оплаты'),
        (STATUS_PAID, 'Оплачен'),
        (STATUS_COMPLETED, 'Выполнен'),
        (STATUS_CANCELLED, 'Отменен'),
        (STATUS_REFUNDED, 'Возврат'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='market_orders',
        verbose_name='Пользователь'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Товар'
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    total_amount = models.DecimalField('Сумма', max_digits=10, decimal_places=2)
    payment_id = models.CharField(
        'ID платежа (T-Bank)',
        max_length=100,
        blank=True,
        null=True
    )
    payment_url = models.URLField('URL оплаты', blank=True, null=True)
    
    # Flexible JSON field for product-specific data
    # For Zoom: zoom_email, zoom_password, contact_info, is_new_account, auto_connect
    order_details = models.JSONField(
        'Детали заказа',
        default=dict,
        blank=True,
        help_text='JSON с данными заказа (для Zoom: email, password, contact_info и т.д.)'
    )
    
    admin_notes = models.TextField('Заметки администратора', blank=True)
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    paid_at = models.DateTimeField('Дата оплаты', null=True, blank=True)
    completed_at = models.DateTimeField('Дата выполнения', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ #{self.id} - {self.product.title} ({self.get_status_display()})"
    
    @property
    def zoom_email(self):
        """Get Zoom email from order_details."""
        return self.order_details.get('zoom_email', '')
    
    @property
    def zoom_password(self):
        """Get Zoom password from order_details."""
        return self.order_details.get('zoom_password', '')
    
    @property
    def contact_info(self):
        """Get contact info from order_details."""
        return self.order_details.get('contact_info', '')
    
    @property
    def is_new_account(self):
        """Check if this is a new account order."""
        return self.order_details.get('is_new_account', False)
    
    @property
    def auto_connect(self):
        """Check if auto-connect to platform is requested."""
        return self.order_details.get('auto_connect', False)
