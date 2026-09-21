"""AI-readiness check: the AIDRIN quality baseline around every tabular stage.

The pipeline-builder instructions require a paired check before and after
every data operation, with reports in ``audit/``.  When a project keeps the
readiness check on (the default at ``dsagt init``), the check for a tabular
stage is the ``aidrin`` skill's quality baseline, run through the ``aidrin``
code that every project registers at init, so each run is an execution
record.  The setting adds one paragraph to the agent's instructions at the
per-operation check rule and changes nothing else: the ``aidrin`` package is
a dependency of dsagt, the skill is a base skill fetched at the release tag
of the installed package, and AIDRIN's own workflow serves a user who asks
for an assessment.

The ``readiness`` block of ``.dsagt/config.yaml`` holds the one setting::

    readiness:
      auto_assess: true
"""

from __future__ import annotations

#: The paragraph :func:`dsagt.agents.base._load_master_instructions` fills in
#: at the per-operation check rule when the check is on.
INSTRUCTIONS_PARAGRAPH = """\
#### AI-readiness check

For a stage whose input or output is a tabular file (CSV, TSV, Excel, JSON,
HDF5, Parquet, npz), the check is the `aidrin` skill's quality baseline: run
it on the data as it arrives and on the output of each transformation,
through the registered `aidrin` code's `executable` (never bare `aidrin`).
A stage's output report is the report its next stage is measured against, so
each file is checked once. Run the baseline directly; do not ask the user about intent or confirm a plan for these checks
(the skill's full workflow is for assessments the user asks for). A JSON,
HDF5, or NumPy file may hold nested or multi-dataset structure that the
baseline reads as one flat table; say so beside the numbers when you report
them. The run's execution record holds the report, and `readiness_reports`
returns the one on record for a file; `dsagt-run` refuses a check that
repeats one already on record for that file's current content. Report the
per-metric change to the user before proposing the next step, comparing a
table with its own earlier report or with the report of the table it was made
from. Do not write a custom check for a metric AIDRIN provides. A stage with
a tabular input or output gets this check; every other stage keeps the check
rule above."""


#: What ``readiness_reports`` says for a file with no current report.
NO_REPORT = (
    "no readiness report for {path} at its current content. Check it with the "
    "aidrin skill (at least its data-quality summary)."
)


#: The code whose runs are the AI-readiness check.
CHECK_CODE = "aidrin"


def repeated_check(command: list[str], project_dir) -> dict | None:
    """The record of an identical check already made on the same content, or ``None``.

    A check is identical when the command matches and every file it names
    hashes to what that run recorded, so re-running it would produce the
    report already on record.  Codex ran four such repeats in one cryo-EM
    walkthrough.  A command naming no file that exists is never a repeat.
    """
    from pathlib import Path as _Path

    from dsagt.provenance import load_pipeline_records, sha256_of

    project_dir = _Path(project_dir)
    named = [a for a in command[1:] if (project_dir / a).is_file()]
    if not named:
        return None
    current = {a: sha256_of(str(project_dir / a)) for a in named}
    for record in load_pipeline_records(project_dir / "trace_archive"):
        execution = record["execution"]
        if record.get("code_name") != CHECK_CODE or execution.get("return_code") != 0:
            continue
        if execution.get("exact_command") != command:
            continue
        recorded = execution.get("file_hashes", {})
        if all(recorded.get(a) == digest for a, digest in current.items()):
            return record
    return None


def aidrin_release_tag(version: str) -> str:
    """The AIDRIN git tag that holds *version* of the ``aidrin`` package.

    AIDRIN tags a release ``v<year>.<month>.<patch>`` with a two-digit month
    (``v2026.08.2``), while the installed package reports the normalized
    version (``2026.8.2``), so the month is zero-padded here.  Raises
    ``ValueError`` for a version that is not three integer components.
    """
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(
            f"aidrin version must be <year>.<month>.<patch>, got {version!r}"
        )
    year, month, patch = parts
    return f"v{year}.{int(month):02d}.{patch}"


def readiness_block(auto_assess: bool) -> dict:
    """The ``readiness`` config block."""
    return {"auto_assess": bool(auto_assess)}


def auto_assess_enabled(config: dict) -> bool:
    """Whether the project runs the readiness check; on when the config has no block."""
    block = config.get("readiness") or {}
    return bool(block.get("auto_assess", True))
