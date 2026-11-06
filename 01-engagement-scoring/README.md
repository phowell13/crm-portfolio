# Email engagement & lead scoring

Scoring customers and leads on behaviour, then using the score to make channel and sales decisions, and proving it works with a control group.

> Built on synthetic data. Inspired by approaches I've used in industry, rebuilt from scratch with no employer data, code or rules.

---

## The problem
> ✏️ _2–3 sentences. Why does a business need an engagement score? (e.g. sending print to customers who'd happily read email wastes money; sending everything to everyone hurts deliverability.)_

## What's in here

| Part | What it does | Where |
|---|---|---|
| Synthetic data | Generates SFMC-style email data (`_Sent`, `_Open`, `_Click`), orders, a campaign with a 10% control group, and B2B leads | `scripts/generate_data.py` |
| B2C engagement score | SQL scoring subscribers on recency and frequency of opens and clicks, grouped into bands | `sql/01_engagement_score.sql` |
| B2B lead score | SQL combining fit and intent into a lead score with an MQL threshold | `sql/02_lead_score.sql` |
| Validation & incrementality | Python checks that the score predicts behaviour, and measures campaign lift against the control group | `analysis/validate_score.py` |
| Dynamic content | AMPscript showing content by engagement band | `ampscript/` |
| QA | Pre-build peer review checklist (GDPR, data QA, email quality) | `qa/pre_build_checklist.md` |
| Decisions | Why each choice was made | `DECISIONS.md` |

## Approach
> ✏️ _Explain your scoring logic in plain English: signals, weights, recency, bands. A non-technical marketer should understand it._

## Results
> ✏️ _Your 2–3 charts from `images/` and what they show. e.g. "Highly engaged customers converted at X% vs Y% for dormant", "The campaign drove Z incremental orders; lift was concentrated in the Engaged band."_

## How the score is used
> ✏️ _The decision rules. e.g. Highly engaged → email only, never print; Dormant → print or SMS win-back; MQL → hand to sales._

## What I'd do next
> ✏️ _Limitations and next steps. e.g. Apple MPP inflating opens, adding purchase data, testing thresholds._

## Run it yourself

```bash
pip install -r ../requirements.txt
python scripts/generate_data.py                # creates data/raw/
python scripts/run_sql.py sql/00_smoke_test.sql
python scripts/run_sql.py sql/01_engagement_score.sql --out data/output/engagement_score.csv
python analysis/validate_score.py
```

SQL is written to work in an SFMC Query Activity (T-SQL) and is tested locally with DuckDB; dialect differences are noted in `DECISIONS.md`.

## Use of AI
> ✏️ _Be upfront, e.g. "I used Claude to scaffold the repo and the data generator. The scoring logic, analysis and decisions are my own."_
