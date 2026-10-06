# Repository verification — 2026-10-06

The generic study workflow is self-contained: Python standard library, tracked Windows pjass,
compiler libraries/version libraries, MPQ reader/writer, editor reconstruction, module splitting,
formatting, export and generated documentation. Python 3.9+ is required; no pip packages are used.
Install pjass separately on non-Windows systems. World Editor/JassHelper are external applications
needed for actual editor Save As verification, not for the command-line study pipeline.

Four synthetic tests cover the full deprotect/split/format/export/document/compatibility pipeline,
input/runtime/asset preservation, nonempty output refusal, Lua rejection and safe identifier renaming.
Three FF visual-profile regressions also pass. No CoTN-RPG map was opened, read or processed.

This is readiness to attempt a future JASS study, not a guarantee that any protected map is supported.
Lua is unsupported. Obfuscated names are not recovered. Archive decompression supports zlib/bzip2;
other compression/protection schemes can require separate work. Module grouping follows generated
InitTrig/Trig names and dependencies; it cannot infer an arbitrary optimizer's original design.
Review generated code/docs, then verify World Editor saves and behavior on a copy.

The downgrade wrapper now accepts an explicit template from the same map and optional object-default
fill map. No FF Epic RPG/r7 path is hardcoded; FF visual edits are opt-in. It requires those user inputs
because a generic converter cannot guess the map's original metadata or missing ability defaults.

The old FF-specific readability phases are examples in the separate FFERPG repository, not dependencies.
The reusable toolkit produces basic modules and insight docs; map-specific refactors remain manual.

Maps, work/out directories, Python caches and logs are ignored. Only tools, libraries, tests and guides
are uploaded. No remote was configured and nothing was published during this verification.
