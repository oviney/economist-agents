# Private Skills

This directory contains organisation-specific agent configurations that are **not** intended for public sharing.

## What belongs here

Place agent YAML files here when they contain:

- Proprietary prompts that encode competitive advantage or internal processes.
- References to internal tooling, systems, or API endpoints.
- Custom personas tuned to your brand voice or editorial standards.
- Domain-specific heuristics that should not be disclosed publicly.

## Structure

```
skills/private/
└── README.md          # This file
```

Add your private agent YAML files following the same schema used in `skills/public/`.
See `agents/schema.json` for the required fields.

## Relationship to `skills/public/`

Public agents in `skills/public/` are generic, domain-agnostic templates.
Private agents extend or replace them with organisation-specific configuration.

**Typical pattern:**

1. Start from a public agent template (e.g., `skills/public/research-analyst.yaml`).
2. Copy it into `skills/private/`.
3. Add your proprietary source lists, tone guidelines, or output schemas.
4. Reference the private agent in your pipeline configuration instead of the public one.

## Privacy reminder

This directory is tracked by Git.  
Do **not** commit API keys, credentials, or any secrets here.  
Use environment variables or a secrets manager for sensitive values.
