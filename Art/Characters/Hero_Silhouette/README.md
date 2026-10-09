# Hero silhouette studies — awaiting selection

The production request was stopped by the user. `Hero_Kaze.blend` is **V0 TECHNICAL MANNEQUIN**, not an approved production character.

The current deliverable is `Hero_Silhouette_ABC.blend`: one static mesh set with three matching shape-key states on every mesh. It has no armature object or animation, uses a single grey clay material, and is excluded from Godot discovery by `.gdignore`. No game scene, gameplay code or existing hands/legs/bow source was replaced.

- **A — Concept:** narrow waist, longer legs/forearms, reduced boots and hardware, relaxed human shoulders.
- **B — Powerful:** slightly fuller ribcage, limbs and shoulders; still substantially leaner than V0.
- **C — Anime lean:** longest legs, narrowest waist and smaller head/feet.

The jacket was rebuilt as broad curved cloth surfaces with an open front, shorter folded lapels, irregular hem and asymmetric sleeves. The oversized shoulder interface and torso plates were removed from the study. Hair uses larger swept asymmetric clumps. Pants are unified broad volumes. This is still a visual proportion study, not a claim that the concept match is approved or finished.

`Review/ABC_All_Views.png` shows front / 3/4 / side for each variant. `Review/Concept_ABC_Front.png` places the reference beside the three fronts. `Review/ABC_Back.png` contains the rear views. Individual full-size captures remain in the same folder. The reference image is a non-rendered Blender image empty, never a surface texture.

To select a state manually, set all three non-Basis keys to zero and enable exactly one state on every mesh. The optional `Tools/Character/study_view.py` helper adds A/B/C buttons in the Blender viewport's **Silhouette** sidebar when Blender is launched with that script. It performs no modelling or rigging.

## Preserved pre-stop work

`Assets/Models/Characters/Hero/` retains the V0 source and the FP drafts saved before the stop request. They are also excluded by `.gdignore`, are not connected to Player, and are not part of the selected silhouette deliverable. The original production builders are retained for provenance, not scheduled to run. Do not resume them without a new user decision.

## Stop condition

Three variants delivered. Await the user's visual selection. No further detailing, rigging, export, Godot integration, commit or push.

Scope check against the preflight SHA-256 snapshot: no existing repository file changed or disappeared. Added files are limited to this study folder, the retained pre-stop `Assets/Models/Characters/Hero/` drafts, and `Tools/Character/` authoring/review scripts. Temporary renders and logs are under ignored `.godot/hero-pass/`. Window automation was stopped after the user's physical Escape input.
