# AI Проверка ЕГЭ/ОГЭ - Архитектурные диаграммы

## 1. Общая архитектура системы

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React)"]
        UI[Интерфейс учителя]
        AIButton[Кнопка "Проверить с AI"]
        AIResult[Компонент результата AI]
    end
    
    subgraph Backend["Django Backend"]
        API[HomeworkSubmissionViewSet]
        ExamService[ExamAIGradingService]
        BaseService[AIGradingService]
        Examples[ai_grading_examples.py<br/>Критерии ФИПИ]
        Cache[Django Cache<br/>Redis]
    end
    
    subgraph External["Внешние сервисы"]
        DeepSeek[DeepSeek API<br/>deepseek-chat]
    end
    
    subgraph Database["База данных"]
        Question[Question<br/>exam_type, exam_task_code]
        Answer[Answer<br/>ai_checked, ai_scores]
    end
    
    UI --> AIButton
    AIButton -->|POST /check-with-ai/| API
    API --> ExamService
    ExamService --> Examples
    ExamService --> BaseService
    ExamService --> Cache
    BaseService -->|HTTP Request| DeepSeek
    DeepSeek -->|JSON Response| BaseService
    BaseService --> ExamService
    ExamService --> API
    API --> AIResult
    API --> Answer
    API --> Question
    
    style DeepSeek fill:#4CAF50
    style Cache fill:#FF9800
    style Examples fill:#2196F3
```

## 2. Workflow проверки работы

```mermaid
sequenceDiagram
    participant Ученик
    participant Frontend
    participant Django
    participant ExamService
    participant Cache
    participant DeepSeek
    participant DB
    participant Учитель
    
    Ученик->>Frontend: Сдает сочинение
    Frontend->>Django: POST /submissions/
    Django->>DB: Сохранить Answer
    
    Note over Django: Автопроверка включена?
    alt Автопроверка включена
        Django->>ExamService: grade_exam_work_sync()
        ExamService->>Cache: Проверить кэш
        
        alt Кэш miss
            ExamService->>DeepSeek: Промпт + работа
            Note over DeepSeek: AI проверка<br/>(5-10 сек)
            DeepSeek-->>ExamService: JSON с оценками
            ExamService->>Cache: Сохранить результат
        else Кэш hit
            Cache-->>ExamService: Результат из кэша
        end
        
        ExamService->>DB: Сохранить ai_scores
        ExamService-->>Django: GradingResult
    end
    
    Django-->>Frontend: Submission с ai_result
    Frontend-->>Ученик: "Проверено! Оценка: 16/25"
    
    Note over Учитель: Через N часов
    Учитель->>Frontend: Открывает проверку
    Frontend->>Django: GET /submission/123
    Django-->>Frontend: Answer + ai_result
    Frontend-->>Учитель: Показать AI оценку
    
    alt Согласен с AI
        Учитель->>Frontend: Одобрить
        Frontend->>Django: PATCH /submission/123
        Django->>DB: Подтвердить оценку
    else Не согласен
        Учитель->>Frontend: Изменить оценку
        Frontend->>Django: PATCH /submission/123
        Django->>DB: teacher_override=True
    end
```

## 3. Структура данных (модели БД)

```mermaid
erDiagram
    QUESTION ||--o{ ANSWER : "has many"
    TEACHER ||--o{ QUESTION : creates
    STUDENT ||--o{ ANSWER : submits
    
    QUESTION {
        int id PK
        text question_text
        enum exam_type "EGE, OGE, NONE"
        string exam_task_code "russian_27, etc"
        bool enable_ai_grading
        int max_points
    }
    
    ANSWER {
        int id PK
        int question_id FK
        int student_id FK
        text answer_text
        bool ai_checked
        int ai_total_score
        json ai_criteria_scores "K1-K12"
        text ai_feedback
        json ai_errors_found
        decimal ai_cost_rubles
        bool teacher_override
        text teacher_notes
        datetime created_at
    }
    
    TEACHER {
        int id PK
        string name
        string email
    }
    
    STUDENT {
        int id PK
        string name
        string email
    }
```

## 4. Процесс экономии токенов

```mermaid
flowchart LR
    subgraph Input["Входные данные"]
        Source[Исходный текст<br/>500 символов]
        Student[Ответ ученика<br/>2000 символов]
    end
    
    subgraph Optimization["Оптимизация"]
        Compress[Сжатый промпт<br/>400 токенов вместо 700]
        Cache1[Кэш системного промпта]
        Cache2[Кэш результатов]
    end
    
    subgraph API["API вызов"]
        Request[Input: 550 токенов]
        Response[Output: 800 токенов]
        Cost[Стоимость: 0.015₽]
    end
    
    subgraph Savings["Экономия"]
        S1[Сжатие: -40% токенов]
        S2[Кэш: 0₽ при повторе]
        S3[Batch: -20% при >30 работ]
    end
    
    Source --> Compress
    Student --> Compress
    Compress --> Cache1
    Cache1 --> Request
    Request --> Response
    Response --> Cache2
    Request --> Cost
    
    Compress -.-> S1
    Cache2 -.-> S2
    Request -.-> S3
    
    style Cost fill:#4CAF50
    style S1 fill:#FF9800
    style S2 fill:#FF9800
    style S3 fill:#FF9800
```

## 5. Критерии ФИПИ для ЕГЭ Русский язык

```mermaid
mindmap
  root((ЕГЭ Русский<br/>Задание 27<br/>25 баллов))
    Содержание
      K1: Проблема (1б)
      K2: Комментарий (6б)
        2 примера
        Пояснения
        Смысловая связь
        Анализ связи
      K3: Позиция автора (1б)
      K4: Своя позиция (1б)
    Композиция
      K5: Логика (2б)
      K6: Речь (2б)
    Грамотность
      K7: Орфография (3б)
      K8: Пунктуация (3б)
      K9: Грамматика (2б)
      K10: Речь (2б)
    Доп критерии
      K11: Этика (1б)
      K12: Факты (1б)
```

## 6. Градация стоимости по моделям

```mermaid
graph TB
    subgraph Models["Модели AI"]
        DC[DeepSeek Chat<br/>0.015₽]
        DR[DeepSeek Reasoner<br/>0.06₽]
        MS[Mistral Small<br/>0.11₽]
        G4M[GPT-4o-mini<br/>0.21₽]
        G4[GPT-4o<br/>3.50₽]
    end
    
    subgraph Use["Применение"]
        Cheap[Массовая проверка<br/>Класс: 0.45₽]
        Medium[Сложные случаи<br/>Класс: 1.80₽]
        Expensive[Не рекомендуется<br/>Класс: 105₽]
    end
    
    DC --> Cheap
    DR --> Medium
    MS --> Medium
    G4M --> Medium
    G4 --> Expensive
    
    style DC fill:#4CAF50,stroke:#2E7D32,stroke-width:3px
    style Cheap fill:#4CAF50
    style Expensive fill:#F44336
```

## 7. Масштабирование системы

```mermaid
graph TD
    subgraph Small["Малая школа<br/>100-200 учеников"]
        S1[Синхронные запросы]
        S2[Локальный кэш Redis]
        S3[Стоимость: 2-4₽/месяц]
    end
    
    subgraph Medium["Крупная школа<br/>500+ учеников"]
        M1[Celery задачи]
        M2[Redis кластер]
        M3[Batch API]
        M4[Стоимость: 10-20₽/месяц]
    end
    
    subgraph Large["EdTech платформа<br/>1000+ учеников"]
        L1[Асинхронные запросы]
        L2[Rate limiting]
        L3[Приоритизация]
        L4[Distributed cache]
        L5[Стоимость: 50-100₽/месяц]
    end
    
    Small --> Medium
    Medium --> Large
    
    style Small fill:#81C784
    style Medium fill:#FFB74D
    style Large fill:#FF8A65
```

## 8. Workflow калибровки AI

```mermaid
flowchart TD
    Start[Старт] --> Collect[Собрать 50-100 работ<br/>проверенных учителем]
    Collect --> Run[Прогнать через AI]
    Run --> Compare{Расхождение<br/>≤ 2 балла?}
    
    Compare -->|Да ≥85%| Good[Точность высокая<br/>Калибровка OK]
    Compare -->|Нет <85%| Analyze[Анализ расхождений]
    
    Analyze --> Patterns{Есть паттерны<br/>ошибок?}
    
    Patterns -->|Да| Adjust[Корректировка промптов]
    Patterns -->|Нет| Examples[Добавить few-shot примеры]
    
    Adjust --> Run
    Examples --> Run
    
    Good --> Monitor[Мониторинг в production]
    Monitor --> Review{Качество<br/>снизилось?}
    Review -->|Да| Analyze
    Review -->|Нет| Monitor
    
    style Good fill:#4CAF50
    style Analyze fill:#FF9800
```

## 9. Экономика проекта (ROI)

```mermaid
graph TB
    subgraph Investment["Инвестиции"]
        I1[Разработка: 4 часа<br/>≈ 4000₽]
        I2[Тестирование: 2 часа<br/>≈ 2000₽]
        I3[API ключ: бесплатно]
        Total[ИТОГО: 6000₽]
    end
    
    subgraph Monthly["Ежемесячные затраты"]
        M1[AI проверка: 1-3₽]
        M2[Инфраструктура: 0₽<br/>уже есть]
        MTotal[ИТОГО: 1-3₽/мес]
    end
    
    subgraph Savings["Экономия"]
        S1[Время учителя: 10-20 час/мес]
        S2[Стоимость: 10000-20000₽/мес]
        S3[ROI: 1-2 месяца]
    end
    
    I1 --> Total
    I2 --> Total
    I3 --> Total
    
    M1 --> MTotal
    M2 --> MTotal
    
    Total -.окупается за.-> S3
    MTotal -.vs.-> S2
    
    style Total fill:#FF9800
    style S2 fill:#4CAF50
    style S3 fill:#4CAF50
```

## 10. Архитектура кэширования

```mermaid
flowchart LR
    subgraph Levels["Уровни кэша"]
        L1[L1: In-memory<br/>Python dict]
        L2[L2: Redis<br/>7 дней]
        L3[L3: Database<br/>постоянно]
    end
    
    subgraph Keys["Ключи кэша"]
        K1[Системный промпт<br/>reused]
        K2[Критерии ФИПИ<br/>reused]
        K3[Результат проверки<br/>MD5 hash]
    end
    
    subgraph Hit["Кэш Hit"]
        H1[Повторная проверка: 0₽]
        H2[Время: <10ms]
        H3[Hit rate: 30-40%]
    end
    
    Request[Запрос] --> L1
    L1 -->|miss| L2
    L2 -->|miss| L3
    L3 -->|miss| AI[DeepSeek API<br/>0.015₽]
    
    K1 -.-> L1
    K2 -.-> L1
    K3 -.-> L2
    
    L1 -->|hit| H1
    L2 -->|hit| H1
    L3 -->|hit| H1
    
    style H1 fill:#4CAF50
    style AI fill:#FF9800
```

---

## Легенда

- 🟢 Зеленый: Оптимально, рекомендуется
- 🟠 Оранжевый: Компромисс, для специальных случаев
- 🔴 Красный: Дорого, не рекомендуется

## Использование диаграмм

Все диаграммы созданы в формате Mermaid и могут быть:
- Встроены в Markdown (GitHub, GitLab поддерживают нативно)
- Экспортированы в PNG/SVG через mermaid.live
- Использованы в презентациях и документации

## Ссылки на документацию

- **Детальное описание**: См. AI_GRADING_GUIDE.md
- **Интеграция**: См. EGE_OGE_AI_INTEGRATION_GUIDE.md
- **Быстрый старт**: См. AI_GRADING_QUICKSTART.md
