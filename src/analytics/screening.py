from __future__ import annotations

import pandas as pd


def screening_category(data: pd.DataFrame) -> pd.Series:
    beneish = data["RiskLabel"].eq("Potential earnings manipulation")
    anomaly = data["AnomalyLabel"].eq(-1)
    return pd.Series([
        "Flagged by Beneish and anomaly" if b and a else "Flagged by Beneish only" if b else "Flagged by anomaly only" if a else "Not indicated by either method"
        for b, a in zip(beneish.fillna(False), anomaly.fillna(False))
    ], index=data.index)
