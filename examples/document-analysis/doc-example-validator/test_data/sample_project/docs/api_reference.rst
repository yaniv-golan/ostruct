================
API Reference
================

AwesomeCLI Python API
====================

The AwesomeCLI tool provides a Python API for programmatic access to all functionality.

Installation
------------

Install the Python package::

    pip install awesome-cli[api]

Quick Start
-----------

Basic usage example::

    from awesome_cli import AwesomeAPI

    # Initialize the API client
    api = AwesomeAPI()

    # Process a single file
    result = api.process_file("input.txt")
    print(result.status)

Authentication
--------------

API Key Setup
~~~~~~~~~~~~~

Set your API key::

    export AWESOME_API_KEY="your-key-here"

Or pass it directly::

    api = AwesomeAPI(api_key="your-key-here")

Core Classes
============

AwesomeAPI
----------

Main API client class.

.. code-block:: python

    class AwesomeAPI:
        def __init__(self, api_key=None, base_url=None):
            """Initialize API client.

            Args:
                api_key (str): Your API key
                base_url (str): Custom API endpoint
            """
            pass

        def process_file(self, filepath, options=None):
            """Process a single file.

            Args:
                filepath (str): Path to input file
                options (dict): Processing options

            Returns:
                ProcessResult: Processing results
            """
            pass

ProcessResult
-------------

Result object returned by processing operations.

.. code-block:: python

    class ProcessResult:
        @property
        def status(self):
            """Get processing status."""
            return self._status

        @property
        def data(self):
            """Get processed data."""
            return self._data

        def save(self, filepath):
            """Save results to file."""
            pass

Methods
=======

File Processing
---------------

Process individual files::

    # Basic processing
    result = api.process_file("data.csv")

    # With options
    result = api.process_file("data.csv", {
        'format': 'json',
        'validate': True,
        'output_dir': '/tmp/output'
    })

Batch Processing
----------------

Process multiple files::

    # Process directory
    results = api.process_directory("./input/")

    # Process file list
    files = ["file1.txt", "file2.txt", "file3.txt"]
    results = api.process_batch(files)

    # Check results
    for result in results:
        if result.status == 'success':
            print(f"Processed: {result.filename}")
        else:
            print(f"Failed: {result.filename} - {result.error}")

Configuration
=============

Global Settings
---------------

Configure global API settings::

    from awesome_cli.config import configure

    configure({
        'timeout': 30,
        'retry_count': 3,
        'debug': True
    })

Per-Request Options
-------------------

Override settings per request::

    result = api.process_file("data.txt", {
        'timeout': 60,
        'format': 'xml',
        'compression': 'gzip'
    })

Error Handling
==============

Exception Types
---------------

The API raises specific exceptions:

.. code-block:: python

    from awesome_cli.exceptions import (
        APIError,
        AuthenticationError,
        ValidationError,
        ProcessingError
    )

    try:
        result = api.process_file("invalid.txt")
    except AuthenticationError:
        print("Check your API key")
    except ValidationError as e:
        print(f"Invalid input: {e}")
    except ProcessingError as e:
        print(f"Processing failed: {e}")
    except APIError as e:
        print(f"API error: {e}")

Retry Logic
-----------

Built-in retry for transient errors::

    # Configure retry behavior
    api = AwesomeAPI(retry_config={
        'max_retries': 5,
        'backoff_factor': 2,
        'retry_statuses': [502, 503, 504]
    })

Examples
========

Data Validation
---------------

Validate CSV files::

    result = api.validate_csv("data.csv", schema={
        'columns': ['name', 'email', 'age'],
        'required': ['name', 'email'],
        'types': {
            'age': 'integer',
            'email': 'email'
        }
    })

    if result.is_valid:
        print("CSV is valid")
    else:
        for error in result.errors:
            print(f"Line {error.line}: {error.message}")

Batch Conversion
----------------

Convert multiple files::

    # Convert all JSON files to CSV
    import os

    json_files = [f for f in os.listdir('.') if f.endswith('.json')]

    for json_file in json_files:
        result = api.convert_file(json_file, 'csv')
        if result.success:
            print(f"Converted {json_file} → {result.output_file}")

Async Processing
----------------

For large files, use async processing::

    # Start async job
    job = api.process_async("large_file.csv")

    # Check status
    while not job.is_complete():
        print(f"Progress: {job.progress}%")
        time.sleep(1)

    # Get results
    if job.success:
        result = job.get_result()
        result.save("output.json")

Integration Examples
===================

Flask Integration
-----------------

Use with Flask web applications::

    from flask import Flask, request, jsonify
    from awesome_cli import AwesomeAPI

    app = Flask(__name__)
    api = AwesomeAPI()

    @app.route('/process', methods=['POST'])
    def process_upload():
        file = request.files['file']
        result = api.process_file(file)

        return jsonify({
            'status': result.status,
            'data': result.data
        })

Django Integration
------------------

Use with Django::

    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt
    from awesome_cli import AwesomeAPI

    @csrf_exempt
    def process_file_view(request):
        if request.method == 'POST':
            api = AwesomeAPI()
            file_content = request.FILES['file'].read()

            result = api.process_content(file_content)

            return JsonResponse({
                'success': result.status == 'success',
                'data': result.data
            })

Troubleshooting
===============

Common Issues
-------------

**ImportError: No module named 'awesome_cli'**

Install the package::

    pip install awesome-cli

**AuthenticationError: Invalid API key**

Check your API key::

    echo $AWESOME_API_KEY

**TimeoutError: Request timed out**

Increase timeout::

    api = AwesomeAPI(timeout=120)

Debug Mode
----------

Enable debug logging::

    import logging
    logging.basicConfig(level=logging.DEBUG)

    api = AwesomeAPI(debug=True)

Performance Tips
================

* Use batch processing for multiple files
* Enable compression for large files
* Set appropriate timeouts
* Use async processing for long-running tasks
* Cache API instances when possible

Version Information
===================

Check API version::

    from awesome_cli import __version__
    print(f"AwesomeCLI API version: {__version__}")

API Compatibility
-----------------

* v1.0+: All features supported
* v0.9+: Limited async support
* v0.8+: Basic functionality only

For more information, visit: https://awesome-cli.readthedocs.io/
