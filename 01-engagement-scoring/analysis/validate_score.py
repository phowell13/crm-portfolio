"""
Validate the engagement score and measure campaign incrementality.

YOUR ANALYSIS GOES HERE. The functions below are an outline with hints.

Run after creating data/output/engagement_score.csv:
  python analysis/validate_score.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "output"
IMAGES = ROOT / "images"


def load():
    score = pd.read_csv(OUT / "engagement_score.csv")
    orders = pd.read_csv(RAW / "orders.csv", parse_dates=["OrderDate"])
    campaign = pd.read_csv(RAW / "campaign_audience.csv")
    truth = pd.read_csv(RAW / "_truth_customer_profile.csv")
    return score, orders, campaign, truth


def score_vs_behaviour(score, orders):
    """Does a higher band actually mean more valuable customers?

    TODO:
      - Join orders to scores by SubscriberKey
      - For each EngagementBand: customers, % who ordered, average revenue
      - Is the pattern what you'd expect? If not, what would you change?
    """
    raise NotImplementedError


def score_vs_truth(score, truth):
    """Sanity check against the hidden profile (only possible with fake data).

    TODO:
      - Correlate EngagementScore with CurrentEngagement
      - Do 'lapsing' customers land in lower bands than 'warming' ones?
    """
    raise NotImplementedError


def holdout_lift(campaign, score=None):
    """Incremental impact of the Winter_Promo campaign.

    TODO:
      - Conversion rate for Target vs Control
      - Absolute lift = Target rate - Control rate
      - Relative lift = absolute lift / Control rate
      - Incremental conversions = absolute lift x number of Target customers
      - Is it statistically significant? (two-proportion z-test)
      - Bonus: lift by EngagementBand. Who should you stop mailing?
    """
    raise NotImplementedError


def charts():
    """Save 1-3 clear charts to images/ for the README.

    TODO: e.g. conversion rate by band, Target vs Control by band.
    """
    raise NotImplementedError


if __name__ == "__main__":
    score, orders, campaign, truth = load()
    score_vs_behaviour(score, orders)
    score_vs_truth(score, truth)
    holdout_lift(campaign, score)
    charts()
