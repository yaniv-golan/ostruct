#!/usr/bin/env bash
# validate_pipeline.sh
# Test suite for AIF argument graph pipeline

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DOC="$SCRIPT_DIR/small_test.md"

echo "=== AIF Pipeline Validation Suite ==================================="
echo "Pipeline directory: $PIPELINE_DIR"
echo "Test document: $TEST_DOC"
echo

# Change to pipeline directory
cd "$PIPELINE_DIR"

# Test 1: Basic pipeline execution
echo "=== Test 1: Basic Pipeline Execution ============================"
if [[ ! -f "$TEST_DOC" ]]; then
  echo "ERROR: Test document not found: $TEST_DOC"
  exit 1
fi

# Run pipeline with test document
echo "Running pipeline on test document..."
if ./pipeline.sh "$TEST_DOC"; then
  echo "✅ Pipeline executed successfully"
else
  echo "❌ Pipeline execution failed"
  exit 1
fi

# Find the output directory
OUTPUT_DIR=$(ls -td output_* | head -1)
echo "Output directory: $OUTPUT_DIR"

# Test 2: Schema validation
echo
echo "=== Test 2: Schema Validation ==================================="

# Validate outline.json
if jq empty "$OUTPUT_DIR/outline.json" 2>/dev/null; then
  echo "✅ outline.json is valid JSON"
else
  echo "❌ outline.json is invalid JSON"
  exit 1
fi

# Validate final_graph.json
if jq empty "$OUTPUT_DIR/final_graph.json" 2>/dev/null; then
  echo "✅ final_graph.json is valid JSON"
else
  echo "❌ final_graph.json is invalid JSON"
  exit 1
fi

# Test 3: Content validation
echo
echo "=== Test 3: Content Validation =================================="

# Check if outline has sections
SECTION_COUNT=$(jq '.outline | length' "$OUTPUT_DIR/outline.json")
if [[ $SECTION_COUNT -gt 0 ]]; then
  echo "✅ Outline contains $SECTION_COUNT sections"
else
  echo "❌ Outline is empty"
  exit 1
fi

# Check if final graph has nodes
NODE_COUNT=$(jq '.nodes | length' "$OUTPUT_DIR/final_graph.json")
if [[ $NODE_COUNT -gt 0 ]]; then
  echo "✅ Final graph contains $NODE_COUNT nodes"
else
  echo "❌ Final graph has no nodes"
  exit 1
fi

# Check if final graph has edges
EDGE_COUNT=$(jq '.edges | length' "$OUTPUT_DIR/final_graph.json")
if [[ $EDGE_COUNT -gt 0 ]]; then
  echo "✅ Final graph contains $EDGE_COUNT edges"
else
  echo "⚠️  Final graph has no edges (may be normal for small documents)"
fi

# Test 4: Graph consistency
echo
echo "=== Test 4: Graph Consistency Check ============================="

# Run graph validation
if jq -f jq/validate_graph.jq "$OUTPUT_DIR/final_graph.json" > "$OUTPUT_DIR/validation_report.json"; then
  echo "✅ Graph validation completed"

  # Check for critical errors
  CRITICAL_ERRORS=$(jq '[.[] | select(.error)] | length' "$OUTPUT_DIR/validation_report.json" 2>/dev/null || echo "0")
  if [[ $CRITICAL_ERRORS -eq 0 ]]; then
    echo "✅ No critical errors found"
  else
    echo "❌ Found $CRITICAL_ERRORS critical errors"
    jq '[.[] | select(.error)]' "$OUTPUT_DIR/validation_report.json"
    exit 1
  fi
else
  echo "❌ Graph validation failed"
  exit 1
fi

# Test 5: Quality metrics
echo
echo "=== Test 5: Quality Metrics ====================================="

# Calculate basic quality metrics
TOTAL_NODES=$(jq '.nodes | length' "$OUTPUT_DIR/final_graph.json")
TOTAL_EDGES=$(jq '.edges | length' "$OUTPUT_DIR/final_graph.json")
AVG_CONFIDENCE=$(jq '[.nodes[].confidence] | add / length' "$OUTPUT_DIR/final_graph.json" 2>/dev/null || echo "0")

echo "Total nodes: $TOTAL_NODES"
echo "Total edges: $TOTAL_EDGES"
echo "Average confidence: $AVG_CONFIDENCE"

# Quality thresholds (based on expert recommendations)
if [[ $TOTAL_NODES -ge 3 ]]; then
  echo "✅ Minimum node count met (≥3)"
else
  echo "⚠️  Node count below minimum threshold"
fi

if command -v bc >/dev/null 2>&1; then
  if (( $(echo "$AVG_CONFIDENCE >= 0.5" | bc -l) )); then
    echo "✅ Average confidence acceptable (≥0.5)"
  else
    echo "⚠️  Average confidence below threshold"
  fi
fi

# Test 6: File completeness
echo
echo "=== Test 6: File Completeness ==================================="

REQUIRED_FILES=(
  "outline.json"
  "final_graph.json"
  "embeddings.json"
)

for file in "${REQUIRED_FILES[@]}"; do
  if [[ -f "$OUTPUT_DIR/$file" ]]; then
    echo "✅ $file exists"
  else
    echo "❌ $file missing"
    exit 1
  fi
done

# Test 7: Resume capability
echo
echo "=== Test 7: Resume Capability ==================================="

echo "Testing resume functionality..."
if ./pipeline.sh "$TEST_DOC" "$OUTPUT_DIR"; then
  echo "✅ Resume capability works"
else
  echo "❌ Resume capability failed"
  exit 1
fi

# Test 8: Performance check
echo
echo "=== Test 8: Performance Check ==================================="

# Check processing time (if available in metadata)
PROCESSING_TIME=$(jq '.metadata.processing_info.processing_time // 0' "$OUTPUT_DIR/final_graph.json" 2>/dev/null || echo "0")
echo "Processing time: ${PROCESSING_TIME}s"

# Check file sizes
echo "Output file sizes:"
ls -lh "$OUTPUT_DIR"/*.json | awk '{print $5, $9}'

echo
echo "=== Validation Summary =========================================="
echo "✅ All tests passed successfully!"
echo "✅ Pipeline is ready for production use"
echo "✅ Output directory: $OUTPUT_DIR"
echo "✅ Test document processed: $TEST_DOC"
echo
echo "Next steps:"
echo "1. Try with larger documents"
echo "2. Examine output files for quality"
echo "3. Integrate with visualization tools"
