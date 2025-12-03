import requests, time

BASE_URL = "http://72.56.81.163/api"
CREDENTIALS = {"email": "deploy_teacher@test.com", "password": "TestPass123!"}

print("Logging in as deploy_teacher@test.com ...")
tokens = requests.post(f"{BASE_URL}/jwt/token/", json=CREDENTIALS)
tokens.raise_for_status()
access = tokens.json()["access"]
headers = {"Authorization": f"Bearer {access}"}
print("Access token received")

timestamp = int(time.time())
questions = [
    {
        "prompt": "Свободный ответ: расскажи о своем дне",
        "question_type": "TEXT",
        "points": 5,
        "order": 0,
        "config": {"answerLength": "long"},
    },
    {
        "prompt": "Выбери столицу Франции",
        "question_type": "SINGLE_CHOICE",
        "points": 5,
        "order": 1,
        "choices": [
            {"text": "Париж", "is_correct": True},
            {"text": "Берлин", "is_correct": False},
            {"text": "Рим", "is_correct": False},
        ],
        "config": {
            "options": [
                {"id": "opt-1", "text": "Париж"},
                {"id": "opt-2", "text": "Берлин"},
                {"id": "opt-3", "text": "Рим"},
            ],
            "correctOptionId": "opt-1",
        },
    },
    {
        "prompt": "Выбери теплые цвета",
        "question_type": "MULTI_CHOICE",
        "points": 5,
        "order": 2,
        "choices": [
            {"text": "Красный", "is_correct": True},
            {"text": "Синий", "is_correct": False},
            {"text": "Оранжевый", "is_correct": True},
        ],
        "config": {
            "options": [
                {"id": "opt-a", "text": "Красный"},
                {"id": "opt-b", "text": "Синий"},
                {"id": "opt-c", "text": "Оранжевый"},
            ],
            "correctOptionIds": ["opt-a", "opt-c"],
        },
    },
    {
        "prompt": "Прослушай аудио и ответь",
        "question_type": "LISTENING",
        "points": 5,
        "order": 3,
        "config": {
            "audioUrl": "https://example.com/audio.mp3",
            "prompt": "Сколько раз прозвучало слово 'hello'?",
            "subQuestions": [
                {"id": "sub-1", "text": "Число повторов", "answer": "3"},
            ],
        },
    },
    {
        "prompt": "Сопоставь животных и их детенышей",
        "question_type": "MATCHING",
        "points": 5,
        "order": 4,
        "config": {
            "pairs": [
                {"id": "pair-1", "left": "Корова", "right": "Теленок"},
                {"id": "pair-2", "left": "Лошадь", "right": "Жеребенок"},
            ],
            "shuffleRightColumn": True,
        },
    },
    {
        "prompt": "Расставь шаги приготовления чая",
        "question_type": "DRAG_DROP",
        "points": 5,
        "order": 5,
        "config": {
            "items": [
                {"id": "step-1", "text": "Закипятить воду"},
                {"id": "step-2", "text": "Залить чай"},
                {"id": "step-3", "text": "Настоять"},
            ],
            "correctOrder": ["step-1", "step-2", "step-3"],
        },
    },
    {
        "prompt": "Заполни пропуски",
        "question_type": "FILL_BLANKS",
        "points": 5,
        "order": 6,
        "config": {
            "template": "Сегодня [___] погода и я иду в [___]",
            "answers": ["солнечная", "школу"],
            "caseSensitive": False,
            "matchingStrategy": "exact",
        },
    },
    {
        "prompt": "Найди материки на карте",
        "question_type": "HOTSPOT",
        "points": 5,
        "order": 7,
        "config": {
            "imageUrl": "https://example.com/map.png",
            "hotspots": [
                {"id": "spot-1", "label": "Европа", "x": 40, "y": 20, "width": 10, "height": 8, "isCorrect": True},
                {"id": "spot-2", "label": "Азия", "x": 60, "y": 25, "width": 15, "height": 12, "isCorrect": True},
            ],
            "maxAttempts": 2,
        },
    },
]

payload = {
    "title": f"E2E publish test {timestamp}",
    "description": "Автотест для проверки публикации всех типов вопросов",
    "questions": questions,
}

print("Creating homework ...")
create_resp = requests.post(f"{BASE_URL}/homework/", json=payload, headers=headers)
print("Create status:", create_resp.status_code)
print("Create response:", create_resp.text)
create_resp.raise_for_status()
homework_id = create_resp.json()["id"]

print("Publishing homework", homework_id)
publish_resp = requests.post(f"{BASE_URL}/homework/{homework_id}/publish/", headers=headers)
print("Publish status:", publish_resp.status_code)
print("Publish response:", publish_resp.text)
publish_resp.raise_for_status()
print("Publish test completed successfully")
