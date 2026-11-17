# Pre-analysis plan: hierarchical forecasts of Zillow metro listing counts

Written 2026-11-09, before any forecast was scored. Its SHA-256 is stored in `docs/pre_analysis_plan.sha256`;
`scripts/run_backtest.py` refuses to run if this file no longer matches that hash. Any change after the hash is a
deviation and is listed in `reports/memo.md` §Deviations, not edited in here.

**What had been looked at before writing this plan** (data structure only, no forecast errors):
- completeness counts of the three additive Zillow metro count files (inventory, new listings, newly pending) and
  the share of the "United States" row covered by complete metros (inventory 84–90 %, new listings 91–96 %);
- fit times of AutoETS and AutoARIMA on one origin (6 s and 18 s for 809 series on 8 cores); no accuracy computed;
- a numerical check, on random numbers, that the shrinkage formula in §5 matches `hierarchicalforecast` 1.5.3.

## 1. Question

For monthly **for-sale inventory** (count of active listings), arranged as
United States → Census division → state → metro, do reconciled forecasts (bottom-up, top-down, OLS, WLS-structural,
MinT-shrink) beat the unreconciled base forecasts and a no-change forecast at horizons 1–12 months, and at which
levels? Which reconciliation method is best at each level?

## 2. Data

- Zillow Research public metro files, hand-downloaded 2026-11-09 (folder `v1_20261109`, read in place from
  `metro_market_ssm/data_external/zillow/`, never copied):
  - primary target: `Metro_invt_fs_uc_sfrcondo_month.csv` (for-sale inventory, all homes, raw monthly);
  - robustness target R2: `Metro_new_listings_uc_sfrcondo_month.csv`.
  - Newly pending is **not** used: only 388 metros are complete in the training window (too little coverage).
- Rows used: `RegionType == "msa"` (927 Zillow metros, which include micropolitan areas) and the
  `"country"` row (United States).
- Window: 2018-03 to 2026-09. 2018-01 and 2018-02 are dropped as partial months (same rule as `metro_market_ssm`).
- Census 2023 CBSA list (`list1_2023.xlsx`): used only for a descriptive crosswalk (CBSA code, metro/micro status,
  and a check that the Zillow name's state equals the CBSA title's first-listed state). The hierarchy itself uses the
  state suffix of the Zillow metro name ("Dallas, TX" → TX), which is the CBSA's principal state.

## 3. Panel and hierarchy

- **Members**: metros with no missing target value in 2018-03 to 2023-10, i.e. everything known at the first
  as-of month (§4). Membership is fixed for all origins.
- Later gaps in a member series are filled by carrying the last observed value forward (uses only past values).
  The number of filled cells is reported.
- **Remainder** leaf: `R_t = US_t − Σ_members y_t` (non-metro areas plus metros that are not members). It appears as
  a pass-through node at the division, state and metro levels, so every level sums exactly to the US row. If any
  `R_t ≤ 0`, the run stops and this is reported.
- Levels: L0 United States (1 node); L1 nine Census divisions + Remainder; L2 states (50 + DC) + Remainder;
  L3 member metros + Remainder. Standard Census divisions:
  New England (CT ME MA NH RI VT); Middle Atlantic (NJ NY PA); East North Central (IL IN MI OH WI);
  West North Central (IA KS MN MO NE ND SD); South Atlantic (DE DC FL GA MD NC SC VA WV);
  East South Central (AL KY MS TN); West South Central (AR LA OK TX); Mountain (AZ CO ID MT NV NM UT WY);
  Pacific (AK CA HI OR WA).
- Coverage breaks: the level-shift/spike rule copied from `metro_market_ssm` (`clean_coverage`) is run on the
  members' training window as of the first origin, **for reporting only**. Nothing is masked, because masking would
  break additivity.

## 4. Pseudo-real-time design

- A value for month t is treated as known from month t + 1 (`known_month = valid_month + 1`; Zillow publishes a
  month's metro data in the middle of the next month).
- Only one vintage exists (downloaded 2026-11-09). Later revisions of listing counts are therefore in the data
  this study uses; this is pseudo-real-time (as-of masking on a late vintage), not real-time.
- **Origins**: as-of months a = 2023-11, 2023-12, …, 2025-10 (24 origins). At as-of month a the training set is
  every value with `known_month ≤ a`, i.e. valid months 2018-03 to a − 1 (expanding window). Targets are valid months
  a − 1 + h for h = 1..12. Every origin has all 12 horizons observed (last target 2026-09).
- Everything that uses data (model fits, the Remainder, top-down proportions, the MinT covariance, the RMSSE scale)
  is computed from that origin's training set only.

## 5. Methods

- **Base forecasts (primary)**: `statsforecast` 2.1.1 `AutoETS(season_length=12)`, default model search, fitted
  separately to every node in levels. In-sample one-step fitted values give the residuals for MinT.
- **Base forecasts (robustness R1)**: `AutoARIMA(season_length=12)`, same everything else.
- **Baselines**: no-change (ŷ_{a−1+h} = y_{a−1}) and seasonal naive (ŷ_{a−1+h} = y_{a−1+h−12}). Both are linear in
  the data, so they are coherent by construction.
- **Reconciliation**: all are linear, ỹ = S G ŷ, with S the summing matrix (rows = all nodes, columns = leaves).
  - Bottom-up (BU): G = [0 | I] (keep the leaves' base forecasts).
  - Top-down (TD): proportions of historical averages over the last 12 training months,
    p_j = Σ y_j / Σ y_US; leaf forecast = p_j × US base forecast.
  - OLS: G = (S′S)⁻¹S′.
  - WLS-structural: W = diag(S 1) (number of leaves under each node), G = (S′W⁻¹S)⁻¹S′W⁻¹.
  - MinT-shrink: same G with W = Schäfer–Strimmer shrinkage of the in-sample one-step residual covariance toward
    its diagonal (residuals centred, T − 1 denominators, λ = Σ_{i≠j} Var(r_ij) / Σ_{i≠j} r_ij², clipped to [0, 1]).
- Own numpy implementation; a test checks G against `hierarchicalforecast` 1.5.3 `MinTrace` on a small hierarchy.
- No non-negativity constraint. The share of negative reconciled forecasts is reported.

## 6. Metrics

- Error e = y − ŷ, in listings.
- **MAE** by level: mean |e| over the level's nodes (Remainder excluded at L1–L3), origins and horizons.
- **RMSSE** for node i at origin o over a horizon set H: sqrt(mean_{h∈H} e² / s²), where s² is the mean squared
  one-step change (y_t − y_{t−1})² over that origin's training window (M5 convention). A level's RMSSE is the mean
  over its nodes and the 24 origins. Reported for H = {1..12} (headline) and for each single h.
- **Relative RMSSE** = method RMSSE / no-change RMSSE at the same level and H.
- **Coherence**: for every aggregate node, |ŷ_parent − Σ ŷ_children| / y_parent; mean and max by level and method.
  Reconciled forecasts should be below 1e-8; base forecasts are not expected to be.
- Headline table: level × method with RMSSE (h = 1..12), relative RMSSE, MAE and coherence error.

## 7. Primary comparisons (fixed now)

- P1: MinT-shrink vs base ETS, level RMSSE (h = 1..12), at each of L0–L3.
- P2: MinT-shrink vs bottom-up at each level.
- P3: the best method at each level vs no-change.
- Inference: for each comparison, level and h ∈ {1, 12}, the per-origin loss differential d_o = mean over the
  level's nodes of (e²/s²)_A − (e²/s²)_B; Diebold–Mariano test with the Harvey–Leybourne–Newbold correction,
  Newey–West lag h − 1, 24 origins, two-sided. Also the number of origins (of 24) where A has the lower loss.
  With 24 overlapping origins over two years these tests are descriptive.
- Wording rule: "reconciliation helps at level L" only if MinT-shrink's level RMSSE is below base **and** the DM
  p-value is below 0.05 at h = 1 or h = 12. Otherwise: "no clear difference" (or "worse").

## 8. Robustness (pre-specified, all reported)

- R1: AutoARIMA base forecasts (inventory).
- R2: new listings as target (AutoETS base, same rules, its own member set by the §3 rule).

## 9. What will not happen

- No method, level, origin or metric is added or dropped after seeing results unless listed as a deviation.
- All methods are reported at all levels, including those that lose to no-change.

## 10. Limits known in advance

- One vintage; revisions are not modelled.
- The Remainder mixes non-metro areas with non-member metros, and its forecast quality is reported separately.
- Listing counts depend on Zillow's listing coverage, which changes over time.
- 24 origins from one two-year period (2023-11 to 2025-10): one market regime.
- Counts only. Prices (ZHVI) do not add up, so a price hierarchy would need weights and is not attempted.
- Point forecasts only; no probabilistic reconciliation.

## 11. Outputs

- Per-origin forecasts are derived from Zillow data: they stay in `tmp/` and are not committed.
- Only aggregate metric tables go to `reports/tables/`. Every chart carries "Data Provided by Zillow Group".
