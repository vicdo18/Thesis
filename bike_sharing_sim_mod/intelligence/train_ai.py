import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb
import matplotlib.pyplot as plt
import seaborn as sns

def train_xgboost_model(data_path='data/synthetic_dataset.csv', model_dir='intelligence', model_name='xgboost_model.pkl'):
    print("--- STEP 1: Loading the Dataset ---")
    
    # 1. Check if the file exists
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at '{data_path}'. Please run generate_dataset.py first.")
        return

    # Load the data
    df = pd.read_csv(data_path)
    print(f"Dataset loaded successfully! Total records: {len(df)}")
    
    # --- STEP 2: Data Preparation ---
    print("\n--- STEP 2: Preparing Data (Train/Test Split) ---")
    
    # Features (X): Everything EXCEPT the 'Accepted' column
    X = df.drop('Accepted', axis=1)
    
    # Target (y): Only the 'Accepted' column
    y = df['Accepted']
    
    # Split the data: 80% for training, 20% for testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)
    
    print(f"Training set size: {len(X_train)} records")
    print(f"Testing set size: {len(X_test)} records")
    
    # --- STEP 3: Model Training ---
    print("\n--- STEP 3: Training the XGBoost Model ---")
    
    # Initialize the XGBoost Classifier
    model = xgb.XGBClassifier(
        n_estimators=100,      # Number of trees
        learning_rate=0.1,     # Step size shrinkage
        max_depth=5,           # Maximum depth of a tree
        random_state=42,       # For reproducibility
        eval_metric='logloss'  # Hides a deprecation warning
    )
    
    # Train the model 
    model.fit(X_train, y_train)
    print("Model training completed!")
    
    # --- STEP 4: Model Evaluation ---
    print("\n--- STEP 4: Evaluating the Model ---")
    
    y_pred = model.predict(X_test)
    
    # Calculate Metrics
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # --- STEP 4.5: Generating AI Visualizations ---
    print("\n--- STEP 4.5: Generating AI Visualizations ---")
    
    # Create a folder to store models and plots
    os.makedirs(model_dir, exist_ok=True)

    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Feature Importance Plot 
    # Using XGBoost's built-in plotter
    xgb.plot_importance(model, ax=axes[0], importance_type='weight', 
                        title='Feature Importance\n(What drives the AI decision?)', 
                        color='#005088', grid=False)
    axes[0].set_ylabel('Features')
    
    # 2. Confusion Matrix Plot (Where does the AI make mistakes?)
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1], cbar=False, annot_kws={"size": 16})
    axes[1].set_title('AI Confusion Matrix', fontsize=14)
    axes[1].set_xlabel('Predicted Action by AI', fontsize=12)
    axes[1].set_ylabel('True Human Action', fontsize=12)
    axes[1].set_xticklabels(['Rejected (0)', 'Accepted (1)'])
    axes[1].set_yticklabels(['Rejected (0)', 'Accepted (1)'], rotation=90)
    
    plt.tight_layout()
    
    plot_path = os.path.join(model_dir, 'ai_diagnostics.png')
    plt.savefig(plot_path, dpi=300)
    print(f"Saved AI Diagnostics plot to: {plot_path}")
    
    print("\n--- STEP 5: Saving the Model ---")
    
    # save model
    model_path = os.path.join(model_dir, model_name)
    joblib.dump({'model': model, 'features': list(X.columns)}, model_path)
    
    print(f"Brain saved successfully at: {model_path}")
    
    # Print the order of features (Important for the RiderBrain)
    feature_names = list(X.columns)
    print(f"\n[IMPORTANT] Model trained with features in this exact order: {feature_names}")
    print("You can now load this model in your simulator to make real-time decisions!")
    
    plt.show()

if __name__ == "__main__":
    train_xgboost_model()