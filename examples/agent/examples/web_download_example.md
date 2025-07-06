# Web Download Example

This example demonstrates the agent's ability to download content from the web and process it.

## Task
Download JSON data from httpbin.org and extract specific information from it.

## Usage
```bash
cd examples/agent
./runner.sh "Download JSON data from https://httpbin.org/json and extract the 'url' field"
```

## Expected Outcome
1. The agent will use the `curl` tool to download the JSON data
2. It will use the `jq` tool to extract the 'url' field from the JSON
3. The final answer should show the extracted URL

## Alternative Task
```bash
./runner.sh "Download JSON from httpbin.org/json, save it to a file, then read and analyze it"
```

## Files Created
- `workdir/sandbox_*/downloaded_data.json` - The downloaded JSON file (if saved)

## Tools Used
- `curl` - For downloading the JSON data
- `jq` - For parsing and extracting data from JSON
- `write_file` - For saving data to file (if needed)
- `read_file` - For reading saved data (if needed)

## Verification
```bash
# Check if any files were created
ls -la workdir/sandbox_*/

# View the logs
tail -f logs/run_*.log
```

## Notes
- The agent will automatically handle network timeouts and size limits
- JSON parsing errors will be caught and handled gracefully
- The download is limited to 10MB for security