# Mission Control Context Structure v1

This is the recommended structure for a docs/context repo or an equivalent
folder inside the Hermes workspace. It is a token-efficiency layer, not an
authority layer. Mission Control records remain authoritative.

```text
projects/
  hermes-mission-control/
    brief.md
    current-state.md
    decisions.md
    risks.md
    specs/
    lanes/
  long-form-video/
  shorts-video/
  tool-tally/
  waha-work/

policies/
  safety.md
  approval-gates.md
  challenge-gate.md
  autonomy-levels.md
  forbidden-actions.md

runbooks/
  new-project-intake.md
  read-only-lane.md
  pr-creation-lane.md
  deploy-approval.md
  rollback-check.md

context-packs/
  mission-control-current.md
  video-system-current.md
```

## Rules

- Accepted state only belongs in context packs.
- Draft discussion belongs in reports or challenge reviews until accepted.
- Context packs should be short enough for Jenny to load without rereading old
  chat history.
- Project-specific contexts must stay isolated, especially Waha and customer
  work.
- A context pack can summarize specs, but must point back to the source file.
