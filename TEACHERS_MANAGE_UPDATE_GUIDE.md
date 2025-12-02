# Руководство по обновлению модального окна «Управление учителями»

Документ описывает полный процесс обновления административного модального окна ***TeachersManage***, которое отвечает за контроль карточек преподавателей, управление подпиской/хранилищем и настройку Zoom‑данных. Руководство покрывает требования к бэкенду и фронтенду, а также порядок проверки и деплоя.

## 1. Цели и сценарии
- Просмотр всех преподавателей с ключевыми метриками (уроки, ученики, дни на платформе).
- Управление статусом подписки (активация на фиксированный срок, перевод в ожидание).
- Увеличение квоты хранилища (GB) поверх базового лимита.
- Редактирование Zoom credentials (account/client/secret/user IDs).
- Удаление преподавателя, поиск по имени/email, автообновление списка.

## 2. Зависимые модули
| Область | Файл | Назначение |
| --- | --- | --- |
| Бэкенд API | `teaching_panel/accounts/admin_views.py` | Эндпоинты профиля, подписки, хранилища, Zoom |
| Маршруты | `teaching_panel/accounts/urls.py` | Роуты `/accounts/api/admin/teachers/...` |
| Подписки | `teaching_panel/accounts/subscriptions_utils.py` | Получение/создание подписки учителя |
| Тесты | `teaching_panel/accounts/tests.py` | API‑тесты `AdminTeacherSubscriptionViewTests`, `AdminTeacherStorageViewTests` |
| UI | `frontend/src/components/TeachersManage.js` | React‑компонент модального окна |
| Стили | `frontend/src/components/TeachersManage.css` | Адаптивное двухколоночное оформление |

## 3. Изменения на бэкенде
1. **API профиля**: `AdminTeacherDetailView` (GET `/profile/`) возвращает `teacher`, `subscription`, `metrics`, `zoom`. Убедитесь, что:
   - `_get_teacher_metrics` считает уроки, группы, студентов и «преподавательские минуты» за 30 дней.
   - `_serialize_subscription` добавляет поля `total_storage_gb`, `storage_usage_percent`, `remaining_days` и т.д.

2. **Подписка**: `AdminTeacherSubscriptionView` (POST `/subscription/`). В теле запроса:
   ```json
   { "action": "activate" | "deactivate", "days": 28 }
   ```
   - `activate`: план `monthly`, статус `active`, `expires_at = now + days`, `auto_renew = False`.
   - `deactivate`: статус `pending`, `expires_at = now`.
   - После обновления вернуть сериализованную подписку.

3. **Хранилище**: `AdminTeacherStorageView` (POST `/storage/`). Тело `{ "extra_gb": <int> }`.
   - Валидация > 0.
   - Увеличить `extra_storage_gb`, вернуть обновлённую подписку.

4. **Удаление/Zoom**: `AdminDeleteTeacherView` (DELETE `/delete/`), `AdminUpdateTeacherZoomView` (PATCH `/zoom/`). Zoom принимает полный JSON с ключами `zoom_account_id`, `zoom_client_id`, `zoom_client_secret`, `zoom_user_id`.

5. **Маршруты**: убедитесь, что пути добавлены в `accounts/urls.py` (см. блок `Admin API endpoints`).

6. **Тесты**: добавьте/обновите `AdminTeacherSubscriptionViewTests` и `AdminTeacherStorageViewTests` в `accounts/tests.py`:
   - Проверьте активацию на 28 дней (окно 27–29 суток из‑за TZ).
   - Проверяйте перевод в `pending`, права доступа (403, если не админ) и валидацию `extra_gb`.
   - Прогон: `python manage.py test accounts.tests.AdminTeacherSubscriptionViewTests accounts.tests.AdminTeacherStorageViewTests`.

## 4. Обновление фронтенда
1. **Компонент**: `TeachersManage.js` реализует управление состоянием:
   - Списки учителей (`/accounts/api/admin/teachers/`) с автообновлением каждые 20 секунд.
   - `loadTeacherProfile` подтягивает расширенные данные по выбранному преподавателю.
   - В левой колонке — карточки с поиском, статус‑пилюлей, метриками последних 30 дней и кнопкой удаления.
   - Правая колонка содержит баннеры успеха/ошибок, карточку профиля, блок метрик, секцию подписки (кнопки активации/деактивации, прогресс‑бар хранилища, форма добавления GB) и форму Zoom credentials.

2. **UI‑состояния**:
   - `actionMessage` и `actionError` показывают результат операций.
   - `actionLoading` блокирует кнопки во время сетевых вызовов.
   - `storageInput` по умолчанию 5 GB; после успешного увеличения сбрасывается.
   - `zoomForm` синхронизируется с `profile.zoom` через `useEffect`.

3. **Стили**: `TeachersManage.css` описывает:
   - Оверлей, модалку, две колонки (`tm-left-panel`, `tm-right-panel`).
   - Карточки учителей, статус‑пилюли, гриды метрик, прогресс‑бар хранилища и адаптивные брейкпоинты (≤1024px, ≤640px).

4. **Хуки и пайплайн запросов**:
   - Все запросы используют `fetch` + `Authorization: Bearer <token>` (берётся из `localStorage` ключ `tp_access_token`).
   - При изменении выбранного преподавателя (`selectedTeacherId`) автоматически подгружается профиль и пересчитываются формы.
   - Удаление подтверждается через `window.confirm` и после успеха обновляет список.

## 5. Чек‑лист реализации
1. **Бэкенд**
   - [ ] Добавлены view/urls для профиля, подписки, хранилища и Zoom.
   - [ ] Гарантировано, что `get_subscription` создаёт запись (триал), если отсутствует.
   - [ ] Написаны/обновлены тесты `AdminTeacherSubscriptionViewTests`, `AdminTeacherStorageViewTests`.
   - [ ] `python manage.py test accounts.tests` проходит локально.

2. **Фронтенд**
   - [ ] Компонент `TeachersManage.js` отображает карточки и правую панель со всеми секциями.
   - [ ] Новые классы присутствуют в `TeachersManage.css`, адаптивность проверена.
   - [ ] ESLint/React предупреждения устранены либо задокументированы.

3. **Интеграция**
   - [ ] Админ может искать, удалять и выбирать учителя слева.
   - [ ] Кнопки управления подпиской и хранилищем выполняют запросы и обновляют UI.
   - [ ] Форма Zoom сохраняет значения и отображает статус «Настроено».
   - [ ] При ошибках API отображается `tm-banner error` с текстом бэкенда.

4. **Деплой**
   - [ ] Все изменения закоммичены в `main` (включая новые миграции, если нужны).
   - [ ] Прогнан `npm run build` (проверить предупреждения) и `python manage.py collectstatic`.
   - [ ] На сервере: `git pull`, `pip install -r requirements.txt`, `python manage.py migrate`, `collectstatic`, `npm install`, `npm run build`, `systemctl restart teaching_panel nginx redis-server`.
   - [ ] Проверен доступ к модалке и ручные операции под админом в проде.

## 6. Советы по отладке
- **Список не грузится** → проверьте `accounts/api/admin/teachers/` в Network и наличие токена; убедитесь, что пользователь с ролью `admin`.
- **Подписка не обновляется** → на сервере убедитесь, что `Subscription` существует (вызов `get_subscription` создаст триал). Проверьте, что часы сервера корректны.
- **Хранилище** → поле `extra_storage_gb` увеличивается кумулятивно. Отображаемый объём = `base_storage_gb + extra_storage_gb`.
- **Zoom** → если `zoom_client_secret` нужно скрыть, можно очищать input перед рендером и отправлять только при изменении.
- **Автообновление** → интервал 20 секунд можно отключить/изменить в `useEffect` при необходимости.

Следуя этому плану, можно безопасно обновить и расширить модальное окно «Управление учителями», сохранив синхронизацию между бэкендом и фронтендом, а также покрыв ключевые сценарии контроля преподавателей.
