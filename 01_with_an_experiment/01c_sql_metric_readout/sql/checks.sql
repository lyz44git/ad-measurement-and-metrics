-- Data checks on `users` (one row per user). One row of counts; see design/analysis_plan.md.
SELECT
    COUNT(*) AS c1_rows,
    SUM(CASE WHEN f0 IS NULL OR f1 IS NULL OR f2 IS NULL OR f3 IS NULL OR f4 IS NULL OR f5 IS NULL
               OR f6 IS NULL OR f7 IS NULL OR f8 IS NULL OR f9 IS NULL OR f10 IS NULL OR f11 IS NULL
               OR treatment IS NULL OR exposure IS NULL OR visit IS NULL OR conversion IS NULL
             THEN 1 ELSE 0 END) AS c2_rows_with_null,
    SUM(CASE WHEN treatment NOT IN (0, 1) OR exposure NOT IN (0, 1)
               OR visit NOT IN (0, 1) OR conversion NOT IN (0, 1)
             THEN 1 ELSE 0 END) AS c3_rows_with_non_binary_flag,
    SUM(CASE WHEN treatment = 0 AND exposure = 1 THEN 1 ELSE 0 END) AS c4_exposed_in_control,
    SUM(CASE WHEN conversion = 1 AND visit = 0 THEN 1 ELSE 0 END) AS c5_conversion_without_visit,
    SUM(CASE WHEN exposure = 1 AND visit = 0 THEN 1 ELSE 0 END) AS c6_exposed_without_visit
FROM users;
