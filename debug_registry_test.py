#!/usr/bin/env python3

import sys
from unittest.mock import MagicMock, patch

from openai_model_registry import ModelRegistry

from ostruct.cli.registry_updates import check_for_registry_updates
from tests.test_registry_updates import (
    RegistryUpdateResult,
    RegistryUpdateStatus,
)

sys.path.insert(0, ".")

print("=== Testing with global mock only ===")
with patch(
    "ostruct.cli.registry_updates.should_check_for_updates", return_value=True
):
    with patch("ostruct.cli.registry_updates._save_last_check_time"):
        result = check_for_registry_updates()
        print(f"Result with global mock: {result}")

# Now let's see what the global mock actually returns

registry = ModelRegistry.get_instance()
update_result = registry.check_for_updates()
print(f"Global mock result: {update_result}")
print(f"Global mock status: {update_result.status}")
print(f"Global mock status.value: {update_result.status.value}")
print(
    f'Is status.value == "update_available"?: {update_result.status.value == "update_available"}'
)
print(
    f'Is status.value == "already_current"?: {update_result.status.value == "already_current"}'
)

# Let's also check what happens when we try to patch
print("\n=== Testing with patch ===")
with patch(
    "ostruct.cli.registry_updates.should_check_for_updates", return_value=True
):
    with patch("ostruct.cli.registry_updates._save_last_check_time"):
        with patch(
            "openai_model_registry.ModelRegistry.get_instance"
        ) as mock_get_instance:
            mock_registry = MagicMock()
            mock_result = RegistryUpdateResult(
                status=RegistryUpdateStatus.ALREADY_CURRENT,
                message="Up to date",
                success=True,
            )
            mock_registry.check_for_updates.return_value = mock_result
            mock_get_instance.return_value = mock_registry

            result = check_for_registry_updates()
            print(f"Result with patch: {result}")
            print(f"Was mock called?: {mock_get_instance.called}")
