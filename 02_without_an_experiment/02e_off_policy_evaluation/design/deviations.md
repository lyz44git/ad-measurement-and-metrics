# Deviations from the analysis plan

1. **Nuisance models use 300 trees, not 100.** Found on simulated data in `tests/test_ope.py`, before any log was
   drawn from the Criteo file. With 100 trees at learning rate 0.05 the propensity model was compressed toward 0.5:
   where the true logging propensity was 0.03 it predicted 0.11, and where it was 0.97 it predicted 0.89. IPS with the
   estimated propensity then gave a lift of 0.057 against a true 0.031, and DR 0.037. With 300 trees the predicted
   propensities matched the true ones within 0.01 in every band and IPS gave 0.028. All other settings are as planned.
   300 trees is also the setting of the value models in study 02d.
