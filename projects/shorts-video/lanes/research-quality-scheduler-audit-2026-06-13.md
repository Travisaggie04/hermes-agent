# Lane Packet - Shorts Research, Quality Gate, And Scheduler Audit

Project ID: `project-shorts-video`

Lane ID: `lane-shorts-research-quality-scheduler-audit-2026-06-13`

## Objective

Create a money-focused short-form plan that improves quality before restoring
volume or live posting.

## Research Finding Incorporated

The short-form research argues against generic faceless explainers and raw
volume. The better path is a commerce-aware, original, proof-heavy vertical
pipeline: one master short per idea, adapted first to YouTube Shorts, then
Facebook Reels, then Instagram Reels. TikTok remains future work until the
developer approval path is fixed.

## Scope

Read-only or shadow-mode work only:

- audit the current Lane A pipeline and scheduler/poster design,
- draft a 25-video queue strategy,
- define quality gates for monetization and originality,
- define a manual-start autoresearch loop,
- identify scheduler safety gaps before any live posting resumes.

## 25-Video Queue Shape

Use five lanes of five videos:

1. Buyer-intent demos.
2. Comparisons and avoid-wasting-money picks.
3. Proof / before-after transformations.
4. Trend response with an original angle.
5. Personality / credibility shorts.

Each candidate should include:

- audience pain,
- promise,
- proof asset,
- monetization route,
- originality/provenance note,
- three hooks,
- platform-safe CTA.

## Recommended Tool Direction

- Rendering/assembly: FFmpeg plus HyperFrames or Remotion.
- Captions/transcription: faster-whisper plus stable-ts or WhisperX.
- Caption correction: Subtitle Edit.
- Local narration: Kokoro or Piper first.
- Research: yt-dlp or YouTube Transcript API, sentence-transformers, BERTopic,
  KeyBERT, maintained Google Trends alternative.
- Generative video: ComfyUI/Wan/FramePack only as sidecar inserts.

## Scheduler Audit Checklist

Do not post. Verify whether the scheduler has:

- one ledger row per intended publish action,
- idempotency key per action,
- dedupe before retry,
- retry backoff/jitter,
- read-after-write confirmation,
- timezone sanity,
- structured logs,
- platform-specific failure states.

## Allowed

- Read-only repo audits.
- Dry-run/shadow scheduler checks.
- Planning docs, queue candidates, quality gate specs.
- No-write data scans.

## Forbidden Without Explicit New Approval

- Social posting or live scheduling.
- Social API writes.
- TikTok developer/app changes.
- Account mutation.
- Hidden research/posting timers.
- Queue mutation outside a separate approved write lane.

## Acceptance Evidence

- 25-video queue plan exists.
- Scheduler audit states pass/fail for each reliability item.
- Quality gate covers hook, originality, monetization path, provenance,
  AI disclosure, platform fit, and safe CTA.
- Report identifies next safe write lane, if any.

## Win Condition

The team knows exactly which 25 shorts to make next and which scheduler fixes
must pass before live posting resumes.
