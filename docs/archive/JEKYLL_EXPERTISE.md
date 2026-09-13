# Jekyll Blog Expertise - Lessons from Blog QA Agent

This document captures Jekyll-specific expertise gained through automated blog validation and bug fixing.

## Table of Contents
- [Configuration Patterns](#configuration-patterns)
- [Layout Architecture](#layout-architecture)
- [Common Pitfalls](#common-pitfalls)
- [Best Practices](#best-practices)
- [SEO Optimization](#seo-optimization)
- [Performance Tips](#performance-tips)
- [Validation Checks](#validation-checks)

---

## Configuration Patterns

### Multi-Document YAML Issues

**Problem:** Jekyll _config.yml files using multiple `---` document separators break PyYAML's `safe_load()`.

```yaml
# ❌ WRONG - Multiple documents
key1: value1
---
key2: value2
---
key3: value3
```

```yaml
# ✅ CORRECT - Single document
key1: value1
key2: value2
key3: value3
```

**Detection:**
```python
# Use safe_load_all for multi-document YAML
with open('_config.yml') as f:
    docs = list(yaml.safe_load_all(f))
    if len(docs) > 1:
        print(f"WARNING: Multi-document YAML detected ({len(docs)} documents)")
```

### Plugin Configuration

**Pattern:** If templates use `{% seo %}` tag, the plugin MUST be in _config.yml

```yaml
# Required for jekyll-seo-tag
plugins:
  - jekyll-feed
  - jekyll-seo-tag  # Must be present if {% seo %} is used
```

**Validation:**
```python
def validate_plugin_config(config_path, layouts_dir):
    # Check if {% seo %} is used in any layout
    seo_tag_used = False
    for layout_file in Path(layouts_dir).glob('*.html'):
        if '{% seo %}' in layout_file.read_text():
            seo_tag_used = True
            break

    # Check if jekyll-seo-tag is configured
    with open(config_path) as f:
        config = yaml.safe_load(f)
        plugins = config.get('plugins', [])

    if seo_tag_used and 'jekyll-seo-tag' not in plugins:
        return False, "Layout uses {% seo %} but jekyll-seo-tag not in plugins"

    return True, "Plugin configuration valid"
```

### Remote Theme Configuration

**Pattern:** For GitHub Pages, use `remote_theme` instead of `theme`

```yaml
# ✅ CORRECT - For GitHub Pages
remote_theme: pages-themes/cayman@v0.2.0

# ❌ WRONG - This won't work on GitHub Pages
theme: cayman
```

---

## Layout Architecture

### Jekyll File Priority

**Key Rule:** Jekyll prioritizes .html over .md files with the same basename.

```
index.html      # ← Jekyll serves this
index.md        # ← This is ignored!
```

**Solution:** Delete .html if .md is intended to be canonical.

### Layout Inheritance

**Pattern:** Use `default.html` as base layout, extend for specific needs.

```
_layouts/
  default.html    # Base layout (header, footer, nav)
  post.html       # Extends default for blog posts
  page.html       # Only if static pages need custom structure
```

**Anti-pattern:** Creating page.html when default.html works fine.

```yaml
# ✅ CORRECT - Use default if it works
---
layout: default
title: About
---

# ❌ WRONG - Unnecessary complexity
---
layout: page  # Creates dependency on _layouts/page.html
title: About
---
```

### Layout File Validation

**Problem:** Front matter references layout that doesn't exist.

```python
def validate_layout_exists(post_path, layouts_dir):
    with open(post_path) as f:
        content = f.read()

    # Extract front matter
    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if match:
        front_matter = yaml.safe_load(match.group(1))
        layout = front_matter.get('layout')

        if layout:
            layout_path = Path(layouts_dir) / f"{layout}.html"
            if not layout_path.exists():
                return False, f"Layout '{layout}' not found at {layout_path}"

    return True, "Layout valid"
```

---

## Common Pitfalls

### 1. Unused/Orphaned Files

**Issue:** Files left behind from theme experiments or old content.

**Examples:**
- `staff.html` - References undefined collections
- `collections.yml` - In wrong directory (should be in `_data/`)
- `home-automation.md` - Empty file with no content

**Detection:**
```bash
# Find files with no inbound links
grep -r "href=\"staff.html\"" . || echo "staff.html is orphaned"

# Find empty markdown files
find . -name "*.md" -type f -empty
```

**Solution:** Regular audits, delete unused files.

### 2. Duplicate Content

**Issue:** Same page exists in multiple formats.

**Example:**
- `index.html` with old "TechFrontier" branding
- `index.md` with current "Quality Engineering Insights" branding

**Impact:** Confusion, wrong content served, maintenance burden.

**Solution:** Standardize on .md files, delete duplicates.

### 3. Placeholder Content

**Issue:** Template placeholders left in production.

**Examples:**
- `YOUR-PROFILE` in LinkedIn URL
- `REPLACE-ME` in configuration
- `TODO: Add content` in markdown

**Detection:**
```python
PLACEHOLDER_PATTERNS = [
    r'YOUR-[A-Z]+',
    r'REPLACE[-_]ME',
    r'TODO:',
    r'FIXME:',
    r'XXX',
]

def find_placeholders(content):
    found = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.finditer(pattern, content, re.IGNORECASE)
        found.extend([m.group() for m in matches])
    return found
```

---

## Best Practices

### Data-Driven Navigation

**Pattern:** Store navigation in `_data/navigation.yml`, render with include.

```yaml
# _data/navigation.yml
- name: Home
  link: /
- name: Blog
  link: /blog/
- name: About
  link: /about/
```

```html
<!-- _includes/navigation.html -->
<nav>
  {% for item in site.data.navigation %}
    <a href="{{ item.link }}">{{ item.name }}</a>
  {% endfor %}
</nav>
```

**Benefits:**
- Single source of truth
- Easy to maintain
- No hardcoded links in templates

### Front Matter Standards

**Required Fields:**
```yaml
---
layout: post
title: "Article Title"
date: 2025-12-31
ai_assisted: true  # If AI was used in creation
categories: [quality-engineering, testing]
---
```

**Validation:**
```python
REQUIRED_FIELDS = ['layout', 'title', 'date']

def validate_front_matter(post_path):
    with open(post_path) as f:
        content = f.read()

    match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return False, "No front matter found"

    front_matter = yaml.safe_load(match.group(1))

    for field in REQUIRED_FIELDS:
        if field not in front_matter:
            return False, f"Missing required field: {field}"

    return True, "Front matter valid"
```

### Content Organization

```
_posts/                      # Published blog posts
  2025-12-31-article.md
_drafts/                     # Unpublished drafts
  wip-article.md
_data/                       # Data files (YAML, JSON, CSV)
  navigation.yml
  authors.yml
_layouts/                    # Layout templates
  default.html
  post.html
_includes/                   # Reusable partials
  navigation.html
  footer.html
assets/                      # Static assets
  css/
  images/
  js/
```

---

## SEO Optimization

### Permalink Structure

**Best Practice:** Use date-based permalinks for blog posts.

```yaml
# _config.yml
permalink: /:year/:month/:day/:title/
```

**Result:** Clean URLs like `/2025/12/31/testing-times/`

**Benefits:**
- SEO-friendly
- Chronological structure
- Prevents URL collisions

### Title Tag Rendering

**Pattern:** Use jekyll-seo-tag for automatic title generation.

```html
<!-- _layouts/default.html -->
<head>
  {% seo %}
</head>
```

**Generates:**
```html
<title>Article Title | Site Name</title>
<meta property="og:title" content="Article Title">
<meta name="twitter:title" content="Article Title">
```

### AI Disclosure

**Pattern:** Add transparency about AI-assisted content.

```yaml
# Front matter
ai_assisted: true
```

```html
<!-- _layouts/post.html -->
{% if page.ai_assisted %}
  <div class="ai-disclosure">
    {{ site.ai_disclosure }}
  </div>
{% endif %}
```

```yaml
# _config.yml
ai_disclosure: >
  This article was created with AI assistance. All content has been
  reviewed by human editors for accuracy and quality.
```

---

## Performance Tips

### Font Loading Optimization

**Problem:** Google Fonts cause console warnings and slow rendering.

**Solution:** Add proper preconnect hints.

```html
<!-- _includes/head-custom.html -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
```

**Impact:** 100-300ms faster font loading.

### Image Optimization

**Best Practice:** Use responsive images with srcset.

```html
<img src="/assets/images/photo.jpg"
     srcset="/assets/images/photo-400w.jpg 400w,
             /assets/images/photo-800w.jpg 800w"
     sizes="(max-width: 600px) 400px, 800px"
     alt="Description">
```

---

## Validation Checks

### Automated Validation Script

```python
#!/usr/bin/env python3
"""Jekyll Blog Validation - Core Checks"""

import yaml
import re
from pathlib import Path

class JekyllValidator:
    def __init__(self, blog_dir):
        self.blog_dir = Path(blog_dir)
        self.errors = []

    def validate_all(self):
        """Run all validation checks"""
        self.check_config()
        self.check_layouts()
        self.check_posts()
        return len(self.errors) == 0

    def check_config(self):
        """Validate _config.yml"""
        config_path = self.blog_dir / '_config.yml'

        # Check for multi-document YAML
        with open(config_path) as f:
            docs = list(yaml.safe_load_all(f))
            if len(docs) > 1:
                self.errors.append(
                    f"Config has {len(docs)} YAML documents, should be 1"
                )

        # Check required plugins
        config = docs[0]
        if '{% seo %}' in self.find_in_layouts():
            plugins = config.get('plugins', [])
            if 'jekyll-seo-tag' not in plugins:
                self.errors.append(
                    "Layout uses {% seo %} but jekyll-seo-tag not configured"
                )

    def check_layouts(self):
        """Validate layout files"""
        layouts_dir = self.blog_dir / '_layouts'

        # Find all layout references
        referenced_layouts = set()
        for post in self.blog_dir.glob('_posts/*.md'):
            with open(post) as f:
                match = re.match(r'^---\n(.*?)\n---', f.read(), re.DOTALL)
                if match:
                    fm = yaml.safe_load(match.group(1))
                    if 'layout' in fm:
                        referenced_layouts.add(fm['layout'])

        # Check if layout files exist
        for layout in referenced_layouts:
            layout_path = layouts_dir / f"{layout}.html"
            if not layout_path.exists():
                self.errors.append(f"Layout '{layout}' not found")

    def check_posts(self):
        """Validate blog posts"""
        for post in self.blog_dir.glob('_posts/*.md'):
            self.validate_post(post)

    def validate_post(self, post_path):
        """Validate single post"""
        with open(post_path) as f:
            content = f.read()

        # Check front matter exists
        match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
        if not match:
            self.errors.append(f"{post_path.name}: No front matter")
            return

        # Parse front matter
        fm = yaml.safe_load(match.group(1))

        # Check required fields
        for field in ['layout', 'title', 'date']:
            if field not in fm:
                self.errors.append(
                    f"{post_path.name}: Missing {field}"
                )

        # Check for placeholders
        placeholders = [
            'YOUR-', 'REPLACE-', 'TODO:', 'FIXME:', 'XXX'
        ]
        for placeholder in placeholders:
            if placeholder in content:
                self.errors.append(
                    f"{post_path.name}: Contains placeholder '{placeholder}'"
                )

if __name__ == '__main__':
    validator = JekyllValidator('/path/to/blog')
    if validator.validate_all():
        print("✅ All checks passed")
    else:
        print(f"❌ {len(validator.errors)} errors found:")
        for error in validator.errors:
            print(f"  - {error}")
```

### Pre-Commit Integration

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run Jekyll validation
python3 /path/to/jekyll_validator.py .

if [ $? -ne 0 ]; then
    echo "❌ Validation failed, commit blocked"
    exit 1
fi

# Build Jekyll to catch issues
bundle exec jekyll build --trace

if [ $? -ne 0 ]; then
    echo "❌ Jekyll build failed, commit blocked"
    exit 1
fi

echo "✅ Pre-commit checks passed"
exit 0
```

---

## Summary

### Most Critical Checks

1. **YAML Parsing** - Avoid multi-document configs
2. **Layout Files** - Validate layouts exist for all references
3. **Plugin Config** - Ensure required plugins are enabled
4. **Duplicate Files** - Delete conflicting .html/.md pairs
5. **Placeholders** - Scan for template text in production
6. **Front Matter** - Require layout, title, date fields
7. **Font Preconnect** - Add proper hints for performance

### Automation Strategy

- **Pre-commit Hook** - Block obviously bad commits
- **GitHub Actions** - Validate on every push
- **Self-Learning QA** - Improve checks based on findings

### Knowledge Evolution

This document reflects expertise gained through:
- 5 production bug discoveries
- 7 bug fixes implemented
- 3-tier validation system deployment
- Self-learning skills system integration

**Last Updated:** 2025-12-31
**Experience Base:** economist-blog-v5 validation runs
