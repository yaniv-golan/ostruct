Scripting Patterns
==================

Advanced automation patterns for ostruct including batch processing, error handling, monitoring, and integration patterns. Learn how to build robust automation workflows that scale with your needs.

.. note::
   These patterns build on the foundation provided in :doc:`ci_cd` and :doc:`containers`. Adapt examples to your specific infrastructure and requirements.

Batch Processing Patterns
=========================

Sequential File Processing
--------------------------

Process multiple files in sequence with comprehensive error handling:

.. code-block:: bash

   #!/bin/bash
   # process_files.sh - Sequential file processor

   set -euo pipefail  # Exit on error, undefined vars, pipe failures

   # Configuration
   TEMPLATE_DIR="./templates"
   SCHEMA_DIR="./schemas"
   INPUT_DIR="./input"
   OUTPUT_DIR="./output"
   RESULTS_DIR="./results"
   TIMEOUT=300

   # Logging setup
   LOG_FILE="./logs/processing_$(date +%Y%m%d_%H%M%S).log"
   mkdir -p "$(dirname "$LOG_FILE")"

   log() {
       echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
   }

   # Validation
   validate_environment() {
       log "Validating environment..."
       
       if [[ -z "${OPENAI_API_KEY:-}" ]]; then
           log "ERROR: OPENAI_API_KEY not set"
           exit 1
       fi
       
       for dir in "$TEMPLATE_DIR" "$SCHEMA_DIR" "$INPUT_DIR"; do
           if [[ ! -d "$dir" ]]; then
               log "ERROR: Directory not found: $dir"
               exit 1
           fi
       done
       
       mkdir -p "$OUTPUT_DIR" "$RESULTS_DIR"
       log "Environment validation complete"
   }

   # Process a single file
   process_file() {
       local input_file="$1"
       local template="$2"
       local schema="$3"
       local output_file="$4"
       
       log "Processing: $input_file -> $output_file"
       
       if ostruct run "$template" "$schema" \
           --base-dir "$PWD" \
           -A "$INPUT_DIR" \
           -A "$OUTPUT_DIR" \
           -ft "input_file=$input_file" \
           --timeout "$TIMEOUT" \
           --code-interpreter-cleanup \
           --file-search-cleanup \
           --output-file "$output_file"; then
           log "SUCCESS: $output_file"
           return 0
       else
           log "ERROR: Failed to process $input_file"
           return 1
       fi
   }

   # Main processing loop
   main() {
       validate_environment
       
       local success_count=0
       local error_count=0
       local total_files=0
       
       log "Starting batch processing..."
       
       # Process all CSV files
       while IFS= read -r -d '' file; do
           ((total_files++))
           
           local basename
           basename=$(basename "$file" .csv)
           local output_file="$OUTPUT_DIR/${basename}_analysis.json"
           
           if process_file "$file" \
               "$TEMPLATE_DIR/data_analysis.j2" \
               "$SCHEMA_DIR/analysis_result.json" \
               "$output_file"; then
               ((success_count++))
           else
               ((error_count++))
           fi
           
       done < <(find "$INPUT_DIR" -name "*.csv" -type f -print0)
       
       # Generate summary report
       local summary_file="$RESULTS_DIR/batch_summary_$(date +%Y%m%d_%H%M%S).json"
       cat > "$summary_file" << EOF
   {
       "batch_id": "$(date +%Y%m%d_%H%M%S)",
       "start_time": "$(date -Iseconds)",
       "total_files": $total_files,
       "successful": $success_count,
       "failed": $error_count,
       "success_rate": $(( success_count * 100 / (total_files > 0 ? total_files : 1) )),
       "log_file": "$LOG_FILE"
   }
   EOF
       
       log "Batch processing complete: $success_count/$total_files successful"
       log "Summary: $summary_file"
       
       # Exit with error if any files failed
       if [[ $error_count -gt 0 ]]; then
           exit 1
       fi
   }

   main "$@"

Parallel Processing
-------------------

Process files in parallel for improved performance:

.. code-block:: bash

   #!/bin/bash
   # parallel_processor.sh - Parallel file processor

   set -euo pipefail

   # Configuration
   MAX_PARALLEL_JOBS=4
   TEMPLATE="./templates/analysis.j2"
   SCHEMA="./schemas/result.json"
   INPUT_DIR="./input"
   OUTPUT_DIR="./output"

   # Process single file (worker function)
   process_file_worker() {
       local input_file="$1"
       local worker_id="$2"
       
       local basename
       basename=$(basename "$input_file")
       local output_file="$OUTPUT_DIR/${basename%.*}_result.json"
       local log_file="./logs/worker_${worker_id}_$(date +%Y%m%d_%H%M%S).log"
       
       {
           echo "Worker $worker_id: Processing $input_file"
           
           if ostruct run "$TEMPLATE" "$SCHEMA" \
               --base-dir "$PWD" \
               -A "$INPUT_DIR" \
               -A "$OUTPUT_DIR" \
               -ft "$input_file" \
               --timeout 300 \
               --code-interpreter-cleanup \
               --output-file "$output_file" \
               2>&1; then
               echo "Worker $worker_id: SUCCESS - $output_file"
           else
               echo "Worker $worker_id: ERROR - Failed processing $input_file"
               exit 1
           fi
       } > "$log_file" 2>&1
   }

   # Export function for parallel execution
   export -f process_file_worker
   export TEMPLATE SCHEMA INPUT_DIR OUTPUT_DIR

   # Main execution
   main() {
       mkdir -p "$OUTPUT_DIR" "./logs"
       
       echo "Starting parallel processing with $MAX_PARALLEL_JOBS workers..."
       
       # Use GNU parallel or xargs for parallel execution
       if command -v parallel &> /dev/null; then
           find "$INPUT_DIR" -name "*.csv" -type f | \
               parallel -j "$MAX_PARALLEL_JOBS" \
               'process_file_worker {} {#}'
       else
           # Fallback to xargs
           find "$INPUT_DIR" -name "*.csv" -type f | \
               xargs -I {} -P "$MAX_PARALLEL_JOBS" \
               bash -c 'process_file_worker "$1" "$$"' _ {}
       fi
       
       echo "Parallel processing complete"
   }

   main "$@"

Queue-Based Processing
----------------------

Use a queue system for scalable processing:

.. code-block:: bash

   #!/bin/bash
   # queue_processor.sh - Queue-based processor

   # Redis-based queue (requires redis-cli)
   QUEUE_NAME="ostruct:processing_queue"
   RESULT_QUEUE="ostruct:results"

   # Add job to queue
   queue_job() {
       local input_file="$1"
       local template="$2"
       local schema="$3"
       
       local job_data
       job_data=$(jq -n \
           --arg input "$input_file" \
           --arg template "$template" \
           --arg schema "$schema" \
           --arg id "$(uuidgen)" \
           '{id: $id, input: $input, template: $template, schema: $schema, status: "queued", queued_at: now}')
       
       redis-cli LPUSH "$QUEUE_NAME" "$job_data"
       echo "Queued job: $input_file"
   }

   # Worker process
   process_queue() {
       local worker_id="$1"
       
       echo "Worker $worker_id starting..."
       
       while true; do
           # Get job from queue (blocking)
           local job_data
           job_data=$(redis-cli BRPOP "$QUEUE_NAME" 30 | tail -n1)
           
           if [[ -z "$job_data" || "$job_data" == "(nil)" ]]; then
               echo "Worker $worker_id: No jobs available, waiting..."
               continue
           fi
           
           # Parse job data
           local job_id input_file template schema
           job_id=$(echo "$job_data" | jq -r '.id')
           input_file=$(echo "$job_data" | jq -r '.input')
           template=$(echo "$job_data" | jq -r '.template')
           schema=$(echo "$job_data" | jq -r '.schema')
           
           echo "Worker $worker_id: Processing job $job_id"
           
           # Update job status
           local updated_job
           updated_job=$(echo "$job_data" | jq '.status = "processing" | .started_at = now')
           redis-cli SET "job:$job_id" "$updated_job"
           
           # Process file
           local output_file="./output/${job_id}_result.json"
           local success=false
           
           if ostruct run "$template" "$schema" \
               -ft "$input_file" \
               --timeout 300 \
               --code-interpreter-cleanup \
               --output-file "$output_file"; then
               success=true
           fi
           
           # Update job status and add result
           if $success; then
               updated_job=$(echo "$updated_job" | jq \
                   '.status = "completed" | .completed_at = now | .output_file = $output' \
                   --arg output "$output_file")
               redis-cli LPUSH "$RESULT_QUEUE" "$updated_job"
               echo "Worker $worker_id: Job $job_id completed successfully"
           else
               updated_job=$(echo "$updated_job" | jq '.status = "failed" | .failed_at = now')
               echo "Worker $worker_id: Job $job_id failed"
           fi
           
           redis-cli SET "job:$job_id" "$updated_job"
       done
   }

   case "${1:-}" in
       "queue")
           shift
           queue_job "$@"
           ;;
       "worker")
           process_queue "${2:-1}"
           ;;
       *)
           echo "Usage: $0 {queue|worker} [args...]"
           echo "  queue <input_file> <template> <schema>"
           echo "  worker [worker_id]"
           exit 1
           ;;
   esac

Error Handling and Recovery
===========================

Retry Mechanisms
----------------

Implement robust retry logic with exponential backoff:

.. code-block:: bash

   #!/bin/bash
   # retry_processor.sh - Processor with retry logic

   # Retry configuration
   MAX_RETRIES=3
   INITIAL_DELAY=1
   BACKOFF_MULTIPLIER=2
   MAX_DELAY=60

   # Retry function with exponential backoff
   retry_with_backoff() {
       local command="$1"
       local max_retries="$2"
       local delay="$INITIAL_DELAY"
       local attempt=1
       
       while [[ $attempt -le $max_retries ]]; do
           echo "Attempt $attempt/$max_retries: $command"
           
           if eval "$command"; then
               echo "Command succeeded on attempt $attempt"
               return 0
           fi
           
           if [[ $attempt -eq $max_retries ]]; then
               echo "Command failed after $max_retries attempts"
               return 1
           fi
           
           echo "Command failed, retrying in ${delay}s..."
           sleep "$delay"
           
           # Exponential backoff with jitter
           delay=$((delay * BACKOFF_MULTIPLIER))
           if [[ $delay -gt $MAX_DELAY ]]; then
               delay=$MAX_DELAY
           fi
           
           # Add jitter (±25%)
           local jitter=$((delay / 4))
           delay=$((delay + (RANDOM % (jitter * 2)) - jitter))
           
           ((attempt++))
       done
   }

   # Process with retry
   process_with_retry() {
       local input_file="$1"
       local template="$2"
       local schema="$3"
       local output_file="$4"
       
       local command="ostruct run '$template' '$schema' \
           -ft '$input_file' \
           --timeout 300 \
           --code-interpreter-cleanup \
           --output-file '$output_file'"
       
       retry_with_backoff "$command" "$MAX_RETRIES"
   }

   # Example usage
   if process_with_retry \
       "./input/data.csv" \
       "./templates/analysis.j2" \
       "./schemas/result.json" \
       "./output/analysis_result.json"; then
       echo "Processing completed successfully"
   else
       echo "Processing failed after all retries"
       exit 1
   fi

Graceful Degradation
--------------------

Handle partial failures gracefully:

.. code-block:: bash

   #!/bin/bash
   # graceful_processor.sh - Processor with graceful degradation

   # Process with fallback options
   process_with_fallback() {
       local input_file="$1"
       local output_file="$2"
       
       # Primary processing: Full analysis with Code Interpreter
       if ostruct run "./templates/full_analysis.j2" "./schemas/full_result.json" \
           -fc "$input_file" \
           --timeout 300 \
           --code-interpreter-cleanup \
           --output-file "$output_file" 2>/dev/null; then
           echo "Full analysis completed: $output_file"
           return 0
       fi
       
       echo "Full analysis failed, trying template-only processing..."
       
       # Fallback 1: Template-only processing
       if ostruct run "./templates/basic_analysis.j2" "./schemas/basic_result.json" \
           -ft "$input_file" \
           --timeout 180 \
           --output-file "$output_file" 2>/dev/null; then
           echo "Basic analysis completed: $output_file"
           return 0
       fi
       
       echo "Basic analysis failed, generating minimal report..."
       
       # Fallback 2: Minimal report with file metadata
       cat > "$output_file" << EOF
   {
       "status": "degraded",
       "file": "$input_file",
       "size": $(stat -c%s "$input_file" 2>/dev/null || echo "unknown"),
       "processed_at": "$(date -Iseconds)",
       "error": "Analysis failed, minimal report generated"
   }
   EOF
       
       echo "Minimal report generated: $output_file"
       return 2  # Indicate degraded processing
   }

Dead Letter Queue
-----------------

Handle persistent failures:

.. code-block:: bash

   #!/bin/bash
   # dlq_processor.sh - Dead letter queue handler

   FAILED_DIR="./failed"
   DLQ_DIR="./dead_letter_queue"
   MAX_DLQ_RETRIES=5

   # Move to dead letter queue
   move_to_dlq() {
       local failed_file="$1"
       local error_info="$2"
       
       mkdir -p "$DLQ_DIR"
       
       local dlq_file="$DLQ_DIR/$(basename "$failed_file").$(date +%s)"
       local metadata_file="${dlq_file}.metadata"
       
       mv "$failed_file" "$dlq_file"
       
       cat > "$metadata_file" << EOF
   {
       "original_file": "$failed_file",
       "moved_to_dlq": "$(date -Iseconds)",
       "error": "$error_info",
       "retry_count": 0,
       "max_retries": $MAX_DLQ_RETRIES
   }
   EOF
       
       echo "Moved to DLQ: $dlq_file"
   }

   # Process DLQ items
   process_dlq() {
       echo "Processing dead letter queue..."
       
       for dlq_file in "$DLQ_DIR"/*.csv 2>/dev/null; do
           [[ -f "$dlq_file" ]] || continue
           
           local metadata_file="${dlq_file}.metadata"
           [[ -f "$metadata_file" ]] || continue
           
           local retry_count
           retry_count=$(jq -r '.retry_count' "$metadata_file")
           local max_retries
           max_retries=$(jq -r '.max_retries' "$metadata_file")
           
           if [[ $retry_count -ge $max_retries ]]; then
               echo "Max retries exceeded for $dlq_file, skipping"
               continue
           fi
           
           echo "Retrying DLQ item: $dlq_file (attempt $((retry_count + 1)))"
           
           if process_with_retry "$dlq_file" \
               "./templates/recovery.j2" \
               "./schemas/result.json" \
               "./output/$(basename "$dlq_file" .csv)_recovered.json"; then
               echo "DLQ item recovered successfully"
               rm -f "$dlq_file" "$metadata_file"
           else
               # Update retry count
               jq --arg count "$((retry_count + 1))" \
                   '.retry_count = ($count | tonumber)' \
                   "$metadata_file" > "${metadata_file}.tmp"
               mv "${metadata_file}.tmp" "$metadata_file"
               echo "DLQ retry failed, count updated"
           fi
       done
   }

Monitoring and Observability
============================

Metrics Collection
------------------

Collect and expose metrics for monitoring:

.. code-block:: bash

   #!/bin/bash
   # metrics_collector.sh - Collect processing metrics

   METRICS_DIR="./metrics"
   METRICS_FILE="$METRICS_DIR/processing_metrics.json"

   # Initialize metrics
   init_metrics() {
       mkdir -p "$METRICS_DIR"
       
       cat > "$METRICS_FILE" << EOF
   {
       "start_time": "$(date -Iseconds)",
       "total_jobs": 0,
       "completed_jobs": 0,
       "failed_jobs": 0,
       "processing_time_total": 0,
       "last_update": "$(date -Iseconds)"
   }
   EOF
   }

   # Update metrics
   update_metrics() {
       local status="$1"  # completed|failed
       local processing_time="$2"
       
       local temp_file
       temp_file=$(mktemp)
       
       jq --arg status "$status" \
          --arg time "$processing_time" \
          --arg now "$(date -Iseconds)" \
          '.total_jobs += 1 |
           if $status == "completed" then .completed_jobs += 1 else .failed_jobs += 1 end |
           .processing_time_total += ($time | tonumber) |
           .last_update = $now |
           .success_rate = (.completed_jobs * 100 / .total_jobs) |
           .average_processing_time = (.processing_time_total / .total_jobs)' \
          "$METRICS_FILE" > "$temp_file"
       
       mv "$temp_file" "$METRICS_FILE"
   }

   # Export metrics for Prometheus
   export_prometheus_metrics() {
       local metrics_output="$METRICS_DIR/prometheus.txt"
       
       local total_jobs completed_jobs failed_jobs success_rate avg_time
       total_jobs=$(jq -r '.total_jobs' "$METRICS_FILE")
       completed_jobs=$(jq -r '.completed_jobs' "$METRICS_FILE")
       failed_jobs=$(jq -r '.failed_jobs' "$METRICS_FILE")
       success_rate=$(jq -r '.success_rate // 0' "$METRICS_FILE")
       avg_time=$(jq -r '.average_processing_time // 0' "$METRICS_FILE")
       
       cat > "$metrics_output" << EOF
   # HELP ostruct_jobs_total Total number of jobs processed
   # TYPE ostruct_jobs_total counter
   ostruct_jobs_total $total_jobs

   # HELP ostruct_jobs_completed Number of successfully completed jobs
   # TYPE ostruct_jobs_completed counter
   ostruct_jobs_completed $completed_jobs

   # HELP ostruct_jobs_failed Number of failed jobs
   # TYPE ostruct_jobs_failed counter
   ostruct_jobs_failed $failed_jobs

   # HELP ostruct_success_rate Success rate percentage
   # TYPE ostruct_success_rate gauge
   ostruct_success_rate $success_rate

   # HELP ostruct_avg_processing_time Average processing time in seconds
   # TYPE ostruct_avg_processing_time gauge
   ostruct_avg_processing_time $avg_time
   EOF
       
       echo "Metrics exported to $metrics_output"
   }

Health Check Endpoints
----------------------

Create health check endpoints for monitoring systems:

.. code-block:: bash

   #!/bin/bash
   # health_check.sh - Health check for ostruct automation

   # Configuration
   MAX_QUEUE_SIZE=100
   MAX_ERROR_RATE=10  # percent
   OSTRUCT_TIMEOUT=30

   # Check ostruct availability
   check_ostruct() {
       if timeout "$OSTRUCT_TIMEOUT" ostruct --version &>/dev/null; then
           echo "ostruct:ok"
           return 0
       else
           echo "ostruct:error"
           return 1
       fi
   }

   # Check API connectivity
   check_api() {
       if [[ -z "${OPENAI_API_KEY:-}" ]]; then
           echo "api:no_key"
           return 1
       fi
       
       # Test with dry run
       if timeout "$OSTRUCT_TIMEOUT" ostruct run \
           <(echo "Test: {{ test }}") \
           <(echo '{"type":"object","properties":{"result":{"type":"string"}}}') \
           -V test=health_check \
           --dry-run &>/dev/null; then
           echo "api:ok"
           return 0
       else
           echo "api:error"
           return 1
       fi
   }

   # Check queue health
   check_queue() {
       local queue_size=0
       
       if command -v redis-cli &>/dev/null; then
           queue_size=$(redis-cli LLEN "ostruct:processing_queue" 2>/dev/null || echo 0)
       fi
       
       if [[ $queue_size -lt $MAX_QUEUE_SIZE ]]; then
           echo "queue:ok:$queue_size"
           return 0
       else
           echo "queue:backlog:$queue_size"
           return 1
       fi
   }

   # Check error rate
   check_error_rate() {
       local metrics_file="./metrics/processing_metrics.json"
       
       if [[ ! -f "$metrics_file" ]]; then
           echo "metrics:no_data"
           return 1
       fi
       
       local error_rate
       error_rate=$(jq -r '.success_rate // 100' "$metrics_file")
       error_rate=$((100 - ${error_rate%.*}))  # Convert to error rate
       
       if [[ $error_rate -lt $MAX_ERROR_RATE ]]; then
           echo "error_rate:ok:${error_rate}%"
           return 0
       else
           echo "error_rate:high:${error_rate}%"
           return 1
       fi
   }

   # Overall health check
   health_check() {
       local status="healthy"
       local checks=()
       
       if ! check_ostruct; then
           status="unhealthy"
       fi
       checks+=("$(check_ostruct)")
       
       if ! check_api; then
           status="degraded"
       fi
       checks+=("$(check_api)")
       
       if ! check_queue; then
           status="degraded"
       fi
       checks+=("$(check_queue)")
       
       if ! check_error_rate; then
           status="degraded"
       fi
       checks+=("$(check_error_rate)")
       
       # Output JSON health status
       local checks_json
       checks_json=$(printf '%s\n' "${checks[@]}" | jq -R . | jq -s .)
       
       jq -n \
           --arg status "$status" \
           --argjson checks "$checks_json" \
           --arg timestamp "$(date -Iseconds)" \
           '{status: $status, checks: $checks, timestamp: $timestamp}'
   }

   # HTTP health endpoint (requires netcat)
   serve_health_endpoint() {
       local port="${1:-8080}"
       
       echo "Starting health check server on port $port..."
       
       while true; do
           {
               echo -e "HTTP/1.1 200 OK\r"
               echo -e "Content-Type: application/json\r"
               echo -e "Connection: close\r"
               echo -e "\r"
               health_check
           } | nc -l -p "$port" -q 1
       done
   }

   case "${1:-check}" in
       "check")
           health_check
           ;;
       "serve")
           serve_health_endpoint "${2:-8080}"
           ;;
       *)
           echo "Usage: $0 {check|serve [port]}"
           exit 1
           ;;
   esac

Integration Patterns
====================

Webhook Integration
-------------------

Integrate with webhook systems for event-driven processing:

.. code-block:: bash

   #!/bin/bash
   # webhook_processor.sh - Process webhook events

   # Webhook handler
   handle_webhook() {
       local payload="$1"
       
       # Parse webhook payload
       local event_type source_url file_path
       event_type=$(echo "$payload" | jq -r '.event_type')
       source_url=$(echo "$payload" | jq -r '.source_url // empty')
       file_path=$(echo "$payload" | jq -r '.file_path // empty')
       
       case "$event_type" in
           "file_uploaded")
               handle_file_upload "$file_path" "$payload"
               ;;
           "url_submitted")
               handle_url_processing "$source_url" "$payload"
               ;;
           "batch_request")
               handle_batch_request "$payload"
               ;;
           *)
               echo "Unknown event type: $event_type"
               return 1
               ;;
       esac
   }

   # Handle file upload events
   handle_file_upload() {
       local file_path="$1"
       local payload="$2"
       
       echo "Processing uploaded file: $file_path"
       
       # Determine processing template based on file type
       local template schema
       case "${file_path##*.}" in
           "csv")
               template="./templates/csv_analysis.j2"
               schema="./schemas/csv_result.json"
               ;;
           "json")
               template="./templates/json_analysis.j2"
               schema="./schemas/json_result.json"
               ;;
           *)
               template="./templates/generic_analysis.j2"
               schema="./schemas/generic_result.json"
               ;;
       esac
       
       # Process with metadata from webhook
       local output_file="./output/webhook_$(date +%s)_result.json"
       local webhook_id
       webhook_id=$(echo "$payload" | jq -r '.id // "unknown"')
       
       ostruct run "$template" "$schema" \
           -ft "$file_path" \
           -J "webhook_metadata=$payload" \
           -V "webhook_id=$webhook_id" \
           --code-interpreter-cleanup \
           --output-file "$output_file"
       
       # Send callback if webhook URL provided
       local callback_url
       callback_url=$(echo "$payload" | jq -r '.callback_url // empty')
       
       if [[ -n "$callback_url" ]]; then
           send_webhook_response "$callback_url" "$webhook_id" "$output_file"
       fi
   }

   # Send response webhook
   send_webhook_response() {
       local callback_url="$1"
       local webhook_id="$2"
       local result_file="$3"
       
       local response_payload
       response_payload=$(jq -n \
           --arg id "$webhook_id" \
           --arg status "completed" \
           --arg timestamp "$(date -Iseconds)" \
           --argjson result "$(cat "$result_file")" \
           '{id: $id, status: $status, timestamp: $timestamp, result: $result}')
       
       curl -X POST "$callback_url" \
           -H "Content-Type: application/json" \
           -d "$response_payload" \
           --max-time 30 \
           --retry 3
   }

Database Integration
--------------------

Store and retrieve processing results:

.. code-block:: bash

   #!/bin/bash
   # db_integration.sh - Database integration for results

   # Database configuration
   DB_TYPE="${DB_TYPE:-sqlite}"
   DB_HOST="${DB_HOST:-localhost}"
   DB_NAME="${DB_NAME:-ostruct_results}"
   DB_USER="${DB_USER:-ostruct}"

   # Initialize database
   init_database() {
       case "$DB_TYPE" in
           "sqlite")
               sqlite3 "$DB_NAME.db" << 'EOF'
   CREATE TABLE IF NOT EXISTS processing_jobs (
       id TEXT PRIMARY KEY,
       input_file TEXT NOT NULL,
       template TEXT NOT NULL,
       schema TEXT NOT NULL,
       status TEXT NOT NULL,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       started_at DATETIME,
       completed_at DATETIME,
       output_file TEXT,
       error_message TEXT,
       processing_time INTEGER
   );

   CREATE TABLE IF NOT EXISTS job_results (
       job_id TEXT PRIMARY KEY,
       result_data TEXT NOT NULL,
       metadata TEXT,
       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY (job_id) REFERENCES processing_jobs (id)
   );
   EOF
               ;;
           "postgres")
               psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'EOF'
   CREATE TABLE IF NOT EXISTS processing_jobs (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       input_file TEXT NOT NULL,
       template TEXT NOT NULL,
       schema TEXT NOT NULL,
       status TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT NOW(),
       started_at TIMESTAMP,
       completed_at TIMESTAMP,
       output_file TEXT,
       error_message TEXT,
       processing_time INTEGER
   );

   CREATE TABLE IF NOT EXISTS job_results (
       job_id UUID PRIMARY KEY,
       result_data JSONB NOT NULL,
       metadata JSONB,
       created_at TIMESTAMP DEFAULT NOW(),
       FOREIGN KEY (job_id) REFERENCES processing_jobs (id)
   );
   EOF
               ;;
       esac
   }

   # Store job record
   store_job() {
       local job_id="$1"
       local input_file="$2"
       local template="$3"
       local schema="$4"
       
       case "$DB_TYPE" in
           "sqlite")
               sqlite3 "$DB_NAME.db" << EOF
   INSERT INTO processing_jobs (id, input_file, template, schema, status)
   VALUES ('$job_id', '$input_file', '$template', '$schema', 'queued');
   EOF
               ;;
           "postgres")
               psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << EOF
   INSERT INTO processing_jobs (id, input_file, template, schema, status)
   VALUES ('$job_id', '$input_file', '$template', '$schema', 'queued');
   EOF
               ;;
       esac
   }

   # Update job status
   update_job_status() {
       local job_id="$1"
       local status="$2"
       local output_file="${3:-}"
       local error_message="${4:-}"
       
       local timestamp_field
       case "$status" in
           "processing") timestamp_field="started_at" ;;
           "completed"|"failed") timestamp_field="completed_at" ;;
       esac
       
       case "$DB_TYPE" in
           "sqlite")
               sqlite3 "$DB_NAME.db" << EOF
   UPDATE processing_jobs 
   SET status = '$status',
       $timestamp_field = CURRENT_TIMESTAMP,
       output_file = '$output_file',
       error_message = '$error_message'
   WHERE id = '$job_id';
   EOF
               ;;
           "postgres")
               psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << EOF
   UPDATE processing_jobs 
   SET status = '$status',
       $timestamp_field = NOW(),
       output_file = '$output_file',
       error_message = '$error_message'
   WHERE id = '$job_id';
   EOF
               ;;
       esac
   }

   # Store job results
   store_results() {
       local job_id="$1"
       local result_file="$2"
       local metadata="${3:-{}}"
       
       local result_data
       result_data=$(cat "$result_file")
       
       case "$DB_TYPE" in
           "sqlite")
               sqlite3 "$DB_NAME.db" << EOF
   INSERT INTO job_results (job_id, result_data, metadata)
   VALUES ('$job_id', '$result_data', '$metadata');
   EOF
               ;;
           "postgres")
               # Escape quotes for PostgreSQL
               result_data=$(echo "$result_data" | sed "s/'/''/g")
               metadata=$(echo "$metadata" | sed "s/'/''/g")
               
               psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << EOF
   INSERT INTO job_results (job_id, result_data, metadata)
   VALUES ('$job_id', '$result_data'::jsonb, '$metadata'::jsonb);
   EOF
               ;;
       esac
   }

Configuration Management
========================

Environment-Specific Configurations
-----------------------------------

Manage configurations across environments:

.. code-block:: bash

   #!/bin/bash
   # config_manager.sh - Environment configuration management

   # Default configuration
   DEFAULT_CONFIG="./config/default.yaml"
   ENV_CONFIG_DIR="./config/environments"

   # Load configuration for environment
   load_config() {
       local environment="$1"
       local config_file="$ENV_CONFIG_DIR/${environment}.yaml"
       
       if [[ ! -f "$config_file" ]]; then
           echo "Configuration not found for environment: $environment"
           exit 1
       fi
       
       # Merge default and environment configs
       local merged_config
       merged_config=$(yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' \
           "$DEFAULT_CONFIG" "$config_file")
       
       echo "$merged_config"
   }

   # Set environment variables from config
   set_env_from_config() {
       local environment="$1"
       local config
       config=$(load_config "$environment")
       
       # Export environment variables
       export OSTRUCT_TIMEOUT=$(echo "$config" | yq e '.ostruct.timeout' -)
       export OSTRUCT_MODEL=$(echo "$config" | yq e '.ostruct.model' -)
       export BATCH_SIZE=$(echo "$config" | yq e '.processing.batch_size' -)
       export MAX_RETRIES=$(echo "$config" | yq e '.processing.max_retries' -)
       
       echo "Environment configured for: $environment"
   }

   # Validate configuration
   validate_config() {
       local environment="$1"
       local config
       config=$(load_config "$environment")
       
       # Required fields validation
       local required_fields=(
           ".ostruct.timeout"
           ".ostruct.model"
           ".processing.batch_size"
           ".processing.max_retries"
       )
       
       for field in "${required_fields[@]}"; do
           local value
           value=$(echo "$config" | yq e "$field" -)
           
           if [[ "$value" == "null" || -z "$value" ]]; then
               echo "Missing required configuration: $field"
               return 1
           fi
       done
       
       echo "Configuration validation passed for: $environment"
   }

Next Steps
==========

These scripting patterns provide a foundation for building robust ostruct automation. Consider:

1. **Monitoring Integration** - Connect metrics to your monitoring stack
2. **Alerting Setup** - Configure alerts for failures and performance issues  
3. **Scaling Strategies** - Implement auto-scaling based on queue depth
4. **Security Hardening** - Apply security best practices from :doc:`../security/overview`
5. **Cost Optimization** - Implement strategies from :doc:`cost_control`

For deployment patterns, see:

- :doc:`ci_cd` - Continuous integration and deployment
- :doc:`containers` - Containerized deployments
- :doc:`cost_control` - Cost management strategies