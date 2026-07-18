"""
train_models.py
Trains and compares eight ML algorithms (Random Forest, XGBoost, LightGBM,
CatBoost, Extra Trees, Gradient Boosting, Voting Ensemble, Stacking
Ensemble) on the fire-risk dataset, evaluates each on Accuracy, Precision,
Recall, F1, ROC-AUC, training time and prediction time, auto-selects the
best model (highest F1, tie-broken by ROC-AUC then lowest false-negative
rate), saves it with joblib, and generates SHAP explainability artifacts.


Run directly:
    python backend/training/train_models.py --data dataset/processed/fire_data.csv
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import (
    ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier,
    StackingClassifier, VotingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score, roc_curve, precision_recall_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import DATA, MODEL, PATHS
from backend.utils.logger import get_logger
from backend.utils.preprocessing import run_preprocessing_pipeline
from backend.utils.feature_engineering import engineer_all_features

logger = get_logger(__name__)


def build_models() -> Dict[str, object]:
    rs = MODEL.random_state
    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, max_depth=None, n_jobs=MODEL.n_jobs, random_state=rs
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            eval_metric="logloss", n_jobs=MODEL.n_jobs, random_state=rs,
            use_label_encoder=False,
        ),
        "LightGBM": LGBMClassifier(
            n_estimators=300, learning_rate=0.05, num_leaves=31,
            n_jobs=MODEL.n_jobs, random_state=rs, verbosity=-1,
        ),
        "CatBoost": CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6,
            random_state=rs, verbose=False,
        ),
        "ExtraTrees": ExtraTreesClassifier(
            n_estimators=300, n_jobs=MODEL.n_jobs, random_state=rs
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=4, random_state=rs
        ),
    }

    voting = VotingClassifier(
        estimators=[
            ("rf", models["RandomForest"]),
            ("xgb", models["XGBoost"]),
            ("lgbm", models["LightGBM"]),
        ],
        voting="soft", n_jobs=MODEL.n_jobs,
    )
    models["VotingEnsemble"] = voting

    stacking = StackingClassifier(
        estimators=[
            ("rf", RandomForestClassifier(n_estimators=200, random_state=rs)),
            ("xgb", XGBClassifier(n_estimators=200, eval_metric="logloss",
                                   random_state=rs, use_label_encoder=False)),
            ("cat", CatBoostClassifier(iterations=200, random_state=rs, verbose=False)),
        ],
        final_estimator=LogisticRegression(max_iter=1000),
        n_jobs=MODEL.n_jobs,
        passthrough=False,
    )
    models["StackingEnsemble"] = stacking

    return models


def evaluate_model(model, X_test, y_test) -> dict:
    start_pred = time.time()
    y_pred = model.predict(X_test)
    pred_time = time.time() - start_pred

    try:
        y_proba = model.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)
    except Exception:
        y_proba = None
        roc_auc = np.nan

    cm = confusion_matrix(y_test, y_pred)
    fn = cm[1][0] if cm.shape == (2, 2) else np.nan

    return {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average="weighted", zero_division=0),
        "recall": recall_score(y_test, y_pred, average="weighted", zero_division=0),
        "f1_score": f1_score(y_test, y_pred, average="weighted", zero_division=0),
        "roc_auc": roc_auc,
        "prediction_time_sec": pred_time,
        "false_negatives": int(fn) if not np.isnan(fn) else None,
        "confusion_matrix": cm.tolist(),
    }


def select_best_model(results_df: pd.DataFrame) -> str:
    """Best model = highest F1, tie-broken by highest ROC-AUC, then lowest FN."""
    sorted_df = results_df.sort_values(
        by=["f1_score", "roc_auc"], ascending=[False, False]
    )
    # among top-F1 ties, prefer lowest false negatives (missed fire events are costly)
    top_f1 = sorted_df[sorted_df["f1_score"] == sorted_df["f1_score"].iloc[0]]
    if len(top_f1) > 1 and top_f1["false_negatives"].notna().all():
        top_f1 = top_f1.sort_values(by="false_negatives", ascending=True)
    return top_f1.index[0]


def generate_shap_explanations(model, X_train_sample: np.ndarray,
                                X_explain: np.ndarray, feature_names: list,
                                model_name: str):
    """
    Generates and saves global + local SHAP explainability artifacts:
    summary plot data, waterfall for one sample, and mean |SHAP| global
    importance table. Uses TreeExplainer for tree-based models (fast, exact)
    with a KernelExplainer fallback for anything else.
    """
    os.makedirs(PATHS.shap_dir, exist_ok=True)
    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_explain)
        if isinstance(shap_values, list):  # binary classifiers sometimes return [class0, class1]
            shap_values = shap_values[1]
    except Exception as e:
        logger.warning(f"TreeExplainer failed for {model_name} ({e}); falling back to KernelExplainer.")
        background = shap.sample(X_train_sample, min(50, len(X_train_sample)))
        explainer = shap.KernelExplainer(model.predict_proba, background)
        shap_values = explainer.shap_values(X_explain, nsamples=100)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        # Handle different SHAP output formats
    shap_values = np.asarray(shap_values)

    if shap_values.ndim == 3:
        # (samples, features, classes)
        shap_values = shap_values[:, :, 1]

    elif shap_values.ndim == 1:
        shap_values = shap_values.reshape(-1, 1)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    # Make sure lengths match
    feature_names = list(feature_names)

    if len(mean_abs_shap) != len(feature_names):
        logger.warning(
            f"SHAP length mismatch: features={len(feature_names)}, shap={len(mean_abs_shap)}"
        )

        n = min(len(feature_names), len(mean_abs_shap))
        feature_names = feature_names[:n]
        mean_abs_shap = mean_abs_shap[:n]

    global_importance = pd.DataFrame({
        "feature": feature_names,
        "mean_abs_shap": mean_abs_shap
    }).sort_values("mean_abs_shap", ascending=False)

    global_importance.to_csv(
        os.path.join(PATHS.shap_dir, f"{model_name}_global_importance.csv"),
        index=False
    )

    np.save(
        os.path.join(PATHS.shap_dir, f"{model_name}_shap_values.npy"),
        shap_values
    )

    logger.info(f"SHAP artifacts saved for {model_name} in {PATHS.shap_dir}")

    return global_importance, shap_values


def run_training(data_path: str, target_col: str = DATA.binary_target_column):
    logger.info(f"Loading dataset from {data_path}")
    raw_df = pd.read_csv(data_path)
    raw_df = engineer_all_features(raw_df) if "temperature" in raw_df.columns else raw_df

    X_train, X_val, X_test, y_train, y_val, y_test, artifacts = run_preprocessing_pipeline(
        raw_df, target_col=target_col
    )

    models = build_models()
    results = {}
    trained_models = {}

    for name, model in models.items():
        logger.info(f"Training {name} ...")
        start = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start

        metrics = evaluate_model(model, X_test, y_test)
        metrics["training_time_sec"] = train_time

        cv = StratifiedKFold(n_splits=MODEL.cv_folds, shuffle=True, random_state=MODEL.random_state)
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1_weighted", n_jobs=MODEL.n_jobs)
        metrics["cv_f1_mean"] = float(cv_scores.mean())
        metrics["cv_f1_std"] = float(cv_scores.std())

        results[name] = metrics
        trained_models[name] = model
        logger.info(f"{name}: F1={metrics['f1_score']:.4f} ROC-AUC={metrics['roc_auc']:.4f} "
                    f"Train={train_time:.2f}s")

    results_df = pd.DataFrame(results).T
    results_df.to_csv(os.path.join(PATHS.reports_dir, "model_comparison.csv"))
    logger.info(f"Model comparison table saved to {PATHS.reports_dir}/model_comparison.csv")

    best_name = select_best_model(results_df)
    best_model = trained_models[best_name]
    logger.info(f"Best model selected: {best_name}")

    joblib.dump(best_model, os.path.join(PATHS.models_dir, "best_model.joblib"))
    with open(os.path.join(PATHS.models_dir, "best_model_meta.json"), "w") as f:
        json.dump({
            "model_name": best_name,
            "metrics": results[best_name],
            "feature_columns": artifacts.feature_columns,
        }, f, indent=2, default=str)

    for name, model in trained_models.items():
        joblib.dump(model, os.path.join(PATHS.models_dir, f"{name}.joblib"))

    sample_idx = np.random.RandomState(MODEL.random_state).choice(
        len(X_test), size=min(100, len(X_test)), replace=False
    )
    generate_shap_explanations(
        best_model, X_train, X_test[sample_idx], artifacts.feature_columns, best_name
    )

    logger.info("Training pipeline complete.")
    return results_df, best_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train and compare fire-risk ML models.")
    parser.add_argument("--data", type=str, required=True, help="Path to processed CSV dataset")
    parser.add_argument("--target", type=str, default=DATA.binary_target_column)
    args = parser.parse_args()

    run_training(args.data, args.target)
