# Premium Minimalist Design - Quick Reference

## 🎨 Color Palette (Exact Hex Codes)

### Primary Colors
| Usage | Color Name | Hex Code | RGB |
|-------|-----------|----------|-----|
| **Primary Brand** | Indigo-600 | `#4F46E5` | rgb(79, 70, 229) |
| **Primary Hover** | Indigo-700 | `#4338CA` | rgb(67, 56, 202) |
| **Primary Light** | Indigo-500 | `#6366F1` | rgb(99, 102, 241) |
| **Primary Subtle** | Indigo-100 | `#E0E7FF` | rgb(224, 231, 255) |
| **Primary Pale** | Indigo-50 | `#EEF2FF` | rgb(238, 242, 255) |

### Neutral Colors
| Usage | Color Name | Hex Code | RGB |
|-------|-----------|----------|-----|
| **App Background** | Slate-50 | `#F8FAFC` | rgb(248, 250, 252) |
| **Card Background** | White | `#FFFFFF` | rgb(255, 255, 255) |
| **Border/Divider** | Slate-200 | `#E2E8F0` | rgb(226, 232, 240) |
| **Input Background** | Slate-100 | `#F1F5F9` | rgb(241, 245, 249) |
| **Dark Text** | Slate-900 | `#0F172A` | rgb(15, 23, 42) |
| **Body Text** | Slate-700 | `#334155` | rgb(51, 65, 85) |
| **Secondary Text** | Slate-500 | `#64748B` | rgb(100, 116, 139) |
| **Tertiary Text** | Slate-400 | `#94A3B8` | rgb(148, 163, 184) |

### Semantic Colors
| Usage | Color Name | Hex Code | RGB |
|-------|-----------|----------|-----|
| **Success** | Emerald-500 | `#10B981` | rgb(16, 185, 129) |
| **Success Light** | Emerald-200 | `#D1FAE5` | rgb(209, 250, 229) |
| **Error/Danger** | Rose-500 | `#F43F5E` | rgb(244, 63, 94) |
| **Error Light** | Rose-100 | `#FEE2E2` | rgb(254, 226, 226) |
| **Warning** | Amber-600 | `#D97706` | rgb(217, 119, 6) |
| **Warning Light** | Yellow-100 | `#FEF3C7` | rgb(254, 243, 199) |
| **Info** | Blue-500 | `#3B82F6` | rgb(59, 130, 246) |
| **Info Light** | Blue-100 | `#DBEAFE` | rgb(219, 234, 254) |

### Dark Mode (Admin Sidebar)
| Usage | Color Name | Hex Code | RGB |
|-------|-----------|----------|-----|
| **Sidebar Background** | Slate-900 | `#0F172A` | rgb(15, 23, 42) |
| **Sidebar Text** | Slate-200 | `#E2E8F0` | rgb(226, 232, 240) |
| **Sidebar Accent** | Indigo-400 | `#818CF8` | rgb(129, 140, 248) |

## 📏 Design Tokens

### Typography
```css
Font Family: 'Plus Jakarta Sans', 'Inter', sans-serif

Weights:
- 800: Logo, Extra Bold Headings
- 700: Section Headings, Important Text
- 600: Subheadings, Labels, Buttons
- 500: Body Text (emphasis)
- 400: Body Text (regular)

Sizes:
- 2.5rem (40px): Large stat numbers
- 2rem (32px): Page titles
- 1.5rem (24px): Section headings
- 1.125rem (18px): Card titles
- 1rem (16px): Body text
- 0.9375rem (15px): Secondary text
- 0.875rem (14px): Small text
- 0.8125rem (13px): Captions
- 0.75rem (12px): Uppercase labels
```

### Spacing
```css
Base: 1rem = 16px

Scale:
- 0.25rem (4px)
- 0.5rem (8px)
- 0.75rem (12px)
- 1rem (16px)
- 1.25rem (20px)
- 1.5rem (24px)
- 1.75rem (28px)
- 2rem (32px)
- 2.5rem (40px)
- 3rem (48px)
- 4rem (64px)
```

### Border Radius
```css
Small:  8px   (inputs, small buttons)
Medium: 12px  (dropdowns, badges)
Large:  16px  (cards, modals)
XLarge: 20px  (feature cards)
Pill:   999px (status badges, tags)
Circle: 50%   (avatars)
```

### Shadows
```css
/* Soft shadows with low opacity */
Small:  0 1px 3px rgba(0, 0, 0, 0.08)
Medium: 0 4px 12px rgba(79, 70, 229, 0.08)
Large:  0 10px 25px rgba(0, 0, 0, 0.1)
XLarge: 0 20px 50px rgba(0, 0, 0, 0.2)

/* Indigo glow for primary elements */
Primary: 0 4px 12px rgba(79, 70, 229, 0.3)
```

### Transitions
```css
/* Smooth easing */
Default: cubic-bezier(0.4, 0, 0.2, 1)
Duration: 0.15s - 0.2s
```

## 🖼️ Component Quick Copy-Paste

### Status Badge
```jsx
// Active (Green)
<span className="admin-status-badge active">Active</span>

// Inactive (Gray)
<span className="admin-status-badge inactive">Inactive</span>

// Pending (Yellow)
<span className="admin-status-badge pending">Pending</span>

// Expired (Red)
<span className="admin-status-badge expired">Expired</span>
```

### Action Button (Student)
```jsx
<button className="student-primary-btn">
  Continue Learning
</button>
```

### Three-Dot Menu (Admin)
```jsx
<div className="admin-action-menu">
  <button className="admin-action-menu-btn">⋯</button>
  {showDropdown && (
    <div className="admin-action-dropdown">
      <button className="admin-action-dropdown-item">
        Edit
      </button>
      <button className="admin-action-dropdown-item danger">
        Delete
      </button>
    </div>
  )}
</div>
```

### Progress Bar (Student)
```jsx
<div className="student-progress-container">
  <div className="student-progress-bar">
    <div 
      className="student-progress-fill" 
      style={{width: `${progress}%`}}
    />
  </div>
  <span>{progress}%</span>
</div>
```

### Stat Card (Admin)
```jsx
<div className="admin-stat-card">
  <span className="admin-stat-label">Total Users</span>
  <div className="admin-stat-value">1,234</div>
  <div className="admin-stat-change positive">
    <span className="admin-stat-change-icon">↑</span>
    12% this month
  </div>
</div>
```

## 📱 Responsive Breakpoints

```css
/* Tablet */
@media (max-width: 1024px) { }

/* Mobile landscape */
@media (max-width: 768px) { }

/* Mobile portrait */
@media (max-width: 480px) { }

/* Small mobile */
@media (max-width: 360px) { }
```

## ✨ Key Design Principles

### DO ✅
- Use exact hex colors (never generic "blue", "red")
- Apply soft shadows (0.08 - 0.1 opacity)
- Use 16-20px border-radius for cards
- Keep line-height at 1.5-1.6 for readability
- Apply hover states with translateY(-2px)
- Use uppercase for labels (0.05-0.08em letter-spacing)
- Prefer gradients for primary actions
- Use pastel backgrounds for status badges

### DON'T ❌
- Use vertical grid lines in tables
- Use harsh shadows (avoid opacity > 0.3)
- Use primary colors for large backgrounds
- Mix rounded and sharp corners
- Use more than 3 font weights per page
- Create action button clutter (use three-dot menus)
- Apply borders AND shadows (pick one)
- Use pure black text (#000000)

---

**Quick Color Test:**
- Primary: `#4F46E5` (Indigo)
- Background: `#F8FAFC` (Slate)
- Success: `#10B981` (Emerald)
- Error: `#F43F5E` (Rose)

**Logo Colors:**
- "Easy" = `#4F46E5` (Indigo-600)
- "Teaching" = `#1E293B` (Slate-800)
