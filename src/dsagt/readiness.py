"""AI-readiness check: an AIDRIN quality report for every table the pipeline reads or writes.

When a project keeps the readiness check on (the default at ``dsagt init``),
``dsagt-run`` prints a note after a registered code exits for each table the
run read or wrote that has no report for its current content, and the agent
checks it with the ``aidrin`` base skill through the ``aidrin`` code every
project registers at init.  The report is that run's execution record, which
holds what AIDRIN printed; ``provenance.current_readiness_report`` finds it by
the table's content hash, for the note and for the ``readiness_reports`` tool
alike.  The note is printed where the agent reads a command's output, which
is when it chooses its next step; a rule in the instructions was read once at
the start, and agents skipped the check around most stages.  The ``aidrin``
package is a dependency of dsagt, and the skill is a base skill fetched at the
release tag of the installed package.

The ``readiness`` block of ``.dsagt/config.yaml`` holds the one setting::

    readiness:
      auto_assess: true
"""

from __future__ import annotations

from pathlib import Path

#: File suffixes read as a table.  A JSON, HDF5 or NumPy file is a table only
#: sometimes, which the ``aidrin`` skill decides when the user asks for a check.
TABLE_SUFFIXES = (".csv", ".tsv", ".parquet", ".xlsx", ".xls")

#: What the agent is told about a table with no current report, by
#: ``dsagt-run`` after a run and by the ``readiness_reports`` tool on request.
NO_REPORT = (
    "no readiness report for {path} at its current content. Check it with the "
    "aidrin skill (at least its data-quality summary) before the next pipeline step."
)


#: The same fact as ``dsagt-run`` prints it on stderr after a run.  A calm
#: line on stdout was read as log text: in the first run that carried it, the
#: agent saw it five times and ran no check.
WARNING = (
    "DANGER!!! The readiness check has NOT been run on {path} at its current "
    "content. STOP: check it with the aidrin skill (at least its data-quality "
    "summary) BEFORE the next pipeline step."
)


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


def readiness_notes(record: dict, project_dir: Path) -> list[str]:
    """The notes ``dsagt-run`` prints after the run *record* describes.

    One per table among the run's inputs and outputs that has no report for
    its current content.  A failed run and a run of ``aidrin`` itself give
    none.  An input the run left unchanged still matches the hash a report
    made now would record, so that report serves as the stage's "before".
    """
    from dsagt.provenance import current_readiness_report

    execution = record["execution"]
    if execution.get("return_code") != 0 or record.get("code_name") == "aidrin":
        return []
    notes = []
    for path in [*execution.get("input_files", []), *execution.get("output_files", [])]:
        if (
            not path.lower().endswith(TABLE_SUFFIXES)
            or not (project_dir / path).is_file()
        ):
            continue
        note = "dsagt: " + WARNING.format(path=path)
        if note not in notes and current_readiness_report(project_dir, path) is None:
            notes.append(note)
    return notes
