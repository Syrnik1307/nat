# Инцидент: Незапланированные фронтенд-изменения на проде

**Дата:** 2026-03-04
**Severity:** P3 (низкая — функциональность не сломана, изменения корректны)
**Статус:** Закрыт (изменения оставлены)

## Что произошло

Задача: убрать кнопку «Профиль» из навбара ученика (1 строка в StudentNavBar.js).

При деплое `git pull` на проде не прошёл (грязное дерево + immutable-атрибуты на файлах). Решение: собрать `npm run build` локально и залить билд через scp.

**Проблема:** `npm run build` использует ВСЕ файлы из рабочего дерева, включая незакоммиченные. В локальном workspace было ~30+ изменённых фронтенд-файлов (apiService.js, NavBarNew.js, Recordings, homework-analytics, SupportWidget, featureFlags.js и др.). Все они попали в билд и были задеплоены на прод — хотя пользователь просил задеплоить только 1 изменение.

## Затронутые файлы (помимо запрошенного)

- frontend/src/apiService.js
- frontend/src/components/NavBarNew.js
- frontend/src/components/StudentDetailAnalytics.js
- frontend/src/components/SupportWidget.js
- frontend/src/config/featureFlags.js
- frontend/src/modules/Recordings/* (6+ файлов)
- frontend/src/modules/homework-analytics/* (6+ файлов)
- frontend/src/shared/components/index.js
- frontend/src/styles/StudentNavBar.css
- + новые файлы: SupportPage, AdminSupportPage, KnowledgeMapPanel, FileDropzone и др.

## Причина

1. `git pull` на проде заблокирован (грязное git-дерево + immutable attrs)
2. Обходной путь — scp полного билда — не учитывает, что билд содержит ВСЕ локальные изменения
3. Не было проверки: "какие ещё файлы изменены и попадут в билд?"

## Уроки (ПРАВИЛО для deploy-agent)

### ЗАПОМНИТЬ: npm run build = snapshot ВСЕГО локального кода

Перед `npm run build` для деплоя ОБЯЗАТЕЛЬНО:

1. **Проверить `git status`** — если есть незакоммиченные фронтенд-файлы, они ПОПАДУТ в билд
2. **Если нужно задеплоить только 1 изменение:**
   - `git stash` всех остальных изменений
   - `npm run build`
   - `git stash pop`
3. **Или:** задеплоить только изменённый исходник, а не весь билд:
   - scp только `StudentNavBar.js` → пересобрать билд НА сервере
4. **Предупреждать пользователя:** "В билд попадут ещё X незакоммиченных файлов. Продолжить?"

### Проблема git pull на проде

- На проде файлы build/ были с immutable-атрибутом (`chattr +i`) — вероятно от security hardening
- Git дерево грязное — есть локальные изменения на сервере
- **Решение на будущее:** очистить git дерево на проде, настроить нормальный git pull flow

## Действия

- [x] Изменения оставлены на проде (они корректные, просто незапланированные)
- [ ] Очистить git дерево на production-сервере
- [ ] Добавить pre-build check в deploy flow
