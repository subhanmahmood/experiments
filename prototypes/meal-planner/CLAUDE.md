# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal health and nutrition data aggregation project. Contains exported data from MyFitnessPal, INSMART smart scale, and Whoop wearable, processed into standardized CSV formats for analysis.

## Environment Setup

```bash
uv venv && source .venv/bin/activate && uv pip install pandas xlrd openpyxl
```

## Data Files

All data is in `data/`:

| File | Description | Key Columns |
|------|-------------|-------------|
| `Nutrition-Summary-*.csv` | MyFitnessPal meal totals (2016-present) | Date, Meal, Calories, Macros, Micros |
| `Food-Items-2025.csv` | Individual food entries with servings | Date, Meal, Food, Serving, Nutrition |
| `Body-Composition.csv` | INSMART scale readings (2023-2025) | Date, Weight, BMI, Body Fat %, Muscle Mass |
| `Measurement-Summary-*.csv` | MyFitnessPal weight only | Date, Weight |
| `Exercise-Summary-*.csv` | Exercise logs (sparse) | Date, Exercise, Calories, Minutes |
| `blood-test.txt` | Blood test results | Vitamins, organ function, blood counts |
| `whoop/physiological_cycles.csv` | Daily recovery & strain (Sept 2025-present) | Cycle start/end, Recovery %, HRV, Resting HR, Day Strain, Sleep metrics |
| `whoop/sleeps.csv` | Detailed sleep records | Sleep onset/wake, Sleep stages (light/deep/REM), Performance %, Efficiency %, Nap |
| `whoop/workouts.csv` | Workout activities | Activity name, Duration, Strain, Energy burned, HR zones |

## Data Schema Notes

- Dates use `YYYY-MM-DD` format
- Meals: `Breakfast`, `Lunch`, `Dinner`, `Snacks`
- Missing values represented as empty cells (not `--` or `null`)
- Weight in kg, calories in kcal
- Join datasets on `Date` (and optionally `Meal`)

### Whoop Data
- Timestamps use `YYYY-MM-DD HH:MM:SS` format (extract date with `.str[:10]` or `pd.to_datetime().dt.date`)
- Cycles represent ~24hr periods from sleep to sleep
- Recovery score: 0-100% (higher = better recovered)
- HRV in milliseconds, Resting HR in bpm
- Day Strain: 0-21 scale (higher = more exertion)
- Sleep durations in minutes
- `Nap` column in sleeps.csv: `true`/`false` to distinguish naps from main sleep

## Processing Binary Files

To convert XLS/Excel files:
```python
import pandas as pd
df = pd.read_excel('data/file.xls')
df.to_csv('data/output.csv', index=False)
```
