# Turning requests into briefs

The brief (`brief.md` in the project) is a contract: it pins down what "done"
means before any code exists. Fill every section of the template.

## Vague request → precise brief

1. **List the ideas the user actually named.** "Explain FFT denoising" contains:
   signal, transform, spectrum, filter, reconstruction. If you can't list the
   ideas, the request is too vague to animate — ask.
2. **Choose a duration class** from content, not preference:
   1 idea ≈ 8–15 s; 2–3 ideas ≈ 15–25 s; a pipeline/process ≈ 25–40 s.
3. **Pin the technical facts and their source.** Every equation, parameter and
   constant gets a line in "Mathematical / technical content". If the user gave
   no numbers, pick canonical ones (integer periods for waves, det=1 matrices)
   and log it as an assumption.
4. **Decide what is *shown*, not just said.** Each idea needs a visual verb:
   draw, transform, highlight, annotate. An idea with no visual verb is a
   caption, not an animation.

## Ask vs. assume

Ask the user only when both are true: (a) the answer changes the structure of
the animation (different scene count, different math), and (b) you cannot pick
a defensible default. Otherwise assume, and write it in the assumptions log.

Ask-worthy: wrong-math risk (user's stated equation contradicts itself),
audience level (changes depth substantially), target duration the user cares
about (e.g. for a lecture slot), branding/style requirements.

Assume-worthy: exact numbers (canonical values), colors (theme), background,
pacing, which of two equivalent visual metaphors to use, order of sub-ideas
(the user's sentence order is the default).

## Assumptions log

Every assumption is a row: question it answers, assumption taken, cost to
change later. Cheap-to-change assumptions (colors, labels, timing) don't need
asking; expensive ones (visual metaphor, math content) do.

## Success criteria are testable

Write criteria you can check on extracted frames: "ĵ's tip at grid (1,1)",
"two spectrum peaks", "labels not overlapping", "no element within 0.3 units
of frame edge". "Looks nice" is not a criterion.
