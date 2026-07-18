"""
preprocessing.py
Handles missing values, duplicates, outliers, encoding, scaling, class
balancing (SMOTE) and the train/val/test split. Returns fitted
transformers alongside the split arrays so the exact same pipeline can be
re-applied to a single live-weather row at inference time.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Tuple

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.config import DATA, PATHS
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PreprocessArtifacts:
    scaler: StandardScaler
    label_encoders: dict
    feature_columns: list


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates()
    logger.info(f"Removed {before - len(df)} duplicate rows.")
    return df


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns

    for col in numeric_cols:
        if df[col].isna().any():
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

    for col in categorical_cols:
        if df[col].isna().any():
            mode_val = df[col].mode().iloc[0] if not df[col].mode().empty else "unknown"
            df[col] = df[col].fillna(mode_val)

    logger.info("Missing values imputed (median for numeric, mode for categorical).")
    return df


def remove_outliers_iqr(df: pd.DataFrame, columns: list, factor: float = 3.0) -> pd.DataFrame:
    """Removes extreme outliers using the IQR rule. factor=3.0 is deliberately
    wide so we only strip clearly erroneous sensor readings, not genuine
    extreme-weather fire-risk events which are exactly what we want to keep."""
    before = len(df)
    mask = pd.Series(True, index=df.index)
    for col in columns:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - factor * iqr, q3 + factor * iqr
        mask &= df[col].between(lower, upper)
    df = df[mask]
    logger.info(f"Removed {before - len(df)} outlier rows.")
    return df


def encode_categoricals(df: pd.DataFrame, categorical_cols: list) -> Tuple[pd.DataFrame, dict]:
    encoders = {}
    for col in categorical_cols:
        if col not in df.columns:
            continue
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    return df, encoders


def scale_features(df: pd.DataFrame, feature_cols: list) -> Tuple[pd.DataFrame, StandardScaler]:
    scaler = StandardScaler()
    df[feature_cols] = scaler.fit_transform(df[feature_cols])
    return df, scaler


def balance_classes(X: pd.DataFrame, y: pd.Series, k_neighbors: int = 5) -> Tuple[pd.DataFrame, pd.Series]:
    """SMOTE oversampling to address the class imbalance ignored by prior work."""
    class_counts = y.value_counts()
    logger.info(f"Class distribution before SMOTE: {class_counts.to_dict()}")

    min_class_size = class_counts.min()
    safe_k = max(1, min(k_neighbors, min_class_size - 1)) if min_class_size > 1 else 1

    smote = SMOTE(random_state=DATA.random_state, k_neighbors=safe_k)
    X_res, y_res = smote.fit_resample(X, y)
    logger.info(f"Class distribution after SMOTE: {pd.Series(y_res).value_counts().to_dict()}")
    return X_res, y_res


def run_preprocessing_pipeline(
    raw_df: pd.DataFrame,
    target_col: str = DATA.binary_target_column,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, PreprocessArtifacts]:
    """
    Full pipeline: clean -> engineer-ready -> encode -> scale -> split -> SMOTE (train only).
    Returns X_train, X_val, X_test, y_train, y_val, y_test, artifacts.
    SMOTE is applied ONLY to the training split to avoid data leakage into
    validation/test — a mistake common in the baseline papers we improve on.
    """
    df = raw_df.copy()
    df = remove_duplicates(df)
    df = handle_missing_values(df)

    numeric_present = [c for c in DATA.numeric_features if c in df.columns]
    df = remove_outliers_iqr(df, numeric_present)

    categorical_present = [c for c in DATA.categorical_features if c in df.columns]
    df, label_encoders = encode_categoricals(df, categorical_present)

    feature_columns = numeric_present + categorical_present
    X = df[feature_columns]
    y = df[target_col]

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=DATA.test_size + DATA.val_size,
        stratify=y, random_state=DATA.random_state
    )
    relative_val_size = DATA.val_size / (DATA.test_size + DATA.val_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=1 - relative_val_size,
        stratify=y_temp, random_state=DATA.random_state
    )

    X_train, scaler = scale_features(X_train, feature_columns)
    X_val[feature_columns] = scaler.transform(X_val[feature_columns])
    X_test[feature_columns] = scaler.transform(X_test[feature_columns])

    X_train_res, y_train_res = balance_classes(X_train, y_train, DATA.smote_k_neighbors)

    artifacts = PreprocessArtifacts(
        scaler=scaler, label_encoders=label_encoders, feature_columns=feature_columns
    )

    os.makedirs(PATHS.models_dir, exist_ok=True)
    joblib.dump(artifacts, os.path.join(PATHS.models_dir, "preprocess_artifacts.joblib"))
    logger.info("Preprocessing complete. Artifacts saved to models/saved/preprocess_artifacts.joblib")

    return (
        X_train_res.values, X_val.values, X_test.values,
        y_train_res.values if hasattr(y_train_res, "values") else np.array(y_train_res),
        y_val.values, y_test.values, artifacts
    )
