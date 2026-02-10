from accounts.models import CustomUser, Subscription
from django.utils import timezone
from datetime import datetime

user = CustomUser.objects.get(email='syrnik131313@gmail.com')
sub, created = Subscription.objects.get_or_create(user=user)
sub.status = 'active'
sub.expires_at = timezone.make_aware(datetime(2099, 12, 31, 23, 59, 59))
sub.plan = 'lifetime'
sub.base_storage_gb = 1000
sub.extra_storage_gb = 0
sub.save()
print(f'✅ Подписка обновлена для {user.email}')
print(f'   Статус: {sub.status}')
print(f'   Истекает: {sub.expires_at}')
print(f'   План: {sub.plan}')
print(f'   Хранилище: {sub.total_storage_gb} GB')
print(f'   Создана новая: {created}')
