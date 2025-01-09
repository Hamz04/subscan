"""
Savings Calculator
Generates cancellation recommendations and savings projections
"""

import pandas as pd
import numpy as np
from typing import List, Dict

CATEGORY_ESSENTIALS = {"software", "finance"}
CATEGORY_LUXURY = {"gaming", "streaming", "fitness", "learning", "news", "reading"}

def rank_cancellation_candidates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["cancel_score"] = (
        df["forgotten_score"] * 0.4 +
        (df["monthly_cost"] / df["monthly_cost"].max() * 100) * 0.3 +
        df["category"].apply(lambda c: 30 if c in CATEGORY_LUXURY else 0) * 0.3
    ).round(1)
    df["recommendation"] = df.apply(classify_recommendation, axis=1)
    df["priority"] = df["cancel_score"].apply(
        lambda s: "High" if s >= 60 else ("Medium" if s >= 35 else "Low")
    )
    return df.sort_values("cancel_score", ascending=False).reset_index(drop=True)

def classify_recommendation(row) -> str:
    if row["forgotten_score"] >= 60:
        return "Likely forgotten — cancel immediately"
    if row["category"] in CATEGORY_LUXURY and row["times_charged"] <= 2:
        return "Low usage detected — consider cancelling"
    if row["category"] in CATEGORY_LUXURY:
        return "Nice to have — cancel if cutting costs"
    return "Regularly used — keep"

def calculate_savings(df: pd.DataFrame, selected_services: List[str] = None) -> Dict:
    if df.empty:
        return {}
    if selected_services:
        cancel_df = df[df["service"].isin(selected_services)]
    else:
        cancel_df = df[df["priority"].isin(["High", "Medium"])]
    total_monthly = df["monthly_cost"].sum()
    total_annual = df["annual_cost"].sum()
    savings_monthly = cancel_df["monthly_cost"].sum()
    savings_annual = cancel_df["annual_cost"].sum()
    category_breakdown = df.groupby("category")["monthly_cost"].sum().to_dict()
    return {
        "total_monthly_spend": round(total_monthly, 2),
        "total_annual_spend": round(total_annual, 2),
        "potential_monthly_savings": round(savings_monthly, 2),
        "potential_annual_savings": round(savings_annual, 2),
        "savings_percentage": round((savings_monthly / total_monthly * 100) if total_monthly > 0 else 0, 1),
        "subscriptions_to_cancel": len(cancel_df),
        "total_subscriptions": len(df),
        "category_breakdown": category_breakdown,
        "top_drain": df.iloc[0]["service"] if not df.empty else None,
        "biggest_forgotten": df[df["forgotten_score"] == df["forgotten_score"].max()].iloc[0]["service"] if not df.empty else None,
    }
