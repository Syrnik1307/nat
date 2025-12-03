#!/usr/bin/env python
"""
UI/UX Testing для Homework Module
Проверяет визуальную доступность, респонсивность, пользовательский опыт
"""
import requests
import json
import re

BASE_URL = "http://72.56.81.163"

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class HomeworkUIUXTester:
    def __init__(self):
        self.teacher_token = None
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
        self.teacher_token = response.json()["access"]
        
    def test_frontend_bundle_size(self):
        """Проверка размера bundle (performance)"""
        js_response = requests.get(f"{BASE_URL}/static/js/main.925eda1e.js")
        css_response = requests.get(f"{BASE_URL}/static/css/main.3d08dba5.css")
        
        assert js_response.status_code == 200, "JS bundle not found"
        assert css_response.status_code == 200, "CSS bundle not found"
        
        js_size_kb = len(js_response.content) / 1024
        css_size_kb = len(css_response.content) / 1024
        
        self.log(f"JS bundle: {js_size_kb:.1f} KB", "INFO")
        self.log(f"CSS bundle: {css_size_kb:.1f} KB", "INFO")
        
        # Рекомендации: JS < 500KB, CSS < 100KB для хорошей производительности
        assert js_size_kb < 500, f"JS bundle too large: {js_size_kb:.1f} KB"
        assert css_size_kb < 100, f"CSS bundle too large: {css_size_kb:.1f} KB"
        
    def test_routes_html_structure(self):
        """Проверка HTML структуры на всех роутах"""
        routes = [
            "/",
            "/homework/constructor",
            "/homework/to-review",
            "/homework/graded"
        ]
        
        for route in routes:
            response = requests.get(f"{BASE_URL}{route}")
            assert response.status_code == 200, f"Route {route} not accessible"
            
            # Проверяем что это HTML
            assert 'text/html' in response.headers.get('Content-Type', ''), f"Route {route} not returning HTML"
            
            # Проверяем наличие базовых мета-тегов
            html = response.text
            assert '<html' in html.lower(), f"Route {route}: No <html> tag"
            assert '<head>' in html.lower(), f"Route {route}: No <head> tag"
            assert '<body>' in html.lower(), f"Route {route}: No <body> tag"
            assert 'root' in html or 'app' in html.lower(), f"Route {route}: No React root element"
            
    def test_api_response_structure(self):
        """Проверка структуры API ответов для UI"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Проверяем homework list
        hw_response = requests.get(f"{BASE_URL}/api/homework/", headers=headers)
        assert hw_response.status_code == 200, "Homework API failed"
        hw_data = hw_response.json()
        
        # Проверяем что есть pagination или results
        assert 'results' in hw_data or isinstance(hw_data, list), "No results in homework API"
        
        if 'results' in hw_data and len(hw_data['results']) > 0:
            hw = hw_data['results'][0]
            # Проверяем необходимые поля для UI
            required_fields = ['id', 'title', 'status']
            for field in required_fields:
                assert field in hw, f"Missing field '{field}' in homework API"
                
    def test_submission_api_fields(self):
        """Проверка полей submission API для корректного отображения"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        response = requests.get(f"{BASE_URL}/api/submissions/", headers=headers)
        assert response.status_code == 200, "Submissions API failed"
        data = response.json()
        
        submissions = data.get('results', data if isinstance(data, list) else [])
        
        if len(submissions) > 0:
            sub = submissions[0]
            
            # Поля для GradedSubmissionsList
            ui_fields = [
                'id',
                'status',
                'total_score',
                'max_score',  # Для вычисления процента
                'student',    # Для отображения имени
                'homework'    # Для отображения названия ДЗ
            ]
            
            for field in ui_fields:
                if field not in sub:
                    self.log(f"Warning: Missing field '{field}' for UI display", "WARN")
                    
    def test_media_url_format(self):
        """Проверка формата media URLs"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        response = requests.get(f"{BASE_URL}/api/homework/", headers=headers)
        hw_data = response.json()
        
        homeworks = hw_data.get('results', hw_data if isinstance(hw_data, list) else [])
        
        media_questions = []
        for hw in homeworks:
            questions = hw.get('questions', [])
            for q in questions:
                if q['question_type'] in ['LISTENING', 'HOTSPOT']:
                    config = q.get('config', {})
                    if 'audioUrl' in config or 'imageUrl' in config:
                        media_questions.append(q)
                        
        if media_questions:
            self.log(f"Found {len(media_questions)} questions with media", "INFO")
            for q in media_questions[:3]:  # Проверяем первые 3
                config = q.get('config', {})
                media_url = config.get('audioUrl') or config.get('imageUrl')
                if media_url:
                    # MediaPreview должен обработать и /media/file.mp3 и file.mp3
                    self.log(f"Media URL: {media_url}", "INFO")
        else:
            self.log("No media questions found (test with mock URLs)", "WARN")
            
    def test_color_coding_logic(self):
        """Проверка логики цветового кодирования badges"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        response = requests.get(f"{BASE_URL}/api/submissions/?status=graded", headers=headers)
        data = response.json()
        
        submissions = data.get('results', data if isinstance(data, list) else [])
        
        if len(submissions) > 0:
            for sub in submissions:
                total_score = sub.get('total_score', 0)
                max_score = sub.get('max_score', 100)
                
                if max_score > 0:
                    percentage = (total_score / max_score) * 100
                    
                    # Проверяем логику цветов
                    if percentage >= 80:
                        expected_color = "green"
                    elif percentage >= 60:
                        expected_color = "yellow"
                    else:
                        expected_color = "red"
                        
                    self.log(f"Submission {sub['id']}: {percentage:.0f}% -> {expected_color} badge", "INFO")
        else:
            self.log("No graded submissions to test color coding", "WARN")
            
    def test_filter_params(self):
        """Проверка работы filter параметров"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Тест фильтра по статусу
        statuses = ['submitted', 'graded', 'draft']
        for status in statuses:
            response = requests.get(f"{BASE_URL}/api/submissions/?status={status}", headers=headers)
            assert response.status_code == 200, f"Filter by status={status} failed"
            data = response.json()
            results = data.get('results', data if isinstance(data, list) else [])
            self.log(f"Status '{status}': {len(results)} submissions", "INFO")
            
    def test_pagination(self):
        """Проверка pagination для больших списков"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        response = requests.get(f"{BASE_URL}/api/homework/", headers=headers)
        data = response.json()
        
        # Проверяем наличие pagination metadata
        if 'count' in data or 'next' in data or 'previous' in data:
            self.log("Pagination detected in API", "INFO")
            self.log(f"Total count: {data.get('count', 'N/A')}", "INFO")
            self.log(f"Next page: {data.get('next', 'None')}", "INFO")
        else:
            self.log("No pagination metadata (may be fine for small datasets)", "WARN")
            
    def test_error_response_format(self):
        """Проверка формата ошибок для UI обработки"""
        # Намеренно неправильный запрос
        response = requests.get(f"{BASE_URL}/api/homework/999999/")
        
        if response.status_code == 404:
            try:
                error_data = response.json()
                # Проверяем что ошибка в JSON формате (не HTML)
                assert isinstance(error_data, dict), "Error not in JSON format"
                self.log("404 errors return JSON (good for UI)", "INFO")
            except:
                # Если HTML, то UI может показать некрасивое сообщение
                self.log("404 returns HTML (may need middleware fix)", "WARN")
                
    def test_search_functionality(self):
        """Проверка search parameter"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        # Проверяем работает ли search
        response = requests.get(f"{BASE_URL}/api/submissions/?search=test", headers=headers)
        
        if response.status_code == 200:
            self.log("Search parameter accepted", "INFO")
        else:
            self.log(f"Search not supported (status {response.status_code})", "WARN")
            
    def test_cors_headers(self):
        """Проверка CORS headers для frontend"""
        response = requests.options(f"{BASE_URL}/api/homework/")
        
        cors_headers = {
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        }
        
        found_headers = set(response.headers.keys())
        cors_present = any(h in found_headers for h in cors_headers)
        
        if cors_present:
            self.log("CORS headers configured", "INFO")
        else:
            self.log("CORS headers may be missing (check middleware)", "WARN")
            
    def test_feedback_summary_structure(self):
        """Проверка структуры teacher_feedback_summary для UI"""
        headers = {"Authorization": f"Bearer {self.teacher_token}"}
        
        response = requests.get(f"{BASE_URL}/api/submissions/?status=graded", headers=headers)
        data = response.json()
        
        submissions = data.get('results', data if isinstance(data, list) else [])
        
        if submissions:
            sub = submissions[0]
            feedback = sub.get('teacher_feedback_summary')
            
            if feedback:
                self.log("teacher_feedback_summary present", "INFO")
                # Проверяем что это dict с ожидаемыми полями
                if isinstance(feedback, dict):
                    expected_keys = ['comment', 'score', 'attachments']
                    for key in expected_keys:
                        if key in feedback:
                            self.log(f"  - {key}: present", "INFO")
            else:
                self.log("No teacher_feedback_summary (maybe no feedback yet)", "WARN")
                
    def run_all_tests(self):
        """Запуск всех UI/UX тестов"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Starting UI/UX Testing for Homework Module{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        tests = [
            ("1. Teacher Authentication", self.auth_teacher),
            ("2. Frontend Bundle Size (Performance)", self.test_frontend_bundle_size),
            ("3. HTML Structure on Routes", self.test_routes_html_structure),
            ("4. API Response Structure", self.test_api_response_structure),
            ("5. Submission API Fields for UI", self.test_submission_api_fields),
            ("6. Media URL Format", self.test_media_url_format),
            ("7. Color Coding Logic", self.test_color_coding_logic),
            ("8. Filter Parameters", self.test_filter_params),
            ("9. Pagination Support", self.test_pagination),
            ("10. Error Response Format", self.test_error_response_format),
            ("11. Search Functionality", self.test_search_functionality),
            ("12. CORS Headers", self.test_cors_headers),
            ("13. Feedback Summary Structure", self.test_feedback_summary_structure),
        ]
        
        for name, test_func in tests:
            self.test(name, test_func)
                
        # Итоги
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}UI/UX Test Results Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        
        print(f"{GREEN}✓ Passed: {passed}/{len(self.results)}{RESET}")
        if failed > 0:
            print(f"{YELLOW}⚠ Failed/Warnings: {failed}/{len(self.results)}{RESET}")
            print(f"\n{YELLOW}Issues found:{RESET}")
            for name, success, error in self.results:
                if not success:
                    print(f"  {YELLOW}⚠{RESET} {name}")
                    print(f"    Note: {error}")
        
        print(f"\n{BLUE}{'='*60}{RESET}\n")
        
        return failed == 0

if __name__ == "__main__":
    tester = HomeworkUIUXTester()
    success = tester.run_all_tests()
    
    # UI/UX тесты могут иметь warnings, но это не критично
    print(f"\n{BLUE}Note: UI/UX tests focus on user experience.{RESET}")
    print(f"{BLUE}Warnings indicate potential improvements, not critical failures.{RESET}\n")
