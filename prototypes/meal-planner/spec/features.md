# Nourish - Feature Specifications

Detailed feature specifications, behaviors, and edge cases.

---

## 1. Food & Ingredient System

### Food Database
- Primary source: OpenFoodFacts API (free, good UK/EU coverage, barcode support)
- Also lookup restaurant nutrition info (McDonald's, chains, etc.) when available
- Cache searched foods locally to reduce API calls
- Support custom user-created foods
- Show data source badge: "From OpenFoodFacts" / "Custom entry" / "AI estimated"
- Show warning badge for suspicious/incomplete nutrition data

### Serving Size Handling (MFP-style)
- All ingredients stored/added by weight (grams)
- Can show approximations (e.g., "1 chicken breast ≈ 150g")
- User can switch between units when logging
- Fractions allowed for servings (0.5, 1, 1.5, 2, etc.)

### Serving Memory
- If user logs different quantity 5+ times, prompt: "Update default amount?"
- Recent foods shown in date-descending order

### Custom Foods
- Create foods with full nutrition data
- Required: name, serving size, calories, protein, carbs, fat
- Optional: fiber, sugar, sodium, full micronutrients

### Barcode Not Found Flow
1. Photo the product for LLM name inference, OR
2. Manual text input for name
3. Then search/create custom food

---

## 2. Meals (Recipes)

Meals are composite foods built from ingredients.

### Meal Creation Methods
1. **Sequential add**: Add ingredients one at a time with amounts (by weight)
2. **Batch entry**: Quick-add multiple ingredients rapidly, then adjust amounts
3. **LLM template suggestions**:
   - User says "steak and fried rice"
   - LLM uses tool to search food database
   - Returns structured ingredient list with standard portions
   - Asks "Is this for 1 person or more?" for multi-person cooking
   - User confirms/edits before saving

### Multi-Person Cooking Support
- User specifies total ingredients used and number of servings made
- App calculates per-serving nutrition automatically
- User logs how many servings they personally ate

### Meal Entries vs Meal Templates
- Meals (templates) and log entries are SEPARATE entities
- When logging, meal is COPIED into the entry
- Editing an entry only affects that entry
- Editing the meal template doesn't change historical entries
- Deleting a meal = soft delete (hidden from library, exists for history)

---

## 3. Meal Planning

### User Eating Timetable
- Capture user's eating style during onboarding
- Standard / Intermittent fasting / Custom slots

### Week View Interface
- Portrait orientation with days as rows
- Scroll vertically through days
- Day-numbered templates (Day 1, Day 2...) for flexibility

### Multi-Slot Meals
- A meal can span multiple slots (brunch = breakfast + lunch)
- Shown once but spans cells visually

### Calorie/Macro Enforcement
- Soft warning (inline badge) for days exceeding goal
- Can save anyway - no blocking

### Plan Adherence Tracking
- Calculate adherence score (% of planned meals followed)
- Deviation = eating completely different meal (not portion difference)
- Skipped meals ≠ deviation

---

## 4. Food Logging

### Manual Logging
- Search by name (searches local DB + OpenFoodFacts)
- Barcode scanning (expo-camera)
- Recent foods (last 2 weeks, date-descending)
- Favorites (all-time count, star system)
- Select serving size/unit, enter quantity

### Photo Meal Recognition
- Take photo of meal
- Always show top 3 guesses
- User can tap "Search Manually" if none match

### Voice Logging
- "I had two eggs and toast for breakfast"
- Voice transcribed → LLM parses → searches food DB
- Shows transcript after completion for confirmation

### Quick Add Calories
- Hidden in menu (⋯)
- For eating out estimates when detailed logging impractical

---

## 5. Pantry Management

**Priority: Secondary** - Can be simpler or come later

### Inventory Tracking
- Each pantry item: name, quantity (weight), unit, location
- Auto-decrement with confirmation after logging meals

### Low Stock Alerts
- Push notification when item drops below threshold
- Warning when creating meal plan that needs unavailable ingredients
- Dashboard indicator showing low stock count

### Shopping List Integration
- Group by store: Supermarket, Halal shop, Costco
- Show both weight needed AND pack size estimate

---

## 6. Weight & Body Tracking

### Data Points
- Weight (kg)
- Body fat percentage
- From smart scale readings (manual input)

### Features
- Log weight with daily reminder (combined with progress photo)
- View weight trend chart
- Show estimated TDEE after sufficient data

---

## 7. Progress Photos

### Daily photo with context
- Horizontal timeline scrubber
- Each date shows: photo, weight, calories, macros, meals eaten
- Drag to browse through history
- Reminder combined with morning weigh-in

---

## 8. Nutrition Tracking

### Data Storage
- Store FULL micronutrient data for all foods/meals
- Macros: calories, protein, carbs, fat
- Extended: fiber, sugar, sodium, cholesterol
- Micros: vitamins, minerals

### UI Display
- Dashboard shows only: Calories, Protein, Carbs, Fat
- Detailed views show full nutrition with source info

---

## 9. Supplement Tracking

- Log vitamins/supplements taken daily
- Simple checklist style
- Track consistency/streaks

---

## 10. AI Chat Agent

### Architecture
- Floating chat button throughout app
- Text or voice input
- Session-based (fresh each time, archive of past sessions)

### Context Awareness
- Screen-specific agents for specific tasks
- Task-specific agents can pull context from elsewhere if needed

### Capabilities
- Every UI action should be doable via agent
- Has tools to search food database
- Prevents hallucinated ingredients

### Confirmation Rules
- Low-risk (search, suggest): no confirm
- High-risk (add, delete, log): confirm first

---

## 11. AI Features Summary

| Feature | AI Type | Provider | Fallback |
|---------|---------|----------|----------|
| Meal template suggestions | LLM with tools | Claude / GPT-4 | Generic substitutes |
| Photo meal recognition | Vision + reasoning | GPT-4 Vision / Claude | Manual entry |
| Pantry photo onboarding | Vision | GPT-4 Vision / Claude | Manual entry |
| Voice transcription | Speech-to-text | OpenAI Whisper | Text input |
| Voice/text commands | LLM with tools | Claude / GPT-4 | Manual UI |
| Restaurant meal estimation | LLM | Claude / GPT-4 | Rough estimate |

---

## 12. Authentication & Sessions

- Single password authentication
- Stay logged in forever (no re-auth required)

---

## 13. Error Handling

- User-friendly actionable messages by default
- Settings toggle for debug mode
- AI failures: graceful degradation to manual options

---

## 14. Offline Support

- Queue offline actions (food logs, weight entries)
- Sync when connection restored
- Clear UI with sync icons on pending items

---

## Edge Cases & Behaviors

### Halal Warnings (Conservative)
Any food with questionable ingredients shows:
```
⚠️ May not be halal
   Check label for gelatin source
```

### Meal Edit Scope
- Editing a saved meal only affects **future** uses
- Existing plan slots keep the version at time of assignment
- Past food log entries are snapshots, never change

### Template Structure
- Templates use Day 1, Day 2, Day 3... (not Mon/Tue)
- When applying, user picks start date
- Flexible for any schedule

### Streak Rules
- Streak continues if **at least one meal logged** that day
- Missing individual meals doesn't break streak
- Only a completely unlogged day resets

### Timezone
- Always follows device timezone
- Meals shift to local time when traveling
