# Step-by-Step Migration Guide

This example provides a practical, incremental approach to migrating from traditional ostruct usage to enhanced multi-tool capabilities.

## Overview

This migration guide demonstrates:

- **Gradual Adoption**: Step-by-step enhancement without breaking existing workflows
- **Risk-Free Migration**: Each step can be validated before proceeding
- **Backward Compatibility**: Traditional commands continue to work throughout
- **Measurable Benefits**: Clear metrics to validate improvements

## Migration Phases

### Phase 1: Baseline Assessment

### Phase 2: Add Explicit File Routing

### Phase 3: Introduce Configuration Management

### Phase 4: Enable Multi-Tool Integration

### Phase 5: Optimize Templates and Workflows

## Directory Structure

```
.
├── README.md                   # This file
├── phase-1-baseline/          # Current state assessment
│   ├── current-commands.sh    # Document existing usage
│   ├── baseline-metrics.py    # Measure current performance
│   └── inventory.md           # Current usage inventory
├── phase-2-routing/           # Explicit file routing
│   ├── traditional.sh         # Original commands
│   ├── enhanced.sh            # With explicit routing
│   └── comparison.py          # Before/after comparison
├── phase-3-config/            # Configuration management
│   ├── basic-config.yaml      # Initial configuration
│   ├── migration-script.sh    # Configuration setup
│   └── validate-config.py     # Configuration validation
├── phase-4-multitools/        # Multi-tool integration
│   ├── code-interpreter.sh    # Add Code Interpreter
│   ├── file-search.sh         # Add File Search
│   ├── mcp-integration.sh     # Add MCP servers
│   └── integration-test.py    # Validate integration
├── phase-5-optimize/          # Template optimization
│   ├── template-migration/    # Template updates
│   ├── workflow-optimization/ # Optimized workflows
│   └── performance-test.py    # Final validation
└── tools/
    ├── migration-checker.py   # Migration validation tool
    ├── rollback.sh            # Emergency rollback
    └── success-metrics.py     # Success measurement
```

## Phase 1: Baseline Assessment

### Step 1.1: Document Current Usage

**phase-1-baseline/current-commands.sh**:

```bash
#!/bin/bash
# Document all current ostruct usage in your project

echo "=== Current ostruct Usage Inventory ==="

# Example current commands (replace with your actual usage)
CURRENT_COMMANDS=(
    "ostruct run analysis.j2 schema.json -ft data input.csv -dc source ./src"
    "ostruct run review.j2 review_schema.json -dc code ./src -R"
    "ostruct run config-check.j2 config_schema.json -ft dev dev.yaml -ft prod prod.yaml"
)

echo "Current commands in use:"
for cmd in "${CURRENT_COMMANDS[@]}"; do
    echo "  $cmd"
done

echo
echo "Files typically processed:"
find . -name "*.py" -o -name "*.js" -o -name "*.yaml" -o -name "*.json" | head -20
```

### Step 1.2: Measure Baseline Performance

**phase-1-baseline/baseline-metrics.py**:

```python
#!/usr/bin/env python3
"""Measure baseline performance of current ostruct usage."""

import subprocess
import time
import json
import sys
from pathlib import Path

def measure_command(cmd, description):
    """Measure performance of a command."""
    print(f"Measuring: {description}")
    print(f"Command: {cmd}")

    start_time = time.time()

    try:
        # Add --dry-run to avoid API costs during measurement
        dry_run_cmd = f"{cmd} --dry-run" if "--dry-run" not in cmd else cmd

        result = subprocess.run(
            dry_run_cmd, shell=True, capture_output=True, text=True, check=True
        )

        end_time = time.time()
        duration = end_time - start_time

        # Try to extract token estimates from output
        tokens = 0
        cost = 0.0

        # Look for token information in output
        if "tokens" in result.stderr.lower():
            # Parse token information if available
            pass

        return {
            "command": cmd,
            "description": description,
            "duration": duration,
            "success": True,
            "estimated_tokens": tokens,
            "estimated_cost": cost,
            "output_length": len(result.stdout)
        }

    except subprocess.CalledProcessError as e:
        end_time = time.time()
        return {
            "command": cmd,
            "description": description,
            "duration": end_time - start_time,
            "success": False,
            "error": e.stderr
        }

def main():
    """Run baseline measurements."""

    # Define your current commands here
    commands = [
        {
            "cmd": "ostruct run templates/analysis.j2 schemas/result.json -ft data examples/data.csv -dc source examples/src",
            "description": "Data analysis workflow"
        },
        {
            "cmd": "ostruct run templates/review.j2 schemas/review.json -dc code examples/src -R",
            "description": "Code review workflow"
        },
        {
            "cmd": "ostruct run templates/config.j2 schemas/config.json -ft dev examples/dev.yaml -ft prod examples/prod.yaml",
            "description": "Configuration validation"
        }
    ]

    results = []

    print("🔍 Running baseline performance measurements...")
    print("=" * 60)

    for command_info in commands:
        result = measure_command(command_info["cmd"], command_info["description"])
        results.append(result)

        if result["success"]:
            print(f"✅ Duration: {result['duration']:.2f}s")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        print()

    # Save baseline results
    baseline_data = {
        "timestamp": time.time(),
        "total_commands": len(commands),
        "successful_commands": sum(1 for r in results if r["success"]),
        "average_duration": sum(r["duration"] for r in results) / len(results),
        "commands": results
    }

    with open("baseline_results.json", "w") as f:
        json.dump(baseline_data, f, indent=2)

    print("=" * 60)
    print("📊 BASELINE SUMMARY")
    print("=" * 60)
    print(f"Total Commands: {baseline_data['total_commands']}")
    print(f"Successful: {baseline_data['successful_commands']}")
    print(f"Average Duration: {baseline_data['average_duration']:.2f}s")
    print(f"Results saved to: baseline_results.json")

if __name__ == "__main__":
    main()
```

### Step 1.3: Create Migration Inventory

**phase-1-baseline/inventory.md**:

```markdown
# Migration Inventory

## Current Usage Assessment

### Commands in Use
1. **Data Analysis**: `ostruct run analysis.j2 schema.json -ft data input.csv -dc source ./src`
   - Files: CSV data, source code
   - Purpose: Analyze data with code context
   - **Migration Opportunity**: Route CSV to Code Interpreter, source to File Search

2. **Code Review**: `ostruct run review.j2 review_schema.json -dc code ./src -R`
   - Files: Source code directory
   - Purpose: Comprehensive code review
   - **Migration Opportunity**: Use Code Interpreter for execution, File Search for docs

3. **Config Validation**: `ostruct run config-check.j2 config_schema.json -ft dev dev.yaml -ft prod prod.yaml`
   - Files: Configuration files
   - Purpose: Multi-environment validation
   - **Migration Opportunity**: Keep configs in template, add docs to File Search

### Files by Type
- **Data Files**: `*.csv`, `*.json` (analysis data) → Code Interpreter
- **Source Code**: `*.py`, `*.js`, `*.ts` → Code Interpreter
- **Documentation**: `*.md`, `docs/` → File Search
- **Configuration**: `*.yaml`, `*.json` (config) → Template
- **Tests**: `test_*.py`, `*_test.js` → Code Interpreter

### Current Pain Points
- [ ] High token usage with large files
- [ ] All files processed identically
- [ ] No cost controls in place
- [ ] Limited analysis capabilities
- [ ] No configuration management

### Migration Goals
- [ ] Reduce token usage by 50%+
- [ ] Enable code execution for data analysis
- [ ] Add documentation search capabilities
- [ ] Implement cost controls
- [ ] Maintain all existing functionality
```

## Phase 2: Add Explicit File Routing

### Step 2.1: Convert to Explicit Routing

**phase-2-routing/traditional.sh**:

```bash
#!/bin/bash
# Original commands (still work)

echo "🔄 Running traditional commands..."

# Traditional data analysis
ostruct run templates/analysis.j2 schemas/result.json \
  -ft data examples/data.csv \
  -dc source examples/src \
  --output-file traditional_analysis.json

# Traditional code review
ostruct run templates/review.j2 schemas/review.json \
  -dc code examples/src \
  -R README.md \
  --output-file traditional_review.json

# Traditional config validation
ostruct run templates/config.j2 schemas/config.json \
  -ft dev examples/dev.yaml \
  -ft prod examples/prod.yaml \
  --output-file traditional_config.json

echo "✅ Traditional commands completed"
```

**phase-2-routing/enhanced.sh**:

```bash
#!/bin/bash
# Enhanced commands with explicit routing

echo "🚀 Running enhanced commands with explicit routing..."

# Enhanced data analysis - route appropriately
ostruct run templates/analysis.j2 schemas/result.json \
  -fc data examples/data.csv \
  -ds source examples/src \
  --output-file enhanced_analysis.json

# Enhanced code review - use Code Interpreter + File Search
ostruct run templates/review.j2 schemas/review.json \
  -dc code examples/src \
  -ds docs docs/ \
  -R README.md \
  --output-file enhanced_review.json

# Enhanced config validation - template + documentation search
ostruct run templates/config.j2 schemas/config.json \
  -ft dev examples/dev.yaml \
  -ft prod examples/prod.yaml \
  -ds infrastructure_docs infrastructure_docs/ \
  --output-file enhanced_config.json

echo "✅ Enhanced commands completed"
```

### Step 2.2: Compare Results

**phase-2-routing/comparison.py**:

```python
#!/usr/bin/env python3
"""Compare traditional vs enhanced routing performance."""

import json
import sys
from pathlib import Path

def compare_results(traditional_file, enhanced_file):
    """Compare traditional and enhanced results."""

    def load_json(filename):
        if not Path(filename).exists():
            print(f"❌ File not found: {filename}")
            return None

        try:
            with open(filename) as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON in {filename}")
            return None

    traditional = load_json(traditional_file)
    enhanced = load_json(enhanced_file)

    if not traditional or not enhanced:
        return 1

    # Extract metrics
    trad_cost = traditional.get("estimated_cost", 0)
    enh_cost = enhanced.get("estimated_cost", 0)

    trad_tokens = traditional.get("total_tokens", 0)
    enh_tokens = enhanced.get("total_tokens", 0)

    # Calculate improvements
    cost_savings = trad_cost - enh_cost
    cost_savings_pct = (cost_savings / trad_cost * 100) if trad_cost > 0 else 0

    token_savings = trad_tokens - enh_tokens
    token_savings_pct = (token_savings / trad_tokens * 100) if trad_tokens > 0 else 0

    print("📊 ROUTING COMPARISON RESULTS")
    print("=" * 50)
    print(f"Traditional Cost:  ${trad_cost:.4f}")
    print(f"Enhanced Cost:     ${enh_cost:.4f}")
    print(f"Cost Savings:      ${cost_savings:.4f} ({cost_savings_pct:.1f}%)")
    print()
    print(f"Traditional Tokens: {trad_tokens:,}")
    print(f"Enhanced Tokens:    {enh_tokens:,}")
    print(f"Token Savings:      {token_savings:,} ({token_savings_pct:.1f}%)")
    print()

    # Provide recommendations
    if cost_savings_pct > 30:
        print("🎉 Excellent savings! Migration highly recommended.")
    elif cost_savings_pct > 15:
        print("✅ Good savings achieved. Continue migration.")
    elif cost_savings_pct > 0:
        print("👍 Some savings. Consider template optimization.")
    else:
        print("⚠️  No savings detected. Review routing strategy.")

    return 0

def main():
    """Compare all result files."""

    comparisons = [
        ("traditional_analysis.json", "enhanced_analysis.json", "Data Analysis"),
        ("traditional_review.json", "enhanced_review.json", "Code Review"),
        ("traditional_config.json", "enhanced_config.json", "Config Validation")
    ]

    total_savings = 0
    successful_comparisons = 0

    for trad_file, enh_file, description in comparisons:
        print(f"\n🔍 Comparing: {description}")
        print("-" * 40)

        if compare_results(trad_file, enh_file) == 0:
            successful_comparisons += 1

    print(f"\n📈 PHASE 2 SUMMARY")
    print("=" * 50)
    print(f"Successful Comparisons: {successful_comparisons}/{len(comparisons)}")

    if successful_comparisons == len(comparisons):
        print("✅ Phase 2 migration successful! Ready for Phase 3.")
    else:
        print("⚠️  Some comparisons failed. Review before proceeding.")

if __name__ == "__main__":
    main()
```

## Phase 3: Configuration Management

### Step 3.1: Create Basic Configuration

**phase-3-config/basic-config.yaml**:

```yaml
# Basic ostruct configuration for migration
models:
  default: gpt-4o

tools:
  code_interpreter:
    auto_download: true
    output_directory: "./migration_output"
  file_search:
    max_results: 15

operation:
  timeout_minutes: 20
  retry_attempts: 2
  require_approval: never

limits:
  max_cost_per_run: 5.00
  warn_expensive_operations: true
```

### Step 3.2: Migration Script

**phase-3-config/migration-script.sh**:

```bash
#!/bin/bash
# Setup configuration management

echo "⚙️  Setting up configuration management..."

# Backup existing configuration if any
if [ -f "ostruct.yaml" ]; then
    echo "📋 Backing up existing configuration..."
    cp ostruct.yaml ostruct.yaml.backup
fi

# Copy basic configuration
cp phase-3-config/basic-config.yaml ostruct.yaml

echo "✅ Configuration file created: ostruct.yaml"
echo

# Test configuration
echo "🧪 Testing configuration..."
if python phase-3-config/validate-config.py; then
    echo "✅ Configuration validation passed"
else
    echo "❌ Configuration validation failed"
    exit 1
fi

# Run test commands with configuration
echo "🚀 Testing commands with configuration..."

ostruct --config ostruct.yaml run templates/analysis.j2 schemas/result.json \
  -fc examples/data.csv \
  -fs examples/src \
  --dry-run

echo "✅ Configuration setup complete"
```

## Phase 4: Multi-Tool Integration

### Step 4.1: Add Code Interpreter

**phase-4-multitools/code-interpreter.sh**:

```bash
#!/bin/bash
# Integrate Code Interpreter capabilities

echo "💻 Adding Code Interpreter integration..."

# Data analysis with code execution
ostruct --config ostruct.yaml run templates/analysis.j2 schemas/result.json \
  -fc data examples/data.csv \
  -fc analysis_script examples/analysis_script.py \
  --output-file code_interpreter_result.json

echo "✅ Code Interpreter integration tested"
```

### Step 4.2: Add File Search

**phase-4-multitools/file-search.sh**:

```bash
#!/bin/bash
# Integrate File Search capabilities

echo "🔍 Adding File Search integration..."

# Code review with documentation context
ostruct --config ostruct.yaml run templates/review.j2 schemas/review.json \
  -dc src examples/src \
  -ds docs docs/ \
  -ft readme README.md \
  --output-file file_search_result.json

echo "✅ File Search integration tested"
```

### Step 4.3: Add MCP Integration

**phase-4-multitools/mcp-integration.sh**:

```bash
#!/bin/bash
# Integrate MCP server capabilities

echo "🌐 Adding MCP integration..."

# Analysis with external repository context
ostruct --config ostruct.yaml run templates/analysis.j2 schemas/result.json \
  -dc src examples/src \
  -ds docs docs/ \
  --mcp-server deepwiki@https://mcp.deepwiki.com/sse \
  -V repo_owner=your-org \
  -V repo_name=your-project \
  --output-file mcp_result.json

echo "✅ MCP integration tested"
```

## Phase 5: Template Optimization

### Step 5.1: Update Templates for Multi-Tool Usage

**phase-5-optimize/template-migration/optimized-analysis.j2**:

```jinja
---
system_prompt: You are an expert data analyst with access to code execution and document search.
---
# Multi-Tool Data Analysis

{% if code_interpreter_files %}
## Available Data and Code
Execute the following for analysis:
{% for file in code_interpreter_files %}
- {{ file.name }}: {{ file.description }}
{% endfor %}
{% endif %}

{% if file_search_results %}
## Documentation Context
{% for result in file_search_results %}
- {{ result.title }}: {{ result.summary }}
{% endfor %}
{% endif %}

Provide comprehensive analysis including:
1. Data insights from code execution
2. Best practices from documentation
3. Actionable recommendations
```

## Migration Validation Tools

### Migration Checker

**tools/migration-checker.py**:

```python
#!/usr/bin/env python3
"""Validate migration progress and success."""

import json
import subprocess
import sys
from pathlib import Path

def check_migration_status():
    """Check overall migration status."""

    print("🔍 Checking migration status...")

    # Check 1: Configuration exists
    config_exists = Path("ostruct.yaml").exists()
    print(f"✅ Configuration file: {'Found' if config_exists else '❌ Missing'}")

    # Check 2: Baseline results available
    baseline_exists = Path("baseline_results.json").exists()
    print(f"✅ Baseline results: {'Found' if baseline_exists else '❌ Missing'}")

    # Check 3: Test enhanced commands
    try:
        result = subprocess.run(
            "ostruct --config ostruct.yaml run templates/analysis.j2 schemas/result.json -fc examples/data.csv --dry-run",
            shell=True, capture_output=True, text=True, check=True
        )
        print("✅ Enhanced commands working")
    except subprocess.CalledProcessError:
        print("❌ Enhanced commands failing")
        return False

    # Check 4: Compare performance if results available
    if Path("traditional_analysis.json").exists() and Path("enhanced_analysis.json").exists():
        # Load and compare results
        try:
            with open("traditional_analysis.json") as f:
                trad = json.load(f)
            with open("enhanced_analysis.json") as f:
                enh = json.load(f)

            trad_cost = trad.get("estimated_cost", 0)
            enh_cost = enh.get("estimated_cost", 0)

            if enh_cost < trad_cost:
                savings = (trad_cost - enh_cost) / trad_cost * 100
                print(f"✅ Cost savings: {savings:.1f}%")
            else:
                print("⚠️  No cost savings detected")

        except (json.JSONDecodeError, FileNotFoundError):
            print("⚠️  Could not compare performance")

    return True

if __name__ == "__main__":
    success = check_migration_status()

    if success:
        print("\n🎉 Migration validation successful!")
        print("\n📝 Next steps:")
        print("1. Run your production workflows with enhanced syntax")
        print("2. Monitor costs and performance")
        print("3. Update team documentation")
        print("4. Consider template optimization")
    else:
        print("\n❌ Migration validation failed")
        print("Please review the issues above before proceeding")
        sys.exit(1)
```

## Success Metrics

After completing the migration, you should see:

- **50-70% reduction in token usage** through explicit routing
- **Improved analysis quality** through multi-tool integration
- **Better cost control** through configuration management
- **Enhanced capabilities** without breaking existing workflows
- **Team productivity gains** through better tooling

## Emergency Rollback

**tools/rollback.sh**:

```bash
#!/bin/bash
# Emergency rollback to traditional usage

echo "🔄 Rolling back to traditional usage..."

# Restore original configuration if exists
if [ -f "ostruct.yaml.backup" ]; then
    mv ostruct.yaml.backup ostruct.yaml
    echo "✅ Configuration restored"
fi

# Provide traditional command equivalents
echo "📝 Use these traditional commands:"
echo "  ostruct run template.j2 schema.json -ft file data.csv -dc source ./src"
echo "  ostruct run template.j2 schema.json -dc code ./src -R"

echo "✅ Rollback complete"
```

This step-by-step migration guide provides a safe, incremental path to adopt ostruct's enhanced capabilities while maintaining full backward compatibility and validating improvements at each stage.
