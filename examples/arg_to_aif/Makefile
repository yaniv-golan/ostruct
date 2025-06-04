# Makefile for arg_to_aif example

# Default text to use if TEXT is not specified
DEFAULT_TEXT := paradox_of_the_court.txt

# Use TEXT parameter if provided, otherwise use default
TEXT_FILE := $(if $(TEXT),$(TEXT),$(DEFAULT_TEXT))

# Default target
.PHONY: run
run:
	ostruct run prompt.j2 schema.json --fta argument_text texts/$(TEXT_FILE) | jq .

# Generate AIF file directly to output
.PHONY: generate
generate:
	@echo "Generating AIF file for $(TEXT_FILE)..."
	ostruct run prompt.j2 schema.json --fta argument_text texts/$(TEXT_FILE) --output-file $(basename $(TEXT_FILE)).aif.json
	@echo "Generated: $(basename $(TEXT_FILE)).aif.json"

# Generate all available texts as AIF files
.PHONY: generate-all
generate-all:
	@for text in texts/*.txt; do \
		base=$$(basename "$$text" .txt); \
		echo "Generating AIF file for $$text..."; \
		ostruct run prompt.j2 schema.json --fta argument_text "$$text" --output-file "$$base.aif.json"; \
		echo "Generated: $$base.aif.json"; \
	done

# Dry run to test template without API call
.PHONY: dry-run
dry-run:
	ostruct run prompt.j2 schema.json --fta argument_text texts/$(TEXT_FILE) --dry-run

# List available texts
.PHONY: list-texts
list-texts:
	@echo "Available texts:"
	@ls -1 texts/*.txt | sed 's|texts/||' | sed 's|\.txt$$||'

# Show examples of usage
.PHONY: examples
examples:
	@echo "Usage examples:"
	@echo "  make run                                    # Use default text ($(DEFAULT_TEXT))"
	@echo "  make run TEXT=aint_i_a_woman_by.txt        # Use specific text"
	@echo "  make generate                               # Generate AIF file for default text"
	@echo "  make generate TEXT=yes_virgina_there_is_a_santa_claus.txt  # Generate AIF file for specific text"
	@echo "  make generate-all                           # Generate AIF files for all texts"
	@echo "  make dry-run                                # Test template without API call"
	@echo "  make list-texts                             # Show available texts"

# Clean generated files
.PHONY: clean
clean:
	rm -f *.aif.json

# Help target
.PHONY: help
help: examples
