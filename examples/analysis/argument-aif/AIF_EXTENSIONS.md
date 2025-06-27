# AIF Visualization Extensions

This example now supports **AIF Extensions** for enhanced visualization while maintaining full compatibility with standard AIF viewers and the AIFdb specification.

## What are AIF Extensions?

AIF (Argument Interchange Format) was designed with a "Core concepts, multiple extensions" architecture. The core AIF specification defines the fundamental node types (I, RA, CA, PA, MA) and edge structure, while extensions add specialized attributes for particular domains or applications.

Our **visualization-v1.0** extension adds optional attributes that enhance diagram generation without breaking AIF compatibility.

## Extension Attributes

### Node Extensions

**displayName** (string, max 60 chars)

- Short, readable version of the node text for compact visualization
- Example: `"Scientists agree on climate change"` instead of full text
- Falls back to truncated text if not provided

**category** (string)

- Semantic category for enhanced styling and icons
- Values: `"premise"`, `"conclusion"`, `"inference"`, `"conflict"`, `"preference"`, `"evidence"`, `"assumption"`
- Provides more nuanced visualization than just AIF node types

**strength** (number, 0.0-1.0)

- Argument confidence/weight for potential future enhancements
- 0.9-1.0: Strong/certain claims
- 0.7-0.8: Moderate confidence
- 0.5-0.6: Weak/uncertain claims

### Edge Extensions

**relationshipType** (string)

- Semantic relationship type for enhanced edge visualization
- Values: `"supports"`, `"conflicts"`, `"infers"`, `"attacks"`, `"relates"`
- Enables semantic edge styling and labels

## Enhanced Visualization Features

### Node Styling by Category

- **premise**: Blue styling with 💬 icon
- **evidence**: Green styling with 💬 icon
- **conclusion**: Dark green styling with 🎯 icon
- **inference**: Green styling with ✅ icon
- **conflict**: Pink styling with ⚔️ icon
- **preference**: Orange styling with ⭐ icon
- **assumption**: Purple styling with 🔗 icon

### Edge Styling by Relationship

- **supports**: Dotted arrows `-.->|"supports"|`
- **conflicts**: Dotted arrows `-.->|"conflicts"|`
- **infers**: Thick arrows `==>|"infers"|`
- **attacks**: Thick arrows `==>|"attacks"|`
- **relates**: Solid arrows `-->|"relates"|`

## Example Output

```json
{
  "AIF": {
    "version": "1.0",
    "analyst": "AI Assistant",
    "created": "2024-01-01T00:00:00Z",
    "extensions": ["visualization-v1.0"]
  },
  "nodes": [
    {
      "nodeID": "1",
      "text": "Climate change is real because 97% of scientists agree.",
      "type": "I",
      "timestamp": "2024-01-01T00:00:00Z",
      "displayName": "Scientists agree on climate change",
      "category": "premise",
      "strength": 0.9
    }
  ],
  "edges": [
    {
      "edgeID": "1",
      "fromID": "1",
      "toID": "2",
      "formEdgeID": "",
      "relationshipType": "supports"
    }
  ]
}
```

## Backward Compatibility

- **Standard AIF viewers**: Extension attributes are ignored, core AIF structure works normally
- **Enhanced viewers**: Can utilize extension attributes for richer visualization
- **AIFdb compliance**: Fully compliant with AIFdb specification
- **Fallback behavior**: Visualization script works with or without extensions

## Usage

The extensions are automatically generated when using the enhanced prompt template:

```bash
# Generate AIF with extensions and enhanced visualization
make run TEXT=your_text.txt

# View results
open output/your_text.svg
```

## Technical Implementation

1. **Schema**: Extended to allow optional extension attributes
2. **Template**: Enhanced to generate extension attributes alongside core AIF
3. **Visualization**: Updated to use extension attributes with fallbacks
4. **Compliance**: Maintains full AIFdb compatibility

This approach follows the AIF specification's intended extensibility mechanism, allowing for enhanced visualization while preserving interoperability with standard AIF tools.
