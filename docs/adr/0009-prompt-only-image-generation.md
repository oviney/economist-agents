# ADR-0009: Prompt-Only Image Generation

**Status:** Proposed
**Date:** 2026-04-19
**Decision Maker:** Engineering Lead
**Supersedes:** None
**Superseded by:** None

## Context

The content pipeline currently uses DALL-E 3 API to generate featured images automatically. This incurs ~$0.08 per image, a cost that is not tracked in ROI telemetry and therefore hidden from business metrics.

Testing confirms that the existing prompt template (defined in `skills/editorial-illustration/SKILL.md` and implemented in `scripts/featured_image_agent.py`) produces high-quality Economist-style images when used manually via ChatGPT UI or other free tools.

The question: should we continue paying for API-generated images, or output the prompt for manual generation?

## Decision

We will modify the content pipeline to output image prompts in article frontmatter instead of calling the DALL-E API. Users will generate images manually using free tools (ChatGPT UI, Midjourney, etc.) before merging article PRs.

The `image_prompt:` field will be added to article frontmatter, containing the full DALL-E prompt. The `image:` field will initially reference a placeholder until the user uploads the generated image.

## Alternatives Considered

1. **Keep DALL-E API (status quo)** — Continue automatic generation at ~$0.08/image. Rejected because the cost is unnecessary given free alternatives produce equivalent quality, and the cost is currently hidden from ROI tracking.

2. **Self-hosted Stable Diffusion** — Run local image generation to eliminate API costs. Rejected because it introduces infrastructure complexity (GPU requirements, model management) disproportionate to the benefit.

3. **Remove featured images entirely** — Simplify pipeline by dropping image generation. Rejected because featured images significantly improve article visual engagement scores and social sharing.

4. **Hybrid approach (prompt-only default, API optional)** — Keep API as opt-in for urgent articles. Considered acceptable as a follow-up enhancement if manual generation proves too slow for some workflows.

## Consequences

- **Positive:** Eliminates ~$0.08/image cost; enables accurate ROI tracking; maintains image quality via proven prompt template
- **Positive:** User retains creative control to iterate on image before publishing
- **Negative:** Adds manual step to PR workflow (~30 seconds to paste prompt and download image)
- **Negative:** Images no longer generated automatically in CI/CD
- **Follow-up:** Update `skills/editorial-illustration/SKILL.md` to document prompt-only workflow
- **Follow-up:** Update `mcp_servers/image_generator_server.py` to add `generate_image_prompt` tool
- **Revisit if:** Manual step becomes bottleneck for high-volume article production

## References

- `skills/editorial-illustration/SKILL.md` — Visual standards and prompt template
- `scripts/featured_image_agent.py` — Current DALL-E integration (lines 171-273)
- `mcp_servers/image_generator_server.py` — MCP server wrapping DALL-E
- User testing: Prompt successfully generated Economist-style image via ChatGPT UI (2026-04-19)
