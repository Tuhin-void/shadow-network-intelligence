# `libs/` — vendored Python packages

This directory is reserved for vendored Python packages that are imported
by the platform via `from libs.X import Y`.

**Current contents:** intentionally empty. The platform's `2_baseline_systems`
and `3_graph_intelligence_core` packages contain everything the orchestrator
needs at runtime; nothing under `libs/` is currently imported.

A previous revision included a 52 MB unmodified copy of TigerGraph's
official `tigergraph/graphrag` repository here. It was reference material
that was never imported by the orchestrator, dashboard, or benchmark
runner, and it was confusing reviewers into thinking the platform was a
wrapper around TigerGraph's CopilotGraph product. It has been removed so
the repository accurately reflects what is shipped.
