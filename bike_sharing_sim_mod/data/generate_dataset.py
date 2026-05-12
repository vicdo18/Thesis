import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_dataset(records=10000):
    np.random.seed(42)
    
    # 1. Feature Generation
    # Distance in meters (0 to 600m)
    distance = np.random.uniform(50, 600, records)
    
    # Incentive in Euros 
    incentive = np.random.uniform(0.5, 5.0, records)
    
    # Weather (0: Clear, 1: Rain/Bad) - 20% chance of rain
    weather = np.random.choice([0, 1], size=records, p=[0.8, 0.2])
    
    # Urgency (0: Low, 1: High) - 30% are in a hurry
    urgency = np.random.choice([0, 1], size=records, p=[0.7, 0.3])
    
    # 2. Bounded Rationality Logic - Utility Function
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

def visualize_behavior(df):
    print("\n--- Generating Visualizations ---")
    sns.set_theme(style="whitegrid")
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    sns.barplot(ax=axes[0], x='Weather_Bad', y='Accepted', data=df, hue='Weather_Bad', palette="Blues_d", legend=False)
    axes[0].set_title('Impact of Rain on Acceptance Rate', fontsize=14)
    axes[0].set_xticks([0, 1]) 
    axes[0].set_xticklabels(['Clear (0)', 'Raining (1)']) 
    axes[0].set_ylabel('Probability of Acceptance')

    sns.barplot(ax=axes[1], x='Urgency_High', y='Accepted', data=df, hue='Urgency_High', palette="Reds_d", legend=False)
    axes[1].set_title('Impact of Urgency on Acceptance Rate', fontsize=14)
    axes[1].set_xticks([0, 1])
    axes[1].set_xticklabels(['Relaxed (0)', 'In a Hurry (1)'])
    axes[1].set_ylabel('')

 
    df['Distance_Bins'] = pd.cut(df['Distance_m'], bins=np.arange(0, 650, 50))
    df['Distance_Midpoint'] = df['Distance_Bins'].apply(lambda x: x.mid).astype(float)
    
    sns.lineplot(ax=axes[2], x='Distance_Midpoint', y='Accepted', data=df, marker="o", color="green")
    axes[2].set_title('Decay of Acceptance over Distance', fontsize=14)
    axes[2].set_xlabel('Distance (meters)')
    axes[2].set_ylabel('')

    plt.tight_layout()
    
    plt.savefig('data/behavioral_analysis.png', dpi=300)
    print("Saved visualization to: data/behavioral_analysis.png")
    
    plt.show()

def visualize_scatter(df):
    print("\n--- Generating Advanced Contour Plot ---")
    sns.set_theme(style="whitegrid")
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    sns.scatterplot(
        x='Distance_m', y='Incentive_Euro', hue='Accepted', 
        data=df, palette={0: '#ff9999', 1: '#99cc99'}, 
        alpha=0.3, s=15, ax=ax, edgecolor=None, legend=False
    )
    
    sns.kdeplot(
        data=df[df['Accepted'] == 1], x='Distance_m', y='Incentive_Euro',
        levels=6, color="darkgreen", linewidths=2, ax=ax, alpha=0.8
    )
    # Red contours for Rejected
    sns.kdeplot(
        data=df[df['Accepted'] == 0], x='Distance_m', y='Incentive_Euro',
        levels=6, color="darkred", linewidths=2, ax=ax, alpha=0.8
    )
    
    plt.title('Decision Topography: Distance vs. Incentive', fontsize=16, fontweight='bold', pad=15)
    plt.xlabel('Distance (meters)', fontsize=12)
    plt.ylabel('Incentive (Euros)', fontsize=12)
    
    from matplotlib.lines import Line2D
    custom_lines = [Line2D([0], [0], color='darkred', lw=4),
                    Line2D([0], [0], color='darkgreen', lw=4)]
    ax.legend(custom_lines, ['Concentration of Rejections (0)', 'Concentration of Acceptances (1)'], 
              title='Density Contours', loc='upper right')
    
    plt.tight_layout()
    
    os.makedirs('data', exist_ok=True)
    plt.savefig('data/advanced_scatter_analysis.png', dpi=300)
    print("Saved advanced plot to: data/advanced_scatter_analysis.png")

    plt.show()

if __name__ == "__main__":
    df = generate_dataset() 
    visualize_behavior(df)
    visualize_scatter(df)