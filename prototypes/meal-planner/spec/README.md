# Nourish - Health Tracker App Specification

## Overview

A self-hosted mobile app (iOS/Android) for meal planning, food tracking, and health analytics with AI-powered features.

| Decision | Choice |
|----------|--------|
| Name | **Nourish** |
| Platform | React Native + Expo (mobile only, portrait locked) |
| Backend | Self-hosted VPS with Fastify + PostgreSQL |
| Users | Single-user (password auth only) |
| Theme | Light mode |
| Offline | Queue offline actions, sync when reconnected |
| Design | Clean minimal - Apple Health style |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Mobile | React Native + Expo + TypeScript |
| Backend | Fastify + TypeScript + Prisma ORM |
| Database | PostgreSQL |
| Infrastructure | Docker + Caddy (auto HTTPS) on VPS |
| AI - Voice | OpenAI Whisper |
| AI - Vision/LLM | Mix of Claude / GPT-4 (best per task) |
| Food Database | OpenFoodFacts API (primary) |

---

## Navigation Architecture

### 4 Tabs + Profile Button

```
┌─────────────────────┐
│ [☰ Profile]    Title│  ← Top bar with profile button
├─────────────────────┤
│                     │
│   Screen Content    │
│                     │
├─────────────────────┤
│  🏠    📋    📅   🍽️  │  ← Bottom tab bar (4 tabs)
│ Home  Log  Plans Meals│
└─────────────────────┘
      [💬] Floating Chat FAB
```

**Tab Bar:**
1. **Home** - Dashboard with today's overview
2. **Log** - Food log with daily entries
3. **Plans** - Meal planning (active plan + templates)
4. **Meals** - Recipe/meal library

**Profile Screen (accessed via ☰):**
- Progress Photos
- Weight & Body
- Supplements
- Analytics
- Pantry
- Settings

---

## Key UI/UX Decisions

| Area | Decision |
|------|----------|
| Navigation | 4 tabs + Profile screen (not drawer) |
| Onboarding | Required: password, stats, activity, goal, schedule, restrictions, ~30 prefs |
| Dashboard | Shows logged (solid) + planned (greyed), tap planned for quick-log |
| Food search | Custom foods first, then database |
| Photo AI | Always show top 3 guesses |
| Barcode incomplete | Prompt to complete via photo or manual input |
| Serving input | Fraction selector (0.5, 1, 1.5, 2, custom) |
| Deviation | Required inline with voice/text explanation + quick tags |
| Plan warnings | Inline badge (⚠️ +50) - soft warning, can save anyway |
| Multi-slot meals | Span cells visually (merged) |
| Edit mode | Tap-tap to swap |
| Templates | Day numbers (flexible start date) |
| Favorites | Star system in meal library |
| Progress photos | Horizontal timeline scrubber with daily stats |
| Quick add | Hidden in menu (for eating out estimates) |
| Pantry | Auto-decrement with confirmation prompt |
| Notifications | Smart only (if not already logged) |
| Chat | Session-based, confirm required for high-risk actions |
| Voice | Show transcript after completion |
| Offline | Clear UI with sync icons on pending items |
| Timezone | Follow device |
| Streak | Per day lenient (at least one meal logged) |
| Halal warnings | Conservative (flag anything questionable) |

---

## Spec Files

- **[screens.md](./screens.md)** - All UI wireframes (onboarding + main screens)
- **[features.md](./features.md)** - Feature specifications and behaviors
- **[technical.md](./technical.md)** - Data model and API endpoints
- **[implementation.md](./implementation.md)** - Development phases and checklists
