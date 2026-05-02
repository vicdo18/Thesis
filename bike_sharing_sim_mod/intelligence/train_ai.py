import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb

def train_xgboost_model():
    print("--- STEP 1: Loading the Dataset ---")
    data_path = 'C:\\Users\\vixky\\Desktop\\Bike-sharing-simulator-v3 2\\Bike-sharing-simulator-v3\\simulator_v4\\bike_sharing_sim_mod\\data\\synthetic_dataset.csv'
    
    if not os.path.exists(data_path):
        print(f"Error: Dataset not found at {data_path}. Please run generate_dataset.py first.")
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
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42)
    
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
        use_label_encoder=False,
        eval_metric='logloss'  # Hides a deprecation warning
    )
    
    # Train the model 
    model.fit(X_train, y_train)
    print("Model training completed!")
    
    # --- STEP 4: Model Evaluation ---
    print("\n--- STEP 4: Evaluating the Model ---")
    
    # Ask the model to predict the outcomes for the unseen Test Set
    y_pred = model.predict(X_test)
    
    # Calculate Metrics
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred))
    
    # --- STEP 5: Saving the Brain ---
    print("\n--- STEP 5: Saving the Model ---")
    
    # Create an 'intelligence' folder to store models
    os.makedirs('intelligence', exist_ok=True)
    
    model_path = 'intelligence/xgboost_model.pkl'
    joblib.dump(model, model_path)
    
    print(f"Brain saved successfully at: {model_path}")
    print("You can now load this model in your simulator to make real-time decisions!")

if __name__ == "__main__":
    train_xgboost_model()