#!/usr/bin/env python3
"""
Blog QA Agent with Self-Learning Skills

Validates blog posts and site structure before publication.
Learns from each run to improve validation patterns over time.

Usage:
    python3 blog_qa_agent.py --blog-dir /path/to/blog --post _posts/2025-12-31-article.md
    python3 blog_qa_agent.py --blog-dir /path/to/blog --show-skills
"""

import os
import sys
import re
import subprocess
from pathlib import Path
import yaml
from skills_manager import SkillsManager

def validate_yaml_front_matter(file_path, skills_manager=None, blog_dir=None):
    """Validate YAML front matter has required fields."""
    issues = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for front matter
    if not content.startswith('---'):
        issues.append("Missing YAML front matter")
        if skills_manager:
            skills_manager.learn_pattern(
                "content_quality",
                "missing_frontmatter",
                {
                    "severity": "critical",
                    "pattern": "Post missing YAML front matter",
                    "check": "Verify file starts with ---",
                    "learned_from": f"File: {Path(file_path).name}"
                }
            )
        return issues
    
    # Extract front matter
    try:
        front_matter = content.split('---')[1]
        data = yaml.safe_load(front_matter)
    except Exception as e:
        issues.append(f"Invalid YAML front matter: {e}")
        return issues
    
    # Required fields
    required_fields = ['layout', 'title', 'date']
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing required field: {field}")
            if field == 'layout' and skills_manager:
                skills_manager.learn_pattern(
                    "jekyll_configuration",
                    "missing_layout_field",
                    {
                        "severity": "critical",
                        "pattern": "Post missing 'layout' field causes empty title and no header/nav",
                        "check": "Verify layout field present in front matter",
                        "learned_from": f"File: {Path(file_path).name}",
                        "impact": "Page renders without Jekyll layout - no title, header, navigation"
                    }
                )
    
    # Validate date format
    if 'date' in data:
        date_str = str(data['date'])
        if not re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            issues.append(f"Invalid date format: {date_str} (expected YYYY-MM-DD)")
    
    # Check if layout exists
    if 'layout' in data and blog_dir:
        layout_name = data['layout']
        layouts_dir = Path(blog_dir) / '_layouts'
        layout_file = layouts_dir / f"{layout_name}.html"
        
        if not layout_file.exists():
            issues.append(f"⚠️  Layout '{layout_name}' not found in _layouts/ directory")
            if skills_manager:
                skills_manager.learn_pattern(
                    "jekyll_configuration",
                    "missing_layout_file",
                    {
                        "severity": "critical",
                        "pattern": "Layout referenced in front matter but file doesn't exist",
                        "check": "Verify _layouts/{layout}.html exists for all layout values",
                        "learned_from": f"Layout '{layout_name}' missing for {Path(file_path).name}"
                    }
                )
    
    # Warn about AI-assisted posts without disclosure flag
    content_lower = content.lower()
    if any(word in content_lower for word in ['ai', 'generated', 'llm', 'gpt', 'claude']):
        if not data.get('ai_assisted'):
            issues.append("⚠️  Post mentions AI but missing 'ai_assisted: true' flag")
    
    return issues


def check_broken_links(file_path):
    """Check for broken internal links."""
    issues = []
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        # Find markdown links
        links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', line)
        for text, url in links:
            # Check internal links (not starting with http)
            if not url.startswith('http') and not url.startswith('#'):
                # Check if it's an asset
                if url.startswith('/assets/') or url.startswith('assets/'):
                    asset_path = url.lstrip('/')
                    blog_dir = Path(file_path).parent.parent
                    full_path = blog_dir / asset_path
                    if not full_path.exists():
                        issues.append(f"Line {i}: Broken asset link: {url}")
                # Check for relative links to posts
                elif url.startswith('/') or url.startswith('../'):
                    issues.append(f"Line {i}: ⚠️  Relative link may be broken: {url}")
    
    return issues


def check_economist_style(file_path):
    """Check for common style violations."""
    issues = []
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Banned phrases
    banned_phrases = [
        (r"in today's (fast-paced )?world", "Throat-clearing opening"),
        (r"it'?s no secret that", "Throat-clearing phrase"),
        (r"when it comes to", "Vague phrase"),
        (r"needless to say", "Redundant phrase"),
        (r"hey there", "Casual greeting"),
        (r"awesome|superheroes|rock and roll", "Overly enthusiastic language"),
        (r"🎉|🚀|💯|✨", "Emojis in prose"),
    ]
    
    for pattern, reason in banned_phrases:
        if re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Style violation: {reason} - found '{pattern}'")
    
    # Check for American spelling
    american_spellings = [
        (r'\borganization\b', 'Use British spelling: organisation'),
        (r'\bfavor\b', 'Use British spelling: favour'),
        (r'\bcolor\b', 'Use British spelling: colour'),
        (r'\boptimize\b', 'Use British spelling: optimise'),
        (r'\banalyze\b', 'Use British spelling: analyse'),
    ]
    
    for pattern, suggestion in american_spellings:
        if re.search(pattern, content):
            issues.append(f"⚠️  {suggestion}")
    
    return issues


def validate_post(file_path, blog_dir=None, skills_manager=None):
    """Run all validation checks on a blog post."""
    print(f"\n{'='*60}")
    print(f"Validating: {file_path}")
    print(f"{'='*60}\n")
    
    all_issues = []
    
    # 1. YAML front matter
    print("📋 Checking YAML front matter...")
    issues = validate_yaml_front_matter(file_path, skills_manager)
    if issues:
        all_issues.extend(["[YAML] " + i for i in issues])
    else:
        print("  ✅ YAML valid")
    
    # 2. Broken links
    print("\n🔗 Checking for broken links...")
    issues = check_broken_links(file_path)
    if issues:
        all_issues.extend(["[LINKS] " + i for i in issues])
    else:
        print("  ✅ No broken links")
    
    # 3. Style checks
    print("\n✍️  Checking Economist style...")
    issues = check_economist_style(file_path)
    if issues:
        all_issues.extend(["[STYLE] " + i for i in issues])
    else:
        print("  ✅ Style checks passed")
    
    # Summary
    print(f"\n{'='*60}")
    if all_issues:
        print(f"❌ Found {len(all_issues)} issues:")
        for issue in all_issues:
            print(f"  • {issue}")
        return False
    else:
        print("✅ All checks passed!")
        return True


def validate_blog_structure(blog_dir, skills_manager=None):
    """Validate entire blog structure."""
    print(f"\n{'='*60}")
    print(f"Validating blog structure: {blog_dir}")
    print(f"{'='*60}\n")
    
    blog_path = Path(blog_dir)
    issues_found = 0
    
    # Check required directories
    required_dirs = ['_posts', '_layouts', 'assets']
    for dir_name in required_dirs:
        dir_path = blog_path / dir_name
        if not dir_path.exists():
            print(f"  ❌ Missing required directory: {dir_name}")
            issues_found += 1
        else:
            print(f"  ✅ {dir_name}")
    
    # Check _config.yml
    config_path = blog_path / '_config.yml'
    if config_path.exists():
        print(f"  ✅ _config.yml")
        
        # Validate Jekyll plugins configuration
        with open(config_path, 'r') as f:
            config_content = f.read()
            # Split on --- to handle multiple YAML documents and take first
            first_doc = config_content.split('\n---\n')[0]
            config_data = yaml.safe_load(first_doc)
            
        plugins = config_data.get('plugins', [])
        
        # Check for jekyll-seo-tag if {% seo %} is used
        default_layout = blog_path / '_layouts' / 'default.html'
        if default_layout.exists():
            with open(default_layout, 'r') as f:
                layout_content = f.read()
                if '{% seo %}' in layout_content and 'jekyll-seo-tag' not in plugins:
                    print(f"  ⚠️  Layout uses {{% seo %}} but jekyll-seo-tag not in plugins")
                    issues_found += 1
                    if skills_manager:
                        skills_manager.learn_pattern(
                            "jekyll_configuration",
                            "missing_seo_plugin",
                            {
                                "severity": "high",
                                "pattern": "Template uses {% seo %} but jekyll-seo-tag not enabled",
                                "check": "Verify jekyll-seo-tag in _config.yml plugins if {% seo %} used",
                                "learned_from": "Production issue: empty page titles"
                            }
                        )
    else:
        print(f"  ❌ _config.yml")
        issues_found += 1
    
    return issues_found
    if not config_path.exists():
        print(f"  ❌ Missing _config.yml")
    else:
        print(f"  ✅ _config.yml")
    
    # Validate all posts
    posts_dir = blog_path / '_posts'
    if posts_dir.exists():
        posts = list(posts_dir.glob('*.md')) + list(posts_dir.glob('*.markdown'))
        print(f"\n📄 Validating {len(posts)} posts...")
        
        failed_posts = []
        for post in posts:
            if not validate_post(post, blog_dir):
                failed_posts.append(post.name)
        
        if failed_posts:
            print(f"\n❌ {len(failed_posts)} posts failed validation:")
            for post_name in failed_posts:
                print(f"  • {post_name}")
            return False
    
    print(f"\n✅ Blog structure validation complete!")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate blog posts with self-learning skills')
    parser.add_argument('--blog-dir', required=True, help='Path to blog directory')
    parser.add_argument('--post', help='Specific post to validate (optional)')
    parser.add_argument('--show-skills', action='store_true', help='Show learned skills report')
    parser.add_argument('--learn', action='store_true', default=True, help='Enable learning from this run (default: true)')
    
    args = parser.parse_args()
    
    # Initialize skills manager
    skills_manager = SkillsManager()
    
    if args.show_skills:
        # Show skills report
        print(skills_manager.export_report())
        sys.exit(0)
    
    total_issues = 0
    
    if args.post:
        # Validate single post
        post_path = Path(args.post)
        if not post_path.is_absolute():
            post_path = Path(args.blog_dir) / args.post
        
        success = validate_post(post_path, args.blog_dir, skills_manager if args.learn else None)
        total_issues = 0 if success else 1
        
        if args.learn:
            skills_manager.record_run(total_issues)
            skills_manager.save()
            print(f"\n💡 Skills updated. Run with --show-skills to see learned patterns.")
        
        sys.exit(0 if success else 1)
    else:
        # Validate entire blog
        blog_dir = Path(args.blog_dir)
        
        # Validate structure with Jekyll config checks
        structure_issues = validate_blog_structure(blog_dir, skills_manager if args.learn else None)
        total_issues += structure_issues
        
        if structure_issues > 0:
            print(f"\n⚠️  Found {structure_issues} structural issues")
        
        # Validate all posts
        posts_dir = blog_dir / '_posts'
        if posts_dir.exists():
            posts = sorted(posts_dir.glob('*.md'))
            print(f"\n📄 Validating {len(posts)} posts...\n")
            
            failed_posts = []
            for post in posts:
                if not validate_post(post, blog_dir, skills_manager if args.learn else None):
                    failed_posts.append(post.name)
                    total_issues += 1
            
            if failed_posts:
                print(f"\n❌ {len(failed_posts)} posts failed validation:")
                for post_name in failed_posts:
                    print(f"  • {post_name}")
            else:
                print(f"\n✅ Blog structure validation complete!")
        
        if args.learn:
            skills_manager.record_run(total_issues, 0)
            skills_manager.save()
            print(f"\n💡 Skills updated. Total runs: {skills_manager.get_stats()['total_runs']}")
            print(f"   Run with --show-skills to see learned patterns.")
        
        sys.exit(0 if total_issues == 0 else 1)
        # Validate all posts
        posts = sorted((blog_dir / '_posts').glob('*.md'))
        print(f"\n📄 Validating {len(posts)} posts...\n")
        
        failed_posts = []
        for post in posts:
            if not validate_post(post, blog_dir, skills_manager if args.learn else None):
                failed_posts.append(post.name)
                total_issues += 1
        
        if failed_posts:
            print(f"\n❌ {len(failed_posts)} posts failed validation:")
            for post_name in failed_posts:
                print(f"  • {post_name}")
        else:
            print(f"\n✅ Blog structure validation complete!")
        
        if args.learn:
            skills_manager.record_run(total_issues, 0)
            skills_manager.save()
            print(f"\n💡 Skills updated. Total runs: {skills_manager.get_stats()['total_runs']}")
            print(f"   Run with --show-skills to see learned patterns.")
        
        sys.exit(0 if not failed_posts else 1)
