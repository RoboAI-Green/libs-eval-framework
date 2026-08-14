# Evaluation-dependent performance claims in machine-learning LIBS

This repository accompanies the manuscript *Evaluation-Dependent Performance Claims in Machine-Learning LIBS: A Framework for Classification, Quantification, and Out-of-Distribution Evaluation* by Toni Aaltonen and Pekka Suominen.

It provides a reporting framework and the released split artifacts for three LIBS case studies:

1. EMSLIBS 2019 soil classification;
2. NASA SuperLIBS quantification; and
3. NASA SuperLIBS lithology classification.

The repository contains split memberships and supporting metadata, not raw spectra, trained models, checkpoints, predictions, or the complete experiment code.

## Why the framework is needed

A performance value is meaningful only for the population and evaluation process that produced it. Randomly held-out spectra from a represented target, spectra from a new physical target, and spectra from a new material family may use the same metric while supporting different claims.

LIBS spectra are hierarchical and acquisition-dependent. Spectra can be nested within locations, physical targets, preparation batches, provenance families, sessions, instruments, and operating conditions. Many spectra therefore do not necessarily represent many independent physical units.

The framework reports two complementary descriptions:

- an **Evaluation Code** for physical independence, instrument/session separation, and evaluation access; and
- a **Domain-Shift Matrix (DSM)** for the specific chemical and acquisition relations between development and evaluation data.

These components are not a scalar quality score or universal difficulty ranking.

## Evaluation Code

Assign the three axes independently to selection validation and final evaluation. If the evidence needed for an axis was not reported, leave it unassigned and disclose the missing information; there is no unknown or `U` code.

### Physical specimen independence (`Ind`)

| Code | Evaluation boundary |
|---|---|
| `Ind-0` | Evaluation spectra come from physical targets represented during fitting. |
| `Ind-1` | Physical targets are disjoint, but a documented parent material, preparation batch, or provenance family may occur on both sides. |
| `Ind-2` | Physical targets and preparation batches are disjoint, but a broader documented provenance family may occur on both sides. |
| `Ind-3` | Physical targets, preparation batches, and prespecified physical-provenance families are disjoint. |

`Ind` describes physical provenance, not chemical or spectral distance. Chemistry relations belong in the DSM.

### Instrumental and temporal separation (`Inst`)

| Code | Evaluation boundary |
|---|---|
| `Inst-0` | Same physical instrument and measurement session or continuous time window. |
| `Inst-1` | Same physical instrument, but a meaningfully different session or time. |
| `Inst-2` | Different physical device with the same or closely similar architecture. |
| `Inst-3` | Different main hardware components, such as laser wavelength or spectrometer/detector architecture. |

### Evaluation access and custody (`Epi`)

| Code | Evaluation boundary |
|---|---|
| `Epi-0` | Internally managed evaluation queried interactively during development. |
| `Epi-1` | Evaluation withheld from optimization but queried internally to select among candidate pipelines. |
| `Epi-2` | Labels held by an independent third party, with multiple submissions permitted. |
| `Epi-3` | Internal evaluation frozen and sequestered before modeling, then queried once after the pipeline is locked. |
| `Epi-4` | Labels held by an independent third party, with exactly one submission permitted before release. |

Report the observed number of final-test queries or submissions.

## Domain-Shift Matrix

Report every applicable factor separately.

| Factor | Required description |
|---|---|
| `R_matrix` | Prespecified matrix or composition relation based primarily on reference chemistry. Keep chemistry groups distinct from physical-provenance families. |
| `Δconc` | Per-analyte interpolation, edge coverage, low-end extrapolation, and high-end extrapolation, including ranges and outside-range counts. |
| `Δopt` | Each varied excitation parameter separately, such as energy, fluence, wavelength, pulse duration, repetition rate, and focus. |
| `Δdet` | Gate delay and gate width in development, selection validation, and final evaluation, including whether either differs. |
| `Δsnr` | Development and evaluation signal-quality distributions, with a defined SNR calculation and statistical unit. |

Do not combine DSM entries into one distance or infer the cause of an error when several shifts co-occur. Other scientifically relevant metadata should still be reported in Methods even when it is not a taxonomy factor.

## Applying the framework

1. State the intended task, deployment population, metric, prediction unit, and operational use.
2. Map the hierarchy of spectra, locations, targets, batches, provenance families, sessions, and devices.
3. Design selection validation separately from final evaluation.
4. Assign `Ind`, `Inst`, and `Epi` independently to both stages.
5. Complete the DSM using physically meaningful quantities and independent statistical units.
6. Fit every learned transformation using training data only, unless a prespecified post-selection refit is explicitly disclosed.
7. Report the metric, aggregation rule, uncertainty unit, independent-unit count, query count, split version, and a bounded scope statement.

The files in [`templates/`](templates/) provide machine-readable starting points for a claim report, DSM, and generic row-level split manifest.

## Repository map

| Path | Purpose |
|---|---|
| `splits/emslibs2019/` | Three fixed EMSLIBS development-set allocations. |
| `splits/superlibs_quantification/` | Row indices and material metadata for the quantification validation and test cohorts. |
| `splits/superlibs_classification/` | Branch A and B row manifests, role summaries, preprocessing locks, and the frozen allocation/row protocols. |
| `templates/` | Framework reporting templates. |
| `scripts/verify_repository.py` | Checks file hashes and the internal structure of the released manifests. |
| `SHA256SUMS.txt` | SHA-256 values for the immutable split, protocol, and template artifacts. |
| `CITATION.cff` | Currently available citation metadata. |

## EMSLIBS 2019 classification splits

The EMSLIBS files describe fixed allocations of 10,000 development spectra from 100 physical samples, with 100 spectra per sample.

| Files | Meaning |
|---|---|
| `random20.npz`, `random20.json` | 8,000 training and 2,000 validation spectra; all 100 physical samples occur on both sides. |
| `group20.npz`, `group20.json` | 8,100 training and 1,900 validation spectra; 81 and 19 physical samples, with no sample overlap. |
| `combined20.npz`, `combined20.json` | 8,100 training and 1,900 validation spectra; a fixed sample-disjoint hard allocation used in the study. |

Each NPZ contains two zero-based integer arrays, `train` and `val`. Its JSON companion records counts, class coverage, sample overlap, and construction metadata.

```python
import json
import numpy as np

split = np.load("splits/emslibs2019/group20.npz", allow_pickle=False)
meta = json.load(open("splits/emslibs2019/group20.json"))
train_rows = split["train"]
validation_rows = split["val"]
```

The public EMSLIBS external benchmark is not included. These files reproduce the internal development allocations used in the case study.

## NASA SuperLIBS quantification splits

| File | Purpose |
|---|---|
| `scientific_manifest_rows.npz` | Authoritative HDF5 row indices for all 38 training, reserved-refit, validation, locked-test, and stress row sets. |
| `scientific_manifest.json` | Manifest version, source fingerprints, split parameters, cohort membership, chemistry policy, and row-set definitions. |
| `material_assignments.csv` | Material identifiers, family relations, composition statistics, exclusions, and assigned cohorts. |
| `row_set_statistics.csv` | Spectrum, material, product, and energy counts for every row set. |

Load a named row set as follows:

```python
import numpy as np

rows = np.load(
    "splits/superlibs_quantification/scientific_manifest_rows.npz",
    allow_pickle=False,
)
selection_train = rows["selection_train"]
validation_v1 = rows["val_v1_in_random"]
test_ood_4p0 = rows["test_ood_4p0"]
```

Every key in the following tables is a top-level array in `scientific_manifest_rows.npz`. Counts are copied from `row_set_statistics.csv`; rows are spectra in the source HDF5. The exact material membership and construction policy remain in `material_assignments.csv` and `scientific_manifest.json`.

### Quantification training, reserved-refit, and selection-validation row sets

| NPZ key | Use | Energy (mJ) | Rows | Materials | Products | Evaluation Code |
|---|---|---:|---:|---:|---:|---|
| `selection_train` | Training population used during model and pipeline selection. | 2.4, 4.0 | 469,500 | 1,934 | 19,150 | — |
| `final_train` | Reserved for an optional post-selection refit; not used to produce the results reported in the article. | 2.4, 4.0 | 527,050 | 2,139 | 21,250 | — |
| `val_v0_shot_random` | Represented-target held-out shots, selected randomly. | 2.4, 4.0 | 5,050 | 100 | 1,010 | `Ind-0/Epi-1` |
| `val_v1_in_random` | Target- and family-disjoint, composition-in-range validation with random shots. | 2.4, 4.0 | 5,125 | 100 | 1,025 | `Ind-3/Epi-1` |
| `val_v2_ood_random` | Target- and family-disjoint, composition-OOD validation with random shots. | 2.4, 4.0 | 5,150 | 100 | 1,030 | `Ind-3/Epi-1` |
| `val_v3_in_boundary` | The V1 targets and products with intensity-boundary shots. | 2.4, 4.0 | 5,125 | 100 | 1,025 | `Ind-3/Epi-1` |
| `val_v4_ood_boundary` | The V2 targets and products with intensity-boundary shots. | 2.4, 4.0 | 5,150 | 100 | 1,030 | `Ind-3/Epi-1` |

The V0–V4 arrays are alternative selection-validation views, not five folds of one cross-validation partition. `selection_train` is the only training population used to produce the results reported in the article. `final_train` is retained as a reserved optional-refit population and was not used.

### Quantification locked-test row sets

| NPZ key | Evaluation population | Energy (mJ) | Rows | Materials | Products | Evaluation Code |
|---|---|---:|---:|---:|---:|---|
| `test_shot_2p4` | Represented targets; held-out random shots. | 2.4 | 2,100 | 100 | 420 | `Ind-0/Epi-3` |
| `test_shot_4p0` | Represented targets; held-out random shots. | 4.0 | 2,100 | 100 | 420 | `Ind-0/Epi-3` |
| `test_location_2p4` | Represented targets; held-out locations. | 2.4 | 2,500 | 100 | 100 | `Ind-0/Epi-3` |
| `test_location_4p0` | Represented targets; held-out locations. | 4.0 | 2,500 | 100 | 100 | `Ind-0/Epi-3` |
| `test_seen_energy_3p2` | Represented targets at the held-out 3.2 mJ energy. | 3.2 | 13,000 | 100 | 520 | `Ind-0/Epi-3` |
| `test_in_2p4` | Target- and family-disjoint, composition-in-range test. | 2.4 | 19,750 | 151 | 790 | `Ind-3/Epi-3` |
| `test_in_3p2` | Target- and family-disjoint, composition-in-range test. | 3.2 | 19,750 | 151 | 790 | `Ind-3/Epi-3` |
| `test_in_4p0` | Target- and family-disjoint, composition-in-range test. | 4.0 | 19,875 | 151 | 795 | `Ind-3/Epi-3` |
| `test_ood_2p4` | Target- and family-disjoint, composition-OOD test. | 2.4 | 19,875 | 150 | 795 | `Ind-3/Epi-3` |
| `test_ood_3p2` | Target- and family-disjoint, composition-OOD test. | 3.2 | 19,875 | 150 | 795 | `Ind-3/Epi-3` |
| `test_ood_4p0` | Target- and family-disjoint, composition-OOD test. | 4.0 | 19,875 | 150 | 795 | `Ind-3/Epi-3` |
| `test_all5_matched_2p4` | Target- and family-disjoint 23-material population matched across all five energies. | 2.4 | 5,750 | 23 | 230 | `Ind-3/Epi-3` |
| `test_all5_matched_3p2` | Same matched 23-material population. | 3.2 | 2,875 | 23 | 115 | `Ind-3/Epi-3` |
| `test_all5_matched_4p0` | Same matched 23-material population. | 4.0 | 5,750 | 23 | 230 | `Ind-3/Epi-3` |
| `test_all5_matched_5p6` | Same matched 23-material population. | 5.6 | 2,875 | 23 | 115 | `Ind-3/Epi-3` |
| `test_all5_matched_7p2` | Same matched 23-material population. | 7.2 | 2,875 | 23 | 115 | `Ind-3/Epi-3` |

### Quantification stress row sets

These separate diagnostic populations are not part of the primary locked-test claim. Zero-row keys are retained to expose the complete prespecified schema; they do not represent observed evaluation data.

| NPZ key | Stress population | Energy key (mJ) | Rows | Materials | Products |
|---|---|---:|---:|---:|---:|
| `stress_pure_metal_2p4` | Pure metal. | 2.4 | 125 | 1 | 5 |
| `stress_nonclosed_reference_2p4` | Non-closed reference material. | 2.4 | 250 | 2 | 10 |
| `stress_nonclosed_mixture_2p4` | Non-closed mixture. | 2.4 | 1,375 | 11 | 55 |
| `stress_pure_metal_3p2` | Pure metal. | 3.2 | 125 | 1 | 5 |
| `stress_nonclosed_reference_3p2` | Non-closed reference material. | 3.2 | 375 | 3 | 15 |
| `stress_nonclosed_mixture_3p2` | Non-closed mixture. | 3.2 | 1,375 | 11 | 55 |
| `stress_pure_metal_4p0` | Pure metal. | 4.0 | 125 | 1 | 5 |
| `stress_nonclosed_reference_4p0` | Non-closed reference material. | 4.0 | 375 | 3 | 15 |
| `stress_nonclosed_mixture_4p0` | Non-closed mixture. | 4.0 | 1,375 | 11 | 55 |
| `stress_pure_metal_5p6` | Pure metal; no eligible rows. | 5.6 | 0 | 0 | 0 |
| `stress_nonclosed_reference_5p6` | Non-closed reference; no eligible rows. | 5.6 | 0 | 0 | 0 |
| `stress_nonclosed_mixture_5p6` | Non-closed mixture; no eligible rows. | 5.6 | 0 | 0 | 0 |
| `stress_pure_metal_7p2` | Pure metal; no eligible rows. | 7.2 | 0 | 0 | 0 |
| `stress_nonclosed_reference_7p2` | Non-closed reference; no eligible rows. | 7.2 | 0 | 0 | 0 |
| `stress_nonclosed_mixture_7p2` | Non-closed mixture; no eligible rows. | 7.2 | 0 | 0 | 0 |

`Inst` is unassigned for these SuperLIBS evaluations because the available session/device metadata do not support an instrumental-separation code.

## NASA SuperLIBS lithology-classification splits

| File | Purpose |
|---|---|
| `branch_a_row_manifest.csv.gz` | Exact Branch A HDF5 rows and roles for eight-class independence/composition-shift evaluation. |
| `branch_b_row_manifest.csv.gz` | Exact Branch B HDF5 rows and roles for four-class energy interpolation and extrapolation. |
| `branch_b_balanced_replication_manifest.csv.gz` | Prespecified balanced-replication sensitivity subset for Branch B evaluation. |
| `branch_a_preprocessing_fit_manifest.json` | Branch A preprocessing-fit population and hashes. |
| `branch_b_preprocessing_fit_manifest.json` | Branch B preprocessing-fit population and hashes. |
| `row_manifest_status.json` | Frozen protocol version, source HDF5 hash, row counts, and release-gate outcomes. |
| `allocation/*_material_roles.csv` | Compact material-to-cohort assignments. |
| `allocation/*_split_group_roles.csv` | Compact independent-group-to-cohort assignments. |
| `allocation/cohort_counts.csv` | Counts by branch, class, and cohort. |
| `ALLOCATION_PROTOCOL.md` | Scientific eligibility, group allocation, weighting, and cross-branch policy. |
| `ROW_PROTOCOL.md` | Row-level holdout, isolation, selection, metric, and release-gate rules. |

The compressed CSV manifests can be read directly. This optional example uses pandas:

```python
import pandas as pd

a = pd.read_csv(
    "splits/superlibs_classification/branch_a_row_manifest.csv.gz"
)
a_train = a[a["row_role"].str.startswith("A_TRAIN_")]
a_locked = a[a["locked"]]
```

Important columns include `hdf5_row_index`, `immutable_row_id`, `material_id`, `family_id`, `split_group_id`, `class_label`, `row_role`, eligibility flags, and the `locked` indicator.

### Exact classification roles

The tables below list every exact value of `row_role`; counts are HDF5 rows in the corresponding compressed CSV. Energy suffixes decode as `2P4` = 2.4 mJ, `3P2` = 3.2 mJ, `4P0` = 4.0 mJ, `5P6` = 5.6 mJ, and `7P2` = 7.2 mJ. `Inst` is unassigned because the available session/device metadata do not support an instrumental-separation code.

#### Branch A: independence and composition shift

`branch_a_row_manifest.csv.gz` contains 505,250 rows across eight lithology classes.

| Exact `row_role` | Use | Rows | Evaluation Code |
|---|---|---:|---|
| `A_TRAIN_2P4` | Training at 2.4 mJ. | 124,890 | — |
| `A_TRAIN_4P0` | Training at 4.0 mJ. | 124,890 | — |
| `A_SHOT_VAL_2P4` | Represented-training-group random-shot selection validation at 2.4 mJ. | 10,860 | `Ind-0/Epi-1` |
| `A_SHOT_VAL_4P0` | Represented-training-group random-shot selection validation at 4.0 mJ. | 10,860 | `Ind-0/Epi-1` |
| `A_V_IN_2P4` | Group-disjoint, composition-in-range selection validation at 2.4 mJ. | 3,000 | `Ind-3/Epi-1` |
| `A_V_IN_4P0` | Group-disjoint, composition-in-range selection validation at 4.0 mJ. | 3,000 | `Ind-3/Epi-1` |
| `A_V_OOD_2P4` | Group-disjoint, composition-OOD selection validation at 2.4 mJ. | 3,125 | `Ind-3/Epi-1` |
| `A_V_OOD_4P0` | Group-disjoint, composition-OOD selection validation at 4.0 mJ. | 3,125 | `Ind-3/Epi-1` |
| `A_T_IN_2P4` | Locked group-disjoint, composition-in-range test at 2.4 mJ. | 7,125 | `Ind-3/Epi-3` |
| `A_T_IN_4P0` | Locked group-disjoint, composition-in-range test at 4.0 mJ. | 7,125 | `Ind-3/Epi-3` |
| `A_T_OOD_2P4` | Locked group-disjoint, composition-OOD test at 2.4 mJ. | 7,500 | `Ind-3/Epi-3` |
| `A_T_OOD_4P0` | Locked group-disjoint, composition-OOD test at 4.0 mJ. | 7,500 | `Ind-3/Epi-3` |
| `A_BUFFER_EXCLUDED` | OOD-proximity buffer excluded from fitting and evaluation. | 3,000 | — |
| `A_UNUSED_ENERGY` | Rows at energies outside the Branch A 2.4/4.0 mJ design. | 189,250 | — |

The Branch A preprocessing population is exactly the 249,780 `A_TRAIN_*` rows; random-shot validation rows are excluded from preprocessing fitting.

#### Branch B: energy interpolation and extrapolation

`branch_b_row_manifest.csv.gz` contains 410,375 rows across four lithology classes. In Branch B, `I` means interpolation, `X` extrapolation, `V` selection validation, and `T` locked test. The optional balanced-replication manifest contains only the group-disjoint interpolation and extrapolation roles; `—` means that a role is absent from that sensitivity subset.

| Exact `row_role` | Use | Main rows | Balanced rows | Evaluation Code |
|---|---|---:|---:|---|
| `B_TRAIN_2P4` | Training at 2.4 mJ. | 106,950 | — | — |
| `B_TRAIN_4P0` | Training at 4.0 mJ. | 106,950 | — | — |
| `B_SHOT_VAL_2P4` | Represented-training-group random-shot selection validation at 2.4 mJ. | 9,300 | — | `Ind-0/Epi-1` |
| `B_SHOT_VAL_4P0` | Represented-training-group random-shot selection validation at 4.0 mJ. | 9,300 | — | `Ind-0/Epi-1` |
| `B_I_V_2P4` | Group-disjoint interpolation selection validation at 2.4 mJ. | 2,125 | 2,125 | `Ind-3/Epi-1` |
| `B_I_V_3P2` | Same interpolation-validation population at 3.2 mJ. | 2,125 | 2,125 | `Ind-3/Epi-1` |
| `B_I_V_4P0` | Same interpolation-validation population at 4.0 mJ. | 2,125 | 2,125 | `Ind-3/Epi-1` |
| `B_I_T_2P4` | Locked group-disjoint interpolation test at 2.4 mJ. | 4,000 | 4,000 | `Ind-3/Epi-3` |
| `B_I_T_3P2` | Same locked interpolation-test population at 3.2 mJ. | 4,000 | 4,000 | `Ind-3/Epi-3` |
| `B_I_T_4P0` | Same locked interpolation-test population at 4.0 mJ. | 4,000 | 4,000 | `Ind-3/Epi-3` |
| `B_X_V_2P4` | Group-disjoint extrapolation selection validation at 2.4 mJ. | 2,250 | 2,000 | `Ind-3/Epi-1` |
| `B_X_V_4P0` | Same extrapolation-validation population at 4.0 mJ. | 2,250 | 2,000 | `Ind-3/Epi-1` |
| `B_X_V_5P6` | Same extrapolation-validation population at 5.6 mJ. | 2,000 | 2,000 | `Ind-3/Epi-1` |
| `B_X_V_7P2` | Same extrapolation-validation population at 7.2 mJ. | 2,000 | 2,000 | `Ind-3/Epi-1` |
| `B_X_T_2P4` | Locked group-disjoint extrapolation test at 2.4 mJ. | 4,375 | 4,125 | `Ind-3/Epi-3` |
| `B_X_T_4P0` | Same locked extrapolation-test population at 4.0 mJ. | 4,375 | 4,125 | `Ind-3/Epi-3` |
| `B_X_T_5P6` | Same locked extrapolation-test population at 5.6 mJ. | 4,125 | 4,125 | `Ind-3/Epi-3` |
| `B_X_T_7P2` | Same locked extrapolation-test population at 7.2 mJ. | 4,125 | 4,125 | `Ind-3/Epi-3` |
| `B_UNUSED_ENERGY` | Rows not used by the Branch B design. | 134,000 | — | — |

The Branch B preprocessing population is exactly the 213,900 `B_TRAIN_*` rows at 2.4 and 4.0 mJ; random-shot validation rows are excluded. Interpolation uses one same-material population at 2.4, 3.2, and 4.0 mJ. Extrapolation uses a different same-material population at 2.4, 4.0, 5.6, and 7.2 mJ; these two populations are disjoint and must not be joined into a single five-energy curve.

Branch A and Branch B are separately trained complementary experiments. Physical materials or split groups may occur in different roles across branches; the branches must not be interpreted as statistically independent replications.

## Raw-data dependency

Raw spectra are not redistributed in this repository. The SuperLIBS manifests map to the NASA SuperLIBS 10K Earth HDF5 row order used in the study. That source HDF5 had:

- size: 35,104,798,513 bytes;
- SHA-256: `b0e4a49a384946b4c213e7edf36b41e59a6162ee640ff0d5cf6577cb270242da`;
- spectral shape: 997,625 × 8,767.

The quantification manifest additionally records its scientific source fingerprint, chemistry fingerprint, and audit hash. Do not apply the row indices to a differently ordered source file merely because its spectra appear similar.

## Verification

Requirements: Python 3 and NumPy.

```bash
python3 scripts/verify_repository.py
```

The verifier checks the released SHA-256 list, EMSLIBS allocations, quantification row sets and bounds, classification manifest counts and required columns, compressed-file readability, and preprocessing-manifest links. A successful result is:

```json
{
  "complete": true,
  "errors": []
}
```

The checksum list covers immutable scientific artifacts, not `README.md`, `CITATION.cff`, or the verifier itself.

## Evidence boundary

| Study | Main comparison | Evidence status |
|---|---|---|
| EMSLIBS 2019 classification | Represented-sample shot validation (`Ind-0`) versus sample-disjoint validation (`Ind-1`) against a fixed public benchmark. | Retrospective diagnostic evidence; benchmark access is `Epi-0`, while final `Ind` and `Inst` cannot be assigned from available metadata. |
| NASA SuperLIBS quantification | Represented-target shot validation (`Ind-0`) versus target- and physical-family-disjoint validation (`Ind-3`). | Validation is `Epi-1`; frozen final cohorts are `Ind-3/Epi-3`. |
| NASA SuperLIBS classification | Represented-sample shot validation (`Ind-0`) versus group-disjoint validation (`Ind-3`) for composition- and energy-defined populations. | Validation is `Epi-1`; frozen final cohorts are `Ind-3/Epi-3`. |

The case studies are supportive, not exhaustive. No available dataset controlled every framework axis. Session/device metadata were insufficient to assign `Inst`, and gate delay and width were insufficiently reported to determine `Δdet`.

The framework does not itself improve final model accuracy. It makes the supported claim explicit, improves comparison between studies, and supplies stable evaluation domains for future augmentation, preprocessing, calibration-transfer, uncertainty, and model-development work.

## Citation

Please cite the accompanying manuscript:

> Toni Aaltonen and Pekka Suominen. *Evaluation-Dependent Performance Claims in Machine-Learning LIBS: A Framework for Classification, Quantification, and Out-of-Distribution Evaluation*. Manuscript.
