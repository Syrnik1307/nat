"""
DRF serializers for finance API.
"""
from decimal import Decimal
from rest_framework import serializers
from .models import StudentFinancialProfile, Transaction, TransactionType


class TransactionSerializer(serializers.ModelSerializer):
    """Сериализатор транзакции (только чтение)."""
    
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display',
        read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True,
        default=''
    )
    lesson_title = serializers.CharField(
        source='lesson.display_name',
        read_only=True,
        default=None
    )
    lesson_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'amount',
            'transaction_type',
            'transaction_type_display',
            'lesson',
            'lesson_title',
            'lesson_date',
            'is_group_lesson',
            'override_price',
            'description',
            'created_by',
            'created_by_name',
            'auto_created',
            'created_at',
        ]
        read_only_fields = fields
    
    def get_lesson_date(self, obj):
        if obj.lesson:
            return obj.lesson.start_time.isoformat()
        return None


class WalletSerializer(serializers.ModelSerializer):
    """Полный сериализатор кошелька для учителя."""
    
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    lessons_left = serializers.FloatField(read_only=True)
    is_debtor = serializers.BooleanField(read_only=True)
    debt_limit_exceeded = serializers.BooleanField(read_only=True)
    balance_status = serializers.CharField(read_only=True)
    
    # История транзакций (последние 50)
    recent_transactions = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentFinancialProfile
        fields = [
            'id',
            'student',
            'student_id',
            'student_name',
            'student_email',
            'teacher',
            'balance',
            'default_lesson_price',
            'currency',
            'debt_limit',
            'lessons_left',
            'is_debtor',
            'debt_limit_exceeded',
            'balance_status',
            'notes',
            'recent_transactions',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'student', 'teacher', 'balance',
            'created_at', 'updated_at'
        ]
    
    def get_recent_transactions(self, obj):
        txns = obj.transactions.all()[:50]
        return TransactionSerializer(txns, many=True).data


class WalletListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор для списка кошельков."""
    
    student_id = serializers.IntegerField(source='student.id', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    lessons_left = serializers.FloatField(read_only=True)
    is_debtor = serializers.BooleanField(read_only=True)
    balance_status = serializers.CharField(read_only=True)
    group_names = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentFinancialProfile
        fields = [
            'id',
            'student_id',
            'student_name',
            'student_email',
            'balance',
            'default_lesson_price',
            'debt_limit',
            'currency',
            'lessons_left',
            'is_debtor',
            'balance_status',
            'group_names',
        ]
    
    def get_group_names(self, obj):
        """Возвращает список названий групп, в которых состоит ученик у этого учителя."""
        from schedule.models import Group
        groups = Group.objects.filter(
            teacher=obj.teacher,
            students=obj.student
        ).values_list('name', flat=True)
        return list(groups)


class WalletCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания кошелька."""
    
    class Meta:
        model = StudentFinancialProfile
        fields = ['student', 'default_lesson_price', 'debt_limit', 'notes']
    
    def validate_default_lesson_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value
    
    def validate_debt_limit(self, value):
        if value < 0:
            raise serializers.ValidationError('Лимит долга не может быть отрицательным')
        return value


class WalletUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления кошелька (только редактируемые поля)."""
    
    class Meta:
        model = StudentFinancialProfile
        fields = ['default_lesson_price', 'debt_limit', 'notes']
    
    def validate_default_lesson_price(self, value):
        if value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value
    
    def validate_debt_limit(self, value):
        if value < 0:
            raise serializers.ValidationError('Лимит долга не может быть отрицательным')
        return value


# ============ Сериализаторы для действий ============

class DepositSerializer(serializers.Serializer):
    """Сериализатор для внесения оплаты."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Сумма должна быть положительной')
        return value


class ChargeSerializer(serializers.Serializer):
    """Сериализатор для ручного списания за урок."""
    lesson_id = serializers.IntegerField()
    override_price = serializers.DecimalField(
        max_digits=8, decimal_places=2,
        required=False, allow_null=True, default=None
    )
    description = serializers.CharField(required=False, allow_blank=True, default='')
    
    def validate_override_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Цена не может быть отрицательной')
        return value


class AdjustSerializer(serializers.Serializer):
    """Сериализатор для корректировки баланса."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(min_length=3)
    
    def validate_amount(self, value):
        if value == 0:
            raise serializers.ValidationError('Сумма не может быть нулевой')
        return value


class RefundSerializer(serializers.Serializer):
    """Сериализатор для возврата за урок."""
    lesson_id = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True, default='')


# ============ Сериализаторы для ученика ============

class StudentBalanceSerializer(serializers.ModelSerializer):
    """
    Сериализатор баланса для ученика.
    
    Показывает только остаток уроков и статус, без детальной истории.
    У ученика может быть несколько учителей — возвращается список.
    """
    teacher_id = serializers.IntegerField(source='teacher.id', read_only=True)
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    lessons_remaining = serializers.FloatField(source='lessons_left', read_only=True)
    balance_status = serializers.CharField(read_only=True)
    
    class Meta:
        model = StudentFinancialProfile
        fields = [
            'teacher_id',
            'teacher_name',
            'lessons_remaining',
            'balance_status',
            'currency',
        ]
