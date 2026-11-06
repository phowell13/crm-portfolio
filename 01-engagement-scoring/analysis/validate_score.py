"""
Validate the engagement score and measure campaign incrementality.

Three questions:
  1. Do higher bands behave better? (orders and revenue by band)
  2. Does the score find the right people? (check against the hidden profile,
     only possible because the data is synthetic)
  3. Did the Winter Promo drive extra sales, and in which bands?
     (Target vs a random 10% Control group)

Run after creating data/output/engagement_score.csv:
  python analysis/validate_score.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "output"
IMAGES = ROOT / "images"
AS_OF = pd.Timestamp("2026-10-31")

BANDS = ["Highly engaged", "Engaged", "Lapsing", "Dormant", "Inactive"]
COLOURS = ["#0b7a75", "#3aa39c", "#e0a43a", "#d9774b", "#9aa5b4"]


def load():
    score = pd.read_csv(OUT / "engagement_score.csv")
    orders = pd.read_csv(RAW / "orders.csv", parse_dates=["OrderDate"])
    campaign = pd.read_csv(RAW / "campaign_audience.csv")
    truth = pd.read_csv(RAW / "_truth_customer_profile.csv")
    score["EngagementBand"] = pd.Categorical(score["EngagementBand"], BANDS, ordered=True)
    return score, orders, campaign, truth


def header(text):
    print(f"\n{'=' * 70}\n{text}\n{'=' * 70}")


def score_vs_behaviour(score, orders, days=90):
    """Orders and revenue by band, over the last `days` days."""
    header(f"1. Orders by band (last {days} days)")
    recent = orders[orders["OrderDate"] >= AS_OF - pd.Timedelta(days=days)]
    per_cust = recent.groupby("SubscriberKey").agg(Orders=("OrderID", "count"), Revenue=("OrderValue", "sum"))
    df = score.merge(per_cust, on="SubscriberKey", how="left").fillna({"Orders": 0, "Revenue": 0})
    table = df.groupby("EngagementBand", observed=True).agg(
        Customers=("SubscriberKey", "count"),
        PctOrdered=("Orders", lambda s: (s > 0).mean()),
        OrdersPerCustomer=("Orders", "mean"),
        RevenuePerCustomer=("Revenue", "mean"),
        TotalRevenue=("Revenue", "sum"),
    )
    table["ShareOfRevenue"] = table["TotalRevenue"] / table["TotalRevenue"].sum()
    table["ShareOfCustomers"] = table["Customers"] / table["Customers"].sum()
    show = table.copy()
    show["PctOrdered"] = (show["PctOrdered"] * 100).round(1).astype(str) + "%"
    show["OrdersPerCustomer"] = show["OrdersPerCustomer"].round(2)
    show["RevenuePerCustomer"] = "£" + show["RevenuePerCustomer"].round(2).astype(str)
    show["TotalRevenue"] = "£" + show["TotalRevenue"].round(0).astype(int).map("{:,}".format)
    show["ShareOfRevenue"] = (show["ShareOfRevenue"] * 100).round(1).astype(str) + "%"
    show["ShareOfCustomers"] = (show["ShareOfCustomers"] * 100).round(1).astype(str) + "%"
    print(show.to_string())
    print("\nNote: scores and orders cover the same period, so this shows the score lines up with "
          "buying behaviour. A true predictive test would score at one date and measure orders afterwards.")
    return table


def score_vs_truth(score, truth):
    """Check the score against the hidden behaviour used to create the data."""
    header("2. Score vs hidden engagement profile (synthetic data only)")
    df = score.merge(truth, on="SubscriberKey")
    corr = df["EngagementScore"].corr(df["CurrentEngagement"])
    print(f"Correlation between EngagementScore and true current engagement: {corr:.2f}")
    mix = pd.crosstab(df["EngagementBand"], df["Trend"], normalize="index").round(2)
    print("\nHidden trend mix within each band (rows add to 1):")
    print(mix.to_string())
    return corr


def two_prop_ztest(conv_a, n_a, conv_b, n_b):
    """Two-sided two-proportion z-test. Returns z and p-value."""
    p_pool = (conv_a + conv_b) / (n_a + n_b)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return 0.0, 1.0
    z = (conv_a / n_a - conv_b / n_b) / se
    return z, 2 * (1 - norm.cdf(abs(z)))


def lift_row(g):
    t, c = g[g["AudienceGroup"] == "Target"], g[g["AudienceGroup"] == "Control"]
    nt, nc = len(t), len(c)
    ct, cc = t["Converted14d"].sum(), c["Converted14d"].sum()
    rt, rc = ct / nt if nt else 0, cc / nc if nc else 0
    z, p = two_prop_ztest(ct, nt, cc, nc) if nt and nc else (0, 1)
    rev_t = t["Revenue14d"].sum() / nt if nt else 0
    rev_c = c["Revenue14d"].sum() / nc if nc else 0
    return pd.Series({
        "Target": nt, "Control": nc,
        "TargetConv": rt, "ControlConv": rc,
        "AbsLift": rt - rc,
        "RelLift": (rt - rc) / rc if rc else np.nan,
        "IncrementalOrders": (rt - rc) * nt,
        "IncrementalRevenue": (rev_t - rev_c) * nt,
        "p_value": p,
    })


def fmt_lift(df):
    out = df.copy()
    for col in ["TargetConv", "ControlConv", "AbsLift"]:
        out[col] = (out[col] * 100).round(1).astype(str) + "%"
    out["RelLift"] = (out["RelLift"] * 100).round(0).astype("Int64").astype(str) + "%"
    out["IncrementalOrders"] = out["IncrementalOrders"].round(0).astype(int)
    out["IncrementalRevenue"] = "£" + out["IncrementalRevenue"].round(0).astype(int).map("{:,}".format)
    out["p_value"] = out["p_value"].round(3)
    out[["Target", "Control"]] = out[["Target", "Control"]].astype(int)
    return out


def holdout_lift(campaign, score):
    """Incremental impact of the Winter_Promo campaign, overall and by band."""
    header("3. Winter Promo: Target vs Control (14-day conversion)")
    overall = lift_row(campaign).to_frame("All customers").T
    print(fmt_lift(overall).to_string())
    sig = "significant at 95%" if overall["p_value"].iloc[0] < 0.05 else "NOT significant at 95%"
    print(f"\nOverall lift is {sig} (p = {overall['p_value'].iloc[0]:.3f}).")

    df = campaign.merge(score[["SubscriberKey", "EngagementBand"]], on="SubscriberKey", how="left")
    by_band = df.groupby("EngagementBand", observed=True).apply(lift_row, include_groups=False)
    print("\nBy band:")
    print(fmt_lift(by_band).to_string())
    print("\nNote: each band has a small control group (roughly 30-70 people), so band-level "
          "p-values are weak. Treat band results as directional; a bigger holdout would confirm them.")
    return overall, by_band


def charts(behaviour, by_band):
    """Save charts to images/ for the README."""
    IMAGES.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})

    # 1. % ordered by band
    fig, ax = plt.subplots(figsize=(7, 4))
    vals = behaviour["PctOrdered"] * 100
    bars = ax.bar(vals.index.astype(str), vals.values, color=COLOURS)
    ax.bar_label(bars, labels=[f"{v:.0f}%" for v in vals.values], padding=3)
    ax.set_ylabel("Customers who ordered (last 90 days)")
    ax.set_title("Higher engagement bands buy more", loc="left", fontweight="bold")
    ax.set_ylim(0, vals.max() * 1.2)
    fig.tight_layout(); fig.savefig(IMAGES / "orders_by_band.png", dpi=150); plt.close(fig)

    # 2. Target vs Control conversion by band
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(by_band)); w = 0.38
    t = by_band["TargetConv"] * 100; c = by_band["ControlConv"] * 100
    b1 = ax.bar(x - w / 2, t, w, label="Target (mailed)", color="#0b7a75")
    b2 = ax.bar(x + w / 2, c, w, label="Control (not mailed)", color="#c9d1db")
    ax.bar_label(b1, labels=[f"{v:.1f}%" for v in t], padding=2, fontsize=8)
    ax.bar_label(b2, labels=[f"{v:.1f}%" for v in c], padding=2, fontsize=8)
    ax.set_xticks(x, by_band.index.astype(str))
    ax.set_ylabel("14-day conversion rate")
    ax.set_title("Winter Promo: where the campaign made a difference", loc="left", fontweight="bold")
    ax.legend(frameon=False)
    ax.set_ylim(0, max(t.max(), c.max()) * 1.25)
    fig.tight_layout(); fig.savefig(IMAGES / "campaign_lift_by_band.png", dpi=150); plt.close(fig)

    # 3. Share of customers vs share of revenue
    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(len(behaviour)); w = 0.38
    sc = behaviour["ShareOfCustomers"] * 100; sr = behaviour["ShareOfRevenue"] * 100
    b1 = ax.bar(x - w / 2, sc, w, label="Share of customers", color="#c9d1db")
    b2 = ax.bar(x + w / 2, sr, w, label="Share of revenue", color="#0b7a75")
    ax.bar_label(b1, labels=[f"{v:.0f}%" for v in sc], padding=2, fontsize=8)
    ax.bar_label(b2, labels=[f"{v:.0f}%" for v in sr], padding=2, fontsize=8)
    ax.set_xticks(x, behaviour.index.astype(str))
    ax.set_ylabel("% (last 90 days)")
    ax.set_title("Revenue is concentrated in the top bands", loc="left", fontweight="bold")
    ax.legend(frameon=False)
    ax.set_ylim(0, max(sc.max(), sr.max()) * 1.25)
    fig.tight_layout(); fig.savefig(IMAGES / "revenue_share_by_band.png", dpi=150); plt.close(fig)
    print(f"\nCharts saved to {IMAGES}")


if __name__ == "__main__":
    score, orders, campaign, truth = load()
    behaviour = score_vs_behaviour(score, orders)
    score_vs_truth(score, truth)
    overall, by_band = holdout_lift(campaign, score)
    charts(behaviour, by_band)
