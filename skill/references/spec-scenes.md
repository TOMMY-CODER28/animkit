# Spec-driven scenes (animkit.layout)

For animations that must be **consistently readable and correctly aligned**,
declare a `SceneSpec` instead of positioning mobjects by hand. You describe
*what* each stage contains and *how components relate*; the layout system
solves coordinates, manages the object lifecycle, and validates the result
before and after rendering.

## The workflow for a spec-driven scene

```
animkit.cmd new <name> --dir examples     # template project
# edit scene.py: build_spec() + a SpecScene subclass
animkit.cmd check-layout <project>        # dry-run: no GPU; spec+solve+geometry
animkit.cmd preview <project>             # 480p; layout_report.json written
animkit.cmd frames <project>              # inspect; media/contact_sheet.png
animkit.cmd render <project> && animkit.cmd deliver <project>
```

## Minimal scene

```python
import sys
import animkit  # resolved via pip install -e . or ANIMKIT_ROOT
from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

def build_spec() -> SceneSpec:
    spec = SceneSpec(name="demo", aspect=16/9, density="comfortable",
                     output_dir=str(__import__("pathlib").Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title", content={"text": "My title"}),
        "nav":   ComponentSpec(id="nav", ctype="nav",
                               content={"stages": ["One", "Two"], "active": 0}),
        "m":     ComponentSpec(id="m", ctype="matrix",
                               content={"values": [[1, 0], [0, 1]], "nd": 0,
                                        "label": "M", "color": "#58C4DD"}),
    }
    spec.stages = [
        StageSpec(id="s1", template="single_center",
                  components={"title": "persistent", "nav": "persistent", "m": "entering"},
                  transition={"title": "static", "nav": "static", "m": "fade_in"},
                  caption="the identity matrix"),
        StageSpec(id="s2", template="single_center",
                  components={"nav": "persistent", "m": "changing"},
                  transition={"nav": "static", "m": "move"}),
    ]
    return spec

class MyScene(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
```

## Rules the system enforces (and you should not fight)

- **Lifecycle is explicit**: every component in a stage is one of
  `persistent` (stays; moves only if the solver says so),
  `entering`, `leaving`, `changing` (same object moves/transforms), or
  `temporary` (auto-removed at stage end). A registered component *absent*
  from a stage leaves implicitly — nothing lingers.
- **Re-entry is a new id**: a component that left cannot re-enter (`V` →
  `V2` with the same content).
- **Owned annotations ride their owner**: give a note/highlight
  `owner=<id>`; removing the owner removes it. Place with `side: below/
  above/left/right`, or `region: "annotation"` for the annotation band.
- **Highlights** target a matrix part: `{"target": "A", "part": ["row", 0]}`
  / `["col", 1]` / `["entry", 2, 2]` — they follow their target.
- **No hand-placed coordinates** unless using the `custom` template
  (escape hatch: `custom_x`/`custom_y` per id; still geometry-validated).
- **Labels live inside their component**: `matrix` content takes
  `label` + `label_side`; never add a separate Text and position it.

## Templates

| template | shape | needs |
|---|---|---|
| `single_center` | one component centred | — |
| `two_columns` | side-by-side, shared centreline | 2 main comps |
| `three_columns` | equal CENTRE spacing, one centreline | 3 main comps |
| `input_op_output` | A → B → C row | 3 main comps |
| `operands_result` | operands above, result below | `stage.operands`, `stage.result` |
| `main_callout` | main + callouts in annotation band | `stage.callouts` |
| `equation_explanation` | equation above, text below | `stage.equation` |
| `custom` | your coordinates | `custom_x`, `custom_y` |

Tuning: `stage.min_gap` (default 0.55), `spec.density` ("comfortable" |
"compact"), `stage.annotation_side` ("bottom" | "right"), `stage.timing`
(`{"enter": 0.9, "move": 1.1, "exit": 0.5, "hold": 1.1}`).

## Regions

`title`, `nav`, `main`, `annotation`, `caption` are bands computed from the
frame with margins; unused bands collapse back into `main`. Components of
ctype title/nav/caption land in their band automatically. Assign other
components with `region=`; annotations placed in the annotation band are
clamped inside it.

## Validation (what "check-layout" reports)

- spec errors: unknown template/ctype, ragged matrices, bad lifecycle
  sequences, dangling highlight/callout targets
- solver: infeasible constraint sets come back with numbers and causes
  ("widths + required gaps exceed the main width — shrink entry_size, split
  the stage, or set density='compact'") — never silently overlapping output
- geometry: containment per region, unintended overlap (arrows/highlights/
  owned children exempt), centreline/equal-spacing tolerances, readability
  floors, attachment of owned labels, finiteness
- rendered preview: `media/layout_report.json` (stale objects, geometry),
  `media/stage_times.json` (boundary times for frame extraction),
  `media/contact_sheet.png` (boundary-frame montage)

## Choosing sizes that fit

Matrix readability floor ≈ 0.14 units per entry at 480p. A 3×3 integer
matrix at `entry_size: 30` with an above-label is ≈ 2.2 units tall; two
stacked such matrices plus a 0.45 gap need ≈ 4.9 units of main height. If
check-layout reports infeasible: shrink `entry_size`, drop the stage's
caption band, split the stage, or use `density: "compact"`.

## Intentional overlaps

Declare them: `permitted_overlaps=[("A", "highlight_x")]` on the stage.
Highlights/arrows/connectors and owned children are already exempt.
