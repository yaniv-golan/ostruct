"""Tests to verify and document pyfakefs symlink behavior.

This test suite serves multiple purposes:
1. Documentation:
   - Demonstrates how pyfakefs handles different symlink scenarios
   - Shows differences from real filesystem behavior
   - Provides clear examples with print statements and logging

2. Regression Testing:
   - Ensures pyfakefs behavior remains consistent across versions
   - Our symlink resolution logic depends on these behaviors:
     * readlink() works on loop members
     * is_symlink() works on loop members
     * exists() returns False for loops
     * No ELOOP errors are raised

3. Development Aid:
   - New developers can run these tests to understand symlink behavior
   - Helps debug issues by providing known behavior baselines
   - Complements the error classification tests

Test Scenarios:
1. Simple symlinks
2. Nested symlink chains
3. Symlink loops
4. Existence checks on symlinks
5. Broken symlinks
6. Chains leading to broken links

Note: These tests intentionally use print statements and detailed logging
to make the behavior explicit. They should be kept as reference even though
we now understand the behavior they document.
"""

import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem


def test_simple_symlink(fs: FakeFilesystem) -> None:
    """Test basic symlink to real file behavior.

    pyfakefs behavior:
    - is_symlink() correctly identifies symlinks
    - exists() returns True for valid symlinks
    - readlink() returns the target path
    - os.path.exists() matches Path.exists()
    """
    # Create a real file
    fs.create_file("/test/real.txt", contents="real")
    # Create symlink to it
    fs.create_symlink("/test/link.txt", "/test/real.txt")

    link_path = Path("/test/link.txt")
    real_path = Path("/test/real.txt")

    print("\nSimple Symlink Test:")
    print(f"link_path.exists(): {link_path.exists()}")
    print(f"link_path.is_symlink(): {link_path.is_symlink()}")
    print(f"real_path.exists(): {real_path.exists()}")
    print(f"os.path.exists(link_path): {os.path.exists(str(link_path))}")
    print(f"os.readlink(link_path): {os.readlink(str(link_path))}")

    # Valid symlink behavior assertions
    assert link_path.exists()  # Link exists because target exists
    assert link_path.is_symlink()  # Correctly identified as symlink
    assert real_path.exists()  # Target file exists
    assert os.path.exists(str(link_path))  # os.path.exists matches Path.exists
    assert (
        os.readlink(str(link_path)) == "/test/real.txt"
    )  # readlink returns target


def test_nested_symlink_chain(fs: FakeFilesystem) -> None:
    """Test chain of symlinks pointing to a real file.

    pyfakefs behavior:
    - All links in valid chain exist
    - is_symlink() works for all chain members
    - readlink() returns immediate target for each link
    - Chain resolves correctly to final target
    """
    # Create a real file
    fs.create_file("/test/real.txt", contents="real")
    # Create chain: link3 -> link2 -> link1 -> real
    fs.create_symlink("/test/link1.txt", "/test/real.txt")
    fs.create_symlink("/test/link2.txt", "/test/link1.txt")
    fs.create_symlink("/test/link3.txt", "/test/link2.txt")

    link3_path = Path("/test/link3.txt")
    link2_path = Path("/test/link2.txt")
    link1_path = Path("/test/link1.txt")
    real_path = Path("/test/real.txt")

    print("\nNested Symlink Chain Test:")
    print(f"link3_path.exists(): {link3_path.exists()}")
    print(f"link2_path.exists(): {link2_path.exists()}")
    print(f"link1_path.exists(): {link1_path.exists()}")
    print(f"real_path.exists(): {real_path.exists()}")
    print(
        f"os.readlink chain: {os.readlink(str(link3_path))} -> {os.readlink(str(link2_path))} -> {os.readlink(str(link1_path))}"
    )

    # Valid chain behavior assertions
    assert link3_path.exists()  # All links exist because final target exists
    assert link2_path.exists()
    assert link1_path.exists()
    assert real_path.exists()  # Final target exists
    assert link3_path.is_symlink()  # All are identified as symlinks
    assert link2_path.is_symlink()
    assert link1_path.is_symlink()
    # Each readlink returns its immediate target
    assert os.readlink(str(link3_path)) == "/test/link2.txt"
    assert os.readlink(str(link2_path)) == "/test/link1.txt"
    assert os.readlink(str(link1_path)) == "/test/real.txt"


def test_symlink_loop(fs: FakeFilesystem) -> None:
    """Test behavior of symlink loops.

    pyfakefs behavior:
    - is_symlink() returns True for all links in loop
    - exists() returns False for all links in loop
    - readlink() works correctly on loop members
    - No ELOOP error is raised
    """
    # Create a loop: link1 -> link2 -> link1
    fs.create_symlink("/test/link1.txt", "/test/link2.txt")
    fs.create_symlink("/test/link2.txt", "/test/link1.txt")

    link1_path = Path("/test/link1.txt")
    link2_path = Path("/test/link2.txt")

    print("\nSymlink Loop Test:")
    print(f"link1_path.exists(): {link1_path.exists()}")
    print(f"link2_path.exists(): {link2_path.exists()}")
    print(f"link1_path.is_symlink(): {link1_path.is_symlink()}")
    print(f"link2_path.is_symlink(): {link2_path.is_symlink()}")
    print(f"os.readlink(link1): {os.readlink(str(link1_path))}")
    print(f"os.readlink(link2): {os.readlink(str(link2_path))}")

    # Loop behavior assertions
    assert link1_path.is_symlink()  # Links are still recognized as symlinks
    assert link2_path.is_symlink()
    assert not link1_path.exists()  # But they don't "exist" due to the loop
    assert not link2_path.exists()
    assert (
        os.readlink(str(link1_path)) == "/test/link2.txt"
    )  # readlink still works
    assert os.readlink(str(link2_path)) == "/test/link1.txt"


def test_broken_symlink(fs: FakeFilesystem) -> None:
    """Test behavior of broken symlinks.

    pyfakefs behavior:
    - is_symlink() returns True for broken links
    - exists() returns False for broken links
    - readlink() works correctly on broken links
    """
    # Create symlink to non-existent file
    fs.create_symlink("/test/broken.txt", "/test/nonexistent.txt")

    broken_path = Path("/test/broken.txt")
    target_path = Path("/test/nonexistent.txt")

    print("\nBroken Symlink Test:")
    print(f"broken_path.exists(): {broken_path.exists()}")
    print(f"broken_path.is_symlink(): {broken_path.is_symlink()}")
    print(f"target_path.exists(): {target_path.exists()}")
    print(f"os.path.exists(broken_path): {os.path.exists(str(broken_path))}")
    print(f"os.readlink(broken_path): {os.readlink(str(broken_path))}")

    # Broken link behavior assertions
    assert broken_path.is_symlink()  # Still recognized as symlink
    assert not broken_path.exists()  # But doesn't exist
    assert not target_path.exists()  # Target doesn't exist
    assert (
        os.readlink(str(broken_path)) == "/test/nonexistent.txt"
    )  # readlink still works


def test_symlink_to_symlink_to_nonexistent(fs: FakeFilesystem) -> None:
    """Test chain of symlinks where the final target doesn't exist.

    pyfakefs behavior:
    - All links in chain to broken target are treated as broken
    - is_symlink() returns True for all links
    - exists() returns False for all links
    - readlink() works correctly on all links
    """
    # Create chain: link2 -> link1 -> nonexistent
    fs.create_symlink("/test/link1.txt", "/test/nonexistent.txt")
    fs.create_symlink("/test/link2.txt", "/test/link1.txt")

    link2_path = Path("/test/link2.txt")
    link1_path = Path("/test/link1.txt")
    target_path = Path("/test/nonexistent.txt")

    print("\nSymlink to Broken Symlink Test:")
    print(f"link2_path.exists(): {link2_path.exists()}")
    print(f"link2_path.is_symlink(): {link2_path.is_symlink()}")
    print(f"link1_path.exists(): {link1_path.exists()}")
    print(f"link1_path.is_symlink(): {link1_path.is_symlink()}")
    print(f"target_path.exists(): {target_path.exists()}")
    print(
        f"os.readlink chain: {os.readlink(str(link2_path))} -> {os.readlink(str(link1_path))}"
    )

    # Chain to broken link behavior assertions
    assert link2_path.is_symlink()  # All links are still symlinks
    assert link1_path.is_symlink()
    assert not link2_path.exists()  # But none exist due to broken target
    assert not link1_path.exists()
    assert not target_path.exists()
    assert (
        os.readlink(str(link2_path)) == "/test/link1.txt"
    )  # readlink works on all links
    assert os.readlink(str(link1_path)) == "/test/nonexistent.txt"
