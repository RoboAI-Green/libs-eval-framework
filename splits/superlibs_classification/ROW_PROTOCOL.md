# SuperLIBS classification protocol 3.0.0

## 1. Primary claim being tested

The study asks whether validation on randomly held-out spectra from physical samples already represented in training gives an over-optimistic basis for model selection compared with validation on genuinely unseen physical samples.

The controlled comparison is:

> same preprocessing fit + same fixed training rows + same candidate training trajectories + different validation view + same locked deployment test.

Validation strategy must never alter training rows, preprocessing, candidate configurations, repetitions, or checkpoint trajectories.

## 2. Random-shot validation

For every scientifically eligible training material and each permitted training-energy product/location block:

- the block must contain exactly 25 spectra;
- the two rows with the smallest `sha256(immutable_row_id|RANDOM_SHOT_VAL)` values are held out;
- the remaining 23 rows are training rows;
- the held-out rows cannot fit scaling, centring, PCA, calibration, or model parameters.

This is applied to every training block, not to a selected subset of materials.

### Branch A roles

- Training: `A_TRAIN_2P4`, `A_TRAIN_4P0`
- Random-shot validation: `A_SHOT_VAL_2P4`, `A_SHOT_VAL_4P0`
- Disjoint in-range validation: `A_V_IN_2P4`, `A_V_IN_4P0`
- Disjoint OOD validation: `A_V_OOD_2P4`, `A_V_OOD_4P0`
- Locked tests: `A_T_IN_*`, `A_T_OOD_*`

### Branch B roles

- Training: `B_TRAIN_2P4`, `B_TRAIN_4P0`
- Random-shot validation: `B_SHOT_VAL_2P4`, `B_SHOT_VAL_4P0`
- Interpolation validation/test: `B_I_V_*`, `B_I_T_*`
- Extrapolation validation/test: `B_X_V_*`, `B_X_T_*`

## 3. Fixed-training invariant

Each branch has exactly one ordered training-row list and one preprocessing fit.

- Branch A candidates all use the same Branch A training-row hash.
- Branch B candidates all use the same Branch B training-row hash.
- Branch B interpolation and extrapolation use the same Branch B model trajectories.
- Different validation views may select different configurations or checkpoints from those trajectories, but may not launch different training runs.

## 4. Non-pooled matched-energy selection

At 2.4 and 4.0 mJ, calculate split-group-weighted balanced accuracy separately by energy and take the equal mean. Do not pool spectra, predictions, or rows across energies before calculating the score.

The same rule applies to shot validation and family-disjoint validation.

## 5. Branch-specific isolation

Within each branch:

- training/preprocessing rows must not overlap any validation or locked-test row;
- training split groups may overlap shot validation by design;
- training split groups must not overlap split-group-disjoint validation or locked-test cohorts;
- locked rows cannot enter preprocessing, training, calibration, feature selection, checkpoint selection, or configuration selection.

Cross-branch reuse is permitted and audited. The branches are complementary experiments, not independent replications.

## 6. Branch B energy populations

Interpolation uses one same-material population at 2.4, 3.2, and 4.0 mJ.

Extrapolation uses a different same-material population at 2.4, 4.0, 5.6, and 7.2 mJ.

Material and split-group identities must be equal across energies within each subbranch. The 3.2, 5.6, and 7.2 mJ results must not be presented as one continuous same-population five-energy curve.

## 7. Metrics and uncertainty

The primary prediction unit is split-group-weighted material level.

- Balanced accuracy: equal mean of split-group-weighted class recalls.
- Macro-F1: equal mean of class F1 values from the split-group-weighted confusion matrix.
- Brier: summed multiclass error within each row, weighted within true class, then averaged equally across true classes.
- NLL: weighted within true class, then averaged equally across true classes; clip epsilon is `1e-12`.

Bootstrap resampling uses `split_group_id`. Repeated draws preserve multiplicity; each sampled copy has total material weight one.

## 8. Release gate

The row stage performs two complete independent generations and requires byte-identical output files. The release gate then derives `spectral_training_allowed` from package hashes, row-output hashes, tests, that deterministic regeneration, shot-holdout integrity, row and preprocessing isolation, Branch B common-identity checks, cross-branch audit reproduction, and balanced-replication construction.

A hard-coded pass flag is prohibited.
