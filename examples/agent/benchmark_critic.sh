#!/bin/bash

# Critic Performance and Cost Analysis
# Comprehensive benchmarking of critic functionality

set -euo pipefail

# Configuration
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$AGENT_DIR/../.." && pwd)"
BENCHMARK_DIR="$AGENT_DIR/benchmark_results"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log_benchmark() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%H:%M:%S')
    case "$level" in
        "INFO") echo -e "[$timestamp] ${BLUE}ℹ INFO${NC}: $message" ;;
        "WARN") echo -e "[$timestamp] ${YELLOW}⚠ WARN${NC}: $message" ;;
        "PASS") echo -e "[$timestamp] ${GREEN}✓ PASS${NC}: $message" ;;
        "FAIL") echo -e "[$timestamp] ${RED}✗ FAIL${NC}: $message" ;;
    esac
}

# Setup benchmark environment
setup_benchmark_env() {
    log_benchmark "INFO" "Setting up benchmark environment"
    mkdir -p "$BENCHMARK_DIR"
    cd "$AGENT_DIR"
}

# Test 1: Execution Time Impact
benchmark_execution_time() {
    log_benchmark "INFO" "Benchmarking execution time impact"

    local task="Create files A.txt, B.txt, C.txt with sequential numbers"
    local without_critic_time with_critic_time

    # Without critic
    log_benchmark "INFO" "Running task without critic..."
    local start_time=$(date +%s.%N)
    CRITIC_ENABLED=false timeout 120s ./runner.sh "$task" >/dev/null 2>&1 || true
    local end_time=$(date +%s.%N)
    without_critic_time=$(echo "$end_time - $start_time" | bc)

    # With critic
    log_benchmark "INFO" "Running task with critic..."
    start_time=$(date +%s.%N)
    CRITIC_ENABLED=true timeout 120s ./runner.sh "$task" >/dev/null 2>&1 || true
    end_time=$(date +%s.%N)
    with_critic_time=$(echo "$end_time - $start_time" | bc)

    # Calculate overhead
    local overhead_pct
    if (( $(echo "$without_critic_time > 0" | bc -l) )); then
        overhead_pct=$(echo "scale=1; ($with_critic_time - $without_critic_time) * 100 / $without_critic_time" | bc)
    else
        overhead_pct="N/A"
    fi

    # Save results
    cat > "$BENCHMARK_DIR/execution_time_${TIMESTAMP}.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "task": "$task",
  "without_critic_seconds": $without_critic_time,
  "with_critic_seconds": $with_critic_time,
  "overhead_percentage": "$overhead_pct",
  "acceptable_threshold": 50.0
}
EOF

    log_benchmark "INFO" "Without critic: ${without_critic_time}s"
    log_benchmark "INFO" "With critic: ${with_critic_time}s"
    log_benchmark "INFO" "Overhead: ${overhead_pct}%"

    # Check if acceptable
    if [[ "$overhead_pct" != "N/A" ]] && (( $(echo "$overhead_pct < 50.0" | bc -l) )); then
        log_benchmark "PASS" "Execution time overhead is acceptable (<50%)"
    else
        log_benchmark "WARN" "Execution time overhead may be high (${overhead_pct}%)"
    fi
}

# Test 2: Individual Critic Call Performance
benchmark_critic_calls() {
    log_benchmark "INFO" "Benchmarking individual critic call performance"

    local test_input='{
        "task": "Performance benchmark",
        "candidate_step": {
            "tool": "write_file",
            "reasoning": "Create a test file",
            "parameters": [
                {"name": "path", "value": "benchmark.txt"},
                {"name": "content", "value": "Performance test content"}
            ]
        },
        "turn": 1,
        "max_turns": 10,
        "last_observation": "Starting benchmark",
        "plan_remainder": [],
        "execution_history_tail": [],
        "tool_spec": {
            "name": "write_file",
            "description": "Write content to a file"
        },
        "sandbox_path": "/tmp/sandbox",
        "temporal_constraints": {
            "files_created": [],
            "files_expected": ["benchmark.txt"],
            "deadline_turns": null
        },
        "failure_patterns": {
            "repeated_tool_failures": {},
            "stuck_iterations": false
        },
        "safety_constraints": ["no_file_ops_outside_sandbox", "max_file_size_32kb"]
    }'

    echo "$test_input" > "$BENCHMARK_DIR/perf_test_input.json"

    # Run multiple iterations
    local total_time=0
    local iterations=10
    local successful_calls=0

    for i in $(seq 1 $iterations); do
        local start_time=$(date +%s.%N)

        if cd "$REPO_ROOT" && ostruct run examples/agent/templates/critic.j2 examples/agent/schemas/critic_out.schema.json \
            --file critic_input "$BENCHMARK_DIR/perf_test_input.json" >/dev/null 2>&1; then
            successful_calls=$((successful_calls + 1))
        fi

        local end_time=$(date +%s.%N)
        local call_time=$(echo "$end_time - $start_time" | bc)
        total_time=$(echo "$total_time + $call_time" | bc)
    done

    local avg_time=$(echo "scale=3; $total_time / $iterations" | bc)
    local success_rate=$(echo "scale=1; $successful_calls * 100 / $iterations" | bc)

    # Save results
    cat > "$BENCHMARK_DIR/critic_calls_${TIMESTAMP}.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "iterations": $iterations,
  "successful_calls": $successful_calls,
  "success_rate_percentage": $success_rate,
  "total_time_seconds": $total_time,
  "average_time_seconds": $avg_time,
  "target_threshold_seconds": 5.0
}
EOF

    log_benchmark "INFO" "Critic calls: $iterations iterations"
    log_benchmark "INFO" "Successful calls: $successful_calls ($success_rate%)"
    log_benchmark "INFO" "Average time per call: ${avg_time}s"

    if (( $(echo "$avg_time < 5.0" | bc -l) )); then
        log_benchmark "PASS" "Critic call performance is acceptable (<5s per call)"
    else
        log_benchmark "WARN" "Critic call performance may be slow (${avg_time}s per call)"
    fi
}

# Test 3: Cost Estimation
estimate_cost_impact() {
    log_benchmark "INFO" "Estimating cost impact"

    # Get typical token usage from a sample call
    local result
    result=$(cd "$REPO_ROOT" && ostruct run examples/agent/templates/critic.j2 examples/agent/schemas/critic_out.schema.json \
        --file critic_input "$BENCHMARK_DIR/perf_test_input.json" --dry-run 2>/dev/null)

    # Extract token information from dry run
    local input_tokens output_tokens
    input_tokens=$(echo "$result" | jq -r '.token_usage.input_tokens // 800' 2>/dev/null || echo "800")
    output_tokens=$(echo "$result" | jq -r '.token_usage.output_tokens // 200' 2>/dev/null || echo "200")

    # Cost calculations (GPT-4 pricing as of 2024)
    local input_cost_per_1k=0.03
    local output_cost_per_1k=0.06

    local input_cost=$(echo "scale=6; $input_tokens * $input_cost_per_1k / 1000" | bc)
    local output_cost=$(echo "scale=6; $output_tokens * $output_cost_per_1k / 1000" | bc)
    local total_cost_per_call=$(echo "scale=6; $input_cost + $output_cost" | bc)

    # Estimate for typical agent run (10 steps)
    local typical_steps=10
    local total_cost_per_run=$(echo "scale=6; $total_cost_per_call * $typical_steps" | bc)

    # Compare to base agent cost (estimated)
    local base_agent_cost=0.20  # Estimated base cost per run
    local cost_increase_pct=$(echo "scale=1; $total_cost_per_run * 100 / $base_agent_cost" | bc)

    # Save results
    cat > "$BENCHMARK_DIR/cost_analysis_${TIMESTAMP}.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "input_tokens": $input_tokens,
  "output_tokens": $output_tokens,
  "input_cost_per_call": $input_cost,
  "output_cost_per_call": $output_cost,
  "total_cost_per_call": $total_cost_per_call,
  "typical_steps_per_run": $typical_steps,
  "total_cost_per_run": $total_cost_per_run,
  "base_agent_cost_estimate": $base_agent_cost,
  "cost_increase_percentage": $cost_increase_pct,
  "acceptable_threshold_percentage": 25.0
}
EOF

    log_benchmark "INFO" "Input tokens per call: $input_tokens"
    log_benchmark "INFO" "Output tokens per call: $output_tokens"
    log_benchmark "INFO" "Cost per critic call: \$${total_cost_per_call}"
    log_benchmark "INFO" "Cost per agent run (${typical_steps} steps): \$${total_cost_per_run}"
    log_benchmark "INFO" "Cost increase vs base agent: ${cost_increase_pct}%"

    if (( $(echo "$cost_increase_pct < 25.0" | bc -l) )); then
        log_benchmark "PASS" "Cost impact is acceptable (<25% increase)"
    else
        log_benchmark "WARN" "Cost impact may be significant (${cost_increase_pct}% increase)"
    fi
}

# Test 4: Memory and Resource Usage
benchmark_resource_usage() {
    log_benchmark "INFO" "Benchmarking resource usage"

    # Monitor process during critic calls
    local pid_file="$BENCHMARK_DIR/critic_pid.tmp"
    local resource_log="$BENCHMARK_DIR/resource_usage_${TIMESTAMP}.log"

    # Start resource monitoring in background
    (
        while [[ -f "$pid_file" ]]; do
            ps -o pid,ppid,%cpu,%mem,vsz,rss,comm -p $$ >> "$resource_log" 2>/dev/null || true
            sleep 1
        done
    ) &
    local monitor_pid=$!

    touch "$pid_file"

    # Run critic calls while monitoring
    for i in {1..5}; do
        cd "$REPO_ROOT" && ostruct run examples/agent/templates/critic.j2 examples/agent/schemas/critic_out.schema.json \
            --file critic_input "$BENCHMARK_DIR/perf_test_input.json" >/dev/null 2>&1 || true
    done

    rm -f "$pid_file"
    kill $monitor_pid 2>/dev/null || true

    # Analyze resource usage
    if [[ -f "$resource_log" ]]; then
        local max_cpu max_mem
        max_cpu=$(awk 'NR>1 {print $3}' "$resource_log" | sort -n | tail -1)
        max_mem=$(awk 'NR>1 {print $4}' "$resource_log" | sort -n | tail -1)

        log_benchmark "INFO" "Peak CPU usage: ${max_cpu}%"
        log_benchmark "INFO" "Peak memory usage: ${max_mem}%"

        # Save results
        cat > "$BENCHMARK_DIR/resource_usage_${TIMESTAMP}.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "peak_cpu_percentage": $max_cpu,
  "peak_memory_percentage": $max_mem,
  "resource_log_file": "$resource_log"
}
EOF

        if (( $(echo "$max_cpu < 80.0" | bc -l) )) && (( $(echo "$max_mem < 80.0" | bc -l) )); then
            log_benchmark "PASS" "Resource usage is acceptable"
        else
            log_benchmark "WARN" "High resource usage detected"
        fi
    else
        log_benchmark "WARN" "Could not collect resource usage data"
    fi
}

# Generate comprehensive report
generate_report() {
    log_benchmark "INFO" "Generating comprehensive performance report"

    local report_file="$BENCHMARK_DIR/performance_report_${TIMESTAMP}.md"

    cat > "$report_file" << 'EOF'
# Critic Performance and Cost Analysis Report

## Executive Summary

This report analyzes the performance impact and cost implications of integrating the Critic component into the ostruct agent system.

## Test Results

### 1. Execution Time Impact

EOF

    # Add execution time results if available
    if [[ -f "$BENCHMARK_DIR/execution_time_${TIMESTAMP}.json" ]]; then
        local without_time with_time overhead
        without_time=$(jq -r '.without_critic_seconds' "$BENCHMARK_DIR/execution_time_${TIMESTAMP}.json")
        with_time=$(jq -r '.with_critic_seconds' "$BENCHMARK_DIR/execution_time_${TIMESTAMP}.json")
        overhead=$(jq -r '.overhead_percentage' "$BENCHMARK_DIR/execution_time_${TIMESTAMP}.json")

        cat >> "$report_file" << EOF
- **Without Critic**: ${without_time}s
- **With Critic**: ${with_time}s
- **Overhead**: ${overhead}%
- **Status**: $(if [[ "$overhead" != "N/A" ]] && (( $(echo "$overhead < 50.0" | bc -l) )); then echo "✅ ACCEPTABLE"; else echo "⚠️ NEEDS ATTENTION"; fi)

EOF
    fi

    cat >> "$report_file" << 'EOF'
### 2. Individual Critic Call Performance

EOF

    # Add critic call results if available
    if [[ -f "$BENCHMARK_DIR/critic_calls_${TIMESTAMP}.json" ]]; then
        local avg_time success_rate
        avg_time=$(jq -r '.average_time_seconds' "$BENCHMARK_DIR/critic_calls_${TIMESTAMP}.json")
        success_rate=$(jq -r '.success_rate_percentage' "$BENCHMARK_DIR/critic_calls_${TIMESTAMP}.json")

        cat >> "$report_file" << EOF
- **Average Time per Call**: ${avg_time}s
- **Success Rate**: ${success_rate}%
- **Status**: $(if (( $(echo "$avg_time < 5.0" | bc -l) )); then echo "✅ ACCEPTABLE"; else echo "⚠️ NEEDS OPTIMIZATION"; fi)

EOF
    fi

    cat >> "$report_file" << 'EOF'
### 3. Cost Analysis

EOF

    # Add cost analysis if available
    if [[ -f "$BENCHMARK_DIR/cost_analysis_${TIMESTAMP}.json" ]]; then
        local cost_per_call cost_per_run cost_increase
        cost_per_call=$(jq -r '.total_cost_per_call' "$BENCHMARK_DIR/cost_analysis_${TIMESTAMP}.json")
        cost_per_run=$(jq -r '.total_cost_per_run' "$BENCHMARK_DIR/cost_analysis_${TIMESTAMP}.json")
        cost_increase=$(jq -r '.cost_increase_percentage' "$BENCHMARK_DIR/cost_analysis_${TIMESTAMP}.json")

        cat >> "$report_file" << EOF
- **Cost per Critic Call**: \$${cost_per_call}
- **Cost per Agent Run**: \$${cost_per_run}
- **Cost Increase**: ${cost_increase}%
- **Status**: $(if (( $(echo "$cost_increase < 25.0" | bc -l) )); then echo "✅ ACCEPTABLE"; else echo "⚠️ SIGNIFICANT IMPACT"; fi)

EOF
    fi

    cat >> "$report_file" << 'EOF'
## Recommendations

Based on the analysis:

1. **Performance**: Monitor execution time overhead and optimize if >50%
2. **Cost**: Consider cost-benefit ratio for improved success rates
3. **Scaling**: Evaluate impact at higher usage volumes
4. **Optimization**: Identify opportunities to reduce critic template complexity

## Files Generated

EOF

    # List all generated files
    for file in "$BENCHMARK_DIR"/*"${TIMESTAMP}"*; do
        if [[ -f "$file" ]]; then
            echo "- \`$(basename "$file")\`" >> "$report_file"
        fi
    done

    log_benchmark "INFO" "Report generated: $report_file"
}

# Main benchmark runner
main() {
    echo "=========================================="
    echo "    CRITIC PERFORMANCE & COST ANALYSIS"
    echo "=========================================="
    echo "Timestamp: $TIMESTAMP"
    echo "Benchmark Directory: $BENCHMARK_DIR"
    echo ""

    setup_benchmark_env

    # Run all benchmarks
    benchmark_execution_time
    echo ""
    benchmark_critic_calls
    echo ""
    estimate_cost_impact
    echo ""
    benchmark_resource_usage
    echo ""

    # Generate report
    generate_report

    echo ""
    echo "=========================================="
    echo "         BENCHMARK COMPLETE"
    echo "=========================================="
    echo "Results saved to: $BENCHMARK_DIR"
    echo "Report: $BENCHMARK_DIR/performance_report_${TIMESTAMP}.md"
}

# Run benchmarks
main "$@"
