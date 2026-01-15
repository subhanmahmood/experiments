# Nourish - Technical Specification

Database schema and API endpoints.

---

## Data Model

### Core Tables

```sql
-- Foods (from API or custom)
foods (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  brand VARCHAR(100),
  barcode VARCHAR(50),
  source VARCHAR(50), -- 'openfoodfacts', 'custom', 'ai_estimated', 'restaurant'
  external_id VARCHAR(100),
  is_custom BOOLEAN,
  data_verified BOOLEAN DEFAULT true,
  created_at TIMESTAMP
)

-- Serving units per food
food_servings (
  id UUID PRIMARY KEY,
  food_id UUID REFERENCES foods,
  unit_name VARCHAR(50),
  grams_equivalent DECIMAL,
  is_default BOOLEAN
)

-- Nutrition per food (per 100g base)
food_nutrition (
  food_id UUID PRIMARY KEY REFERENCES foods,
  calories DECIMAL,
  protein_g DECIMAL,
  carbs_g DECIMAL,
  fat_g DECIMAL,
  fiber_g DECIMAL,
  sugar_g DECIMAL,
  sodium_mg DECIMAL,
  vitamin_a_iu DECIMAL,
  vitamin_c_mg DECIMAL,
  vitamin_d_iu DECIMAL,
  calcium_mg DECIMAL,
  iron_mg DECIMAL,
  potassium_mg DECIMAL
)

-- Meals (recipes)
meals (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  description TEXT,
  servings_made INTEGER,
  is_favorite BOOLEAN DEFAULT false,
  created_at TIMESTAMP,
  deleted_at TIMESTAMP
)

-- Meal ingredients
meal_ingredients (
  id UUID PRIMARY KEY,
  meal_id UUID REFERENCES meals,
  food_id UUID REFERENCES foods,
  amount_grams DECIMAL,
  unit_display VARCHAR(50),
  sort_order INTEGER
)

-- Meal plans
meal_plans (
  id UUID PRIMARY KEY,
  name VARCHAR(100),
  start_date DATE,
  end_date DATE,
  is_active BOOLEAN,
  is_template BOOLEAN DEFAULT false,
  created_at TIMESTAMP
)

-- Planned meals in a plan
planned_meals (
  id UUID PRIMARY KEY,
  meal_plan_id UUID REFERENCES meal_plans,
  meal_id UUID REFERENCES meals,
  day_number INTEGER, -- Day 1, Day 2, etc. (not date for templates)
  date DATE, -- NULL for templates
  meal_slots VARCHAR(20)[],
  sort_order INTEGER
)

-- Food log entries (copies of meals, not references)
food_log (
  id UUID PRIMARY KEY,
  date DATE,
  meal_slot VARCHAR(20),
  source_meal_id UUID REFERENCES meals,
  meal_name VARCHAR(255),
  servings DECIMAL,
  calories DECIMAL,
  protein_g DECIMAL,
  carbs_g DECIMAL,
  fat_g DECIMAL,
  fiber_g DECIMAL,
  planned_meal_id UUID REFERENCES planned_meals,
  is_deviation BOOLEAN,
  deviation_reason VARCHAR(50),
  deviation_note TEXT,
  synced BOOLEAN DEFAULT true,
  created_at TIMESTAMP
)

-- Pantry inventory
pantry (
  id UUID PRIMARY KEY,
  food_id UUID REFERENCES foods,
  name VARCHAR(255),
  quantity_grams DECIMAL,
  unit_display VARCHAR(50),
  min_threshold_grams DECIMAL,
  location VARCHAR(50),
  store VARCHAR(50),
  expiry_date DATE,
  updated_at TIMESTAMP
)

-- Body measurements
measurements (
  id UUID PRIMARY KEY,
  date DATE,
  weight_kg DECIMAL,
  body_fat_pct DECIMAL,
  synced BOOLEAN DEFAULT true,
  created_at TIMESTAMP
)

-- Progress photos
progress_photos (
  id UUID PRIMARY KEY,
  date DATE,
  photo_path VARCHAR(500),
  created_at TIMESTAMP
)

-- Supplements
supplements (
  id UUID PRIMARY KEY,
  name VARCHAR(255),
  dosage VARCHAR(100),
  created_at TIMESTAMP
)

-- Supplement log
supplement_log (
  id UUID PRIMARY KEY,
  supplement_id UUID REFERENCES supplements,
  date DATE,
  time_taken TIME,
  taken BOOLEAN DEFAULT true,
  created_at TIMESTAMP
)

-- Ingredient preferences
ingredient_preferences (
  id UUID PRIMARY KEY,
  food_id UUID REFERENCES foods,
  category VARCHAR(50),
  preference_level INTEGER, -- 1=love, 2=like, 3=ok, 4=avoid_taste, 5=never
)

-- User settings
settings (
  id UUID PRIMARY KEY,
  password_hash VARCHAR(255),
  height_cm DECIMAL,
  current_weight_kg DECIMAL,
  age INTEGER,
  sex VARCHAR(10),
  activity_level VARCHAR(20),
  goal_type VARCHAR(20),
  goal_rate DECIMAL,
  target_calories INTEGER,
  target_protein_g INTEGER,
  target_carbs_g INTEGER,
  target_fat_g INTEGER,
  dietary_restrictions TEXT[],
  eating_schedule JSONB,
  notification_weigh_time TIME,
  notification_meal_delay_min INTEGER,
  debug_mode BOOLEAN DEFAULT false,
  updated_at TIMESTAMP
)

-- Chat agent sessions
chat_sessions (
  id UUID PRIMARY KEY,
  context VARCHAR(50),
  messages JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

---

## API Endpoints

### Auth
```
POST /api/auth/login              { password } → { token }
POST /api/auth/change-password    { old, new }
```

### Foods
```
GET  /api/foods/search?q=         Search local + OpenFoodFacts
GET  /api/foods/barcode/:code     Barcode lookup
GET  /api/foods/recent            Recently logged (2 weeks)
GET  /api/foods/favorites         Most logged (starred)
GET  /api/foods/:id               Food detail
POST /api/foods                   Create custom food
```

### Meals
```
GET  /api/meals                   List saved meals
GET  /api/meals/:id               Meal with ingredients
POST /api/meals                   Create meal
PUT  /api/meals/:id               Update meal
DELETE /api/meals/:id             Soft delete meal
POST /api/meals/:id/favorite      Toggle favorite
POST /api/meals/suggest           LLM template suggestion
```

### Food Log
```
GET    /api/log?date=             Day's entries
GET    /api/log/summary?date=     Daily totals
POST   /api/log                   Add entry
PATCH  /api/log/:id               Update entry
DELETE /api/log/:id               Delete entry
POST   /api/log/:id/deviation     Log deviation reason
POST   /api/log/sync              Sync offline entries
```

### Meal Plans
```
GET    /api/plans                 List plans
GET    /api/plans/templates       List templates
GET    /api/plans/:id             Plan with meals
POST   /api/plans                 Create plan
PUT    /api/plans/:id             Update plan
DELETE /api/plans/:id             Delete plan
POST   /api/plans/:id/meals       Add meal to plan
DELETE /api/plans/:id/meals/:mid  Remove meal
POST   /api/plans/:id/apply       Copy plan to food log
POST   /api/plans/:id/save-template
GET    /api/plans/:id/shopping    Generate shopping list
GET    /api/plans/:id/adherence   Get adherence stats
```

### Pantry
```
GET    /api/pantry                List inventory
POST   /api/pantry                Add item
PATCH  /api/pantry/:id            Update quantity
DELETE /api/pantry/:id            Remove item
POST   /api/pantry/consume        Log consumption
GET    /api/pantry/low-stock      Items below threshold
```

### Measurements
```
GET  /api/measurements?range=     Weight history
POST /api/measurements            Log weight
GET  /api/measurements/trend      Trend data
GET  /api/measurements/tdee       TDEE estimate
```

### Progress Photos
```
GET  /api/progress-photos         List photos with stats
POST /api/progress-photos         Upload photo
GET  /api/progress-photos/:date   Get photo + stats for date
```

### Supplements
```
GET    /api/supplements           List supplements
POST   /api/supplements           Add supplement
DELETE /api/supplements/:id       Remove supplement
POST   /api/supplements/log       Log supplement taken
GET    /api/supplements/history   Supplement history
```

### Preferences
```
GET  /api/preferences             Ingredient preferences
POST /api/preferences             Set preferences (batch)
GET  /api/preferences/eating-schedule
POST /api/preferences/eating-schedule
```

### Dashboard
```
GET /api/dashboard/today          Today's summary (with streak)
GET /api/dashboard/week           Weekly stats
```

### AI
```
POST /api/ai/transcribe           Voice → text
POST /api/ai/photo-meal           Photo → meal match
POST /api/ai/photo-pantry         Photo → pantry items
POST /api/ai/parse-command        Text → structured action
POST /api/ai/chat                 Chat agent interaction
GET  /api/ai/chat/sessions        Chat session history
```
