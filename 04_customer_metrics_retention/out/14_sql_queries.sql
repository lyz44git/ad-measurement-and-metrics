-- inv/days tables: see 14_ltv_extension.py
-- Rule segments at 2011-06-01

WITH rfm AS (
  SELECT cid, COUNT(*) AS n6, SUM(rev) AS gross6, date_diff('day', MAX(day), DATE '2011-06-01') AS recency_d
  FROM days WHERE day >= DATE '2010-12-01' AND day < DATE '2011-06-01' GROUP BY cid),
fut AS (SELECT cid, SUM(rev) AS y FROM days WHERE day >= DATE '2011-06-01' AND day < DATE '2011-12-01' GROUP BY cid),
ranked AS (
  SELECT r.*, COALESCE(f.y, 0) AS y,
         CASE WHEN recency_d <= 60 THEN 'recent<=60d' WHEN recency_d <= 120 THEN '61-120d' ELSE '>120d' END AS rband,
         -- value terciles by rank; boundary accounts go to the upper tercile (same convention as pandas qcut on ranks,
         -- which gives 905/905/906 here; NTILE(3) gives 906/905/905 and moved 3 boundary accounts in the first run)
         CASE WHEN ROW_NUMBER() OVER (ORDER BY gross6, cid) < 1 + (COUNT(*) OVER () - 1) / 3.0 THEN 1
              WHEN ROW_NUMBER() OVER (ORDER BY gross6, cid) < 1 + 2 * (COUNT(*) OVER () - 1) / 3.0 THEN 2 ELSE 3 END AS vtile
  FROM rfm r LEFT JOIN fut f USING (cid))
SELECT rband, vtile, COUNT(*) AS n, SUM(y) AS y_sum, AVG(CASE WHEN y > 0 THEN 1.0 ELSE 0.0 END) AS repeat_rate,
       COUNT(*) * 1.0 / SUM(COUNT(*)) OVER () AS share_accounts, SUM(y) / SUM(SUM(y)) OVER () AS share_sales
FROM ranked GROUP BY 1, 2 ORDER BY share_sales DESC

-- New-account cohorts

WITH m AS (SELECT DISTINCT cid, date_trunc('month', day) AS mon FROM days),
cand AS (
  SELECT a.cid, a.mon FROM m a
  WHERE a.mon BETWEEN DATE '2010-12-01' AND DATE '2011-06-01'
    AND NOT EXISTS (SELECT 1 FROM days d WHERE d.cid = a.cid AND d.day < a.mon AND d.day >= a.mon - INTERVAL 12 MONTH)),
firsts AS (SELECT cid, MIN(mon) AS cm FROM cand GROUP BY cid),
sizes AS (SELECT cm, COUNT(*) AS n FROM firsts GROUP BY cm),
act AS (SELECT f.cm, date_diff('month', f.cm, m.mon) AS k, COUNT(DISTINCT m.cid) AS buyers
        FROM firsts f JOIN m USING (cid) WHERE m.mon > f.cm AND m.mon <= DATE '2011-11-01' GROUP BY 1, 2)
SELECT strftime(a.cm, '%Y-%m') AS cm, a.k, a.buyers * 1.0 / s.n AS repeat_rate, s.n FROM act a JOIN sizes s USING (cm) ORDER BY 1, 2
