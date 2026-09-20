"""AI-readiness check: config block, release tag, and the instructions paragraph."""

import re
from importlib.metadata import version

import pytest

from dsagt import readiness as rd
from dsagt.agents.base import _load_master_instructions


class TestConfigBlock:

    def test_block_holds_the_one_setting(self):
        assert rd.readiness_block(True) == {"auto_assess": True}
        assert rd.readiness_block(False) == {"auto_assess": False}

    def test_enabled_reads_the_block_and_defaults_on(self):
        assert rd.auto_assess_enabled({}) is True
        assert rd.auto_assess_enabled({"readiness": {"auto_assess": False}}) is False
        assert rd.auto_assess_enabled({"readiness": {"auto_assess": True}}) is True


class TestReleaseTag:

    def test_zero_pads_the_month(self):
        # importlib.metadata reports the normalized version; the tag keeps
        # the two-digit month AIDRIN releases under.
        assert rd.aidrin_release_tag("2026.8.2") == "v2026.08.2"
        assert rd.aidrin_release_tag("2026.08.2") == "v2026.08.2"
        assert rd.aidrin_release_tag("2026.11.1") == "v2026.11.1"

    def test_rejects_other_shapes(self):
        for bad in ("2026.8", "2026.8.2.dev1", "v2026.08.2", ""):
            with pytest.raises(ValueError, match="year"):
                rd.aidrin_release_tag(bad)

    def test_installed_package_maps_to_a_tag(self):
        tag = rd.aidrin_release_tag(version("aidrin"))
        assert re.fullmatch(r"v\d{4}\.\d{2}\.\d+", tag), tag


def _record(code, inputs, outputs, rc=0):
    return {
        "record_id": "r1",
        "code_name": code,
        "execution": {
            "exact_command": [code],
            "return_code": rc,
            "input_files": inputs,
            "output_files": outputs,
            "file_hashes": {},
        },
    }


class TestReadinessNotes:
    """What dsagt-run prints after a run, where the agent reads it."""

    def _project(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "in.csv").write_text("a\n1\n")
        (tmp_path / "data" / "out.csv").write_text("a\n2\n")
        (tmp_path / "data" / "out.json").write_text("{}")
        (tmp_path / "trace_archive").mkdir()
        return tmp_path

    def test_one_note_per_table_without_a_report(self, tmp_path):
        from dsagt.readiness import readiness_notes

        project = self._project(tmp_path)
        record = _record("convert", ["data/in.csv"], ["data/out.csv", "data/out.json"])
        notes = readiness_notes(record, project)
        assert len(notes) == 2  # the JSON output is not read as a table
        assert "data/in.csv" in notes[0] and "data/out.csv" in notes[1]
        assert "aidrin skill" in notes[0]

    def test_a_current_report_ends_the_note(self, tmp_path):
        import hashlib
        import json

        from dsagt.readiness import readiness_notes

        project = self._project(tmp_path)
        check = _record("aidrin", ["data/out.csv"], [])
        check["execution"]["stdout"] = '{"outliers": 0.03}'
        check["execution"]["timestamp_start"] = "2026-01-01T00:00:00Z"
        check["execution"]["file_hashes"] = {
            "data/out.csv": hashlib.sha256(b"a\n2\n").hexdigest()
        }
        (project / "trace_archive" / "aidrin_1.json").write_text(json.dumps(check))
        record = _record("convert", [], ["data/out.csv"])
        assert readiness_notes(record, project) == []
        # The table changes; the report is no longer current.
        (project / "data" / "out.csv").write_text("a\n3\n")
        assert len(readiness_notes(record, project)) == 1

    def test_a_failed_run_and_an_aidrin_run_give_none(self, tmp_path):
        from dsagt.readiness import readiness_notes

        project = self._project(tmp_path)
        assert (
            readiness_notes(_record("convert", [], ["data/out.csv"], rc=1), project)
            == []
        )
        assert readiness_notes(_record("aidrin", ["data/out.csv"], []), project) == []


def test_the_instructions_carry_no_readiness_text():
    text = _load_master_instructions()
    assert "readiness" not in text.lower()
    assert "<!--" not in text
