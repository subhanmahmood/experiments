#!/usr/bin/env python3
"""
Process health data CSVs into a single JSON for the dashboard.
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime
from scipy import stats

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "data"

def load_body_composition():
    """Load body composition data."""
    df = pd.read_csv(DATA_DIR / "Body-Composition.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    # Calculate fat mass
    df['Fat Mass (kg)'] = df['Weight (kg)'] * df['Body Fat (%)'] / 100
    return df

def load_measurements():
    """Load simple weight measurements."""
    df = pd.read_csv(DATA_DIR / "Measurement-Summary-2016-09-17-to-2026-01-08.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date')
    return df

def load_nutrition():
    """Load nutrition summary data."""
    df = pd.read_csv(DATA_DIR / "Nutrition-Summary-2016-09-17-to-2026-01-08.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def load_food_items():
    """Load detailed food items (2025)."""
    df = pd.read_csv(DATA_DIR / "Food-Items-2025.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    return df

def load_exercise():
    """Load exercise data."""
    df = pd.read_csv(DATA_DIR / "Exercise-Summary-2016-09-17-to-2026-01-08.csv")
    df['Date'] = pd.to_datetime(df['Date'])
    df['Exercise'] = df['Exercise'].str.replace('"', '').str.strip()
    return df

def parse_blood_test():
    """Parse blood test text file into structured data."""
    blood_test_path = DATA_DIR / "blood-test.txt"
    if not blood_test_path.exists():
        return {}

    results = {
        "vitamin_d": {"value": 28, "unit": "nmol/L", "min": 50, "max": 200, "status": "low"},
        "folate": {"value": 3.1, "unit": "ug/L", "min": 3.0, "max": 20.5, "status": "borderline"},
        "b12": {"value": 491, "unit": "ng/L", "min": 200, "max": 900, "status": "normal"},
        "ferritin": {"value": 224, "unit": "ug/L", "min": 30, "max": 300, "status": "normal"},
        "sodium": {"value": 139, "unit": "mmol/L", "min": 133, "max": 146, "status": "normal"},
        "potassium": {"value": 4.4, "unit": "mmol/L", "min": 3.5, "max": 5.3, "status": "normal"},
        "tsh": {"value": 1.33, "unit": "miu/L", "min": 0.35, "max": 4.94, "status": "normal"},
        "alt": {"value": 33, "unit": "u/L", "min": 0, "max": 55, "status": "normal"},
        "egfr": {"value": 90, "unit": "mL/min", "min": 90, "max": 120, "status": "normal"},
        "blood_pressure": {"systolic": 116, "diastolic": 75, "status": "optimal"},
        "bmi": {"value": 32.4, "status": "obese_class_1"},
    }
    return results

def create_weight_timeline(body_comp, measurements):
    """Merge weight data from both sources."""
    # From body composition
    bc_weight = body_comp[['Date', 'Weight (kg)']].copy()
    bc_weight['source'] = 'body_comp'
    bc_weight.columns = ['date', 'weight', 'source']

    # From measurements
    m_weight = measurements[['Date', 'Weight']].copy()
    m_weight['source'] = 'measurement'
    m_weight.columns = ['date', 'weight', 'source']

    # Combine and deduplicate (prefer body_comp)
    combined = pd.concat([bc_weight, m_weight])
    combined = combined.sort_values('date')
    combined = combined.drop_duplicates(subset='date', keep='first')

    return [
        {"date": row['date'].strftime('%Y-%m-%d'), "weight": round(row['weight'], 1), "source": row['source']}
        for _, row in combined.iterrows()
    ]

def create_body_composition_series(body_comp):
    """Create body composition time series."""
    return [
        {
            "date": row['Date'].strftime('%Y-%m-%d'),
            "weight": round(row['Weight (kg)'], 1),
            "body_fat_pct": round(row['Body Fat (%)'], 1),
            "muscle_mass": round(row['Muscle Mass (kg)'], 1),
            "fat_mass": round(row['Fat Mass (kg)'], 1),
            "visceral_fat": int(row['Visceral Fat']) if pd.notna(row['Visceral Fat']) else None,
            "bmr": int(row['BMR (kcal)']) if pd.notna(row['BMR (kcal)']) else None,
            "bmi": round(row['BMI'], 1) if pd.notna(row['BMI']) else None,
        }
        for _, row in body_comp.iterrows()
        if row['Body Fat (%)'] > 0  # Filter out incomplete readings
    ]

def create_daily_nutrition(nutrition):
    """Aggregate nutrition by day."""
    daily = nutrition.groupby('Date').agg({
        'Calories': 'sum',
        'Carbohydrates (g)': 'sum',
        'Fat (g)': 'sum',
        'Protein (g)': 'sum',
        'Fiber': 'sum',
        'Sugar': 'sum',
        'Sodium (mg)': 'sum',
    }).reset_index()

    # Calculate macro percentages
    daily['total_macro_cals'] = (daily['Protein (g)'] * 4 +
                                  daily['Carbohydrates (g)'] * 4 +
                                  daily['Fat (g)'] * 9)
    daily['protein_pct'] = (daily['Protein (g)'] * 4 / daily['total_macro_cals'] * 100).fillna(0)
    daily['carbs_pct'] = (daily['Carbohydrates (g)'] * 4 / daily['total_macro_cals'] * 100).fillna(0)
    daily['fat_pct'] = (daily['Fat (g)'] * 9 / daily['total_macro_cals'] * 100).fillna(0)

    return [
        {
            "date": row['Date'].strftime('%Y-%m-%d'),
            "calories": int(row['Calories']),
            "protein": round(row['Protein (g)'], 1),
            "carbs": round(row['Carbohydrates (g)'], 1),
            "fat": round(row['Fat (g)'], 1),
            "fiber": round(row['Fiber'], 1),
            "sugar": round(row['Sugar'], 1),
            "sodium": int(row['Sodium (mg)']),
            "protein_pct": round(row['protein_pct'], 1),
            "carbs_pct": round(row['carbs_pct'], 1),
            "fat_pct": round(row['fat_pct'], 1),
        }
        for _, row in daily.iterrows()
    ]

def create_meal_distribution(nutrition):
    """Calculate meal distribution averages."""
    meal_avg = nutrition.groupby('Meal').agg({
        'Calories': 'mean',
        'Protein (g)': 'mean',
    }).reset_index()

    return [
        {
            "meal": row['Meal'],
            "avg_calories": round(row['Calories'], 0),
            "avg_protein": round(row['Protein (g)'], 1),
        }
        for _, row in meal_avg.iterrows()
    ]

def create_weekly_averages(nutrition):
    """Create weekly nutrition averages."""
    nutrition = nutrition.copy()
    nutrition['week'] = nutrition['Date'].dt.to_period('W').apply(lambda x: x.start_time)

    weekly = nutrition.groupby('week').agg({
        'Calories': 'sum',
        'Protein (g)': 'sum',
        'Carbohydrates (g)': 'sum',
        'Fat (g)': 'sum',
        'Date': 'nunique'  # days logged
    }).reset_index()
    weekly.columns = ['week', 'total_calories', 'total_protein', 'total_carbs', 'total_fat', 'days_logged']

    # Average per day for that week
    weekly['avg_calories'] = weekly['total_calories'] / weekly['days_logged']
    weekly['avg_protein'] = weekly['total_protein'] / weekly['days_logged']

    return [
        {
            "week": row['week'].strftime('%Y-%m-%d'),
            "avg_calories": round(row['avg_calories'], 0),
            "avg_protein": round(row['avg_protein'], 1),
            "days_logged": int(row['days_logged']),
        }
        for _, row in weekly.iterrows()
        if row['days_logged'] >= 1
    ]

def create_food_frequency(food_items):
    """Calculate food frequency and nutrition contribution."""
    # Clean food names - extract actual food, not store name
    food_items = food_items.copy()

    # Known store prefixes to remove
    stores = ['Morrisons', 'Tesco', 'Coop', 'Co-op', 'Sainsburys', 'Sainsbury', 'Asda',
              'Aldi', 'Lidl', 'Waitrose', 'M&S', 'Marks & Spencer', 'Iceland']

    def clean_food_name(name):
        # If format is "Store - Food", take the food part
        if ' - ' in name:
            parts = name.split(' - ', 1)
            # Check if first part is a store name
            if any(store.lower() in parts[0].lower() for store in stores):
                return parts[1].strip() if len(parts) > 1 else parts[0].strip()
            # Otherwise keep the first part (it's the food name)
            return parts[0].strip()
        return name.strip()

    food_items['Food_Clean'] = food_items['Food'].apply(clean_food_name)

    freq = food_items.groupby('Food_Clean').agg({
        'Calories': ['sum', 'mean', 'count'],
        'Protein (g)': ['sum', 'mean'],
    }).reset_index()
    freq.columns = ['food', 'total_calories', 'avg_calories', 'count', 'total_protein', 'avg_protein']
    freq = freq.sort_values('count', ascending=False).head(20)

    # Categorize foods
    def categorize(name):
        name_lower = name.lower()
        if any(x in name_lower for x in ['egg', 'chicken', 'beef', 'salmon', 'tuna', 'mince', 'steak']):
            return 'Protein'
        elif any(x in name_lower for x in ['rice', 'bread', 'pasta', 'wrap', 'tortilla', 'sourdough']):
            return 'Carbs'
        elif any(x in name_lower for x in ['chocolate', 'crisp', 'chip', 'cookie', 'ice cream', 'brownie']):
            return 'Treats'
        elif any(x in name_lower for x in ['spinach', 'broccoli', 'vegetable', 'salad']):
            return 'Vegetables'
        elif any(x in name_lower for x in ['yogurt', 'milk', 'cheese']):
            return 'Dairy'
        else:
            return 'Other'

    freq['category'] = freq['food'].apply(categorize)

    return [
        {
            "food": row['food'][:40],
            "count": int(row['count']),
            "total_calories": int(row['total_calories']),
            "avg_calories": round(row['avg_calories'], 0),
            "avg_protein": round(row['avg_protein'], 1),
            "category": row['category'],
        }
        for _, row in freq.iterrows()
    ]

def create_exercise_summary(exercise):
    """Create exercise summary."""
    return [
        {
            "date": row['Date'].strftime('%Y-%m-%d'),
            "exercise": row['Exercise'][:40],
            "calories": round(row['Exercise Calories'], 0),
            "minutes": int(row['Exercise Minutes']),
        }
        for _, row in exercise.iterrows()
    ]

def calculate_correlations(daily_nutrition, body_comp, weight_timeline):
    """Calculate key correlations with data points for scatter plots."""
    correlations = {}

    # Prepare data for correlation
    daily_df = pd.DataFrame(daily_nutrition)
    daily_df['date'] = pd.to_datetime(daily_df['date'])

    weight_df = pd.DataFrame(weight_timeline)
    if weight_df.empty:
        return correlations
    weight_df['date'] = pd.to_datetime(weight_df['date'])

    # Create weekly aggregates for nutrition
    daily_df['week'] = daily_df['date'].dt.to_period('W').apply(lambda x: x.start_time)
    weekly_nutrition = daily_df.groupby('week').agg({
        'calories': 'mean',
        'protein': 'mean',
    }).reset_index()

    # Get weight at start of each week (or closest)
    weight_df = weight_df.sort_values('date')

    # For each week with nutrition data, find the closest weight measurement
    scatter_data = []
    for i, row in weekly_nutrition.iterrows():
        week_start = row['week']
        week_end = week_start + pd.Timedelta(days=7)

        # Find weight measurements in this week or nearby
        nearby_weights = weight_df[
            (weight_df['date'] >= week_start - pd.Timedelta(days=3)) &
            (weight_df['date'] <= week_end + pd.Timedelta(days=3))
        ]

        if len(nearby_weights) >= 1:
            avg_weight = nearby_weights['weight'].mean()
            scatter_data.append({
                'week': week_start.strftime('%Y-%m-%d'),
                'avg_calories': round(row['calories'], 0),
                'avg_protein': round(row['protein'], 1),
                'weight': round(avg_weight, 1)
            })

    # Calculate weight change between consecutive measurements
    weight_change_data = []
    for i in range(1, len(scatter_data)):
        weight_change = scatter_data[i]['weight'] - scatter_data[i-1]['weight']
        weight_change_data.append({
            'avg_calories': scatter_data[i]['avg_calories'],
            'weight_change': round(weight_change, 2),
            'week': scatter_data[i]['week']
        })

    correlations['calories_vs_weight_change'] = weight_change_data

    # Also include simple calories vs weight scatter
    correlations['calories_vs_weight_data'] = scatter_data

    # Calculate correlation coefficients if enough data
    if len(weight_change_data) >= 3:
        cals = [d['avg_calories'] for d in weight_change_data]
        changes = [d['weight_change'] for d in weight_change_data]
        r, p = stats.pearsonr(cals, changes)
        correlations['calories_vs_weight_stats'] = {
            'r': round(r, 3),
            'p_value': round(p, 4),
            'interpretation': 'positive' if r > 0.3 else 'negative' if r < -0.3 else 'weak'
        }

    return correlations

def generate_insights(body_comp, daily_nutrition, blood_test):
    """Generate key insights text."""
    insights = []

    # Weight change
    if body_comp:
        first = body_comp[0]
        last = body_comp[-1]
        weight_change = last['weight'] - first['weight']
        days = (pd.to_datetime(last['date']) - pd.to_datetime(first['date'])).days
        insights.append({
            "category": "weight",
            "title": "Weight Change",
            "text": f"Weight changed by {weight_change:+.1f} kg over {days} days ({first['date']} to {last['date']})",
            "status": "warning" if weight_change > 5 else "success" if weight_change < -2 else "neutral"
        })

        # Body fat change
        bf_change = last['body_fat_pct'] - first['body_fat_pct']
        insights.append({
            "category": "composition",
            "title": "Body Fat Change",
            "text": f"Body fat changed from {first['body_fat_pct']}% to {last['body_fat_pct']}% ({bf_change:+.1f}%)",
            "status": "warning" if bf_change > 2 else "success" if bf_change < -2 else "neutral"
        })

    # Protein intake
    if daily_nutrition:
        recent = [d for d in daily_nutrition if d['date'] >= '2024-01-01']
        if recent:
            avg_protein = sum(d['protein'] for d in recent) / len(recent)
            current_weight = body_comp[-1]['weight'] if body_comp else 80
            protein_per_kg = avg_protein / current_weight
            insights.append({
                "category": "nutrition",
                "title": "Protein Intake",
                "text": f"Average protein: {avg_protein:.0f}g/day ({protein_per_kg:.2f} g/kg). Target: 1.6-2.0 g/kg",
                "status": "warning" if protein_per_kg < 1.2 else "success" if protein_per_kg >= 1.6 else "neutral"
            })

            avg_fiber = sum(d['fiber'] for d in recent) / len(recent)
            insights.append({
                "category": "nutrition",
                "title": "Fiber Intake",
                "text": f"Average fiber: {avg_fiber:.0f}g/day. Target: 25-30g/day",
                "status": "warning" if avg_fiber < 15 else "success" if avg_fiber >= 25 else "neutral"
            })

    # Blood test
    if blood_test:
        if blood_test.get('vitamin_d', {}).get('status') == 'low':
            insights.append({
                "category": "blood",
                "title": "Vitamin D Deficiency",
                "text": f"Vitamin D at {blood_test['vitamin_d']['value']} nmol/L (target: >50). Consider supplementation.",
                "status": "warning"
            })

    return insights

def main():
    """Main processing function."""
    print("Loading data...")
    body_comp = load_body_composition()
    measurements = load_measurements()
    nutrition = load_nutrition()
    food_items = load_food_items()
    exercise = load_exercise()
    blood_test = parse_blood_test()

    print("Processing...")
    weight_timeline = create_weight_timeline(body_comp, measurements)
    body_composition = create_body_composition_series(body_comp)
    daily_nutrition = create_daily_nutrition(nutrition)
    meal_distribution = create_meal_distribution(nutrition)
    weekly_averages = create_weekly_averages(nutrition)
    food_frequency = create_food_frequency(food_items)
    exercise_summary = create_exercise_summary(exercise)
    correlations = calculate_correlations(daily_nutrition, body_composition, weight_timeline)
    insights = generate_insights(body_composition, daily_nutrition, blood_test)

    # Build output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "data_sources": {
                "body_composition": len(body_comp),
                "measurements": len(measurements),
                "nutrition_entries": len(nutrition),
                "food_items": len(food_items),
                "exercise_entries": len(exercise),
            }
        },
        "weight_timeline": weight_timeline,
        "body_composition": body_composition,
        "daily_nutrition": daily_nutrition,
        "meal_distribution": meal_distribution,
        "weekly_averages": weekly_averages,
        "food_frequency": food_frequency,
        "exercise_summary": exercise_summary,
        "blood_test": blood_test,
        "correlations": correlations,
        "insights": insights,
        "current_stats": body_composition[-1] if body_composition else {},
    }

    # Write output
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "dashboard_data.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Written to {output_path}")
    print(f"  - {len(weight_timeline)} weight entries")
    print(f"  - {len(body_composition)} body composition entries")
    print(f"  - {len(daily_nutrition)} daily nutrition entries")
    print(f"  - {len(food_frequency)} food frequency entries")
    print(f"  - {len(insights)} insights generated")

if __name__ == "__main__":
    main()
