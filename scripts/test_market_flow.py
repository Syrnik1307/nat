#!/usr/bin/env python
"""
Test script for Market module flow.
Emulates the full order creation and payment process.

Usage:
    cd teaching_panel
    python ../scripts/test_market_flow.py
"""
import os
import sys
import django

# Setup Django
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
teaching_panel_dir = os.path.join(project_root, 'teaching_panel')

sys.path.insert(0, teaching_panel_dir)
os.chdir(teaching_panel_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from market.models import Product, MarketOrder

User = get_user_model()


def create_test_product():
    """Create or get test Zoom product."""
    product, created = Product.objects.get_or_create(
        product_type=Product.TYPE_ZOOM,
        defaults={
            'title': 'Zoom Pro (1 месяц)',
            'description': 'Профессиональный аккаунт Zoom с неограниченным временем конференций, записью в облако и другими Pro-функциями.',
            'price': Decimal('990.00'),
            'is_active': True,
            'icon': 'zoom',
            'sort_order': 1,
        }
    )
    if created:
        print(f"[OK] Created product: {product}")
    else:
        print(f"[OK] Product already exists: {product}")
    return product


def create_test_order(user, product):
    """Create a test order for a user."""
    order = MarketOrder.objects.create(
        user=user,
        product=product,
        status=MarketOrder.STATUS_PENDING,
        total_amount=product.price,
        payment_id=f'test-{user.id}-{product.id}',
        order_details={
            'zoom_email': 'test@example.com',
            'zoom_password': 'TestPass123',
            'contact_info': '@test_telegram',
            'is_new_account': True,
            'auto_connect': True,
        }
    )
    print(f"[OK] Created order: {order}")
    return order


def simulate_payment_confirmation(order):
    """Simulate webhook payment confirmation."""
    from django.utils import timezone
    
    order.status = MarketOrder.STATUS_PAID
    order.paid_at = timezone.now()
    order.save()
    
    print(f"[OK] Order #{order.id} marked as PAID")
    
    # Test admin notification
    from accounts.notifications import send_telegram_admin_alert
    
    account_type = 'Новый' if order.is_new_account else 'Существующий'
    auto_connect = 'ДА' if order.auto_connect else 'НЕТ'
    
    message = f"""💰 МАРКЕТ: ТЕСТОВАЯ ОПЛАТА

Юзер: {order.user.email}
Товар: {order.product.title}
Сумма: {order.total_amount} ₽

Тип: {account_type}
Логин: {order.zoom_email or '-'}
Пароль: {order.zoom_password or '-'}
Контакты: {order.contact_info or '-'}
Авто-подключение к платформе: {auto_connect}

Заказ #{order.id} (ТЕСТ)"""
    
    result = send_telegram_admin_alert(message)
    if result:
        print("[OK] Telegram admin notification sent")
    else:
        print("[WARN] Telegram notification not sent (bot not configured)")


def test_api_endpoints():
    """Test API endpoints."""
    from rest_framework.test import APIClient
    
    # Get or create test user
    user, _ = User.objects.get_or_create(
        email='market_test@example.com',
        defaults={
            'first_name': 'Market',
            'last_name': 'Test',
            'role': 'teacher',
            'is_active': True,
        }
    )
    if not user.has_usable_password():
        user.set_password('TestPass123!')
        user.save()
    
    print(f"[OK] Test user: {user.email}")
    
    client = APIClient()
    client.force_authenticate(user=user)
    
    # Test products endpoint
    response = client.get('/api/market/products/')
    print(f"[OK] GET /api/market/products/ - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"     Products count: {len(response.data)}")
    
    # Test my-orders endpoint
    response = client.get('/api/market/my-orders/')
    print(f"[OK] GET /api/market/my-orders/ - Status: {response.status_code}")
    if response.status_code == 200:
        print(f"     Orders count: {len(response.data)}")
    
    # Test buy endpoint (validation)
    response = client.post('/api/market/buy/', {
        'product_id': 999,
        'is_new_account': True,
        'zoom_password': 'short',
        'contact_info': '',
    })
    print(f"[OK] POST /api/market/buy/ (invalid) - Status: {response.status_code}")
    if response.status_code == 400:
        print(f"     Validation works correctly")


def cleanup_test_data():
    """Remove test data."""
    MarketOrder.objects.filter(payment_id__startswith='test-').delete()
    print("[OK] Test orders cleaned up")


def main():
    print("=" * 60)
    print("Market Module Test Script")
    print("=" * 60)
    print()
    
    # 1. Create test product
    print("1. Creating test product...")
    product = create_test_product()
    print()
    
    # 2. Test API endpoints
    print("2. Testing API endpoints...")
    test_api_endpoints()
    print()
    
    # 3. Create test order
    print("3. Creating test order...")
    user = User.objects.filter(email='market_test@example.com').first()
    if user:
        order = create_test_order(user, product)
        print()
        
        # 4. Simulate payment
        print("4. Simulating payment confirmation...")
        simulate_payment_confirmation(order)
        print()
        
        # 5. Cleanup
        print("5. Cleaning up test data...")
        cleanup_test_data()
    print()
    
    print("=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
