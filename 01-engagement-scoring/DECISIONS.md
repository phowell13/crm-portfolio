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
