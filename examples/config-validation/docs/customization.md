# Customizing Configuration Validation

This guide explains how to customize the configuration validation process for your specific needs.

## Custom Validation Rules

### Adding New Rules

1. **Extend the System Prompt**

   ```yaml
   # Add to prompts/system.txt
   Additional validation rules:
   - Check for specific naming conventions
   - Validate custom environment variables
   - Enforce team-specific standards
   ```

2. **Define Custom Patterns**

   Generic pattern:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     --dir configs /path/to/configs \
     --recursive \
     --sys-file prompts/system.txt \
     -J custom_patterns='["^service_", "^env_"]'
   ```

   Ready to run example:

   ```bash
   ostruct run prompts/task.j2 schemas/validation_result.json \
     --dir configs examples/basic \
     --recursive \
     --sys-file prompts/system.txt \
     -J custom_patterns='["^service_", "^env_"]'
   ```

### Rule Severity Levels

- **error**: Configuration will not work
- **warning**: Potential issues or anti-patterns
- **info**: Suggestions for improvement
- **security**: Security-related concerns

## Environment-Specific Validation

### Development Environment

Generic pattern:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs /path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=development \
  -V allow_local_urls=true \
  -V skip_ssl_verify=true
```

Ready to run example:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs examples/basic \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=development \
  -V allow_local_urls=true \
  -V skip_ssl_verify=true
```

### Production Environment

Generic pattern:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs /path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=production \
  -V require_ssl=true \
  -V require_secrets=true
```

Ready to run example:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs examples/intermediate \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=production \
  -V require_ssl=true \
  -V require_secrets=true
```

## Custom Output Formats

### JSON Output Schema

Extend `schemas/validation_result.json` to include custom fields:

```json
{
  "properties": {
    "custom_metrics": {
      "type": "object",
      "properties": {
        "your_metric": {
          "type": "number"
        }
      }
    }
  }
}
```

### Output Formatting

Generic pattern:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs /path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  --output-file custom_format.json \
  -V format=detailed
```

Ready to run example:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs examples/basic \
  --recursive \
  --sys-file prompts/system.txt \
  --output-file basic_validation.json \
  -V format=detailed
```

## Integration Points

### CI/CD Integration

1. **GitHub Actions**

   ```yaml
   - name: Validate Configs
     run: |
       ./run.sh \
         --strict \
         --env ${{ github.ref_name }} \
         --output validation.json \
         ./configs
   ```

2. **GitLab CI**

   ```yaml
   validate_configs:
     script:
       - ./run.sh --strict --env $CI_COMMIT_REF_NAME configs/
     artifacts:
       paths:
         - validation.json
   ```

### Cross-Service Validation

Generic pattern:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs /path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V cross_service=true \
  -J service_map='{"service1": "path1", "service2": "path2"}'
```

Ready to run example:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs examples/advanced/services \
  --recursive \
  --sys-file prompts/system.txt \
  -V cross_service=true \
  -J service_map='{"app": "app.yaml", "db": "db.yaml", "cache": "cache.yaml"}'
```

### Custom Hooks

Add pre/post validation hooks:

```bash
./run.sh \
  --pre-validate="./scripts/pre_validate.sh" \
  --post-validate="./scripts/post_validate.sh" \
  path/to/configs
```

### Template Support

Generic pattern:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs /path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V enable_templates=true \
  -J template_vars='{"env": "prod", "region": "us-west"}'
```

Ready to run example:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs examples/advanced/services \
  --recursive \
  --sys-file prompts/system.txt \
  -V enable_templates=true \
  -J template_vars='{"env": "prod", "region": "us-west"}'
```

## Advanced Features

### Cross-Service Validation

Enable validation across multiple services:

```bash
./run.sh \
  --cross-service \
  --service-map=service_map.yaml \
  path/to/configs
```

### Custom Validators

Add custom validation logic:

```python
# validators/custom.py
def validate_custom_rule(config, context):
    # Custom validation logic
    return {
        "valid": bool,
        "findings": []
    }
```

### Template Support

Use templates in configurations:

```yaml
# Enable template processing
./run.sh \
  --enable-templates \
  --template-vars=vars.yaml \
  path/to/configs
```

## Best Practices

1. **Organizing Rules**
   - Group related rules together
   - Use clear, descriptive names
   - Document rule rationale

2. **Performance Optimization**
   - Use `--ignore-patterns` for irrelevant files
   - Enable caching for large codebases
   - Use selective validation with `--paths`

3. **Security Considerations**
   - Always validate secrets handling
   - Check for secure defaults
   - Verify environment isolation

4. **Maintenance**
   - Keep rules updated
   - Document customizations
   - Version control configurations

### Custom Patterns

To use custom validation patterns:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V custom_patterns='["^service_", "^env_"]'
```

### Environment-Specific Rules

Development environment:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=development
```

Production environment:

```bash
ostruct run prompts/task.j2 schemas/validation_result.json \
  --dir configs path/to/configs \
  --recursive \
  --sys-file prompts/system.txt \
  -V environment=production
```
