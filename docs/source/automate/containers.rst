Container Deployment
====================

Deploy ostruct in containerized environments using Docker, Docker Compose, and Kubernetes. This guide covers container creation, orchestration, security hardening, and production deployment patterns.

.. note::
   Container deployments require careful handling of API keys and file access permissions. See the :doc:`../security/overview` guide for security best practices.

Docker Fundamentals
===================

Basic Docker Usage
------------------

Run ostruct directly in a container:

.. code-block:: bash

   # Basic container execution
   docker run --rm \
     -e OPENAI_API_KEY="your-api-key" \
     -v $(pwd):/workspace \
     -w /workspace \
     python:3.11-slim \
     bash -c "pip install ostruct-cli && ostruct run template.j2 schema.json -ft data.txt"

   # With specific Python version
   docker run --rm \
     -e OPENAI_API_KEY="your-api-key" \
     -v $(pwd)/templates:/templates:ro \
     -v $(pwd)/schemas:/schemas:ro \
     -v $(pwd)/data:/data:ro \
     -v $(pwd)/output:/output \
     python:3.11-slim \
     bash -c "pip install ostruct-cli && ostruct run /templates/analysis.j2 /schemas/result.json -ft /data/input.csv --output-file /output/results.json"

Creating Custom Docker Images
=============================

Minimal Dockerfile
------------------

.. code-block:: dockerfile

   FROM python:3.11-slim

   # Install ostruct
   RUN pip install ostruct-cli

   # Create non-root user for security
   RUN useradd --create-home --shell /bin/bash ostruct
   USER ostruct
   WORKDIR /home/ostruct

   # Set default command
   ENTRYPOINT ["ostruct"]

   # Example usage:
   # docker build -t ostruct:minimal .
   # docker run --rm -e OPENAI_API_KEY="key" -v $(pwd):/data ostruct:minimal run /data/template.j2 /data/schema.json

Production Dockerfile
---------------------

.. code-block:: dockerfile

   FROM python:3.11-slim as builder

   # Install build dependencies
   RUN apt-get update && apt-get install -y \
       build-essential \
       && rm -rf /var/lib/apt/lists/*

   # Create virtual environment
   RUN python -m venv /opt/venv
   ENV PATH="/opt/venv/bin:$PATH"

   # Install ostruct and dependencies
   RUN pip install --no-cache-dir ostruct-cli

   # Production image
   FROM python:3.11-slim

   # Install runtime dependencies only
   RUN apt-get update && apt-get install -y \
       ca-certificates \
       && rm -rf /var/lib/apt/lists/* \
       && apt-get clean

   # Copy virtual environment from builder
   COPY --from=builder /opt/venv /opt/venv
   ENV PATH="/opt/venv/bin:$PATH"

   # Create non-root user
   RUN groupadd -r ostruct && useradd -r -g ostruct ostruct

   # Create directories with proper permissions
   RUN mkdir -p /app/templates /app/schemas /app/data /app/output \
       && chown -R ostruct:ostruct /app

   USER ostruct
   WORKDIR /app

   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD ostruct --version || exit 1

   ENTRYPOINT ["ostruct"]

   # Build: docker build -t ostruct:production -f Dockerfile.production .
   # Run: docker run --rm -e OPENAI_API_KEY="key" -v $(pwd):/app/data ostruct:production run /app/data/template.j2 /app/data/schema.json

Multi-Stage Build with Templates
--------------------------------

.. code-block:: dockerfile

   FROM python:3.11-slim as base

   # Install ostruct
   RUN pip install ostruct-cli

   # Template preparation stage
   FROM base as templates

   # Copy and validate templates
   COPY templates/ /app/templates/
   COPY schemas/ /app/schemas/

   # Validate templates (optional)
   RUN for template in /app/templates/*.j2; do \
         ostruct run "$template" /app/schemas/validation.json --dry-run || exit 1; \
       done

   # Final runtime image
   FROM base as runtime

   # Copy validated templates
   COPY --from=templates /app/ /app/

   # Create non-root user
   RUN useradd --create-home ostruct
   USER ostruct

   WORKDIR /app
   ENTRYPOINT ["ostruct"]

Docker Compose Deployments
==========================

Basic Docker Compose
--------------------

.. code-block:: yaml

   # docker-compose.yml
   version: '3.8'

   services:
     ostruct:
       build: .
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
       volumes:
         - ./data:/app/data:ro
         - ./templates:/app/templates:ro
         - ./schemas:/app/schemas:ro
         - ./output:/app/output
       command: run /app/templates/analysis.j2 /app/schemas/result.json -ft /app/data/input.csv --output-file /app/output/results.json

   # Usage:
   # docker-compose up

Analysis Pipeline with Services
-------------------------------

.. code-block:: yaml

   version: '3.8'

   services:
     # Data preparation
     data-prep:
       image: ostruct:production
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
       volumes:
         - ./pipeline/data:/app/data:ro
         - ./pipeline/templates:/app/templates:ro
         - ./pipeline/schemas:/app/schemas:ro
         - ./pipeline/intermediate:/app/output
       command: run /app/templates/data_prep.j2 /app/schemas/prep_result.json -fc /app/data/raw.csv --output-file /app/output/prepared.json

     # Security analysis
     security-scan:
       image: ostruct:production
       depends_on:
         - data-prep
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
       volumes:
         - ./pipeline/src:/app/src:ro
         - ./pipeline/templates:/app/templates:ro
         - ./pipeline/schemas:/app/schemas:ro
         - ./pipeline/intermediate:/app/intermediate:ro
         - ./pipeline/results:/app/output
       command: run /app/templates/security.j2 /app/schemas/security.json -fc /app/src/ -ft /app/intermediate/prepared.json --output-file /app/output/security_report.json

     # Final report generation
     report-gen:
       image: ostruct:production
       depends_on:
         - security-scan
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
       volumes:
         - ./pipeline/templates:/app/templates:ro
         - ./pipeline/schemas:/app/schemas:ro
         - ./pipeline/results:/app/results:ro
         - ./pipeline/final:/app/output
       command: run /app/templates/final_report.j2 /app/schemas/report.json -ft /app/results/security_report.json --output-file /app/output/final_report.json

   # Usage:
   # docker-compose up --build

Scheduled Analysis with Cron
----------------------------

.. code-block:: yaml

   version: '3.8'

   services:
     # Scheduled daily analysis
     daily-analysis:
       image: ostruct:production
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY}
         - ANALYSIS_SCHEDULE=0 2 * * *  # Daily at 2 AM
       volumes:
         - ./data:/app/data:ro
         - ./templates:/app/templates:ro
         - ./schemas:/app/schemas:ro
         - ./reports:/app/output
         - /var/run/docker.sock:/var/run/docker.sock:ro
       command: >
         bash -c "
           echo '${ANALYSIS_SCHEDULE} ostruct run /app/templates/daily.j2 /app/schemas/daily.json -fc /app/data/ --output-file /app/output/daily-$(date +%Y%m%d).json' | crontab - &&
           crond -f
         "
       restart: unless-stopped

Environment-Specific Configurations
-----------------------------------

.. code-block:: yaml

   # docker-compose.override.yml (development)
   version: '3.8'

   services:
     ostruct:
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY_DEV}
         - OSTRUCT_LOG_LEVEL=DEBUG
       volumes:
         - ./:/app:rw  # Read-write for development
       command: run /app/templates/dev_analysis.j2 /app/schemas/dev.json --verbose --dry-run

.. code-block:: yaml

   # docker-compose.prod.yml (production)
   version: '3.8'

   services:
     ostruct:
       environment:
         - OPENAI_API_KEY=${OPENAI_API_KEY_PROD}
         - OSTRUCT_LOG_LEVEL=INFO
       volumes:
         - ./data:/app/data:ro
         - ./templates:/app/templates:ro
         - ./schemas:/app/schemas:ro
         - ./output:/app/output:rw
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
         restart_policy:
           condition: on-failure
           max_attempts: 3

   # Usage:
   # docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

Kubernetes Deployment
======================

Basic Kubernetes Deployment
---------------------------

.. code-block:: yaml

   # ostruct-deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ostruct-analyzer
     labels:
       app: ostruct
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: ostruct
     template:
       metadata:
         labels:
           app: ostruct
       spec:
         containers:
         - name: ostruct
           image: ostruct:production
           env:
           - name: OPENAI_API_KEY
             valueFrom:
               secretKeyRef:
                 name: ostruct-secrets
                 key: openai-api-key
           volumeMounts:
           - name: data-volume
             mountPath: /app/data
             readOnly: true
           - name: templates-volume
             mountPath: /app/templates
             readOnly: true
           - name: output-volume
             mountPath: /app/output
           resources:
             requests:
               memory: "256Mi"
               cpu: "100m"
             limits:
               memory: "512Mi"
               cpu: "500m"
           securityContext:
             runAsNonRoot: true
             runAsUser: 1000
             readOnlyRootFilesystem: true
         volumes:
         - name: data-volume
           configMap:
             name: analysis-data
         - name: templates-volume
           configMap:
             name: analysis-templates
         - name: output-volume
           emptyDir: {}

Secret Management
-----------------

.. code-block:: yaml

   # ostruct-secrets.yaml
   apiVersion: v1
   kind: Secret
   metadata:
     name: ostruct-secrets
   type: Opaque
   data:
     openai-api-key: <base64-encoded-api-key>

   ---
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: analysis-templates
   data:
     analysis.j2: |
       ---
       system_prompt: You are an expert data analyst.
       ---
       Analyze this data: {{ data.content }}
     security.j2: |
       ---
       system_prompt: You are a security expert.
       ---
       Scan this code: {{ code.content }}

CronJob for Scheduled Analysis
------------------------------

.. code-block:: yaml

   # ostruct-cronjob.yaml
   apiVersion: batch/v1
   kind: CronJob
   metadata:
     name: daily-analysis
   spec:
     schedule: "0 2 * * *"  # Daily at 2 AM
     jobTemplate:
       spec:
         template:
           spec:
             containers:
             - name: ostruct
               image: ostruct:production
               env:
               - name: OPENAI_API_KEY
                 valueFrom:
                   secretKeyRef:
                     name: ostruct-secrets
                     key: openai-api-key
               command:
               - ostruct
               - run
               - /app/templates/daily.j2
               - /app/schemas/daily.json
               - -fc
               - /app/data/
               - --output-file
               - /app/output/daily-analysis.json
               volumeMounts:
               - name: data-volume
                 mountPath: /app/data
                 readOnly: true
               - name: templates-volume
                 mountPath: /app/templates
                 readOnly: true
               - name: output-volume
                 mountPath: /app/output
               resources:
                 requests:
                   memory: "256Mi"
                   cpu: "100m"
                 limits:
                   memory: "512Mi"
                   cpu: "500m"
             volumes:
             - name: data-volume
               persistentVolumeClaim:
                 claimName: analysis-data-pvc
             - name: templates-volume
               configMap:
                 name: analysis-templates
             - name: output-volume
               persistentVolumeClaim:
                 claimName: analysis-output-pvc
             restartPolicy: OnFailure
     successfulJobsHistoryLimit: 3
     failedJobsHistoryLimit: 1

Multi-Environment Kubernetes
----------------------------

.. code-block:: yaml

   # Base configuration - ostruct-base.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: ostruct-config
   data:
     timeout: "600"
     cleanup: "true"

   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ostruct
   spec:
     replicas: 1
     selector:
       matchLabels:
         app: ostruct
     template:
       metadata:
         labels:
           app: ostruct
       spec:
         containers:
         - name: ostruct
           image: ostruct:production
           envFrom:
           - configMapRef:
               name: ostruct-config
           - secretRef:
               name: ostruct-secrets

.. code-block:: yaml

   # Development overlay - overlays/dev/kustomization.yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization

   resources:
   - ../../base

   patchesStrategicMerge:
   - deployment-patch.yaml

   configMapGenerator:
   - name: ostruct-config
     behavior: merge
     literals:
     - timeout=300
     - log_level=DEBUG

.. code-block:: yaml

   # Production overlay - overlays/prod/kustomization.yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization

   resources:
   - ../../base

   patchesStrategicMerge:
   - deployment-patch.yaml

   configMapGenerator:
   - name: ostruct-config
     behavior: merge
     literals:
     - timeout=900
     - log_level=INFO

   # Usage:
   # kubectl apply -k overlays/dev
   # kubectl apply -k overlays/prod

Container Security
==================

Security Hardening
------------------

**Dockerfile Security Best Practices:**

.. code-block:: dockerfile

   FROM python:3.11-slim

   # Update base image and remove package manager
   RUN apt-get update && apt-get upgrade -y && \
       apt-get install -y --no-install-recommends ca-certificates && \
       apt-get clean && \
       rm -rf /var/lib/apt/lists/* && \
       rm -rf /usr/bin/apt*

   # Create non-root user with specific UID/GID
   RUN groupadd -g 1000 ostruct && \
       useradd -u 1000 -g ostruct -m ostruct

   # Install ostruct with hash verification (example)
   RUN pip install --no-cache-dir \
       --index-url https://pypi.org/simple/ \
       --trusted-host pypi.org \
       ostruct-cli==0.8.0

   # Set up secure directory structure
   RUN mkdir -p /app/{templates,schemas,data,output} && \
       chown -R ostruct:ostruct /app && \
       chmod 755 /app && \
       chmod 700 /app/output

   USER ostruct
   WORKDIR /app

   # Remove shell access for security
   RUN rm -f /bin/sh /bin/bash

   ENTRYPOINT ["ostruct"]

**Runtime Security:**

.. code-block:: yaml

   # Kubernetes security context
   securityContext:
     runAsNonRoot: true
     runAsUser: 1000
     runAsGroup: 1000
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
     capabilities:
       drop:
       - ALL
     seccompProfile:
       type: RuntimeDefault

**Volume Security:**

.. code-block:: bash

   # Docker with read-only volumes and tmpfs
   docker run --rm \
     --read-only \
     --tmpfs /tmp:rw,noexec,nosuid,size=100m \
     -v $(pwd)/data:/app/data:ro \
     -v $(pwd)/output:/app/output:rw \
     ostruct:production

Network Security
----------------

.. code-block:: yaml

   # Kubernetes network policy
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: ostruct-network-policy
   spec:
     podSelector:
       matchLabels:
         app: ostruct
     policyTypes:
     - Egress
     - Ingress
     egress:
     - to: []  # Allow all egress (for OpenAI API)
       ports:
       - protocol: TCP
         port: 443
     ingress: []  # No ingress needed

Secrets Management
------------------

**Docker Secrets:**

.. code-block:: bash

   # Using Docker secrets
   echo "your-openai-api-key" | docker secret create openai_api_key -

   docker service create \
     --secret openai_api_key \
     --env OPENAI_API_KEY_FILE=/run/secrets/openai_api_key \
     ostruct:production

**Kubernetes External Secrets:**

.. code-block:: yaml

   # Using External Secrets Operator
   apiVersion: external-secrets.io/v1beta1
   kind: ExternalSecret
   metadata:
     name: ostruct-secrets
   spec:
     refreshInterval: 1h
     secretStoreRef:
       name: vault-secret-store
       kind: SecretStore
     target:
       name: ostruct-secrets
       creationPolicy: Owner
     data:
     - secretKey: openai-api-key
       remoteRef:
         key: secret/ostruct
         property: openai_api_key

Performance Optimization
========================

Resource Management
-------------------

.. code-block:: yaml

   # Kubernetes resource optimization
   resources:
     requests:
       memory: "128Mi"
       cpu: "50m"
     limits:
       memory: "512Mi"
       cpu: "500m"

   # Horizontal Pod Autoscaler (if processing queues)
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   metadata:
     name: ostruct-hpa
   spec:
     scaleTargetRef:
       apiVersion: apps/v1
       kind: Deployment
       name: ostruct
     minReplicas: 1
     maxReplicas: 5
     metrics:
     - type: Resource
       resource:
         name: cpu
         target:
           type: Utilization
           averageUtilization: 70

Image Optimization
------------------

.. code-block:: dockerfile

   # Multi-stage build for smaller images
   FROM python:3.11-slim as builder
   RUN pip install ostruct-cli
   RUN pip list --format=freeze > requirements.txt

   FROM python:3.11-alpine as runtime
   COPY --from=builder requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   # Result: ~50% smaller image

Volume Caching
--------------

.. code-block:: yaml

   # Persistent volume for caching
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: ostruct-cache-pvc
   spec:
     accessModes:
     - ReadWriteOnce
     resources:
       requests:
         storage: 1Gi

   # Mount in deployment
   volumeMounts:
   - name: cache-volume
     mountPath: /tmp/ostruct-cache

Monitoring and Observability
============================

Health Checks
-------------

.. code-block:: dockerfile

   # Dockerfile health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
     CMD ostruct --version || exit 1

.. code-block:: yaml

   # Kubernetes health checks
   livenessProbe:
     exec:
       command:
       - ostruct
       - --version
     initialDelaySeconds: 30
     periodSeconds: 30
   readinessProbe:
     exec:
       command:
       - ostruct
       - --version
     initialDelaySeconds: 5
     periodSeconds: 10

Logging
-------

.. code-block:: yaml

   # Structured logging configuration
   env:
   - name: OSTRUCT_LOG_LEVEL
     value: "INFO"
   - name: OSTRUCT_LOG_FORMAT
     value: "json"

   # Log aggregation with Fluentd
   - name: fluentd-logger
     image: fluentd:latest
     volumeMounts:
     - name: log-volume
       mountPath: /var/log

Metrics Collection
------------------

.. code-block:: yaml

   # Prometheus metrics sidecar
   - name: metrics-exporter
     image: prometheus/node-exporter:latest
     ports:
     - containerPort: 9100
       name: metrics

   # ServiceMonitor for Prometheus
   apiVersion: monitoring.coreos.com/v1
   kind: ServiceMonitor
   metadata:
     name: ostruct-metrics
   spec:
     selector:
       matchLabels:
         app: ostruct
     endpoints:
     - port: metrics

Deployment Strategies
=====================

Blue-Green Deployment
---------------------

.. code-block:: yaml

   # Blue deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ostruct-blue
     labels:
       app: ostruct
       version: blue
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: ostruct
         version: blue

   ---
   # Green deployment
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ostruct-green
     labels:
       app: ostruct
       version: green
   spec:
     replicas: 2
     selector:
       matchLabels:
         app: ostruct
         version: green

   ---
   # Service routing
   apiVersion: v1
   kind: Service
   metadata:
     name: ostruct-service
   spec:
     selector:
       app: ostruct
       version: blue  # Switch to green for deployment

Canary Deployment
-----------------

.. code-block:: yaml

   # Using Istio for canary deployment
   apiVersion: networking.istio.io/v1alpha3
   kind: VirtualService
   metadata:
     name: ostruct-canary
   spec:
     http:
     - match:
       - headers:
           canary:
             exact: "true"
       route:
       - destination:
           host: ostruct-service
           subset: v2
     - route:
       - destination:
           host: ostruct-service
           subset: v1
         weight: 90
       - destination:
           host: ostruct-service
           subset: v2
         weight: 10

Troubleshooting
===============

Common Container Issues
-----------------------

**Permission Errors:**

.. code-block:: bash

   # Debug container permissions
   docker run --rm -it ostruct:production sh
   # Check user and permissions
   id
   ls -la /app

   # Fix: Ensure proper ownership in Dockerfile
   RUN chown -R ostruct:ostruct /app

**API Key Issues:**

.. code-block:: bash

   # Debug environment variables
   docker run --rm ostruct:production env | grep OPENAI

   # Test API key access
   docker run --rm -e OPENAI_API_KEY="test" ostruct:production run --dry-run template.j2 schema.json

**Volume Mount Issues:**

.. code-block:: bash

   # Debug volume mounts
   docker run --rm -v $(pwd):/app/data ostruct:production ls -la /app/data

   # Fix: Check host directory permissions
   chmod 755 $(pwd)
   chown -R 1000:1000 $(pwd)

**Resource Constraints:**

.. code-block:: bash

   # Monitor container resources
   docker stats

   # Check Kubernetes pod resources
   kubectl top pods

Network Debugging
-----------------

.. code-block:: bash

   # Test network connectivity
   docker run --rm ostruct:production sh -c "ping -c 3 api.openai.com"

   # Check DNS resolution
   docker run --rm ostruct:production nslookup api.openai.com

   # Kubernetes network debugging
   kubectl run debug --image=busybox -it --rm -- sh

Performance Troubleshooting
---------------------------

.. code-block:: bash

   # Monitor container performance
   docker exec -it container_name top

   # Check I/O performance
   docker exec -it container_name iostat

   # Kubernetes resource monitoring
   kubectl describe pod ostruct-pod
   kubectl logs ostruct-pod --previous

Best Practices Summary
======================

Security
--------

1. **Use non-root users** in containers
2. **Read-only root filesystem** when possible
3. **Minimal base images** (alpine, distroless)
4. **Secret management** via external systems
5. **Network policies** to restrict traffic
6. **Regular security scanning** of images

Performance
-----------

1. **Multi-stage builds** for smaller images
2. **Resource limits** and requests
3. **Health checks** for reliability
4. **Caching strategies** for efficiency
5. **Horizontal scaling** for load handling

Operations
----------

1. **Structured logging** for observability
2. **Metrics collection** for monitoring
3. **Graceful shutdown** handling
4. **Backup strategies** for persistent data
5. **Disaster recovery** planning

Next Steps
==========

- :doc:`ci_cd` - Integrate containers with CI/CD pipelines
- :doc:`scripting_patterns` - Advanced automation patterns
- :doc:`cost_control` - Cost optimization strategies
- :doc:`../security/overview` - Comprehensive security guide
