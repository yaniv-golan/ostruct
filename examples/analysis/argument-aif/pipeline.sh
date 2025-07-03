#!/usr/bin/env bash
# argument-aif/pipeline.sh
# =========================================================
# Usage:  ./pipeline.sh path/to/document.md
# Produces: output_<timestamp>/{outline.json,all_nodes.json,final_graph.json,...}

set -euo pipefail

DOC="${1:?Supply a Markdown/OCR-txt document}"
RESUME_DIR="${2:-}"  # Optional: resume from existing output directory

# Environment variable overrides (HIGH-IMPACT IMPROVEMENT)
LINES_PER_CHUNK="${AIF_LINES_PER_CHUNK:-1000}"    # Parameterizable chunking
MIN_NODES_PER_SECTION="${AIF_MIN_NODES:-3}"       # Dynamic node quotas
NODES_PER_100_WORDS="${AIF_NODES_PER_100W:-2.5}"  # Scaling factor

# Resume capability (HIGH-IMPACT IMPROVEMENT)
if [[ -n "$RESUME_DIR" && -d "$RESUME_DIR" ]]; then
  OUTDIR="$RESUME_DIR"
  echo "RESUMING from existing directory: $OUTDIR"
else
  TIMESTAMP=$(date +%s)
  OUTDIR="output_${TIMESTAMP}"
  mkdir -p "$OUTDIR"
fi

# Pass-ordering guard (VALIDATION IMPROVEMENT)
# Track input document checksum to invalidate stale downstream artifacts
DOC_CHECKSUM=$(sha256sum "$DOC" | cut -d' ' -f1)
CHECKSUM_FILE="$OUTDIR/.input_checksum"

if [[ -f "$CHECKSUM_FILE" ]]; then
  STORED_CHECKSUM=$(cat "$CHECKSUM_FILE")
  if [[ "$DOC_CHECKSUM" != "$STORED_CHECKSUM" ]]; then
    echo "WARNING: Input document changed since last run. Clearing downstream artifacts."
    rm -f "$OUTDIR"/{synthesized_graph.json,final_graph.json,embeddings.json,consistency_report.json}
  fi
fi
echo "$DOC_CHECKSUM" > "$CHECKSUM_FILE"

# Document statistics and heuristic targets
WORDCOUNT=$(wc -w < "$DOC")
PAGES=$(( WORDCOUNT / 500 ))           # crude page ≈500w
TARGET_NODES=$(( PAGES * 3 + 40 ))     # ≈3 nodes / page

# Dynamic node quota calculation (EXPERT RECOMMENDATION)
MIN_NODES=$(echo "$WORDCOUNT $MIN_NODES_PER_SECTION $NODES_PER_100_WORDS" | awk '{calc=int($1/100*$3); print (calc < $2) ? $2 : calc}')

echo "Input: $DOC  |  Words: $WORDCOUNT  |  Heuristic pages: $PAGES"
echo "Node target for final graph: $TARGET_NODES (min per section: $MIN_NODES)"
echo "Output dir: $OUTDIR"
echo "Environment: LINES_PER_CHUNK=$LINES_PER_CHUNK, MIN_NODES=$MIN_NODES_PER_SECTION"
echo

# Dependency checking
echo "=== Checking Dependencies ========================================"
command -v ostruct >/dev/null 2>&1 || { echo "ERROR: ostruct not found"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found"; exit 1; }
command -v wc >/dev/null 2>&1 || { echo "ERROR: wc not found"; exit 1; }
command -v split >/dev/null 2>&1 || { echo "ERROR: split not found"; exit 1; }

# Validate input file
[[ -f "$DOC" ]] || { echo "ERROR: Input file '$DOC' not found"; exit 1; }
[[ -r "$DOC" ]] || { echo "ERROR: Input file '$DOC' not readable"; exit 1; }

# Validate template and schema files exist
[[ -f "templates/01_outline.j2" ]] || { echo "ERROR: Template templates/01_outline.j2 not found"; exit 1; }
[[ -f "schemas/outline.json" ]] || { echo "ERROR: Schema schemas/outline.json not found"; exit 1; }

echo "All dependencies verified."
echo

# Error handling wrapper function
run_ostruct() {
  local pass_name="$1"
  shift
  echo "Running $pass_name..."
  if ! ostruct "$@"; then
    echo "ERROR: $pass_name failed"
    exit 1
  fi
}

# PASS 1 - Outline extraction (with resume capability)
echo "=== PASS 1 : Outline ============================================="
if [[ ! -f "$OUTDIR/outline.json" ]]; then
  run_ostruct "outline extraction" run \
    templates/01_outline.j2 schemas/outline.json \
    --file fs:doc "$DOC" \
    --tool-choice file-search \
    --output-file "$OUTDIR/outline.json" \
    --temperature 0
else
  echo "SKIPPING - outline.json already exists (resume mode)"
fi

# Handle empty outline fallback - UTF-8 SAFE VERSION
if [[ $(jq '.outline|length' "$OUTDIR/outline.json") -eq 0 ]] ; then
  echo "Outline empty → invoking UTF-8 safe chunker"

  # Calculate lines per chunk (safer than byte splitting)
  TOTAL_LINES=$(wc -l < "$DOC")
  LINES_PER_CHUNK=$((TOTAL_LINES / 10 + 1))  # Aim for ~10 chunks

  # Use line-based splitting to avoid UTF-8 corruption
  split -l "$LINES_PER_CHUNK" --numeric-suffixes=1 --additional-suffix=.slice "$DOC" "$OUTDIR/chunk_"

  jq -n '{outline:[]}' > "$OUTDIR/outline.json"

  i=0
  for f in "$OUTDIR"/chunk_*.slice ; do
    # Calculate character positions more safely
    if [[ $i -eq 0 ]]; then
      start=0
    else
      start=$(head -n $((i * LINES_PER_CHUNK)) "$DOC" | wc -c)
    fi
    end=$((start + $(wc -c < "$f")))
    id=$(printf "chunk_%03d" $((i+1)))

    jq --arg id "$id" --arg start "$start" --arg end "$end" \
       '.outline += [{"id":$id,"title":$id,"start":($start|tonumber),"end":($end|tonumber)}]' \
       "$OUTDIR/outline.json" > "$OUTDIR/tmp.$$" && mv "$OUTDIR/tmp.$$" "$OUTDIR/outline.json"
    ((i++))
  done

  # Clean up chunk files
  rm -f "$OUTDIR"/chunk_*.slice
fi

# PASS 2 - Section extraction
echo "=== PASS 2 : Section Extraction ================================="
# Use mapfile to avoid subshell issues with while loop
mapfile -t sections_array < <(jq -c '.outline[]' "$OUTDIR/outline.json")

for section in "${sections_array[@]}"; do
  id=$(echo "$section" | jq -r '.id')
  title=$(echo "$section" | jq -r '.title')
  start=$(echo "$section" | jq -r '.start')
  end=$(echo "$section" | jq -r '.end')

  echo "Processing section: $id ($title)"

  # Skip if already exists (resume capability)
  if [[ -f "$OUTDIR/extract_$id.json" ]]; then
    echo "SKIPPING - extract_$id.json already exists (resume mode)"
    continue
  fi

  # Extract section content
  content=$(tail -c "+$((start+1))" "$DOC" | head -c "$((end-start))")

  run_ostruct "section extraction for $id" run \
    templates/02_extract_section.j2 schemas/extraction.json \
    --var section_id="$id" \
    --var section_title="$title" \
    --var section_content="$content" \
    --tool-choice none \
    --output-file "$OUTDIR/extract_$id.json" \
    --temperature 0.1
done

# PASS 3 - Graph synthesis (EXPERT RECOMMENDATION: use --file prompt:)
echo "=== PASS 3 : Graph Synthesis ===================================="
if [[ ! -f "$OUTDIR/synthesized_graph.json" ]]; then
  echo "Running graph synthesis..."
  jq -s '.' "$OUTDIR"/extract_*.json > "$OUTDIR/all_extractions.json"

  # Use --file prompt: to avoid token budget overflow (CRITICAL FIX)
  run_ostruct "graph synthesis" run \
    templates/03_synthesise_graph.j2 schemas/rich_aif.json \
    --file prompt:sections "$OUTDIR/all_extractions.json" \
    --tool-choice none \
    --output-file "$OUTDIR/synthesized_graph.json" \
    --temperature 0.1
else
  echo "SKIPPING - synthesized_graph.json already exists (resume mode)"
fi

# PASS 4 - Global linking
echo "=== PASS 4 : Global Linking ====================================="
if [[ ! -f "$OUTDIR/linked_graph.json" ]]; then
  run_ostruct "global linking" run \
    templates/04_link_global.j2 schemas/rich_aif.json \
    --file prompt:graph "$OUTDIR/synthesized_graph.json" \
    --tool-choice none \
    --output-file "$OUTDIR/linked_graph.json" \
    --temperature 0
else
  echo "SKIPPING - linked_graph.json already exists (resume mode)"
fi

# PASS 5 - Consistency check
echo "=== PASS 5 : Consistency Check =================================="
if [[ ! -f "$OUTDIR/final_graph.json" ]]; then
  run_ostruct "consistency check" run \
    templates/05_consistency_check.j2 schemas/rich_aif.json \
    --file prompt:graph "$OUTDIR/linked_graph.json" \
    --tool-choice none \
    --output-file "$OUTDIR/final_graph.json" \
    --temperature 0
else
  echo "SKIPPING - final_graph.json already exists (resume mode)"
fi

# PASS 6 - Embedding analysis (optional)
echo "=== PASS 6 : Embedding Analysis ================================="
if [[ ! -f "$OUTDIR/embeddings.json" ]]; then
  run_ostruct "embedding analysis" run \
    templates/embed_cosine.j2 schemas/embedding_pairs.json \
    --file prompt:nodes "$OUTDIR/final_graph.json" \
    --tool-choice none \
    --output-file "$OUTDIR/embeddings.json" \
    --temperature 0.2
else
  echo "SKIPPING - embeddings.json already exists (resume mode)"
fi

# Final processing and summary
echo "=== PIPELINE COMPLETE ==========================================="
echo "Output directory: $OUTDIR"
echo "Generated files:"
ls -la "$OUTDIR"/*.json

# Generate summary statistics
if [[ -f "$OUTDIR/final_graph.json" ]]; then
  TOTAL_NODES=$(jq '.nodes | length' "$OUTDIR/final_graph.json")
  TOTAL_EDGES=$(jq '.edges | length' "$OUTDIR/final_graph.json")
  echo
  echo "Final graph statistics:"
  echo "  Nodes: $TOTAL_NODES"
  echo "  Edges: $TOTAL_EDGES"
  echo "  Target was: $TARGET_NODES nodes"
fi

echo
echo "Pipeline completed successfully!"
echo "Main output: $OUTDIR/final_graph.json"
echo "Embeddings: $OUTDIR/embeddings.json"
