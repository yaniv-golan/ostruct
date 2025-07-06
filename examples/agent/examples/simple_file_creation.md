# Simple File Creation Example

This example demonstrates the basic functionality of the agent system by creating and manipulating files.

## Task
Create a text file named "greeting.txt" with the content "Hello, World!" and then read it back to confirm.

## Usage
```bash
cd examples/agent
./runner.sh "Create a file named greeting.txt with the content 'Hello, World!' and then read it back"
```

## Expected Outcome
1. The agent will plan to use the `write_file` tool to create the file
2. It will then use the `read_file` tool to verify the content
3. The final answer should confirm the file was created and contains the expected content

## Files Created
- `workdir/sandbox_*/greeting.txt` - The created file

## Log Output
Check the logs in `logs/run_*.log` to see the detailed execution flow.

## Verification
```bash
# Check the created file
cat workdir/sandbox_*/greeting.txt

# Should output: Hello, World!
```