# 📡 API Documentation - Teaching Panel

## Base URL
```
http://127.0.0.1:8000/api/
```

---

## 📚 Courses API

### List all courses
```http
GET /api/courses/
```
**Response:**
```json
[
  {
    "id": 1,
    "title": "Introduction to Python Programming",
    "description": "Learn Python from scratch...",
    "teacher_name": "admin",
    "student_count": 3,
    "created_at": "2025-11-13T18:00:00Z"
  }
]
```

---

## 📅 Lessons API

### List all lessons
```http
GET /api/lessons/
```

---

## 📝 Assignments API

### List all assignments
```http
GET /api/assignments/
```

---

## 📤 Submissions API

### List all submissions
```http
GET /api/submissions/
```
