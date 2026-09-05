from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split

from backend.app.simulator import generate_transactions
from backend.app.features import extract_root_cause_features, FEATURE_NAMES

MODEL_PATH = ROOT / "backend" / "app" / "artifacts" / "root_cause_model.joblib"
SCENARIOS = ["issuer_degradation", "rail_degradation", "regional_network", "merchant_integration"]


def build_training_data(samples_per_class: int = 45):
    rows, labels = [], []
    for idx, scenario in enumerate(SCENARIOS):
        for n in range(samples_per_class):
            seed = 1000 + idx * 1000 + n
            df = generate_transactions(minutes=90, transactions_per_minute=18, incident_type=scenario, seed=seed)
            rows.append(extract_root_cause_features(df))
            labels.append(scenario)
    return pd.DataFrame(rows)[FEATURE_NAMES], labels


if __name__ == "__main__":
    X, y = build_training_data()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=220, max_depth=8, min_samples_leaf=2,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print(f"Validation accuracy: {accuracy_score(y_test, pred):.3f}")
    print(classification_report(y_test, pred, digits=3))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")
