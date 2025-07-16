"""Tests for OST argument policy enforcement."""

from unittest.mock import patch

import pytest
from ostruct.cli.ost.arg_policy import (
    ArgumentPolicy,
    GlobalArgsPolicyEnforcer,
    PolicyMode,
    PolicyViolationError,
    create_policy_enforcer,
)


class TestArgumentPolicy:
    """Tests for ArgumentPolicy class."""

    def test_fixed_mode_valid(self) -> None:
        """Test fixed mode with valid value."""
        policy = ArgumentPolicy(PolicyMode.FIXED, value="gpt-4o")
        result = policy.enforce("--model", "gpt-4o")
        assert result == "gpt-4o"

    def test_fixed_mode_none_value(self) -> None:
        """Test fixed mode with None provided value."""
        policy = ArgumentPolicy(PolicyMode.FIXED, value="gpt-4o")
        result = policy.enforce("--model", None)
        assert result == "gpt-4o"

    def test_fixed_mode_violation(self) -> None:
        """Test fixed mode with invalid value."""
        policy = ArgumentPolicy(PolicyMode.FIXED, value="gpt-4o")
        with pytest.raises(
            PolicyViolationError, match="Flag '--model' is fixed to 'gpt-4o'"
        ):
            policy.enforce("--model", "gpt-3.5-turbo")

    def test_blocked_mode_none(self) -> None:
        """Test blocked mode with None value."""
        policy = ArgumentPolicy(PolicyMode.BLOCKED)
        result = policy.enforce("--enable-tool", None)
        assert result is None

    def test_blocked_mode_violation(self) -> None:
        """Test blocked mode with provided value."""
        policy = ArgumentPolicy(PolicyMode.BLOCKED)
        with pytest.raises(
            PolicyViolationError,
            match="Flag '--enable-tool' is blocked by policy",
        ):
            policy.enforce("--enable-tool", "web-search")

    def test_allowed_mode_valid(self) -> None:
        """Test allowed mode with valid value."""
        policy = ArgumentPolicy(
            PolicyMode.ALLOWED, allowed=["gpt-4o", "gpt-3.5-turbo"]
        )
        result = policy.enforce("--model", "gpt-4o")
        assert result == "gpt-4o"

    def test_allowed_mode_default(self) -> None:
        """Test allowed mode with default value."""
        policy = ArgumentPolicy(
            PolicyMode.ALLOWED,
            allowed=["gpt-4o", "gpt-3.5-turbo"],
            default="gpt-4o",
        )
        result = policy.enforce("--model", None)
        assert result == "gpt-4o"

    def test_allowed_mode_violation(self) -> None:
        """Test allowed mode with invalid value."""
        policy = ArgumentPolicy(
            PolicyMode.ALLOWED, allowed=["gpt-4o", "gpt-3.5-turbo"]
        )
        with pytest.raises(
            PolicyViolationError,
            match="Flag '--model' value 'invalid' not in allowed list",
        ):
            policy.enforce("--model", "invalid")

    def test_pass_through_mode_value(self) -> None:
        """Test pass-through mode with provided value."""
        policy = ArgumentPolicy(PolicyMode.PASS_THROUGH)
        result = policy.enforce("--model", "gpt-4o")
        assert result == "gpt-4o"

    def test_pass_through_mode_default(self) -> None:
        """Test pass-through mode with default value."""
        policy = ArgumentPolicy(PolicyMode.PASS_THROUGH, default="gpt-4o")
        result = policy.enforce("--model", None)
        assert result == "gpt-4o"

    def test_pass_through_mode_none(self) -> None:
        """Test pass-through mode with no default."""
        policy = ArgumentPolicy(PolicyMode.PASS_THROUGH)
        result = policy.enforce("--model", None)
        assert result is None


class TestGlobalArgsPolicyEnforcer:
    """Tests for GlobalArgsPolicyEnforcer class."""

    def test_init_valid_config(self) -> None:
        """Test initialization with valid configuration."""
        config = {
            "model": {"mode": "fixed", "value": "gpt-4o"},
            "temperature": {"mode": "pass-through", "default": 0.7},
            "enable-tool": {"mode": "blocked"},
        }
        enforcer = GlobalArgsPolicyEnforcer(config)
        assert len(enforcer.policies) == 3
        assert enforcer.policies["--model"].mode == PolicyMode.FIXED
        assert (
            enforcer.policies["--temperature"].mode == PolicyMode.PASS_THROUGH
        )
        assert enforcer.policies["--enable-tool"].mode == PolicyMode.BLOCKED

    def test_init_invalid_mode(self) -> None:
        """Test initialization with invalid mode."""
        config = {"model": {"mode": "invalid_mode", "value": "gpt-4o"}}
        with pytest.raises(
            ValueError, match="Invalid policy mode 'invalid_mode'"
        ):
            GlobalArgsPolicyEnforcer(config)

    def test_resolve_alias(self) -> None:
        """Test flag alias resolution."""
        enforcer = GlobalArgsPolicyEnforcer({})
        assert enforcer.resolve_alias("-m") == "--model"
        assert enforcer.resolve_alias("--model") == "--model"
        assert enforcer.resolve_alias("--unknown") == "--unknown"

    def test_parse_flag_value_boolean(self) -> None:
        """Test parsing boolean flag values."""
        enforcer = GlobalArgsPolicyEnforcer({})

        # Boolean flags
        assert enforcer.parse_flag_value("--verbose", None) is True
        assert enforcer.parse_flag_value("--verbose", "true") is True
        assert enforcer.parse_flag_value("--verbose", "false") is False
        assert enforcer.parse_flag_value("--verbose", "1") is True
        assert enforcer.parse_flag_value("--verbose", "0") is False

    def test_parse_flag_value_repeatable(self) -> None:
        """Test parsing repeatable flag values."""
        enforcer = GlobalArgsPolicyEnforcer({})

        # Repeatable flags with comma separation
        result = enforcer.parse_flag_value("--var", "key1=value1,key2=value2")
        assert result == ["key1=value1", "key2=value2"]

        # Single value
        result = enforcer.parse_flag_value("--var", "key=value")
        assert result == "key=value"

    def test_parse_flag_value_regular(self) -> None:
        """Test parsing regular flag values."""
        enforcer = GlobalArgsPolicyEnforcer({})
        result = enforcer.parse_flag_value("--model", "gpt-4o")
        assert result == "gpt-4o"

    def test_enforce_policies_fixed_mode(self) -> None:
        """Test policy enforcement with fixed mode."""
        config = {"model": {"mode": "fixed", "value": "gpt-4o"}}
        enforcer = GlobalArgsPolicyEnforcer(config)

        # Should use fixed value
        args = ["--model", "gpt-3.5-turbo"]
        with patch("sys.exit") as mock_exit:
            enforcer.enforce_policies(args)
            mock_exit.assert_called_with(2)

    def test_enforce_policies_blocked_mode(self) -> None:
        """Test policy enforcement with blocked mode."""
        config = {"enable-tool": {"mode": "blocked"}}
        enforcer = GlobalArgsPolicyEnforcer(config)

        # Should block the flag
        args = ["--enable-tool", "web-search"]
        with patch("sys.exit") as mock_exit:
            enforcer.enforce_policies(args)
            mock_exit.assert_called_with(2)

    def test_enforce_policies_allowed_mode_valid(self) -> None:
        """Test policy enforcement with allowed mode - valid value."""
        config = {
            "model": {
                "mode": "allowed",
                "allowed": ["gpt-4o", "gpt-3.5-turbo"],
            }
        }
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--model", "gpt-4o"]
        sanitized, unknown = enforcer.enforce_policies(args)
        assert sanitized == ["--model", "gpt-4o"]
        assert unknown == []

    def test_enforce_policies_allowed_mode_invalid(self) -> None:
        """Test policy enforcement with allowed mode - invalid value."""
        config = {
            "model": {
                "mode": "allowed",
                "allowed": ["gpt-4o", "gpt-3.5-turbo"],
            }
        }
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--model", "invalid-model"]
        with patch("sys.exit") as mock_exit:
            enforcer.enforce_policies(args)
            mock_exit.assert_called_with(2)

    def test_enforce_policies_pass_through_global_true(self) -> None:
        """Test policy enforcement with pass_through_global=True."""
        config = {}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--unknown-flag", "value"]
        sanitized, unknown = enforcer.enforce_policies(
            args, pass_through_global=True
        )
        assert sanitized == ["--unknown-flag", "value"]
        assert unknown == []

    def test_enforce_policies_pass_through_global_false(self) -> None:
        """Test policy enforcement with pass_through_global=False."""
        config = {}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--unknown-flag", "value"]
        with patch("sys.exit") as mock_exit:
            enforcer.enforce_policies(args, pass_through_global=False)
            mock_exit.assert_called_with(2)

    def test_enforce_policies_boolean_flag(self) -> None:
        """Test policy enforcement with boolean flags."""
        config = {"verbose": {"mode": "pass-through"}}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--verbose"]
        sanitized, unknown = enforcer.enforce_policies(args)
        assert sanitized == ["--verbose"]
        assert unknown == []

    def test_enforce_policies_flag_equals_format(self) -> None:
        """Test policy enforcement with --flag=value format."""
        config = {"model": {"mode": "pass-through"}}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--model=gpt-4o"]
        sanitized, unknown = enforcer.enforce_policies(args)
        assert sanitized == ["--model", "gpt-4o"]
        assert unknown == []

    def test_enforce_policies_non_flag_args(self) -> None:
        """Test policy enforcement preserves non-flag arguments."""
        config = {}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["template.ost", "positional_arg", "--flag", "value"]
        sanitized, unknown = enforcer.enforce_policies(args)
        assert sanitized == [
            "template.ost",
            "positional_arg",
            "--flag",
            "value",
        ]
        assert unknown == []

    def test_enforce_policies_repeatable_flag(self) -> None:
        """Test policy enforcement with repeatable flags."""
        config = {"var": {"mode": "pass-through"}}
        enforcer = GlobalArgsPolicyEnforcer(config)

        args = ["--var", "key1=value1,key2=value2"]
        sanitized, unknown = enforcer.enforce_policies(args)
        assert sanitized == ["--var", "key1=value1", "key2=value2"]
        assert unknown == []

    def test_get_policy_table(self) -> None:
        """Test policy table generation."""
        config = {
            "model": {"mode": "fixed", "value": "gpt-4o"},
            "temperature": {"mode": "pass-through", "default": 0.7},
            "enable-tool": {"mode": "blocked"},
            "output-format": {"mode": "allowed", "allowed": ["json", "yaml"]},
        }
        enforcer = GlobalArgsPolicyEnforcer(config)

        table = enforcer.get_policy_table()
        assert len(table) == 4

        # Check that table is sorted and contains expected entries
        flags = [row[0] for row in table]
        assert flags == sorted(flags)

        # Check specific entries
        fixed_row = next(row for row in table if row[0] == "--model")
        assert fixed_row[1] == "fixed"
        assert "Fixed to 'gpt-4o'" in fixed_row[2]

        blocked_row = next(row for row in table if row[0] == "--enable-tool")
        assert blocked_row[1] == "blocked"
        assert "Blocked" in blocked_row[2]


class TestCreatePolicyEnforcer:
    """Tests for create_policy_enforcer function."""

    def test_create_with_config(self) -> None:
        """Test creating enforcer with valid configuration."""
        config = {"model": {"mode": "fixed", "value": "gpt-4o"}}
        enforcer = create_policy_enforcer(config)
        assert enforcer is not None
        assert isinstance(enforcer, GlobalArgsPolicyEnforcer)

    def test_create_with_none(self) -> None:
        """Test creating enforcer with None configuration."""
        enforcer = create_policy_enforcer(None)
        assert enforcer is None

    def test_create_with_empty_config(self) -> None:
        """Test creating enforcer with empty configuration."""
        enforcer = create_policy_enforcer({})
        assert enforcer is None
