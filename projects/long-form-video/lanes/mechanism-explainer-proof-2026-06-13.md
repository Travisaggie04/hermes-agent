# Lane Packet - Long-Form Mechanism Explainer Proof

Project ID: `project-long-form-video`

Lane ID: `lane-long-form-mechanism-explainer-proof-2026-06-13`

## Objective

Stop pursuing full character animation first. Prove a repeatable long-form
production style through a deterministic 10-15 second mechanism explainer.

## Research Finding Incorporated

The long-form research recommends a faceless documentary/explainer hybrid with
mechanism-style visuals, not full character animation. The current local
video-model ecosystem is useful for inserts and ideation, but not reliable
enough to be the backbone for episode-scale production.

## Scope

Build or prepare one internal proof:

- 10-15 seconds,
- mechanism-explainer visual language,
- voiceover,
- readable captions,
- deterministic assets,
- QA evidence.

The proof should be treated as a pipeline test, not a publishing event.

## Preferred Format

Faceless documentary/explainer with:

- diagrams,
- mechanism animations,
- kinetic captions,
- screenshots or stills where useful,
- voiceover,
- optional tightly controlled 3D/generative insert.

Avoid character acting, lip-sync, and full episode production in this lane.

## Recommended Tool Direction

- Hub/finishing: DaVinci Resolve.
- Vector assets: Inkscape.
- Media QA: FFmpeg and ffprobe.
- Transcription/captions: faster-whisper or WhisperX, Subtitle Edit.
- Motion templates: Cavalry or Resolve/Fusion.
- 3D inserts only when useful: Blender.
- AI inserts only as sidecar experiments: ComfyUI with Wan/FramePack.

## Proof Prompt

Example proof concept:

`Every payment enters the machine, gets routed, sliced, skimmed, and exits
smaller than it arrived.`

Micro-beats:

1. entry,
2. routing,
3. fee extraction,
4. output comparison,
5. branded end card.

## Pass / Fail Criteria

Pass only if:

- final render can be regenerated from project files,
- claim-critical text is legible and OCR spot-checkable,
- subtitle text materially matches the voiceover,
- audio is clear and measured rather than guessed,
- every beat changes viewer understanding,
- no missing asset scavenging is required.

## Allowed

- Local-only proof planning.
- Local tool preflight.
- Internal test renders.
- QA scripts and evidence packets.

## Forbidden Without Explicit New Approval

- Live posting.
- Account mutation.
- Paid purchases.
- Full episode production.
- Scheduler/queue automation.
- Hidden worker/timer/daemon.

## Acceptance Evidence

- Local tool preflight result.
- Proof plan or artifact path.
- Render/QA checklist result.
- Clear decision on whether the style can scale.

## Win Condition

The long-form lane has a repeatable visual direction and proof criteria before
spending time on full episodes or character rigs.
