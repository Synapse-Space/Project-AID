# Project-AID tester kickoff

## What we're building (one sentence)
A free Chrome extension that renders Indian Sign Language alongside web video
and text, so ISL-signing deaf users can consume mainstream content (YouTube,
lectures, articles) more easily.

## What we need from you (30 min / week, 4 months)
1. Use the tool on real content weekly.
2. Flag wrong/missing/awkward signs via the in-app flag button (lands in Month 2).
3. Join a 20-minute video call every 2 weeks for feedback.

## What this is NOT (honesty is part of the product)
- Not a replacement for a human interpreter.
- Not full ISL with facial grammar yet — starts closer to signed English in SOV order.
- Missing signs are currently shown as black slides; fingerspelling fallback lands in Month 2.
- We will fix things you flag, in the open, with you named as a contributor
  if you opt in.

## Current capabilities (as of Month 1 exit)
- Text → ISL video via the popup ("Sign it" button).
- ~2,971 signs in the word map, sourced from ISLRTC's official YouTube dictionary playlists.
- Grammar-aware gloss rewriter (SOV reorder, time-first, negation move, WH-end, plural marking, etc.).
- Whisper ASR wired (local, CPU, no cloud dependency) for future live-audio mode.
- Clips stream from YouTube (no redistribution — standard embedding).

## Known limitations (at Month 1 exit)
- `/sign` currently tries to fetch YouTube URLs as direct MP4s; a yt-dlp
  resolver layer is needed for production playback (Month 2 scope).
- Some gold English→ISL pairs (locative motion sentences like "I go to school tomorrow")
  produce slightly different token order than a fluent ISL signer would expect.
  Deaf-advisor review is on the roadmap.
- No non-manual markers (facial grammar). Overlay `?` and `✗` glyphs partially
  compensate for question and negation mood; full fix requires an avatar renderer (Path B).

## Recruitment outreach template

**Subject:** Help build a free ISL tool for deaf students — 30 min/week

Hi [name],

I'm building an open-source Chrome extension that turns YouTube lectures and
web articles into ISL video for deaf users. I'm looking for 5–10 ISL signers
willing to test weekly and tell me what's wrong so I can fix it.

Commitment: ~30 min/week for 4 months, one 20-min call every 2 weeks.
No tech skills needed beyond using Chrome. You'll be credited (if you want) in
the public release.

Would you be open to a 15-min intro call this week?

— Yuvraj

## Week 0 kickoff call agenda (60 min)

1. Who everyone is — signers and developer (10)
2. Demo of the current MVP (sign "I drink water") (10)
3. Honest limitations walkthrough (10)
4. Feedback tooling — how to flag (10)
5. Testing cadence + expectations (10)
6. Q&A (10)

## Consent & data handling (for the kickoff call)

- Testing is voluntary. You can leave any time, no reason needed.
- All feedback is opt-in to share with the project. "Keep local only" is the
  default; uploading flags to the project requires you clicking the checkbox.
- We will never attach your name to a flag without explicit permission.
- Credits (in the public README) are also opt-in.

## Developer contact

- Email: yuvraj.singh@kocharsoft.com
- Repo: `github.com/Synapse-Space/Project-AID` (branch `isl-real-product`)
