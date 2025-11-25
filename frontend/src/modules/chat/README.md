# 💬 Модуль Chat System

**Ответственный:** Напарник #2  
**Детальное ТЗ:** [`../../CHAT_MODULE_SPEC.md`](../../CHAT_MODULE_SPEC.md)

## 🎯 Назначение
Real-time чат между преподавателями и студентами с WebSocket, файлами и уведомлениями.

## 📁 Структура папок
```
chat/
├── components/
│   ├── ChatList.js           # Список чатов
│   ├── ChatWindow.js         # Окно чата
│   ├── MessageInput.js       # Поле ввода
│   ├── FileUpload.js         # Загрузка файлов
│   └── ChatNotifications.js  # Уведомления
├── services/
│   ├── chatService.js        # REST API
│   └── websocketService.js   # WebSocket
├── hooks/
│   ├── useChat.js
│   └── useWebSocket.js
└── README.md (этот файл)
```

## 🔗 API Endpoints
- `GET /api/chat/conversations/`
- `POST /api/chat/messages/`
- `WebSocket: ws://localhost:8000/ws/chat/{id}/`

## 🔧 Backend (нужно создать)
```
teaching_panel/chat/
├── models.py              # Conversation, Message
├── consumers.py           # WebSocket consumer
├── routing.py             # WebSocket routing
├── views.py               # REST API
└── serializers.py
```

## 🚀 Старт разработки
См. подробные промпты в [`CHAT_MODULE_SPEC.md`](../../CHAT_MODULE_SPEC.md)

## ✅ Чеклист
- [ ] Backend (Models, WebSocket)
- [ ] ChatList
- [ ] ChatWindow
- [ ] Real-time функционал
- [ ] Файлы и медиа
- [ ] Уведомления
- [ ] Групповые чаты
