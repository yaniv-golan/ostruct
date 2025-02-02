# Testing Guide

This directory contains tests for the ostruct project. Below are important notes about testing specific components.

## Testing with Tiktoken

### Background

Tiktoken has a unique way of handling its encoding data files that requires special consideration in tests:

1. **File Storage**:
   - Tiktoken doesn't bundle encoding files with the package
   - Instead, it downloads them on first use and caches them locally
   - Cache location is determined by (in order):
     1. `TIKTOKEN_CACHE_DIR` environment variable
     2. `DATA_GYM_CACHE_DIR` environment variable
     3. Fallback: `<temp_dir>/data-gym-cache`

2. **First Use**:
   - On first use, tiktoken needs to:
     1. Download the encoding file from OpenAI's servers
     2. Cache it locally using a SHA-1 hash of the URL as filename
     3. Load the file into memory

### Testing with pyfakefs

Since we use pyfakefs for file system isolation in tests, special handling is needed for tiktoken:

1. **Required Access**:
   - Tiktoken package directory (for the library code)
   - Cache directory (for storing downloaded files)
   - Temp directory (for initial downloads)
   - Network access during initialization

2. **Solution**:
   We provide a `setup_tiktoken()` helper method that:
   - Adds necessary real directories to pyfakefs
   - Creates cache directory if needed
   - Temporarily enables network access
   - Initializes tiktoken with a base encoding

### Usage in Tests

1. **Basic Usage**:

   ```python
   def test_my_function(self, fs):
       self.setup_tiktoken(fs)
       # Your test code here
   ```

2. **Common Issues**:
   - "Unknown encoding": Make sure `setup_tiktoken()` is called before using tiktoken
   - "File exists": Ignore FileExistsError when adding directories
   - Network errors: Ensure network access during initialization

3. **Example Implementation**:
   See `test_tokens.py` for a complete implementation of the `setup_tiktoken()` method.

### Environment Variables

You can customize tiktoken's behavior in tests:

```bash
# Set custom cache directory
export TIKTOKEN_CACHE_DIR=/path/to/cache

# Or use DATA_GYM_CACHE_DIR
export DATA_GYM_CACHE_DIR=/path/to/cache
```

### References

- [Tiktoken Documentation](https://github.com/openai/tiktoken)
- [pyfakefs Documentation](https://pytest-pyfakefs.readthedocs.io/)

## Testing with MockSecurityManager

The project uses a custom `MockSecurityManager` for secure file operations in tests. This section explains how to use it correctly.

### Overview

`MockSecurityManager` provides:

- A secure testing environment for file operations
- Integration with pyfakefs
- Consistent path validation and resolution
- Pre-configured allowed directories

### Directory Structure

The test environment has the following structure:

```
/test_workspace/  # Base directory for tests
/test/           # Additional test directory
/test1/          # Additional test directory
/test2/          # Additional test directory
/tmp/            # Mock temp directory
/workspace/      # Additional workspace directory
```

### Best Practices

1. **Use the Fixture**

   ```python
   def test_something(fs, security_manager):
       # Always use the security_manager fixture
       # Don't create MockSecurityManager instances directly
   ```

2. **File Creation**

   ```python
   # Do this:
   fs.create_file("/test_workspace/file.txt")  # Absolute path in test_workspace
   fs.create_file("file.txt")                  # Relative path (resolves to test_workspace)
   fs.create_file("/tmp/temp.txt")             # Temp directory

   # Don't do this:
   fs.create_file("/random/path/file.txt")     # Will fail validation
   ```

3. **File Operations**

   ```python
   # Always pass security_manager to file operations
   file_info = read_file("test.txt", security_manager=security_manager)
   files = collect_files("*.txt", security_manager=security_manager)
   ```

4. **Path Resolution**
   - Relative paths resolve against `/test_workspace`
   - Absolute paths must be in allowed directories
   - Temp paths (`/tmp/*`) are handled specially

### Common Issues

1. **PathSecurityError**
   - Cause: Trying to access files outside allowed directories
   - Solution: Use paths within `/test_workspace` or other allowed directories

2. **FileExistsError in Setup**
   - Cause: Directory already exists in fake filesystem
   - Solution: Check existence before creation or use `exist_ok=True`

3. **Missing Security Manager**
   - Cause: Not passing security_manager to file operations
   - Solution: Always include security_manager parameter

### Testing Different Scenarios

1. **Base Directory Files**

   ```python
   def test_base_dir_file(fs, security_manager):
       fs.create_file("/test_workspace/test.txt")
       file_info = read_file("test.txt", security_manager=security_manager)
   ```

2. **Temp Files**

   ```python
   def test_temp_file(fs, security_manager):
       fs.create_file("/tmp/temp.txt")
       file_info = read_file("/tmp/temp.txt", security_manager=security_manager)
   ```

3. **Multiple Files**

   ```python
   def test_multiple_files(fs, security_manager):
       fs.create_file("/test_workspace/file1.txt")
       fs.create_file("/test_workspace/file2.txt")
       files = collect_files("*.txt", security_manager=security_manager)
   ```

### Migration Guide

If you have existing tests using real file operations:

1. Add the fixtures:

   ```python
   def test_something(fs, security_manager):
   ```

2. Replace real paths with test paths:

   ```python
   # Before:
   with tempfile.NamedTemporaryFile() as f:
       f.write(b"content")
       
   # After:
   test_file = "/test_workspace/test.txt"
   fs.create_file(test_file, contents="content")
   ```

3. Add security_manager to file operations:

   ```python
   # Before:
   file_info = read_file("test.txt")
   
   # After:
   file_info = read_file("test.txt", security_manager=security_manager)
   ```

## Other Testing Topics
