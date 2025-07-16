"""The setup command for environment configuration and Windows registration."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import rich_click as click

from ..ost.windows_launcher import is_windows


def get_localappdata_path() -> Path:
    """Get the %LOCALAPPDATA% path on Windows."""
    if not is_windows():
        raise RuntimeError("LOCALAPPDATA only available on Windows")

    localappdata = os.environ.get("LOCALAPPDATA")
    if not localappdata:
        raise RuntimeError("LOCALAPPDATA environment variable not found")

    return Path(localappdata)


def get_ostruct_launcher_dir() -> Path:
    """Get the ostruct launcher directory in %LOCALAPPDATA%."""
    return get_localappdata_path() / "ostruct"


def create_global_ost_runner() -> Path:
    """Create the global OST runner executable in %LOCALAPPDATA%\\ostruct."""
    launcher_dir = get_ostruct_launcher_dir()
    launcher_dir.mkdir(parents=True, exist_ok=True)

    # For now, create a .cmd file since we can't easily create .exe without distlib complexity
    cmd_runner_path = launcher_dir / "ostruct-ost-runner.cmd"
    cmd_content = """@echo off
REM Global OST runner for Windows
python -c "import sys; from ostruct.cli.runx.runx_main import runx_main; sys.exit(runx_main())" %*
"""

    cmd_runner_path.write_text(cmd_content, encoding="utf-8")

    return cmd_runner_path


def run_windows_command(command: str) -> tuple[int, str]:
    """Run a Windows command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"
    except Exception as e:
        return 1, f"Command failed: {e}"


def register_ost_file_association() -> bool:
    """Register .ost file association with Windows."""
    click.echo("🔗 Registering .ost file association...")

    # Register file association
    assoc_cmd = "assoc .ost=OstructTemplate"
    exit_code, output = run_windows_command(assoc_cmd)

    if exit_code != 0:
        click.echo(f"❌ Failed to register .ost association: {output}")
        return False

    # Register file type
    runner_path = get_ostruct_launcher_dir() / "ostruct-ost-runner.cmd"
    ftype_cmd = f'ftype OstructTemplate="{runner_path}" "%1" %*'
    exit_code, output = run_windows_command(ftype_cmd)

    if exit_code != 0:
        click.echo(
            f"❌ Failed to register OstructTemplate file type: {output}"
        )
        return False

    click.echo("✅ File association registered successfully")
    return True


def add_ost_to_pathext() -> bool:
    """Add .OST to PATHEXT environment variable."""
    click.echo("🔧 Adding .OST to PATHEXT...")

    # Get current PATHEXT
    pathext_cmd = "echo %PATHEXT%"
    exit_code, current_pathext = run_windows_command(pathext_cmd)

    if exit_code != 0:
        click.echo(f"❌ Failed to get PATHEXT: {current_pathext}")
        return False

    current_pathext = current_pathext.strip()

    # Check if .OST is already in PATHEXT
    if ".OST" in current_pathext.upper():
        click.echo("ℹ️  .OST already in PATHEXT")
        return True

    # Add .OST to PATHEXT (user environment only)
    new_pathext = current_pathext + ";.OST"
    setx_cmd = f'setx PATHEXT "{new_pathext}"'
    exit_code, output = run_windows_command(setx_cmd)

    if exit_code != 0:
        click.echo(f"❌ Failed to update PATHEXT: {output}")
        return False

    click.echo("✅ .OST added to PATHEXT successfully")
    return True


def unregister_ost_file_association() -> bool:
    """Unregister .ost file association from Windows."""
    click.echo("🔗 Unregistering .ost file association...")

    # Remove file association
    assoc_cmd = "assoc .ost="
    exit_code, output = run_windows_command(assoc_cmd)

    # Remove file type
    ftype_cmd = "ftype OstructTemplate="
    exit_code2, output2 = run_windows_command(ftype_cmd)

    if exit_code != 0 and exit_code2 != 0:
        click.echo(
            f"⚠️  Some associations may not have been removed: {output} {output2}"
        )
        return False

    click.echo("✅ File association unregistered successfully")
    return True


def remove_ost_from_pathext() -> bool:
    """Remove .OST from PATHEXT environment variable."""
    click.echo("🔧 Removing .OST from PATHEXT...")

    # Get current PATHEXT
    pathext_cmd = "echo %PATHEXT%"
    exit_code, current_pathext = run_windows_command(pathext_cmd)

    if exit_code != 0:
        click.echo(f"❌ Failed to get PATHEXT: {current_pathext}")
        return False

    current_pathext = current_pathext.strip()

    # Check if .OST is in PATHEXT
    if ".OST" not in current_pathext.upper():
        click.echo("ℹ️  .OST not in PATHEXT")
        return True

    # Remove .OST from PATHEXT
    new_pathext = (
        current_pathext.replace(";.OST", "")
        .replace(".OST;", "")
        .replace(".OST", "")
    )
    setx_cmd = f'setx PATHEXT "{new_pathext}"'
    exit_code, output = run_windows_command(setx_cmd)

    if exit_code != 0:
        click.echo(f"❌ Failed to update PATHEXT: {output}")
        return False

    click.echo("✅ .OST removed from PATHEXT successfully")
    return True


@click.group(name="setup")
def setup() -> None:
    """Environment setup and configuration commands."""
    pass


@setup.command(name="windows-register")
def windows_register() -> None:
    """Register OST file associations and PATHEXT on Windows.

    This command:
    - Creates a global OST runner in %LOCALAPPDATA%\\ostruct
    - Registers .ost file association with Windows
    - Adds .OST to PATHEXT environment variable

    After running this, you can execute .ost files directly from cmd.exe.
    """
    if not is_windows():
        click.echo("❌ This command is only available on Windows")
        sys.exit(1)

    click.echo("🚀 Setting up Windows OST integration...")

    try:
        # Create global runner
        runner_path = create_global_ost_runner()
        click.echo(f"✅ Created global OST runner: {runner_path}")

        # Register file association
        if not register_ost_file_association():
            sys.exit(1)

        # Add to PATHEXT
        if not add_ost_to_pathext():
            sys.exit(1)

        click.echo()
        click.echo("🎉 Windows OST integration setup complete!")
        click.echo("You can now execute .ost files directly from cmd.exe")
        click.echo("Example: hello_cli.ost --help")

    except Exception as e:
        click.echo(f"❌ Setup failed: {e}")
        sys.exit(1)


@setup.command(name="windows-unregister")
def windows_unregister() -> None:
    """Unregister OST file associations and PATHEXT on Windows.

    This command reverses the changes made by windows-register:
    - Removes .ost file association from Windows
    - Removes .OST from PATHEXT environment variable
    - Optionally removes the global OST runner
    """
    if not is_windows():
        click.echo("❌ This command is only available on Windows")
        sys.exit(1)

    click.echo("🧹 Removing Windows OST integration...")

    try:
        # Remove file association
        if not unregister_ost_file_association():
            click.echo("⚠️  Some file associations may not have been removed")

        # Remove from PATHEXT
        if not remove_ost_from_pathext():
            click.echo("⚠️  Failed to remove .OST from PATHEXT")

        # Ask about removing global runner
        launcher_dir = get_ostruct_launcher_dir()
        if launcher_dir.exists():
            if click.confirm(
                f"Remove global OST runner directory ({launcher_dir})?"
            ):
                shutil.rmtree(launcher_dir)
                click.echo(f"🗑️  Removed: {launcher_dir}")

        click.echo()
        click.echo("✅ Windows OST integration removed successfully")

    except Exception as e:
        click.echo(f"❌ Unregistration failed: {e}")
        sys.exit(1)
