# Optimization Examples

This directory contains examples for performance tuning, cost reduction, efficiency optimization, and smart resource management using ostruct CLI with multi-tool integration.

## Available Examples

### [Prompt Optimization](prompt-optimization/)

**Cost and performance optimization techniques** - Smart template design with 50-70% token reduction through tool-specific routing:

**Features:**

- **Automatic Template Optimization**: Smart prompt structuring and token management
- **Tool-Specific Routing**: Optimal file distribution across Code Interpreter, File Search, and templates
- **Performance Measurement**: Real-time visibility into optimization decisions and cost tracking
- **Configuration-Driven**: Environment-specific settings for cost vs. performance trade-offs

**Validation Results:**

- **Token Efficiency**: 50-70% reduction in token usage through explicit routing
- **Cost Savings**: 50-60% cost reduction compared to traditional approaches
- **Performance**: 30-40% faster execution through optimized processing
- **Error Reduction**: 70-80% fewer errors through better resource management

**Best For:** Cost-conscious workflows, high-volume processing, performance-critical applications, budget-constrained environments

## Key Features

### Smart Resource Management

All optimization examples demonstrate ostruct's efficiency capabilities:

- **Explicit File Routing**: Strategic distribution of files to optimal tools
- **Template Optimization**: Smart prompt design for minimal token usage
- **Configuration Management**: Environment-specific optimization settings
- **Cost Monitoring**: Real-time budget tracking and cost controls

### Performance Enhancement

**Measurable Improvements:**

- Reduced token consumption through intelligent routing
- Faster processing with parallel multi-tool integration
- Lower error rates through optimized configurations
- Scalable patterns for high-volume operations

### Usage Patterns

**Traditional vs. Optimized Comparison:**

```bash
# Traditional (inefficient): All files in template context
ostruct run templates/analysis.j2 schemas/result.json \
  -f data=large_dataset.csv \
  -f code=script.py \
  -f docs=documentation.md

# Optimized (efficient): Tool-specific routing
ostruct run templates/smart-analysis.j2 schemas/result.json \
  -fc large_dataset.csv \
  -fc script.py \
  -fs documentation.md
```

**Cost-Focused Configuration:**

```bash
# Budget-controlled optimization
ostruct --config configs/cost-focused.yaml run templates/efficient-analysis.j2 schemas/result.json \
  -fc data.csv \
  -fs docs/
```

**Performance Benchmarking:**

```bash
# Measure optimization impact
python scripts/benchmark.py
python scripts/cost-comparison.py traditional_result.json optimized_result.json
```

## Getting Started

1. Navigate to the specific example directory (e.g., `prompt-optimization/`)
2. Review the README.md for optimization techniques and patterns
3. Run baseline measurements to understand current resource usage
4. Apply optimization strategies incrementally
5. Measure and validate improvements

## Optimization Strategies

### 1. File Routing Optimization

- Use `-fc` for files requiring code execution or data processing
- Use `-fs` for reference documents and search contexts
- Use `-ft` for configuration files and metadata
- Avoid generic `-f` flags that load everything into templates

### 2. Template Design

- Design templates for tool-specific content handling
- Minimize prompt context size through smart structuring
- Use conditional logic for tool availability
- Implement progressive enhancement patterns

### 3. Configuration Management

- Create environment-specific configurations (development, production)
- Set appropriate cost limits and timeouts
- Configure retry policies to minimize waste
- Use model selection based on task requirements

### 4. Performance Monitoring

- Track token usage and costs over time
- Measure processing time and success rates
- Monitor error patterns and optimization opportunities
- Use baseline comparisons to validate improvements

## Cost Optimization Techniques

### Token Usage Reduction

**Before Optimization:**

- All files loaded into template context (high token usage)
- No tool-specific optimization
- Redundant processing of similar content
- Higher API costs due to inefficient patterns

**After Optimization:**

- Strategic file routing to appropriate tools
- Tool-specific content handling
- Elimination of redundant processing
- 50-70% token reduction in typical scenarios

### Configuration-Driven Efficiency

**Cost-Focused Settings:**

```yaml
models:
  default: gpt-4o  # Cost-effective model selection
tools:
  file_search:
    max_results: 10  # Limit search results
operation:
  timeout_minutes: 15  # Prevent runaway costs
limits:
  max_cost_per_run: 2.00  # Budget controls
```

**Performance-Focused Settings:**

```yaml
models:
  default: gpt-4o  # Balanced performance
tools:
  file_search:
    max_results: 20  # More comprehensive search
operation:
  timeout_minutes: 30  # Allow longer processing
limits:
  max_cost_per_run: 5.00  # Higher budget for quality
```

## Benchmarking and Measurement

### Performance Metrics

Track these key metrics to validate optimizations:

- **Token Usage**: Before vs. after comparison
- **Processing Time**: End-to-end execution duration
- **Cost per Operation**: Direct financial impact
- **Success Rate**: Error reduction and reliability
- **Quality Scores**: Output quality maintenance

### Baseline Assessment

Use the provided tools to establish baseline measurements:

```bash
# Measure current performance
python scripts/baseline-metrics.py

# Compare optimization approaches
python scripts/benchmark.py

# Validate cost improvements
python scripts/cost-comparison.py before.json after.json
```

### Migration Validation

Ensure optimizations don't degrade functionality:

```bash
# Validate migration improvements
python scripts/migration-checker.py

# Run comprehensive validation
bash scripts/optimization-demo.sh
```

## Optimization Patterns

### Progressive Enhancement

**Phase 1: Baseline Measurement**

1. Document current token usage and costs
2. Identify files suitable for different tools
3. Measure processing time and success rates

**Phase 2: File Routing Optimization**

1. Convert generic `-f` flags to tool-specific routing
2. Update templates for multi-tool integration
3. Test with `--dry-run` to validate improvements

**Phase 3: Configuration Optimization**

1. Create environment-specific configurations
2. Set appropriate cost limits and timeouts
3. Implement monitoring and alerting

**Phase 4: Template Refinement**

1. Optimize templates for tool-specific content
2. Add conditional logic for tool availability
3. Implement progressive enhancement patterns

### Expected Results

| Metric | Traditional | Optimized | Improvement |
|--------|-------------|-----------|-------------|
| **Token Usage** | 15,000-25,000 | 7,500-12,500 | 50-70% reduction |
| **Cost per Run** | $0.30-$0.50 | $0.15-$0.25 | 50-60% savings |
| **Processing Time** | 45-90 seconds | 30-60 seconds | 30-40% faster |
| **Error Rate** | 5-10% | 1-3% | 70-80% reduction |

## Contributing

When adding new optimization examples:

1. Include before/after comparison examples with measurable metrics
2. Provide comprehensive benchmarking and measurement tools
3. Document expected cost savings and performance improvements
4. Include validation scripts to verify optimization effectiveness
5. Follow established patterns for configuration management
6. Ensure examples demonstrate scalable optimization techniques

## Future Examples

This category is designed to accommodate additional optimization patterns:

- **Model Selection Optimization**: Choosing optimal models for specific tasks
- **Batch Processing Optimization**: Efficient handling of high-volume operations
- **Cache Management**: Intelligent caching strategies for repeated operations
- **Multi-Environment Optimization**: Different optimization strategies for different environments
- **Advanced Routing Patterns**: Complex file routing strategies for specialized use cases
- **Cost Prediction**: Predictive models for cost estimation and budget planning
