Необходимо внести следующие изменения:

## 1. Исправить импорт в schedule/views.py

Заменить строку 1:
```python
from rest_framework import viewsets, status
```

На:
```python
from rest_framework import viewsets, status, permissions
```

## 2. Обновить StudentHomePage.js

В файле `frontend/src/components/StudentHomePage.js`:

### Изменить импорты (строки 1-6):
```javascript
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { getLessons, getHomeworkList, getSubmissions, getGroups } from '../apiService';
import Logo from './Logo';
import JoinGroupModal from './JoinGroupModal';
import '../styles/StudentHome.css';
```

### Добавить состояние (после строки 14):
```javascript
const [showJoinModal, setShowJoinModal] = useState(false);
const [groups, setGroups] = useState([]);
```

### Изменить useEffect (строки 16-38):
```javascript
useEffect(() => {
  loadData();
}, []);

const loadData = async () => {
  try {
    const [lessonsRes, hwRes, subRes, groupsRes] = await Promise.all([
      getLessons({}),
      getHomeworkList({}),
      getSubmissions({}),
      getGroups(),
    ]);
    setLessons(Array.isArray(lessonsRes.data) ? lessonsRes.data : lessonsRes.data.results || []);
    const hwList = Array.isArray(hwRes.data) ? hwRes.data : hwRes.data.results || [];
    setHomework(hwList);
    const subsList = Array.isArray(subRes.data) ? subRes.data : subRes.data.results || [];
    setSubmissions(subsList);
    const groupsList = Array.isArray(groupsRes.data) ? groupsRes.data : groupsRes.data.results || [];
    setGroups(groupsList);
  } catch (e) {
    console.error('Error loading data:', e);
  }
};

const handleJoinSuccess = () => {
  loadData();
};
```

### Изменить отображение курсов (строка ~175):
Заменить:
```javascript
<a href="#" className="student-link-button">Есть промокод?</a>
```
На:
```javascript
<button onClick={() => setShowJoinModal(true)} className="student-link-button">
  Есть промокод?
</button>
```

### Заменить условие отображения (строка ~180):
Заменить `courses.length === 0` на `groups.length === 0`

Добавить в пустое состояние:
```javascript
<button onClick={() => setShowJoinModal(true)} className="student-join-first-btn">
  Присоединиться к группе
</button>
```

### Заменить рендеринг карточек курсов (строка ~188):
```javascript
<div className="student-courses-grid">
  {groups.map(group => (
    <div key={group.id} className="student-course-card">
      <div className="student-course-logo">
        📚
      </div>
      <div className="student-course-info">
        <h3>{group.name}</h3>
        <p className="student-course-progress">
          Преподаватель: {group.teacher?.first_name || group.teacher?.email || 'Не указан'}
        </p>
        <p className="student-course-students">
          {group.student_count || 0} {group.student_count === 1 ? 'ученик' : 'учеников'}
        </p>
      </div>
    </div>
  ))}
</div>
```

### Добавить перед Floating buttons (перед последним закрывающим div):
```javascript
{/* Join Group Modal */}
{showJoinModal && (
  <JoinGroupModal 
    onClose={() => setShowJoinModal(false)}
    onSuccess={handleJoinSuccess}
  />
)}
```

## 3. Добавить стили для кнопки в StudentHome.css

```css
.student-join-first-btn {
  margin-top: 1.5rem;
  padding: 0.875rem 2rem;
  background: #0284c7;
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.student-join-first-btn:hover {
  background: #0369a1;
  transform: translateY(-1px);
}

.student-link-button {
  background: none;
  border: none;
  cursor: pointer;
  /* остальные стили остаются */
}

.student-course-students {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 0.25rem 0 0 0;
}
```

## 4. После внесения изменений выполнить:

```bash
cd teaching_panel
..\.venv\Scripts\python.exe manage.py makemigrations
..\.venv\Scripts\python.exe manage.py migrate
```
