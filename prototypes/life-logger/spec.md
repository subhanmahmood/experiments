# Life Logger App - Product Spec

## Overview

An hourly check-in app that uses voice input and AI to log how you spend your time, producing a heatmap visualization over time. The goal is to document every waking hour for a year or more, creating a detailed record of how time is spent.

---

## Core Flow

```
Hourly push notification (during active hours)
       ↓
   [Record voice]  or  [Quick-tap category + optional note]  or  [Skip]
       ↓
Audio stored immediately → Sent to transcription service
       ↓
LLM: summarize → categorize (using past corrections as context)
       ↓
Entry auto-saved (user can edit/override)
       ↓
User can edit any entry within 24 hours of its timestamp

End of day
       ↓
App enters "Review Mode" - must fill gaps before continuing
       ↓
[Fill individually] or [Bulk fill: "Xpm-Ypm was Z"]
       ↓
If not completed before sleep → Morning prompt to complete yesterday's review
```

---

## Features

### 1. Hourly Prompts
- **Push notification from server** every hour during user-defined active hours
- Serverless scheduled function (Cloudflare Workers / Vercel Cron) triggers pushes
- **Subtle vibration only** - no sound
- **Persistent notification** for current hour
- Older missed hours become **badge count only** (notifications don't stack)
- Tap to open voice recorder

### 2. Voice Input
- Speak freely about the **past hour** (what did you do in the last hour?)
- Typical entry: **30-60 seconds**
- Audio stored immediately to object storage, then sent to transcription
- Works offline: audio queued locally, uploaded when connected

### 3. Quick-Tap Mode (Silent Fallback)
- For situations where speaking is awkward (meetings, library, etc.)
- **Grid of icons** showing all categories
- Tap category → optionally type a short note → done
- Works fully offline

### 4. AI Processing
- **Transcription**: Whisper or equivalent (mix of providers for best quality)
- **Summarization**: Generate short summary (~10-20 words)
- **Categorization**: Auto-assign high-level category, optionally subcategory
- **Context**: LLM sees recent entries + past corrections (prompt injection) to improve accuracy
- **Latency**: Instant processing, cost acceptable
- **Auto-save**: Entry saves immediately after LLM processing
- **Error handling**: Show error immediately if transcription/LLM fails, let user retry or save manually

### 5. Manual Overrides
- Edit summary, category, or subcategory after the fact
- **Correction feedback**: Dropdown to pick correct category + optional reason why LLM was wrong
- Corrections stored and injected into future prompts to improve categorization
- **24-hour edit window**: Entries become read-only 24 hours after their timestamp

### 6. Sleep Logging
- Manually mark **"going to sleep"** and **"waking up"**
- When "waking up" is logged, **auto-fill all hours since "going to sleep"** with individual Sleep entries
- Sleep hours are regular entries in the Rest category

### 7. Missed Hour Handling
- Missed hours left blank during the day (shown as outline only in heatmap)
- **End-of-day Review Mode**: Separate app mode you must complete before normal use
- Cannot access main app until all gaps for the day are filled
- **Must complete**: No snooze or dismiss option
- If review not done before bed → **Morning prompt** forces completion before new day starts
- **Batch backfill**: Select time range, assign one category to all hours
- After 24 hours, gaps become permanently blank (no retroactive editing)

### 8. Offline Support
- **Hybrid offline mode**
- Can record voice offline: audio stored locally, queued for upload
- Can quick-tap categories offline
- Entries sync when connectivity returns
- No transcription/LLM processing until online

---

## Visualization

### Default View: Year (Calendar-style)
- **Hours as columns** (24), **days as rows** (365)
- Each cell colored by category
- **Inactive hours** (outside active hours) shown but **dimmed**
- **Empty hours** (within active hours, no entry) shown as **outline only**
- **8 separate cells** for consecutive same-category hours (no visual merging)
- **Virtualized rendering** (FlashList or similar) for performance

### Navigation
- Default landing: **Full year view**
- Drill down: Year → Month → Week → Day
- **Date picker** to jump to specific date
- Tap any cell → Full entry detail (summary, category, subcategory, transcript)
- **Transcript hidden by default**, expandable on tap

### Views Available
- Year view (default)
- Month view
- Week view
- Day view (24-hour timeline)

---

## Categories

### High-Level (12 Categories)

| Category      | Icon (system default) | Subcategories (examples)              |
|---------------|-----------------------|---------------------------------------|
| Work          | Briefcase             | Deep work, Meetings, Admin, Email     |
| Exercise      | Dumbbell              | Gym, Walk, Sports, Stretching         |
| Social        | People                | Friends, Family, Dating               |
| Rest          | Moon                  | Sleep, Nap, Downtime                  |
| Entertainment | TV                    | TV, Games, Reading, Music             |
| Learning      | Book                  | Course, Reading, Practice             |
| Chores        | Home                  | Cleaning, Errands, Cooking            |
| Travel        | Car                   | Commute, Trip, Walking                |
| Prayer        | Hands                 | (user-defined)                        |
| Health        | Heart                 | Medical, Therapy, Doctor              |
| Self-care     | Spa                   | Grooming, Relaxation, Mental health   |
| Spiritual     | Sparkle               | Religious study, Meditation           |

- Users can add custom categories and subcategories
- **Primary activity wins** when an hour spans multiple categories
- System-default icons, category colors TBD

---

## Data Model

```typescript
Entry {
  id              string (uuid)
  user_id         string (fk)
  timestamp       datetime (hour block, e.g., "2024-01-15T14:00:00Z")
  summary         string (~10-20 words, LLM-generated)
  transcript      string (full transcription, hidden by default in UI)
  audio_url       string (S3/R2 URL)
  category        string (high-level)
  subcategory     string? (optional)
  input_type      enum: "voice" | "quick_tap"
  backfilled      boolean (was this filled retroactively?)
  llm_feedback    string? (user feedback when correcting categorization)
  created_at      datetime
  updated_at      datetime
}

UserSettings {
  id              string (uuid)
  user_id         string (fk)
  active_hours    { start: string, end: string } (e.g., "07:00", "23:00")
  timezone        string (e.g., "America/New_York")
  categories      Category[] (custom additions)
  created_at      datetime
  updated_at      datetime
}

Category {
  id              string (uuid)
  user_id         string? (null for defaults)
  name            string
  icon            string (system icon name)
  color           string (hex, TBD)
  subcategories   string[]
  is_default      boolean
  sort_order      number
}

CorrectionExample {
  id              string (uuid)
  user_id         string (fk)
  transcript      string (what user said)
  wrong_category  string (what LLM guessed)
  correct_category string (what user corrected to)
  feedback        string? (optional reason)
  created_at      datetime
}
```

---

## Day Boundaries & Time Semantics

- **Calendar day**: Midnight is the cutoff (12:00am = new day)
- **Analysis perspective**: Wake-to-sleep defines a "logical day"
- **Entries represent past hour**: 9:00 notification asks "What did you do 8-9am?"
- **Active hours**: User-defined, single schedule for all days
- **Inactive hours**: Shown dimmed in heatmap, no notifications sent

---

## Storage & Infrastructure

### Database
- **Local dev**: PostgreSQL
- **Production**: Render PostgreSQL
- No analytics or telemetry

### Audio Storage
- **Provider**: S3, R2, or Cloudflare
- Audio stored immediately on record
- Kept indefinitely (full transcript + audio retained)

### Authentication
- **Email/password** authentication
- Data is **critical** - never lose it
- Cloud backup mandatory
- **Fully private**: No sharing features, no export (MVP), no external access

---

## Technical Stack

### Mobile App
- **React Native** with **Expo** (managed workflow)
- Performance: Best practices (Hermes enabled), target <500ms cold start
- Heatmap: Virtualized list rendering

### API
- **TypeScript** with **tRPC** (end-to-end type safety)
- Hosted on Render or similar

### LLM Services
- **Transcription**: Whisper API (or best available)
- **Summarization/Categorization**: Mix of providers (OpenAI, Anthropic) based on quality
- Direct API calls, fast processing prioritized over cost

### Push Notifications
- **Server-sent push** for reliability (not local notifications)
- **Serverless scheduled** function triggers pushes
- Grouped by user timezone, hourly cron

---

## UX Details

### Notification Behavior
- Push notification at top of each hour during active hours
- Subtle vibration, no sound
- Current hour: Persistent notification until dismissed/acted on
- Older hours: Badge count only (no stacking)

### Quick-Tap Screen
- 4x3 grid of category icons
- All 12 categories visible at once
- Tap → optional text note → save

### Entry Detail Screen
- Summary (prominent)
- Category + subcategory
- Transcript (collapsed, tap to expand)
- Edit button (if within 24-hour window)
- Timestamp

### Review Mode
- Separate app mode for filling gaps
- Shows list of missing hours
- Fill individually or select range for bulk fill
- Cannot exit until complete
- Morning prompt if previous day incomplete

---

## Constraints & Non-Goals (MVP)

- No search functionality
- No export features
- No gamification (no streaks, badges, achievements)
- No pause/focus mode for notifications
- No analytics or telemetry
- No sharing or social features
- No widgets (future consideration)
- Single schedule for all days (no weekday/weekend split)

---

## Failure Modes to Mitigate

1. **Notification fatigue**: Subtle vibration only, no sound, easy quick-tap
2. **Too much friction**: Quick-tap fallback, auto-save, 30-60 second voice entries
3. **Missing too many days**: After 24 hours, gaps are permanent - part of the habit-building process

---

## Open Items

- [ ] Heatmap color scheme (one color per category)
- [ ] Exact category icons
- [ ] Specific LLM prompts for summarization/categorization
- [ ] Push notification service provider (APNs directly vs OneSignal vs Expo Push)
- [ ] Audio compression/format for storage efficiency
