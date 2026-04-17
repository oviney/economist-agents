# Agent Skills Configs

Agent YAML configurations — both the generic public templates and any
organisation-specific variants that extend them.

## Structure

```
agents/skills_configs/
├── README.md              # This file
├── research-analyst.yaml  # Public: verified data briefs
├── content-writer.yaml    # Public: evidence-based articles
├── data-analyst.yaml      # Public: insight summaries and chart specs
└── editor-reviewer.yaml   # Public: structured quality review
```

All agents validate against `agents/schema.json`.

## Public vs private

Public agents are generic, domain-agnostic templates suitable for community
reuse. Private agents extend or replace them with proprietary prompts, internal
tooling references, or brand-specific voice.

**Typical pattern for a private variant:**

1. Start from a public template (e.g., `research-analyst.yaml`).
2. Copy it alongside with a distinguishing name (e.g., `research-analyst-internal.yaml`).
3. Add proprietary source lists, tone guidelines, or output schemas.
4. Reference the private agent in your pipeline configuration.

## Privacy reminder

This directory is tracked by Git. Do **not** commit API keys, credentials, or
secrets — use environment variables or a secrets manager.
