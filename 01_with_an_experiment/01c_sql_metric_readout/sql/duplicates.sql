-- C7: rows identical to at least one other row in all 16 columns.
SELECT COALESCE(SUM(k), 0) AS c7_rows_identical_to_another
FROM (
    SELECT COUNT(*) AS k
    FROM users
    GROUP BY f0, f1, f2, f3, f4, f5, f6, f7, f8, f9, f10, f11, treatment, exposure, visit, conversion
    HAVING COUNT(*) > 1
) AS g;
