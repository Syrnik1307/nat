#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teaching_panel.settings')
sys.path.insert(0, '/var/www/teaching_panel/teaching_panel')
django.setup()

from market.models import MarketOrder

print('=== All MarketOrders ===')
orders = MarketOrder.objects.all().order_by('-created_at')[:20]
for o in orders:
    paid = o.paid_at.strftime('%Y-%m-%d %H:%M') if o.paid_at else 'NULL'
    print(f'Order #{o.id} | status: {o.status:12} | paid_at: {paid} | user: {o.user.email} | product: {o.product.title}')
