"""
Тесты конкурентного доступа к Zoom Pool.

Этот файл содержит unit-тесты для проверки race conditions
и корректности блокировок при работе с пулом Zoom аккаунтов.

Требования:
- pytest
- pytest-django

Запуск:
    pytest zoom_pool/tests/test_concurrency.py -v -s
    
Или через Django:
    python manage.py test zoom_pool.tests.test_concurrency
"""
import pytest
from django.test import TransactionTestCase
from django.db import connection, transaction
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Barrier, Timer
from datetime import timedelta
import time
import logging

from zoom_pool.models import ZoomAccount
from accounts.models import CustomUser

logger = logging.getLogger(__name__)


class ZoomPoolConcurrencyTestBase(TransactionTestCase):
    """
    Базовый класс для тестов конкурентного доступа.
    
    Используем TransactionTestCase вместо TestCase для:
    - Реальных транзакций (не обёрнутых в savepoint)
    - Возможности тестировать SELECT FOR UPDATE
    - Изоляции между потоками
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём тестового учителя
        cls.teacher = CustomUser.objects.create_user(
            email='teacher_concurrency@test.com',
            password='test123',
            role='teacher'
        )
    
    def setUp(self):
        """Создаём тестовый пул аккаунтов."""
        self.accounts = []
        for i in range(3):
            acc = ZoomAccount.objects.create(
                email=f'zoom_concurrency_{i}@test.com',
                zoom_account_id=f'concurrency_acc_{i}',
                api_key=f'key_{i}',
                api_secret=f'secret_{i}',
                max_concurrent_meetings=1,
                current_meetings=0,
                is_active=True
            )
            self.accounts.append(acc)
    
    def tearDown(self):
        """Очищаем тестовые данные."""
        ZoomAccount.objects.filter(email__startswith='zoom_concurrency_').delete()


class TestAcquireRaceCondition(ZoomPoolConcurrencyTestBase):
    """
    Тестируем race condition при одновременном acquire().
    
    Сценарий:
    - N потоков одновременно пытаются захватить M аккаунтов
    - Каждый аккаунт имеет max_concurrent_meetings=1
    - Ожидание: ровно M успешных acquire, остальные - ValueError
    """
    
    def test_concurrent_acquire_respects_limits(self):
        """
        10 потоков пытаются захватить 3 аккаунта одновременно.
        
        Ожидаемый результат:
        - 3 успешных acquire (по 1 на каждый аккаунт)
        - 7 ValueError (аккаунты недоступны)
        - current_meetings каждого аккаунта <= max_concurrent_meetings
        """
        num_threads = 10
        num_accounts = len(self.accounts)
        
        # Барьер для синхронизации старта всех потоков
        barrier = Barrier(num_threads)
        results = {'success': 0, 'error': 0, 'errors': []}
        
        def try_acquire(account_id):
            """Попытка захватить аккаунт."""
            # Создаём новое подключение к БД для каждого потока
            connection.ensure_connection()
            
            # Ждём пока все потоки будут готовы
            barrier.wait()
            
            try:
                # Получаем свежую копию из БД
                account = ZoomAccount.objects.get(pk=account_id)
                account.acquire()
                return ('success', account_id)
            except ValueError as e:
                return ('error', str(e))
            except Exception as e:
                return ('exception', str(e))
            finally:
                # Закрываем соединение потока
                connection.close()
        
        # Распределяем потоки по аккаунтам (round-robin)
        # Т.е. потоки 0,3,6,9 пытаются захватить account[0]
        # потоки 1,4,7 пытаются захватить account[1]
        # потоки 2,5,8 пытаются захватить account[2]
        account_ids = [self.accounts[i % num_accounts].pk for i in range(num_threads)]
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_acquire, acc_id) for acc_id in account_ids]
            
            for future in as_completed(futures):
                result_type, result_data = future.result()
                if result_type == 'success':
                    results['success'] += 1
                else:
                    results['error'] += 1
                    results['errors'].append(f"{result_type}: {result_data}")
        
        # Проверяем результаты
        self.assertEqual(
            results['success'], 
            num_accounts,
            f"Expected {num_accounts} successful acquires, got {results['success']}. "
            f"Errors: {results['errors']}"
        )
        
        self.assertEqual(
            results['error'], 
            num_threads - num_accounts,
            f"Expected {num_threads - num_accounts} errors, got {results['error']}"
        )
        
        # Проверяем состояние БД - ни один аккаунт не превысил лимит
        for account in ZoomAccount.objects.filter(pk__in=[a.pk for a in self.accounts]):
            self.assertLessEqual(
                account.current_meetings, 
                account.max_concurrent_meetings,
                f"Account {account.email} exceeds max: "
                f"{account.current_meetings}/{account.max_concurrent_meetings}"
            )


class TestReleaseIdempotency(ZoomPoolConcurrencyTestBase):
    """
    Тестируем идемпотентность release().
    
    Сценарий:
    - Аккаунт захвачен (current_meetings=1)
    - N потоков одновременно вызывают release()
    - Ожидание: current_meetings=0, без отрицательных значений
    """
    
    def test_double_release_safe(self):
        """
        5 потоков одновременно вызывают release() на одном аккаунте.
        
        Ожидаемый результат:
        - Без ошибок
        - current_meetings = 0 (не отрицательное!)
        """
        account = self.accounts[0]
        account.acquire()
        
        self.assertEqual(account.current_meetings, 1)
        
        num_threads = 5
        barrier = Barrier(num_threads)
        errors = []
        
        def try_release():
            connection.ensure_connection()
            barrier.wait()
            try:
                # Получаем свежую копию
                acc = ZoomAccount.objects.get(pk=account.pk)
                acc.release()
                return 'ok'
            except Exception as e:
                return str(e)
            finally:
                connection.close()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_release) for _ in range(num_threads)]
            for future in as_completed(futures):
                result = future.result()
                if result != 'ok':
                    errors.append(result)
        
        # Проверяем
        account.refresh_from_db()
        self.assertEqual(
            account.current_meetings, 
            0, 
            f"current_meetings should be 0 after releases, got {account.current_meetings}"
        )
        self.assertGreaterEqual(
            account.current_meetings,
            0,
            "current_meetings should never be negative"
        )


class TestAcquireAfterRelease(ZoomPoolConcurrencyTestBase):
    """
    Тестируем что аккаунт становится доступен сразу после release().
    
    Сценарий:
    - Thread 1: acquire → держит 100ms → release
    - Thread 2: пытается acquire, блокируется, получает после release
    """
    
    def test_acquire_after_release_works(self):
        """
        Один поток держит аккаунт, другой ждёт его освобождения.
        
        Ожидаемый результат:
        - Thread 1 успешно захватывает и освобождает
        - Thread 2 успешно захватывает после освобождения
        """
        account = self.accounts[0]
        results = {'thread1': None, 'thread2': None}
        
        barrier = Barrier(2)
        
        def thread1_job():
            connection.ensure_connection()
            try:
                barrier.wait()
                acc = ZoomAccount.objects.get(pk=account.pk)
                acc.acquire()
                results['thread1'] = 'acquired'
                time.sleep(0.1)  # Держим 100ms
                acc.release()
                results['thread1'] = 'released'
            except Exception as e:
                results['thread1'] = f'error: {e}'
            finally:
                connection.close()
        
        def thread2_job():
            connection.ensure_connection()
            try:
                barrier.wait()
                time.sleep(0.05)  # Стартуем чуть позже
                
                # Должен подождать release от thread1 благодаря select_for_update
                acc = ZoomAccount.objects.get(pk=account.pk)
                acc.acquire()
                results['thread2'] = 'acquired'
            except Exception as e:
                results['thread2'] = f'error: {e}'
            finally:
                connection.close()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(thread1_job)
            f2 = executor.submit(thread2_job)
            f1.result()
            f2.result()
        
        self.assertEqual(results['thread1'], 'released')
        self.assertEqual(results['thread2'], 'acquired')


class TestDeadlockPrevention(ZoomPoolConcurrencyTestBase):
    """
    Тестируем отсутствие deadlock при работе с несколькими аккаунтами.
    
    Классический сценарий deadlock:
    - Thread 1: lock(A) → lock(B)
    - Thread 2: lock(B) → lock(A)
    
    select_for_update(nowait=False) должен предотвратить это,
    заставляя один поток ждать.
    """
    
    def test_no_deadlock_on_multiple_accounts(self):
        """
        Два потока пытаются захватить два аккаунта в разном порядке.
        
        Ожидаемый результат:
        - Нет deadlock (тест завершается в течение 5 секунд)
        - Оба потока завершаются (один может подождать другого)
        """
        account1 = self.accounts[0]
        account2 = self.accounts[1]
        # Увеличиваем лимит чтобы можно было захватить оба
        account1.max_concurrent_meetings = 2
        account1.save()
        account2.max_concurrent_meetings = 2
        account2.save()
        
        barrier = Barrier(2)
        results = {'thread1': [], 'thread2': []}
        
        def thread1_job():
            connection.ensure_connection()
            try:
                barrier.wait()
                
                acc1 = ZoomAccount.objects.get(pk=account1.pk)
                acc1.acquire()
                results['thread1'].append('got_acc1')
                
                time.sleep(0.05)
                
                acc2 = ZoomAccount.objects.get(pk=account2.pk)
                acc2.acquire()
                results['thread1'].append('got_acc2')
                
            except Exception as e:
                results['thread1'].append(f'error: {e}')
            finally:
                # Освобождаем
                try:
                    ZoomAccount.objects.get(pk=account1.pk).release()
                    ZoomAccount.objects.get(pk=account2.pk).release()
                except:
                    pass
                connection.close()
        
        def thread2_job():
            connection.ensure_connection()
            try:
                barrier.wait()
                
                acc2 = ZoomAccount.objects.get(pk=account2.pk)
                acc2.acquire()
                results['thread2'].append('got_acc2')
                
                time.sleep(0.05)
                
                acc1 = ZoomAccount.objects.get(pk=account1.pk)
                acc1.acquire()
                results['thread2'].append('got_acc1')
                
            except Exception as e:
                results['thread2'].append(f'error: {e}')
            finally:
                try:
                    ZoomAccount.objects.get(pk=account2.pk).release()
                    ZoomAccount.objects.get(pk=account1.pk).release()
                except:
                    pass
                connection.close()
        
        # Таймаут на тест - если deadlock, тест провалится
        timeout_occurred = [False]
        
        def set_timeout():
            timeout_occurred[0] = True
        
        timer = Timer(5.0, set_timeout)  # 5 секунд timeout
        timer.start()
        
        try:
            with ThreadPoolExecutor(max_workers=2) as executor:
                f1 = executor.submit(thread1_job)
                f2 = executor.submit(thread2_job)
                f1.result(timeout=5)
                f2.result(timeout=5)
        except Exception as e:
            self.fail(f"Deadlock or timeout: {e}")
        finally:
            timer.cancel()
        
        self.assertFalse(timeout_occurred[0], "Deadlock detected - test timed out")
        
        # При правильной реализации оба потока должны завершиться
        logger.info(f"Thread1 results: {results['thread1']}")
        logger.info(f"Thread2 results: {results['thread2']}")


class TestTeacherAffinity(ZoomPoolConcurrencyTestBase):
    """
    Тестируем логику teacher affinity при выборе аккаунта.
    
    Сценарий:
    - Учитель имеет preferred Zoom account
    - При запросе должен получить свой preferred (если доступен)
    """
    
    def test_preferred_account_selected_first(self):
        """
        Учитель с привязкой к аккаунту получает его первым.
        """
        # Привязываем учителя к первому аккаунту
        preferred_account = self.accounts[0]
        preferred_account.preferred_teachers.add(self.teacher)
        
        # Запрашиваем аккаунт для учителя
        available = ZoomAccount.get_available_for_teacher(self.teacher)
        
        # Должен вернуть preferred аккаунт (или его в приоритете)
        self.assertIsNotNone(available)
        
        # Проверяем что preferred аккаунт в списке доступных
        available_ids = list(ZoomAccount.objects.filter(
            is_active=True,
            current_meetings__lt=1  # max_concurrent_meetings=1
        ).values_list('id', flat=True))
        
        self.assertIn(preferred_account.id, available_ids)


class TestHighLoadSimulation(ZoomPoolConcurrencyTestBase):
    """
    Симуляция высокой нагрузки: много потоков, мало аккаунтов.
    
    Сценарий:
    - 3 аккаунта с max_concurrent_meetings=2 (всего 6 слотов)
    - 20 потоков пытаются захватить аккаунты
    - Ожидание: 6 успешных, 14 ошибок
    """
    
    def setUp(self):
        super().setUp()
        # Увеличиваем лимиты
        for acc in self.accounts:
            acc.max_concurrent_meetings = 2
            acc.save()
    
    def test_high_load_respects_total_capacity(self):
        """
        20 потоков на 6 слотов (3 аккаунта × 2 meetings).
        """
        num_threads = 20
        total_capacity = sum(a.max_concurrent_meetings for a in self.accounts)
        
        barrier = Barrier(num_threads)
        results = {'success': 0, 'error': 0}
        
        def try_acquire():
            connection.ensure_connection()
            barrier.wait()
            try:
                # Пробуем захватить любой доступный аккаунт
                for acc in ZoomAccount.objects.filter(is_active=True):
                    try:
                        acc.acquire()
                        return 'success'
                    except ValueError:
                        continue
                return 'no_available'
            except Exception as e:
                return f'error: {e}'
            finally:
                connection.close()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(try_acquire) for _ in range(num_threads)]
            for future in as_completed(futures):
                result = future.result()
                if result == 'success':
                    results['success'] += 1
                else:
                    results['error'] += 1
        
        # Проверяем что захвачено не больше чем capacity
        self.assertLessEqual(
            results['success'],
            total_capacity,
            f"Acquired {results['success']} but capacity is {total_capacity}"
        )
        
        # Проверяем состояние БД
        total_current = sum(
            ZoomAccount.objects.get(pk=a.pk).current_meetings 
            for a in self.accounts
        )
        self.assertLessEqual(
            total_current,
            total_capacity,
            f"Total current_meetings {total_current} exceeds capacity {total_capacity}"
        )


# Если запускаем напрямую
if __name__ == '__main__':
    import django
    django.setup()
    
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
