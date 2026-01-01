#!/usr/bin/env python3
"""
Sprint Discipline Validator

Enforces sprint planning and iteration discipline by validating:
1. Work aligns to active sprint stories
2. Progress is tracked in SPRINT.md
3. Sprint rules are followed
4. Retrospectives are completed

Usage:
    # Check before starting work
    python3 scripts/sprint_validator.py --check-before-work "Implement feature X"
    
    # Validate current sprint status
    python3 scripts/sprint_validator.py --validate-sprint
    
    # Check if sprint is complete
    python3 scripts/sprint_validator.py --check-sprint-complete
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
import json

class SprintValidator:
    """Validates sprint discipline and planning adherence"""
    
    def __init__(self, sprint_file: str = "SPRINT.md"):
        self.sprint_file = Path(sprint_file)
        self.skills_file = Path("skills/blog_qa_skills.json")
        self.violations = []
        
        if not self.sprint_file.exists():
            raise FileNotFoundError(f"Sprint file not found: {sprint_file}")
        
        with open(self.sprint_file, 'r') as f:
            self.sprint_content = f.read()
    
    def get_active_sprint(self) -> dict:
        """Extract active sprint information"""
        # Find which sprint is marked as active
        status_match = re.search(r'\*\*Active Sprint\*\*: Sprint (\d+)', self.sprint_content)
        if not status_match:
            return None
        
        active_sprint_num = int(status_match.group(1))
        
        # Find that sprint's section - match "## Sprint N:" with any text after
        sprint_match = re.search(
            rf'## Sprint {active_sprint_num}:\s*([^\(]+)(?:\([^\)]+\))?',
            self.sprint_content
        )
        if not sprint_match:
            return None
        
        sprint_name = sprint_match.group(1).strip()
        
        # Extract sprint goal
        goal_match = re.search(r'### Sprint Goal\n([^\n]+)', self.sprint_content)
        goal = goal_match.group(1) if goal_match else "Not defined"
        
        # Sprint is active (we already matched it above)
        is_active = True
        
        # Extract completed stories
        completed_match = re.search(r'\*\*Completed Stories\*\*: (\d+)/(\d+)', self.sprint_content)
        completed = int(completed_match.group(1)) if completed_match else 0
        total = int(completed_match.group(2)) if completed_match else 0
        
        # Extract story points
        points_match = re.search(r'\*\*Story Points Done\*\*: (\d+)/(\d+)', self.sprint_content)
        points_done = int(points_match.group(1)) if points_match else 0
        points_total = int(points_match.group(2)) if points_match else 0
        
        return {
            'number': active_sprint_num,
            'name': sprint_name,
            'goal': goal,
            'is_active': is_active,
            'completed_stories': completed,
            'total_stories': total,
            'points_done': points_done,
            'points_total': points_total
        }
    
    def get_sprint_stories(self) -> list:
        """Extract all stories from active sprint"""
        stories = []
        
        # Find story sections
        story_pattern = r'#### Story (\d+): ([^\n]+)\n\*\*Priority\*\*: ([^\n]+)\n\*\*Story Points\*\*: (\d+)'
        matches = re.finditer(story_pattern, self.sprint_content)
        
        for match in matches:
            story_num = int(match.group(1))
            title = match.group(2)
            priority = match.group(3)
            points = int(match.group(4))
            
            # Extract tasks
            story_section = self.sprint_content[match.end():match.end()+2000]
            task_matches = re.findall(r'- \[([ x])\] ([^\n]+)', story_section)
            
            tasks = []
            for checked, task_text in task_matches:
                tasks.append({
                    'text': task_text,
                    'completed': checked == 'x'
                })
            
            completed = all(t['completed'] for t in tasks) if tasks else False
            
            stories.append({
                'number': story_num,
                'title': title,
                'priority': priority,
                'points': points,
                'tasks': tasks,
                'completed': completed
            })
        
        return stories
    
    def check_before_work(self, work_description: str) -> bool:
        """Validate before starting new work"""
        print(f"🔍 Sprint Validator: Checking if '{work_description}' aligns with sprint...\n")
        
        # Check 1: Is there an active sprint?
        sprint = self.get_active_sprint()
        if not sprint or not sprint['is_active']:
            self.violations.append({
                'id': 'work_without_planning',
                'severity': 'critical',
                'message': f"No active sprint found. Create sprint plan before working on '{work_description}'",
                'action': "1. Open SPRINT.md\n2. Define sprint goal and stories\n3. Estimate story points\n4. Mark sprint as active"
            })
            return False
        
        print(f"✅ Active Sprint: Sprint {sprint['number']} - {sprint['name']}")
        print(f"   Goal: {sprint['goal']}\n")
        
        # Check 2: Does this work map to a sprint story?
        stories = self.get_sprint_stories()
        matching_story = None
        
        for story in stories:
            # Simple fuzzy match - check if key words overlap
            story_words = set(story['title'].lower().split())
            work_words = set(work_description.lower().split())
            overlap = story_words.intersection(work_words)
            
            if len(overlap) >= 2:  # At least 2 words match
                matching_story = story
                break
        
        if not matching_story:
            self.violations.append({
                'id': 'work_without_planning',
                'severity': 'critical',
                'message': f"'{work_description}' doesn't match any sprint story",
                'action': f"Add this work to sprint backlog:\n\n#### Story X: {work_description}\n**Priority**: P?\n**Story Points**: ?\n**Tasks**:\n- [ ] Define tasks\n\nOR wait until next sprint if not urgent."
            })
            return False
        
        print(f"✅ Matched to Story {matching_story['number']}: {matching_story['title']}")
        print(f"   Priority: {matching_story['priority']}")
        print(f"   Story Points: {matching_story['points']}")
        print(f"   Tasks: {len([t for t in matching_story['tasks'] if t['completed']])}/{len(matching_story['tasks'])} completed\n")
        
        # Check 3: Are acceptance criteria defined?
        story_section = self.sprint_content[self.sprint_content.find(matching_story['title']):]
        if '**Acceptance Criteria:**' not in story_section[:1000]:
            self.violations.append({
                'id': 'work_without_acceptance_criteria',
                'severity': 'high',
                'message': f"Story {matching_story['number']} lacks acceptance criteria",
                'action': "Define clear acceptance criteria before starting:\n- How will you know it's done?\n- What tests prove it works?\n- What's the definition of 'complete'?"
            })
            return False
        
        print(f"✅ Acceptance criteria defined\n")
        
        # Check 4: Story points estimated?
        if matching_story['points'] == 0:
            self.violations.append({
                'id': 'unestimated_work',
                'severity': 'medium',
                'message': f"Story {matching_story['number']} has no story point estimate",
                'action': "Estimate using scale: 1 (1hr), 2 (1-2hr), 3 (2-4hr), 5 (1day), 8 (2days)"
            })
            return False
        
        print(f"✅ Story estimated at {matching_story['points']} points\n")
        
        print("="*60)
        print("✅ ALL CHECKS PASSED - You're clear to start work!")
        print("="*60)
        print(f"\n📝 Remember to:")
        print(f"   1. Update task checkboxes in SPRINT.md as you progress")
        print(f"   2. Reference 'Story {matching_story['number']}' in commit messages")
        print(f"   3. Update sprint status when story is complete\n")
        
        return True
    
    def validate_sprint(self) -> bool:
        """Validate current sprint status and progress"""
        print("🔍 Sprint Validator: Checking sprint health...\n")
        
        sprint = self.get_active_sprint()
        if not sprint or not sprint['is_active']:
            print("❌ No active sprint found\n")
            return False
        
        print(f"Sprint {sprint['number']}: {sprint['name']}")
        print(f"Goal: {sprint['goal']}")
        print(f"Progress: {sprint['completed_stories']}/{sprint['total_stories']} stories ({sprint['points_done']}/{sprint['points_total']} points)\n")
        
        # Check stories
        stories = self.get_sprint_stories()
        
        for story in stories:
            status = "✅" if story['completed'] else "🔄"
            print(f"{status} Story {story['number']}: {story['title']} ({story['points']} pts)")
            
            incomplete_tasks = [t for t in story['tasks'] if not t['completed']]
            if incomplete_tasks and not story['completed']:
                print(f"   Tasks remaining: {len(incomplete_tasks)}")
                for task in incomplete_tasks[:3]:  # Show first 3
                    print(f"   - [ ] {task['text']}")
        
        print()
        
        # Check for violations
        if sprint['completed_stories'] == 0 and sprint['points_done'] == 0:
            print("⚠️  No progress yet on sprint - ensure work is starting\n")
        
        completion_rate = sprint['points_done'] / sprint['points_total'] if sprint['points_total'] > 0 else 0
        if completion_rate > 0.5:
            print(f"✅ Sprint on track: {int(completion_rate*100)}% complete\n")
        elif completion_rate > 0:
            print(f"⚠️  Sprint progress: {int(completion_rate*100)}% - may need to adjust scope\n")
        
        return True
    
    def check_sprint_complete(self) -> bool:
        """Check if sprint is ready to close"""
        print("🔍 Sprint Validator: Checking if sprint is complete...\n")
        
        sprint = self.get_active_sprint()
        stories = self.get_sprint_stories()
        
        all_complete = all(s['completed'] for s in stories)
        
        if not all_complete:
            print("❌ Sprint NOT complete - stories remaining:\n")
            for story in stories:
                if not story['completed']:
                    print(f"   Story {story['number']}: {story['title']}")
            print()
            return False
        
        print("✅ All stories complete!\n")
        
        # Check for retrospective
        if '## Sprint' in self.sprint_content and 'Retrospective' in self.sprint_content:
            retro_section = re.search(
                rf'### Sprint {sprint["number"]} Retrospective',
                self.sprint_content
            )
            
            if not retro_section:
                self.violations.append({
                    'id': 'skipped_retrospective',
                    'severity': 'high',
                    'message': f"Sprint {sprint['number']} lacks retrospective",
                    'action': "Document:\n1. What went well?\n2. What could improve?\n3. Action items for next sprint"
                })
                print("❌ Retrospective not completed\n")
                return False
        
        print("✅ Retrospective documented\n")
        print("="*60)
        print("🎉 SPRINT COMPLETE!")
        print("="*60)
        print("\nNext steps:")
        print("1. Archive sprint details")
        print("2. Calculate actual velocity")
        print("3. Plan next sprint\n")
        
        return True
    
    def report_violations(self):
        """Report any sprint discipline violations"""
        if not self.violations:
            return
        
        print("\n" + "="*60)
        print("⚠️  SPRINT DISCIPLINE VIOLATIONS")
        print("="*60 + "\n")
        
        for v in self.violations:
            print(f"❌ [{v['severity'].upper()}] {v['id']}")
            print(f"   {v['message']}\n")
            print(f"   ACTION REQUIRED:")
            for line in v['action'].split('\n'):
                print(f"   {line}")
            print()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate sprint discipline')
    parser.add_argument('--check-before-work', metavar='WORK_DESC',
                       help='Check if work aligns with sprint before starting')
    parser.add_argument('--validate-sprint', action='store_true',
                       help='Validate current sprint status')
    parser.add_argument('--check-sprint-complete', action='store_true',
                       help='Check if sprint is ready to close')
    
    args = parser.parse_args()
    
    try:
        validator = SprintValidator()
        
        if args.check_before_work:
            result = validator.check_before_work(args.check_before_work)
            validator.report_violations()
            sys.exit(0 if result else 1)
        
        elif args.validate_sprint:
            result = validator.validate_sprint()
            sys.exit(0 if result else 1)
        
        elif args.check_sprint_complete:
            result = validator.check_sprint_complete()
            validator.report_violations()
            sys.exit(0 if result else 1)
        
        else:
            parser.print_help()
            sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
