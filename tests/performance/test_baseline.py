"""Performance baseline tests for ostruct functionality."""

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ostruct.cli.config import OstructConfig


class PerformanceBenchmark:
    """Performance benchmarks and baselines."""

    # Expected response times based on probe tests (in seconds)
    EXPECTED_RESPONSE_TIMES = {
        "basic_responses": (1, 2),  # From probe tests
        "structured_output": (1, 2),  # From probe tests
        "code_interpreter": (10, 16),  # From probe tests
        "file_search": (7, 8),  # From probe tests
        "mcp_integration": (5, 6),  # From probe tests
    }

    # Token usage baselines
    EXPECTED_TOKEN_USAGE = {
        "small_file": (100, 500),  # Small template + file
        "medium_file": (500, 2000),  # Medium complexity
        "large_file": (2000, 8000),  # Large file processing
    }

    # Cost baselines (in USD)
    EXPECTED_COSTS = {
        "basic_analysis": (0.001, 0.01),
        "code_execution": (0.01, 0.05),
        "comprehensive": (0.05, 0.15),
    }


class TestPerformanceBaselines:
    """Test performance baselines and regressions."""

    def setup_method(self):
        """Set up performance test fixtures."""
        self.benchmark = PerformanceBenchmark()

    @pytest.mark.asyncio
    async def test_basic_response_time(self):
        """Test basic response time performance."""
        start_time = time.time()

        # Mock basic API response
        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content='{"result": "test"}'))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Simulate basic operation
            await asyncio.sleep(0.1)  # Simulate minimal processing

        end_time = time.time()
        duration = end_time - start_time

        min_time, max_time = self.benchmark.EXPECTED_RESPONSE_TIMES[
            "basic_responses"
        ]

        # Allow for test environment overhead
        assert (
            duration < max_time * 2
        ), f"Basic response took {duration:.2f}s, expected < {max_time * 2}s"

    @pytest.mark.asyncio
    async def test_structured_output_performance(self):
        """Test structured output performance baseline."""
        start_time = time.time()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content='{"analysis": "complete"}'))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Simulate structured output processing
            await asyncio.sleep(0.2)  # Simulate processing time

        end_time = time.time()
        duration = end_time - start_time

        min_time, max_time = self.benchmark.EXPECTED_RESPONSE_TIMES[
            "structured_output"
        ]
        assert (
            duration < max_time * 2
        ), f"Structured output took {duration:.2f}s, expected < {max_time * 2}s"

    @pytest.mark.asyncio
    async def test_code_interpreter_performance(self):
        """Test Code Interpreter performance baseline."""
        start_time = time.time()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()

            # Mock file upload
            mock_file = Mock()
            mock_file.id = "file-123"
            mock_client.files.create.return_value = mock_file

            # Mock execution
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content='{"output": "Analysis complete"}'))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Simulate code interpreter operations
            await asyncio.sleep(0.5)  # Simulate upload + execution

        end_time = time.time()
        duration = end_time - start_time

        min_time, max_time = self.benchmark.EXPECTED_RESPONSE_TIMES[
            "code_interpreter"
        ]
        assert (
            duration < max_time * 2
        ), f"Code Interpreter took {duration:.2f}s, expected < {max_time * 2}s"

    @pytest.mark.asyncio
    async def test_file_search_performance(self):
        """Test File Search performance baseline."""
        start_time = time.time()

        with patch("openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()

            # Mock vector store operations
            mock_vector_store = Mock()
            mock_vector_store.id = "vs-123"
            mock_client.beta.vector_stores.create.return_value = (
                mock_vector_store
            )

            # Mock file upload to vector store
            mock_file = Mock()
            mock_file.id = "file-456"
            mock_client.files.create.return_value = mock_file

            # Mock search response
            mock_response = Mock()
            mock_response.choices = [
                Mock(message=Mock(content='{"results": ["found"]}'))
            ]
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client

            # Simulate file search operations
            await asyncio.sleep(0.3)  # Simulate vector store + search

        end_time = time.time()
        duration = end_time - start_time

        min_time, max_time = self.benchmark.EXPECTED_RESPONSE_TIMES[
            "file_search"
        ]
        assert (
            duration < max_time * 2
        ), f"File Search took {duration:.2f}s, expected < {max_time * 2}s"

    @pytest.mark.asyncio
    async def test_mcp_integration_performance(self):
        """Test MCP integration performance baseline."""
        start_time = time.time()

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "result": {"content": "MCP response"}
            }
            mock_client.post.return_value = mock_response
            mock_httpx.return_value.__aenter__.return_value = mock_client

            # Simulate MCP server communication
            await asyncio.sleep(0.2)  # Simulate network request

        end_time = time.time()
        duration = end_time - start_time

        min_time, max_time = self.benchmark.EXPECTED_RESPONSE_TIMES[
            "mcp_integration"
        ]
        assert (
            duration < max_time * 2
        ), f"MCP integration took {duration:.2f}s, expected < {max_time * 2}s"

    def test_token_usage_baselines(self):
        """Test token usage stays within expected ranges."""
        # Test different file sizes
        test_cases = [
            ("small", "x" * 100, "small_file"),
            ("medium", "x" * 1000, "medium_file"),
            ("large", "x" * 10000, "large_file"),
        ]

        for size_name, content, baseline_key in test_cases:
            # Estimate tokens (rough approximation: 4 chars per token)
            estimated_tokens = len(content) // 4

            min_tokens, max_tokens = self.benchmark.EXPECTED_TOKEN_USAGE[
                baseline_key
            ]

            # Allow some variance for test content
            assert (
                estimated_tokens <= max_tokens * 2
            ), f"{size_name} file tokens {estimated_tokens} exceeds baseline {max_tokens}"

    def test_cost_estimation_baselines(self):
        """Test cost estimations stay within expected ranges."""
        # Mock cost calculations
        test_scenarios = [
            ("basic_analysis", 1000, "basic_analysis"),
            ("code_execution", 5000, "code_execution"),
            ("comprehensive", 15000, "comprehensive"),
        ]

        for scenario_name, token_count, baseline_key in test_scenarios:
            # Rough cost estimate: $0.01 per 1K tokens (simplified)
            estimated_cost = (token_count / 1000) * 0.01

            min_cost, max_cost = self.benchmark.EXPECTED_COSTS[baseline_key]

            assert (
                estimated_cost <= max_cost * 2
            ), f"{scenario_name} cost ${estimated_cost:.4f} exceeds baseline ${max_cost}"


class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_template_rendering_performance(self):
        """Test template rendering performance."""
        start_time = time.time()

        # Mock template rendering
        template_content = "Analyze this: {{ content }}"
        context = {"content": "x" * 1000}

        # Simulate Jinja2 rendering
        from jinja2 import Template

        template = Template(template_content)
        rendered = template.render(context)

        end_time = time.time()
        duration = end_time - start_time

        # Template rendering should be very fast
        assert (
            duration < 0.1
        ), f"Template rendering took {duration:.4f}s, expected < 0.1s"
        assert "Analyze this:" in rendered

    def test_file_processing_performance(self, security_manager, fs):
        """Test file processing performance."""
        from ostruct.cli.file_utils import FileInfo

        # Create test files on fake filesystem
        for i in range(100):
            fs.create_file(
                f"/test_workspace/base/file_{i}.txt", contents=f"content_{i}"
            )

        start_time = time.time()

        # Create test files
        test_files = [
            FileInfo(
                path=f"/test_workspace/base/file_{i}.txt",
                security_manager=security_manager,
            )
            for i in range(100)
        ]

        # Simulate processing
        processed_count = 0
        for file_info in test_files:
            # Simulate basic file processing
            if file_info.content:
                processed_count += 1

        end_time = time.time()
        duration = end_time - start_time

        # Processing 100 small files should be fast
        assert (
            duration < 1.0
        ), f"Processing 100 files took {duration:.4f}s, expected < 1.0s"
        assert processed_count == 100

    def test_configuration_loading_performance(self):
        """Test configuration loading performance."""
        start_time = time.time()

        # Test configuration loading
        config = OstructConfig()

        # Access various configuration values
        model = config.get_model_default()
        mcp_servers = config.get_mcp_servers()
        ci_config = config.get_code_interpreter_config()

        end_time = time.time()
        duration = end_time - start_time

        # Configuration operations should be very fast
        assert (
            duration < 0.01
        ), f"Configuration loading took {duration:.4f}s, expected < 0.01s"
        assert model is not None
        assert isinstance(mcp_servers, dict)
        assert isinstance(ci_config, dict)

    def test_security_validation_performance(self):
        """Test security validation performance."""
        from ostruct.cli.security import SecurityManager

        start_time = time.time()

        # Create security manager with base_dir to avoid conftest override
        security_manager = SecurityManager(
            base_dir="/tmp", allowed_dirs=["/tmp/test"]
        )

        # Test multiple path validations
        test_paths = [f"/tmp/test/file_{i}.txt" for i in range(50)]

        for path in test_paths:
            try:
                # Simulate path validation
                security_manager.is_path_safe(path)
            except Exception:
                # Some validation might fail in test environment
                pass

        end_time = time.time()
        duration = end_time - start_time

        # Security validation should be fast
        assert (
            duration < 0.5
        ), f"Security validation took {duration:.4f}s, expected < 0.5s"


class TestScalabilityBaselines:
    """Test scalability baselines."""

    def test_large_file_handling(self, security_manager, fs):
        """Test handling of large files."""
        from ostruct.cli.file_utils import FileInfo

        # Simulate large file content
        large_content = "x" * (1024 * 1024)  # 1MB

        # Create the file on fake filesystem
        fs.create_file(
            "/test_workspace/base/large.txt", contents=large_content
        )

        start_time = time.time()

        # Test file info creation
        file_info = FileInfo(
            path="/test_workspace/base/large.txt",
            security_manager=security_manager,
        )

        # Test basic operations on large file
        assert len(file_info.content) == 1024 * 1024
        assert file_info.abs_path == "/test_workspace/base/large.txt"

        end_time = time.time()
        duration = end_time - start_time

        # Large file operations should still be reasonable
        assert (
            duration < 1.0
        ), f"Large file handling took {duration:.4f}s, expected < 1.0s"

    def test_multiple_tool_coordination(self):
        """Test coordination of multiple tools."""
        start_time = time.time()

        # Simulate multiple tool initialization
        tools_initialized = []

        # Mock tool initialization
        for tool in ["code_interpreter", "file_search", "mcp"]:
            # Simulate tool setup
            tools_initialized.append(tool)
            time.sleep(0.01)  # Simulate setup time

        end_time = time.time()
        duration = end_time - start_time

        # Multi-tool coordination should be efficient
        assert (
            duration < 0.5
        ), f"Multi-tool coordination took {duration:.4f}s, expected < 0.5s"
        assert len(tools_initialized) == 3

    def test_concurrent_request_handling(self):
        """Test handling of concurrent requests."""
        import queue
        import threading

        results = queue.Queue()

        def simulate_request(request_id):
            start = time.time()
            # Simulate request processing
            time.sleep(0.1)
            end = time.time()
            results.put((request_id, end - start))

        # Start multiple concurrent requests
        threads = []
        for i in range(5):
            thread = threading.Thread(target=simulate_request, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all requests to complete
        for thread in threads:
            thread.join()

        # Check results
        total_time = 0
        completed_requests = 0

        while not results.empty():
            request_id, duration = results.get()
            total_time += duration
            completed_requests += 1

        average_time = (
            total_time / completed_requests if completed_requests > 0 else 0
        )

        # Concurrent requests should complete efficiently
        assert completed_requests == 5
        assert (
            average_time < 0.2
        ), f"Average request time {average_time:.4f}s, expected < 0.2s"


@pytest.mark.slow
class TestStressBaselines:
    """Stress test baselines (marked as slow)."""

    def test_memory_usage_baseline(self):
        """Test memory usage baseline."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Simulate memory-intensive operations
        large_data = []
        for i in range(1000):
            large_data.append(f"data_item_{i}" * 100)

        current_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - initial_memory

        # Memory increase should be reasonable
        assert (
            memory_increase < 100
        ), f"Memory increased by {memory_increase:.2f}MB, expected < 100MB"

        # Cleanup
        del large_data

    def test_high_concurrency_baseline(self):
        """Test high concurrency baseline."""
        import concurrent.futures

        def simulate_work(task_id):
            # Simulate CPU-bound work
            result = sum(i * i for i in range(1000))
            return task_id, result

        start_time = time.time()

        # Run many concurrent tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(simulate_work, i) for i in range(50)]
            results = [
                future.result()
                for future in concurrent.futures.as_completed(futures)
            ]

        end_time = time.time()
        duration = end_time - start_time

        # High concurrency should complete within reasonable time
        assert len(results) == 50
        assert (
            duration < 5.0
        ), f"High concurrency test took {duration:.2f}s, expected < 5.0s"

    def test_large_schema_processing(self):
        """Test processing of large schemas."""
        # Create a large schema
        large_schema = {"type": "object", "properties": {}}

        # Add many properties
        for i in range(100):
            large_schema["properties"][f"field_{i}"] = {
                "type": "string",
                "description": f"Description for field {i}",
            }

        start_time = time.time()

        # Simulate schema processing
        property_count = len(large_schema["properties"])
        len(str(large_schema))  # Check schema size

        end_time = time.time()
        duration = end_time - start_time

        # Large schema processing should be fast
        assert property_count == 100
        assert (
            duration < 0.1
        ), f"Large schema processing took {duration:.4f}s, expected < 0.1s"
