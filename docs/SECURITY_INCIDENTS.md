# Security incidents

A chronological log of security incidents, key rotations, and remediations for Project-AID.

---

## 2026-04-16 — Leaked AssemblyAI API key

**Key prefix:** `95b1e4b1…` (redacted suffix)

**Exposure:**
- Committed to git history as a literal string in `backend/server.js:40`.
- Present in commits `4790789` (initial integration) through `dae2395`.
- Public in the working tree until `9622bea` removed it.

**Scope:** Transcription API only. No billing-level or admin-level access.

**Remediation:**
1. **Key rotated on AssemblyAI dashboard** (manual, out-of-band). Old key revoked so even historical git access cannot use it.
2. Hardcoded key removed from `backend/server.js` in commit `9622bea`. New `.env`-based configuration.
3. `/transcribe` endpoint will be re-implemented in Task 6 as a proxy to a local Python sidecar (no third-party key required).

**Git-history scrub:** deferred decision. The leaked key remains reachable via `git log -p` for historical commits but is inert once rotated. Scrubbing requires a coordinated force-push and rewrite; revisit before the branch merges to `main`.

**Preventative:** `.env.example` now carries only non-secret variable names. `.env` is git-ignored. Future credentials should be committed only via `.env.example` templates.
