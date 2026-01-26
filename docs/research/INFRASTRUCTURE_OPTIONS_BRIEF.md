# Research Brief: Infrastructure Options for Production Agentic Workflows

**Prepared for**: Architecture Decision
**Date**: 2026-01-25
**Context**: Evaluating GitHub Actions vs VPS vs Cloud for reliable agent execution

---

## Problem Statement

Our agentic workflow currently runs on GitHub Actions with local filesystem persistence. This creates reliability and scalability concerns:

1. **Ephemeral Runners**: GitHub Actions runners reset between runs - no persistent state
2. **Vector DB Loss**: ChromaDB at `.chromadb/` is wiped on each run
3. **Execution Limits**: 6-hour max job runtime, limited concurrency
4. **No Monitoring**: No real-time alerts or observability
5. **Cost Uncertainty**: GitHub Actions minutes can spike unexpectedly

**Current Execution Pattern**: On-demand article generation (not always-on)

---

## Current State Analysis

| Component | Current Location | Persistence | Risk Level |
|-----------|------------------|-------------|------------|
| ChromaDB Vector Store | `.chromadb/` (local) | ❌ Ephemeral | 🔴 HIGH |
| Generated Articles | `output/` (local) | ❌ Ephemeral | 🟡 MEDIUM |
| Governance Logs | `output/governance/` | ❌ Ephemeral | 🟡 MEDIUM |
| ROI Telemetry | `output/execution_roi.json` | ❌ Ephemeral | 🟢 LOW |
| Code & Config | Git repository | ✅ Persistent | 🟢 LOW |

**GitHub Actions Limits** (as of 2025):
- Job timeout: 6 hours (default), 35 days max for self-hosted
- Concurrent jobs: 20 (free), 60 (Pro), 500 (Enterprise)
- Storage: 500 MB (free), 2 GB (Pro) for artifacts
- Minutes: 2,000/month (free), 3,000 (Pro), unlimited (Enterprise)
- Artifact retention: 90 days max

---

## Option Analysis

### Option 1: Enhanced GitHub Actions (Minimal Change)

**What it is**: Keep GitHub Actions but add cloud storage for persistence.

**Architecture**:
```
GitHub Actions Runner (ephemeral)
    ├── Download state from S3/GCS on job start
    ├── Run agent workflow
    ├── Upload state to S3/GCS on job end
    └── Commit outputs to Git
```

**Implementation**:
```yaml
# In workflow
- name: Restore ChromaDB
  uses: actions/cache@v4
  with:
    path: .chromadb
    key: chromadb-${{ hashFiles('archived/**/*.md') }}

# Or use S3
- name: Restore from S3
  run: aws s3 sync s3://bucket/.chromadb .chromadb
```

**Pros**:
- Minimal architecture change
- No server management
- Pay-per-use (good for on-demand workloads)
- Already familiar infrastructure

**Cons**:
- Cold start latency (download state each run)
- 6-hour job limit still applies
- Not suitable for real-time/interactive use
- Debugging is harder (ephemeral environment)

**Cost Estimate**:
- GitHub Actions: ~$0/month (within free tier for occasional runs)
- S3 storage: ~$2-5/month for vector DB + artifacts
- **Total**: ~$5/month

**Effort**: 2-3 story points

---

### Option 2: Dedicated VPS (Full Control)

**What it is**: Run everything on a persistent virtual server.

**Providers**: DigitalOcean, Linode, Hetzner, Vultr

**Architecture**:
```
VPS (always-on)
    ├── ChromaDB (persistent on disk)
    ├── Agent runtime (Python + CrewAI)
    ├── API endpoint (optional - FastAPI/Flask)
    └── Cron jobs or webhook triggers
```

**Recommended Specs**:
- 4 GB RAM (ChromaDB + Python runtime)
- 2 vCPUs
- 80 GB SSD (vector DB + outputs)
- Ubuntu 22.04 LTS

**Pros**:
- Full control over environment
- Persistent state (no cold starts)
- No execution time limits
- Can run interactive/real-time workloads
- Predictable costs
- Easy debugging (SSH access)

**Cons**:
- Server maintenance responsibility
- Always-on cost (even when idle)
- Need to manage security, backups, updates
- Single point of failure (unless you add redundancy)

**Cost Estimate**:
- DigitalOcean Droplet (4GB): $24/month
- Hetzner CX22 (4GB): €4.85/month (~$5)
- Linode 4GB: $24/month
- **Total**: $5-24/month + your time

**Effort**: 5-8 story points (setup + Dockerfile + deployment automation)

---

### Option 3: Managed Container Platform (Balance)

**What it is**: Deploy as containers on managed platforms with persistent storage.

**Providers**: Fly.io, Railway, Render, Google Cloud Run

**Architecture**:
```
Container Platform
    ├── App Container (Python + CrewAI)
    │   └── Scales to zero when idle
    ├── Persistent Volume (ChromaDB)
    └── Managed Postgres (optional - for structured data)
```

**Fly.io Example**:
```toml
# fly.toml
[mounts]
  source = "chromadb_data"
  destination = "/app/.chromadb"

[http_service]
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0
```

**Pros**:
- Scales to zero (cost-efficient for on-demand)
- Persistent volumes available
- No server management
- Easy deployment (git push)
- Built-in monitoring and logging
- Can expose API endpoints

**Cons**:
- Less control than VPS
- Vendor-specific configuration
- Cold starts when scaling from zero (~2-5 seconds)
- Volume costs add up

**Cost Estimate**:
- Fly.io: $0-5/month (scales to zero) + $0.15/GB/month for volumes
- Railway: $5/month + usage
- Render: $7/month for always-on, or per-request
- **Total**: $5-15/month

**Effort**: 3-5 story points (Dockerfile + platform config)

---

### Option 4: Full Cloud (Enterprise Scale)

**What it is**: AWS/GCP/Azure with managed services.

**Architecture**:
```
Cloud Provider (AWS example)
    ├── Lambda or ECS (compute)
    ├── S3 (artifact storage)
    ├── OpenSearch or Pinecone (managed vector DB)
    ├── RDS/DynamoDB (structured data)
    ├── CloudWatch (monitoring)
    └── EventBridge (scheduling)
```

**Pros**:
- Enterprise-grade reliability
- Managed vector DB (Pinecone, Weaviate Cloud)
- Auto-scaling
- Full observability
- Compliance-ready (SOC2, HIPAA, etc.)

**Cons**:
- Complexity overkill for current scale
- Higher baseline cost
- Cloud expertise required
- Vendor lock-in

**Cost Estimate**:
- Minimum viable: $50-100/month
- With managed vector DB: $70-150/month
- **Total**: $50-150/month

**Effort**: 13-21 story points (IaC, networking, security, deployment)

---

### Option 5: Hybrid (Recommended for Your Use Case)

**What it is**: GitHub Actions for CI/CD + cloud storage for state + optional API endpoint.

**Architecture**:
```
GitHub Actions (CI/CD, article generation)
    ├── Pulls ChromaDB from cloud storage
    ├── Runs agent workflow
    ├── Pushes results to cloud storage
    └── Commits articles to Git

Cloud Storage (S3/GCS/R2)
    ├── ChromaDB snapshots
    ├── Generated artifacts
    └── Telemetry data

Optional: Fly.io API (for on-demand triggers)
    └── Webhook endpoint for manual runs
```

**Pros**:
- Best of both worlds
- Minimal operational burden
- Cost-efficient (pay only for what you use)
- Persistent state without always-on server
- Can add API layer incrementally

**Cons**:
- Cold start latency (acceptable for batch workloads)
- Slightly more complex than pure GitHub Actions

**Cost Estimate**:
- GitHub Actions: Free tier
- Cloudflare R2: $0.015/GB/month (no egress fees!)
- Optional Fly.io: $0-5/month
- **Total**: $1-10/month

**Effort**: 3-5 story points

---

## Decision Matrix

| Criterion | Weight | Option 1 | Option 2 | Option 3 | Option 4 | Option 5 |
|-----------|--------|----------|----------|----------|----------|----------|
| Persistence | 25% | Medium | High | High | High | High |
| Cost (low is better) | 20% | Low | Medium | Low | High | Low |
| Operational burden | 20% | Low | High | Low | Medium | Low |
| Scalability | 15% | Medium | Medium | High | High | Medium |
| Time to implement | 10% | Fast | Medium | Fast | Slow | Fast |
| Future flexibility | 10% | Medium | High | Medium | High | High |

**Weighted Scores** (5 = best):
- Option 1 (Enhanced GHA): 3.5
- Option 2 (VPS): 3.2
- Option 3 (Containers): 4.0
- Option 4 (Full Cloud): 3.0
- Option 5 (Hybrid): **4.3** ⭐

---

## Specific Recommendations by Use Case

### If you run articles weekly (current state):
→ **Option 5 (Hybrid)** - Add S3/R2 for ChromaDB persistence, keep GitHub Actions

### If you want real-time/interactive generation:
→ **Option 3 (Fly.io)** - API endpoint with persistent volume

### If you want maximum control and learning:
→ **Option 2 (Hetzner VPS)** - $5/month, full control, great for learning

### If you're scaling to enterprise:
→ **Option 4 (AWS/GCP)** - But probably overkill for now

---

## Quick Wins (Do This Week)

1. **Add GitHub Actions cache for ChromaDB**:
```yaml
- uses: actions/cache@v4
  with:
    path: .chromadb
    key: chromadb-v1-${{ hashFiles('archived/**/*.md') }}
    restore-keys: chromadb-v1-
```

2. **Create Dockerfile** for portability:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "scripts/economist_agent.py"]
```

3. **Add backup to cloud storage** (one-time setup):
```bash
# After each run
aws s3 sync .chromadb s3://economist-agents/chromadb/
aws s3 sync output/ s3://economist-agents/output/
```

---

## Questions for Further Analysis

1. How often do you generate articles? (Daily, weekly, on-demand?)
2. Do you need an API endpoint for external triggers?
3. What's your budget ceiling per month?
4. Do you need real-time monitoring/alerts?
5. Are there compliance requirements (data residency, etc.)?

---

## References

- GitHub Actions Limits: https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration
- Fly.io Pricing: https://fly.io/docs/about/pricing/
- Cloudflare R2 Pricing: https://developers.cloudflare.com/r2/pricing/
- Hetzner Cloud: https://www.hetzner.com/cloud
- ChromaDB Deployment: https://docs.trychroma.com/deployment

---

## Current Codebase References

- ChromaDB setup: `/home/user/economist-agents/src/tools/style_memory_tool.py`
- GitHub Actions workflows: `/home/user/economist-agents/.github/workflows/`
- Output directory: `/home/user/economist-agents/output/`
- Governance logs: `/home/user/economist-agents/output/governance/`
