# Decision log

Every meaningful choice, why you made it, and what you considered instead.
Keep entries short. Add a new one whenever you change your mind; the history is part of the point.

---

## Template

### [Date] Decision title
**Decision:** what you chose
**Why:** the reasoning
**Alternatives considered:** what else you could have done, and why not
**How I'd check it:** what would tell you it was wrong

---

### 2026-11-06 Lookback window: 180 days
**Decision:** Score activity from the last 180 days, with recent activity weighted more heavily.
**Why:** SFMC data views (_Sent, _Open, _Click) keep about 6 months of history, so a 180-day window works straight from live SFMC data. It doesn't depend on a business having its own data warehouse or backed-up history. In the test data, 81% of subscribers opened in the last 90 days and 96% in the last 12 months, so a long window would make almost everyone look engaged. Weighting recent activity more means the score still picks up people who are drifting away, even inside a 6-month window.
**Alternatives considered:**
- 90 days: sharper, but too harsh on someone who goes quiet for a few weeks.
- 12 months: needs history stored outside SFMC, and barely separates customers.
- 180 days with no recency weighting: simpler, but an open 5 months ago would count the same as one yesterday.
**How I'd check it:** Compare scores against later behaviour (orders, campaign response). If lapsing customers still score highly, the recency weighting isn't strong enough.

### 2026-11-06 Click vs open weighting: click = 3, open = 1
**Decision:** Each click scores 3 points and each open scores 1.
**Why:** A click shows real intent: the customer acted on the content rather than just viewing it. Opens are also less reliable since Apple Mail Privacy Protection, which can register opens automatically. In the test data there are about 4 opens for every click, so clicks are rarer and more meaningful.
**Alternatives considered:**
- 1:4, weighting by rarity: defensible, but 1:3 is simpler to explain to stakeholders and close to the data.
- Clicks only: most resistant to Apple's privacy feature, but it would score most of the base as unengaged.
**How I'd check it:** Test whether clickers convert or order at a clearly higher rate than openers. If they don't, the weighting is too high.

### 2026-11-06 Count every open, but unique clicks only
**Decision:** Every individual open scores 1 point, including repeat opens of the same email. Clicks are counted once per email (unique clicks).
**Why:** Counting unique opens only would undervalue highly engaged readers. For example, someone who opened one email once and clicked would score 4, while someone who opened the same email 16 times would score just 1. Repeat opens show genuine ongoing interest. Clicks stay unique so one email can't be clicked repeatedly to inflate a score.
**Alternatives considered:**
- Unique opens only: cleaner and harder to inflate, but it undervalues the most engaged readers.
- All clicks: double-counts people clicking several links in one email.
**How I'd check it:** Repeat opens can come from forwarding, security scanners or Apple's privacy feature rather than the person. Check the distribution of opens per email per subscriber. If a small group has extreme counts (e.g. 20+ opens of one email), cap opens per email (e.g. max 5) and record that as a new decision.


### 2026-11-06 Recency weighting: time buckets
**Decision:** Weight activity by how recent it is, using three time buckets:
- 0–30 days: ×1.0 (full value)
- 31–90 days: ×0.6
- 91–180 days: ×0.3

**Why:** Buckets are easy to explain to marketers and stakeholders ("recent activity counts most, older activity counts less") and simple to build in an SFMC Query Activity with a CASE statement. The weights are a starting point, to be tuned against results.
**Alternatives considered:**
- Smooth decay (activity loses half its value every 45 days): more precise, with no sudden drop when activity moves from one bucket to the next. It's harder to explain, though. If stakeholders were comfortable with the idea of a "half-life", decay would be a good upgrade, and it could be tested side by side against the buckets.
- No weighting: an open 5 months ago would count the same as one yesterday (rejected in the lookback decision).
**How I'd check it:** Look at customers just either side of a bucket boundary (e.g. last active 29 vs 31 days ago). If their scores jump sharply for no real difference in behaviour, adjust the weights or move to smooth decay.

### 2026-11-06 Engagement bands: five fixed-score bands
**Decision:** Group subscribers into five bands using fixed score thresholds:

| Band | Score | Share of base | Journey action | Print? |
|---|---|---|---|---|
| Highly engaged | 10+ | 25% | Email only | Never |
| Engaged | 4.6–9.9 | 25% | Normal programme | Never |
| Lapsing | 2–4.5 | 20% | Re-engagement journey | Allowed |
| Dormant | 0.75–1.9 | 13% | Light-touch re-engagement email | Allowed |
| Inactive | below 0.75 | 17% | Print or SMS win-back, or suppress from email | Allowed |

**Why:** Fixed scores keep a steady definition of "engaged" over time, so band changes reflect real changes in behaviour rather than a moving bar. The top two thresholds sit at the top quartile (10) and the median (4.6) of the first run, so the bands start at sensible sizes. The bottom of the base is split into Dormant and Inactive so people with some recent activity aren't written off. An open-cap of 0.75 means Inactive holds people with no activity, or only one or two old opens, which may be automatic opens from Apple Mail Privacy Protection rather than real engagement.
**Alternatives considered:**
- Percentage bands (e.g. top 25%): always even groups, but the bar moves as the base becomes more or less engaged.
- Four bands with Dormant starting at 0.1: Lapsing held 40% of the base, too broad to act on.
- Four bands with Dormant starting at 2: Dormant tripled to 30%, including 533 people still showing some activity.
**How I'd check it:** Compare conversion and orders by band. Each band should perform clearly better than the one below. Review band sizes monthly; if a band grows or shrinks sharply, check whether behaviour changed or the thresholds need revisiting.
