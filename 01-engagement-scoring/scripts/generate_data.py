"""
Generate synthetic CRM data for the engagement & lead scoring project.

Everything here is invented. No real customer, company or employer data is used.

Outputs (in data/raw/):
  B2C (email programme, shaped like Salesforce Marketing Cloud data views)
    customers.csv          one row per subscriber
    job.csv                one row per email send (like the _Job data view)
    sent.csv               one row per email sent to a subscriber (like _Sent)
    open.csv               one row per open (like _Open)
    click.csv              one row per click (like _Click)
    orders.csv             purchases
    campaign_audience.csv  a promo campaign with a random 10% control group

  B2B (lead scoring)
    leads.csv              one row per lead, with firmographics
    lead_activity.csv      email, web, form and webinar activity
    opportunities.csv      leads that became sales opportunities

  _truth_customer_profile.csv
    The hidden engagement profile used to simulate behaviour. Do NOT use it
    to build the score. Use it afterwards to check whether your score
    recovers the real pattern.

Usage:
  python scripts/generate_data.py            # defaults
  python scripts/generate_data.py --customers 5000 --leads 3000 --seed 7
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

AS_OF = pd.Timestamp("2026-10-31")  # fixed "today" so results are reproducible
WEEKS = 52


# ---------------------------------------------------------------------------
# B2C email programme
# ---------------------------------------------------------------------------
def engagement_multiplier(trend, t):
    """How a customer's engagement changes over the year. t runs 0 -> 1."""
    if trend == "stable":
        return 1.0
    if trend == "lapsing":
        return 1.4 - 1.2 * t      # starts keen, fades
    if trend == "warming":
        return 0.4 + 1.1 * t      # starts quiet, warms up
    return 1.0


def make_b2c(rng, n_customers):
    ids = np.array([f"C{100000 + i}" for i in range(n_customers)])
    signup = AS_OF - pd.to_timedelta(rng.integers(30, 1500, n_customers), unit="D")
    region = rng.choice(
        ["London", "South East", "North West", "Midlands", "Scotland", "Wales", "South West"],
        n_customers, p=[0.22, 0.18, 0.14, 0.16, 0.1, 0.06, 0.14],
    )
    consent = rng.random(n_customers) < 0.86
    base = rng.beta(1.3, 4.0, n_customers)                 # underlying open propensity
    trend = rng.choice(["stable", "lapsing", "warming"], n_customers, p=[0.65, 0.25, 0.10])

    customers = pd.DataFrame({
        "SubscriberKey": ids,
        "SignupDate": signup.date,
        "Region": region,
        "EmailOptIn": consent.astype(int),
    })

    # One marketing email per week, plus an occasional extra promo send
    jobs, sent, opens, clicks = [], [], [], []
    job_id = 50000
    start = AS_OF - pd.Timedelta(weeks=WEEKS)
    for w in range(WEEKS):
        n_jobs = 2 if rng.random() < 0.25 else 1
        for j in range(n_jobs):
            job_id += 1
            send_time = start + pd.Timedelta(weeks=w, days=int(rng.integers(0, 5)), hours=int(rng.integers(7, 19)))
            name = "Weekly_Newsletter" if j == 0 else "Promo_" + rng.choice(["Sale", "NewIn", "Offer", "Reminder"])
            jobs.append((job_id, f"{name}_W{w + 1:02d}", send_time))

            eligible = consent & (signup < send_time)
            idx = np.flatnonzero(eligible)
            t = w / (WEEKS - 1)
            mult = np.array([engagement_multiplier(tr, t) for tr in trend[idx]])
            p_open = np.clip(base[idx] * mult * (0.8 if j else 1.0), 0, 0.95)
            opened = rng.random(len(idx)) < p_open
            p_click = np.clip(0.10 + 0.45 * base[idx], 0, 0.8)
            clicked = opened & (rng.random(len(idx)) < p_click)

            for k in idx:
                sent.append((job_id, ids[k], send_time))
            open_delay = pd.to_timedelta(rng.exponential(10, opened.sum()), unit="h")
            for k, d in zip(idx[opened], open_delay):
                opens.append((job_id, ids[k], send_time + d, 1))
                # some people open the same email again
                if rng.random() < 0.25:
                    opens.append((job_id, ids[k], send_time + d + pd.Timedelta(hours=float(rng.exponential(20))), 0))
            for k in idx[clicked]:
                link = rng.choice(["hero_cta", "product_1", "product_2", "footer_offer"])
                clicks.append((job_id, ids[k], send_time + pd.Timedelta(hours=float(rng.exponential(12))), link, 1))

    job = pd.DataFrame(jobs, columns=["JobID", "EmailName", "DeliveredTime"])
    sent = pd.DataFrame(sent, columns=["JobID", "SubscriberKey", "EventDate"])
    opn = pd.DataFrame(opens, columns=["JobID", "SubscriberKey", "EventDate", "IsUnique"])
    clk = pd.DataFrame(clicks, columns=["JobID", "SubscriberKey", "EventDate", "LinkName", "IsUnique"])
    # nothing can happen after "today", and keep timestamps to the second
    for df in (sent, opn, clk):
        df["EventDate"] = df["EventDate"].dt.floor("s")
    opn = opn[opn["EventDate"] <= AS_OF].reset_index(drop=True)
    clk = clk[clk["EventDate"] <= AS_OF].reset_index(drop=True)

    # Purchases: more engaged (right now) customers buy more often
    current = base * np.array([engagement_multiplier(tr, 1.0) for tr in trend])
    n_orders = rng.poisson(0.5 + 6 * current)
    order_rows = []
    oid = 900000
    for k in np.flatnonzero(n_orders):
        first_day = max(0, (AS_OF - pd.Timestamp(signup[k])).days)
        window = min(365, first_day)
        if window <= 0:
            continue
        for _ in range(n_orders[k]):
            oid += 1
            when = AS_OF - pd.Timedelta(days=int(rng.integers(0, window)))
            order_rows.append((oid, ids[k], when.date(), round(float(rng.lognormal(4.0, 0.5)), 2)))
    orders = pd.DataFrame(order_rows, columns=["OrderID", "SubscriberKey", "OrderDate", "OrderValue"])

    # Promo campaign 3 weeks ago, with a random 10% holdout (control) group
    camp_idx = np.flatnonzero(consent)
    group = np.where(rng.random(len(camp_idx)) < 0.10, "Control", "Target")
    eng = current[camp_idx] / current.max()
    p_conv = 0.02 + 0.05 * eng + np.where(group == "Target", 0.015 + 0.08 * eng, 0)
    converted = rng.random(len(camp_idx)) < p_conv
    revenue = np.where(converted, np.round(rng.lognormal(4.1, 0.45, len(camp_idx)), 2), 0.0)
    campaign = pd.DataFrame({
        "CampaignName": "Winter_Promo",
        "SendDate": (AS_OF - pd.Timedelta(days=21)).date(),
        "SubscriberKey": ids[camp_idx],
        "AudienceGroup": group,
        "Converted14d": converted.astype(int),
        "Revenue14d": revenue,
    })

    truth = pd.DataFrame({
        "SubscriberKey": ids,
        "BaseOpenPropensity": base.round(4),
        "Trend": trend,
        "CurrentEngagement": current.round(4),
    })
    return {
        "customers": customers, "job": job, "sent": sent, "open": opn, "click": clk,
        "orders": orders, "campaign_audience": campaign, "_truth_customer_profile": truth,
    }


# ---------------------------------------------------------------------------
# B2B lead scoring
# ---------------------------------------------------------------------------
def make_b2b(rng, n_leads):
    ids = np.array([f"L{200000 + i}" for i in range(n_leads)])
    industry = rng.choice(["Retail", "Financial Services", "Healthcare", "Manufacturing", "Education", "Tech"], n_leads)
    size = rng.choice(["1-49", "50-249", "250-999", "1000+"], n_leads, p=[0.4, 0.3, 0.2, 0.1])
    level = rng.choice(["Exec", "Director", "Manager", "Individual"], n_leads, p=[0.08, 0.17, 0.35, 0.40])
    source = rng.choice(["Organic", "Paid Search", "Event", "Referral", "Content Download"], n_leads)
    created = AS_OF - pd.to_timedelta(rng.integers(5, 270, n_leads), unit="D")

    size_fit = pd.Series(size).map({"1-49": 0.0, "50-249": 0.6, "250-999": 1.0, "1000+": 0.8}).to_numpy()
    level_fit = pd.Series(level).map({"Exec": 1.0, "Director": 0.9, "Manager": 0.5, "Individual": 0.1}).to_numpy()
    fit = (size_fit + level_fit) / 2 + rng.normal(0, 0.1, n_leads)
    intent = rng.beta(1.2, 3.0, n_leads)

    leads = pd.DataFrame({
        "LeadID": ids, "CreatedDate": created.date, "Industry": industry,
        "CompanySize": size, "JobLevel": level, "LeadSource": source,
    })

    rates = {  # expected events per lead at full intent
        "EmailOpen": 12, "EmailClick": 4, "WebVisit": 8,
        "PricingPageVisit": 2, "FormFill": 1, "WebinarAttend": 0.6,
    }
    rows = []
    for k in range(n_leads):
        age = max(1, (AS_OF - created[k]).days)
        for act, r in rates.items():
            for _ in range(rng.poisson(r * intent[k] + 0.2)):
                rows.append((ids[k], act, (AS_OF - pd.Timedelta(days=int(rng.integers(0, age)))).date()))
    activity = pd.DataFrame(rows, columns=["LeadID", "ActivityType", "ActivityDate"])

    p_opp = 1 / (1 + np.exp(-(-4.2 + 2.0 * fit + 3.0 * intent)))
    became_opp = rng.random(n_leads) < p_opp
    opps = pd.DataFrame({
        "LeadID": ids[became_opp],
        "OpportunityCreatedDate": [
            (AS_OF - pd.Timedelta(days=int(rng.integers(0, max(1, (AS_OF - created[k]).days))))).date()
            for k in np.flatnonzero(became_opp)
        ],
    })
    return {"leads": leads, "lead_activity": activity, "opportunities": opps}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--customers", type=int, default=3000)
    ap.add_argument("--leads", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data"))
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "sample").mkdir(parents=True, exist_ok=True)

    tables = {**make_b2c(rng, args.customers), **make_b2b(rng, args.leads)}
    for name, df in tables.items():
        df.to_csv(out / "raw" / f"{name}.csv", index=False)
        df.head(20).to_csv(out / "sample" / f"{name}.csv", index=False)
        print(f"{name:<26} {len(df):>8,} rows")
    print(f"\nWritten to {out / 'raw'} (full) and {out / 'sample'} (first 20 rows)")


if __name__ == "__main__":
    main()
