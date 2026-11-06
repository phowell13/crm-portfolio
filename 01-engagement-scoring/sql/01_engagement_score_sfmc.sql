-- ===========================================================================
-- B2C email engagement score: Salesforce Marketing Cloud version
-- ===========================================================================
-- Same logic as 01_engagement_score.sql, in SFMC's SQL Server dialect.
-- Paste into a Query Activity in Automation Studio.
--
-- Target Data Extension (e.g. "Engagement_Score"), suggested fields:
--   SubscriberKey     Text(254)   Primary Key
--   Sends180          Number
--   Opens180          Number
--   UniqueClicks180   Number
--   OpenPoints        Decimal(18,2)
--   ClickPoints       Decimal(18,2)
--   EngagementScore   Decimal(18,2)
--   EngagementBand    Text(20)
-- Data action: Overwrite
--
-- Differences from the repo version:
--   date_diff('day', EventDate, as_of())  ->  DATEDIFF(day, EventDate, GETDATE())
--   No ORDER BY (SFMC ignores it when writing to a Data Extension)
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
    SELECT SubscriberKey, COUNT(*) AS Sends180
    FROM _Sent
    WHERE DATEDIFF(day, EventDate, GETDATE()) <= 180
    GROUP BY SubscriberKey
) s
LEFT JOIN (
    SELECT
        SubscriberKey,
        COUNT(*) AS Opens180,
        SUM(1 * CASE
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 30  THEN 1.0
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 90  THEN 0.6
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 180 THEN 0.3
                    ELSE 0
                END) AS OpenPoints
    FROM _Open
    WHERE DATEDIFF(day, EventDate, GETDATE()) <= 180
    GROUP BY SubscriberKey
) o ON o.SubscriberKey = s.SubscriberKey
LEFT JOIN (
    SELECT
        SubscriberKey,
        COUNT(*) AS UniqueClicks180,
        SUM(3 * CASE
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 30  THEN 1.0
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 90  THEN 0.6
                    WHEN DATEDIFF(day, EventDate, GETDATE()) <= 180 THEN 0.3
                    ELSE 0
                END) AS ClickPoints
    FROM _Click
    WHERE IsUnique = 1
      AND DATEDIFF(day, EventDate, GETDATE()) <= 180
    GROUP BY SubscriberKey
) c ON c.SubscriberKey = s.SubscriberKey
