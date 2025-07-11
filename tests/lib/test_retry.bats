#!/usr/bin/env bats

setup() {
  LIB_DIR="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../../examples/agent/lib" && pwd)"
  source "$LIB_DIR/retry.sh"
  attempt_count=0
}

@test "with_retry succeeds within attempts" {
  flaky() { attempt_count=$((attempt_count+1)); [ $attempt_count -ge 2 ]; }
  run with_retry 3 0.1 0.1 -- flaky
  [ "$status" -eq 0 ]
  [ $attempt_count -eq 2 ]
}

@test "with_retry fails after max attempts" {
  always_fail() { return 1; }
  run with_retry 2 0.1 -- always_fail
  [ "$status" -ne 0 ]
}
