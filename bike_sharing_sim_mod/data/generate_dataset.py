import pandas as pd
import numpy as np
import os

def generate_improved_dataset(records=10000):
    np.random.seed(42)
    
    # 1. Feature Generation
    # Distance in meters (0 to 600m)
    distance = np.random.uniform(50, 600, records)
    
    # Incentive in Euros (0.5 to 5.0)
    incentive = np.random.uniform(0.5, 5.0, records)
    
    # Weather (0: Clear, 1: Rain/Bad) - 20% chance of rain
    weather = np.random.choice([0, 1], size=records, p=[0.8, 0.2])
    
    # Urgency (0: Low, 1: High) - 30% are in a hurry
    urgency = np.random.choice([0, 1], size=records, p=[0.7, 0.3])
    
    # 2. Bounded Rationality Logic (The "Utility" Function)
    # This is NOT linear. We use a log-base for incentives and penalty for distance.
    
    # Base utility starts from the incentive (logarithmic growth)
    utility = 2 * np.log1p(incentive) 
    
    # Penalties
    utility -= 0.01 * distance  # Linear penalty for distance
    utility -= 1.5 * weather    # Heavy penalty for rain
    utility -= 2.0 * urgency    # Heaviest penalty for being in a hurry
    
    # Threshold Effect: If distance > 400m, add an extra penalty (the "exhaustion" barrier)
    utility[distance > 400] -= 1.5
    
    # 3. Decision Making (Sigmoid function to convert utility to probability)
    # We add some "Noise" (human randomness)
    noise = np.random.normal(0, 0.5, records)
    probability = 1 / (1 + np.exp(-(utility + noise)))
    
    # Final Decision: 1 if prob > 0.5, else 0
    accepted = (probability > 0.5).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        'Distance_m': distance.round(2),
        'Incentive_Euro': incentive.round(2),
        'Weather_Bad': weather,
        'Urgency_High': urgency,
        'Accepted': accepted
    })
    
    # Create directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/synthetic_dataset.csv', index=False)
    
    print(f"--- Dataset V2 Generated ---")
    print(df['Accepted'].value_counts(normalize=True))
    return df

if __name__ == "__main__":
    generate_improved_dataset()