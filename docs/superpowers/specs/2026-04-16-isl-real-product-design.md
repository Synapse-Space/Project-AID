# Project-AID: ISL Real Product — Design Spec

**Date:** 2026-04-16
**Branch:** `isl-real-product`
**Status:** Design approved; implementation planning next
**Owner:** yuvraj.singh@kocharsoft.com

---

## 1. Summary

Project-AID is evolving from an ASL-based Chrome-extension demo into a **real product that renders Indian Sign Language (ISL) video alongside web content**, making mainstream digital content accessible to ISL-signing deaf users in India.

The user consumes content normally (YouTube, articles, lectures, news). The extension produces an ISL video companion — grammar-aware, with honest fallbacks for out-of-vocabulary terms — that plays in a side panel synced to the content.

This is a single-developer, open-source, CPU-only, browser-first tool. MVP horizon: **4 months to beta with 20+ real deaf users**.

---

## 2. Target user and scope

### Primary user
Indian deaf users who sign ISL and want to consume mainstream digital content (educational video, news, articles) in sign. The tool exists to help them read/learn/work alongside hearing peers with less friction.

### Explicitly not the target
- Hearing learners of ISL
- Deaf/HoH users who rely on lipreading or text captions and do not sign
- Users of non-ISL sign languages (ASL, BSL, etc.)

### Content sources we support (priority order)
1. **YouTube** — largest source of Indian educational video; has a captions API
2. **Khan Academy, Coursera, Udemy** — HTML5 video with captions
3. **Selected text on any webpage** — news, Wikipedia, blog posts
4. **NPTEL / SWAYAM / DIKSHA** — government educational platforms
5. Local video files (phase 2)
6. PDF textbooks (phase 2)

### Non-goals for this 4-month release
- Mobile app (future; browser-first for MVP)
- Avatar / pose-based sign generation (Path B; out of MVP scope)
- Reverse direction (sign → text/speech)
- Sign languages other than ISL
- PDF / textbook reading
- Offline-first model bundling (post-install offline works; first install needs internet)

---

## 3. Path chosen and rationale

Three approaches were evaluated:

- **Path A — clip-stitching MVP** (chosen): replace WLASL with ISLRTC clips, add grammar-aware gloss rewriter, fingerspelling fallback, ship to real users in 3–4 months.
- **Path B — hybrid clips + 2D avatar**: same plus interpolating avatar; 8–12 months; requires ML depth.
- **Path C — pose-based generation**: research-frontier; 1.5–2 years; uncertain outcome.

**Rationale for Path A:** Real deaf users need it to *work today*, not be cutting-edge. A 70%-good tool being used by 20 people beats a 95%-good tool that never ships. Path A is designed so Path B can be bolted on later as a drop-in renderer upgrade.

---

## 4. Architecture

### High-level components

```
┌────────────────────────────────────────────────────────────┐
│ Chrome Extension (MV3) — existing scaffolding              │
│  • Popup / Side Panel / Options / Content Script           │
│  • Background service worker                               │
│  • Offscreen document (tab audio capture)                  │
└─────────────┬──────────────────────────────────────────────┘
              │ localhost HTTP
┌─────────────▼──────────────────────────────────────────────┐
│ Node/Express backend (existing)                            │
│  • Media pipeline: download / normalize / concat (FFmpeg)  │
│  • Clip cache management                                   │
└─────────────┬──────────────────────────────────────────────┘
              │ localhost HTTP
┌─────────────▼──────────────────────────────────────────────┐
│ Python FastAPI sidecar (new)                               │
│  • whisper.cpp bindings (English ASR)                      │
│  • IndicConformer / IndicWhisper (Hindi ASR)               │
│  • spaCy (English parse) + Stanza (Hindi parse)            │
│  • Gloss rewriter (rules in YAML)                          │
│  • OOV resolver                                            │
└────────────────────────────────────────────────────────────┘
```

### Why a Python sidecar
Node/Express stays for media (ffmpeg, clip routing) because the developer already knows it and the existing code is clean. Python is added only for NLP/ASR — the ecosystem (whisper.cpp bindings, spaCy, Stanza, AI4Bharat) is far stronger. The two services communicate over localhost HTTP only; no shared state.

### Data flow (summary)

```
[user action] → extension → backend /process
  → python sidecar:
       audio → ASR              (whisper.cpp / IndicConformer)
       text  → parse            (spaCy / Stanza)
       parse → gloss            (YAML rule engine)
       gloss → OOV resolve      (fingerspell / paraphrase / skip)
  → backend:
       gloss+clip-ids → fetch/cache clips → normalize → stitch → MP4
  → extension renders in side panel / companion overlay
```

---

## 5. Tech stack (open-source, CPU-only)

| Concern | Component | License | Notes |
|---|---|---|---|
| English ASR | **whisper.cpp** (`base` model) | MIT | ~0.3× real-time on CPU. Streaming mode for live. |
| Hindi/Hinglish ASR | **AI4Bharat IndicConformer / IndicWhisper** | Apache-2.0 | Best open Hindi ASR; fallback to Whisper large-v3 if packaging is painful |
| English parse | **spaCy** `en_core_web_sm` | MIT | POS, dep, lemma |
| Hindi parse | **Stanza** (Hindi model) | Apache-2.0 | POS, dep, lemma |
| Gloss rewriter | Custom rules in YAML | (our code, AGPL-3.0 proposed) | Human-readable; deaf-advisor reviewable |
| ISL clip library | **ISLRTC dictionary** (primary) + **INCLUDE** (fallback) + user-recorded seeds | TBD: verify ISLRTC redistribution rights week 1 | ~10K signs from ISLRTC |
| Video processing | **FFmpeg** via `fluent-ffmpeg` | LGPL | Existing |
| Clip transitions | FFmpeg `xfade` filter (150ms) | LGPL | New: reduces jarring cuts |
| Backend | Node/Express (existing) | MIT | No change |
| NLP sidecar | **FastAPI** + uvicorn | MIT | Thin; no state |
| Extension | Chrome MV3 (existing) | — | No change |
| Local clip cache | Filesystem + IndexedDB manifest | — | Stream on first use, background prefetch remainder |

**No GPU required anywhere.** Whisper base, spaCy, Stanza, FFmpeg all run on a mid-range laptop. Total one-time model download for the primary stack: ~400 MB (whisper-base ~142 MB + IndicConformer-small ~150 MB + spaCy en_core_web_sm ~15 MB + Stanza hi ~100 MB). If the Whisper large-v3 fallback is used for Hindi, downloads grow by ~1.5 GB and ASR latency increases on CPU. ISL clip library grows to ~5 GB on demand, not bundled.

### Components removed from current code
- AssemblyAI integration (paid, plus leaked key at `backend/server.js:40` — must rotate)
- WLASL dataset scripts (ASL; deprecated on this branch — `main` still retains them)

---

## 6. Translation / gloss pipeline

### ISL gloss conventions
ALL CAPS for signs; hyphens for compounds; `FS_` prefix for fingerspelled tokens; `+` suffix for repetition; `~` marker for paraphrased substitutions; `?` and `✗` overlay markers for questions and negation (compensating partially for missing non-manual markers).

### Six-stage pipeline

```
audio/text
   │
   ▼
[1] ASR (if audio)  → whisper.cpp (en) / IndicConformer (hi)
   │
   ▼
[2] Normalize       → lowercase, strip fillers, split into clauses
   │
   ▼
[3] Parse           → spaCy (en) / Stanza (hi) → POS + deps + lemmas
   │
   ▼
[4] Gloss rewriter  → ~30 YAML rules → ISL gloss token list
   │
   ▼
[5] OOV resolver    → fingerspell | paraphrase | skip+mark
   │
   ▼
[6] Renderer        → clip lookup → FFmpeg stitch + crossfade → MP4 / MSE
```

### Starter rule set (in YAML, deaf-advisor reviewable)

**Structural:**
- Drop `DET` (the, a, an), `AUX` (is, am, are, was, were), subordinating conjunctions
- Lemmatize verbs (`going → GO`, `ran → RUN`)
- Reorder to **SOV** (move direct object before verb)
- **Time-topic-first**: hoist temporal adjunct (`tomorrow`, `yesterday`, `today`) to clause start
- **Negation**: move `NOT` to after the verb it negates
- **Questions**: move WH-word to clause end, append `?` marker token

**Lexical:**
- Pronouns → ISL deictics (`I / YOU / HE-SHE / WE / THEY`)
- Numbers → ISL number glosses (already in ISLRTC)
- Plural via `+` repetition when contextually demanded
- Possessives `MY BOOK → I BOOK` (ISL juxtaposes)

**Hinglish-specific:**
- Per-token language ID (not per-sentence — Hinglish switches mid-clause)
- English nouns in Hindi frames: keep → lookup → fingerspell if OOV
- Hindi case markers (`का / की / में / से`) → drop

### OOV fallback decision tree

```
Is token a proper noun (PERSON / GPE)?
  → Fingerspell (e.g. FS_RAHUL, FS_DELHI)
Is it a number?
  → Use ISL number signs
Does WordNet have a synonym that is in the ISL dict?
  → Substitute + show ~ marker
Is it in the curated paraphrase map?
  → Substitute (e.g. "purchased" → BUY, "enormous" → BIG VERY)
Else:
  → Fingerspell, cache the spelling for reuse this session
```

The paraphrase map starts empty and grows from real user OOV logs + deaf-advisor review.

### Processing modes (priority order)

1. **Pre-processed video** (flagship) — fetch captions or transcribe full video once, render side-panel signer synced to playhead. Look-ahead enables best quality. Ship week 6.
2. **On-demand text** (simplest) — right-click selection → "sign it." Ship week 4.
3. **Live audio** (experimental) — tab capture, 5-sec sliding window, ~3s lag. Ship week 13.

### Known limitations (stated honestly to users)

- No non-manual markers (facial grammar). Partial fix via `?` and `✗` overlay glyphs. Full fix requires avatar (Path B).
- Rules-based gloss misses idioms. Common structures handled well; unusual sentences poorly.
- Clip-stitching lacks co-articulation. Crossfades soften but do not eliminate jarring transitions.

---

## 7. Product surfaces and UX

### Extension surfaces (existing scaffolding retained)

| Surface | Job |
|---|---|
| **Content script** (all pages) | Inject small "🖐 Sign" button into YouTube / HTML5 video controls; optional caption overlay |
| **Side panel** | Signer stage: large video, playback controls, gloss trail, flag buttons |
| **Popup** | Quick ops: paste-text-to-sign, start/stop live mode, link to side panel |
| **Context menu** | Right-click selected text → "Sign this" |
| **Options page** | Preferences: signer size/speed, language default, OOV strategy, feedback opt-in |

### Three core flows

**A. YouTube lecture (flagship)**
1. User opens video (e.g. NPTEL, Khan Academy, NCERT)
2. Content script detects `<video>`, injects "🖐 Sign" button
3. User clicks → side panel opens, progress bar "Preparing signs…"
4. Extension: use YouTube captions if present → else whisper.cpp transcription → gloss pipeline → clip pre-fetch
5. Video plays; signer syncs to playhead
6. Controls: signer speed, pause/resume (syncs both), skip-back 5s, replay current sign
7. Gloss trail: `[last] [CURRENT] [next]`; paraphrase/fingerspell tokens show `~` / `FS` badge

**B. Article in sign**
1. User selects text on any webpage
2. Right-click → "Sign this"
3. Side panel opens, sign video renders inline

**C. Live audio (degraded mode)**
1. User clicks "Start live mode" in popup on a tab with audio
2. Tab audio streams → whisper.cpp in 5-sec windows → gloss → clips
3. Side panel signer + live gloss text, ~3s lag
4. Onboarding sets expectation: "Live mode is lower quality than pre-processed."

### Feedback loop (single most important UX element)

**Per-segment controls:** 👍 / 👎 / 🏳️ flag.

**Flag categories (one tap):** wrong sign, missing sign, grammar wrong, paraphrase bad, fingerspelling unnecessary, other.

**Flag record fields:** source text chunk, gloss produced, clip IDs rendered, timestamp, anonymous session ID.

**Delivery:** local log first. Opt-in at onboarding: keep local only / send anonymized to project. Batched, never per-click.

**Review cadence:** weekly digest to deaf advisors → decide rule patch / wordmap patch / paraphrase map patch.

### Onboarding (first run)

1. "Who is this for?" — one screen, explicit: ISL-signing deaf users consuming Indian/international content.
2. "What works well / what's rough" — honest checklist.
3. "Join the feedback program?" — opt-in.
4. Permissions explained in plain language.
5. First-time model download (~400 MB) with progress bar.
6. Preferences: signer size, speed, language default.

### Meta-accessibility (the app itself)
- All controls keyboard-reachable
- High-contrast toggle
- Signer video size scales (XL option for low-vision-plus-deaf users)
- Source text shown alongside signs (bilingual cross-reference)
- No audio-only feedback ever

### Clip cache strategy
Stream-and-cache on first use. Background prefetch of remainder once cache is seeded. IndexedDB manifest + filesystem blobs. Entire pipeline runs offline after first-run setup completes.

---

## 8. Milestone plan (4 months)

### Month 1 — Foundation

| Week | Deliverable |
|---|---|
| 1 | Rotate AssemblyAI key. Proper `.env`. Swap AssemblyAI → whisper.cpp (en). Python FastAPI sidecar scaffolded. |
| 2 | ISLRTC scraper + licensing check. `isl_wordmap.json` (~10K entries). Stream-on-demand cache wired up. |
| 3 | Basic gloss rewriter: spaCy + ~15 rules. Unit tests on 50 hand-written English↔ISL pairs. |
| 4 | End-to-end smoke: paste English text → signed ISL video. Recruit 5–10 deaf testers; kickoff call. |

**Exit gate:** "I am going to school tomorrow" → recognizable ISL video. Testers have seen it and said continue / here's what's broken.

### Month 2 — Core product

| Week | Deliverable |
|---|---|
| 5 | OOV resolver. Fingerspelling clip library (ISL two-handed alphabet). Decision tree wired. |
| 6 | Pre-processed YouTube mode (flagship flow), side-panel signer synced to playhead. |
| 7 | Feedback UI: 👍/👎/flag + categories. Local log + opt-in upload endpoint. |
| 8 | **Alpha ship to testers.** Weekly feedback sessions begin. First flag-driven patches land. |

**Exit gate:** 5–10 testers using it on at least one real YouTube video each, flagging issues, patches shipping within the week.

### Month 3 — Coverage and quality

| Week | Deliverable |
|---|---|
| 9 | Hindi/Hinglish pipeline: Stanza + IndicConformer. Per-token language ID. |
| 10 | Rule refinement from Month 2 flags. Deaf advisor reviews YAML rule changes weekly. |
| 11 | Paraphrase map curation from OOV logs. Grow from 0 to ~300 common entries. |
| 12 | **Second milestone ship.** Expand cohort: 20+ testers, diverse content. |

**Exit gate:** Hindi-medium YouTube works. Paraphrase quality meaningfully above Month 2.

### Month 4 — Live mode, polish, beta release

| Week | Deliverable |
|---|---|
| 13 | Live audio mode (streaming whisper, 5-sec window, 3s lag). Labeled "experimental." |
| 14 | Onboarding flow. Options page. Meta-accessibility pass. |
| 15 | Performance tuning. Offline-first hardening. Model-version lockfile. Security audit. |
| 16 | **Beta release.** GitHub public. One NGO/school partner committed. Quiet announce to deaf community channels first. |

**Exit gate:** real tool on GitHub; 20+ deaf weekly actives; one partner org; working feedback loop.

---

## 9. Risks and mitigations

1. **ISLRTC licensing.** If redistribution is restricted, fallback order: INCLUDE dataset (263 words, public) → co-record 500 highest-frequency signs with a deaf collaborator → partner with a deaf school to co-record curriculum vocabulary. Week 1 decides this.
2. **IndicConformer packaging friction.** If Python install is painful, fall back to Whisper large-v3 for Hindi. Worse on Indian accents but unblocking.
3. **Tester consistency.** Confirm explicitly with testers: 30 min/week for 4 months. If uncertain, recruit 2× the target.
4. **Non-manual markers rejection.** Some testers will (rightly) say this isn't real ISL. Frame honestly as "captions-in-sign" MVP, not "ISL translator." Listen; let rejection drive Path B roadmap.
5. **Scope creep.** Everything not on this plan is out of scope for 4 months (see §2 non-goals).

---

## 10. Success metrics at Month 4

- **20+ weekly active deaf users**
- **≥80% of flagged issues addressed within 2 weeks** (acknowledged, categorized, triaged — not necessarily fixed)
- **≥85% of words in an average NPTEL lecture are either signed or meaningfully paraphrased** (not fingerspelled)
- **1 partner organization committed to onboarding 50+ additional users**
- **Public repo with honest README and deaf-reviewed "what this is / isn't" doc**

---

## 11. Open items (to resolve in Week 1 of implementation)

- ISLRTC email to verify redistribution rights (`ISLRTC@nic.in`); draft in hand before Monday
- Rotate leaked AssemblyAI key; decide whether to scrub from git history or leave and stop using
- Confirm tester commitment (30 min/week × 4 months) with the specific people in the developer's network
- Decide on project license (proposal: AGPL-3.0 for code; clip content under whatever ISLRTC permits)
