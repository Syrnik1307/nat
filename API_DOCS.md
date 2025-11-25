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

### Get single course
```http
GET /api/courses/{id}/
```

### Create course
```http
POST /api/courses/
Content-Type: application/json

{
  "title": "New Course",
  "description": "Course description",
  "teacher": 1
}
```

### Update course
```http
PUT /api/courses/{id}/
Content-Type: application/json

{
  "title": "Updated Course",
  "description": "Updated description"
}
```

### Delete course
```http
DELETE /api/courses/{id}/
```

### Add student to course
```http
POST /api/courses/{id}/add_student/
Content-Type: application/json

{
  "student_id": 2
}
```

### Remove student from course
```http
POST /api/courses/{id}/remove_student/
Content-Type: application/json

{
  "student_id": 2
}
```

---

## 📅 Lessons API

### List all lessons
```http
GET /api/lessons/
```

### Filter lessons by course
```http
GET /api/lessons/?course={course_id}
```

**Response:**
```json
[
  {
    "id": 1,
    "course": 1,
    "title": "Introduction and Setup",
    "description": "Lesson 1...",
    "start_time": "2025-11-15T10:00:00Z",
    "end_time": "2025-11-15T12:00:00Z",
    "zoom_meeting_id": "123456789",
    "zoom_join_url": "https://zoom.us/j/123456789",
    "zoom_password": "abc123",
    "assignments": [...]
  }
]
```

### Create lesson
```http
POST /api/lessons/
Content-Type: application/json

{
  "course": 1,
  "title": "New Lesson",
  "description": "Lesson content",
  "start_time": "2025-11-20T10:00:00Z",
  "end_time": "2025-11-20T12:00:00Z"
}
```

### Create Zoom meeting for lesson
```http
POST /api/lessons/{id}/create_zoom_meeting/
```

**Response:**
```json
{
  "status": "zoom meeting created",
  "join_url": "https://zoom.us/j/123456789",
  "meeting_id": "123456789"
}
```

---

## 📝 Assignments API

### List all assignments
```http
GET /api/assignments/
```

### Filter assignments by lesson
```http
GET /api/assignments/?lesson={lesson_id}
```

**Response:**
```json
[
  {
    "id": 1,
    "lesson": 1,
    "title": "Homework: Introduction",
    "description": "Complete the exercises...",
    "due_date": "2025-11-18T23:59:59Z",
    "max_points": 100,
    "created_at": "2025-11-13T18:00:00Z"
  }
]
```

### Create assignment
```http
POST /api/assignments/
Content-Type: application/json

{
  "lesson": 1,
  "title": "New Assignment",
  "description": "Assignment details",
  "due_date": "2025-11-25T23:59:59Z",
  "max_points": 100
}
```

### Get submissions for assignment
```http
GET /api/assignments/{id}/submissions/
```

---

## 📤 Submissions API

### List all submissions
```http
GET /api/submissions/
```

### Filter submissions
```http
GET /api/submissions/?assignment={assignment_id}
GET /api/submissions/?student={student_id}
GET /api/submissions/?assignment={assignment_id}&student={student_id}
```

**Response:**
```json
[
  {
    "id": 1,
    "assignment": 1,
    "student": {
      "id": 2,
      "username": "student1",
      "email": "student1@example.com",
      "first_name": "Student",
      "last_name": "Number 1"
    },
    "content": "My homework answer...",
    "file_url": "https://example.com/file.pdf",
    "submitted_at": "2025-11-17T20:30:00Z",
    "status": "submitted",
    "grade": null,
    "feedback": ""
  }
]
```

### Submit assignment
```http
POST /api/submissions/
Content-Type: application/json

{
  "assignment": 1,
  "student": 2,
  "content": "My answer to the homework",
  "file_url": "https://example.com/mywork.pdf"
}
```

### Grade submission
```http
POST /api/submissions/{id}/grade/
Content-Type: application/json

{
  "grade": 95,
  "feedback": "Excellent work! Well done."
}
```

**Response:**
```json
{
  "status": "graded",
  "grade": 95
}
```

---

## 🔐 Authentication (TODO)

Currently, the API allows anonymous access for development.

In production, you should implement:
- JWT authentication
- User permissions
- Teacher/Student role checks

---

## 📊 Response Status Codes

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## 🧪 Testing with curl

### Get all courses
```bash
curl http://127.0.0.1:8000/api/courses/
```

### Create a course
```bash
curl -X POST http://127.0.0.1:8000/api/courses/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Course",
    "description": "Testing",
    "teacher": 1
  }'
```

### Create Zoom meeting
```bash
curl -X POST http://127.0.0.1:8000/api/lessons/1/create_zoom_meeting/
```

---

## 💡 Frontend Usage Examples

See `frontend/src/apiService.js` for ready-to-use functions:

```javascript
import { getCourses, createCourse, addStudentToCourse } from './apiService';

// Get all courses
const courses = await getCourses();

// Create a new course
const newCourse = await createCourse({
  title: "My Course",
  description: "Course description",
  teacher: 1
});

// Add student to course
await addStudentToCourse(courseId, studentId);
```

---

*API построено на Django REST Framework 3.14+*
