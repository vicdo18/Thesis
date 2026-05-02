import pandas as pd
import numpy as np
import random
import os

def generate_synthetic_dataset(num_agents=10000):
    print(f"Starting Monte Carlo Simulation for {num_agents} Agents...")
    
    # 1. SETUP: Create 'data' folder to keep things organized
    os.makedirs('data', exist_ok=True)
    
    # Use a List instead of a DataFrame for maximum speed
    data = []
    
    for _ in range(num_agents):
        # ---------------------------------------------------------
        # 2. AGENT & ENVIRONMENT GENERATION
        # ---------------------------------------------------------
        
        # User Category (Based on options.json): 
        # 1 = Loyal (30%), 2 = Flexible (50%), 3 = Opportunistic (20%)
        user_category = np.random.choice([1, 2, 3], p=[0.3, 0.5, 0.2])
        
        # Objective Conditions
        distance = round(random.uniform(0.1, 3.0), 2)  # Distance: 0.1 to 3.0 blocks
        incentive = round(random.uniform(0.1, 2.0), 2) # Offer: 0.10€ to 2.00€
        
        # Subjective Conditions (Bounded Rationality)
        weather = random.choice([0, 1])  # 0 = Clear, 1 = Rain
        urgency = round(random.uniform(0.0, 1.0), 2)  # 0 = Relaxed (Leisure), 1 = In a hurry
        
        # ---------------------------------------------------------
        # 3. THE BRAIN (THE DECISION FUNNEL)
        # ---------------------------------------------------------
        
        # A. Define Base Probability based on Agent's psychology
        if user_category == 1:
            base_prob = random.uniform(0.0, 0.2)
        elif user_category == 2:
            base_prob = random.uniform(0.4, 0.7)
        else:
            base_prob = random.uniform(0.8, 1.0)
            
        # B. Distance Penalty: Degradation of incentive value due to distance
        distance_penalty = distance / 3.0
        effective_incentive = incentive * (1 - distance_penalty * 0.7)
        
        # Calculate Initial Acceptance Probability
        prob = base_prob * effective_incentive * 1.5
        
        # C. Bounded Rationality Penalties (The thesis innovations)
        # Rain cuts probability by 40% (Based on Kim, 2018)
        weather_penalty = 0.4 if weather == 1 else 0.0
        # Urgency cuts probability by up to 35% (Based on Fukushige et al., 2022)
        urgency_penalty = urgency * 0.35 
        
        prob = prob - weather_penalty - urgency_penalty
        
        # D. Stochastic Noise to avoid AI Overfitting
        noise = random.uniform(-0.1, 0.1)
        prob = prob + noise
        
        # Lock probability strictly between 0.0 and 1.0
        final_prob = max(0.0, min(1.0, prob))
        
        # E. The Final Decision: Roll the virtual dice
        accepted = 1 if random.random() < final_prob else 0
        
        # ---------------------------------------------------------
        # Record the experience in the list (fast O(1) operation)
        # ---------------------------------------------------------
        data.append({
            'User_Type': user_category,
            'Distance_Blocks': distance,
            'Incentive_Euros': incentive,
            'Weather_Rain': weather,
            'Urgency_Level': urgency,
            'Accepted': accepted
        })

    # ---------------------------------------------------------
    # 4. EXPORT AND SANITY CHECKS
    # ---------------------------------------------------------
    
    # Convert the list to a DataFrame
    df = pd.DataFrame(data)
    
    # Save the dataset
    output_path = "bike_sharing_sim_mod/data/synthetic_dataset.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Simulation completed successfully!")
    print(f"File saved to: {output_path}")
    
    #validate if file was saved 
    if os.path.exists(output_path):
        print("File validation successful: The dataset was saved correctly.")
    else:
        print("File validation failed: The dataset was not found.")
    
    # Data Validation: Sanity Check
    acceptance_rate = df['Accepted'].mean() * 100
    print(f"\n--- Data Validation (Sanity Check) ---")
    print(f"Total Incentive Acceptance Rate: {acceptance_rate:.2f}%")
    
    if 15.0 <= acceptance_rate <= 40.0:
        print("The acceptance rate is highly realistic!")
    else:
        print("Warning: The acceptance rate is outside realistic bounds. We might need to adjust the weights.")
    
    print("\nPreview of the first 5 records:")
    print(df.head())

# Execute the script
if __name__ == "__main__":
    generate_synthetic_dataset()