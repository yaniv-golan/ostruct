# Text Processing Example

This example demonstrates the agent's text processing capabilities using grep, sed, and awk.

## Task

Create a CSV file with sample data and perform various text processing operations on it.

## Usage

```bash
cd examples/agent
./runner.sh "Create a CSV file with names and ages, then find all people over 25 and calculate the average age"
```

## Expected Outcome

1. The agent will use `write_file` to create a CSV with sample data
2. It will use `grep` or `awk` to filter people over 25
3. It will use `awk` to calculate the average age
4. The final answer should show the filtered results and average

## Sample Data

The agent might create something like:

```
Name,Age
Alice,30
Bob,25
Charlie,35
Diana,22
Eve,28
```

## Alternative Tasks

```bash
# Text replacement example
./runner.sh "Create a text file with multiple lines, then replace all occurrences of 'old' with 'new'"

# Pattern extraction example
./runner.sh "Create a log file with timestamps and extract all error messages"

# Word counting example
./runner.sh "Create a text file and count the frequency of each word"
```

## Tools Used

- `write_file` - For creating the initial data file
- `grep` - For pattern matching and filtering
- `sed` - For text extraction and transformation
- `awk` - For field processing and calculations
- `text_replace` - For search and replace operations

## Files Created

- `workdir/sandbox_*/data.csv` - The sample CSV file
- `workdir/sandbox_*/filtered_data.txt` - Filtered results
- `workdir/sandbox_*/analysis.txt` - Analysis results

## Verification

```bash
# Check created files
ls -la workdir/sandbox_*/

# View file contents
cat workdir/sandbox_*/data.csv
cat workdir/sandbox_*/filtered_data.txt
cat workdir/sandbox_*/analysis.txt
```

## Notes

- All text processing operations are performed within the sandbox
- File size is limited to 32KB for security
- Complex operations will be broken down into multiple steps automatically
