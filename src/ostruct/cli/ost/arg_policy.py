"""Argument policy enforcement for OST templates.

This module handles policy enforcement for global ostruct arguments,
including fixed values, allowed lists, blocked flags, and alias resolution.
"""

import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PolicyMode(Enum):
    """Policy enforcement modes for global arguments."""

    FIXED = "fixed"
    PASS_THROUGH = "pass-through"
    ALLOWED = "allowed"
    BLOCKED = "blocked"


class PolicyViolationError(Exception):
    """Raised when a policy violation is detected."""

    pass


class ArgumentPolicy:
    """Policy configuration for a single argument."""

    def __init__(
        self,
        mode: PolicyMode,
        value: Any = None,
        allowed: Optional[List[str]] = None,
        default: Any = None,
    ) -> None:
        """Initialize argument policy.

        Args:
            mode: Policy enforcement mode
            value: Fixed value (for FIXED mode)
            allowed: List of allowed values (for ALLOWED mode)
            default: Default value (for PASS_THROUGH mode)
        """
        self.mode = mode
        self.value = value
        self.allowed = allowed or []
        self.default = default

    def enforce(self, flag: str, provided_value: Any) -> Any:
        """Enforce policy for a given flag and value.

        Args:
            flag: The flag name
            provided_value: The value provided by the user

        Returns:
            The value to use (may be modified by policy)

        Raises:
            PolicyViolationError: If policy is violated
        """
        if self.mode == PolicyMode.FIXED:
            if provided_value is not None and provided_value != self.value:
                raise PolicyViolationError(
                    f"Flag '{flag}' is fixed to '{self.value}', "
                    f"but '{provided_value}' was provided"
                )
            return self.value

        elif self.mode == PolicyMode.BLOCKED:
            if provided_value is not None:
                raise PolicyViolationError(
                    f"Flag '{flag}' is blocked by policy"
                )
            return None

        elif self.mode == PolicyMode.ALLOWED:
            if provided_value is not None:
                if str(provided_value) not in self.allowed:
                    raise PolicyViolationError(
                        f"Flag '{flag}' value '{provided_value}' not in allowed list: {self.allowed}"
                    )
            return (
                provided_value if provided_value is not None else self.default
            )

        elif self.mode == PolicyMode.PASS_THROUGH:
            return (
                provided_value if provided_value is not None else self.default
            )

        else:
            raise ValueError(f"Unknown policy mode: {self.mode}")


class GlobalArgsPolicyEnforcer:
    """Enforces global argument policies for OST templates."""

    # Common flag aliases mapping short to long form
    FLAG_ALIASES = {
        "-m": "--model",
        "-v": "--verbose",
        "-d": "--debug",
        "-h": "--help",
        "-V": "--version",
    }

    # Boolean flags that don't take values
    BOOLEAN_FLAGS = {
        "--verbose",
        "--debug",
        "--help",
        "--version",
        "--dry-run",
        "--dry-run-json",
    }

    # Repeatable flags that can appear multiple times
    REPEATABLE_FLAGS = {
        "--var",
        "--json-var",
        "--file",
        "--dir",
        "--collect",
        "--enable-tool",
        "--mcp-server",
    }

    def __init__(self, global_args_config: Dict[str, Dict[str, Any]]) -> None:
        """Initialize policy enforcer.

        Args:
            global_args_config: Global args configuration from front-matter
        """
        self.policies: Dict[str, ArgumentPolicy] = {}

        # Parse policy configurations
        for flag, config in global_args_config.items():
            # Skip non-flag configuration options
            if flag == "pass_through_global":
                continue

            if not isinstance(config, dict):
                raise ValueError(
                    f"Configuration for flag '{flag}' must be a dictionary"
                )

            mode_str = config.get("mode", "pass-through")
            try:
                mode = PolicyMode(mode_str)
            except ValueError:
                raise ValueError(
                    f"Invalid policy mode '{mode_str}' for flag '{flag}'"
                )

            policy = ArgumentPolicy(
                mode=mode,
                value=config.get("value"),
                allowed=config.get("allowed"),
                default=config.get("default"),
            )

            # Normalize flag name (add -- prefix if missing)
            normalized_flag = flag if flag.startswith("-") else f"--{flag}"
            self.policies[normalized_flag] = policy

    def resolve_alias(self, flag: str) -> str:
        """Resolve flag alias to its canonical form.

        Args:
            flag: Flag name (may be alias)

        Returns:
            Canonical flag name
        """
        return self.FLAG_ALIASES.get(flag, flag)

    def parse_flag_value(self, flag: str, value: str) -> Any:
        """Parse flag value based on flag type.

        Args:
            flag: Flag name
            value: Raw string value

        Returns:
            Parsed value
        """
        if flag in self.BOOLEAN_FLAGS:
            # Boolean flags: presence = True, absence = False
            return (
                value.lower() in ("true", "1", "yes", "on") if value else True
            )

        # For repeatable flags, handle comma-separated values
        if flag in self.REPEATABLE_FLAGS and "," in value:
            return [v.strip() for v in value.split(",")]

        return value

    def enforce_policies(
        self, args: List[str], pass_through_global: bool = True
    ) -> Tuple[List[str], List[str]]:
        """Enforce policies on command line arguments.

        Args:
            args: Command line arguments
            pass_through_global: Whether to pass through unknown global flags

        Returns:
            Tuple of (sanitized_args, unknown_args)

        Raises:
            PolicyViolationError: If policy is violated
        """
        sanitized: List[str] = []
        unknown: List[str] = []
        i = 0

        while i < len(args):
            arg = args[i]

            # Skip non-flag arguments
            if not arg.startswith("-"):
                sanitized.append(arg)
                i += 1
                continue

            # Handle --flag=value format
            if "=" in arg:
                flag, value = arg.split("=", 1)
                next_value = None
                next_value = value
            else:
                flag = arg
                # Look ahead for value
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    next_value = args[i + 1]
                    i += 1  # Consume the value
                else:
                    next_value = None

            # Resolve alias
            canonical_flag = self.resolve_alias(flag)

            # Parse value
            if next_value is not None:
                parsed_value = self.parse_flag_value(
                    canonical_flag, next_value
                )
            elif canonical_flag in self.BOOLEAN_FLAGS:
                parsed_value = True
            else:
                parsed_value = None

            # Check if we have a policy for this flag
            if canonical_flag in self.policies:
                try:
                    enforced_value = self.policies[canonical_flag].enforce(
                        canonical_flag, parsed_value
                    )

                    # Add to sanitized args if not blocked
                    if enforced_value is not None:
                        if canonical_flag in self.BOOLEAN_FLAGS:
                            if enforced_value:
                                sanitized.append(canonical_flag)
                        else:
                            sanitized.append(canonical_flag)
                            if isinstance(enforced_value, list):
                                # Handle repeatable flags
                                for val in enforced_value:
                                    sanitized.append(str(val))
                            else:
                                sanitized.append(str(enforced_value))

                except PolicyViolationError as e:
                    # Exit with code 2 for policy violations
                    print(f"Policy violation: {e}", file=sys.stderr)
                    sys.exit(2)

            else:
                # Unknown flag
                if pass_through_global:
                    # Pass through unknown flags
                    sanitized.append(flag)
                    if next_value is not None:
                        sanitized.append(next_value)
                else:
                    # Error on unknown flags
                    print(
                        f"Error: unrecognized flag '{flag}'", file=sys.stderr
                    )
                    sys.exit(2)

            i += 1

        return sanitized, unknown

    def get_policy_table(self) -> List[Tuple[str, str, str]]:
        """Get policy table for help display.

        Returns:
            List of (flag, mode, description) tuples
        """
        table = []
        for flag, policy in self.policies.items():
            if policy.mode == PolicyMode.FIXED:
                desc = f"Fixed to '{policy.value}'"
            elif policy.mode == PolicyMode.BLOCKED:
                desc = "Blocked"
            elif policy.mode == PolicyMode.ALLOWED:
                desc = f"Allowed: {', '.join(policy.allowed)}"
            else:
                desc = (
                    f"Default: {policy.default}"
                    if policy.default
                    else "Pass-through"
                )

            table.append((flag, policy.mode.value, desc))

        return sorted(table)


def create_policy_enforcer(
    global_args_config: Optional[Dict[str, Dict[str, Any]]],
) -> Optional[GlobalArgsPolicyEnforcer]:
    """Create a policy enforcer from front-matter configuration.

    Args:
        global_args_config: Global args configuration from front-matter

    Returns:
        Policy enforcer instance, or None if no policies defined
    """
    if not global_args_config:
        return None

    return GlobalArgsPolicyEnforcer(global_args_config)
