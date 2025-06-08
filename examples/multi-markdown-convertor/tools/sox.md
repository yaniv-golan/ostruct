---
tool: sox
kind: utility
tool_min_version: "14.4"
tool_version_check: "sox --version"
recommended_output_format: wav
---

# SoX - Sound eXchange

## Overview

SoX is the Swiss Army knife of sound processing programs. It can convert, process, and normalize audio files, including extracting and processing embedded audio tracks from Office documents.

**IMPORTANT**: SoX processes audio files. For extracting audio from Office documents, you may need to extract the media first using other tools.

## Installation

- **macOS**: `brew install sox`
- **Ubuntu/Debian**: `apt-get install sox`
- **Windows**: Download from <http://sox.sourceforge.net/>

## Capabilities

- Audio format conversion
- Audio normalization and processing
- Volume adjustment
- Noise reduction
- Audio effects and filters
- Batch processing

## Common Usage Patterns

### Convert audio format

```bash
sox {{INPUT_FILE}} {{OUTPUT_FILE}}
```

- Automatically detects formats from file extensions

### Normalize audio volume

```bash
sox {{INPUT_FILE}} {{OUTPUT_FILE}} norm
```

- `norm`: Normalize to maximum volume without clipping

### Convert to specific format

```bash
sox {{INPUT_FILE}} -r 44100 -c 2 -b 16 {{OUTPUT_FILE}}
```

- `-r 44100`: Sample rate 44.1kHz
- `-c 2`: Stereo (2 channels)
- `-b 16`: 16-bit depth

### Extract audio information

```bash
sox --info {{INPUT_FILE}}
```

- Shows audio file metadata and properties

### Apply noise reduction

```bash
sox {{INPUT_FILE}} {{OUTPUT_FILE}} noisered profile.txt 0.21
```

- Applies noise reduction using a noise profile

### Trim audio

```bash
sox {{INPUT_FILE}} {{OUTPUT_FILE}} trim 10 30
```

- Extracts 30 seconds starting from 10 seconds

## Output Formats

- WAV (uncompressed)
- MP3 (with LAME encoder)
- FLAC (lossless compression)
- OGG Vorbis
- Many others

## Security Considerations

- ✅ Local processing only
- ✅ No network access required
- ✅ Safe for sensitive documents
- ✅ No data transmission to external services

## Performance

- **Speed**: Fast for audio processing
- **Memory**: Efficient for most audio files
- **File Size**: Handles various audio file sizes

## Best Practices

1. Use `--info` to check audio properties first
2. Normalize audio for consistent processing
3. Convert to WAV for maximum compatibility
4. Use appropriate sample rates for target use
5. Test effects on small samples before batch processing
