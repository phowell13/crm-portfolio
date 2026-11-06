-- Smoke test: checks the data loaded correctly.
-- Sends, unique opens and unique clicks per email, with open and click rates.
-- Run: python scripts/run_sql.py sql/00_smoke_test.sql

SELECT
    j.JobID,
    j.EmailName,
    CAST(j.DeliveredTime AS DATE)                                   AS SendDate,
    COUNT(DISTINCT s.SubscriberKey)                                 AS Sent,
    COUNT(DISTINCT o.SubscriberKey)                                 AS UniqueOpens,
    COUNT(DISTINCT c.SubscriberKey)                                 AS UniqueClicks,
    ROUND(100.0 * COUNT(DISTINCT o.SubscriberKey) / COUNT(DISTINCT s.SubscriberKey), 1) AS OpenRatePct,
    ROUND(100.0 * COUNT(DISTINCT c.SubscriberKey) / COUNT(DISTINCT s.SubscriberKey), 1) AS ClickRatePct
FROM _Job j
JOIN _Sent s       ON s.JobID = j.JobID
LEFT JOIN _Open o  ON o.JobID = s.JobID AND o.SubscriberKey = s.SubscriberKey
LEFT JOIN _Click c ON c.JobID = s.JobID AND c.SubscriberKey = s.SubscriberKey
GROUP BY j.JobID, j.EmailName, j.DeliveredTime
ORDER BY j.DeliveredTime DESC
