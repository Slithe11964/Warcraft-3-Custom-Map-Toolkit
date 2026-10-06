# MapToolkit: open up, study and clean up a Warcraft III map

These are the tools behind FF Epic RPG's cleanup, made reusable for other JASS maps (classic or
Reforged). They need Python 3 and `pjass` (`tools/bin/`).

Steps 1–3 also run in one command:

```
python tools/pipeline.py "SomeProtectedMap.w3x" out/SomeMap
```

Read [PLAYBOOK.md](PLAYBOOK.md) for the whole process. It also explains how FF Epic RPG went from a
protected map to the documented, modular map it is now.

## Setup and verification

Python 3.9+ is required; all Python dependencies are in the standard library. The Windows compiler
tools/bin/pjass.exe and compiler/version libraries are tracked. No sibling project is needed.
On other operating systems install pjass on PATH. Warcraft III World Editor/JassHelper are needed
for editor Save As and in-game verification, not the command-line study pipeline.

```powershell
python tools/test_pipeline.py
python tools/test_downgrade_visuals.py
```

The first command tests the complete pipeline on a synthetic JASS map, preserving original/runtime/
assets, rejecting existing work and Lua, and protecting strings/comments during renaming. No third-party
map is needed. See VERIFY.md for current results/limits. Generated maps, work/out folders and logs
are excluded from Git. Pipeline outputs include manifest.json with input and output hashes.

## Optional classic conversion

```powershell
.\downgrade_129.ps1 -Map "Reforged.w3x" -Template "SameMap-classic.w3x" -FillFrom "SameMap-classic.w3x"
```

The template must be a classic-format copy of the same map. FillFrom restores missing object defaults
when such a copy is available. The batch invokes this script and accepts the same arguments.
No FF Epic RPG input path is hardcoded. Output is a sibling 1.29.2 folder with the same basename;
existing output is refused. -FFERPGVisuals is an explicit FF-only appearance profile, unnecessary
for studying other maps. FFERPG has its own standalone shortcut/toolchain in its own repository.

## Tools

| Step | Tool | What it does |
|---|---|---|
| 1 | `deprotect.py` | Protected map → editable: the compiled script becomes the map custom script, plus one GUI trigger that runs it. |
| 2 | `split_modules.py` | One custom-text trigger (vJass library) per original trigger. Shared helpers go in `Shared`, start-up code stays in the custom script. |
| 3 | `format_modules.py` | Re-indents all code. It checks that only whitespace changed. |
| 3 | `export_sources.py` | Writes the code to plain files (`src/`), for reading, searching and Git. |
| 3 | `document.py` | Writes `TRIGGER_INDEX.md` (every trigger and what fires it), `GLOBALS.md` (every variable and who uses it) and `DEAD_CODE.md`. |
| any | `check_editable.py` | Compiles what World Editor would build from the map's trigger text, and the playable script, with pjass. Also warns about save-breaking long strings. |
| any | `compat_report.py` | Which game versions can run the script, and which file formats need converting. |
| any | `downgrade.py` | Turns a Reforged-saved map into a playable 1.29.2 map (terrain, doodads, units, objects, map info, script). Every converter was checked against the same map saved by an older editor. |
| any | `objdata.py` | Reads and writes object data (v2 classic, v3 Reforged), byte-exact. |
| any | `version_libs.py` | Builds `common.j`/`blizzard.j` for any patch (1.29.2, 1.31.1, …) from the annotated jassdoc libraries in `tools/jassdoc/`. |

Libraries the tools share:

| File | Use |
|---|---|
| `mpq.py` | Read maps; replace, add and remove files; compact. |
| `wct_any.py` | Custom script text, classic and Reforged formats. |
| `wtg.py` | Reforged trigger tree, including variables. |
| `vjass_lite.py` | A small JassHelper stand-in, for checks only. |
| `jtok.py`, `jfmt.py` | Tokenizer and formatter. |

## Tested on

- **HVH Reloaded 1.7:** a protected map with 1,012 functions and 82 triggers. All steps pass,
  every function is unchanged, and the result compiles for 1.29.2, 1.31.1 and Reforged.
  *This map contains injected cheat code (a `-cheats` command in `main`). The documents make that
  easy to spot, which is one more reason to look before you play a downloaded map.*
- **FF Epic RPG:** its own tools are in `FFERPG/tools`.

## Not covered

- **Lua maps:** not supported.
- **Scrambled names:** maps whose names an optimizer scrambled stay scrambled. The tools restore
  structure, not names.
- **World Editor:** the tools prepare the map and check it, but it must still be opened, saved and
  play tested in World Editor.
