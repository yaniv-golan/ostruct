# Multi-Agent Evidence-Seeking Debate

This example demonstrates a structured debate between two AI agents (PRO and CON) on a given topic, with each agent able to conduct web searches for evidence. The debate generates a live Mermaid diagram showing the argument flow and relationships.

## Features

- **Two-agent debate**: PRO and CON sides with structured turns
- **Evidence-based arguments**: Each agent can perform up to 2 web searches per turn
- **Structured output**: All responses validate against JSON schemas
- **Colorful visual mapping**: Auto-generated Mermaid diagrams with color-coded agents (blue PRO, red CON) and relationships (🤝 supports, ⚔️ attacks)
- **Impartial judging**: Final summary with verdict and source auditing

## Quick Start

```bash
# Run a 2-round debate (2 turns per side)
cd examples/multi_agent_debate
./run_debate.sh 2
open output/debate_detailed.html  # Interactive detailed view
open output/debate_overview.svg   # Clean structure diagram
cat output/summary.json

# Or with a custom topic
./run_debate.sh 2 "Artificial intelligence should be regulated by international law"
```

## Requirements

- **Network access**: Required for OpenAI API and web search
- **Environment**: `OPENAI_API_KEY` must be set

### Auto-Installing Dependencies

The script automatically installs required tools if missing:

- **jq**: JSON processor (via package manager, GitHub binary, or Docker)
- **Mermaid CLI**: Diagram generation (via npx or Docker)

No manual setup required - just run the script on a fresh system!

## File Structure

```
multi_agent_debate/
├── README.md              # This documentation
├── topic.txt              # The debate topic
├── run_debate.sh          # Main script to run complete debate
├── prompts/               # Jinja2 templates
│   ├── pro.j2            # Template for PRO arguments
│   ├── con.j2            # Template for CON arguments
│   └── summary.j2        # Template for judge analysis
├── schemas/               # JSON schemas for structured output
│   ├── turn.json         # Schema for individual turns
│   └── summary.json      # Schema for final summary
├── scripts/               # Utility scripts
│   ├── run_round.sh      # Helper for individual turns
│   ├── json2mermaid.sh   # Converts transcript to Mermaid diagram
│   ├── json2html.sh      # Converts transcript to interactive HTML
│   ├── ensure_mermaid.sh # Installs Mermaid CLI if needed
│   └── ensure_jq.sh      # Installs jq JSON processor if needed
└── output/                # Generated files (created during run)
    ├── debate_init.json  # Full debate transcript
    ├── summary.json      # Judge analysis and verdict
    ├── debate_overview.svg    # Clean argument flow diagram
    └── debate_detailed.html   # Interactive detailed view
```

## Usage

### Basic Debate

```bash
# Show help and usage examples
./run_debate.sh --help

# Default 2 rounds (uses topic.txt)
./run_debate.sh

# Custom number of rounds
./run_debate.sh 4

# Custom topic via command line
./run_debate.sh 2 "Social media platforms should be liable for user-generated content"

# Custom rounds and topic
./run_debate.sh 3 "Universal basic income should be implemented globally"
```

### Manual Round Execution

```bash
# Run individual turns (requires topic argument)
./scripts/run_round.sh pro 1 "Your debate topic here"
./scripts/run_round.sh con 1 "Your debate topic here"
./scripts/run_round.sh pro 2 "Your debate topic here"
./scripts/run_round.sh con 2 "Your debate topic here"
```

### Custom Topics

You can specify topics in two ways:

**Option 1: Command line argument (recommended)**

```bash
./run_debate.sh 3 "Artificial intelligence should be regulated by international law"
```

**Option 2: Edit topic.txt file**

```bash
echo "Artificial intelligence should be regulated by international law." > topic.txt
./run_debate.sh 3
```

## Output Files

All generated files are placed in the `output/` directory:

- **`output/debate_init.json`** - Complete debate transcript with all turns
- **`output/summary.json`** - Judge's verdict and analysis
- **`output/debate_detailed.html`** - Interactive detailed view with full arguments and citations
- **`output/debate_overview.svg`** - Clean argument flow diagram for structure overview

**Note**: The `output/` directory is preserved in git with a `.gitkeep` file, but the actual output files are ignored (via `.gitignore`) to avoid cluttering the repository with generated content.

## Cost Considerations

Approximate cost per debate:

- **2 rounds**: ~4 agent turns + 2 web searches each + 1 summary = moderate cost
- **4 rounds**: ~8 agent turns + 2 web searches each + 1 summary = higher cost

Each agent can perform up to 2 web searches per turn, so total searches = rounds × 2 agents × 2 searches.

## Technical Details

- Uses `--enable-tool web-search` for real-time information gathering
- All JSON outputs validate against strict schemas
- Colorful Mermaid diagrams show argument support/attack relationships with visual coding
- Auto-installs dependencies (jq, Mermaid CLI) if not available
- Cross-platform support: Linux, macOS, Windows (WSL/Git Bash)
- Handles both auto-naming and explicit variable assignment

## Example Output

The debate generates:

1. **Structured arguments** with citations and source validation
2. **Relationship mapping** showing which arguments support/attack others
3. **Dual visualizations**:
   - **Interactive HTML** - Full arguments, citations, and relationships in a readable format
   - **Colorful SVG diagram** - Clean structural overview with color-coded agents and relationships
4. **Impartial judgment** with winner determination and source auditing
