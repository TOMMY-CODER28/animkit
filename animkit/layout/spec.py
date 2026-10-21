"""Validated intermediate scene specification.

The AI (or a human) describes WHAT each stage contains and HOW components
relate; the layout system decides coordinates. A spec is a list of stages;
each stage lists components with lifecycle + transition intent, a layout
template, timing, and any explicitly permitted overlaps.

Constraint vocabulary (component-level, optional — templates add their own):
  ("contain", region_name)            keep inside region (margin applied)
  ("centerline_y", [ids])             shared horizontal centreline
  ("equal_spacing_x", [ids], mode)    mode 'centers' | 'gaps'
  ("min_gap_x", a, b, g)              a fully left of b with gap >= g
  ("min_gap_y", a, b, g)              a fully below b with gap >= g
  ("order_x", [ids], gap)             left-to-right order with min gap
  ("center_in", region, axis)         centre within region ('x'/'y'/'both')

Custom escape hatch: stage.template == "custom" requires stage.custom_x /
custom_y dicts (id -> internal coordinates); custom layouts still pass
geometry validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from animkit.layout.geom import REGION_NAMES

LIFECYCLE = frozenset({"persistent", "entering", "changing", "leaving", "temporary"})
TRANSITIONS = frozenset({"fade_in", "write", "grow", "transform", "move", "scale", "reveal", "static"})
CTYPES = frozenset({"matrix", "equation", "text", "arrow", "callout", "highlight", "nav", "title", "caption"})
TEMPLATES = frozenset({
    "single_center", "two_columns", "three_columns", "input_op_output",
    "operands_result", "main_callout", "equation_explanation", "custom",
})
DENSITIES = frozenset({"comfortable", "compact"})


@dataclass
class ComponentSpec:
    id: str
    ctype: str
    region: str = "main"
    owner: str | None = None                 # logical owner (labels, highlights)
    # content, per ctype:
    #   matrix:   {"values": [[...]], "label": str|None, "nd": int, "color": "#hex"|None,
    #              "label_side": "above"|"below"|"left"|"right"}
    #   equation: {"parts": [(text, color|None), ...], "font_size": float}
    #   text:     {"text": str, "font_size": float, "color": "#hex"|None}
    #   nav:      {"stages": [names], "active": int}
    #   highlight:{"target": comp_id, "part": ["row"|"col"|"entry", i, (j)]}
    #   arrow:    {"from": (id, anchor), "to": (id, anchor), "label": str|None}
    #   callout:  {"text": str, "target": id, "side": "right"|"left"}
    content: dict = field(default_factory=dict)
    constraints: list = field(default_factory=list)   # required
    preferred: list = field(default_factory=list)     # soft ("stay", ("near", id, dx, dy), ("center_in", region))
    min_readable: float = 0.16                        # min text height, units


@dataclass
class StageSpec:
    id: str
    template: str
    components: dict[str, str]                    # id -> lifecycle
    transition: dict[str, str] = field(default_factory=dict)   # id -> TRANSITIONS (default fade_in)
    timing: dict = field(default_factory=dict)    # {"move": 1.0, "hold": 0.8, "exit": 0.5}
    permitted_overlaps: list = field(default_factory=list)     # [(id_a, id_b), ...]
    regions_used: list | None = None              # default: derived from components
    annotation_side: str = "bottom"
    custom_x: dict | None = None                  # for template="custom"
    custom_y: dict | None = None
    caption: str | None = None                    # shorthand: caption component
    title: str | None = None                      # shorthand: title component
    # template tuning (optional):
    min_gap: float = 0.55                         # default minimum gap between main comps
    operands: list = field(default_factory=list)  # operands_result: ids of operands
    result: str | None = None                     # operands_result: the result id
    equation: str | None = None                   # equation_explanation: the equation id
    callouts: list = field(default_factory=list)  # main_callout: ids placed in annotation
    narration: str | None = None                  # spoken text for this stage (TTS)


@dataclass
class SceneSpec:
    name: str
    aspect: float = 16 / 9
    density: str = "comfortable"
    debug: bool = False
    output_dir: str | None = None                 # where reports/stage times are written
    audio: dict | None = None                     # {"voice","speed","lang","pad"} enables narration
    stages: list = field(default_factory=list)    # [StageSpec]
    components: dict = field(default_factory=dict)  # id -> ComponentSpec (all stages)


def validate_spec(spec: SceneSpec) -> tuple[list[str], list[str]]:
    """Structural validation. Returns (errors, warnings) with actionable text."""
    errors: list[str] = []
    warnings: list[str] = []

    if not spec.stages:
        errors.append("spec has no stages — add at least one StageSpec")
    if spec.density not in DENSITIES:
        errors.append(f"density {spec.density!r} not in {sorted(DENSITIES)}")
    if not (0.5 <= spec.aspect <= 3.5):
        errors.append(f"aspect {spec.aspect:.3f} looks wrong (width/height, e.g. 1.778 for 16:9)")

    for cid, comp in spec.components.items():
        if comp.ctype not in CTYPES:
            errors.append(f"component {cid!r}: unknown ctype {comp.ctype!r} (known: {sorted(CTYPES)})")
        if comp.region not in REGION_NAMES:
            errors.append(f"component {cid!r}: region {comp.region!r} not in {sorted(REGION_NAMES)}")
        if comp.ctype == "matrix":
            values = comp.content.get("values")
            if not values or not isinstance(values, list) or not isinstance(values[0], list):
                errors.append(f"component {cid!r}: matrix content needs 'values': [[...], [...]]")
            elif len({len(r) for r in values}) != 1:
                errors.append(f"component {cid!r}: matrix rows must all have the same length")
        if comp.ctype == "highlight":
            target = comp.content.get("target")
            if target not in spec.components:
                errors.append(f"component {cid!r}: highlight target {target!r} is not a declared component")
            elif spec.components[target].ctype != "matrix":
                errors.append(f"component {cid!r}: highlight targets {target!r} which is not a matrix")
        if comp.ctype == "callout":
            if comp.content.get("target") not in spec.components:
                errors.append(f"component {cid!r}: callout target {comp.content.get('target')!r} not declared")
        if comp.owner and comp.owner not in spec.components:
            errors.append(f"component {cid!r}: owner {comp.owner!r} not declared")

    seen_stages = set()
    for stage in spec.stages:
        sid = stage.id
        if sid in seen_stages:
            errors.append(f"stage id {sid!r} repeated")
        seen_stages.add(sid)
        if stage.template not in TEMPLATES:
            errors.append(f"stage {sid!r}: unknown template {stage.template!r} (known: {sorted(TEMPLATES)})")
        if stage.template == "custom" and not (stage.custom_x and stage.custom_y):
            errors.append(f"stage {sid!r}: template 'custom' needs custom_x and custom_y position maps")
        for cid, life in stage.components.items():
            if life not in LIFECYCLE:
                errors.append(f"stage {sid!r}: component {cid!r} lifecycle {life!r} not in {sorted(LIFECYCLE)}")
            if cid not in spec.components:
                errors.append(f"stage {sid!r}: component {cid!r} used but never declared")
        for cid, intent in stage.transition.items():
            if intent not in TRANSITIONS:
                errors.append(f"stage {sid!r}: transition {intent!r} for {cid!r} not in {sorted(TRANSITIONS)}")
            if cid not in stage.components:
                errors.append(f"stage {sid!r}: transition given for {cid!r} which is not in this stage")
        for pair in stage.permitted_overlaps:
            if len(pair) != 2 or pair[0] not in stage.components or pair[1] not in stage.components:
                errors.append(
                    f"stage {sid!r}: permitted_overlap {pair!r} must be a pair of component ids present in the stage"
                )
        for key, value in stage.timing.items():
            if key not in ("move", "hold", "exit", "enter") or not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"stage {sid!r}: timing[{key!r}] must be a positive number (keys: move/hold/exit/enter)")
        if stage.regions_used is not None:
            unknown = set(stage.regions_used) - REGION_NAMES
            if unknown:
                errors.append(f"stage {sid!r}: regions_used has unknown names {sorted(unknown)}")

    # lifecycle continuity: a component cannot re-enter after leaving
    left = set()
    for stage in spec.stages:
        for cid, life in stage.components.items():
            if life == "leaving":
                left.add(cid)
            elif life in ("entering",) and cid in left:
                errors.append(
                    f"stage {stage.id!r}: component {cid!r} re-enters after leaving — "
                    f"use a new id (e.g. {cid}_2) to keep the registry honest"
                )
        for cid in stage.components:
            if cid in left and stage.components[cid] not in ("leaving",):
                errors.append(f"stage {stage.id!r}: component {cid!r} is listed after leaving without lifecycle 'leaving'")

    return errors, warnings


def derived_regions_used(spec: SceneSpec, stage: StageSpec) -> set[str]:
    """Bands the stage touches, from its components (+ caption/title shorthand)."""
    used = {"main"}
    for cid in stage.components:
        comp = spec.components[cid]
        if comp.ctype in ("title", "nav", "caption"):
            used.add(comp.ctype)
        elif comp.region in ("annotation",) and comp.ctype not in ("arrow", "highlight"):
            used.add("annotation")
    if stage.caption:
        used.add("caption")
    if stage.title:
        used.add("title")
    if stage.regions_used:
        used |= set(stage.regions_used)
    return used
