# SuperLIBS lithology-classification protocol — Version 2.1.2

## Status

Version 2.1.2 is the canonical cross-branch role and access-isolation clarification for the unchanged Version 2.1.1 deterministic allocation. Version 2.1.1 remains the exact selected-material review and metric-definition lock; Version 2.1 remains the historical scientific-eligibility allocation; Version 2.0 remains the historical allocator before correction of the material-type population.

Version 2.1.2 freezes scientific screening, selected-material decisions, exact class-balanced metric definitions, group allocations, material-level manifests, and the rule governing cross-branch overlap. No allocation-affecting parameter or cohort assignment is changed. It authorizes construction of branch-specific spectral-row manifests but does **not** authorize spectral training. Training remains blocked until row-level access controls, preprocessing, and integrity tests are generated and frozen.

## 1. Scientific material-eligibility gate

The primary task is classification of archived chemistry-defined igneous lithological categories. The eligibility gate is applied to the full source population before calculation of split groups, composition transforms, atypicality, nearest-neighbour graphs, buffers, or allocations.

The policy has three components:

1. archived `category=mixture` materials are excluded as synthetic mixtures;
2. archived `category=pure_metal` materials are excluded;
3. screened or otherwise known reference-like materials receive an explicit frozen decision in `material_type_reviewed_decisions_v1.csv`.

The screening rules are review triggers, not automatic class labels. For materials that passed the upstream label, chemistry, and 2.4/4.0 mJ coverage screen, review is triggered by any of:

- eight-oxide sum below 85 wt%;
- more than two zero-valued split oxides;
- Al2O3 above 32 wt%;
- Fe2O3* above 30 wt%;
- MnO above 5 wt%;
- a frozen target-name regular expression.

Every triggered material must have an explicit reviewed decision or input preparation fails. Reviewed exclusions are BARITE, C5STD, FERRINATRITE, GBW07313, JAROSITE, MELANTERITE, MHC86276, MUSCOC17, and ST44A. The decision table records the evidence, reason, review status, and notes for each material. This list is applied globally; no selected cohort is manually repaired.

After deterministic allocation, every selected non-training evaluation material, represented-family anchor material, and OOD-buffer material must also have an explicit frozen row in `selected_material_review_decisions_v1.csv`. The decision key is `experiment + material_id + selected_role`. The required values are `decision=approve` and `review_status=completed_metadata_review`. Missing, duplicated, extra, rejected, or incomplete decisions cause allocator failure. Any exclusion requires complete upstream regeneration; manual cohort substitution is prohibited.

The selected-material review is a structured metadata review for the archived chemistry-defined lithology task. It confirms consistency with the frozen archived-label, source-category, chemistry-screening, and exclusion policy. It is not independent petrographic or mineralogical authentication.

Changing the material-type gate requires complete regeneration of:

- eligible materials;
- exact-chemistry linkage and `split_group_id`;
- robust-log scaling;
- radial distance, local sparsity, and atypicality;
- nearest-neighbour graphs and OOD buffers;
- Branch A and Branch B allocations;
- group/material manifests and hashes.

The status file reports separately:

- `allocator_algorithm_pass`;
- `scientific_screening_pass`;
- `selected_material_review_pass`;
- `metric_definition_lock_pass`;
- `scientific_eligibility_gate_pass`;
- `cohort_allocation_pass`;
- `spectral_row_manifest_generation_allowed`;
- `spectral_training_allowed`.

## 2. Independent analysis unit

`split_group_id` is the canonical independent unit for assignment, weighting, and bootstrap resampling. Original family IDs connected by exact eight-oxide duplicates are retained in one split group.

Each split group receives total analysis weight one, divided across its retained materials. Bootstrap resampling is by split group. Repeated draws are not deduplicated: every sampled copy contains the complete material set and has within-copy material weights summing to one.

## 2.1 Cross-branch role and access-isolation policy

Branch A and Branch B are separately trained experiments with separate training manifests, separate fitted preprocessing objects, separate classifiers, separate model-selection processes, and branch-specific evaluation locks. Branch B interpolation and extrapolation continue to share one common Branch B 2.4/4.0 mJ training population and one set of Branch B candidate trajectories.

A `split_group_id` or physical material may occur in different roles across Branch A and Branch B. This cross-branch overlap is permitted because no fitted object or model-selection decision is shared between the two separately trained branches.

Within each branch, all of the following are prohibited:

- a validation or locked-evaluation split group entering that branch's training rows;
- a validation or locked-evaluation row contributing to that branch's fitted scaling, centring, PCA, feature selection, calibration, or any other preprocessing state;
- a locked-evaluation prediction contributing to checkpoint, configuration, ensemble, threshold, or model-selection decisions.

Cross-branch overlap must be exported as split-group-level and material-level audit tables and disclosed in the manuscript or Supporting Information. Because overlapping physical units can contribute evidence to both branches, Branch A and Branch B must not be interpreted as statistically independent replications. Cross-branch overlap does not require reallocation and does not block row-manifest construction when all within-branch isolation checks pass.

## 3. Primary and secondary chemistry representations

Primary composition coordinates are calculated only from scientifically eligible split groups:

1. take the median eight-oxide chemistry within each split group;
2. apply `log1p` oxide-wise;
3. centre by the global eligible-split-group median;
4. scale by the global eligible-split-group interquartile range.

Preliminary composition atypicality is the equal-weight mean of class-relative radial-distance and local-sparsity percentiles. The resulting full-class atypicality percentile is calculated once from the complete scientifically eligible class population. It is frozen before energy-coverage filtering, subbranch selection, or cross-subbranch exclusions.

Branch B also exports a subbranch-candidate-pool percentile. It is diagnostic only and cannot determine hard eligibility.

CLR coordinates with oxide-specific half-minimum-positive zero replacement are a prespecified sensitivity analysis, not a hard allocation gate. The report flags low primary-versus-CLR distance-rank agreement, in-range groups above the CLR training-neighbour 90th percentile, Branch A loss of OOD/in-range ordering, and Branch B selected groups above the CLR training-neighbour 90th percentile.

## 4. Branch A — independence and composition shift

The eight classes are Basalt, Rhyolite, Dacite, Basaltic andesite, Trachyandesite, Andesite, Basaltic trachyandesite, and Foidite. Training and matched-energy evaluation use 2.4 and 4.0 mJ.

After the scientific material-type exclusions, Foidite contains 41 independent split groups. To retain all eight classes, at least 20 training groups, and room for one OOD-buffer group, the frozen symmetric cohort sizes are:

- `A_SHOT_VAL`: 6 represented training split groups per class;
- `V_IN`: 3 group-disjoint in-range split groups per class;
- `T_IN`: 7 development-locked in-range split groups per class;
- `V_OOD`: 3 group-disjoint composition-OOD split groups per class;
- `T_OOD`: 7 development-locked composition-OOD split groups per class;
- `OOD_BUFFER`: every non-evaluation group strictly closer than the frozen class-specific threshold to any selected OOD group.

OOD candidates must have full-class atypicality percentile at least 0.70. OOD selection is deterministic maximin selection. Distances are recalculated relative to the final training population after all evaluation and buffer groups are removed. For every class, the OOD median nearest-training distance must exceed the in-range 90th percentile. A secondary median-ratio floor of 1.30 is also enforced.

Validation/test partitioning is exhaustive and lexicographic. Because validation contains three groups, campaign and series prevalence change in increments of one third. The frozen Branch A limits are therefore:

- maximum campaign-prevalence difference: 1/3;
- maximum series-prevalence difference: 1/3;
- maximum relative median nearest-training-distance difference: 0.60;
- maximum relative IQR nearest-training-distance difference: 0.55.

These tolerances are feasibility constraints, not a claim that every validation/test distance distribution is closely matched.

`A_SHOT_VAL` is selected from final training groups by deterministic lexicographic matching to `V_IN + T_IN`. The objective includes chemistry-coordinate means, full-class atypicality median and IQR, nearest-training distance, campaign, series, material count, and exact-energy product and location-count vectors. The implementation uses a deterministic shortlist, greedy construction, one-swap improvement, and immutable-ID tie-breaking.

## 5. Branch B — paired nominal-energy experiments

The infeasible all-five-energy design is replaced by two separately paired physical populations in four classes: Basalt, Rhyolite, Basaltic andesite, and Trachyandesite.

### 5.1 Interpolation

The same physical-material IDs are evaluated at 2.4, 3.2, and 4.0 mJ.

- `I_V`: 4 split groups per class;
- `I_T`: 8 split groups per class.

### 5.2 Extrapolation

The same physical-material IDs are evaluated at 2.4, 4.0, 5.6, and 7.2 mJ.

- `X_V`: 4 split groups per class;
- `X_T`: 8 split groups per class.

Interpolation and extrapolation evaluation groups are disjoint. Both are evaluated by candidate trajectories trained on one common 2.4/4.0 mJ population that excludes their union.

For a Branch B split group, cohort chemistry is calculated from the median chemistry of the identical common materials actually evaluated at every energy in that subbranch. Non-common family members cannot influence hard centrality or matching.

Hard in-range centrality uses the frozen full-class atypicality percentile. Energy coverage and cross-subbranch exclusion are applied without recalculating that percentile. A true-nearest-neighbour ceiling at the 0.92 full-class quantile is frozen because it is the smallest value retaining the required 12 scientifically eligible Basaltic-andesite extrapolation groups.

Validation/test partitioning is exhaustive and lexicographic. Hard limits include:

- maximum relative median nearest-training-distance difference: 0.35;
- maximum relative IQR nearest-training-distance difference: 0.35;
- maximum campaign-prevalence difference: 0.25;
- maximum series-prevalence difference: 0.25;
- maximum single-campaign fraction in either cohort: 0.75.

The matching objective also contains chemistry-coordinate means and exact-energy product-count and material-location-count vectors. Campaign and series constraints are enforced jointly, not audited after allocation.

`E_A_SHOT_VAL` contains 6 represented training split groups per class. Anchors are deterministically matched to the combined interpolation and extrapolation evaluation population using its 2.4/4.0 mJ chemistry, atypicality, distance, campaign, series, material count, product count, and location count characteristics.

Branch-specific campaign reports contain only energies belonging to that branch. Incidental coverage at other energies does not enter branch-specific campaign summaries.

## 6. Metrics, weighting, and replication

Primary predictions remain material-level. Each `split_group_id` receives total weight one, divided across its retained materials. These weights are applied within each true class before class balancing.

For labels `1,...,C`, material probabilities `p_ik`, true labels `y_i`, and split-group-derived material weights `w_i`, the frozen definitions are:

- balanced accuracy: the equal mean of class recalls from the split-group-weighted confusion matrix;
- macro-F1: the equal mean of class F1 values from the same weighted confusion matrix;
- multiclass Brier score: calculate `sum_k (p_ik - 1[y_i=k])^2` per material, calculate its weighted mean separately within each true class, then average the class-specific values equally;
- negative log-likelihood: calculate `-log(max(p_i,y_i, epsilon))` per material, calculate its weighted mean separately within each true class, then average the class-specific values equally.

The probability-clipping constant is frozen in the hashed protocol as `probability_clip_epsilon = 1e-12`; it is not a function default. The reference test deliberately uses unequal class group counts and unequal class total weights so that the class-balanced calculation differs from a single overall weighted mean.

The Brier convention sums probability error over classes before true-class averaging. Its numerical range differs from implementations that average internally over the class dimension. Numerical comparisons are valid only under the same convention.

Exact-energy product and material-location counts are exported for every selected Branch B group. Validation/test matching uses those vectors rather than only subbranch totals. At the later row-manifest stage, a deterministic balanced-replication sensitivity must impose equal frozen replication counts per material and exact energy.

## 7. Determinism, provenance, and tests

All classes, energies, cohort sizes, exclusions, thresholds, objectives, tolerances, and tie rules are read from hashed configuration or reviewed-decision files. Input rows are sorted by immutable identifiers. Manual substitutions are prohibited.

The package hashes code, configuration, both decision tables, source tables, generated inputs, protocol documents, outputs, and environment records. Cross-branch overlap is exported at split-group and material level. Tests cover scientific screening, exact selected-material decision completeness, exact class counts, common-material equality, frozen full-class centrality, Branch B IQR limits, branch-permitted campaign energies, exact-energy replication vectors, zero-distance neighbours, split-group weighting, bootstrap multiplicity, class-balanced Brier/NLL under unequal class weights, clipping from the hashed protocol, hash consistency, and deterministic reruns under shuffled source-row order.

## 8. Training gate

Spectral-row manifest construction may proceed because the scientific screening, explicit selected-material review, metric-definition lock, and deterministic group allocation pass. Spectral training remains prohibited until all of the following pass:

1. exact spectral-row manifest construction from the canonical HDF5;
2. Branch A row-level cohort identity and locked-test access checks;
3. Branch B exact equality of common material IDs and row-set identities across energies;
4. branch-specific training, fitted-preprocessing, and model-selection isolation checks;
5. split-group-level and material-level cross-branch overlap audits, hash verification, and disclosure;
6. exact-energy replication audit and balanced-replication sensitivity definition;
7. preprocessing lock and test-row access controls;
8. byte-identical deterministic rerun and complete hash verification.
