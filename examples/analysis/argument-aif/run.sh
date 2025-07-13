#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
source "$ROOT/scripts/examples/standard_runner.sh"

# AIF (Argument Interchange Format) extraction example
# Enhanced with configurable file size limits and better tool integration

run_example() {
  case "$MODE" in
    "test-dry"|"test-live")
      echo "🔹 Testing basic AIF extraction..."
      run_test templates/01_outline.j2 schemas/outline.json \
        --file fs:doc texts/a_letter_to_a_royal_academy_about_farting.txt
      ;;
    "enhanced")
      echo "🚀 Running enhanced extraction with configurable file size limits..."

      # Test 1: Basic extraction with unlimited file size (new default)
      echo "🔹 Basic extraction with unlimited file size..."
      run_ostruct templates/01_outline.j2 schemas/outline.json \
        --file fs:doc texts/test_1page.txt \
        --output-file "output/test_1page_unlimited.json"

      # Test 2: Large document processing (previously blocked by 64KB limit)
      if [[ -f ~/Downloads/R17-long-final.md ]]; then
        echo "🔹 Processing large document (444KB) - now possible with unlimited file size..."
        run_ostruct templates/01_outline.j2 schemas/outline.json \
          --file fs:doc ~/Downloads/R17-long-final.md \
          --output-file "output/large_document_unlimited.json" \
          --path-security permissive
      fi

      # Test 3: Multi-tool enhanced extraction with File Search
      echo "🔹 Enhanced extraction with File Search tool..."
      run_ostruct templates/01_outline.j2 schemas/outline.json \
        --file fs:doc texts/test_1page.txt \
        --output-file "output/test_1page_file_search.json"

      # Test 4: Multi-tool enhanced extraction with Code Interpreter
      echo "🔹 Enhanced extraction with Code Interpreter tool..."
      run_ostruct templates/01_outline.j2 schemas/outline.json \
        --file ci:doc texts/test_1page.txt \
        --output-file "output/test_1page_code_interpreter.json"

      # Test 5: Combined multi-tool approach for maximum accuracy
      echo "🔹 Combined multi-tool extraction for maximum accuracy..."
      run_ostruct templates/01_outline.j2 schemas/outline.json \
        --file fs:doc texts/test_1page.txt \
        --file ci:doc texts/test_1page.txt \
        --output-file "output/test_1page_multi_tool.json"

      # Test 6: Demonstrate configurable file size limits
      echo "🔹 Testing configurable file size limits..."
      echo "   - This will show a warning but still process with lazy loading:"
      run_ostruct templates/01_outline.j2 schemas/outline.json \
        --file fs:doc texts/test_1page.txt \
        --max-file-size 2000 \
        --output-file "output/test_1page_size_limited.json" || true

      echo "✅ Enhanced extraction completed successfully"
      echo ""
      echo "📊 Key improvements demonstrated:"
      echo "   ✅ Removed 64KB file size limit (now unlimited by default)"
      echo "   ✅ Configurable limits via --max-file-size or OSTRUCT_MAX_FILE_SIZE"
      echo "   ✅ Better tool integration with automatic variable detection"
      echo "   ✅ Enhanced template with conditional multi-tool instructions"
      echo "   ✅ Large document processing capabilities"
      ;;
  esac
}

# Parse arguments (no custom arguments needed for this example)
parse_args_with_getoptions "$@" <<'EOF'
EOF

execute_mode
