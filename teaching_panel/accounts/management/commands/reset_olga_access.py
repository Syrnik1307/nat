from django.core.management.base import BaseCommand, CommandError

from accounts.models import CustomUser
from tenants.models import TenantMembership


class Command(BaseCommand):
    help = (
        "Сброс доступа для пользователя Ольги: активирует пользователя, "
        "обновляет пароль и показывает membership в тенантах."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            default='olga@olgaflowers.ru',
            help='Email пользователя (по умолчанию: olga@olgaflowers.ru)',
        )
        parser.add_argument(
            '--password',
            default='Test12345!',
            help='Новый пароль (по умолчанию: Test12345!)',
        )
        parser.add_argument(
            '--tenant',
            default='olga',
            help='Slug целевого тенанта для проверки membership (по умолчанию: olga)',
        )

    def handle(self, *args, **options):
        email = options['email'].strip().lower()
        password = options['password']
        tenant_slug = options['tenant'].strip().lower()

        user = CustomUser.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f'Пользователь с email {email} не найден')

        user.email = email
        user.is_active = True
        user.set_password(password)
        user.save(update_fields=['email', 'is_active', 'password'])

        memberships = list(
            TenantMembership.objects.filter(user=user, is_active=True)
            .select_related('tenant')
            .values_list('tenant__slug', 'role')
        )
        has_target_tenant = any(slug == tenant_slug for slug, _ in memberships)

        self.stdout.write(self.style.SUCCESS('[OK] Доступ пользователя обновлён'))
        self.stdout.write(f'Email: {user.email}')
        self.stdout.write('is_active: True')
        self.stdout.write(f'Пароль установлен: {password}')
        self.stdout.write(f'Роль пользователя: {user.role}')

        if memberships:
            self.stdout.write('Активные membership:')
            for slug, role in memberships:
                self.stdout.write(f'  - tenant={slug}, role={role}')
        else:
            self.stdout.write(self.style.WARNING('[WARN] Нет активных membership'))

        if not has_target_tenant:
            self.stdout.write(
                self.style.WARNING(
                    f'[WARN] Пользователь не состоит в тенанте {tenant_slug}. '
                    'Нужно добавить membership вручную.'
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS(f'[OK] Membership в тенанте {tenant_slug} найден'))
