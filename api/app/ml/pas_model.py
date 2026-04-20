"""
PAS Proxy Labeller — Kozlov et al. (RAID 2020) three-class framework.

Training data priority:
  1. Real instafake OSN dataset (Instagram genuine/fake accounts, ~1400 records)
     downloaded from github.com/fcakyon/instafake-dataset
  2. Synthetic fallback if download fails (documented distributions)

Model tiers:
  v1  — DecisionTree(depth=10)           fast, interpretable
  v2  — DecisionTree(depth=15)           higher capacity
  production — BaggingClassifier(50 trees) + CalibratedClassifierCV(isotonic)
"""
import logging
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import BaggingClassifier
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from app.ml.real_data import load_real_pas_data, get_feature_columns
from app.ml.synthetic_data import generate_dataset, get_available_features, LABEL_MAP, LABEL_REVERSE

logger = logging.getLogger(__name__)

MODEL_DIR = Path(os.getenv("STORAGE_PATH", "./storage")) / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Feature columns provided by the real dataset
REAL_FEATURES = get_feature_columns()

# Synthetic feature names (superset, pruned by n_day_delay)
_SYNTHETIC_FEATURES = None


def _get_synthetic_features(n_day_delay: int = 7) -> list[str]:
    global _SYNTHETIC_FEATURES
    if _SYNTHETIC_FEATURES is None:
        _SYNTHETIC_FEATURES = get_available_features(n_day_delay)
    return _SYNTHETIC_FEATURES


def _prepare_real_data(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Convert real instafake DataFrame → (X, y) arrays for sklearn."""
    X = df[REAL_FEATURES].fillna(0).values.astype(float)
    label_map = {"GPAS": 0, "BPAS": 1, "EPAS": 2}
    y = df["pas_label"].map(label_map).values.astype(int)
    return X, y


def _prepare_synthetic_data(n: int, features: list[str]) -> tuple[np.ndarray, np.ndarray]:
    df = generate_dataset(n)
    X = df[features].values.astype(float)
    y = df["label"].values.astype(int)
    return X, y


class PASModel:
    def __init__(self, version: str, tier: str, n_day_delay: int = 7):
        self.version = version
        self.tier = tier
        self.n_day_delay = n_day_delay
        self.model = None
        self.scaler = StandardScaler()
        self.features: list[str] = []
        self.data_source: str = "unknown"
        self._trained = False

    def _build_clf(self):
        if self.tier == "v1":
            return DecisionTreeClassifier(max_depth=10, min_samples_leaf=5, random_state=42)
        if self.tier == "v2":
            return DecisionTreeClassifier(max_depth=15, min_samples_leaf=3, random_state=42)
        # production
        base = DecisionTreeClassifier(max_depth=10, min_samples_leaf=5, random_state=42)
        bagging = BaggingClassifier(
            estimator=base,
            n_estimators=50,
            max_samples=0.8,
            max_features=0.8,
            bootstrap=True,
            random_state=42,
            n_jobs=-1,
        )
        return CalibratedClassifierCV(bagging, method="isotonic", cv=3)

    def train(self, df: pd.DataFrame | None = None) -> dict:
        # --- try real data first ---
        real_df = load_real_pas_data()
        if real_df is not None and len(real_df) >= 100:
            logger.info(
                "Training PAS model on REAL instafake data (%d records)", len(real_df)
            )
            X, y = _prepare_real_data(real_df)
            self.features = REAL_FEATURES
            self.data_source = "instafake-real"
        else:
            # synthetic fallback
            syn_features = _get_synthetic_features(self.n_day_delay)
            n_samples = 50_000
            logger.info(
                "Real data unavailable — training on synthetic data (%d samples)", n_samples
            )
            X, y = _prepare_synthetic_data(n_samples, syn_features)
            self.features = syn_features
            self.data_source = "synthetic"

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, stratify=y, random_state=42
        )

        X_train_s = self.scaler.fit_transform(X_train)
        X_test_s = self.scaler.transform(X_test)

        self.model = self._build_clf()
        self.model.fit(X_train_s, y_train)
        self._trained = True

        metrics = self._evaluate(X_test_s, y_test)
        metrics["data_source"] = self.data_source
        metrics["n_train"] = len(X_train)
        metrics["n_test"] = len(X_test)
        return metrics

    def _evaluate(self, X: np.ndarray, y: np.ndarray) -> dict:
        y_pred = self.model.predict(X)
        precision, recall, f1, support = precision_recall_fscore_support(
            y, y_pred, labels=[0, 1, 2], zero_division=0
        )
        return {
            "precision_gpas": round(float(precision[0]), 4),
            "recall_gpas":    round(float(recall[0]), 4),
            "f1_gpas":        round(float(f1[0]), 4),
            "precision_bpas": round(float(precision[1]), 4),
            "recall_bpas":    round(float(recall[1]), 4),
            "f1_bpas":        round(float(f1[1]), 4),
            "precision_epas": round(float(precision[2]), 4),
            "recall_epas":    round(float(recall[2]), 4),
            "f1_epas":        round(float(f1[2]), 4),
        }

    def predict(self, feature_vectors: list[list[float]]) -> list[dict]:
        if not self._trained:
            raise RuntimeError("Model not trained")
        X = np.array(feature_vectors, dtype=float)
        X_s = self.scaler.transform(X)
        labels = self.model.predict(X_s)
        probs = (
            self.model.predict_proba(X_s)
            if hasattr(self.model, "predict_proba")
            else np.eye(3)[labels]
        )
        return [
            {
                "proxy_label": LABEL_REVERSE[int(lbl)],
                "proxy_probability": float(probs[i].max()),
                "probabilities": {
                    "GPAS": float(probs[i][0]),
                    "BPAS": float(probs[i][1]),
                    "EPAS": float(probs[i][2]),
                },
            }
            for i, lbl in enumerate(labels)
        ]

    def save(self, path: Path | None = None) -> Path:
        path = path or MODEL_DIR / f"pas_{self.tier}_{self.version}.joblib"
        joblib.dump(
            {
                "model": self.model,
                "scaler": self.scaler,
                "features": self.features,
                "version": self.version,
                "tier": self.tier,
                "n_day_delay": self.n_day_delay,
                "data_source": self.data_source,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "PASModel":
        data = joblib.load(path)
        inst = cls(
            version=data["version"],
            tier=data["tier"],
            n_day_delay=data["n_day_delay"],
        )
        inst.model = data["model"]
        inst.scaler = data["scaler"]
        inst.features = data["features"]
        inst.data_source = data.get("data_source", "unknown")
        inst._trained = True
        return inst


# ── singleton ──────────────────────────────────────────────────────────────────

_current_model: PASModel | None = None


def get_current_model() -> PASModel:
    global _current_model
    if _current_model is not None:
        return _current_model

    model_path = MODEL_DIR / "pas_production_current.joblib"
    if model_path.exists():
        try:
            _current_model = PASModel.load(model_path)
            logger.info(
                "PAS model loaded from disk: version=%s source=%s",
                _current_model.version, _current_model.data_source,
            )
            return _current_model
        except Exception as exc:
            logger.warning("Failed to load saved model (%s), retraining", exc)

    logger.info("Training PAS production model")
    m = PASModel(version="v1.0", tier="production")
    metrics = m.train()
    logger.info("PAS model ready: %s", metrics)
    m.save(model_path)
    _current_model = m
    return _current_model


def classify_accounts(
    accounts: list[dict],
    n_day_delay: int = 7,
    mode: str = "standard",
) -> list[dict]:
    model = get_current_model()

    # Build feature vectors using the model's feature list
    def _get_val(account: dict, feat: str) -> float:
        return float(account.get(feat, 0) or 0)

    vectors = [[_get_val(a, f) for f in model.features] for a in accounts]
    if not vectors:
        return []

    results = model.predict(vectors)
    for i, res in enumerate(results):
        res["account_id"] = accounts[i].get("account_id", f"acc_{i}")
    return results
