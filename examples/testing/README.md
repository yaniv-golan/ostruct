# Testing Examples

This directory contains examples for automated test generation, test analysis, and testing workflow automation using ostruct CLI.

## 🧪 Testing Automation Features

### Test Generation

- **Unit test generation** from source code
- **Integration test creation** for APIs and services
- **Test data generation** with realistic scenarios
- **Coverage analysis** and gap identification

### Test Analysis

- **Failure analysis** with root cause identification
- **Test result interpretation** and recommendations
- **Performance test analysis** and optimization
- **Test quality assessment** and improvement suggestions

## Available Examples

### [Test Generation](test-generation/)

**Comprehensive automated test generation system**

**Features:**

- Unit test generation from source code
- Integration test patterns for APIs
- Test data creation with edge cases
- Multiple testing framework support
- Coverage gap analysis

**Best For:** TDD workflows, legacy code testing, test automation

## Key Features

### Multi-Tool Integration

**Code Interpreter Integration:**

- Execute existing tests to understand patterns
- Generate test data with realistic scenarios
- Analyze code coverage and identify gaps
- Create performance benchmarks

**File Search Integration:**

- Search existing test patterns and documentation
- Find testing best practices and examples
- Locate relevant test configurations
- Access testing framework documentation

### Output Quality

**Professional Test Generation:**

- Syntactically correct test code
- Meaningful test scenarios and edge cases
- Proper assertions and validation
- Framework-specific best practices
- Comprehensive test documentation

## Usage Patterns

### Test Generation Workflow

```bash
# Generate unit tests for code
ostruct run prompts/test_generation.j2 schemas/test_result.json \
  -fc source_code src/calculator.py \
  -fs test_examples tests/ \
  --sys-file prompts/system.txt
```

### Test Analysis Workflow

```bash
# Analyze test failures
ostruct run prompts/failure_analysis.j2 schemas/analysis_result.json \
  -fc test_results test_output.xml \
  -fc source_code src/ \
  -fs documentation docs/ \
  --sys-file prompts/system.txt
```

### Comprehensive Testing

```bash
# Full testing workflow
ostruct run prompts/comprehensive_test.j2 schemas/test_suite.json \
  -fc source_code src/ \
  -fc existing_tests tests/ \
  -fs documentation docs/ \
  -ft config pytest.ini \
  --sys-file prompts/system.txt
```

## Testing Framework Support

### Supported Frameworks

- **Python**: pytest, unittest, nose2
- **JavaScript**: Jest, Mocha, Jasmine
- **Java**: JUnit, TestNG
- **C#**: NUnit, MSTest, xUnit
- **Go**: testing package, Ginkgo
- **Ruby**: RSpec, Minitest

### Output Formats

- Framework-specific test files
- Test configuration files
- Test data fixtures
- Documentation and reports

## Getting Started

1. Navigate to any testing example directory
2. Review the specific README.md for usage instructions
3. Start with simple unit test generation
4. Progress to integration and comprehensive testing
5. Customize templates for your testing framework

## Integration Examples

### CI/CD Integration

- Automated test generation in pipelines
- Test quality gates and validation
- Coverage reporting and analysis
- Test result interpretation

### Development Workflow

- TDD workflow automation
- Legacy code test generation
- Test maintenance and updates
- Quality assurance automation

## Contributing

When adding new testing examples:

1. Support multiple testing frameworks
2. Include realistic test scenarios
3. Provide framework-specific examples
4. Document expected test quality
5. Include CI/CD integration patterns
6. Follow testing best practices
