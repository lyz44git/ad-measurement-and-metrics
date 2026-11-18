# Deviations from `analysis_plan.md` (Part B)

The plan covers this study (Part B) and study 02c (Part A); it was written and hashed once, before either was run.

1. **Path definition.** The plan defined converter paths by the conversion label, but in this file the label sits on
   clicked impressions only (0 of 10.5M unclicked impressions carry it), so that definition would drop converters'
   unclicked touches. Converter paths are all of the user's impressions up to the first conversion.
2. **Data-driven credit not used.** The decision rule was met (AUC 0.83 against 0.62), but the removal-effect credits
   are not reliable: removing a touch does not re-index the recency of the remaining touches, and negative effects are
   clipped. They are in `out/mta.json` (`cr_dd`) and are not used in any conclusion.
3. **A data profile quoted in the plan.** The plan says 32.3% of conversions have more than one touch and 0.7% touch
   more than one campaign. Both figures come from the raw file's conversion label, which sits on clicked impressions
   only (item 1), so they understate path length and campaign spread. On the rebuilt paths, 65% of converting paths
   have more than one touch ([`out/mta.json`](../out/mta.json)) and 29% touch two or more campaigns; among the 64,159
   multi-touch test conversions the share is 44.7% ([`out/campaign_span.json`](../out/campaign_span.json)). No test
   is affected; the statement that this is attribution within one display network, not across channels, still holds.
