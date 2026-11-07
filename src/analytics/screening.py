from __future__ import annotations

import pandas as pd


def screening_category(data: pd.DataFrame) -> pd.Series:
    beneish = data["RiskLabel"].eq("Potential earnings manipulation")
    anomaly = data["AnomalyLabel"].eq(-1)
    return pd.Series([
        "Terindikasi oleh Beneish dan anomaly" if b and a else "Terindikasi oleh Beneish saja" if b else "Terdeteksi anomaly saja" if a else "Tidak terindikasi manipulasi oleh kedua metode"
        for b, a in zip(beneish.fillna(False), anomaly.fillna(False))
    ], index=data.index)
