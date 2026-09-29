"""
Predictive risk model for NWIS.

For the prototype we synthesize a training set of drilling-parameter
snapshots with a rule-based ground-truth risk generator (plus noise) that
encodes realistic domain patterns (e.g. Barail Group + low mud weight +
high torque => elevated stuck-pipe/mud-loss risk). This lets us train and
demo a genuine ML classifier rather than a hardcoded if-else, while being
transparent that a production version would train on real DDR/WCR-derived
time series instead.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib
import os

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.joblib")
ENCODER_PATH = os.path.join(MODEL_DIR, "formation_encoder.joblib")

FORMATIONS = ["Alluvium", "Girujan Clay", "Tipam Sandstone", "Barail Group", "Basement (Pre-Tertiary)"]

# Base geological risk factor per formation (domain-informed for the demo)
FORMATION_RISK = {
    "Alluvium": 0.05,
    "Girujan Clay": 0.15,
    "Tipam Sandstone": 0.25,
    "Barail Group": 0.55,
    "Basement (Pre-Tertiary)": 0.40,
}


def synthesize_training_data(n=4000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        formation = rng.choice(FORMATIONS)
        depth = rng.uniform(100, 3100)
        rop = rng.uniform(4, 35)                    # rate of penetration m/hr
        mud_weight = rng.uniform(1.05, 1.85)         # SG
        torque = rng.uniform(8, 32)                  # kNm
        downhole_pressure = rng.uniform(0.9, 1.6)    # pore pressure gradient proxy (sg equiv)

        base_risk = FORMATION_RISK[formation]
        underbalance = max(0, downhole_pressure - mud_weight)      # underbalanced -> kick/loss risk
        torque_excess = max(0, torque - 22) / 10.0                  # high torque -> stuck pipe / pack-off
        depth_factor = min(depth / 3200, 1.0) * 0.2

        risk_score = base_risk + underbalance * 0.9 + torque_excess * 0.5 + depth_factor
        risk_score += rng.normal(0, 0.08)  # noise
        risk_score = np.clip(risk_score, 0, 1)
        label = 1 if risk_score > 0.55 else 0

        rows.append({
            "formation": formation,
            "depth_m": depth,
            "rop_m_hr": rop,
            "mud_weight_sg": mud_weight,
            "torque_knm": torque,
            "downhole_pressure_sg": downhole_pressure,
            "high_risk": label,
        })
    return pd.DataFrame(rows)


def train():
    df = synthesize_training_data()
    encoder = LabelEncoder()
    df["formation_enc"] = encoder.fit_transform(df["formation"])

    feature_cols = ["formation_enc", "depth_m", "rop_m_hr", "mud_weight_sg", "torque_knm", "downhole_pressure_sg"]
    X = df[feature_cols]
    y = df["high_risk"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    clf = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    auc = roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
    print(f"Trained risk model. Test AUC: {auc:.3f}")
    print("Feature importances:", dict(zip(feature_cols, clf.feature_importances_.round(3))))

    joblib.dump(clf, MODEL_PATH)
    joblib.dump(encoder, ENCODER_PATH)
    return auc


def load_model():
    if not (os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH)):
        train()
    clf = joblib.load(MODEL_PATH)
    encoder = joblib.load(ENCODER_PATH)
    return clf, encoder


def predict_risk(formation: str, depth_m: float, rop_m_hr: float, mud_weight_sg: float,
                  torque_knm: float, downhole_pressure_sg: float):
    clf, encoder = load_model()
    if formation not in encoder.classes_:
        formation = min(FORMATIONS, key=lambda f: 0)  # fallback to first known formation
    formation_enc = encoder.transform([formation])[0]
    X = pd.DataFrame([{
        "formation_enc": formation_enc,
        "depth_m": depth_m,
        "rop_m_hr": rop_m_hr,
        "mud_weight_sg": mud_weight_sg,
        "torque_knm": torque_knm,
        "downhole_pressure_sg": downhole_pressure_sg,
    }])
    proba = clf.predict_proba(X)[0, 1]
    return float(proba)


if __name__ == "__main__":
    train()
    # quick sanity check
    print(predict_risk("Barail Group", 2100, 12, 1.15, 27, 1.45))   # expect high risk
    print(predict_risk("Alluvium", 300, 20, 1.2, 12, 1.1))          # expect low risk
