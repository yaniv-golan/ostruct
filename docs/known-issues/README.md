# Known Issues & Workarounds

This directory contains documentation for known issues in ostruct and their workarounds.

## Active Issues

### OpenAI API Issues

- **[2025-01-openai-json-duplication.md](2025-01-openai-json-duplication.md)** - OpenAI structured output JSON duplication bug
  - **Status**: ✅ Resolved with robust parsing workaround
  - **Affects**: All models using structured output (JSON schemas)
  - **Workaround**: Automatic recovery with `json_parsing_strategy: "robust"` (default)
  - **Version**: v1.2.0+

- **[2025-06-responses-ci-file-output.md](2025-06-responses-ci-file-output.md)** - OpenAI Code Interpreter file download bug with structured output
  - **Status**: ✅ Resolved with two-pass sentinel workaround
  - **Affects**: Code Interpreter + structured output (JSON schemas)
  - **Workaround**: Configure `download_strategy: "two_pass_sentinel"` or use `--enable-feature ci-download-hack`
  - **Version**: v0.8.3+

## Resolved Issues

*No fully resolved issues yet - the above issue has a working workaround but awaits upstream fix from OpenAI.*

## Issue Reporting

If you encounter a new issue:

1. Check existing issues in this directory
2. Search [GitHub Issues](https://github.com/yaniv-aknin/ostruct/issues)
3. Create a new issue with:
   - Clear reproduction steps
   - Expected vs actual behavior
   - Environment details (OS, Python version, ostruct version)
   - Relevant configuration and command-line usage

## Contributing Workarounds

When documenting workarounds:

1. Create a new `.md` file with format: `YYYY-MM-component-brief-description.md`
2. Include technical root cause analysis
3. Provide complete implementation details
4. Document performance implications
5. Include removal/deprecation plan for when upstream fixes are available
6. Add comprehensive testing results

---

**Last Updated**: January 2025
