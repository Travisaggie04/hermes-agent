---
name: stop-slop
description: >
  Checklist-only writing review for cutting formulaic AI prose while preserving
  the user's facts, constraints, citations, commands, code, terminology, and
  safety warnings. Use when the user asks to review, polish, de-slop, tighten,
  or sanity-check a draft, document, release note, web copy, or agent handoff.
version: 1.0.0
author: Hermes Agent (adapted from hardikpandya/stop-slop concepts)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [communication, writing, editing, checklist, prose-review, anti-ai-slop]
    category: communication
    homepage: https://github.com/hardikpandya/stop-slop
---

# Stop Slop Writing Review

Use this optional skill as a checklist for reviewing or lightly editing user-provided writing. It is not a global voice rule, automatic rewriting system, lint daemon, or replacement for technical review.

## When to Use

- The user asks to review, polish, de-slop, tighten, or sanity-check prose.
- The draft is a document, release note, blog/web copy, email, memo, proposal, PR description, or agent handoff.
- The goal is clearer writing without changing the underlying content.

## Do Not Use When

- Technical correctness matters more than polish.
- The user asked for a formal, legal, medical, regulatory, academic, or standards-driven style.
- Strict terminology, citations, commands, code, or safety wording must remain exactly as written.
- A terse style would remove necessary context, nuance, caveats, or implementation detail.
- The user wants a full voice match or humanized rewrite; use a dedicated humanizer/voice skill if available.

## Review Rules

- Preserve facts, constraints, citations, commands, code, filenames, numbers, dates, and safety warnings.
- Do not invent evidence, claims, benefits, risks, or emotional tone.
- Prefer direct, specific statements over vague claims of importance.
- Use active voice and name the actor when it clarifies responsibility, but do not ban passive voice.
- Vary sentence length and structure without making the draft theatrical.
- Keep useful context. Do not make engineering handoffs artificially terse.
- Treat adverbs, passive voice, and em dashes as context-dependent choices, not automatic defects.

## Checklist

Score each area from 0 to 2:

- **Directness:** Does the draft get to the point without throat-clearing, generic setup, or ceremonial conclusions?
- **Specificity:** Are claims tied to concrete facts, examples, owners, dates, outcomes, or constraints?
- **Actor/action clarity:** Is it clear who did what, who needs to act, and what changed?
- **Rhythm/structure variety:** Do sentence openings, lengths, and contrast patterns feel varied rather than mechanical?
- **Trust/calibration:** Are claims appropriately scoped, with uncertainty, risk, and limits stated plainly?
- **Density:** Does each sentence carry useful information without padding or repeated meaning?

Suggested output:

1. Give the score out of 12.
2. List the 3-5 highest-value edits.
3. Provide a revised version only if the user asked for edits or if a short rewrite is clearly useful.

## Common Anti-Patterns

- Throat-clearing: "In today's fast-paced world", "It is important to note", "At its core".
- Inflated significance: "serves as a testament", "marks a pivotal moment", "underscores the importance".
- Mechanical contrast: "not just X, but Y", "from X to Y", "whether A or B".
- Vague praise: "robust", "seamless", "powerful", "cutting-edge" without proof.
- Filler endings: broad future-looking conclusions that add no decision, next step, or evidence.

## Provenance

This skill is adapted from concepts in `hardikpandya/stop-slop`, whose MIT license was noted in the Hermes external repo watchlist. It is a small Hermes-native checklist, not a wholesale import of upstream content.
