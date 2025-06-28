# Makefile for arg_to_aif example

# Default text to use if TEXT is not specified
DEFAULT_TEXT := paradox_of_the_court.txt

# Default model to use if MODEL is not specified
DEFAULT_MODEL := gpt-4.1

# Use TEXT parameter if provided, otherwise use default
TEXT_FILE := $(if $(TEXT),$(TEXT),$(DEFAULT_TEXT))

# Use MODEL parameter if provided, otherwise use default
MODEL_NAME := $(if $(MODEL),$(MODEL),$(DEFAULT_MODEL))

# Default target - now includes visualization
.PHONY: run
run: visualize

# Console output only (original behavior)
.PHONY: console
console:
	ostruct run prompt.j2 schema.json --file argument_text texts/$(TEXT_FILE) --model $(MODEL_NAME) | jq .

# Generate AIF file with Mermaid visualization
.PHONY: visualize
visualize:
	@echo "Generating AIF analysis with visualization for $(TEXT_FILE)..."
	./scripts/run_with_visualization.sh texts/$(TEXT_FILE) $(basename $(TEXT_FILE) .txt) $(MODEL_NAME)

# Generate AIF file directly to output (legacy)
.PHONY: generate
generate:
	@echo "Generating AIF file for $(TEXT_FILE)..."
	ostruct run prompt.j2 schema.json --file argument_text texts/$(TEXT_FILE) --model $(MODEL_NAME) --output-file output/$(basename $(TEXT_FILE)).aif.json
	@echo "Generated: output/$(basename $(TEXT_FILE)).aif.json"

# Generate all available texts with visualizations
.PHONY: generate-all
generate-all:
	@for text in texts/*.txt; do \
		echo "Generating AIF analysis with visualization for $$text..."; \
		./scripts/run_with_visualization.sh "$$text" "$$(basename "$$text" .txt)" $(MODEL_NAME); \
	done

# Generate all available texts as AIF files only (legacy)
.PHONY: generate-all-json
generate-all-json:
	@for text in texts/*.txt; do \
		base=$$(basename "$$text" .txt); \
		echo "Generating AIF file for $$text..."; \
		ostruct run prompt.j2 schema.json --file argument_text "$$text" --model $(MODEL_NAME) --output-file "output/$$base.aif.json"; \
		echo "Generated: output/$$base.aif.json"; \
	done

# Dry run to test template without API call
.PHONY: dry-run
dry-run:
	ostruct run prompt.j2 schema.json --file argument_text texts/$(TEXT_FILE) --model $(MODEL_NAME) --dry-run

# List available texts
.PHONY: list-texts
list-texts:
	@echo "Available texts:"
	@ls -1 texts/*.txt | sed 's|texts/||' | sed 's|\.txt$$||'

# Show examples of usage
.PHONY: examples
examples:
	@echo "Usage examples:"
	@echo "  make run                                    # Generate AIF + Mermaid visualization ($(DEFAULT_TEXT), $(DEFAULT_MODEL))"
	@echo "  make run TEXT=aint_i_a_woman_by.txt        # Generate AIF + Mermaid for specific text"
	@echo "  make run MODEL=gpt-4o                      # Use different model"
	@echo "  make run TEXT=essay.txt MODEL=gpt-4.1      # Specify both text and model"
	@echo "  make console                                # Console output only (original behavior)"
	@echo "  make visualize                              # Generate AIF + Mermaid visualization"
	@echo "  make generate                               # Generate AIF file only"
	@echo "  make generate-all                           # Generate AIF + Mermaid for all texts"
	@echo "  make generate-all-json                      # Generate AIF files only for all texts"
	@echo "  make dry-run                                # Test template without API call"
	@echo "  make list-texts                             # Show available texts"
	@echo "  make clean                                  # Remove generated files"

# Clean generated files
.PHONY: clean
clean:
	rm -f *.aif.json output/*.aif.json output/*.mmd output/*.svg output/*.png output/*.pdf

# Help target
.PHONY: help
help: examples
