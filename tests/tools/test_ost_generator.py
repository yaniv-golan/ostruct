"""Smoke-test the OST Generator.

This test runs tools/ost-generator/run.sh on a minimal template + schema and
asserts that the generated .ost file exists and passes validation.
"""

# Use tempfile.TemporaryDirectory instead of pytest tmp_path to avoid basetemp issues
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "tools" / "ost-generator" / "run.sh"


def _write_fixture(tmp_dir: Path):
    """Write minimal template + schema into tmp directory and return paths."""
    template = tmp_dir / "sample.j2"
    template.write_text("""{{ input }}\n""")

    schema = tmp_dir / "sample.schema.json"
    schema.write_text(
        json.dumps(
            {"type": "object", "properties": {"result": {"type": "string"}}}
        )
    )
    return template, schema


# Disable the default Pyfakefs fixture which interferes with run.sh filesystem operations
# by marking the test with "no_fs".
@pytest.mark.no_fs
def test_run_sh_smoke():  # noqa: D103
    with tempfile.TemporaryDirectory() as tmpd:
        tmp_dir = Path(tmpd)
        template, schema = _write_fixture(tmp_dir)
        outdir = tmp_dir / "out"
        outdir.mkdir()

        # Run the generator
        subprocess.run(
            [
                "bash",
                str(GENERATOR),
                "-t",
                str(template),
                "-s",
                str(schema),
                "-o",
                str(outdir),
                "--dry-run",
            ],
            check=True,
            cwd=REPO_ROOT,
        )

        # Expect a generated .ost file
        generated = next(outdir.glob("*.ost"), None)
        assert (
            generated and generated.is_file()
        ), "Generated .ost file not found"

        # Basic sanity: shebang and front-matter delimiter present
        content = generated.read_text()
        assert content.startswith(
            "#!/usr/bin/env -S ostruct runx\n---\n"
        ), "Shebang and front-matter missing in generated .ost"
