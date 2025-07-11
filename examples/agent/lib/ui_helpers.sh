#!/usr/bin/env bash
# ui_helpers.sh – gum-based UI helpers for agent system
#
# Provides enhanced visual feedback using Charmbracelet's gum tool
# Falls back to plain text if gum is not available
#
# Functions:
#   ui_init              – Initialize UI system
#   ui_header            – Display header with title
#   ui_step_start        – Announce step start with progress
#   ui_step_success      – Display successful step completion
#   ui_step_warning      – Display step warning
#   ui_step_error        – Display step error
#   ui_progress          – Show progress bar
#   ui_spinner           – Show spinner during operations
#   ui_status            – Display status information
#   ui_final_result      – Display final result with formatting

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "ui_helpers.sh: source this file, do not execute" >&2
    exit 1
fi

# Global UI state
UI_ENABLED=true
GUM_AVAILABLE=false

# Initialize UI system
ui_init() {
    # Check if gum is available
    if command -v gum >/dev/null 2>&1; then
        GUM_AVAILABLE=true
    else
        GUM_AVAILABLE=false
    fi

    # Check if we're in a terminal
    if [[ ! -t 1 ]]; then
        UI_ENABLED=false
    fi

    # Allow override via environment
    if [[ "${AGENT_UI_DISABLE:-false}" == "true" ]]; then
        UI_ENABLED=false
    fi
}

# Display header with title
ui_header() {
    local title="$1"
    local subtitle="${2:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        echo
        gum style --foreground="#00D4AA" --bold --border="rounded" --padding="1 2" --margin="1 0" "$title"
        if [[ -n "$subtitle" ]]; then
            gum style --foreground="#7C7C7C" --italic "$subtitle"
        fi
        echo
    else
        echo "=== $title ==="
        if [[ -n "$subtitle" ]]; then
            echo "$subtitle"
        fi
        echo
    fi
}

# Announce step start with progress
ui_step_start() {
    local step_name="$1"
    local current="${2:-0}"
    local total="${3:-0}"
    local description="${4:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        local progress_text=""
        if [[ $total -gt 0 ]]; then
            progress_text=" ($current/$total)"
        fi

        gum style --foreground="#FFD700" --bold "▶ $step_name$progress_text"
        if [[ -n "$description" ]]; then
            gum style --foreground="#A0A0A0" --italic "  $description"
        fi
    else
        local progress_text=""
        if [[ $total -gt 0 ]]; then
            progress_text=" ($current/$total)"
        fi
        echo "▶ $step_name$progress_text"
        if [[ -n "$description" ]]; then
            echo "  $description"
        fi
    fi
}

# Display successful step completion
ui_step_success() {
    local step_name="$1"
    local result="${2:-}"
    local duration="${3:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        local duration_text=""
        if [[ -n "$duration" ]]; then
            duration_text=" (${duration}s)"
        fi

        gum style --foreground="#00D4AA" --bold "✓ $step_name$duration_text"
        if [[ -n "$result" ]]; then
            # Truncate long results
            local display_result="$result"
            if [[ ${#result} -gt 100 ]]; then
                display_result="${result:0:97}..."
            fi
            gum style --foreground="#A0A0A0" "  $display_result"
        fi
    else
        local duration_text=""
        if [[ -n "$duration" ]]; then
            duration_text=" (${duration}s)"
        fi
        echo "✓ $step_name$duration_text"
        if [[ -n "$result" ]]; then
            echo "  $result"
        fi
    fi
}

# Display step warning
ui_step_warning() {
    local step_name="$1"
    local warning="$2"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        gum style --foreground="#FFB000" --bold "⚠ $step_name"
        gum style --foreground="#FFB000" "  $warning"
    else
        echo "⚠ $step_name"
        echo "  $warning"
    fi
}

# Display step error
ui_step_error() {
    local step_name="$1"
    local error="$2"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        gum style --foreground="#FF6B6B" --bold "✗ $step_name"
        gum style --foreground="#FF6B6B" "  $error"
    else
        echo "✗ $step_name"
        echo "  $error"
    fi
}

# Show progress bar
ui_progress() {
    local current="$1"
    local total="$2"
    local label="${3:-Progress}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        local percentage=$((current * 100 / total))
        echo "$label: $current/$total ($percentage%)"
        # Note: gum doesn't have a built-in progress bar, so we use text
    else
        local percentage=$((current * 100 / total))
        echo "$label: $current/$total ($percentage%)"
    fi
}

# Show spinner during operations
ui_spinner() {
    local message="$1"
    local command="$2"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        gum spin --spinner="dot" --title="$message" -- $command
    else
        echo "$message..."
        eval "$command"
    fi
}

# Display status information
ui_status() {
    local status="$1"
    local details="${2:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        gum style --foreground="#00BFFF" --bold "ℹ $status"
        if [[ -n "$details" ]]; then
            gum style --foreground="#A0A0A0" "  $details"
        fi
    else
        echo "ℹ $status"
        if [[ -n "$details" ]]; then
            echo "  $details"
        fi
    fi
}

# Display final result with formatting
ui_final_result() {
    local success="$1"
    local title="$2"
    local content="$3"

    echo
    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        if [[ "$success" == "true" ]]; then
            gum style --foreground="#00D4AA" --bold --border="rounded" --padding="1 2" --margin="1 0" "✓ $title"
        else
            gum style --foreground="#FF6B6B" --bold --border="rounded" --padding="1 2" --margin="1 0" "✗ $title"
        fi

        if [[ -n "$content" ]]; then
            gum style --foreground="#E0E0E0" --padding="0 2" "$content"
        fi
    else
        if [[ "$success" == "true" ]]; then
            echo "=== ✓ $title ==="
        else
            echo "=== ✗ $title ==="
        fi

        if [[ -n "$content" ]]; then
            echo "$content"
        fi
        echo "==================="
    fi
    echo
}

# Display turn header
ui_turn_header() {
    local turn="$1"
    local max_turns="$2"
    # Remove the redundant task parameter - it's already shown at the start

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        echo ""
        gum style --foreground="#00D7FF" --bold "Turn $turn/$max_turns"
    else
        echo ""
        echo "Turn $turn/$max_turns"
    fi
}

# Display planning phase
ui_planning_phase() {
    local phase="$1"
    local details="${2:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        gum style --foreground="#FF69B4" --bold "🧠 $phase"
        if [[ -n "$details" ]]; then
            gum style --foreground="#A0A0A0" "  $details"
        fi
    else
        echo "🧠 $phase"
        if [[ -n "$details" ]]; then
            echo "  $details"
        fi
    fi
}

# Display critic feedback
ui_critic_feedback() {
    local score="$1"
    local comment="$2"
    local action="$3"  # "approved", "warning", "blocked"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        case "$action" in
            "approved")
                gum style --foreground="#00D4AA" --bold "👍 Critic Score: $score"
                ;;
            "warning")
                gum style --foreground="#FFB000" --bold "⚠ Critic Score: $score"
                ;;
            "blocked")
                gum style --foreground="#FF6B6B" --bold "🚫 Critic Score: $score"
                ;;
        esac

        if [[ -n "$comment" ]]; then
            gum style --foreground="#A0A0A0" "  $comment"
        fi
    else
        case "$action" in
            "approved")
                echo "👍 Critic Score: $score"
                ;;
            "warning")
                echo "⚠ Critic Score: $score"
                ;;
            "blocked")
                echo "🚫 Critic Score: $score"
                ;;
        esac

        if [[ -n "$comment" ]]; then
            echo "  $comment"
        fi
    fi
}

# Display planning phase with progress tracking
ui_planning_progress() {
    local phase="$1"
    local current="${2:-0}"
    local total="${3:-0}"
    local details="${4:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        local progress_text=""
        if [[ $total -gt 0 ]]; then
            progress_text=" ($current/$total)"
        fi

        gum style --foreground="#FF69B4" --bold "🧠 $phase$progress_text"
        if [[ -n "$details" ]]; then
            gum style --foreground="#A0A0A0" "  $details"
        fi
    else
        local progress_text=""
        if [[ $total -gt 0 ]]; then
            progress_text=" ($current/$total)"
        fi
        echo "🧠 $phase$progress_text"
        if [[ -n "$details" ]]; then
            echo "  $details"
        fi
    fi
}

# Show plan generation progress with individual plan status
ui_plan_status() {
    local plan_id="$1"
    local status="$2"  # "generating", "completed", "failed"
    local details="${3:-}"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        case "$status" in
            "generating")
                gum style --foreground="#FFD700" "  ⏳ Plan $plan_id: Generating..."
                ;;
            "completed")
                gum style --foreground="#00D4AA" "  ✓ Plan $plan_id: Generated successfully"
                ;;
            "failed")
                gum style --foreground="#FF6B6B" "  ✗ Plan $plan_id: Generation failed"
                ;;
            "duplicate")
                gum style --foreground="#FFB000" "  ⚠ Plan $plan_id: Duplicate (skipped)"
                ;;
        esac

        if [[ -n "$details" ]]; then
            gum style --foreground="#A0A0A0" "    $details"
        fi
    else
        case "$status" in
            "generating")
                echo "  ⏳ Plan $plan_id: Generating..."
                ;;
            "completed")
                echo "  ✓ Plan $plan_id: Generated successfully"
                ;;
            "failed")
                echo "  ✗ Plan $plan_id: Generation failed"
                ;;
            "duplicate")
                echo "  ⚠ Plan $plan_id: Duplicate (skipped)"
                ;;
        esac

        if [[ -n "$details" ]]; then
            echo "    $details"
        fi
    fi
}

# Show a summary of plan generation results
ui_plan_summary() {
    local total="$1"
    local completed="$2"
    local failed="$3"
    local duplicates="$4"

    if [[ "$UI_ENABLED" == "true" && "$GUM_AVAILABLE" == "true" ]]; then
        echo
        gum style --foreground="#9370DB" --bold "📋 Plan Generation Summary"
        gum style --foreground="#A0A0A0" "  Total requested: $total"

        if [[ $completed -gt 0 ]]; then
            gum style --foreground="#00D4AA" "  ✓ Successfully generated: $completed"
        fi

        if [[ $duplicates -gt 0 ]]; then
            gum style --foreground="#FFB000" "  ⚠ Duplicates removed: $duplicates"
        fi

        if [[ $failed -gt 0 ]]; then
            gum style --foreground="#FF6B6B" "  ✗ Failed: $failed"
        fi
        echo
    else
        echo
        echo "📋 Plan Generation Summary"
        echo "  Total requested: $total"

        if [[ $completed -gt 0 ]]; then
            echo "  ✓ Successfully generated: $completed"
        fi

        if [[ $duplicates -gt 0 ]]; then
            echo "  ⚠ Duplicates removed: $duplicates"
        fi

        if [[ $failed -gt 0 ]]; then
            echo "  ✗ Failed: $failed"
        fi
        echo
    fi
}

# Export all functions
export -f ui_init ui_header ui_step_start ui_step_success ui_step_warning ui_step_error
export -f ui_progress ui_spinner ui_status ui_final_result ui_turn_header ui_planning_phase ui_critic_feedback
export -f ui_planning_progress ui_plan_status ui_plan_summary
