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

   ```bash
   # Use the --var flag to pass custom patterns
   ./run.sh --var custom_patterns='["^service_", "^env_"]' path/to/configs
   ```

### Rule Severity Levels

- **error**: Configuration will not work
- **warning**: Potential issues or anti-patterns
- **info**: Suggestions for improvement
- **security**: Security-related concerns

## Environment-Specific Validation

### Development Environment

```bash
./run.sh --env development \
  --var allow_local_urls=true \
  --var skip_ssl_verify=true \
  path/to/configs
```

### Production Environment

```bash
./run.sh --env production \
  --var require_ssl=true \
  --var require_secrets=true \
  path/to/configs
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

Use the `--output` flag with templates:

```bash
./run.sh --output custom_format.json \
  --var format=detailed \
  path/to/configs
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

### Custom Hooks

Add pre/post validation hooks:

```bash
./run.sh \
  --pre-validate="./scripts/pre_validate.sh" \
  --post-validate="./scripts/post_validate.sh" \
  path/to/configs
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
