"""animkit.layout — spec-driven layout, lifecycle and validation for ManimGL.

Public entry points:
  SceneSpec / StageSpec / ComponentSpec / validate_spec   (spec.py)
  SpecScene                                               (compose.py)
  plan_regions / Box                                      (geom.py)
  solve_stage / choose_template                           (templates.py)
  StageRegistry                                           (registry.py)
  validate_stage_layout / summarise                       (validate.py)
  check_paths                                             (paths.py)
  build_contact_sheet / rendered_checks                   (rendered.py)
"""

from animkit.layout.geom import Box, Region, RegionPlan, plan_regions, FRAME_HEIGHT
from animkit.layout.spec import SceneSpec, StageSpec, ComponentSpec, validate_spec
from animkit.layout.templates import solve_stage, choose_template
from animkit.layout.registry import StageRegistry
from animkit.layout.validate import validate_stage_layout, summarise
from animkit.layout.paths import check_paths


from animkit.layout.compose import SpecScene  # requires manimlib (venv python)
