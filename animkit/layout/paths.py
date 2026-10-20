"""Movement-path estimation: collisions ALONG transitions, not just endpoints.

For each component that moves in a transition, sample its bounding box at k
points on the (linear) path and check against every other visible component's
box at the same phase. Overlaps that are declared, ownership-related, or of an
exempt class (arrows/highlights on their targets) are skipped.

This is an estimate: real animations may use arcs. It runs before animating so
problems surface as actionable warnings (stagger, sequence, fade) rather than
as visual surprises. Problematic transitions can then be densely sampled from
the rendered preview (see validate.rendered).
"""

from __future__ import annotations

from animkit.layout.geom import Box

EXEMPT_CLASS_PAIRS = {
    frozenset({"arrow", "block"}),
    frozenset({"highlight", "block"}),
    frozenset({"connector", "block"}),
    frozenset({"arrow", "label"}),
    frozenset({"highlight", "label"}),
}


def _exempt(a: str, b: str, declared: set[frozenset], owners: dict[str, str | None]) -> bool:
    if frozenset((a, b)) in declared:
        return True
    ca, cb = owners.get(a), owners.get(b)
    if ca and (ca == b or ca == cb):
        return True
    if cb and cb == a:
        return True
    pair = frozenset((_class_of(a), _class_of(b)))
    return pair in EXEMPT_CLASS_PAIRS


_classes: dict[str, str] = {}


def _class_of(cid: str) -> str:
    return _classes.get(cid, "block")


def check_paths(moves: dict[str, tuple[tuple[float, float], tuple[float, float]]],
                boxes: dict[str, Box], declared: list, comp_meta: dict) -> list[str]:
    """moves: id -> (start_xy, end_xy). Returns human-readable collision notes."""
    _classes.clear()
    _classes.update({cid: meta.overlap_class for cid, meta in comp_meta.items()})
    declared_set = {frozenset(p) for p in declared}
    owners = {cid: meta.owner for cid, meta in comp_meta.items()}
    static = {cid: b for cid, b in boxes.items() if cid not in moves}
    notes = []
    k = 5
    for cid, (start, end) in moves.items():
        box = boxes[cid]
        for phase in range(1, k):
            t = phase / k
            cx = start[0] + (end[0] - start[0]) * t
            cy = start[1] + (end[1] - start[1]) * t
            moving = box.moved_to(cx, cy)
            for other_id, other in static.items():
                if _exempt(cid, other_id, declared_set, owners):
                    continue
                if moving.overlaps(other, pad=0.04):
                    notes.append(
                        f"path collision: {cid!r} sweeps within 0.04 of {other_id!r} "
                        f"at t={t:.2f} of its move — stagger the move, change order, "
                        f"or declare permitted_overlaps [({cid!r}, {other_id!r})]"
                    )
                    break
    return notes
