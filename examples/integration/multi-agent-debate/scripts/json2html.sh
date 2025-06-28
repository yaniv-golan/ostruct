#!/usr/bin/env bash
# Convert debate JSON to interactive HTML visualization
set -euo pipefail

TRANSCRIPT=${1:-debate_init.json}
OUTPUT=${2:-debate_detailed.html}
SUMMARY=${3:-summary.json}
SVG_FILE=${4:-debate_overview.svg}

# Generate HTML with embedded CSS and JavaScript
cat > "$OUTPUT" << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Agent Debate - Detailed View</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0 0 20px 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .topic-section {
            background: rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 25px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .topic-label {
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.8;
            margin-bottom: 10px;
            font-weight: 500;
        }
        .topic-text {
            font-size: 1.4em;
            font-weight: 400;
            line-height: 1.4;
            margin: 0;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .header .subtitle {
            margin: 15px 0 0 0;
            opacity: 0.8;
            font-size: 1em;
        }
        .debate-flow {
            padding: 30px;
        }
        .turn {
            margin-bottom: 30px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .turn-header {
            padding: 15px 20px;
            font-weight: 600;
            font-size: 1.1em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .turn-pro .turn-header {
            background: #e3f2fd;
            color: #1565c0;
            border-left: 4px solid #2196f3;
        }
        .turn-con .turn-header {
            background: #fce4ec;
            color: #c2185b;
            border-left: 4px solid #e91e63;
        }
        .turn-content {
            padding: 20px;
            background: white;
        }
        .stance {
            font-weight: 600;
            margin-bottom: 15px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid #dee2e6;
        }
        .argument {
            margin-bottom: 20px;
            line-height: 1.7;
        }
        .citations {
            margin-bottom: 20px;
        }
        .citations h4 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .citation {
            margin-bottom: 8px;
            padding: 8px 12px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9em;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        .citation-number {
            color: #666;
            font-weight: bold;
            min-width: 25px;
            flex-shrink: 0;
        }
        .citation a {
            color: #1976d2;
            text-decoration: none;
        }
        .citation a:hover {
            text-decoration: underline;
        }
        .citation-link {
            color: #1976d2;
            text-decoration: none;
            font-weight: bold;
            padding: 1px 3px;
            border-radius: 3px;
            background-color: rgba(25, 118, 210, 0.1);
        }
        .citation-link:hover {
            background-color: rgba(25, 118, 210, 0.2);
            text-decoration: none;
        }
        .relationships {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }
        .relationships h4 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .relationship {
            display: inline-block;
            margin: 4px 8px 4px 0;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .attacks {
            background: #ffebee;
            color: #c62828;
            border: 1px solid #ffcdd2;
        }
        .supports {
            background: #e8f5e8;
            color: #2e7d32;
            border: 1px solid #c8e6c9;
        }
        .summary {
            margin-top: 40px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .summary h2 {
            margin: 0 0 20px 0;
            color: #333;
        }
        .winner {
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 6px;
        }
        .winner-pro {
            background: #e3f2fd;
            color: #1565c0;
        }
        .winner-con {
            background: #fce4ec;
            color: #c2185b;
        }
        .strongest-point, .verdict {
            margin-bottom: 20px;
        }
        .strongest-point h3, .verdict h3 {
            margin: 0 0 10px 0;
            color: #666;
            font-size: 1em;
        }
        .turn-id {
            background: rgba(255,255,255,0.2);
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: normal;
        }
        .svg-container {
            margin-top: 30px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .svg-container h3 {
            margin: 0 0 20px 0;
            color: #333;
        }
        .svg-container svg {
            max-width: 100%;
            height: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Multi-Agent Debate</h1>
            <div class="topic-section">
                <div class="topic-label">📋 Debate Topic</div>
                <div class="topic-text" id="topic-text">Loading debate topic...</div>
            </div>
            <p class="subtitle">Evidence-based structured argumentation</p>
        </div>

        <div class="debate-flow">
            <div id="turns-container">
                <!-- Turns will be populated by JavaScript -->
            </div>

            <div class="summary" id="summary-container">
                <!-- Summary will be populated by JavaScript -->
            </div>

            <div class="svg-container" id="svg-container">
                <h3>📊 Argument Flow Diagram</h3>
                <!-- SVG will be embedded here -->
            </div>
        </div>
    </div>

    <script>
        // Debate data will be injected here
        const debateData =
EOF

# Inject the JSON data
jq '.' "$TRANSCRIPT" >> "$OUTPUT"

cat >> "$OUTPUT" << 'EOF'
        ;

        // Summary data will be injected here
        const summaryData =
EOF

# Inject summary data if available
if [ -f "$SUMMARY" ]; then
    jq '.' "$SUMMARY" >> "$OUTPUT"
else
    echo "null" >> "$OUTPUT"
fi

cat >> "$OUTPUT" << 'EOF'
        ;

        // Populate the page
        document.addEventListener('DOMContentLoaded', function() {
            // Set topic - extract from debate data
            const topicElement = document.getElementById('topic-text');
            let topic = '';

            // Try to get topic from the JSON topic field first
            if (debateData.topic && debateData.topic.trim() !== '') {
                topic = debateData.topic;
            }
            // If no topic field, extract from the first turn's stance
            else if (debateData.turns && debateData.turns.length > 0 && debateData.turns[0].stance) {
                topic = debateData.turns[0].stance.trim();
            }
            // Fallback to placeholder that will be replaced by shell script
            else {
                topic = 'TOPIC_PLACEHOLDER';
            }

            topicElement.textContent = topic;

            // Populate turns
            const turnsContainer = document.getElementById('turns-container');
            debateData.turns.forEach((turn, index) => {
                const turnDiv = document.createElement('div');
                turnDiv.className = `turn turn-${turn.agent}`;

                const relationships = [];
                if (turn.attacks && turn.attacks.length > 0) {
                    turn.attacks.forEach(attackedTurn => {
                        relationships.push(`<span class="relationship attacks">⚔️ Attacks Turn ${attackedTurn + 1}</span>`);
                    });
                }
                if (turn.supports && turn.supports.length > 0) {
                    turn.supports.forEach(supportedTurn => {
                        relationships.push(`<span class="relationship supports">🤝 Supports Turn ${supportedTurn + 1}</span>`);
                    });
                }

                // Post-process citations: convert any format to numbered citations
                let processedResponse = turn.response;
                let allCitations = [];

                // Extract inline citations from text: [text](url) or ([text](url))
                const inlineLinkRegex = /\(?(\[([^\]]+)\]\(([^)]+)\))\)?/g;
                let match;
                const inlineMatches = [];

                while ((match = inlineLinkRegex.exec(turn.response)) !== null) {
                    const fullMatch = match[1]; // [text](url) part
                    const linkText = match[2];  // text inside brackets
                    const url = match[3];       // url inside parentheses

                    inlineMatches.push({
                        fullMatch: match[0], // includes potential outer parentheses
                        linkMatch: fullMatch,
                        text: linkText,
                        url: url,
                        source: 'inline'
                    });

                    // Check if we have a better title in structured citations
                    let betterTitle = linkText;
                    if (turn.citations) {
                        // Remove query parameters for URL matching
                        const cleanUrl = url.split('?')[0];
                        const structuredCitation = turn.citations.find(c =>
                            c.url === url || c.url === cleanUrl || c.url.split('?')[0] === cleanUrl
                        );
                        if (structuredCitation && structuredCitation.title && structuredCitation.title !== structuredCitation.url) {
                            betterTitle = structuredCitation.title;
                        }
                    }

                    // Add to citations list with best available title
                    allCitations.push({
                        url: url,
                        title: betterTitle,
                        source: 'inline'
                    });
                }

                // Replace inline citations with numbered references
                for (const inlineMatch of inlineMatches) {
                    const citationIndex = allCitations.findIndex(c => c.url === inlineMatch.url);
                    const citationNumber = citationIndex + 1;

                    // Replace the inline citation with numbered link
                    const replacement = `<a href="${inlineMatch.url}" target="_blank" class="citation-link">[${citationNumber}]</a>`;
                    processedResponse = processedResponse.replace(inlineMatch.fullMatch, replacement);
                }

                // Also handle any existing numbered citations [1], [2], etc.
                allCitations.forEach((citation, index) => {
                    const citationNumber = index + 1;
                    const numberRegex = new RegExp(`\\[${citationNumber}\\](?![^<]*>)`, 'g');
                    processedResponse = processedResponse.replace(numberRegex,
                        `<a href="${citation.url}" target="_blank" class="citation-link">[${citationNumber}]</a>`);
                });

                // Generate citations HTML
                const citations = allCitations.map((citation, index) => {
                    const citationNumber = index + 1;
                    return `<div class="citation"><span class="citation-number">[${citationNumber}]</span> <a href="${citation.url}" target="_blank">${citation.title}</a></div>`;
                }).join('');

                turnDiv.innerHTML = `
                    <div class="turn-header">
                        <span>${turn.agent.toUpperCase()}</span>
                        <span class="turn-id">Turn ${index + 1}</span>
                    </div>
                    <div class="turn-content">
                        <div class="stance">${turn.stance}</div>
                        <div class="argument">${processedResponse}</div>
                        ${citations ? `
                            <div class="citations">
                                <h4>📚 Citations</h4>
                                ${citations}
                            </div>
                        ` : ''}
                        ${relationships.length > 0 ? `
                            <div class="relationships">
                                <h4>🔗 Argument Relationships</h4>
                                ${relationships.join('')}
                            </div>
                        ` : ''}
                    </div>
                `;

                turnsContainer.appendChild(turnDiv);
            });

            // Populate summary if available
            if (summaryData) {
                const summaryContainer = document.getElementById('summary-container');
                summaryContainer.innerHTML =
                    '<h2>🏆 Debate Results</h2>' +
                    '<div class="winner winner-' + summaryData.winning_side.toLowerCase() + '">' +
                        '🥇 Winner: ' + summaryData.winning_side.toUpperCase() +
                    '</div>' +
                    '<div class="strongest-point">' +
                        '<h3>💪 Strongest Argument</h3>' +
                        '<p>' + summaryData.strongest_point + '</p>' +
                    '</div>' +
                    '<div class="verdict">' +
                        '<h3>📋 Judge\'s Reasoning</h3>' +
                        '<p>' + summaryData.verdict + '</p>' +
                    '</div>';
            } else {
                document.getElementById('summary-container').style.display = 'none';
            }

            // Embed SVG if available
            const svgContainer = document.getElementById('svg-container');
            // SVG content will be injected here by the shell script
        });
    </script>
</body>
</html>
EOF

# Read topic from topic.txt if available and inject it as fallback
if [ -f "topic.txt" ]; then
    TOPIC_TEXT=$(cat topic.txt | tr -d '\n' | sed 's/"/\\"/g')
    sed -i.bak "s|TOPIC_PLACEHOLDER|${TOPIC_TEXT}|" "$OUTPUT"
    rm -f "${OUTPUT}.bak"
fi

# Embed SVG if available
if [ -f "$SVG_FILE" ]; then
    # Extract SVG content and inject it into the HTML
    SVG_CONTENT=$(cat "$SVG_FILE")
    # Replace the SVG container placeholder with actual SVG
    sed -i.bak "s|<!-- SVG will be embedded here -->|${SVG_CONTENT}|" "$OUTPUT"
    rm -f "${OUTPUT}.bak"
    echo "Generated interactive HTML with embedded SVG: $OUTPUT"
else
    # Hide SVG container if no SVG available
    sed -i.bak "s|<!-- SVG will be injected here by the shell script -->|document.getElementById('svg-container').style.display = 'none';|" "$OUTPUT"
    rm -f "${OUTPUT}.bak"
    echo "Generated interactive HTML (no SVG available): $OUTPUT"
fi
