---
name: ui-ux-designer
description: Enforce Premium AI Industry Standard Design (Glassmorphism, Dark Mode, Micro-interactions). Use when modifying ANY frontend component to ensure "wow" factor.
---

# Premium UI/UX Designer Skill

This skill enforces a high-end, "AI-native" aesthetic inspired by Linear, Vapi, and modern SaaS dashboards.

## Core Design Principles

### 1. Typography (The "Premium" Feel)

- **Font**: Use `Inter` or `Geist Sans`.
- **Sizing**: Default text should be `text-sm` (14px). Use `text-xs` (12px) for metadata.
- **Headings**: `text-lg` or `text-xl` is usually large enough for section headers. `text-3xl` only for main page titles.
- **Tracking**: Use `tracking-tight` on almost ALL text larger than `text-xs`.
- **Color**: Never use pure black/white.
  - Primary text: `text-slate-50` (Dark Mode) / `text-gray-900` (Light Mode)
  - Secondary: `text-slate-400` / `text-gray-500`
  - Tertiary: `text-slate-500` / `text-gray-400`

### 2. The Glassmorphism & Borders System

- **Cards**:
  - Dark: `bg-slate-900/50 backdrop-blur-md border border-slate-800/50`
  - Light: `bg-white/70 backdrop-blur-md border border-gray-100 shadow-sm`
- **Borders**: Subtle is key. `border-slate-800` (dark) or `border-gray-200` (light).
- **Rounding**: `rounded-xl` or `rounded-2xl` for containers. `rounded-lg` for internal elements (buttons, inputs).

### 3. Layout

- **Spacing**: Use multiples of 4 (1rem). `p-6` for cards, `gap-4` or `gap-6` for grids.
- **Grids**: Use "Bento Box" style grids for metrics.
- **Whitespace**: Don't crowd elements. "Airy" interfaces feel expensive.

### 4. Interaction & Performance

- **No Page Reloads**: Use Client Components with SWR/React Query for data.
- **Skeleton Loaders**: NEVER show a spinning global loader for a small component update. Use skeletons where the content will appear.
- **Transitions**: `transition-all duration-200 ease-in-out` on interactive elements.
- **Hover Effects**: `hover:bg-slate-800` (dark) or `hover:bg-gray-50` (light) for table rows/list items.

## Refactoring Checklist (The "Ugly" Fixer)

When user says "Ugly" or "Cheap", check for:

1. [ ] **Font Sizes**: Is everything too big? Downscale `text-base` to `text-sm`.
2. [ ] **Contrast**: Is secondary text too faint? Or too bold?
3. [ ] **Borders**: Are borders thick (2px)? Make them 1px and subtle.
4. [ ] **Shadows**: Are shadows generic? Use colored shadows or subtle diffused shadows.
5. [ ] **Loading**: Is the whole screen flashing white? Fix the loading state to be local.

## Example Component Implementation

```tsx
// Premium Card Example
<div className="group relative p-6 rounded-2xl border border-slate-800/60 bg-slate-900/40 backdrop-blur-sm hover:bg-slate-800/60 transition-all duration-300">
  <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-emerald-500/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
  <h3 className="text-sm font-medium text-slate-400 tracking-tight">Total Revenue</h3>
  <div className="mt-2 flex items-baseline gap-2">
    <span className="text-2xl font-semibold text-slate-50 tracking-tight">$45,231.89</span>
    <span className="text-xs font-medium text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded-full">+20.1%</span>
  </div>
</div>
```
