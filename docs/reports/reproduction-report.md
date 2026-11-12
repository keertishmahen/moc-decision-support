# Reproduction report — the decision-allocation instrument

**Date:** 12 November 2026 · **Question:** can the outputs of Parth Atiwadkar's
computational instrument (thesis, instrument v1.14) be reproduced independently?

## Answer

Yes. An implementation written only from the thesis text and figures reproduces every
published output of the model, with two documented exceptions that trace to the thesis or
the original instrument rather than to the model. The checks below run as automated tests
(`tests/allocation/`).

## How the eight axes become four scores

Each selected category adds its weight to the dimensions it feeds (weights in Fig. 5):

- **Risk** = A1 nature + A3 duration + A8 impact type (maximum 3)
- **Complexity** = A2 system level + A4 scope + A5 acceptance + A6 occurrence (maximum 4)
- **Uncertainty** = A6 occurrence + A7 information (maximum 2)
- **Impact** = A1 + A2 + A3 + A4 + A8 (maximum 5)

Each score is levelled LOW / MED / HIGH against thresholds that are fractions of its
maximum (Fig. 7); Risk, Complexity and Uncertainty are each read against the Impact level
(Fig. 8) to give a factor; any factor III is human-led, all factor I is AI-led, anything
else AI-supported. Full tables: `docs/references/decision-allocation-model.md`.

## Results

| Published result | Thesis | Reproduced |
|---|---|---|
| Size of the characterisation space | 2,592 | 2,592 ✓ |
| AI-led / AI-supported / human-led | 62 / 406 / 2,124 | 62 / 406 / 2,124 ✓ |
| Signatures reached | 24 of 27 | 24 of 27 ✓ (missing: II/III/I, III/II/I, III/III/I) |
| High-U, low-R, low-C region | 64 points | 64 ✓ |
| Most frequent signatures (Fig. 11) | III/III/III 918, II/II/III 220, … | all eight match ✓ |
| Ten FCC cases (Table 2) | scores, levels, signature, allocation | 10 of 10 ✓ |
| MOC-F02 | R 2, C 1.5, U 0.5, I 2.5 → AI-supported | identical ✓ |
| Dashboard example (Fig. 10) | 2.50 / 0.00 / 0.50 / 2.50, III/I/II, margins 0.50 / 1.48 / 0.02 / 0.47 | identical ✓ |
| Single-axis swing (Fig. 11) | per-axis spans | identical ✓ |
| Weight perturbation ±20 % (Fig. 12) | A8→I 6.6 %, A7→U 4.2 %, … ten values | all ten match ✓ |
| Threshold sweep (Fig. 13) | 19 % – 96 % human-led | four of five columns match ✓ |
| Appendix G framework allocations | four practitioners | three of four ✓ |

## Differences

1. **Threshold sweep, column 0.75.** With the upper threshold at exactly 0.75, the
   Complexity and Uncertainty boundaries fall exactly on attainable scores (3.0 and 1.5).
   Under the rule in Section 6.1 those scores are HIGH, giving 58 / 56 / 53 / 47 / 37 %.
   The published column (42 / 42 / 40 / 38 / 31 %) is reproduced exactly when the boundary
   sits marginally above 0.75, which is what floating-point rounding in the original
   instrument would produce. The model is unaffected; only this sweep column is.
2. **Appendix G, Interviewee01.** The recorded selection (operational, unit, permanent,
   local, individual, situational, deterministic, technical) scores R 1.5, C 1, U 1,
   I 1.5 — identical to MOC-F01, which Table 2 lists as human-led. Appendix G lists the
   framework allocation for this row as AI-supported. The model gives human-led.

Not reproducible from the thesis: the Monte Carlo stability figure (100 % at human-led),
because the case it was run on is not identified. The Monte Carlo procedure is implemented.

## Notes on how figures were matched

- The weight-perturbation share in Fig. 12 is the mean of the −20 % and +20 % runs; level
  boundaries are held at their baseline values, as the thesis specifies.
- Risk 2.0 is MED, not HIGH, because 0.667 × 3 = 2.001.

## The ten case characterisations are reconstructions

The thesis publishes each case's scores but not its eight axis selections. The published
scores fix five axes (system level, scope, acceptance, occurrence, information) for almost
every case; nature of change and impact type have two or three valid combinations; duration
is taken as permanent because no MoC record carries a duration. Between 2 and 20
characterisations reproduce each case's scores. The chosen ones are in
`core/allocation/config/reference_cases.json`, each marked
`reconstructed-pending-confirmation` with its alternatives.

## Questions for the author

1. Please confirm the axis selections for MOC-F01 … MOC-F10 (or share the instrument's case register).
2. Appendix G, Interviewee01: is the framework allocation AI-supported or human-led?
3. Section 5.3 and Appendix E give "temporary with undefined duration" the same weight as
   permanent (1) and "temporary" 0.5; the instrument (Fig. 5) uses 0.5 and 0. The
   instrument values are implemented because only they reproduce the published totals.
   Which is intended?
4. Which case was the Monte Carlo run on?
