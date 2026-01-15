# Nourish - Implementation Plan

Development phases and verification checklists.

---

## Implementation Phases

### Phase 1: Core Infrastructure
- [ ] Monorepo setup (pnpm workspaces)
- [ ] Fastify server with TypeScript
- [ ] PostgreSQL + Prisma schema
- [ ] Docker + docker-compose
- [ ] Simple JWT auth
- [ ] Basic Expo app shell
- [ ] Offline action queue infrastructure

### Phase 2: Onboarding & Setup
- [ ] Password setup screen
- [ ] Body stats + TDEE calculation
- [ ] Activity level + goal selection
- [ ] Eating schedule configuration
- [ ] Dietary restrictions
- [ ] Ingredient preferences swipe UI (~30 core)
- [ ] Contextual tooltips system

### Phase 3: Food System
- [ ] OpenFoodFacts API integration
- [ ] Food search with custom-first ordering
- [ ] Barcode lookup with incomplete data flow
- [ ] Custom food creation
- [ ] Mobile: food search UI
- [ ] Mobile: barcode scanner

### Phase 4: Meals & Logging
- [ ] Meals table + CRUD (with favorites)
- [ ] Meal ingredient builder with per-serving display
- [ ] Multi-person serving calculation
- [ ] Food log CRUD
- [ ] Serving fraction selector
- [ ] Quick-log from planned meals
- [ ] Deviation flow with voice explanation
- [ ] Mobile: dashboard with logged/planned display
- [ ] Mobile: food log screen

### Phase 5: Meal Planning
- [ ] Meal plans with day-number templates
- [ ] Week grid with multi-slot spanning
- [ ] Meal drawer with suggestions
- [ ] Tap-tap swap edit mode
- [ ] Soft over-goal warnings
- [ ] Shopping list generation (weight + packs)
- [ ] Adherence tracking
- [ ] Mobile: plan builder UI

### Phase 6: AI Features
- [ ] Whisper voice transcription
- [ ] Photo meal recognition (top 3 guesses)
- [ ] LLM meal template suggestions
- [ ] Chat agent with session-based history
- [ ] Confirmation for high-risk actions
- [ ] Graceful degradation
- [ ] Mobile: voice input UI
- [ ] Mobile: chat interface

### Phase 7: Body & Progress Tracking
- [ ] Measurements table
- [ ] Weight trend + TDEE calculation
- [ ] Progress photos with timeline scrubber
- [ ] Daily stats on photo view
- [ ] Combined weigh-in + photo notification
- [ ] Mobile: weight & body screen
- [ ] Mobile: progress photos screen

### Phase 8: Pantry
- [ ] Pantry inventory CRUD
- [ ] Auto-decrement with confirmation
- [ ] Low stock alerts
- [ ] Shopping list - pantry integration
- [ ] Mobile: pantry management UI

### Phase 9: Supplements & Polish
- [ ] Supplements CRUD + logging
- [ ] Streak tracking (per-day lenient)
- [ ] Smart notifications
- [ ] Offline sync with UI indicators
- [ ] Mobile: supplements checklist
- [ ] Mobile: profile screen

### Phase 10: Deployment
- [ ] VPS setup
- [ ] Caddy configuration
- [ ] Docker deployment
- [ ] EAS build for mobile

---

## Verification Checklist

### Backend
- [ ] Search food: `curl /api/foods/search?q=chicken`
- [ ] Barcode lookup with incomplete data handling
- [ ] Create meal with multi-person servings
- [ ] Log food entry with fraction servings
- [ ] Create meal plan with day-numbered templates
- [ ] Generate shopping list with weight + pack estimates
- [ ] Voice transcription works
- [ ] Photo recognition returns top 3
- [ ] Chat agent with session history
- [ ] Offline entries sync correctly

### Mobile
- [ ] Complete onboarding flow (all required steps)
- [ ] Ingredient preferences swipe (~30 + show more)
- [ ] Dashboard shows logged + planned (greyed)
- [ ] Tap planned meal → quick-log sheet
- [ ] Search shows custom foods first
- [ ] Create meal with ingredient breakdown
- [ ] Build plan with multi-slot meals
- [ ] Tap-tap swap in edit mode
- [ ] Log deviation with voice explanation
- [ ] Progress photos timeline scrubber
- [ ] Log offline and verify sync icons

### End-to-End
- [ ] Full week: plan → shop → cook → log → analyze
- [ ] Multi-person meal: cook for 4, log 1.5 servings
- [ ] Pantry decrements with confirmation
- [ ] Progress photo shows stats for that day
- [ ] Streak continues with at least one meal logged
- [ ] Photo AI → manual fallback flow
