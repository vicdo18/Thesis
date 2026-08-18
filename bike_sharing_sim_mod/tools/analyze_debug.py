"""
Analyze debug_realistic_decisions.csv to understand:
- Distribution of distances offered to RiderBrain
- How often the simulator offers distance=0 (same station)
- Whether strategies converge because of a bottleneck or by design
"""
import pandas as pd
import os

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, '..', 'outputs', 'debug_realistic_decisions.csv')

# Read CSV, skip duplicate header rows
df = pd.read_csv(CSV_PATH)
# Remove any row where 'strategy' literally equals 'strategy' (leaked headers)
df = df[df['strategy'] != 'strategy'].reset_index(drop=True)

# Type conversion (may have been strings due to mixed headers)
for col in ['hour', 'incentive', 'distance_units', 'distance_m',
            'weather_bad', 'urgency_high', 'probability', 'decision']:
    df[col] = pd.to_numeric(df[col])

print("=" * 60)
print(f"TOTAL DECISIONS LOGGED: {len(df):,}")
print("=" * 60)

print("\n--- Decisions per strategy ---")
print(df.groupby('strategy').size().sort_values(ascending=False))

print("\n--- Distance distribution (grid units) ---")
print(df['distance_units'].describe())

print("\n--- CRITICAL: How many offers are distance = 0? ---")
zero_dist = (df['distance_units'] == 0).sum()
print(f"Zero-distance offers: {zero_dist:,} ({100*zero_dist/len(df):.1f}%)")

print("\n--- Distance buckets ---")
buckets = pd.cut(df['distance_m'],
                 bins=[-0.1, 0.1, 100, 200, 300, 400, 600],
                 labels=['0m', '0-100m', '100-200m', '200-300m', '300-400m', '400-600m'])
print(df.groupby(buckets, observed=True).agg(
    count=('decision', 'size'),
    accept_rate=('decision', 'mean'),
    avg_prob=('probability', 'mean')
).round(3))

print("\n--- Acceptance rate per strategy (from debug data) ---")
print(df.groupby('strategy').agg(
    n_offers=('decision', 'size'),
    accept_rate=('decision', 'mean'),
    avg_incentive=('incentive', 'mean'),
    avg_distance_m=('distance_m', 'mean')
).round(3))

print("\n--- Cross-tab: distance bucket × strategy (accept rate) ---")
pivot = df.groupby([buckets, 'strategy'], observed=True)['decision'].mean().unstack()
print(pivot.round(3))