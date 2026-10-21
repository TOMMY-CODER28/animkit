# Production workflow — editing, checking, delivering

Rules that keep animation work and engine work separated, make required
checks authoritative, and tie every claim in a completion report to evidence.
The hooks (`hooks/pre-commit`, `hooks/pre-push`, active via
`git config core.hooksPath hooks`) enforce the check parts mechanically.

## 1. Separate animation changes from engine changes

**Animation production** touches only:
`script.md` · `scene.py` · `project.json` · existing templates/settings
(`theme.py`, `animkit/layout/components.py` settings passed via content dicts).

If an animation exposes a **shared defect** (a bug in `animkit/layout/`,
`animkit/audio/`, the CLI, or templates):
1. Record the failure (in the example's storyboard.md or the run notes).
2. Create a separate engine patch — do not mix it into the animation commit.
3. Add a focused regression check (tests/test_layout.py or test_audio.py)
   that fails before the patch and passes after.
4. Verify another relevant example still behaves correctly.
5. Commit the engine patch as its own commit.

Never change shared behavior solely to satisfy one example's duration or
appearance — adjust that example's spec settings instead
(`timing.hold`, `audio.pad`, `speed`, `entry_size`, `min_gap`, density).

## 2. Checks are authoritative

- Run required checks ONLY through the runner:
  `python tools/check.py --fast` (pre-commit set) / `python tools/check.py`
  (full set, pre-push). The runner captures each suite's real exit code,
  writes complete logs under `logs/`, and prints one-line summaries.
- Never pipe a test through `tail`/`grep` and read the filter's exit status.
  (This exact mistake shipped once; the runner exists to prevent it.)
- A failed required check BLOCKS commit (pre-commit, fast set) and push
  (pre-push, full set). Failure status stays visible in
  `logs/last_run.json` until the affected check passes.
- Do not disable checks, skip tests, or broaden ignore rules to make
  validation pass. Fix the cause.

## 3. Timing semantics (documented, not folklore)

| term | meaning | where set |
|---|---|---|
| narration start offset | 0 — the narration track places each stage's WAV exactly at that stage's `t_start` (the mux aligns to stage_times.json) | fixed by the mux |
| minimum visual duration | with audio: `narration + audio.pad + timing.hold`; without: scripted enter+exit+hold | `StageSpec.timing`, `spec.audio.pad` |
| pause after narration | `audio.pad` (default 0.35 s; narrative examples use 0.8 s) plus the scripted hold — sink-in time after speech ends | `spec.audio.pad`, `timing.hold` |
| voice speed | Kokoro speed multiplier: 1.0 native, 0.9 slower/clearer (beginner examples) | `spec.audio.speed`, project.json `audio.speed` |

Adjust pacing through those settings. Changing the compose sync logic itself
is an engine change (rule 1) and needs a migration note + regression check.

## 4. Narration vs the actual scene timeline

`animkit audio <project> --verify` checks every narrated stage against
stage_times.json (the measured timeline, not the spec's intentions):
narration starts within its stage · ends before the stage leaves · the
requested pause remains after it · the final video includes the complete
visual ending · the exported video has an audio stream · coverage is complete
(no missing or orphan narration). Failures name the stage and the numbers.

## 5. Controlled edits

- Prefer focused Edit-tool patches. If a scripted (regex/string) replacement
  is necessary, verify the expected match count BEFORE writing (assert the
  number of replacements made).
- Review `git diff` after each logical change; stage only files belonging to
  the task (`git add <paths>`, not blanket adds) unless the change is
  repo-wide by design.
- Portable manifests and reproduction instructions use paths RELATIVE to the
  project root (audio manifests do; REPRODUCE.md is machine-local and
  gitignored).

## 6. Visual review gate (after every preview)

Inspect: one settled frame per stage · frames around stage boundaries · the
final hold · content size at viewing scale (readable at 480p ⇒ fine at 1080p).
Reject: unreadable equations/matrices, excessive unused space, clipping,
detached labels, stale objects. Correct presentation through component and
template settings first (entry_size, label_side, template choice, density) —
not through ad-hoc coordinates.

## 7. Audio review is separate from video review

`animkit audio <project> --verify` covers the mechanical checks (stream,
placement, coverage, pauses, complete ending). Nonzero audio energy is NOT
proof of correct speech. When listening is available, listen to the first and
last sentences of the final MP4. When it is not available, say so in the
completion report — this environment currently CANNOT listen; that limitation
must be stated in every narrated delivery.

## 8. Deliver exactly what was checked

Sequence: edit → relevant checks (runner) → preview → inspect → revise →
final render → verify final output (audio --verify) → package (deliver) →
verify the packaged output (streams/duration of the DELIVERED file).
Record in the report: source revision (git hash), relevant settings, output
hashes. Deliver prefers the narrated mux when present — confirm packaging
used the verified video. If code, settings, narration, or export processing
change afterward, repeat the affected checks. An earlier preview never
verifies a later render.

## 9. Completion report template

```
Files changed: <list>
Engine changes: <none | list + why + regression test>
Checks run: <runner output — exact sets and results; never "all tests
  passed" unless tools/check.py full ran and passed>
Frames inspected: <which frames, from which render>
Audio checks: <audio --verify results + listening status/limitation>
Remaining limitations: <list>
Final deliverable: <path> (<revision>, <settings>)
```
