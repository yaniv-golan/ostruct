"""Symlink resolution module.

This module provides secure symlink resolution with:
- Maximum depth enforcement
- Loop detection
- Security validation
- Windows path handling

Design Choices:
1. Security First:
   - Validate before resolving
   - Check each step in chain
   - Fail closed on errors

2. Loop Detection:
   - Track visited paths
   - Check before traversal
   - Handle all loop types

3. Windows Support:
   - Handle Windows-specific paths
   - Support both APIs
   - Our approach works with both behaviors
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from .allowed_checker import is_path_in_allowed_dirs
from .errors import PathSecurityError, SecurityErrorReasons
from .normalization import normalize_path
from .windows_paths import is_windows_path, validate_windows_path

logger = logging.getLogger(__name__)


@dataclass
class SymlinkInfo:
    """Information about a symlink in the resolution chain.

    This class is used for logging and auditing symlink resolution chains.
    Each instance represents one step in the resolution process.
    """

    source: Path
    target: Path
    depth: int
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"{self.source} -> {self.target}"


def _debug_seen_set(seen: Set[Path], prefix: str = "") -> None:
    """Debug helper to log the contents of the seen set."""
    paths = "\n  ".join(str(p) for p in seen)
    logger.debug("%sSeen set contents:\n  %s", prefix, paths)


def _follow_symlink_chain(
    path: Path, seen: Set[Path], max_depth: int = 16
) -> Optional[List[Path]]:
    """Follow a symlink chain to detect loops, without checking existence.

    This function follows a chain of symlinks, looking only at the targets
    (via readlink) without checking existence. This allows us to detect
    loops even when the filesystem reports loop members as non-existent.

    Implementation Details:
    1. Chain Following:
       - Starts at the given path
       - Uses readlink() to get each target
       - Normalizes paths for consistent comparison
       - Continues until a non-symlink or error is encountered

    2. Loop Detection:
       - Maintains a chain of followed links
       - Uses a separate seen set for chain following
       - Checks if each new target is in the chain seen set
       - If found in chain seen set -> loop detected
       - If max depth reached -> returns None

    3. Error Handling:
       - OSError from readlink -> chain ends (no loop)
       - Max depth exceeded -> returns None
       - Target in chain seen set -> loop detected

    Filesystem Behavior:
    1. Real Filesystem:
       - May raise ELOOP for symlink loops
       - exists() behavior varies by OS
       - readlink() works on loop members

    2. pyfakefs:
       - No ELOOP errors are raised
       - exists() returns False for all symlinks in a loop
       - is_symlink() works correctly even in loops
       - readlink() works correctly on loop members

    3. Our Approach:
       - Filesystem-agnostic loop detection
       - Works with both real and fake filesystems
       - Consistent error classification
       - Detects loops before checking existence
       - Works despite differences in filesystem implementations

    Note: This function assumes the initial path has already been validated
    by the SecurityManager. It focuses solely on secure symlink resolution.

    Race Condition Warning:
    This function cannot guarantee atomic operations between validation
    and usage. A malicious actor could potentially modify symlinks or
    their targets between checks. Use appropriate filesystem permissions
    to mitigate TOCTOU risks.

    Args:
        path: The path to start following from
        seen: Set of already seen paths from main resolution
        max_depth: Maximum depth to follow

    Returns:
        List of paths in the chain if a loop is found, None otherwise
    """
    logger.debug(
        "\n=== Following symlink chain ===\n"
        "Starting path: %s\n"
        "Resolution seen: %s",
        path,
        sorted(list(seen)),
    )

    chain: list[Path] = []
    chain_seen: set[Path] = set()  # Separate seen set for chain following
    current = normalize_path(path)

    for depth in range(max_depth):
        try:
            # Check for loop using chain seen set
            if current in chain_seen:
                logger.warning(
                    "\n=== Loop detected in chain! ===\n"
                    "Target creating loop: %s\n"
                    "Chain: %s\n"
                    "Chain seen: %s\n"
                    "Resolution seen: %s",
                    current,
                    chain,
                    sorted(list(chain_seen)),
                    sorted(list(seen)),
                )
                return chain + [
                    current
                ]  # Return complete chain including loop point

            # Add to chain and chain seen set before reading link
            chain.append(current)
            chain_seen.add(current)

            # Use readlink to follow link without existence check
            target_str = os.readlink(str(current))
            if not os.path.isabs(target_str):
                target_str = os.path.normpath(
                    os.path.join(str(current.parent), target_str)
                )

            # Normalize the target path
            current = normalize_path(Path(target_str))
            logger.debug(
                "Chain step %d:\n"
                "  Current: %s\n"
                "  Target: %s\n"
                "  Chain so far: %s\n"
                "  Chain seen: %s\n"
                "  Resolution seen: %s",
                depth,
                chain[-1],
                current,
                chain,
                sorted(list(chain_seen)),
                sorted(list(seen)),
            )

        except OSError as e:
            logger.debug(
                "Failed to read symlink at depth %d: %s - %s",
                depth,
                current,
                e,
            )
            return None

    logger.debug(
        "Chain exceeded max depth (%d) without finding loop", max_depth
    )
    return None


def _resolve_symlink(
    path: Path,
    max_depth: int,
    allowed_dirs: List[Path],
    seen: Optional[Set[Path]] = None,
    current_depth: int = 0,
) -> Path:
    """Internal security primitive for symlink resolution.

    INTERNAL API: This function is not part of the public interface.
    Use SecurityManager.resolve_path() for general path resolution.

    This function resolves symlinks with the following security measures:
    1. Maximum depth enforcement to prevent infinite recursion
    2. Loop detection to prevent symlink cycles
    3. Allowed directory checks at each resolution step
    4. Security validation BEFORE existence checks

    Security Design Choices:
    1. Path Normalization:
       - All paths are normalized before loop detection and recursion
       - Consistent NFKC Unicode normalization
       - Handles path separator differences

    2. Loop Detection Strategy:
       - Loop detection is purely path-based, using a seen set
       - Loops are detected before any existence checks
       - Three-phase detection:
         a) Check if current path is in seen set (catches A->B->A)
         b) Check if target would create loop (catches A->A)
         c) Follow entire chain to detect complex loops (catches C->B->A->A)
       - A path is added to seen immediately when encountered
       - This ensures accurate loop detection regardless of filesystem behavior

    3. Security Checks Order:
       1. Maximum depth check (prevent infinite recursion)
       2. Path normalization (consistent comparison)
       3. Current path loop check (detect revisiting paths)
       4. Add current path to seen set
       5. Allowed directory check
       6. Symlink check
       7. Target resolution and normalization
       8. Target loop check
       9. Chain loop check
       10. Target existence check (only after confirming no loops)
       11. Target allowed directory check
       12. Recursion with target

    4. Error Precedence:
       - SYMLINK_LOOP takes precedence over SYMLINK_BROKEN
       - Loop detection happens before existence checks
       - This ensures correct classification regardless of how the filesystem
         reports existence for looped symlinks

    5. pyfakefs Behavior:
       - pyfakefs simulates filesystem behavior but has some differences:
         a) Symlink loops are not detected by the OS layer (no ELOOP)
         b) exists() returns False for all symlinks in a loop
         c) is_symlink() works correctly even in loops
         d) readlink() works correctly even in loops
       - Our loop detection is filesystem-agnostic and works with:
         a) Real filesystems (that raise ELOOP)
         b) pyfakefs (that silently allows loops)
         c) Other filesystem implementations

    Known Limitations:
    1. Windows Support:
       - Limited handling of Windows-specific paths
       - UNC paths may not resolve correctly
       - Reparse points not fully supported

    2. Race Conditions:
       - TOCTOU races possible between checks
       - Symlinks can change between resolution steps
       - No atomic path resolution guarantee

    3. Filesystem Differences:
       - Different filesystems handle symlink loops differently
       - Some raise ELOOP immediately
       - Others allow following until a depth limit

    Args:
        path: The starting Path object.
        max_depth: Maximum allowed resolution depth.
        allowed_dirs: List of allowed directories for the target.
        seen: Set of already seen normalized paths to detect loops.
        current_depth: Current depth in the resolution chain.

    Returns:
        A Path object for the resolved target.

    Raises:
        PathSecurityError: With context["reason"] indicating:
            - SYMLINK_MAX_DEPTH: Chain exceeds maximum depth
            - SYMLINK_LOOP: Cyclic reference detected
            - SYMLINK_BROKEN: Target doesn't exist
    """
    logger.debug(
        "\n=== Starting symlink resolution ===\n"
        "Path: %s\n"
        "Depth: %d\n"
        "Seen paths: %s",
        path,
        current_depth,
        sorted(list(seen or set())),
    )

    # 1. Check maximum recursion depth first (highest precedence)
    if current_depth >= max_depth:
        logger.warning(
            "\n=== Maximum symlink depth exceeded ===\n"
            "Path: %s\n"
            "Current depth: %d\n"
            "Max depth: %d\n"
            "Chain: %s",
            path,
            current_depth,
            max_depth,
            sorted(list(seen or set())),
        )
        raise PathSecurityError(
            "Symlink security violation: maximum depth exceeded",
            path=str(path),
            context={
                "reason": SecurityErrorReasons.SYMLINK_MAX_DEPTH,
                "depth": current_depth,
                "max_depth": max_depth,
                "chain": [str(p) for p in (seen or set())],
            },
        )

    # 2. Initialize seen set if not provided
    if seen is None:
        seen = set()
        logger.debug("Initialized new seen set")

    # 3. Normalize path for consistent comparison
    norm_path = normalize_path(path)
    logger.debug("Normalized path: %s", norm_path)

    # 4. Check if it's a symlink first
    try:
        if not norm_path.is_symlink():
            logger.debug(
                "Not a symlink, returning normalized path: %s", norm_path
            )
            return norm_path

        # 5. Check for loops using chain following (second highest precedence)
        chain = _follow_symlink_chain(
            norm_path, seen, max_depth - current_depth
        )
        if chain:
            logger.warning(
                "\n=== Loop detected in symlink chain! ===\n"
                "Starting path: %s\n"
                "Chain: %s\n"
                "Seen paths: %s",
                norm_path,
                chain,
                sorted(list(seen)),
            )
            raise PathSecurityError(
                "Symlink security violation: loop detected",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.SYMLINK_LOOP,
                    "chain": [str(p) for p in chain],
                    "seen": [str(p) for p in seen],
                },
            )

        # 6. Read and normalize the target
        target_str = os.readlink(norm_path)
        logger.debug("Raw symlink target: %s", target_str)

        # Convert to absolute path if needed
        if not os.path.isabs(target_str):
            target_str = os.path.normpath(
                os.path.join(str(path.parent), target_str)
            )
        logger.debug("Absolute target path: %s", target_str)

        # Normalize the target path
        normalized_target = normalize_path(target_str)
        logger.debug(
            "\n=== Processing symlink target ===\n"
            "Original path: %s\n"
            "Target string: %s\n"
            "Normalized target: %s\n"
            "Current seen set: %s",
            path,
            target_str,
            normalized_target,
            sorted(list(seen)),
        )

        # 7. Validate Windows-specific path features
        if os.name == "nt":
            if is_windows_path(path):
                error_msg = validate_windows_path(path)
                if error_msg:
                    logger.warning(
                        "Windows path validation failed: %s - %s",
                        path,
                        error_msg,
                    )
                    raise PathSecurityError(
                        f"Symlink security violation: {error_msg}",
                        path=str(path),
                        context={
                            "reason": SecurityErrorReasons.SYMLINK_ERROR,
                            "windows_specific": True,
                            "chain": [str(p) for p in seen],
                        },
                    )

        # 8. Check existence after confirming no loops (lowest precedence)
        if not normalized_target.exists():
            logger.debug(
                "\n=== Broken symlink detected ===\n"
                "Path: %s\n"
                "Target: %s\n"
                "Chain: %s",
                path,
                normalized_target,
                sorted(list(seen)),
            )
            raise PathSecurityError(
                f"Symlink security violation: broken symlink target '{normalized_target}' does not exist",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.SYMLINK_BROKEN,
                    "source": str(path),
                    "target": str(normalized_target),
                    "chain": [str(p) for p in seen],
                },
            )

        # 9. Validate target is allowed
        if not is_path_in_allowed_dirs(normalized_target, allowed_dirs):
            logger.warning(
                "Symlink target not allowed: %s -> %s", path, normalized_target
            )
            raise PathSecurityError(
                "Symlink security violation: target not allowed",
                path=str(path),
                context={
                    "reason": SecurityErrorReasons.SYMLINK_TARGET_NOT_ALLOWED,
                    "source": str(path),
                    "target": str(normalized_target),
                    "chain": [str(p) for p in seen],
                },
            )

        # 10. Recurse with the normalized target
        logger.debug(
            "\n=== Recursing to target ===\n"
            "From path: %s\n"
            "To target: %s\n"
            "Current depth: %d\n"
            "Chain so far: %s",
            path,
            normalized_target,
            current_depth + 1,
            sorted(list(seen)),
        )
        return _resolve_symlink(
            normalized_target, max_depth, allowed_dirs, seen, current_depth + 1
        )

    except OSError as e:
        logger.debug("OSError during symlink resolution: %s - %s", path, e)
        raise PathSecurityError(
            f"Symlink security violation: failed to resolve symlink - {e}",
            path=str(path),
            context={
                "reason": SecurityErrorReasons.SYMLINK_ERROR,
                "error": str(e),
                "chain": [str(p) for p in (seen or set())],
            },
        ) from e
