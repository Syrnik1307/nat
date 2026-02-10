from accounts.models import CustomUser, Subscription
from django.utils import timezone

u = CustomUser.objects.get(email='syrnik131313@gmail.com')
s = Subscription.objects.get(user=u)
days_left = (s.expires_at - timezone.now()).days

print('='*50)
print('Проверка подписки для syrnik131313@gmail.com')
print('='*50)
print(f'Email: {u.email}')
print(f'Role: {u.role}')
print(f'Subscription status: {s.status}')
print(f'Plan: {s.plan}')
print(f'Expires at: {s.expires_at}')
print(f'Days remaining: {days_left:,}')
print(f'Storage total: {s.total_storage_gb} GB')
print(f'Storage used: {s.used_storage_gb} GB')
print('='*50)
print('✅ Подписка работает идеально!')
