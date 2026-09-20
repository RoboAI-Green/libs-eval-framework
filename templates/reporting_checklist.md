# LIBS evaluation-claim reporting checklist

Use this checklist with the manuscript framework. It is a reporting aid, not a quality score. Omit DSM rows that are genuinely not applicable to the claim; if a factor is applicable but unavailable, keep it and state whether it was not measured or not reported.

## Claim and units

- [ ] State the task, intended deployment/evaluation population, and operational use.
- [ ] State the primary metric and prediction unit.
- [ ] Report the selection-validation and final-evaluation designs separately.
- [ ] State the split unit for selection and final evaluation (for example shot, location/crater, target, batch, family, session, instrument, site, or campaign).
- [ ] Report the number of independent units underlying the reported estimate.

## Evaluation Code

- [ ] Assign `Ind`, `Inst`, and `Epi` independently to selection validation and final evaluation, only where supported by metadata.
- [ ] For `Ind-0`, state whether the split separates only shots/spectra or also locations, craters, mapped regions, or other subtarget units.
- [ ] For mixed physical boundaries, assign the highest `Ind` level satisfied by every evaluation unit and report counts/proportions satisfying any stricter boundary separately.
- [ ] If an axis cannot be assigned, state the missing provenance/session/device/access information rather than using an unknown code.
- [ ] Report the observed number of final-test queries or submissions.

## Domain-Shift Matrix

For every applicable factor, report the development, selection-validation, and final-evaluation domains; the relation; a quantitative summary where possible; and the statistical/estimation unit.

- [ ] `R_matrix`: matrix/composition relation defined primarily from prespecified reference chemistry or composition groups.
- [ ] `Delta_conc`: per-analyte interpolation, edge coverage, low-end extrapolation, and high-end extrapolation; include ranges and outside-range counts/proportions.
- [ ] `Delta_prep`: sample form/phase, particle size, binder, compaction/fusion, moisture, surface/roughness, and prior ablation or cleaning-shot protocol when relevant.
- [ ] `Delta_env`: gas identity/composition and pressure, with temperature/humidity when relevant.
- [ ] `Delta_opt`: laser/excitation parameters plus focus, stand-off distance, beam incidence, and collection geometry.
- [ ] `Delta_det`: gate timing, wavelength coverage/grid, spectral-axis registration/calibration, resolving power, spectral response/efficiency, and applied corrections.
- [ ] `Delta_snr`: defined SNR or other signal-quality calculation, distribution/summary, and statistical unit.
- [ ] Add a named row for any other acquisition or sample condition that materially defines the intended claim.
- [ ] Do not collapse DSM factors into a single universal distance or difficulty score.

## Aggregation, transformations, and quantification companions

- [ ] State the aggregation rule: number of spectra/shots combined and whether preprocessing occurs before or after aggregation.
- [ ] Fit every learned transformation (imputation, scaling, feature/wavelength selection, PCA, target transformation, etc.) on the training partition/fold only during selection.
- [ ] If the frozen pipeline is refitted once on the complete development set before final evaluation, report that refit explicitly.
- [ ] For quantification, report the reference method and reference-value uncertainty for each domain when available; these are companion fields, not DSM factors.

## Reproducibility and scope

- [ ] Provide the versioned split specification or manifest and the rules used to construct every boundary.
- [ ] Identify the dataset/archive release and immutable source fingerprint when available.
- [ ] Report the uncertainty unit and method consistently with the physical dependence structure.
- [ ] State a bounded claim describing exactly which population and shifts the reported metric supports.
- [ ] Pin the repository state with a full Git commit SHA; use a release DOI/tag in addition when archived.
