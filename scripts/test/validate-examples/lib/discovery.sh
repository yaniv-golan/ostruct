#!/bin/bash
# Discovery library - finds README files and manages caching of parsed results

# Check if a file is gitignored
is_file_gitignored() {
    local file_path="$1"

    if ! command -v git >/dev/null 2>&1; then
        return 1  # Git not available, assume not ignored
    fi

    # Convert to relative path from project root
    local relative_path="${file_path#${PROJECT_ROOT}/}"

    # If path is outside project root, not gitignored
    if [[ "$relative_path" == "$file_path" ]]; then
        return 1
    fi

    # Check if file is gitignored
    cd "$PROJECT_ROOT" && git check-ignore "$relative_path" >/dev/null 2>&1
}

# Find all README files in the given directory and subdirectories
discover_readme_files() {
    local search_dir="$1"

    if [[ ! -d "$search_dir" ]]; then
        vlog "ERROR" "Directory does not exist: $search_dir" >&2
        return 1
    fi

    # Find all README files (case insensitive), respecting .gitignore
    if command -v git >/dev/null 2>&1 && [[ -f "${PROJECT_ROOT}/.gitignore" ]]; then
        # Use git ls-files to respect .gitignore patterns
        local relative_search_dir="${search_dir#${PROJECT_ROOT}/}"

        # If search_dir is outside PROJECT_ROOT, use it as-is
        if [[ "$relative_search_dir" == "$search_dir" ]]; then
            relative_search_dir="$search_dir"
        fi

        local readme_files
        readme_files=$(cd "$PROJECT_ROOT" && git ls-files "$relative_search_dir" 2>/dev/null | \
            grep -i -E "(readme\.md|readme\.txt|readme\.rst)$" | \
            sed "s|^|${PROJECT_ROOT}/|" | \
            sort)

        # Log how many files were found vs total
        local total_readme_files
        total_readme_files=$(find "$search_dir" -type f \( -iname "readme.md" -o -iname "readme.txt" -o -iname "readme.rst" \) | wc -l)
        local git_readme_files
        git_readme_files=$(echo "$readme_files" | grep -c . || echo 0)

        if [[ $total_readme_files -gt $git_readme_files ]]; then
            local skipped=$((total_readme_files - git_readme_files))
            vlog "DEBUG" "Skipped $skipped gitignored README files" >&2
        fi

        echo "$readme_files"
    else
        # Fallback to find if git is not available
        vlog "DEBUG" "Git not available or no .gitignore found, using find" >&2
        find "$search_dir" -type f \( -iname "readme.md" -o -iname "readme.txt" -o -iname "readme.rst" \) | sort
    fi
}

# Get the cache file path for a README file
get_cache_file_path() {
    local readme_file="$1"
    local relative_path="${readme_file#${PROJECT_ROOT}/}"
    local cache_file="${CACHE_DIR}/${relative_path//\//_}.cache"
    echo "$cache_file"
}

# Get the commands file path for a README file
get_commands_file_path() {
    local readme_file="$1"
    local relative_path="${readme_file#${PROJECT_ROOT}/}"
    local commands_file="${CACHE_DIR}/${relative_path//\//_}.commands"
    echo "$commands_file"
}

# Check if cache is valid for a README file
is_cache_valid() {
    local readme_file="$1"
    local cache_file="$2"

    if [[ "$FORCE_REFRESH" == "true" ]]; then
        vlog "DEBUG" "Force refresh enabled, cache invalid" >&2
        return 1
    fi

    if [[ ! -f "$cache_file" ]]; then
        vlog "DEBUG" "Cache file does not exist: $cache_file" >&2
        return 1
    fi

    # Compare modification times
    if [[ "$readme_file" -nt "$cache_file" ]]; then
        vlog "DEBUG" "README file is newer than cache: $readme_file" >&2
        return 1
    fi

    vlog "DEBUG" "Cache is valid for: $readme_file" >&2
    return 0
}

# Parse README file with caching support
parse_readme_with_cache() {
    local readme_file="$1"
    local cache_file=$(get_cache_file_path "$readme_file")
    local commands_file=$(get_commands_file_path "$readme_file")

    # Ensure cache directory exists
    mkdir -p "$(dirname "$cache_file")"

    if is_cache_valid "$readme_file" "$cache_file"; then
        vlog "DEBUG" "Using cached results for: ${readme_file#${PROJECT_ROOT}/}" >&2
        echo "$commands_file"
        return 0
    fi

    vlog "DEBUG" "Parsing README file: ${readme_file#${PROJECT_ROOT}/}" >&2

    # Extract commands from README
    local commands=$(extract_ostruct_commands "$readme_file")

    if [[ -n "$commands" ]]; then
        # Save commands to file
        echo "$commands" > "$commands_file"

        # Create cache metadata
        cat > "$cache_file" << EOF
# Cache metadata for ${readme_file}
README_FILE="$readme_file"
PARSED_AT=$(date -Iseconds)
README_MTIME=$(stat -f %m "$readme_file" 2>/dev/null || stat -c %Y "$readme_file" 2>/dev/null)
COMMANDS_COUNT=$(echo "$commands" | wc -l)
EOF

        vlog "DEBUG" "Cached $(echo "$commands" | wc -l) commands from ${readme_file#${PROJECT_ROOT}/}" >&2
    else
        # Create empty commands file
        touch "$commands_file"

        # Create cache metadata for empty result
        cat > "$cache_file" << EOF
# Cache metadata for ${readme_file}
README_FILE="$readme_file"
PARSED_AT=$(date -Iseconds)
README_MTIME=$(stat -f %m "$readme_file" 2>/dev/null || stat -c %Y "$readme_file" 2>/dev/null)
COMMANDS_COUNT=0
EOF

        vlog "DEBUG" "No commands found in ${readme_file#${PROJECT_ROOT}/}" >&2
    fi

    echo "$commands_file"
}

# Clear all cached results
clear_cache() {
    vlog "INFO" "Clearing all cached results..." >&2
    rm -rf "${CACHE_DIR}"/*
}

# Show cache statistics
show_cache_stats() {
    local cache_files=$(find "${CACHE_DIR}" -name "*.cache" 2>/dev/null | wc -l)
    local commands_files=$(find "${CACHE_DIR}" -name "*.commands" 2>/dev/null | wc -l)

    echo "Cache Statistics:"
    echo "  Cache files: $cache_files"
    echo "  Commands files: $commands_files"

    if [[ $cache_files -gt 0 ]]; then
        echo "  Cache entries:"
        find "${CACHE_DIR}" -name "*.cache" -exec basename {} .cache \; | sort | sed 's/^/    /'
    fi
}
