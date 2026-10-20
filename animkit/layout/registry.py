"""Stage registry: semantic component IDs -> live rendered objects.

Lifecycle rules enforced here (fixing the stale-object defect class):
  - Every visible object belongs to exactly one registered Component; owned
    children (labels, highlights, connectors) live INSIDE the owner's group,
    so fading/removing the owner takes them along.
  - leaving: FadeOut (ManimGL's FadeOut removes the mobject from the scene)
    + updater cleanup + temp-object sweep. Registry entry dropped.
  - changing with intent 'transform': ReplacementTransform(old, new) —
    ManimGL swaps the scene objects, so the registry re-points id -> new.
  - changing with intent 'move': the SAME group animates to the solved
    position (identity preserved, updaters keep working).
  - persistent: position verified against the solved layout; moved only if
    the solver says so.
  - temporary: enter this stage, leave automatically at stage end.
  - A post-stage sweep compares scene.mobjects against the registry and
    reports anything unregistered (stale objects) instead of leaking them.

The scene is accessed through a narrow interface (play/add/remove/mobjects)
so tests can use a FakeScene without a renderer.
"""

from __future__ import annotations

from manimlib import *  # noqa: F401,F403  (FadeOut/FadeIn/Write/ReplacementTransform...)

from animkit.layout.components import Component, MAKERS, make_highlight_component, make_arrow_component, make_callout_component


class StageRegistry:
    def __init__(self, spec):
        self.spec = spec
        self.components: dict[str, Component] = {}
        self.temp_objects: dict[str, list] = {}       # stage id -> [Component]
        self.stale_report: list[str] = []
        self.stage_log: list[dict] = []

    # -- building ------------------------------------------------------------
    def build(self, cid: str, solved_pos: tuple[float, float] | None = None,
              anchors: dict | None = None, peers: dict | None = None) -> Component:
        cs = self.spec.components[cid]
        target_of = lambda t: (peers or {}).get(t) or self.components[t]  # noqa: E731
        if cs.ctype == "highlight":
            comp = make_highlight_component(cs, target=target_of(cs.content["target"]))
        elif cs.ctype == "arrow":
            comp = make_arrow_component(cs, anchors or {})
        elif cs.ctype == "callout":
            comp = make_callout_component(cs, target=target_of(cs.content["target"]))
        else:
            comp = MAKERS[cs.ctype](cs)
        if comp.ctype in ("title", "nav", "caption"):
            comp.region = comp.ctype  # band components validate against their band
        if solved_pos is not None and comp.overlap_class != "highlight":
            comp.group.move_to([solved_pos[0], solved_pos[1], 0])
        return comp

    # -- stage application -----------------------------------------------------
    def apply_stage(self, scene, stage, positions, timings, build_extra=None) -> dict:
        """Perform one stage's animations. Returns a record for the report.

        positions: id -> (x, y) from the solver, for ids visible this stage.
        timings:   {"enter": t, "move": t, "exit": t, "hold": t}
        """
        record = {"stage": stage.id, "actions": [], "issues": []}
        entering, leaving, changing, persistent, temporary = [], [], [], [], []
        for cid, life in stage.components.items():
            {"entering": entering, "leaving": leaving, "changing": changing,
             "persistent": persistent, "temporary": temporary}[life].append(cid)

        # implicit leaving: registered components this stage doesn't mention
        # leave now — nothing lingers across an unmentioned boundary
        implicit = [cid for cid in self.components
                    if cid not in stage.components and cid not in leaving]
        if implicit:
            leaving = leaving + implicit
            record["actions"].append(f"implicit leave: {implicit}")

        # 1) leaving (with owned children inside their groups)
        if leaving:
            anims = []
            for cid in leaving:
                comp = self.components.pop(cid, None)
                if comp is None:
                    record["issues"].append(f"leaving {cid!r} was never registered")
                    continue
                comp.group.clear_updaters()
                anims.append(FadeOut(comp.group))
            if anims:
                scene.play(*anims, run_time=timings.get("exit", 0.5))
                record["actions"].append(f"leave: {leaving}")

        # 2) changing
        move_t = timings.get("move", 1.0)
        transform_ids, move_ids = [], []
        for cid in changing:
            intent = stage.transition.get(cid, "move")
            (transform_ids if intent == "transform" else move_ids).append(cid)
        for cid in transform_ids:
            new_comp = (build_extra or self.build)(cid, positions.get(cid))
            old = self.components.get(cid)
            if old is None:
                scene.add(new_comp.group)
            else:
                old.group.clear_updaters()
                scene.play(ReplacementTransform(old.group, new_comp.group), run_time=move_t)
            self.components[cid] = new_comp
            record["actions"].append(f"transform: {cid}")
        if move_ids:
            anims = []
            for cid in move_ids:
                comp = self.components.get(cid)
                if comp is None:
                    record["issues"].append(f"changing {cid!r} was never registered")
                    continue
                target = positions.get(cid)
                if target and (abs(comp.group.get_center()[0] - target[0]) > 1e-6 or
                               abs(comp.group.get_center()[1] - target[1]) > 1e-6):
                    anims.append(comp.group.animate.move_to([target[0], target[1], 0]))
            if anims:
                scene.play(*anims, run_time=move_t)
            record["actions"].append(f"move: {move_ids}")

        # nav is a persistent component whose cursor tracks the stage
        for cid in persistent + changing:
            comp = self.components.get(cid)
            if comp and comp.ctype == "nav":
                stage_idx = self.spec.stages.index(stage)
                nav = comp.parts["nav"]
                n_chips = len(nav.stage_names)
                if stage_idx >= n_chips:
                    record["issues"].append(
                        f"nav {cid!r} declares {n_chips} stages but the spec has "
                        f"{len(self.spec.stages)} — clamping to the last chip"
                    )
                    stage_idx = n_chips - 1
                if nav.active != stage_idx:
                    scene.play(nav.cursor.animate.move_to(_chip_center(nav, stage_idx)),
                               run_time=0.5)
                    nav.set_active(stage_idx)

        # 3) persistent band-shifts BEFORE new content enters: a nav row that
        # slides up (title band collapsing) must not sweep through the stage's
        # freshly entered equation/matrix (path warnings are real otherwise)
        drift = []
        persist_moves = []
        for cid in persistent:
            comp = self.components.get(cid)
            if comp is None:
                # first stage often declares nav/title as 'persistent' without an
                # entering stage — auto-enter rather than nag every stage
                comp = self.build(cid, positions.get(cid))
                self.components[cid] = comp
                self.add_component(scene, comp)
                record["actions"].append(f"auto-enter persistent: {cid}")
                continue
            target = positions.get(cid)
            if target:
                dx = abs(comp.group.get_center()[0] - target[0])
                dy = abs(comp.group.get_center()[1] - target[1])
                if dx > 1e-3 or dy > 1e-3:
                    persist_moves.append(
                        comp.group.animate.move_to([target[0], target[1], 0]))
                    drift.append(cid)
        if persist_moves:
            scene.play(*persist_moves, run_time=timings.get("move", 1.0))
            record["actions"].append(f"persistent moved: {drift}")

        # 4) entering + temporary (built at solved positions)
        enters = entering + temporary
        if enters:
            anims = []
            for cid in enters:
                comp = self.build(cid, positions.get(cid), anchors=_current_anchors(self.components))
                if cid in self.components:
                    record["issues"].append(f"{cid!r} entered while already registered — duplicate id")
                self.components[cid] = comp
                anims.append(_enter_anim(comp, stage.transition.get(cid, "fade_in")))
            scene.play(*anims, run_time=timings.get("enter", 0.8))
            record["actions"].append(f"enter: {enters}")
            if temporary:
                self.temp_objects.setdefault(stage.id, []).extend(
                    self.components[cid] for cid in temporary
                )

        self.stage_log.append(record)
        return record

    def add_component(self, scene, comp: Component):
        """Put a component's group in the scene (idempotent)."""
        if comp.group not in scene.mobjects:
            scene.add(comp.group)

    def end_stage(self, scene, stage):
        """Remove temporary objects and sweep for stale scene members."""
        temps = self.temp_objects.pop(stage.id, [])
        if temps:
            anims = []
            for comp in temps:
                comp.group.clear_updaters()
                anims.append(FadeOut(comp.group))
                self.components.pop(comp.id, None)
            scene.play(*anims, run_time=0.4)
        # sweep: anything in the scene that no registered group owns is stale
        known_top = {comp.group for comp in self.components.values()}
        from manimlib.camera.camera_frame import CameraFrame  # ManimGL keeps one in every scene
        stale = [
            m for m in scene.mobjects
            if m not in known_top and not isinstance(m, CameraFrame)
        ]
        for m in stale:
            self.stale_report.append(
                f"stage {stage.id!r}: unregistered object in scene "
                f"({type(m).__name__}) — removing"
            )
            scene.remove(m)
        return stale

    def finish(self, scene):
        """Closing fade of everything still registered."""
        anims = [FadeOut(c.group) for c in self.components.values() if c.ctype != "nav"]
        if anims:
            scene.play(*anims, run_time=0.8)
        self.components.clear()


def _chip_center(nav, idx):
    return nav._chip_rects[idx].get_center()


def _enter_anim(comp: Component, intent: str):
    if intent == "write":
        return Write(comp.group)
    if intent == "grow":
        return GrowFromPoint(comp.group, comp.group.get_center())
    if intent == "reveal":
        return ShowCreation(comp.group)
    return FadeIn(comp.group, scale=0.85 if intent == "fade_in" else 1.0)


def _current_anchors(components: dict[str, Component]) -> dict:
    return {cid: comp.group.get_center()[:2] for cid, comp in components.items()}


class FakeScene:
    """Test double: records plays/adds/removes without rendering."""

    def __init__(self):
        self.mobjects: list = []
        self.plays: list[dict] = []

    def add(self, *mobs):
        for m in mobs:
            if m not in self.mobjects:
                self.mobjects.append(m)

    def remove(self, *mobs):
        for m in mobs:
            while m in self.mobjects:
                self.mobjects.remove(m)

    def play(self, *anims, run_time=1.0):
        self.plays.append({"anims": anims, "run_time": run_time})
        for a in anims:
            self._apply(a)

    def _apply(self, anim):
        from manimlib.animation.animation import Animation
        from manimlib.animation.fading import FadeOut
        from manimlib.animation.transform import ReplacementTransform, Transform
        if isinstance(anim, FadeOut):
            self.remove(anim.mobject)
        elif isinstance(anim, ReplacementTransform):
            self.remove(anim.mobject)
            self.add(anim.target_mobject)
        elif isinstance(anim, Transform):
            pass  # identity morph; scene membership unchanged
        elif hasattr(anim, "target_mobject") and anim.target_mobject is not None:
            # .animate builders: apply end state
            pass
