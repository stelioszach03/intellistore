"""
Training script for IntelliStore hot/cold tiering model
"""

import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
import onnx
import skl2onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType


def generate_synthetic_data(n_samples: int = 10000) -> pd.DataFrame:
    """Generate synthetic training data for hot/cold tiering"""
    np.random.seed(42)
    
    data = []
    
    for i in range(n_samples):
        # Time-based features
        timestamp = datetime.now() - timedelta(days=np.random.randint(0, 365))
        hour_of_day = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = int(day_of_week >= 5)
        is_business_hours = int(9 <= hour_of_day <= 17)
        
        # Object characteristics
        size = np.random.lognormal(mean=10, sigma=2)  # Log-normal distribution for file sizes
        size_mb = size / (1024 * 1024)
        
        if size_mb < 1:
            size_category = 'small'
        elif size_mb < 100:
            size_category = 'medium'
        elif size_mb < 1000:
            size_category = 'large'
        else:
            size_category = 'xlarge'
        
        # Content type (affects access patterns)
        content_types = ['image/', 'video/', 'audio/', 'text/', 'application/']
        content_type = np.random.choice(content_types, p=[0.3, 0.2, 0.1, 0.2, 0.2])
        is_media = int(content_type in ['image/', 'video/', 'audio/'])
        
        # Current tier
        current_tier = np.random.choice(['hot', 'cold'], p=[0.3, 0.7])
        
        # Access patterns (these would normally come from historical data)
        base_activity = np.random.exponential(scale=5)
        
        # Business hours and weekdays have higher activity
        if is_business_hours:
            base_activity *= 1.5
        if not is_weekend:
            base_activity *= 1.3
        
        # Media files tend to have different access patterns
        if is_media:
            base_activity *= 0.8
        
        # Larger files tend to be accessed less frequently
        if size_category in ['large', 'xlarge']:
            base_activity *= 0.6
        
        user_activity_level = max(1, int(base_activity))
        bucket_popularity = np.random.poisson(lam=5) + 1
        
        # Recent access patterns
        access_count_7d = np.random.poisson(lam=base_activity * 0.7)
        download_count_7d = max(0, access_count_7d - np.random.poisson(lam=2))
        unique_users_7d = min(access_count_7d, np.random.poisson(lam=base_activity * 0.3) + 1)
        
        # Derived features
        avg_daily_access = access_count_7d / 7.0
        last_access_hours_ago = np.random.exponential(scale=48) if access_count_7d > 0 else 168
        
        # Trend calculation (simplified)
        recent_access_trend = np.random.normal(loc=1.0, scale=0.3)
        
        # Object age
        object_age_days = np.random.exponential(scale=30)
        
        # Target variable (hot/cold prediction)
        # Hot tier probability based on access patterns
        hot_probability = 0.1  # Base probability
        
        # Recent access increases hot probability
        if access_count_7d > 5:
            hot_probability += 0.4
        elif access_count_7d > 2:
            hot_probability += 0.2
        elif access_count_7d > 0:
            hot_probability += 0.1
        
        # Business hours access increases probability
        if is_business_hours and access_count_7d > 0:
            hot_probability += 0.2
        
        # Recent access time
        if last_access_hours_ago < 24:
            hot_probability += 0.3
        elif last_access_hours_ago < 72:
            hot_probability += 0.1
        
        # User activity level
        if user_activity_level > 10:
            hot_probability += 0.2
        
        # Size considerations (smaller files more likely to be hot)
        if size_category == 'small':
            hot_probability += 0.1
        elif size_category in ['large', 'xlarge']:
            hot_probability -= 0.1
        
        # Current tier bias (objects already in hot tier more likely to stay)
        if current_tier == 'hot':
            hot_probability += 0.2
        
        # Ensure probability is in valid range
        hot_probability = max(0.05, min(0.95, hot_probability))
        
        # Generate target
        target = int(np.random.random() < hot_probability)
        
        data.append({
            'hour_of_day': hour_of_day,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend,
            'is_business_hours': is_business_hours,
            'object_age_days': object_age_days,
            'size': size,
            'size_category': size_category,
            'is_media': is_media,
            'current_tier': current_tier,
            'user_activity_level': user_activity_level,
            'bucket_popularity': bucket_popularity,
            'access_count_7d': access_count_7d,
            'download_count_7d': download_count_7d,
            'unique_users_7d': unique_users_7d,
            'avg_daily_access': avg_daily_access,
            'last_access_hours_ago': last_access_hours_ago,
            'recent_access_trend': recent_access_trend,
            'target': target
        })
    
    return pd.DataFrame(data)


def preprocess_data(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict]:
    """Preprocess the data for training"""
    
    # Separate features and target
    X = df.drop('target', axis=1)
    y = df['target']
    
    # Handle categorical variables
    label_encoders = {}
    categorical_columns = ['size_category', 'current_tier']
    
    for col in categorical_columns:
        if col in X.columns:
            le = LabelEncoder()
            X[f'{col}_encoded'] = le.fit_transform(X[col])
            label_encoders[col] = le
            X = X.drop(col, axis=1)
    
    # Feature columns for later use
    feature_columns = X.columns.tolist()
    
    # Scale numerical features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    preprocessing_objects = {
        'scaler': scaler,
        'label_encoders': label_encoders,
        'feature_columns': feature_columns
    }
    
    return X_scaled, y.values, preprocessing_objects


def train_model(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    """Train the Random Forest model"""
    
    # Random Forest is good for this type of problem
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    # Train the model
    model.fit(X, y)
    
    return model


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
    """Evaluate the trained model"""
    
    # Predictions
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Metrics
    auc_score = roc_auc_score(y_test, y_pred_proba)
    
    # Classification report
    class_report = classification_report(y_test, y_pred, output_dict=True)
    
    # Confusion matrix
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    return {
        'auc_score': auc_score,
        'classification_report': class_report,
        'confusion_matrix': conf_matrix.tolist(),
        'accuracy': class_report['accuracy'],
        'precision': class_report['1']['precision'],
        'recall': class_report['1']['recall'],
        'f1_score': class_report['1']['f1-score']
    }


def save_model_artifacts(model, preprocessing_objects: Dict, evaluation_results: Dict, 
                        feature_columns: List[str], output_dir: str = "models"):
    """Save all model artifacts"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the scikit-learn model
    joblib.dump(model, os.path.join(output_dir, "tiering_model.joblib"))
    
    # Save preprocessing objects
    joblib.dump(preprocessing_objects, os.path.join(output_dir, "preprocessing.joblib"))
    
    # Convert to ONNX for production inference
    try:
        # Define input type
        initial_type = [('float_input', FloatTensorType([None, len(feature_columns)]))]
        
        # Convert model
        onnx_model = convert_sklearn(model, initial_types=initial_type)
        
        # Save ONNX model
        with open(os.path.join(output_dir, "tiering_model.onnx"), "wb") as f:
            f.write(onnx_model.SerializeToString())
        
        print("ONNX model saved successfully")
        
    except Exception as e:
        print(f"Failed to convert to ONNX: {e}")
    
    # Save model metadata
    metadata = {
        'model_version': f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'training_date': datetime.now().isoformat(),
        'model_type': 'RandomForestClassifier',
        'feature_columns': feature_columns,
        'evaluation_results': evaluation_results,
        'model_parameters': model.get_params()
    }
    
    with open(os.path.join(output_dir, "model_metadata.json"), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Model artifacts saved to {output_dir}/")
    print(f"Model version: {metadata['model_version']}")
    print(f"AUC Score: {evaluation_results['auc_score']:.4f}")
    print(f"Accuracy: {evaluation_results['accuracy']:.4f}")


def main():
    """Main training pipeline"""
    print("Starting IntelliStore ML model training...")
    
    # Generate synthetic data
    print("Generating synthetic training data...")
    df = generate_synthetic_data(n_samples=10000)
    print(f"Generated {len(df)} samples")
    
    # Preprocess data
    print("Preprocessing data...")
    X, y, preprocessing_objects = preprocess_data(df)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {len(X_train)} samples")
    print(f"Test set: {len(X_test)} samples")
    print(f"Hot tier ratio: {y.mean():.2%}")
    
    # Train model
    print("Training model...")
    model = train_model(X_train, y_train)
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='roc_auc')
    print(f"Cross-validation AUC: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    # Evaluate model
    print("Evaluating model...")
    evaluation_results = evaluate_model(model, X_test, y_test)
    
    # Feature importance
    feature_importance = dict(zip(preprocessing_objects['feature_columns'], model.feature_importances_))
    top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print("\nTop 10 most important features:")
    for feature, importance in top_features:
        print(f"  {feature}: {importance:.4f}")
    
    # Save model artifacts
    print("\nSaving model artifacts...")
    save_model_artifacts(
        model, 
        preprocessing_objects, 
        evaluation_results,
        preprocessing_objects['feature_columns']
    )
    
    print("Training completed successfully!")


if __name__ == "__main__":
    main()