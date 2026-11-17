-- One row per assignment arm (0 = control, 1 = ad arm). Denominator of every rate: all users assigned to the arm.
SELECT
    treatment                              AS arm,
    COUNT(*)                               AS users,
    SUM(exposure)                          AS exposed_users,
    SUM(visit)                             AS visits,
    SUM(conversion)                        AS conversions,
    SUM(visit * exposure)                  AS visits_of_exposed_users,
    SUM(conversion * exposure)             AS conversions_of_exposed_users,
    CAST(SUM(exposure) AS DOUBLE) / COUNT(*)   AS exposure_rate,
    CAST(SUM(visit) AS DOUBLE) / COUNT(*)      AS visit_rate,
    CAST(SUM(conversion) AS DOUBLE) / COUNT(*) AS conversion_rate
FROM users
GROUP BY treatment
ORDER BY treatment;
