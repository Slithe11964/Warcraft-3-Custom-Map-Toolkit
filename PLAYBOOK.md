# Playbook: from a protected map to a map a new developer can work on

This is the process used on Final Fantasy Epic RPG (2026), written so it can be repeated on another
custom map, for example to learn how another RPG was built.

## 0. Before you start

- Work on a **copy**, never the original download. Keep the original untouched as your baseline.
- **Look at compatibility:** `python tools/compat_report.py MAP.w3x` reads the playable JASS script.
  Missing editor text is expected on a protected input; run check_editable.py after deprotecting.
  The deprotector rejects Lua. Unknown archive compression/protection may require additional work.
- **Check versions:** `python tools/compat_report.py MAP.w3x` shows which game versions it targets.
- **Respect the author.** Opening a map to learn from it is one thing. Republishing someone else's
  work needs their permission. FF Epic RPG's maintainers were involved in this project.

## 1. Deprotect (make it editable)

`python tools/deprotect.py MAP.w3x out/1-deprotected.w3x`

- **What changes:** the whole compiled script becomes the map custom script. The functions World
  Editor writes by itself are renamed `*_old`, and a GUI trigger "MainDeprotected" calls
  `main_old()` at map start.
- **Pre-placed objects:** units, regions, cameras and sounds are created by the script, so their
  editor files are emptied to avoid creating everything twice.
- **Check:** run `python tools/check_editable.py out/1-deprotected.w3x`, then open the map in
  World Editor (JassHelper + vJass on), Save As, and play a few minutes. It should play exactly like
  the original.
- FF Epic RPG: the r7 map we received was already in this state (`MainDeprotected` + the whole
  script with `_old` names). `deprotect.py` produces the identical trigger tree.

## 2. Split into modules

`python tools/split_modules.py out/1-deprotected.w3x out/2-split.w3x --report out/split.json`

- **One module per trigger:** each original trigger becomes one custom-text trigger, holding its
  code and the helpers only it uses. Shared helpers go into `Shared`, and start-up code stays in
  the custom script.
- **Same start-up order:** `InitTrig_X` becomes `Register_X`. main_old still creates every trigger
  in the original order, so nothing about start-up changes.
- **Check:** run `check_editable.py`, then World Editor Save As + play.
- FF Epic RPG: ChatGPT's Builder23/24 tools did this step in many stages (739 modules, then
  registration helpers moved into their modules). `split_modules.py` does the core of it in one go.

## 3. Read and document

```
python tools/format_modules.py out/2-split.w3x out/3-formatted.w3x
python tools/export_sources.py out/3-formatted.w3x out/src
python tools/document.py out/src out/docs
```

Now the code is indented and in plain files, and you have:

- an index of every trigger and what fires it;
- every variable and who uses it;
- a list of dead code.

**Put `out/src` in Git** (`git init`, commit). From here on, every change is a reviewable diff.

`python tools/pipeline.py MAP.w3x out/` runs steps 1–3 with checks after each. Use an empty
output folder: existing work is refused. manifest.json records input/output hashes.

## 4. Clean up (map-specific; FF Epic RPG's phases as a template)

These steps need judgement about the particular map. The FF Epic RPG scripts are in
`FFERPG/tools/refactor/`. Copy and adapt them; the docs explain each phase
(see that repository's CONTRIBUTING.md, SYSTEMS.md and PHASE16.md).
These FF-specific phases are optional examples, not part of this toolkit's automated pipeline.

| Phase | What | FF Epic RPG script |
|---|---|---|
| 1 | Formatting only | `phase1_format.py` |
| 2 | Readable start-up: name the steps of `main_old`, group the trigger registration | `phase2_startup.py` + `startup_audit.py` (proves the same statements run in the same order) |
| 3 | Each module declares the variables only it uses | `phase3_state.py` |
| 4 | Explain: comments on object IDs and formulas, a developer guide in the map header, `SYSTEMS.md` | `phase4_explain.py` |
| 5 | Long texts into GUI triggers (string table). **Long script strings crash loading saved games.** | `phase5_questlog.py` |
| 6 | Safe switching off: `requires optional` + `static if` guards, and a tool that proves a module can be disabled | `phase6_optional.py`, `disable_check.py` |
| 7 | Remove dead code, repeated until nothing new turns up | `phase7_dead_code.py` |
| 8 | Split giant functions, rename leftovers, move shared variables into the Variable Editor | `phase8_*.py`, `rename_module.py` |
| 9 | Hand-off: map name, `CONTRIBUTING.md`, variable sub-folders | `phase9_cleanup.py` |

### Rules that kept FF Epic RPG working through all of this

1. **Change one thing per step,** and prove it before moving on. Each script checks that function
   bodies are token-identical (or lists exactly what changed).
2. **Keep the start-up order identical.** Triggers that share an event fire in creation order, so
   moving a registration can change gameplay.
3. **After every step:** automated checks, then a World Editor **Save As**, then a short play test
   that covers saving and loading a game.
4. **Keep long text (over ~1000 characters) out of script strings.** Use GUI actions / the string
   table, or loading a saved game crashes.
5. **Test before you trust.** "It compiles" is not "it plays". Keep the last map that was confirmed
   in game as the baseline.
6. **Write things down** (`CONTINUE_PROJECT.md`) so another session, person or AI can pick up.

## 5. Other game versions

`compat_report.py` and `version_libs.py` answer "does the script work in 1.29.2 / 1.31?". File
formats are the harder part: Reforged saves every world and object file in a newer format. See
`FFERPG/docs/LEGACY_129.md` for the FF Epic RPG study.

## FF Epic RPG's history, in short

| When | What | Where it is now |
|---|---|---|
| Sep 2026 | r7 received deprotected (one giant custom script). The WinForms extractor app was built to explore it: function search, call tree, subsystem discovery. | `WarcraftMapExtractor/Program.cs` (run with `dotnet run`) |
| Sep–Oct 2026 | ChatGPT (Builder23/24): split into 739 modules; registration ownership; staged initialisation; native save/load fix (long text → string table); r11 author changes merged; neutral-unit fix. | `WarcraftMapExtractor/Builder24/` (C# + Python scripts, notes); outputs in `_archive/` |
| Oct 2026 | Claude, phases 0–9: Git repo, readable start-up, module-owned variables, docs, quest-log GUI, safe disabling, dead code, damage split, Variable Editor, hand-off docs. | `WarcraftMapExtractor/FFERPG/` |
| Oct 2026 | Reusable toolkit (this folder), tested on a second, protected map. | `WarcraftMapExtractor/MapToolkit/` |

The full step-by-step log is `WarcraftMapExtractor/CONTINUE_PROJECT.md` (newest at the top).
