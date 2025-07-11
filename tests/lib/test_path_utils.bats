#!/usr/bin/env bats

setup() {
  LIB_DIR="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../../examples/agent/lib" && pwd)"
  SANDBOX_PATH="$(mktemp -d)"
  source "$LIB_DIR/path_utils.sh"
}

teardown() {
  rm -rf "$SANDBOX_PATH"
}

@test "file_size returns correct size" {
  echo -n "abc" > "$SANDBOX_PATH/sample.txt"
  run file_size "$SANDBOX_PATH/sample.txt"
  [ "$status" -eq 0 ]
  [ "$output" -eq 3 ]
}

@test "safe_path resolves relative path inside sandbox" {
  run safe_path "foo.txt"
  [ "$status" -eq 0 ]
  [[ "$output" == "$SANDBOX_PATH"/* ]]
}

@test "safe_path blocks escapes" {
  run safe_path "/tmp/evil.txt"
  [ "$status" -ne 0 ]
}
