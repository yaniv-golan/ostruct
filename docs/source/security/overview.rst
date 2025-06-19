Security Overview
=================

Security is a fundamental aspect of ostruct's design. This guide covers API key management, file access control, data handling policies, and security best practices for production deployments.

.. warning::
   **Data Privacy**: All content sent to ostruct may be transmitted to external AI services:

   - **Template files** (``--file alias path``): Content is included in prompts sent to OpenAI
   - **Code Interpreter files** (``--file ci:alias path``): Files are uploaded to OpenAI for execution
   - **File Search files** (``--file fs:alias path``): Files are uploaded to OpenAI for vector search

   Review your data sensitivity before processing confidential information with any tool routing option.

.. note::
   For quick security configuration, see the :doc:`../user-guide/cli_reference` section on Path Security.

Security Architecture
=====================

ostruct implements a multi-layered security model:

1. **API Key Management** - Secure handling of OpenAI credentials
2. **File Access Control** - Path validation and directory restrictions
3. **Data Upload Controls** - Tool-specific file routing with explicit user control
4. **MCP Security** - Validation and approval for external server connections
5. **Runtime Security** - Symlink resolution and path traversal prevention

API Key Management
==================

Secure Credential Handling
---------------------------

ostruct never logs or stores API keys. Credentials are handled through:

**Environment Variables (Recommended):**

.. code-block:: bash

   export OPENAI_API_KEY="your-api-key-here"
   ostruct run template.j2 schema.json

**.env Files (Convenient for Development):**

.. code-block:: bash

   # Create .env file in your project directory
   echo 'OPENAI_API_KEY=your-api-key-here' > .env
   ostruct run template.j2 schema.json

.. note::
   ostruct automatically loads ``.env`` files from the current directory. Environment variables take precedence over ``.env`` file values.

**Command Line (Development Only):**

.. code-block:: bash

   ostruct run template.j2 schema.json --api-key "your-api-key"

.. warning::
   **CLI API Keys**: Avoid using ``--api-key`` in production as it may be visible in process lists or shell history.

**Configuration Files:**

.. code-block:: yaml

   # ostruct.yaml
   api:
     key: "${OPENAI_API_KEY}"  # Environment variable substitution

Best Practices
--------------

✅ **Do:**
- Use environment variables for API keys
- Rotate API keys regularly
- Use dedicated API keys for different environments
- Set usage limits in OpenAI dashboard
- Monitor API usage and costs

❌ **Don't:**
- Commit API keys to version control
- Share API keys in plain text
- Use production keys in development
- Log or print API keys in applications

Environment-Specific Keys
-------------------------

.. code-block:: bash

   # Development
   export OPENAI_API_KEY="sk-dev-..."

   # Staging
   export OPENAI_API_KEY="sk-staging-..."

   # Production
   export OPENAI_API_KEY="sk-prod-..."

File Access Control
===================

SecurityManager Architecture
-----------------------------

All file operations in ostruct go through a centralized SecurityManager located at ``src/ostruct/cli/security/security_manager.py``. This provides:

- **Path Normalization**: Resolves relative paths and symlinks safely
- **Directory Validation**: Ensures files are within allowed directories
- **Symlink Protection**: Prevents directory traversal attacks
- **Case-Sensitive Handling**: Platform-appropriate path handling

Allowed Directories
-------------------

By default, ostruct restricts file access to the current working directory. Expand access with:

**Single Directory:**

.. code-block:: bash

   ostruct run template.j2 schema.json --allow /data --file config /data/config.yaml

**Multiple Directories:**

.. code-block:: bash

   ostruct run template.j2 schema.json \
     --allow /data \
     --allow /configs \
     --allow /tmp/workspace \
     --file config /data/input.csv

**From File:**

.. code-block:: bash

   # allowed_dirs.txt
   /data
   /configs
   /tmp/workspace

   ostruct run template.j2 schema.json --allowed-dir-file allowed_dirs.txt

Base Directory Control
----------------------

Set a base directory to restrict all relative path operations:

.. code-block:: bash

   # All relative paths resolve within /project
   ostruct run template.j2 schema.json \
     --path-security strict --allow /project \
     --file config config.yaml \
     --file config data/input.csv

Security Validation Process
---------------------------

For every file access, ostruct:

1. **Normalizes** the path (resolves ``.``, ``..``, symlinks)
2. **Validates** the path is within allowed directories
3. **Checks** file existence and permissions
4. **Resolves** symlinks with depth and loop protection
5. **Provides** the validated absolute path to the application

Path Traversal Prevention
-------------------------

ostruct prevents common path traversal attacks:

.. code-block:: bash

   # These are blocked by SecurityManager
   ostruct run template.j2 schema.json --file config "../../../etc/passwd"
   ostruct run template.j2 schema.json --file config "config/../../../sensitive.txt"

   # Use allowed directories for legitimate access outside project
   ostruct run template.j2 schema.json --allow /etc --file config /etc/config.yaml

Data Upload and Tool Security
=============================

File Search Data Handling
--------------------------

.. important::
   **Future-Proof Policy**: Files may be uploaded to external services, depending on the backend provider. The current implementation uploads files to OpenAI's File Search service for vector processing.

**What happens to your files:**
- Files are uploaded to vector stores for semantic search
- Content is processed and indexed for retrieval
- Files are accessible during the session for search operations
- Cleanup removes files and vector stores after completion (when enabled)

**Security considerations:**
- Review data sensitivity before uploading documents
- Consider redacting sensitive information from documents
- Use cleanup options to remove data after processing
- Monitor your OpenAI usage dashboard for uploaded files

Code Interpreter Data Handling
-------------------------------

.. important::
   **Data Upload**: Files are uploaded to OpenAI's Code Interpreter environment for Python execution and analysis.

**What happens to your files:**
- Files are uploaded to an isolated execution environment
- Code can read, process, and analyze the files
- Generated outputs (charts, results) can be downloaded
- Cleanup removes uploaded files after execution (when enabled)

**Security considerations:**
- Avoid uploading confidential datasets
- Review generated outputs before sharing
- Use cleanup options to manage storage quotas
- Consider data anonymization for sensitive datasets

Web Search Data Handling
-------------------------

.. important::
   **Search Query Privacy**: When using ``--enable-tool web-search``, search queries may be sent to external search services via OpenAI. These queries can be derived from your prompts and template content.

**What happens during web search:**
- Search queries are generated based on your prompt and template content
- Queries are sent to external search services through OpenAI's web search tool
- Search results are retrieved and processed by the model
- No files are uploaded, but prompt content may influence search queries

**API Key and Authentication:**
- Web search uses your existing ``OPENAI_API_KEY`` - no separate authentication required
- The same API key that powers other ostruct features also handles web search requests
- No additional API keys or service subscriptions needed beyond your OpenAI account

**Rate Limits and Quotas:**
- Web search requests count toward your standard OpenAI API rate limits (RPM/TPM)
- No separate rate limits are imposed specifically on the web search tool
- Existing ostruct retry logic and error handling applies to web search operations
- Monitor your OpenAI dashboard for usage tracking across all features including web search

**Security considerations:**
- **Avoid sensitive information in prompts** when using web search
- Review template content for potentially sensitive keywords or data
- Consider using ``--no-web-search`` for sensitive prompts
- Be aware that search queries may be logged by search providers
- Web search is automatically disabled for Azure OpenAI endpoints

**Best practices:**
- Use generic terms rather than specific internal project names
- Avoid including personal information, credentials, or proprietary data in prompts
- Test with public information first to understand search behavior
- Consider the query implications of your template variables

**Opt-in requirement:**
Web search is always opt-in and requires explicit use of the ``--enable-tool web-search`` flag. This ensures users are aware when external search services may be accessed.

Template File Security
----------------------

Template files (``--file alias path``) are processed differently than Code Interpreter and File Search files:

- Files remain on your local system (not uploaded as file objects)
- Content is read locally and included in template rendering
- **Template content is sent to OpenAI servers as part of the prompt text**
- Consider data sensitivity when including file content in templates

Tool Routing Security Matrix
-----------------------------

.. list-table:: File Routing Security Implications
   :header-rows: 1
   :widths: 20 30 50

   * - Flag
     - Security Level
     - Data Handling
   * - ``--file`` (Template)
     - Medium Security
     - Content sent in prompt to OpenAI
   * - ``--file ci:`` (Code Interpreter)
     - Medium Security
     - Uploaded to OpenAI for execution
   * - ``--file fs:`` (File Search)
     - Medium Security
     - Uploaded to OpenAI for vector search

Cleanup and Data Retention
---------------------------

Enable cleanup to minimize data retention:

.. code-block:: bash

   # Enable cleanup (default: true)
   ostruct run template.j2 schema.json \
     --file ci:data data.csv \
     --code-interpreter-cleanup

   ostruct run template.j2 schema.json \
     --file fs:docs docs.pdf \
     --file-search-cleanup

MCP Server Security
===================

Model Context Protocol (MCP) servers extend ostruct with external capabilities, requiring additional security considerations.

Server Validation
-----------------

ostruct validates MCP connections:

- **URL Validation**: Ensures proper HTTPS URLs for remote servers
- **Certificate Validation**: Verifies SSL certificates for secure connections
- **Timeout Controls**: Prevents hanging connections
- **Error Handling**: Graceful failure for unreachable servers

**Example secure connection:**

.. code-block:: bash

   ostruct run template.j2 schema.json \
     --mcp-server "deepwiki@https://mcp.deepwiki.com/sse" \
     --mcp-headers '{"Authorization": "Bearer your-token"}'

Tool Restrictions
-----------------

Restrict which tools MCP servers can use:

.. code-block:: bash

   # Allow only specific tools
   ostruct run template.j2 schema.json \
     --mcp-server "research@https://mcp.example.com" \
     --mcp-allowed-tools "research:search,summarize"

Approval Controls
-----------------

.. code-block:: bash

   # Require approval for tool usage (CLI requires 'never')
   ostruct run template.j2 schema.json \
     --mcp-server "external@https://mcp.example.com" \
     --mcp-require-approval never

Authentication
--------------

Secure MCP server authentication:

.. code-block:: bash

   # Bearer token authentication
   ostruct run template.j2 schema.json \
     --mcp-server "secure@https://mcp.example.com" \
     --mcp-headers '{"Authorization": "Bearer token123"}'

   # API key authentication
   ostruct run template.j2 schema.json \
     --mcp-server "api@https://mcp.example.com" \
     --mcp-headers '{"X-API-Key": "key123"}'

Third-Party Security Review
---------------------------

Before connecting to MCP servers:

1. **Review server documentation** for data handling policies
2. **Verify HTTPS and certificate validity**
3. **Understand what data may be sent** to the server
4. **Check authentication requirements**
5. **Test with non-sensitive data** first

Threat Model and Risk Assessment
================================

Data Classification
-------------------

Classify your data before processing:

**Public Data** ✅
- Public documentation
- Open source code
- Marketing materials
- Published research

**Internal Data** ⚠️
- Configuration files (review for secrets before including in templates)
- Development code (review for credentials before including in templates)
- Business documents (assess sensitivity before including in prompts)
- Log files (may contain sensitive information - review before processing)

**Confidential Data** ❌
- Customer PII
- Financial records
- Authentication credentials
- Trade secrets

**Restricted Data** 🚫
- Government classified information
- Healthcare PHI/PII
- Payment card data
- Legal privileged information

Common Threats and Mitigations
------------------------------

**Path Traversal Attacks**
- *Threat*: Malicious paths accessing unauthorized files
- *Mitigation*: SecurityManager validation, allowed directories

**Credential Exposure**
- *Threat*: API keys in logs, processes, or version control
- *Mitigation*: Environment variables, secure handling

**Data Exfiltration**
- *Threat*: Sensitive data uploaded to external services
- *Mitigation*: Tool routing control, data classification

**Injection Attacks**
- *Threat*: Malicious content in templates or file names
- *Mitigation*: Template validation, path sanitization

**MCP Server Compromise**
- *Threat*: Malicious or compromised external servers
- *Mitigation*: HTTPS validation, tool restrictions, approval controls

Production Security Checklist
==============================

Pre-Deployment Security Review
-------------------------------

.. code-block:: text

   □ API keys stored in environment variables
   □ No hardcoded credentials in templates or configs
   □ Allowed directories properly configured
   □ Base directory set for path restriction
   □ File routing reviewed for data sensitivity
   □ Cleanup enabled for uploaded files
   □ MCP servers reviewed and validated
   □ Data classification completed
   □ Security policies documented

Runtime Security Monitoring
----------------------------

.. code-block:: text

   □ API usage monitoring enabled
   □ File access logging reviewed
   □ Upload cleanup verified
   □ Error handling for security failures
   □ Regular security assessment scheduled

Incident Response
-----------------

If security issues occur:

1. **Immediate Actions:**
   - Rotate compromised API keys
   - Remove uploaded sensitive data
   - Disconnect compromised MCP servers
   - Review logs for unauthorized access

2. **Investigation:**
   - Identify scope of data exposure
   - Review file access logs
   - Check API usage patterns
   - Assess impact on downstream systems

3. **Recovery:**
   - Implement additional controls
   - Update security documentation
   - Train team on new procedures
   - Monitor for recurring issues

Security Configuration Examples
===============================

Development Environment
-----------------------

.. code-block:: bash

   # Development: Relaxed but secure
   export OPENAI_API_KEY="sk-dev-..."

   ostruct run template.j2 schema.json \
     --path-security strict --allow ./project \
     --allow ./test_data \
     --file config config.yaml \
     --file ci:data test_data.csv \
     --code-interpreter-cleanup \
     --file-search-cleanup

Staging Environment
-------------------

.. code-block:: bash

   # Staging: Production-like security
   export OPENAI_API_KEY="sk-staging-..."

   ostruct run template.j2 schema.json \
     --path-security strict --allow /app \
     --allow /app/data \
     --allow /app/configs \
     --allowed-dir-file /app/allowed_dirs.txt \
     --file config configs/app.yaml \
     --code-interpreter-cleanup \
     --file-search-cleanup \
     --verbose

Production Environment
----------------------

.. code-block:: bash

   # Production: Maximum security
   export OPENAI_API_KEY="sk-prod-..."

   ostruct run template.j2 schema.json \
     --path-security strict --allow /prod/app \
     --allowed-dir-file /prod/security/allowed_dirs.txt \
     --file config configs/production.yaml \
     --code-interpreter-cleanup \
     --file-search-cleanup \
     --timeout 300

CI/CD Pipeline Security
-----------------------

.. code-block:: yaml

   # .github/workflows/secure-analysis.yml
   steps:
     - name: Secure Analysis
       env:
         OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
       run: |
         ostruct run analysis.j2 schema.json \
           --path-security strict --allow ${{ github.workspace }} \
           --allow ${{ github.workspace }}/data \
           --file config config.yaml \
           --file ci:data data/metrics.csv \
           --code-interpreter-cleanup \
           --file-search-cleanup \
           --output-file results.json

Security Resources
==================

Documentation
-------------

- :doc:`../user-guide/cli_reference` - Complete CLI security options
- :doc:`../user-guide/quickstart` - Security-aware examples
- :doc:`../automate/ci_cd` - Secure CI/CD integration

Code References
---------------

- ``src/ostruct/cli/security/security_manager.py`` - Main security validation
- ``src/ostruct/cli/security/allowed_checker.py`` - Directory validation
- ``src/ostruct/cli/security/symlink_resolver.py`` - Symlink safety
- ``src/ostruct/cli/security/normalization.py`` - Path normalization

External Resources
------------------

- OpenAI API Documentation (available on the OpenAI Platform)
- `OWASP Path Traversal Prevention <https://owasp.org/www-community/attacks/Path_Traversal>`_
- `Secure API Key Management <https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html>`_

Getting Security Help
=====================

If you discover security issues:

1. **For ostruct vulnerabilities**: Report to the project maintainers
2. **For OpenAI API issues**: Contact OpenAI support
3. **For MCP server issues**: Contact the server provider
4. **For general security questions**: Consult your security team

Remember: Security is a shared responsibility between ostruct, service providers, and your implementation.
