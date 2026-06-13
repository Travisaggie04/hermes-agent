# Long-Form Proof Inventory - 2026-06-13

This is a read-only planning and inventory record. It does not approve full
episode production, publishing, scheduling, account mutation, paid purchases,
hidden workers, timers, or live platform actions.

## Recommendation

Keep the next long-form lane focused on one 10-15 second proof:

> Adult animated fee-machine mechanism proof with a reusable character layer,
> narration, captions, and deterministic final assembly.

Do not restart full long-form production yet. The evidence shows enough useful
assets to attempt a small proof, but not enough to approve a repeatable
long-form pipeline.

## Current Source Of Truth

- Shared video repo:
  `/home/jenny/wt/agentic-video-channel-factory`
- Repo status observed:
  `main...origin/main [ahead 32]`
- Untracked runtime directory observed:
  `runtime/`
- Pipeline registry:
  `docs/signal-room-pipeline-registry.md`

The pipeline registry says long-form is separate and not completed. Before any
automation, it needs its own quality lock, metadata contract, queue ledger,
backlog rules, and scheduler.

## Useful Existing Proof Assets

### Character / Rig Selection

Path:

`review-packages/signal-room-adult-character-rig-selection-2026-05-28`

Findings:

- Review-only rig-selection package exists.
- Best immediate candidate is `Suit_Male`; backup is `Suit_Female`.
- Candidate license files for Quaternius packs are present and marked CC0.
- Unknown-license local 2D character must stay review-only until license/source
  is confirmed.
- Blender was not installed on the Linux VPS, so fresh candidate renders were
  not produced there.
- `rig_acting_scorecard.json` currently fails because no
  `character_frames/<candidate>/rig_pass_manifest.json` directories exist yet.

Required next artifact:

- Transparent pose and mouth-switch frames for one selected adult character.

### Moho Character Fee-Machine Proof

Path:

`review-packages/signal-room-moho-character-fee-machine-proof-2026-05-28`

Findings:

- 12-second vertical review proof exists.
- It proved Moho-rendered transparent sample rig frames can composite over the
  existing hidden-fee machine scene.
- It did not prove final brand art, facial acting, lip sync, custom adult
  style, named reusable bones, or mouth switches.

Required next artifact:

- One real adult Signal Room character rig pass, not another sample-rig proof.

### Fee-Machine V2 HyperFrames Scaffold

Path:

`review-packages/signal-room-fee-machine-v2-hyperframes-scaffold-2026-05-28`

Findings:

- Review-only 15-second 1080x1920 scaffold exists.
- It uses HyperFrames with commands:
  - `npm run check`
  - `npm run preview`
  - `npm run render`
- It expects approved character frames to replace `assets/poses/*.svg`.
- Design direction is adult, practical, investigative, and not mascot-like.
- Current source rig is a review-only vector starter, not approved final art.

Required next artifact:

- Replace temporary pose SVGs with approved Blender/Moho character frames only
  after the rig acting gate passes.

### Historical Long-Form Mixed-Media Proof

Path:

`review-packages/signal-room-longform-phone-number-tracking-key-mixed-media-2026-05-18`

Findings:

- 349.46-second 1280x720 proof exists.
- QA recommendation was `REVIEW`.
- QA reported:
  - 5 high OCR/text safe-area risks,
  - 16 medium OCR/text warnings,
  - 54 ffmpeg black/freeze/silence warning events.
- This proves the repo has QA machinery and long-form assembly experience, but
  it also explains why jumping straight to full long-form is unsafe.

Required next artifact:

- Reuse the QA discipline, not the full-length production scope.

## Local Windows Tool Availability Observed From Codex

Found in standard paths:

- DaVinci Resolve:
  `C:\Program Files\Blackmagic Design\DaVinci Resolve`
- Inkscape:
  `C:\Program Files\Inkscape`
- Cavalry:
  `C:\Program Files\Cavalry`
- Node/npm/git available on PATH.

Not found from this shell:

- `ffmpeg`
- `ffprobe`
- `python`
- `blender`
- `inkscape` on PATH, even though Inkscape is installed under Program Files
- Moho under `C:\Program Files\Moho`
- Blender under `C:\Program Files\Blender Foundation`

Interpretation:

- The laptop likely has enough creative tools for manual proof work, but the
  command-line automation surface is not ready.
- Before asking Jenny to render, create a local tool preflight that locates
  Resolve, Inkscape, Cavalry, Blender/Moho if installed elsewhere, Python, and
  ffmpeg/ffprobe.

## Next Safe Lane

Create a local-only long-form proof-prep lane:

1. Locate or install the missing command-line prerequisites:
   Python, ffmpeg, ffprobe, and either Blender or the confirmed Moho CLI/manual
   export path.
2. Run the adult character rig render/gate from the existing rig-selection
   package on the Windows laptop or another render-capable machine.
3. Produce the required transparent frames:
   - `neutral_read.png`
   - `bill_shock.png`
   - `skeptical_point.png`
   - `look_to_machine.png`
   - `lean_weight_shift.png`
   - `mouth_a.png`
   - `mouth_o.png`
   - `mouth_closed.png`
4. Run the rig acting gate and save `rig_pass_manifest.json`.
5. Only if the rig passes, use the fee-machine HyperFrames scaffold for a
   10-15 second review render.
6. Write an evidence packet with:
   source prompt, asset list, tool list, render steps, final clip path,
   screenshots or frame stills, QA results, failure notes, and scale/no-scale
   decision.

## Stop Conditions

Stop before rendering or escalating if:

- Blender/Moho path cannot be verified.
- ffmpeg/ffprobe are unavailable.
- the rig acting scorecard still fails.
- candidate license/source is unclear.
- pose frames do not read at phone size.
- the proof requires paid purchases or account changes.
- the lane drifts toward a full episode, scheduler, or posting workflow.

## Morning Definition Of Done

A good morning outcome for long-form is:

- exact local render/tool prerequisites are known,
- one character candidate is selected,
- rig acting gate requirements are staged,
- the 10-15 second fee-machine proof path is ready to run,
- no full episode or hidden automation has been started.
