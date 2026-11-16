# Deviations from `analysis_plan.md` (Part B)

The plan covers this study (Part B) and study 06 (Part A); it was written and hashed once, before either was run.

1. **Path definition.** The plan defined converter paths by the conversion label, but in this file the label sits on
   clicked impressions only (0 of 10.5M unclicked impressions carry it), so that definition would drop converters'
   unclicked touches. Converter paths are all of the user's impressions up to the first conversion.
2. **Data-driven credit not used.** The decision rule was met (AUC 0.83 against 0.62), but the removal-effect credits
   are not reliable: removing a touch does not re-index the recency of the remaining touches, and negative effects are
   clipped. They are in `out/mta.json` (`cr_dd`) and are not used in any conclusion.
