"""
Locust Load Testing Script для Teaching Panel LMS
Симуляция поведения 500 учителей и 4500 учеников (5000 total)

Запуск для 5000 пользователей:
    locust -f locustfile.py --host=http://127.0.0.1:8000 --users 5000 --spawn-rate 50

Headless режим (без UI):
    locust -f locustfile.py --host=http://127.0.0.1:8000 --headless \
        --users 5000 --spawn-rate 100 --run-time 10m \
        --html=load_test_report.html --csv=load_test_results

Веб-интерфейс: http://localhost:8089
"""
from locust import HttpUser, task, between, constant, events
import random
import json
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Счетчики для статистики
login_success = 0
login_failed = 0


class TeacherUser(HttpUser):
    """
    Симуляция поведения учителя (10% от общего числа = 500 из 5000)
    Действия: просмотр групп, уроков, проверка работ
    """
    weight = 1  # 10% пользователей
    wait_time = between(2, 5)  # Пауза между действиями 2-5 секунд
    
    def on_start(self):
        """Выполняется один раз при создании пользователя - логин"""
        global login_success, login_failed
        
        # Логин учителя (используем loadtest пользователей)
        teacher_id = random.randint(1, 500)
        response = self.client.post("/api/jwt/token/", json={
            "email": f"teacher{teacher_id}@loadtest.local",
            "password": "loadtest123"
        }, name="Login Teacher")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            login_success += 1
        else:
            login_failed += 1
            # Fallback: пустые headers, запросы будут возвращать 401
            self.headers = {'Content-Type': 'application/json'}
            self.token = None
    
    @task(3)
    def view_groups(self):
        """Просмотр групп учителя"""
        self.client.get(
            "/api/schedule/groups/",
            headers=self.headers,
            name="Teacher: View Groups"
        )
    
    @task(4)
    def view_lessons(self):
        """Просмотр расписания"""
        self.client.get(
            "/api/schedule/lessons/",
            headers=self.headers,
            name="Teacher: View Lessons"
        )
    
    @task(2)
    def view_calendar(self):
        """Просмотр календаря (самый тяжелый запрос)"""
        import datetime
        now = datetime.datetime.now()
        start = now.strftime("%Y-%m-%dT00:00:00")
        end = (now + datetime.timedelta(days=30)).strftime("%Y-%m-%dT23:59:59")
        self.client.get(
            f"/api/schedule/lessons/calendar_feed/?start={start}&end={end}",
            headers=self.headers,
            name="Teacher: Calendar Feed"
        )
    
    @task(2)
    def view_submissions_list(self):
        """Просмотр списка работ учеников"""
        self.client.get(
            "/api/submissions/",
            headers=self.headers,
            name="Teacher: View Submissions"
        )
    
    @task(1)
    def view_homework_list(self):
        """Просмотр списка домашних заданий"""
        self.client.get(
            "/api/homework/",
            headers=self.headers,
            name="Teacher: View Homework"
        )
    
    @task(1)
    def view_me(self):
        """Просмотр профиля"""
        self.client.get(
            "/api/me/",
            headers=self.headers,
            name="Teacher: View Profile"
        )
    
    @task(1)
    def grade_submission(self):
        """Выставление оценки (симуляция)"""
        # Получаем список работ
        response = self.client.get(
            "/api/submissions/?status=submitted",
            headers=self.headers,
            name="Get Submissions for Grading"
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                submission = random.choice(results)
                submission_id = submission['id']
                
                # Симулируем выставление оценки
                if submission.get('answers'):
                    answer = random.choice(submission['answers'])
                    
                    self.client.patch(
                        f"/api/submissions/{submission_id}/update_answer/",
                        headers=self.headers,
                        json={
                            "answer_id": answer['id'],
                            "teacher_score": random.randint(0, 10),
                            "teacher_feedback": "Good work!"
                        },
                        name="Grade Answer"
                    )


class StudentUser(HttpUser):
    """
    Симуляция поведения ученика (90% от общего числа = 4500 из 5000)
    Действия: просмотр расписания, заданий, отправка работ
    """
    weight = 9  # 90% пользователей
    wait_time = between(3, 8)  # Ученики работают медленнее
    
    def on_start(self):
        """Логин ученика"""
        global login_success, login_failed
        
        student_id = random.randint(1, 4500)
        response = self.client.post("/api/jwt/token/", json={
            "email": f"student{student_id}@loadtest.local",
            "password": "loadtest123"
        }, name="Login Student")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            login_success += 1
        else:
            login_failed += 1
            self.headers = {'Content-Type': 'application/json'}
            self.token = None
    
    @task(4)
    def view_my_schedule(self):
        """Просмотр своего расписания"""
        self.client.get(
            "/api/schedule/lessons/",
            headers=self.headers,
            name="Student: View Schedule"
        )
    
    @task(3)
    def view_homework_list(self):
        """Просмотр доступных заданий"""
        self.client.get(
            "/api/homework/",
            headers=self.headers,
            name="Student: View Homework"
        )
    
    @task(2)
    def view_my_submissions(self):
        """Просмотр своих работ"""
        self.client.get(
            "/api/submissions/",
            headers=self.headers,
            name="Student: View Submissions"
        )
    
    @task(2)
    def view_my_groups(self):
        """Просмотр своих групп"""
        self.client.get(
            "/api/schedule/groups/",
            headers=self.headers,
            name="Student: View Groups"
        )
    
    @task(1)
    def view_me(self):
        """Просмотр профиля"""
        self.client.get(
            "/api/me/",
            headers=self.headers,
            name="Student: View Profile"
        )
    
    @task(1)
    def submit_homework(self):
        """Отправка домашней работы (симуляция)"""
        # Получаем список заданий
        response = self.client.get(
            "/api/homework/",
            headers=self.headers,
            name="Get Homework for Submission"
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            if results:
                homework = random.choice(results)
                
                # Создаём попытку
                self.client.post(
                    "/api/submissions/",
                    headers=self.headers,
                    json={
                        "homework": homework['id'],
                        "status": "submitted",
                        "answers": []
                    },
                    name="Submit Homework"
                )


class AnonymousUser(HttpUser):
    """
    Симуляция анонимного пользователя (проверка доступности)
    Не включен в основной тест (weight=0)
    """
    weight = 0  # Исключен из основного теста
    wait_time = constant(5)
    
    @task(1)
    def visit_homepage(self):
        """Посещение главной страницы"""
        self.client.get("/", name="Anonymous: Homepage")
    
    @task(1)
    def health_check(self):
        """Проверка здоровья API"""
        self.client.get("/api/", name="Anonymous: API Root")


# =============================================================================
# Event Handlers для сбора статистики
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Вызывается при старте теста"""
    logger.info("=" * 60)
    logger.info("Starting load test for Teaching Panel LMS")
    logger.info("Target: 5000 concurrent users (500 teachers + 4500 students)")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Вызывается при остановке теста"""
    logger.info("=" * 60)
    logger.info("Load test completed")
    logger.info(f"Login success: {login_success}, failed: {login_failed}")
    if login_success + login_failed > 0:
        success_rate = login_success / (login_success + login_failed) * 100
        logger.info(f"Login success rate: {success_rate:.1f}%")
    logger.info("=" * 60)


# =============================================================================
# Распределение пользователей:
# - TeacherUser (weight=1): ~10% = 500 учителей
# - StudentUser (weight=9): ~90% = 4500 студентов
# =============================================================================
