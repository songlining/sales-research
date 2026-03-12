# Design: unify sales-research artifact and brief directories

**Date**: 2026-03-11
**Approach**: Single company folder under the customer path
**Goal**: Remove the split between intermediate research artifacts and the final sales brief so the skill writes all output into one predictable company directory.

## Problem

The active skill docs currently describe a split output model:

1. Intermediate research artifacts go to `docs/sales-research/[account-slug]/`
2. The final brief goes to `HashiCorp/by-customer/[Customer]/[Company] Sales Intelligence Brief.md`

That forces the agent to reason about two parent locations for the same research session, and it makes handoff, review, and incremental updates harder than necessary.

## Approved solution

Standardize on one company folder:

`HashiCorp/by-customer/[Customer]/[Company]/`

That folder becomes the single parent directory for:

- the final brief: `[Company] Sales Intelligence Brief.md`
- all intermediate research artifacts such as `contacts-pass-1.md`, `tech-landscape-research.md`, and `consolidation-notes.md`
- later incremental updates to the same account research

The intermediate files will remain as separate markdown files directly in the company folder. No `artifacts/` subfolder will be introduced.

## Documentation changes

Update these surfaces to describe the same layout:

- `SKILL.md`
- `SKILL.copilot.md`
- `Howto.md`
- `IMPLEMENTATION_SUMMARY.md`

The edits should:

1. replace active instructions that point to `docs/sales-research/...`
2. update example paths, folder trees, and save locations to the new company-folder layout
3. update prior-research lookup guidance so it checks the same company folder that now holds artifacts and the final brief
4. keep legacy-path discussion out of the active workflow unless it is needed as historical context

## Validation

After editing, verify that the docs consistently say:

- create `HashiCorp/by-customer/[Customer]/[Company]/`
- save intermediate markdown artifacts there
- save the final brief there
- continue incremental updates in that same folder
