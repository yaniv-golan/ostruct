# Customizing the Code Review

This guide explains how to customize the code review for your specific needs.

## Prompts

The code review uses two prompts in the `prompts/` directory:

1. `system.txt`: Configures the AI's role and expertise
   - Modify this to focus on specific aspects (security, performance, etc.)
   - Add domain-specific knowledge or best practices
   - Change the review style or tone

2. `task.j2`: Template for the review request
   - Customize how code is presented to the AI
   - Add additional context or constraints
   - Modify the review structure

## Schema

The `schemas/code_review.json` file defines the structure of the review output:

- Add new fields for additional information
- Modify severity levels or categories
- Add custom validation rules
- Change required vs optional fields

## Examples

The `examples/` directory contains sample code demonstrating different issues:

- Add your own examples
- Organize by category (security, performance, style)
- Use real-world code patterns from your projects

## Common Customizations

1. **Focus on Security**:
   - Add security-specific fields to schema
   - Enhance system prompt with security expertise
   - Include security-focused example code

2. **Style Guide Enforcement**:
   - Add style guide rules to system prompt
   - Include style-specific fields in schema
   - Add examples of style violations

3. **Performance Analysis**:
   - Add performance metrics to schema
   - Enhance system prompt with performance patterns
   - Include examples of performance issues
