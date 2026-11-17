-- One row per outcome with every metric of the plan: the effect of assignment (primary readout) and the
-- attribution diagnostics.
WITH arm AS (
    SELECT treatment,
           CAST(COUNT(*) AS DOUBLE)                   AS n,
           CAST(SUM(exposure) AS DOUBLE)              AS exposed,
           CAST(SUM(visit) AS DOUBLE)                 AS visit,
           CAST(SUM(conversion) AS DOUBLE)            AS conversion,
           CAST(SUM(visit * exposure) AS DOUBLE)      AS visit_exposed,
           CAST(SUM(conversion * exposure) AS DOUBLE) AS conversion_exposed
    FROM users
    GROUP BY treatment
),
long AS (
    SELECT 'visit' AS outcome, treatment, n, exposed, visit AS y, visit_exposed AS y_exposed FROM arm
    UNION ALL
    SELECT 'conversion' AS outcome, treatment, n, exposed, conversion AS y, conversion_exposed AS y_exposed FROM arm
),
wide AS (
    SELECT outcome,
           MAX(CASE WHEN treatment = 0 THEN n END)         AS n0,
           MAX(CASE WHEN treatment = 1 THEN n END)         AS n1,
           MAX(CASE WHEN treatment = 1 THEN exposed END)   AS exposed1,
           MAX(CASE WHEN treatment = 0 THEN y END)         AS y0,
           MAX(CASE WHEN treatment = 1 THEN y END)         AS y1,
           MAX(CASE WHEN treatment = 1 THEN y_exposed END) AS credited
    FROM long
    GROUP BY outcome
),
rates AS (
    SELECT *, y0 / n0 AS p0, y1 / n1 AS p1 FROM wide
)
SELECT
    outcome,
    n0                                              AS users_control,
    n1                                              AS users_ad_arm,
    y0                                              AS outcomes_control,
    y1                                              AS outcomes_ad_arm,
    p0                                              AS control_rate,
    p1                                              AS ad_arm_rate,
    p1 - p0                                         AS effect_of_assignment,
    SQRT(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)   AS standard_error,
    (p1 - p0) * n1                                  AS outcomes_caused,
    credited                                        AS outcomes_credited,
    credited / ((p1 - p0) * n1)                     AS credited_over_caused,
    exposed1 / n1                                   AS exposure_rate,
    (p1 - p0) / (exposed1 / n1)                     AS effect_per_exposed_user
FROM rates
ORDER BY outcome DESC;
