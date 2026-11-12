# Product spec — Decision Allocation

## Who it is for

An engineer or MoC coordinator deciding how a proposed change should be handled, and the
person reviewing that decision afterwards.

## What it answers

*Who should decide this change: AI-led, AI-supported, or human-led — and why?*

## Behaviour

1. **Choose the change.** Either an existing MoC record or a proposed change (type, asset,
   description, and whether a HAZOP is needed if known). A change entered in Smart Form,
   Risk or Cost carries over.
2. **See the impact assessment.** Target asset and criticality, downstream assets reached,
   HAZOP / PSSR / shutdown, risk assessment, parameter change, history on the asset.
3. **Review eight characteristics.** Each axis shows a suggested value, where it came from
   (knowledge graph, reference characterisation, assumption) and the evidence. Low-confidence
   suggestions are flagged. Any value can be changed; changes can be reset.
4. **Read the result.** Four scores with their level, boundaries and margin; three matrices
   showing each dimension against Impact; the signature; the recommended allocation.
5. **Understand it.** Which characteristics drove each score, which dimension forced
   escalation, and which single change would alter the recommendation.
6. **Export** the characterisation and result as a file.
7. **Check the model.** The ten thesis cases with published and computed outputs side by
   side; the model's weights, thresholds, rule and author.

## Rules

- The recommendation is computed by the fixed model. It is identical for identical inputs.
- A recommendation is never shown without its reasons.
- Assumed or reconstructed inputs are labelled as such.
- The feature works when the AI service is down, and scores when the knowledge graph is down.
- MoCBot and the agent report the same result when asked; they do not form their own.

## Acceptance

- MoC-002 → AI-supported, Risk 2 / Complexity 1.5 / Uncertainty 0.5 / Impact 2.5, signature II/II/II.
- MoC-001 → human-led, escalated by Uncertainty alone.
- All ten reference cases match thesis Table 2.
- Changing any axis updates scores, matrices, recommendation and reasons.
- An incomplete characterisation is rejected with the axis named.

## Not in scope yet

Saving a confirmed characterisation to the knowledge graph; authentication; editing the
model's weights or thresholds in the UI; AI-suggested characterisation. See
[../reports/mvp-backlog.md](../reports/mvp-backlog.md).
