"""Windows launcher generation for OST templates using distlib."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

try:
    from distlib.scripts import ScriptMaker  # type: ignore
except ImportError:
    ScriptMaker = None


class WindowsLauncherError(Exception):
    """Raised when Windows launcher generation fails."""

    pass


def is_windows() -> bool:
    """Check if running on Windows."""
    return os.name == "nt"


def generate_windows_launcher(
    template_path: Path, output_dir: Optional[Path] = None
) -> tuple[Path, Path]:
    """Generate Windows launcher files for an OST template.

    Args:
        template_path: Path to the .ost template file
        output_dir: Directory to place launcher files (default: same as template)

    Returns:
        Tuple of (launcher_exe_path, cmd_shim_path)

    Raises:
        WindowsLauncherError: If launcher generation fails
    """
    if not is_windows():
        raise WindowsLauncherError(
            "Windows launcher generation only supported on Windows"
        )

    if ScriptMaker is None:
        raise WindowsLauncherError(
            "distlib not available - cannot generate Windows launcher"
        )

    if not template_path.exists():
        raise WindowsLauncherError(f"Template file not found: {template_path}")

    if not template_path.suffix == ".ost":
        raise WindowsLauncherError(
            f"Template must have .ost extension: {template_path}"
        )

    # Determine output directory
    if output_dir is None:
        output_dir = template_path.parent

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate launcher name
    template_name = template_path.stem
    launcher_name = f"{template_name}_launcher"

    # Create ScriptMaker
    script_maker = ScriptMaker(
        source_dir=str(output_dir),
        target_dir=str(output_dir),
        executable=sys.executable,
    )

    # Create launcher script content
    # This will be embedded in the .exe and call our runx module
    launcher_script = f"""
import sys
import os
from pathlib import Path

# Add the template path to arguments
template_path = Path(__file__).parent / "{template_path.name}"
sys.argv = [sys.argv[0], str(template_path)] + sys.argv[1:]

# Import and run the runx main function
from ostruct.cli.runx.runx_main import runx_main
sys.exit(runx_main())
"""

    # Generate the .exe launcher
    try:
        # Create a temporary script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as tmp_script:
            tmp_script.write(launcher_script)
            tmp_script_path = tmp_script.name

        # Generate the launcher
        launcher_specs = [
            {
                "name": launcher_name,
                "script": tmp_script_path,
                "console": True,
            }
        ]

        generated_files = script_maker.make_multiple(launcher_specs)

        # Clean up temporary script
        os.unlink(tmp_script_path)

        # Find the generated .exe file
        launcher_exe_path = None
        for file_path in generated_files:
            if file_path.endswith(".exe"):
                launcher_exe_path = Path(file_path)
                break

        if not launcher_exe_path:
            raise WindowsLauncherError("Failed to generate .exe launcher")

    except Exception as e:
        raise WindowsLauncherError(f"Failed to generate launcher: {e}")

    # Generate .cmd shim
    cmd_shim_path = output_dir / f"{template_name}.cmd"
    cmd_shim_content = f"""@echo off
REM Windows CMD shim for {template_name}.ost
REM This file allows execution in environments that don't allow .exe files

python -m ostruct.cli.runx "%~dp0{template_path.name}" %*
"""

    try:
        cmd_shim_path.write_text(cmd_shim_content, encoding="utf-8")
    except Exception as e:
        raise WindowsLauncherError(f"Failed to generate .cmd shim: {e}")

    return launcher_exe_path, cmd_shim_path


def generate_launcher_for_template(template_path: Path) -> None:
    """Generate Windows launcher files for a template and display results.

    Args:
        template_path: Path to the .ost template file
    """
    try:
        launcher_exe, cmd_shim = generate_windows_launcher(template_path)

        print("✅ Generated Windows launcher files:")
        print(f"   📄 Launcher: {launcher_exe}")
        print(f"   📄 CMD Shim: {cmd_shim}")
        print()
        print("Usage:")
        print(f"   {launcher_exe.name} [args...]")
        print(f"   {cmd_shim.name} [args...]")

    except WindowsLauncherError as e:
        print(f"❌ Failed to generate Windows launcher: {e}")
        sys.exit(1)


def cleanup_launcher_files(template_path: Path) -> None:
    """Clean up generated launcher files for a template.

    Args:
        template_path: Path to the .ost template file
    """
    template_name = template_path.stem
    output_dir = template_path.parent

    # List of files to clean up
    files_to_remove = [
        output_dir / f"{template_name}_launcher.exe",
        output_dir / f"{template_name}.cmd",
    ]

    removed_count = 0
    for file_path in files_to_remove:
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"🗑️  Removed: {file_path}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️  Failed to remove {file_path}: {e}")

    if removed_count == 0:
        print("ℹ️  No launcher files found to remove")
    else:
        print(f"✅ Removed {removed_count} launcher file(s)")
