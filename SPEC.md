# Hingecheck 0.1 specification

Hingecheck records explicit assumptions and downstream dependency structure.

## Assumption

```json
{
  "id": "H001",
  "text": "S004 is independent of S002.",
  "status": "uncertain",
  "authorities": ["A001"],
  "recheck_when": "A source relationship between S004 and S002 is established.",
  "status_history": [
    {
      "status": "uncertain",
      "reason": "Initial project state.",
      "authorities": ["A001"]
    }
  ],
  "dependents": []
}
```

## Dependent record

```json
{
  "id": "E007",
  "kind": "evidence",
  "dependency": "relies-on",
  "note": "Independence affects corroboration weight."
}
```

## Status rule

Changing an assumption to `challenged` or `invalidated` does not change any dependent record automatically.

Instead, those dependents become part of the impact/recheck output.

## Authority

Authority pointers use the same deliberately lightweight pattern as Bridgekeeper:

```json
{
  "id": "A001",
  "label": "Sourceweave lineage check",
  "location": "sourceweave:north-reach:S004",
  "kind": "tool-record",
  "note": ""
}
```

## Boundary rule

Hingecheck records declared assumptions and declared dependency relationships.

It must not infer that a record depends on an assumption merely because the two are topically related.
