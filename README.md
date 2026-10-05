# Hingecheck

**Version:** 0.1  
**Status:** experimental

Hingecheck tracks project assumptions, what depends on them, and what should be rechecked when an assumption changes.

Its central rule:

> **When a hinge moves, show which doors moved with it.**

Hingecheck does not automatically declare dependent claims false. It identifies the records whose reasoning path should be revisited.

## Assumption statuses

- `declared`
- `supported`
- `uncertain`
- `challenged`
- `invalidated`

A status is descriptive project state, not an automatic truth score.

## What it records

A project contains:

- assumptions
- status history
- authority pointers
- dependent records
- dependency types
- recheck triggers
- impact notes

Typical dependent record kinds:

- claim
- evidence
- classification
- conflict
- hypothesis
- writing-unit
- conclusion
- other

Dependency types:

- requires
- relies-on
- strengthens
- weakens-if-false
- invalid-if-false
- interpretive-context

## Quick start

```bash
python hingecheck.py new hinges.json --title "North Reach assumptions"

python hingecheck.py authority hinges.json A001 \
  --label "Sourceweave lineage check" \
  --location "sourceweave:north-reach:S004" \
  --kind tool-record

python hingecheck.py assumption hinges.json \
  "S004 is independent of S002." \
  --status uncertain \
  --authority A001 \
  --recheck-when "A source relationship between S004 and S002 is established."

python hingecheck.py depend hinges.json H001 \
  E007 --kind evidence --type relies-on \
  --note "Independence affects corroboration weight."

python hingecheck.py status hinges.json H001 challenged \
  --reason "S004 cites material derived from S002." \
  --authority A001

python hingecheck.py impact hinges.json H001
python hingecheck.py audit hinges.json
python hingecheck.py render hinges.json -o report.md
python hingecheck.py mermaid hinges.json -o hinges.mmd
```

## Recheck behavior

When an assumption is `challenged` or `invalidated`, Hingecheck surfaces its dependents for review.

It does **not** automatically:

- delete dependent records
- reverse their conclusions
- change evidence classifications
- resolve contradictions
- infer replacement assumptions

The output is a recheck queue, not a cascade of automatic conclusions.

## Authority pointers

Authority pointers can reference:

- tool records
- documents
- repositories
- commits
- specifications
- conversations
- other explicit locations

Hingecheck stores a pointer and label rather than copying entire source systems.

## Relationship to the other tools

Hingecheck complements the existing toolkit:

- Evidence Ledger can identify where independence matters.
- Contradiction Atlas can expose conflicts that challenge an assumption.
- Sourceweave can reveal hidden source dependence.
- Provenance Lens can show which finished writing units used the assumption.
- Tracebridge can carry dependency references between tools.
- Bridgekeeper can preserve an assumption-status change across continuity handoffs.

None of those tools is required to use Hingecheck.

## Audit behavior

The structural audit can flag:

- assumptions with no authority pointer
- challenged or invalidated assumptions with no reason
- dependencies with no note
- assumptions with no recheck condition
- dependents pointing at duplicate local identifiers within the same assumption

These are structural warnings, not truth judgments.

## Outputs

Hingecheck can produce:

- JSON project files
- Markdown assumption reports
- focused impact/recheck reports
- Mermaid dependency graphs
- structural audits

## What Hingecheck does not do

Hingecheck is not a truth engine.

It does not infer hidden assumptions automatically.

It does not decide whether a challenged assumption is false.

It does not invalidate downstream conclusions by association.

It makes the hinge and its dependent doors visible.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

When a hinge moves, show which doors moved with it.
