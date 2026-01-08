#!/bin/bash
# Full Blog Post Generation and Validation Workflow
# 
# This script orchestrates the complete pipeline:
# 1. Generate blog post (Scrum Master Agent)
# 2. Validate deployment readiness (Blog QA Agent)
# 3. Run E2E validation tests (Quality Enforcer)

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BLOG_DIR="${BLOG_DIR:-../economist-blog-v5}"  # Default blog directory
OUTPUT_DIR="${OUTPUT_DIR:-output}"
TOPIC="${TOPIC:-}"
TALKING_POINTS="${TALKING_POINTS:-}"
CATEGORY="${CATEGORY:-quality-engineering}"
AUTO_DISCOVER="${AUTO_DISCOVER:-false}"  # Set to 'true' to use Topic Scout Agent

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print info messages
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ══════0 (OPTIONAL): TOPIC DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

if [ "$AUTO_DISCOVER" = "true" ] && [ -z "$TOPIC" ]; then
    print_header "STAGE 0: TOPIC DISCOVERY (Topic Scout Agent)"
    
    print_info "Running Topic Scout Agent to discover high-value topics..."
    ./run.sh scripts/topic_scout.py
    
    if [ $? -ne 0 ]; then
        print_error "Topic discovery failed!"
        exit 1
    fi
    
    # Read top topic from content_queue.json
    if [ -f "content_queue.json" ]; then
            DISCOVERED_TOPIC=$(./run.sh -c "import json; data=json.load(open('content_queue.json')); print(data['topics'][0]['topic'])")
            DISCOVERED_POINTS=$(./run.sh -c "import json; data=json.load(open('content_queue.json')); print(data['topics'][0].get('talking_points', ''))")
        print_success "Discovered topic: $DISCOVERED_TOPIC"
        print_success "Talking points: $DISCOVERED_POINTS"
        
        export TOPIC="$DISCOVERED_TOPIC"
        export TALKING_POINTS="$DISCOVERED_POINTS"
    else
        print_error "content_queue.json not found after discovery"
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STAGE ═════════════════════════════════════════════════════════════════════
# STAGE 1: BLOG POST GENERATION
# ═══════════════════════════════════════════════════════════════════════════

print_header "STAGE 1: BLOG POST GENERATION (Scrum Master Agent)"

if [ -z "$TOPIC" ]; then
    print_warning "No TOPIC specified, using queued topic from content_queue.json"
else
    print_info "Topic: $TOPIC"
    export TOPIC
fi

if [ -n "$TALKING_POINTS" ]; then
    print_info "Talking Points: $TALKING_POINTS"
    export TALKING_POINTS
fi

print_info "Category: $CATEGORY"
export CATEGORY

print_info "Output Directory: $OUTPUT_DIR"
export OUTPUT_DIR

print_info "Running Scrum Master Agent to generate blog post..."
./run.sh scripts/economist_agent.py

if [ $? -ne 0 ]; then
    print_error "Blog post generation failed!"
    exit 1
fi

# Check if article was quarantined (validation failure)
QUARANTINE_DIR="$OUTPUT_DIR/quarantine"
if [ -d "$QUARANTINE_DIR" ]; then
    LATEST_QUARANTINED=$(ls -t "$QUARANTINE_DIR"/*.md 2>/dev/null | head -1)
    if [ -n "$LATEST_QUARANTINED" ]; then
        # Find most recent non-quarantine article to compare timestamps
        LATEST_SUCCESS=$(ls -t "$OUTPUT_DIR"/*.md 2>/dev/null | grep -v "review.md" | grep -v "/quarantine/" | head -1)
        
        # If quarantine is newer than last success (or no success exists), generation failed
        if [ -z "$LATEST_SUCCESS" ] || [ "$LATEST_QUARANTINED" -nt "$LATEST_SUCCESS" ]; then
            print_error "Article QUARANTINED due to validation failure!"
            print_error "Article: $(basename $LATEST_QUARANTINED)"
            
            # Show validation report if exists
            VALIDATION_REPORT="${LATEST_QUARANTINED%.md}-VALIDATION-FAILED.txt"
            if [ -f "$VALIDATION_REPORT" ]; then
                print_warning "Validation report:"
                cat "$VALIDATION_REPORT"
            fi
            
            print_error "Fix validation issues and regenerate article"
            exit 1
        fi
    fi
fi

print_success "Blog post generated successfully!"

# Find the most recent article (excluding quarantine)
LATEST_ARTICLE=$(ls -t "$OUTPUT_DIR"/*.md 2>/dev/null | grep -v "review.md" | grep -v "/quarantine/" | head -1)

if [ -z "$LATEST_ARTICLE" ]; then
    print_error "No article found in $OUTPUT_DIR"
    exit 1
fi

print_success "Generated article: $LATEST_ARTICLE"

# ═══════════════════════════════════════════════════════════════════════════
# STAGE 2: DEPLOYMENT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

print_header "STAGE 2: DEPLOYMENT VALIDATION (Blog QA Agent)"

# Check if blog directory exists
if [ ! -d "$BLOG_DIR" ]; then
    print_warning "Blog directory not found: $BLOG_DIR"
    print_warning "Skipping Blog QA validation (optional)"
    print_info "To enable, set BLOG_DIR=/path/to/your/blog"
else
    print_info "Blog Directory: $BLOG_DIR"
    print_info "Running Blog QA Agent for Jekyll validation..."
    
    # Copy article to blog's _posts directory for validation
    BLOG_POSTS_DIR="$BLOG_DIR/_posts"
    if [ -d "$BLOG_POSTS_DIR" ]; then
        cp "$LATEST_ARTICLE" "$BLOG_POSTS_DIR/"
        BLOG_ARTICLE="$BLOG_POSTS_DIR/$(basename $LATEST_ARTICLE)"
        print_success "Copied article to blog: $BLOG_ARTICLE"
        
        ./run.sh scripts/blog_qa_agent.py --blog-dir "$BLOG_DIR" --post "$BLOG_ARTICLE" --learn
        
        if [ $? -ne 0 ]; then
            print_error "Blog QA validation failed!"
            print_warning "Article copied to blog but has validation issues"
            exit 1
        fi
        
        print_success "Blog QA validation passed!"
    else
        print_warning "_posts directory not found in blog, skipping copy"
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# STAGE 3: END-TO-END VALIDATION
# ═══════════════════════════════════════════════════════════════════════════

print_header "STAGE 3: END-TO-END VALIDATION (Quality Enforcer)"

print_info "Running integration test suite..."
pytest scripts/test_agent_integration.py -v --tb=short

if [ $? -ne 0 ]; then
    print_error "Integration tests failed!"
    exit 1
fi

print_success "Integration tests passed!"

# ═══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

print_header "WORKFLOW COMPLETE ✅"

echo -e "${GREEN}Generated Article:${NC} $LATEST_ARTICLE"
echo -e "${GREEN}Output Directory:${NC} $OUTPUT_DIR"

if [ -d "$BLOG_DIR" ]; then
    echo -e "${GREEN}Blog Directory:${NC} $BLOG_DIR"
fi

echo ""
print_success "All stages completed successfully!"
print_info "Article is ready for publication"

# Optional: Show article preview
echo ""
read -p "Show article preview? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_header "ARTICLE PREVIEW"
    head -n 50 "$LATEST_ARTICLE"
    echo ""
    print_info "Showing first 50 lines. View full article: cat $LATEST_ARTICLE"
fi

exit 0
