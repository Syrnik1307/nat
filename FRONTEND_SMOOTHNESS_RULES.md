# 🎭 Frontend UX Smoothness Rules - ОБЯЗАТЕЛЬНО К ВЫПОЛНЕНИЮ

## Цель

Все изменения фронтенда должны обеспечивать **плавный, мягкий UI** без "лязга" и "дребезга". Глаз пользователя не должен уставать от резких переходов.

---

## 🚫 ЗАПРЕЩЕНО

1. **Резкие появления элементов** - никогда `display: none → display: block` без анимации
2. **Мгновенные смены состояний** - loading → content без fade
3. **Прыжки layout (CLS)** - когда контент загружается и "прыгает"
4. **Линейные анимации** - `transition-timing-function: linear` выглядит механически
5. **Слишком быстрые transitions** - меньше 150ms не воспринимается глазом
6. **Слишком медленные transitions** - больше 500ms раздражает

---

## ✅ ОБЯЗАТЕЛЬНО

### 1. Используйте CSS токены из `smooth-transitions.css`

```css
/* ❌ ПЛОХО */
transition: all 0.2s ease;

/* ✅ ХОРОШО */
transition: 
  opacity var(--transition-hover),
  transform var(--transition-hover);
```

### 2. Все интерактивные элементы = transition

```css
/* Любая кнопка, карточка, ссылка */
.my-button {
  transition: 
    opacity var(--duration-fast) var(--ease-smooth),
    transform var(--duration-fast) var(--ease-smooth),
    background-color var(--duration-fast) var(--ease-smooth);
}
```

### 3. Loading → Content = плавный fade

```jsx
// ❌ ПЛОХО
{loading ? <Spinner /> : <Content />}

// ✅ ХОРОШО
<div className={`content ${loading ? 'is-loading' : 'is-loaded'}`}>
  {loading && <div className="loading-overlay is-loading"><Spinner /></div>}
  <div className="animate-content">
    <Content />
  </div>
</div>
```

### 4. Skeleton loaders вместо пустоты

```jsx
// ❌ ПЛОХО - резкое появление данных
{data ? <List items={data} /> : null}

// ✅ ХОРОШО - skeleton пока грузится
{data ? (
  <div className="animate-stagger">
    <List items={data} />
  </div>
) : (
  <div className="skeleton-list">
    <div className="skeleton skeleton-card"></div>
    <div className="skeleton skeleton-card"></div>
  </div>
)}
```

### 5. Модалки с плавным появлением

```css
/* Backdrop */
.modal-backdrop {
  opacity: 0;
  backdrop-filter: blur(0);
  transition: 
    opacity var(--duration-slow) var(--ease-smooth),
    backdrop-filter var(--duration-slow) var(--ease-smooth);
}

.modal-backdrop.is-open {
  opacity: 1;
  backdrop-filter: blur(8px);
}

/* Modal content */
.modal-content {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
  transition: 
    opacity var(--duration-slow) var(--ease-spring),
    transform var(--duration-slow) var(--ease-spring);
}

.modal-content.is-open {
  opacity: 1;
  transform: scale(1) translateY(0);
}
```

### 6. Табы и переключатели

```jsx
// Оберните контент таба
<div className="animate-tab-content" key={activeTab}>
  {tabContent}
</div>
```

### 7. Списки с каскадной анимацией

```jsx
<ul className="animate-stagger">
  {items.map(item => <li key={item.id}>{item.name}</li>)}
</ul>
```

---

## 📏 Timing Reference

| Действие | Duration | Easing |
|----------|----------|--------|
| Hover подсветка | 180ms | `--ease-smooth` |
| Клик/фокус | 180ms | `--ease-out-soft` |
| Переключение табов | 280ms | `--ease-smooth` |
| Появление контента | 280ms | `--ease-out-soft` |
| Открытие модалки | 400ms | `--ease-spring` |
| Закрытие модалки | 280ms | `--ease-smooth` |

---

## 🎨 Готовые классы

```css
/* Появление страницы */
.animate-page-enter

/* Fade in контента */
.animate-content

/* Каскад для списков */
.animate-stagger

/* Модалка */
.animate-modal-enter

/* Loading пульсация */
.animate-loading

/* Skeleton shimmer */
.skeleton, .skeleton-text, .skeleton-card, .skeleton-avatar

/* Hover эффекты */
.hover-lift       /* Поднятие на 4px */
.hover-lift-soft  /* Мягкое поднятие 2px */
.hover-grow       /* Scale 1.02 */
.hover-glow       /* Glow ring */
```

---

## 🔧 Проверка перед коммитом

1. [ ] Все новые компоненты имеют transition на интерактивных элементах
2. [ ] Loading states используют fade/skeleton, не резкую смену
3. [ ] Модалки появляются с анимацией
4. [ ] Нет CLS (Cumulative Layout Shift) - контент не "прыгает"
5. [ ] `prefers-reduced-motion` учтён (наша система это делает автоматически)

---

## 📚 Файлы системы

- `src/styles/smooth-transitions.css` - основная система анимаций
- `src/styles/design-system.css` - дизайн токены
- `FRONTEND_SMOOTHNESS_RULES.md` - этот документ

---

## 💡 Принцип

> **"Если анимация заметна - она слишком резкая. Хорошая анимация ощущается, но не отвлекает."**
