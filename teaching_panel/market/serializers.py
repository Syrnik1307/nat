"""
Market API serializers.
"""
from rest_framework import serializers
from .models import Product, MarketOrder


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product listing."""
    
    class Meta:
        model = Product
        fields = [
            'id', 'title', 'description', 'price', 'product_type',
            'icon', 'is_active'
        ]
        read_only_fields = fields


class MarketOrderSerializer(serializers.ModelSerializer):
    """Serializer for MarketOrder display."""
    
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_type = serializers.CharField(source='product.product_type', read_only=True)
    
    class Meta:
        model = MarketOrder
        fields = [
            'id', 'product', 'product_title', 'product_type',
            'status', 'total_amount', 'created_at', 'paid_at', 'completed_at'
        ]
        read_only_fields = fields


class CreateZoomOrderSerializer(serializers.Serializer):
    """Serializer for creating a Zoom order."""
    
    product_id = serializers.IntegerField(
        help_text='ID товара (Zoom)'
    )
    is_new_account = serializers.BooleanField(
        help_text='True = создать новый аккаунт, False = оплатить существующий'
    )
    zoom_email = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Email/логин для Zoom аккаунта'
    )
    zoom_password = serializers.CharField(
        max_length=100,
        help_text='Пароль Zoom аккаунта'
    )
    contact_info = serializers.CharField(
        max_length=255,
        help_text='Telegram или номер телефона для связи'
    )
    auto_connect = serializers.BooleanField(
        default=False,
        help_text='Автоматически подключить к платформе Lectio Space'
    )
    random_email = serializers.BooleanField(
        default=False,
        help_text='Сгенерировать случайный email (только для нового аккаунта)'
    )
    
    def validate(self, data):
        """Validate Zoom order data."""
        is_new = data.get('is_new_account', False)
        zoom_email = data.get('zoom_email', '')
        random_email = data.get('random_email', False)
        
        # For new account: either provide email or request random
        if is_new and not zoom_email and not random_email:
            raise serializers.ValidationError({
                'zoom_email': 'Укажите email или выберите "Сгенерировать случайный"'
            })
        
        # Validate password (Zoom requirements: 8+ chars, at least one letter and number)
        password = data.get('zoom_password', '')
        if len(password) < 8:
            raise serializers.ValidationError({
                'zoom_password': 'Пароль должен содержать минимум 8 символов'
            })
        if not any(c.isalpha() for c in password):
            raise serializers.ValidationError({
                'zoom_password': 'Пароль должен содержать хотя бы одну букву'
            })
        if not any(c.isdigit() for c in password):
            raise serializers.ValidationError({
                'zoom_password': 'Пароль должен содержать хотя бы одну цифру'
            })
        
        # Validate contact info
        contact = data.get('contact_info', '').strip()
        if not contact:
            raise serializers.ValidationError({
                'contact_info': 'Укажите Telegram или номер телефона'
            })
        
        return data
