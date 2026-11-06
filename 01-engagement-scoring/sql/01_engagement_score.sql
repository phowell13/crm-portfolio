-- ===========================================================================
-- B2C email engagement score
-- ===========================================================================
-- One row per subscriber who was sent at least one email in the last 180 days.
--
-- Rules (see DECISIONS.md):
--   Lookback       last 180 days only
--   Opens          every open counts, including repeat opens   = 1 point
--   Clicks         unique clicks only (one per email)          = 3 points
--   Recency        0-30 days x1.0 | 31-90 days x0.6 | 91-180 days x0.3
--   Bands          Highly engaged 10+ | Engaged 4.6+ | Lapsing 2+ | Dormant 0.75+ | Inactive <0.75
--
-- Written without CTEs (WITH ...) because SFMC Query Activities don't support
-- them, so the same shape works in SFMC. The SFMC version, with the T-SQL date
-- functions, is in 01_engagement_score_sfmc.sql.
--
-- Run: python scripts/run_sql.py sql/01_engagement_score.sql --out data/output/engagement_score.csv
-- ===========================================================================

SELECT
    s.SubscriberKey,
    s.Sends180,
    COALESCE(o.Opens180, 0)                                       AS Opens180,
    COALESCE(c.UniqueClicks180, 0)                                AS UniqueClicks180,
    ROUND(COALESCE(o.OpenPoints, 0), 2)                           AS OpenPoints,
    ROUND(COALESCE(c.ClickPoints, 0), 2)                          AS ClickPoints,
    ROUND(COALESCE(o.OpenPoints, 0) + COALESCE(c.ClickPoints, 0), 2) AS EngagementScore,
    -- Bands (see DECISIONS.md). CASE stops at the first match, top to bottom.
    CASE
        WHEN COALESCE(o.OpenPoints, 0) + COALESCE(c.ClickPoints, 0) >= 10   THEN 'Highly engaged'
        WHEN COALESCE(o.OpenPoints, 0) + COALESCE(c.ClickPoints, 0) >= 4.6  THEN 'Engaged'
        WHEN COALESCE(o.OpenPoints, 0) + COALESCE(c.ClickPoints, 0) >= 2    THEN 'Lapsing'
        WHEN COALESCE(o.OpenPoints, 0) + COALESCE(c.ClickPoints, 0) >= 0.75 THEN 'Dormant'
        ELSE 'Inactive'
    END AS EngagementBand

FROM (
    -- Step 1: everyone we emailed in the window. This is the base, so people
    -- who never opened or clicked still appear, with a score of 0.
    SELECT
        SubscriberKey,
        COUNT(*) AS Sends180
    FROM _Sent
    WHERE date_diff('day', EventDate, as_of()) <= 180
    GROUP BY SubscriberKey
) s

LEFT JOIN (
    -- Step 2: every open (repeat opens included), 1 point each x recency weight
    SELECT
        SubscriberKey,
        COUNT(*) AS Opens180,
        SUM(
            1 * CASE
                    WHEN date_diff('day', EventDate, as_of()) <= 30  THEN 1.0
                    WHEN date_diff('day', EventDate, as_of()) <= 90  THEN 0.6
                    WHEN date_diff('day', EventDate, as_of()) <= 180 THEN 0.3
                    ELSE 0
                END
        ) AS OpenPoints
    FROM _Open
    WHERE date_diff('day', EventDate, as_of()) <= 180
    GROUP BY SubscriberKey
) o ON o.SubscriberKey = s.SubscriberKey

LEFT JOIN (
    -- Step 3: unique clicks only (IsUnique = 1 is the first click on each email),
    -- 3 points each x recency weight
    SELECT
        SubscriberKey,
        COUNT(*) AS UniqueClicks180,
        SUM(
            3 * CASE
                    WHEN date_diff('day', EventDate, as_of()) <= 30  THEN 1.0
                    WHEN date_diff('day', EventDate, as_of()) <= 90  THEN 0.6
                    WHEN date_diff('day', EventDate, as_of()) <= 180 THEN 0.3
                    ELSE 0
                END
        ) AS ClickPoints
    FROM _Click
    WHERE IsUnique = 1
      AND date_diff('day', EventDate, as_of()) <= 180
    GROUP BY SubscriberKey
) c ON c.SubscriberKey = s.SubscriberKey


ORDER BY EngagementScore DESC
