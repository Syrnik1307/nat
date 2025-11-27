"""
Locust Load Testing Script для Teaching Panel LMS
Симуляция поведения 1000 учителей и 3000 учеников

Запуск:
    locust -f locustfile.py --host=http://127.0.0.1:8000

Веб-интерфейс: http://localhost:8089
"""
from locust import HttpUser, task, between, constant
import random
import json


class TeacherUser(HttpUser):
    """
    Симуляция поведения учителя
    """
    wait_time = between(2, 5)  # Пауза между действиями 2-5 секунд
    
    def on_start(self):
        """Выполняется один раз при создании пользователя - логин"""
        # Логин учителя
        response = self.client.post("/api/jwt/token/", json={
            "email": f"teacher{random.randint(1, 1000)}@example.com",
            "password": "testpassword123"
        }, name="Login Teacher")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
        else:
            # Fallback: используем мок-токен для тестов без регистрации
            self.headers = {'Content-Type': 'application/json'}
    
    @task(3)
    def view_submissions_list(self):
        """Просмотр списка работ учеников"""
        self.client.get(
            "/api/submissions/",
            headers=self.headers,
            name="View Submissions List"
        )
    
    @task(2)
    def view_homework_list(self):
        """Просмотр списка домашних заданий"""
        self.client.get(
            "/api/homework/",
            headers=self.headers,
            name="View Homework List"
        )
    
    @task(1)
    def view_groups(self):
        """Просмотр групп"""
        self.client.get(
            "/api/groups/",
            headers=self.headers,
            name="View Groups"
        )
    
    @task(2)
    def view_lessons(self):
        """Просмотр расписания"""
        self.client.get(
            "/api/schedule/lessons/",
            headers=self.headers,
            name="View Lessons Schedule"
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
    Симуляция поведения ученика
    """
    wait_time = between(3, 8)  # Ученики работают медленнее
    
    def on_start(self):
        """Логин ученика"""
        response = self.client.post("/api/jwt/token/", json={
            "email": f"student{random.randint(1, 3000)}@example.com",
            "password": "testpassword123"
        }, name="Login Student")
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get('access')
            self.headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
        else:
            self.headers = {'Content-Type': 'application/json'}
    
    @task(5)
    def view_homework_list(self):
        """Просмотр доступных заданий"""
        self.client.get(
            "/api/homework/",
            headers=self.headers,
            name="View Available Homework"
        )
    
    @task(3)
    def view_my_submissions(self):
        """Просмотр своих работ"""
        self.client.get(
            "/api/submissions/",
            headers=self.headers,
            name="View My Submissions"
        )
    
    @task(2)
    def view_schedule(self):
        """Просмотр расписания"""
        self.client.get(
            "/api/schedule/lessons/",
            headers=self.headers,
            name="View My Schedule"
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
    Симуляция анонимного пользователя (без авторизации)
    """
    wait_time = constant(5)
    
    @task(1)
    def visit_homepage(self):
        """Посещение главной страницы"""
        self.client.get("/", name="Homepage")
    
    @task(1)
    def health_check(self):
        """Проверка здоровья API"""
        self.client.get("/", name="Health Check")


# Распределение пользователей:
# 25% учителей, 70% учеников, 5% анонимных
# Настраивается через веб-интерфейс Locust
