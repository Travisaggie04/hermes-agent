# Video Production Decision Memo - 2026-06-12

This memo covers the Shorts and Long-form video projects for the overnight
Mission Control run. It is planning evidence only. It does not approve posting,
scheduling, account mutation, hidden workers, timers, paid tools, or customer
facing changes.

## Current Policy Constraints

YouTube's current channel monetization policy is the most important constraint:
monetized content must be original and authentic, and should not be
mass-produced, repetitive, or made from generic AI templates with minimal
original insight.

That changes the optimization target. The system should not maximize raw video
count first. It should maximize repeatable originality:

- materially varied substance from video to video,
- clear human-readable thesis or story,
- original commentary, narration, or perspective,
- explicit quality gates before anything reaches a queue,
- evidence capture so weak formats can be killed quickly.

TikTok direct posting also remains a separate approval problem. TikTok's Content
Posting API requires app approval for `video.publish`, user authorization for
that scope, and audit before public visibility is unrestricted. TikTok should
stay disabled until that approval lane is reopened explicitly.

## Toolchain Signal

Do not build the next video system around OpenAI Sora. OpenAI's help center says
the Sora web/app experience was discontinued on 2026-04-26 and the Sora API is
scheduled to be discontinued on 2026-09-24.

Current toolchain candidates should be split into two classes:

1. Deterministic production tools for repeatability:
   - DaVinci Resolve for edit, audio, color, and final assembly.
   - Moho for reusable character rigs if the adult animated path wins.
   - Inkscape for vector assets and clean reusable art.
   - Cavalry for motion graphics, data visuals, and explainers.
   - Local scripts for packaging, captions, metadata, quality checks, and
     evidence records.

2. Generative video services for controlled proofs, not the source of truth:
   - Runway API is relevant because the current API docs expose image-to-video
     generation and current model access.
   - Google Veo is relevant because Google DeepMind positions Veo 3.1 as a
     cinematic video model with native audio and improved prompt adherence.
   - Any generative service must be evaluated with cost, rights, repeatability,
     content policy, and API reliability before production use.

## Decision

Use a Shorts-first quality engine plus one long-form proof path.

Do not attempt full long-form production tonight. The previous failures point to
too many unknowns at once: visual style, asset continuity, narration pacing,
scene assembly, queue ledger, metadata contract, and scheduler all competing for
attention.

The next money-oriented path should be:

1. Reconcile the existing Shorts queue and generate a 25-video slate plan that
   passes Lane A quality gates.
2. Pick one long-form proof direction and make a 10-15 second proof, not a full
   episode.
3. Convert the winning proof method into reusable assets and checks before
   generating volume.

## Shorts Plan

Shorts should become the fast experimental loop.

Next 25-video slate structure:

- 5 formats x 5 topics, not 25 one-off prompts.
- Each format must have a repeatable storyboard, voice style, thumbnail/title
  pattern, and quality checklist.
- Each topic must have a distinct thesis, evidence hook, and viewer payoff.
- All outputs must include a review packet before scheduling.

Recommended first format families:

- "The hidden mechanism": one surprising system behind a normal thing.
- "Bad advice teardown": why a common internet claim fails.
- "Before/after proof": show a concrete transformation or comparison.
- "Tiny business autopsy": one failed or odd business model explained quickly.
- "Impossible but true": visually strong factual curiosities, with strict
  sourcing and no fake-footage framing.

Minimum quality gates:

- explicit original thesis,
- no generic AI template language,
- no reused clips without transformative narration,
- hook visible in first 2 seconds,
- one memorable visual beat,
- clean captions,
- platform-safe title/description,
- queue record links back to source package and quality lock.

The next Shorts lane should answer:

- why the queue reporter says YouTube/Facebook have missing next-five-day
  slots despite existing queued/scheduled records,
- which of the seven backfill candidates are still usable,
- which 18 review-only packages can be promoted only if they receive missing
  quality fields,
- which 25 new packages should be generated if refill is needed.

## Long-Form Plan

Long-form should not be volume-driven yet. It needs one proof that answers a
specific production question.

Ranked options:

1. Adult animated Signal Room explainer
   - Best continuity with existing Moho/character-rig work.
   - Best chance to become reusable if rig, mouth shapes, and scene templates
     are solved.
   - Risk: character acting and asset consistency can consume a lot of time.

2. Impossible Footage, Shorts-first
   - Strong hook potential and good fit for generative video tests.
   - Better treated as 30-60 second Shorts first, then expanded only if metrics
     prove retention.
   - Risk: must be clearly framed as reconstruction/visualization, not real
     footage.

3. Faceless documentary/explainer
   - Easiest to assemble with deterministic tools.
   - Good fit for Cavalry, Inkscape, DaVinci, sourced narration, and motion
     graphics.
   - Risk: crowded niche; quality bar is high for retention.

4. Business/finance/news
   - Monetization potential exists, but research and accuracy burden is high.
   - Should wait until the autoresearch/evidence system is stronger.

Recommended proof:

- Build a 10-15 second adult animated Signal Room mechanism proof.
- Requirements:
  - one reusable adult character pose or rig,
  - one deterministic mechanism animation,
  - one clean narration beat,
  - final assembly in DaVinci or equivalent reproducible pipeline,
  - review packet documenting exact tools, render steps, failure points, and
    whether the method can scale.

Fallback if Moho/local rigging blocks:

- Build a 10-15 second faceless mechanism explainer using Inkscape + Cavalry or
  scriptable motion graphics, then compare retention potential against the
  animated character route.

## Autoresearch Loop

Build this as a manual-start record-backed process first.

Do not add a hidden timer tonight.

Stages:

1. Collect metrics:
   - views,
   - retention,
   - click-through rate,
   - watch time,
   - comments/saves/shares where available,
   - platform and publish time.

2. Label content:
   - format family,
   - topic,
   - hook type,
   - visual type,
   - narration style,
   - duration,
   - quality gate result.

3. Produce findings:
   - winning formats,
   - weak formats,
   - platform-specific differences,
   - quality defects,
   - next 10 topic hypotheses.

4. Require approval before generation or scheduling:
   - no automatic posting,
   - no hidden scheduler change,
   - no TikTok mutation,
   - no account/API changes.

Later, if stable, the loop can become scheduled only after Mission Control has:

- visible run records,
- stop controls,
- duplicate protection,
- platform gates,
- budget/cost limits,
- explicit approval states.

## Morning Definition Of Done

By morning, a good outcome is not "lots of videos posted." A good outcome is:

- Shorts queue reconciliation complete,
- 25-video slate plan drafted,
- one long-form proof path selected,
- toolchain shortlist documented,
- no live posting or account mutation performed,
- next lanes visible in Mission Control.

## Sources Checked

- YouTube channel monetization policies:
  https://support.google.com/youtube/answer/1311392
- TikTok Content Posting API:
  https://developers.tiktok.com/doc/content-posting-api-get-started
- OpenAI Sora discontinuation:
  https://help.openai.com/en/articles/20001152-what-to-know-about-the-sora-discontinuation
- Runway API docs:
  https://docs.dev.runwayml.com/
- Google DeepMind Veo:
  https://deepmind.google/models/veo/
