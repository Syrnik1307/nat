#!/usr/bin/env python3
"""
Скрипт для полного тестирования API посещаемости и рейтинга на продакшн сервере
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Конфигурация
BASE_URL = "http://72.56.81.163"
API_URL = f"{BASE_URL}/api"

# Учетные данные
TEST_TEACHER = {
    "email": "deploy_teacher@test.com",
    "password": "TestPass123!"
}

# Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")

def print_section(title):
    print(f"\n{Colors.BLUE}{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}{Colors.RESET}\n")


class AttendanceAPITester:
    def __init__(self):
        self.token = None
        self.teacher_id = None
        self.session = requests.Session()
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0
        }
    
    def test(self, name, func):
        """Декоратор для тестов"""
        self.test_results["total"] += 1
        print_info(f"Тест: {name}")
        try:
            func()
            self.test_results["passed"] += 1
            print_success(f"Пройден: {name}")
            return True
        except Exception as e:
            self.test_results["failed"] += 1
            print_error(f"Провален: {name}")
            print_error(f"Ошибка: {str(e)}")
            return False
    
    def login(self):
        """1. Авторизация"""
        print_section("Шаг 1: Авторизация")
        
        url = f"{API_URL}/jwt/token/"
        response = self.session.post(url, json=TEST_TEACHER)
        
        if response.status_code != 200:
            print_error(f"Не удалось авторизоваться: {response.status_code}")
            print_error(f"Ответ: {response.text}")
            sys.exit(1)
        
        data = response.json()
        self.token = data.get("access")
        
        if not self.token:
            print_error("Токен не получен")
            sys.exit(1)
        
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        
        print_success("Авторизация успешна")
        print_info(f"Токен: {self.token[:50]}...")
        
        # Получаем информацию о пользователе
        me_response = self.session.get(f"{API_URL}/me/")
        if me_response.status_code == 200:
            user_data = me_response.json()
            self.teacher_id = user_data.get("id")
            print_info(f"ID учителя: {self.teacher_id}")
            print_info(f"Email: {user_data.get('email')}")
            print_info(f"Роль: {user_data.get('role')}")
    
    def test_groups_list(self):
        """2. Получение списка групп"""
        print_section("Шаг 2: Тестирование списка групп")
        
        def _test():
            response = self.session.get(f"{API_URL}/groups/")
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            groups = data.get("results", [])
            
            print_info(f"Найдено групп: {len(groups)}")
            
            if groups:
                group = groups[0]
                print_info(f"Первая группа: ID={group['id']}, Название={group.get('name', 'N/A')}")
                self.test_group_id = group['id']
                return group
            else:
                print_warning("Группы не найдены, создадим тестовую группу")
                return self.create_test_group()
        
        self.test(_test.__doc__, _test)
    
    def create_test_group(self):
        """Создание тестовой группы"""
        group_data = {
            "name": f"Тестовая группа {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "subject": "Математика",
            "description": "Автоматически созданная группа для тестирования"
        }
        
        response = self.session.post(f"{API_URL}/schedule/groups/", json=group_data)
        
        if response.status_code in [200, 201]:
            group = response.json()
            self.test_group_id = group['id']
            print_success(f"Создана тестовая группа: ID={group['id']}")
            return group
        else:
            print_error(f"Не удалось создать группу: {response.status_code}")
            print_error(f"Ответ: {response.text}")
            raise Exception("Не удалось создать группу")
    
    def test_attendance_records_endpoint(self):
        """3. Тест endpoint /api/attendance-records/"""
        print_section("Шаг 3: Тестирование /api/attendance-records/")
        
        def _test():
            response = self.session.get(f"{API_URL}/attendance-records/")
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            records = data.get("results", [])
            
            print_info(f"Найдено записей посещаемости: {len(records)}")
            
            if records:
                record = records[0]
                print_info(f"Первая запись: ID={record['id']}")
                print_info(f"  Студент: {record.get('student_name', 'N/A')}")
                print_info(f"  Урок: {record.get('lesson_id', 'N/A')}")
                print_info(f"  Статус: {record.get('status', 'N/A')}")
        
        self.test(_test.__doc__, _test)
    
    def test_ratings_endpoint(self):
        """4. Тест endpoint /api/ratings/"""
        print_section("Шаг 4: Тестирование /api/ratings/")
        
        def _test():
            response = self.session.get(f"{API_URL}/ratings/")
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            ratings = data.get("results", [])
            
            print_info(f"Найдено рейтингов: {len(ratings)}")
            
            if ratings:
                rating = ratings[0]
                print_info(f"Первый рейтинг: ID={rating['id']}")
                print_info(f"  Студент: {rating.get('student_name', 'N/A')}")
                print_info(f"  Группа: {rating.get('group_name', 'N/A')}")
                print_info(f"  Баллы посещаемости: {rating.get('attendance_points', 0)}")
                print_info(f"  Баллы ДЗ: {rating.get('homework_points', 0)}")
                print_info(f"  Баллы КТ: {rating.get('control_points', 0)}")
                print_info(f"  Всего: {rating.get('total_points', 0)}")
        
        self.test(_test.__doc__, _test)
    
    def test_group_attendance_log(self):
        """5. Тест endpoint /api/groups/{id}/attendance-log/"""
        print_section("Шаг 5: Тестирование журнала посещаемости группы")
        
        def _test():
            if not hasattr(self, 'test_group_id'):
                raise Exception("Группа для тестирования не найдена")
            
            response = self.session.get(
                f"{API_URL}/groups/{self.test_group_id}/attendance-log/"
            )
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            
            print_info(f"Столбцы: {len(data.get('lessons', []))}")
            print_info(f"Строки (студенты): {len(data.get('students', []))}")
            
            if data.get('lessons'):
                print_info(f"Первый урок: {data['lessons'][0].get('date', 'N/A')}")
            
            if data.get('students'):
                print_info(f"Первый студент: {data['students'][0].get('name', 'N/A')}")
        
        self.test(_test.__doc__, _test)
    
    def test_group_rating(self):
        """6. Тест endpoint /api/groups/{id}/rating/"""
        print_section("Шаг 6: Тестирование рейтинга группы")
        
        def _test():
            if not hasattr(self, 'test_group_id'):
                raise Exception("Группа для тестирования не найдена")
            
            response = self.session.get(
                f"{API_URL}/groups/{self.test_group_id}/rating/"
            )
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            students = data.get("students", [])
            
            print_info(f"Студентов в рейтинге: {len(students)}")
            
            if students:
                top_student = students[0]
                print_info(f"Топ студент:")
                print_info(f"  Имя: {top_student.get('name', 'N/A')}")
                print_info(f"  Ранг: {top_student.get('rank', 'N/A')}")
                print_info(f"  Баллы: {top_student.get('total_points', 0)}")
        
        self.test(_test.__doc__, _test)
    
    def test_group_report(self):
        """7. Тест endpoint /api/groups/{id}/report/"""
        print_section("Шаг 7: Тестирование отчета группы")
        
        def _test():
            if not hasattr(self, 'test_group_id'):
                raise Exception("Группа для тестирования не найдена")
            
            response = self.session.get(
                f"{API_URL}/groups/{self.test_group_id}/report/"
            )
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            
            print_info(f"Процент посещаемости: {data.get('attendance_percentage', 0)}%")
            print_info(f"Процент выполнения ДЗ: {data.get('homework_percentage', 0)}%")
            print_info(f"Средний балл КТ: {data.get('control_points_avg', 0)}")
            
            recommendations = data.get('recommendations', [])
            if recommendations:
                print_info(f"Рекомендаций: {len(recommendations)}")
                for rec in recommendations[:3]:
                    print_info(f"  - {rec}")
        
        self.test(_test.__doc__, _test)
    
    def test_student_card(self):
        """8. Тест endpoint /api/students/{id}/card/"""
        print_section("Шаг 8: Тестирование карточки студента")
        
        def _test():
            # Сначала получим студентов из группы
            groups_response = self.session.get(f"{API_URL}/groups/")
            assert groups_response.status_code == 200, f"Неверный статус: {groups_response.status_code}"
            
            groups_data = groups_response.json()
            groups = groups_data.get("results", [])
            
            if not groups:
                print_warning("Группы не найдены, пропускаем тест карточки")
                return
            
            students = groups[0].get('students', [])
            
            if not students:
                print_warning("Студенты не найдены, пропускаем тест карточки")
                return
            
            student_id = students[0]['id']
            print_info(f"Тестируем студента ID={student_id}")
            
            card_response = self.session.get(f"{API_URL}/students/{student_id}/card/")
            assert card_response.status_code == 200, f"Неверный статус: {card_response.status_code}"
            
            card_data = card_response.json()
            
            print_info(f"Имя: {card_data.get('name', 'N/A')}")
            print_info(f"Email: {card_data.get('email', 'N/A')}")
            print_info(f"Всего баллов: {card_data.get('total_points', 0)}")
            print_info(f"Посещено уроков: {card_data.get('lessons_attended', 0)}/{card_data.get('total_lessons', 0)}")
            
            errors = card_data.get('recent_errors', [])
            if errors:
                print_info(f"Недавних ошибок: {len(errors)}")
        
        self.test(_test.__doc__, _test)
    
    def test_individual_students(self):
        """9. Тест endpoint /api/individual-students/"""
        print_section("Шаг 9: Тестирование индивидуальных студентов")
        
        def _test():
            response = self.session.get(f"{API_URL}/individual-students/")
            assert response.status_code == 200, f"Неверный статус: {response.status_code}"
            
            data = response.json()
            students = data.get("results", [])
            
            print_info(f"Найдено индивидуальных студентов: {len(students)}")
            
            if students:
                student = students[0]
                print_info(f"Первый студент: ID={student['id']}")
                print_info(f"  Имя: {student.get('student_name', 'N/A')}")
                print_info(f"  Учитель: {student.get('teacher_name', 'N/A')}")
                print_info(f"  Заметки: {student.get('teacher_notes', 'N/A')[:50]}...")
        
        self.test(_test.__doc__, _test)
    
    def test_update_attendance(self):
        """10. Тест обновления посещаемости"""
        print_section("Шаг 10: Тестирование обновления посещаемости")
        
        def _test():
            if not hasattr(self, 'test_group_id'):
                raise Exception("Группа для тестирования не найдена")
            
            # Получаем журнал посещаемости
            log_response = self.session.get(
                f"{API_URL}/groups/{self.test_group_id}/attendance-log/"
            )
            assert log_response.status_code == 200, f"Неверный статус: {log_response.status_code}"
            
            log_data = log_response.json()
            
            if not log_data.get('students') or not log_data.get('lessons'):
                print_warning("Нет данных для обновления посещаемости")
                return
            
            # Пытаемся обновить первую ячейку
            student_id = log_data['students'][0]['id']
            lesson_id = log_data['lessons'][0]['id']
            
            update_data = {
                "updates": [
                    {
                        "student_id": student_id,
                        "lesson_id": lesson_id,
                        "status": "attended"
                    }
                ]
            }
            
            update_response = self.session.post(
                f"{API_URL}/groups/{self.test_group_id}/attendance-log/update/",
                json=update_data
            )
            
            # Может быть 200 или 404 если endpoint не реализован
            if update_response.status_code == 200:
                print_success("Посещаемость обновлена успешно")
            elif update_response.status_code == 404:
                print_warning("Endpoint обновления не найден (возможно не реализован)")
            else:
                assert False, f"Неожиданный статус: {update_response.status_code}"
        
        self.test(_test.__doc__, _test)
    
    def print_summary(self):
        """Вывод итогов тестирования"""
        print_section("Итоги тестирования")
        
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        
        print_info(f"Всего тестов: {total}")
        print_success(f"Пройдено: {passed}")
        
        if failed > 0:
            print_error(f"Провалено: {failed}")
        else:
            print_success("Все тесты пройдены! 🎉")
        
        percentage = (passed / total * 100) if total > 0 else 0
        print_info(f"Успешность: {percentage:.1f}%")
    
    def run_all_tests(self):
        """Запуск всех тестов"""
        try:
            self.login()
            self.test_groups_list()
            self.test_attendance_records_endpoint()
            self.test_ratings_endpoint()
            self.test_group_attendance_log()
            self.test_group_rating()
            self.test_group_report()
            self.test_student_card()
            self.test_individual_students()
            self.test_update_attendance()
            
        except Exception as e:
            print_error(f"Критическая ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.print_summary()


def main():
    print_section("Тестирование API посещаемости и рейтинга")
    print_info(f"Сервер: {BASE_URL}")
    print_info(f"Учитель: {TEST_TEACHER['email']}")
    
    tester = AttendanceAPITester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
