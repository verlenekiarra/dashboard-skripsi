from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from src.analytics.beneish import (
    BASELINE_THRESHOLD,
    INDEX_COLUMNS,
    SENSITIVITY_THRESHOLD,
    AnalysisConfig,
    calculate_indices,
    classify_beneish,
    rank_screening,
)

INSUFFICIENT = "Insufficient data / not calculable"


def analyze_against_population(
    frame: pd.DataFrame,
    population: pd.DataFrame | None = None,
    config: AnalysisConfig = AnalysisConfig(),
) -> tuple[pd.DataFrame, int]:
    """Analyze `frame`, judging anomalies against `population`.

    Returns the analyzed rows for `frame` only, plus the number of observations
    the Isolation Forest was fitted on. When `population` is empty or missing
    the eight indices, this falls back to fitting on `frame` alone, which is the
    existing single-batch behaviour.
    """
    result = calculate_indices(frame)
    result["Status_178"] = classify_beneish(result["MScore"], BASELINE_THRESHOLD)
    result["Status_222"] = classify_beneish(result["MScore"], SENSITIVITY_THRESHOLD)
    result["RiskLabel"] = result["Status_178"]

    index_columns = list(INDEX_COLUMNS)
    result["AnomalyScore"] = np.nan
    result["AnomalyLabel"] = pd.Series(pd.array([pd.NA] * len(result), dtype="Int64"), index=result.index)
    result["AnomalyStatus"] = INSUFFICIENT

    complete = result[index_columns].notna().all(axis=1)
    if complete.sum() == 0:
        return _finalize(result), 0

    own_features = result.loc[complete, index_columns]

    reference = pd.DataFrame(columns=index_columns)
    if population is not None and not population.empty and set(index_columns).issubset(population.columns):
        reference = population[index_columns].dropna()

    training = pd.concat([reference, own_features], ignore_index=True)
    model = IsolationForest(
        n_estimators=config.n_estimators,
        contamination=config.contamination,
        random_state=config.random_state,
    )
    model.fit(training)

    result.loc[complete, "AnomalyScore"] = -model.score_samples(own_features)
    result.loc[complete, "AnomalyLabel"] = model.predict(own_features)
    return _finalize(result), len(training)


def _finalize(result: pd.DataFrame) -> pd.DataFrame:
    """Apply the stored status and screening conventions."""
    anomaly_label = result["AnomalyLabel"].astype("Int64")
    result["AnomalyStatus"] = np.select(
        [
            anomaly_label.eq(-1).fillna(False).to_numpy(dtype=bool),
            anomaly_label.eq(1).fillna(False).to_numpy(dtype=bool),
        ],
        ["Anomaly", "Normal"],
        default=INSUFFICIENT,
    )
    risk_flag = result["RiskLabel"].eq("Potential earnings manipulation").fillna(False).to_numpy(dtype=bool)
    anomaly_flag = anomaly_label.eq(-1).fillna(False).to_numpy(dtype=bool)
    incomplete = (result["MScore"].isna() | anomaly_label.isna()).to_numpy(dtype=bool)
    result["ScreeningPriority"] = np.select(
        [risk_flag & anomaly_flag, risk_flag, anomaly_flag, incomplete],
        ["Priority screening", "Beneish flag", "Anomaly flag", INSUFFICIENT],
        default="Low priority",
    )
    return rank_screening(result)
