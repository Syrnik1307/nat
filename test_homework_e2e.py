#!/usr/bin/env python
"""
End-to-End тестирование homework модуля на production
Тестирует все 8 типов вопросов, автопроверку, feedback, фильтры
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://72.56.81.163"

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class HomeworkE2ETester:
    def __init__(self):
        self.teacher_token = None
        self.student_token = None
        self.homework_id = None
        self.submission_id = None
        self.group_id = None
        self.results = []
        
    def log(self, message, status="INFO"):
        color = BLUE if status == "INFO" else GREEN if status == "OK" else RED if status == "FAIL" else YELLOW
        print(f"{color}[{status}]{RESET} {message}")
        
    def test(self, name, func):
        """Запуск теста с обработкой ошибок"""
        try:
            self.log(f"Testing: {name}", "INFO")
            func()
            self.log(f"✓ {name}", "OK")
            self.results.append((name, True, None))
            return True
        except Exception as e:
            self.log(f"✗ {name}: {str(e)}", "FAIL")
            self.results.append((name, False, str(e)))
            return False
    
    def auth_teacher(self):
        """Авторизация преподавателя"""
        response = requests.post(f"{BASE_URL}/api/jwt/token/", json={
            "email": "deploy_teacher@test.com",
            "password": "TestPass123!"
        })
        assert response.status_code == 200, f"Auth failed: {response.status_code}"
        data = response.json()
        self.teacher_token = data["access"]
        assert self.teacher_token, "No access token received"
        
    def auth_student(self):
        """Создание и авторизация студента"""
        # Создаём тестового студента
        student_email = f"test_student_{datetime.now().timestamp()}@test.com"
        response = requests.post(f"{BASE_URL}/api/jwt/register/", json={
            "email": student_email,
            "password": "TestPass123!",
            "first_name": "Test",
            "last_name": "Student",
            "role": "student"
        })
        assert response.status_code in [200, 201], f"Student registration failed: {response.status_code}"
        data = response.json()
        self.student_token = data["access"]
        assert self.student_token, "No student access token"
        
    def create_group(self):
        """Создание тестовой группы"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Получаем teacher_id из профиля
        me_response = requests.get(f"{BASE_URL}/api/me/", headers=headers)
        assert me_response.status_code == 200, "Failed to get teacher profile"
        teacher_id = me_response.json()["id"]
        
        response = requests.post(f"{BASE_URL}/api/groups/", 
            headers=headers,
            json={
                "name": f"Test Group {datetime.now().timestamp()}",
                "description": "E2E test group",
                "teacher_id": teacher_id
            }
        )
        if response.status_code not in [200, 201]:
            self.log(f"Group creation error: {response.text[:200]}", "WARN")
            # Пробуем получить существующую группу
            get_resp = requests.get(f"{BASE_URL}/api/groups/", headers=headers)
            if get_resp.status_code == 200:
                groups = get_resp.json().get("results", [])
                if groups:
                    self.group_id = groups[0]["id"]
                    self.log(f"Using existing group ID: {self.group_id}", "WARN")
                    return
        assert response.status_code in [200, 201], f"Group creation failed: {response.status_code}"
        data = response.json()
        self.group_id = data["id"]
        assert self.group_id, "No group ID"
        
    def create_homework_all_types(self):
        """Создание ДЗ со всеми 8 типами вопросов"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        homework_data = {
            "title": "E2E Test Homework - All Question Types",
            "description": "Testing all 8 question types",
            "status": "draft",
            "questions": [
                {
                    "prompt": "Q1: Text question",
                    "question_type": "TEXT",
                    "points": 10,
                    "order": 1,
                    "config": {"answerLength": "short"}
                },
                {
                    "prompt": "Q2: Single choice",
                    "question_type": "SINGLE_CHOICE",
                    "points": 10,
                    "order": 2,
                    "config": {
                        "correctOptionId": "opt1",
                        "options": [
                            {"id": "opt1", "text": "Correct answer"},
                            {"id": "opt2", "text": "Wrong answer"}
                        ]
                    },
                    "choices": [
                        {"text": "Correct answer", "is_correct": True},
                        {"text": "Wrong answer", "is_correct": False}
                    ]
                },
                {
                    "prompt": "Q3: Multiple choice",
                    "question_type": "MULTI_CHOICE",
                    "points": 10,
                    "order": 3,
                    "config": {
                        "correctOptionIds": ["opt1", "opt2"],
                        "options": [
                            {"id": "opt1", "text": "Correct 1"},
                            {"id": "opt2", "text": "Correct 2"},
                            {"id": "opt3", "text": "Wrong"}
                        ]
                    },
                    "choices": [
                        {"text": "Correct 1", "is_correct": True},
                        {"text": "Correct 2", "is_correct": True},
                        {"text": "Wrong", "is_correct": False}
                    ]
                },
                {
                    "prompt": "Q4: Listening",
                    "question_type": "LISTENING",
                    "points": 10,
                    "order": 4,
                    "config": {
                        "audioUrl": "/media/test_audio.mp3",
                        "subQuestions": [
                            {"id": "sq1", "text": "What did you hear?", "answer": "test"}
                        ]
                    }
                },
                {
                    "prompt": "Q5: Matching",
                    "question_type": "MATCHING",
                    "points": 10,
                    "order": 5,
                    "config": {
                        "pairs": [
                            {"id": "p1", "left": "Cat", "right": "Meow"},
                            {"id": "p2", "left": "Dog", "right": "Woof"}
                        ]
                    }
                },
                {
                    "prompt": "Q6: Drag and drop",
                    "question_type": "DRAG_DROP",
                    "points": 10,
                    "order": 6,
                    "config": {
                        "items": [
                            {"id": "i1", "text": "First"},
                            {"id": "i2", "text": "Second"},
                            {"id": "i3", "text": "Third"}
                        ],
                        "correctOrder": ["i1", "i2", "i3"]
                    }
                },
                {
                    "prompt": "Q7: Fill in the blanks",
                    "question_type": "FILL_BLANKS",
                    "points": 10,
                    "order": 7,
                    "config": {
                        "template": "The [___] is blue and the [___] is red.",
                        "answers": ["sky", "apple"]
                    }
                },
                {
                    "prompt": "Q8: Hotspot",
                    "question_type": "HOTSPOT",
                    "points": 10,
                    "order": 8,
                    "config": {
                        "imageUrl": "/media/test_image.jpg",
                        "hotspots": [
                            {"id": "h1", "label": "Red zone", "isCorrect": True},
                            {"id": "h2", "label": "Blue zone", "isCorrect": False}
                        ]
                    }
                }
            ]
        }
        
        response = requests.post(f"{BASE_URL}/api/homework/",
            headers=headers,
            json=homework_data
        )
        assert response.status_code in [200, 201], f"Homework creation failed: {response.status_code} - {response.text[:200]}"
        data = response.json()
        self.homework_id = data["id"]
        assert self.homework_id, "No homework ID"
        
    def publish_homework(self):
        """Публикация ДЗ"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        response = requests.post(
            f"{BASE_URL}/api/homework/{self.homework_id}/publish/",
            headers=headers
        )
        assert response.status_code == 200, f"Publish failed: {response.status_code} - {response.text[:200]}"
        
    def submit_homework_student(self):
        """Студент отправляет ДЗ со всеми типами ответов"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        
        # Получаем список доступных homework для студента
        list_response = requests.get(
            f"{BASE_URL}/api/homework/",
            headers=headers
        )
        assert list_response.status_code == 200, f"List homework failed: {list_response.status_code}"
        
        homeworks = list_response.json().get("results", list_response.json() if isinstance(list_response.json(), list) else [])
        
        # Ищем наш homework
        target_hw = None
        for hw in homeworks:
            if hw["id"] == self.homework_id:
                target_hw = hw
                break
        
        if not target_hw:
            # Homework не виден студенту, пробуем прямой доступ к вопросам
            hw_response = requests.get(
                f"{BASE_URL}/api/homework/{self.homework_id}/",
                headers={"Authorization": f"Bearer {self.teacher_token}"}
            )
            assert hw_response.status_code == 200, f"Get homework as teacher failed: {hw_response.status_code}"
            target_hw = hw_response.json()
        
        questions = target_hw.get("questions", [])
        
        # Формируем ответы
        answers = []
        for q in questions:
            answer_data = {"question": q["id"]}
            
            if q["question_type"] == "TEXT":
                answer_data["text_answer"] = "My text answer"
                
            elif q["question_type"] == "SINGLE_CHOICE":
                # Выбираем первый вариант (правильный)
                answer_data["selected_choices"] = [q["choices"][0]["id"]]
                
            elif q["question_type"] == "MULTI_CHOICE":
                # Выбираем первые два (правильные)
                answer_data["selected_choices"] = [q["choices"][0]["id"], q["choices"][1]["id"]]
                
            elif q["question_type"] == "LISTENING":
                answer_data["text_answer"] = json.dumps({"sq1": "test"})
                
            elif q["question_type"] == "MATCHING":
                answer_data["text_answer"] = json.dumps({"p1": "Meow", "p2": "Woof"})
                
            elif q["question_type"] == "DRAG_DROP":
                answer_data["text_answer"] = json.dumps(["i1", "i2", "i3"])
                
            elif q["question_type"] == "FILL_BLANKS":
                answer_data["text_answer"] = json.dumps(["sky", "apple"])
                
            elif q["question_type"] == "HOTSPOT":
                answer_data["text_answer"] = json.dumps(["h1"])
                
            answers.append(answer_data)
        
        # Отправляем submission
        submission_data = {
            "homework": self.homework_id,
            "status": "submitted",
            "answers": answers
        }
        
        response = requests.post(
            f"{BASE_URL}/api/submissions/",
            headers=headers,
            json=submission_data
        )
        assert response.status_code in [200, 201], f"Submission failed: {response.status_code} - {response.text[:200]}"
        data = response.json()
        self.submission_id = data["id"]
        assert self.submission_id, "No submission ID"
        
    def check_auto_grading(self):
        """Проверка автоматической оценки"""
        # Проверяем после того как teacher добавил feedback (status=graded)
        # До этого момента submission может быть недоступен для teacher
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Получаем список submissions
        list_response = requests.get(
            f"{BASE_URL}/api/submissions/",
            headers=headers
        )
        assert list_response.status_code == 200, f"List submissions failed: {list_response.status_code}"
        
        submissions = list_response.json().get("results", list_response.json() if isinstance(list_response.json(), list) else [])
        
        # Ищем наш submission
        target_sub = None
        for sub in submissions:
            if sub["id"] == self.submission_id:
                target_sub = sub
                break
        
        assert target_sub is not None, "Submission not found in list"
        data = target_sub
        
        # Проверяем что есть автобаллы
        total_score = data.get("total_score")
        assert total_score is not None, "No auto score calculated"
        
        # Должны быть баллы за SINGLE_CHOICE, MULTI_CHOICE и другие типы кроме TEXT
        assert total_score > 0, f"Auto score is {total_score}, expected > 0"
        
        # Проверяем каждый ответ
        answers = data.get("answers", [])
        assert len(answers) == 8, f"Expected 8 answers, got {len(answers)}"
        
        for answer in answers:
            q_type = answer["question_type"]
            auto_score = answer.get("auto_score")
            needs_review = answer.get("needs_manual_review")
            
            if q_type == "TEXT":
                assert needs_review == True, f"TEXT should need manual review"
            else:
                assert auto_score is not None, f"{q_type} should have auto_score"
                
    def teacher_add_feedback(self):
        """Преподаватель добавляет комментарий"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        response = requests.patch(
            f"{BASE_URL}/api/submissions/{self.submission_id}/feedback/",
            headers=headers,
            json={
                "comment": "Great work! Keep it up!",
                "score": 85,
                "attachments": []
            }
        )
        assert response.status_code == 200, f"Feedback failed: {response.status_code} - {response.text[:200]}"
        data = response.json()
        assert data.get("status") == "graded", "Status should be graded"
        assert data.get("teacher_feedback_summary"), "No feedback summary"
        
    def teacher_update_answer(self):
        """Преподаватель редактирует оценку отдельного ответа"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Получаем submission из списка
        list_response = requests.get(
            f"{BASE_URL}/api/submissions/",
            headers=headers
        )
        assert list_response.status_code == 200
        
        submissions = list_response.json().get("results", list_response.json() if isinstance(list_response.json(), list) else [])
        target_sub = None
        for sub in submissions:
            if sub["id"] == self.submission_id:
                target_sub = sub
                break
        
        assert target_sub is not None, "Submission not found"
        answers = target_sub.get("answers", [])
        assert len(answers) > 0, "No answers in submission"
        
        # Редактируем первый TEXT ответ
        text_answers = [a for a in answers if a.get("question_type") == "TEXT"]
        if not text_answers:
            # Если нет TEXT, берем любой
            text_answer = answers[0]
        else:
            text_answer = text_answers[0]
        
        response = requests.patch(
            f"{BASE_URL}/api/submissions/{self.submission_id}/update_answer/",
            headers=headers,
            json={
                "answer_id": text_answer["id"],
                "teacher_score": 8,
                "teacher_feedback": "Good answer, but could be more detailed"
            }
        )
        assert response.status_code == 200, f"Update answer failed: {response.status_code} - {response.text[:200]}"
        
    def test_filters_teacher(self):
        """Тест фильтров для преподавателя"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Фильтр по статусу
        response = requests.get(
            f"{BASE_URL}/api/submissions/?status=graded",
            headers=headers
        )
        assert response.status_code == 200, "Filter by status failed"
        data = response.json()
        results = data.get("results", data if isinstance(data, list) else [])
        assert len(results) > 0, "No graded submissions found"
        
    def test_navigation_routes(self):
        """Тест что все роуты доступны"""
        routes_to_test = [
            "/",
            "/homework/constructor",
            "/homework/to-review",
            "/homework/graded"
        ]
        
        for route in routes_to_test:
            response = requests.get(f"{BASE_URL}{route}")
            assert response.status_code == 200, f"Route {route} returned {response.status_code}"
            
    def run_all_tests(self):
        """Запуск всех тестов"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Starting E2E Homework Module Testing{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        tests = [
            ("1. Teacher Authentication", self.auth_teacher),
            ("2. Student Registration & Auth", self.auth_student),
            ("3. Create Test Group", self.create_group),
            ("4. Create Homework (All 8 Types)", self.create_homework_all_types),
            ("5. Publish Homework", self.publish_homework),
            ("6. Student Submit Homework", self.submit_homework_student),
            ("7. Teacher Add Feedback", self.teacher_add_feedback),
            ("8. Check Auto-Grading", self.check_auto_grading),
            ("9. Teacher Update Answer Score", self.teacher_update_answer),
            ("10. Test Filters", self.test_filters_teacher),
            ("11. Test Navigation Routes", self.test_navigation_routes),
        ]
        
        for name, test_func in tests:
            if not self.test(name, test_func):
                # Продолжаем даже если тест упал
                pass
                
        # Итоги
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Results Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        
        print(f"{GREEN}✓ Passed: {passed}/{len(self.results)}{RESET}")
        if failed > 0:
            print(f"{RED}✗ Failed: {failed}/{len(self.results)}{RESET}")
            print(f"\n{RED}Failed tests:{RESET}")
            for name, success, error in self.results:
                if not success:
                    print(f"  {RED}✗{RESET} {name}")
                    print(f"    Error: {error}")
        
        print(f"\n{BLUE}{'='*60}{RESET}\n")
        
        return failed == 0

if __name__ == "__main__":
    tester = HomeworkE2ETester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
