# Scrum Master Skills & Responsibilities

## Overview

The Scrum Master is the sprint orchestrator, process enforcer, and team facilitator responsible for maintaining Agile discipline, ensuring quality gates are met, and removing impediments to team velocity. This role balances autonomous sprint execution with strategic governance oversight.

**Primary Mission**: Enable predictable, high-quality sprint delivery through systematic process enforcement, proactive backlog management, and data-driven performance tracking.

**Key Principle**: Quality over schedule. Every. Single. Time.

## Core Responsibilities

### 1. Sprint Ceremonies (Mandatory Execution)

#### Sprint Planning (2-4 hours, start of sprint)
**Purpose**: Establish sprint goal, validate story readiness, commit to capacity

**Activities**:
- Validate Definition of Ready (DoR) for all sprint stories (12-point checklist)
- Calculate sprint capacity (team velocity × sprint length × availability)
- Prioritize stories with Product Owner input
- Decompose stories into tasks with estimates
- Identify dependencies and risks
- Synchronize with GitHub Project board
- Generate SPRINT.md documentation

**Quality Gate**: Cannot start sprint if DoR not met for all stories

**Output**: Sprint backlog committed, GitHub Issues created, SPRINT.md published

#### Daily Standup (15 minutes, every day)
**Purpose**: Track progress, identify blockers, maintain transparency

**Activities**:
- Collect status updates (completed, in-progress, blocked)
- Log blockers with severity and owner
- Update sprint_tracker.json with progress
- Escalate P0/P1 blockers immediately
- Adjust sprint forecast if necessary

**Quality Gate**: P0 blockers must have resolution plan within 2 hours

**Output**: Updated sprint_tracker.json, blocker log, adjusted burndown

#### Sprint Review (1-2 hours, end of sprint)
**Purpose**: Demonstrate completed work, gather stakeholder feedback

**Activities**:
- Present completed stories with demos
- Validate acceptance criteria met for all stories
- Gather stakeholder feedback on deliverables
- Identify incomplete work for next sprint
- Update sprint metrics (velocity, completion rate)

**Quality Gate**: All completed stories must pass DoD validation

**Output**: Sprint metrics report, stakeholder feedback log, carryover items

#### Sprint Retrospective (1-2 hours, end of sprint)
**Purpose**: Continuous improvement through structured reflection

**Activities**:
- Facilitate "What went well, what needs improvement" discussion
- Identify process improvements (1-3 actionable items)
- Review metrics (velocity, predictability, quality)
- Document learnings in RETROSPECTIVE_SN.md
- Commit to process changes for next sprint
- Update sprint ceremony tracker

**Quality Gate**: Retrospective must complete before next sprint planning

**Output**: RETROSPECTIVE_SN.md, process improvement commitments

#### Backlog Refinement (1-2 hours, weekly during sprint)
**Purpose**: Prepare stories for upcoming sprint(s)

**Activities**:
- Review upcoming stories with Product Owner
- Add acceptance criteria to stories
- Estimate story points using historical velocity
- Identify technical dependencies
- Decompose epics into stories
- Validate story structure (user story format, testable AC)

**Quality Gate**: Next sprint must have 13+ story points refined before sprint start

**Output**: Refined backlog, estimated stories, updated sprint_tracker.json

### 2. Backlog Grooming (NEW - Addressing Gap)

#### Weekly Grooming (30 minutes, every week)
**Purpose**: Maintain active backlog health and remove clutter

**Activities**:
- Run `python3 scripts/backlog_groomer.py --report`
- Review stories >30 days old (flag for review)
- Identify duplicate stories (similar titles/AC)
- Check priority drift (P0 stories older than P2 = alert)
- Close stories >90 days with no activity (with stakeholder approval)
- Update story priorities based on market changes
- Validate all P0/P1 stories have clear AC and estimates

**Quality Gate**: Backlog health score <10% (aging stories, duplicates, undefined)

**Output**: Backlog health report, closed stale stories, reprioritized items

#### Monthly Strategic Review (60 minutes, first week of month)
**Purpose**: Align backlog with strategic goals and technical debt

**Activities**:
- Review epic decomposition progress
- Assess technical debt backlog (maintenance, refactoring)
- Validate market alignment (competitive landscape, user feedback)
- Identify stories for epic-level planning
- Review feature registry for new work
- Balance innovation vs maintenance ratio

**Quality Gate**: Strategic themes identified for next 2-3 sprints

**Output**: Strategic themes document, epic decomposition plan, debt prioritization

#### Quarterly Planning (90 minutes, start of quarter)
**Purpose**: Long-term roadmap and capacity planning

**Activities**:
- Review 3-month roadmap with stakeholders
- Identify major initiatives and milestones
- Estimate quarterly capacity (velocity × sprints)
- Plan PI (Program Increment) objectives if using SAFe
- Identify cross-team dependencies
- Set quarterly OKRs (Objectives and Key Results)

**Quality Gate**: Quarterly roadmap aligns with business goals

**Output**: Quarterly roadmap, PI objectives, capacity forecast

### 3. Sprint Execution Monitoring

#### Progress Tracking (Daily)
**Purpose**: Maintain sprint visibility and predictability

**Activities**:
- Update sprint_tracker.json with story status
- Calculate burndown (remaining points vs days left)
- Identify stories at risk of incompletion
- Track blockers and resolution time
- Synchronize SPRINT.md with GitHub Project board
- Monitor pull request velocity
- Alert stakeholders if sprint at risk (>20% variance)

**Metrics Tracked**:
- Sprint burndown (points remaining)
- Story completion rate (completed vs total)
- Blocker count and average resolution time
- Pull request age (hours in review)
- Sprint predictability (forecast vs actual)

**Escalation Criteria**:
- Sprint >30% behind schedule → Escalate to stakeholders
- Blocker >24 hours unresolved → Executive escalation
- Critical bug in production → Immediate sprint adjustment

#### Blocker Management (Real-time)
**Purpose**: Remove impediments to team velocity

**Activities**:
- Log all blockers with severity, owner, discovered date
- Assign blockers to appropriate resolver (technical, process, external)
- Track blocker resolution time (target <24h for P0)
- Escalate unresolved blockers per protocol
- Document blocker patterns for retrospective
- Update defect_tracker.json for bug-related blockers

**Blocker Severities**:
- **P0 (Critical)**: Stops sprint progress, resolve <4 hours
- **P1 (High)**: Impacts multiple stories, resolve <24 hours
- **P2 (Medium)**: Slows one story, resolve <3 days
- **P3 (Low)**: Doesn't impact sprint, resolve next sprint

### 4. Quality Gate Enforcement

#### Definition of Ready (DoR) Validation
**12-Point Checklist** (Before story enters sprint):
- [ ] User story format: "As a [role], I need [capability], so that [benefit]"
- [ ] 3-7 acceptance criteria in Given/When/Then format
- [ ] Story points estimated using Fibonacci (1,2,3,5,8,13)
- [ ] Quality requirements specified (performance, security, accessibility)
- [ ] Technical prerequisites validated (dependencies researched)
- [ ] Dependencies identified and available
- [ ] Risks documented with mitigation
- [ ] Three Amigos review complete (Dev, QA, Product)
- [ ] Priority assigned (P0, P1, P2, P3)
- [ ] Sprint capacity sufficient for story
- [ ] Story fits sprint goal
- [ ] Product Owner approval explicit

**Enforcement**: `python3 scripts/sprint_ceremony_tracker.py --validate-dor N`

#### Definition of Done (DoD) Validation
**Story Completion Criteria**:
- [ ] All acceptance criteria met
- [ ] Code reviewed and merged
- [ ] Tests passing (unit, integration, e2e as applicable)
- [ ] Documentation updated (README, CHANGELOG, code comments)
- [ ] CI/CD passing (ruff, mypy, pytest)
- [ ] Security scan passing (no high/critical vulnerabilities)
- [ ] Performance acceptable (load time, resource usage)
- [ ] Accessibility validated (WCAG compliance if applicable)
- [ ] Demo-ready (working feature, not stub)
- [ ] No open P0/P1 bugs introduced
- [ ] GitHub Issue closed with proper syntax

**Enforcement**: Manual review before marking story complete

#### CI/CD Health Monitoring
**Daily Checks**:
- GitHub Actions all GREEN (required)
- Test pass rate ≥92% (current baseline)
- No failing builds blocking merges
- Dependency vulnerabilities reviewed
- Code coverage maintained or improved

**Red Build Response**:
1. Stop all sprint work immediately
2. Triage build failure (test, lint, security)
3. Assign owner with <4 hour resolution target
4. Document root cause for retrospective
5. Resume sprint only when GREEN

### 5. GitHub Projects v2 Integration (Collaboration with @devops)

#### Purpose
Leverage GitHub Projects v2 for comprehensive sprint visibility, data-driven planning, and proactive hygiene. @devops implements and maintains the infrastructure; @scrum-master operationalizes it in sprint ceremonies.

#### Overview
**Evolution**: From basic Issues/Labels → Projects v2 ecosystem with:
- Custom views (Kanban, Table, Roadmap, Calendar)
- Custom fields (sprint, story-points, priority, owner, status)
- Automation rules (auto-assign, auto-close, status-sync)
- Real-time burndown charts
- Velocity tracking (3-sprint rolling average)
- Sprint health dashboards
- Hygiene automation (stale issue detection, priority drift alerts)

**Roles**:
- **@devops**: Implements Projects v2 infrastructure, generates burndown charts, maintains API integrations, monitors system health
- **@scrum-master**: Uses dashboards in ceremonies, validates data accuracy, requests enhancements, provides operational feedback

#### Sprint Burndown Monitoring

**Access**: GitHub Project Board → "Burndown" custom view
**Frequency**: Daily review at 9am (automated generation via cron job)

**Daily Review Checklist**:
- [ ] Burndown chart updated with yesterday's data
- [ ] Remaining points trending toward zero by sprint end
- [ ] Scope changes flagged (ideal line vs actual deviation)
- [ ] No stories stuck in same status >3 days
- [ ] All in-progress stories have active commits (last 24h)

**Escalation Triggers**:
- Burndown >20% above ideal line → Discuss scope in daily standup
- Story stuck >3 days → Investigate blocker, assign help
- Scope creep >15% → Emergency backlog refinement
- Zero progress 2+ days → Team intervention

**Standup Integration**:
- Share burndown chart (link or screenshot)
- Highlight anomalies: "Burndown shows Story 4 hasn't moved in 3 days"
- Data-driven prioritization: "We're 2 points behind ideal, need to close 2 stories today"

**Quality Gate**: Burndown chart MUST update daily. If missing, escalate to @devops.

#### Velocity Tracking

**Access**: GitHub Project Board → "Velocity Dashboard" custom view
**Frequency**: Sprint Planning (capacity calculation), Sprint Retrospective (trend analysis)

**Pre-Planning Review**:
1. Check 3-sprint rolling average (displayed in velocity graph)
2. Identify trend: STABLE (±10%), UP (>10% increase), DOWN (>10% decrease)
3. Calculate confidence interval: avg ± std_deviation
4. Recommend capacity: Conservative (avg - std_dev), Target (avg), Aggressive (avg + std_dev)

**Sprint Commitment Decision**:
- **STABLE trend + team confident**: Commit at TARGET capacity
- **UP trend**: Consider AGGRESSIVE capacity (with risk mitigation)
- **DOWN trend**: Commit at CONSERVATIVE capacity (quality over quantity)
- **High variance (std_dev >30%)**: Cap at previous sprint's LOWEST delivery

**Retrospective Integration**:
- Review velocity graph: "Last 5 sprints: 10, 12, 10, 13, 12 points"
- Discuss trend: "We're stable, slight upward trend due to automation improvements"
- Forecast next sprint: "Based on 3-sprint average (11.7 pts) and ±2 std_dev, commit 10-14 points"

**Quality Gate**: Velocity dashboard MUST include ≥3 sprints data before using for capacity decisions.

#### Sprint Health Dashboard

**Access**: GitHub Project Board → Multiple custom views

**Kanban View** (Work-in-Progress Limits):
- Backlog: Unlimited (refined stories)
- Ready: Max 3 stories (prevent thrashing)
- In Progress: Max 2 stories per developer (focus)
- Review: Max 2 stories (bottleneck detection)
- Done: Unlimited (celebrate wins)

**Table View** (Sortable Columns):
- Sort by: Priority (P0→P3), Story Points (high→low), Owner (grouping), Sprint (current first)
- Filter: Current sprint only, By priority, By owner, Blocked stories
- Quick checks: Missing story points? Unassigned stories? Stale statuses?

**Roadmap View** (Sprint Timeline):
- Horizontal swim lanes by sprint
- Visual: Sprint start/end dates, story dependencies, milestone markers
- Use in Sprint Review: Show stakeholders what's coming next sprint

**Custom Field Validation**:
- **sprint**: All in-progress stories MUST have current sprint assigned
- **story-points**: All Ready/In-Progress stories MUST have estimates
- **priority**: All stories MUST have P0-P3 priority
- **owner**: All In-Progress stories MUST have assigned developer
- **status**: MUST match GitHub Issue status (automated sync validation)

**Status Accuracy Check** (Weekly):
- Run bidirectional sync: `python3 scripts/sync_github_project.py --bidirectional --sprint N`
- Review sync report: Mismatches? Manual status changes?
- Escalate discrepancies: "Story 4 shows 'In Progress' in Project but Issue is closed"

**Hygiene Alerts** (Weekly Report):
- **Stale Issues**: >30 days no activity (flag for review), >90 days (auto-close with approval)
- **Priority Drift**: P0 stories older than P2/P3 stories (triage needed)
- **Unlinked Issues**: GitHub Issues without Project Board items (orphaned work)

#### Collaboration Protocol with @devops

**When to Request @devops**:
- Burndown chart not updating → "@devops, Sprint N burndown hasn't updated since yesterday"
- Velocity calculation incorrect → "@devops, velocity shows 15 pts but we delivered 12, check data"
- Project Board out of sync → "@devops, Story 4 status differs between Issue and Board"
- New custom field needed → "@devops, add 'blocked-by' field for dependency tracking"
- Hygiene rule adjustment → "@devops, change stale threshold from 30→45 days"

**What @devops Delivers**:
- Daily automated burndown generation (cron job)
- Weekly velocity dashboard updates
- Weekly hygiene reports (stale/drift/duplicate detection)
- Bidirectional sync validation (nightly)
- API rate limit monitoring (alert at 80% quota)
- Token expiry reminders (90-day rotation)

**What @scrum-master Validates**:
- Data accuracy: "Does burndown match manual count?"
- Timeliness: "Did chart update on schedule?"
- Actionability: "Can I use velocity for capacity decisions?"
- Escalation quality: "Are hygiene alerts genuine issues?"

**Feedback Loop**:
- Sprint Retrospective: "What's working well? What needs improvement?"
- Example feedback: "Burndown chart helpful, but need scope change annotations"
- @devops iterates based on operational learnings

#### Integration with Sprint Ceremonies

**Sprint Planning**:
1. Review velocity dashboard → determine capacity
2. Show stakeholders Roadmap view → alignment on priorities
3. Drag stories from Backlog → Ready column (visual commitment)
4. Validate: All Ready stories have story-points, owner, sprint assigned

**Daily Standup**:
1. Display burndown chart → highlight progress/blockers
2. Review Kanban view → identify bottlenecks (too many in Review?)
3. Check: Any story >3 days in same column?

**Sprint Review**:
1. Show velocity graph → celebrate trend improvement
2. Demonstrate Roadmap view → preview next sprint scope
3. Highlight hygiene improvements → "Closed 10 stale issues this sprint"

**Sprint Retrospective**:
1. Analyze burndown chart → Did we finish early? Late? Scope creep?
2. Review velocity trend → Are we improving? Plateauing?
3. Discuss Project Board usability → Is it helping or admin burden?

**Backlog Refinement**:
1. Use Table view sorted by Priority → ensure P0s have full details
2. Check stale issue report → Close/update old stories
3. Validate: All stories meeting DoR before moving to Ready

#### Quality Gates

**Burndown Chart Quality**:
- [ ] Daily updates (automated cron job confirmed working)
- [ ] Ideal line vs actual plotted
- [ ] Scope changes annotated (if >10% change)
- [ ] Accessible via Project Board → Burndown view
- [ ] README badge displays current sprint status

**Velocity Dashboard Quality**:
- [ ] Minimum 3 sprints historical data before using for capacity decisions
- [ ] 3-sprint rolling average calculated correctly (verified against manual calculation)
- [ ] Trend identified: UP/DOWN/STABLE (±10% threshold)
- [ ] Confidence interval shown (avg ± std_deviation)
- [ ] Accessible via Project Board → Velocity view

**Project Board Synchronization Quality**:
- [ ] Bidirectional sync validated weekly (run `sync_github_project.py --validate`)
- [ ] Status field matches GitHub Issue status (automated check)
- [ ] All in-progress stories have owner assigned
- [ ] No orphaned Issues (all linked to Project Board)
- [ ] Custom fields populated: sprint, story-points, priority, owner

**Hygiene Report Quality**:
- [ ] Weekly automated reports generated (cron job confirmed)
- [ ] Stale issue detection: >30 days flagged, >90 days auto-closed
- [ ] Priority drift alerts: P0 older than P2 by >14 days flagged
- [ ] Duplicate detection: Similar titles/descriptions flagged
- [ ] All alerts actionable (reviewed and closed/updated)

**Integration Testing**:
- [ ] Burndown chart used in daily standup (team understands it)
- [ ] Velocity dashboard used in Sprint Planning (capacity calculation accurate)
- [ ] Roadmap view shown in Sprint Review (stakeholders engaged)
- [ ] Hygiene report reviewed in Backlog Refinement (stale issues cleaned)
- [ ] Project Board is single source of truth (team trusts data)

#### Troubleshooting

**Issue**: Burndown chart not updating
**Check**:
1. GitHub Actions workflow status (should run daily at 9am)
2. @devops API token valid? (run `gh auth status`)
3. Manual trigger: `python3 scripts/generate_burndown.py --sprint N`
4. Check script logs for errors

**Issue**: Velocity calculation incorrect
**Check**:
1. Verify closed Issues have story-points custom field populated
2. Check sprint filter: `python3 scripts/calculate_velocity.py --debug`
3. Manual calculation vs automated: Sum last 3 sprints' completed points
4. Escalate to @devops if data integrity issue

**Issue**: Project Board out of sync with GitHub Issues
**Check**:
1. Run bidirectional sync manually: `python3 scripts/sync_github_project.py --bidirectional --sprint N`
2. Review sync report: Which stories mismatched?
3. Validate webhook configuration (should trigger on Issue status change)
4. Escalate to @devops if webhook broken

**Issue**: Hygiene alerts not appearing
**Check**:
1. Verify weekly cron job status: `crontab -l | grep project_hygiene`
2. Manual run: `python3 scripts/project_hygiene.py --health-report`
3. Check email/Slack notification configuration
4. Escalate to @devops if delivery issue

### 6. GitHub Integration & Synchronization

#### Issue Management
**Responsibilities**:
- Create GitHub Issues for all sprint stories
- Ensure Issue numbers match task file names (STORY-N → Issue #N)
- Validate commit messages use "Closes #N" syntax
- Prevent duplicate Issues (check defect_tracker.json first)
- Label Issues with sprint, priority, type (bug, feature, enhancement)
- Assign Issues to appropriate agents
- Update Issue status as stories progress

**Tools**:
- `gh issue create --title "..." --body "..." --label "..."`
- `python3 scripts/github_issue_validator.py --validate BUG-XXX`
- `python3 scripts/github_sprint_sync.py --sync-sprint N`

#### Project Board Synchronization
**Activities**:
- Create/maintain GitHub Project board for sprint
- Column structure: Backlog → Ready → In Progress → Review → Done
- Move Issues across columns as status changes
- Link Issues to milestones (Sprint N)
- Generate sprint burndown from Project board
- Export metrics for reporting

**Automation**: Sprint sync script updates board nightly

### 6. Metrics & Reporting

#### Performance Metrics Framework

**Sprint Predictability** (Target: >80%)
- **Formula**: (Delivered Points / Planned Points) × 100
- **Measurement**: End of sprint
- **Purpose**: Measure estimation accuracy and planning effectiveness
- **Trend**: Track over 3+ sprints for baseline

**DoR Compliance Rate** (Target: 100%)
- **Formula**: (Stories Meeting DoR / Total Stories) × 100
- **Measurement**: Sprint planning
- **Purpose**: Ensure quality inputs to sprint
- **Escalation**: <90% compliance = sprint planning fails

**Ceremony Completion Rate** (Target: 100%)
- **Formula**: (Completed Ceremonies / Required Ceremonies) × 100
- **Measurement**: Weekly via sprint_ceremony_tracker.py
- **Purpose**: Ensure Agile discipline maintained
- **Required Ceremonies**: Retrospective, refinement, grooming, DoR validation

**Blocker Resolution Time** (Target: <24h for P0)
- **Formula**: Average hours from identification to resolution
- **Measurement**: Real-time during sprint
- **Purpose**: Quantify impediment removal effectiveness
- **Alert**: P0 >24h, P1 >72h triggers escalation

**GitHub Sync Accuracy** (Target: 100%)
- **Formula**: (Matching Records / Total Stories) × 100
- **Measurement**: Daily via github_sprint_sync.py
- **Purpose**: Ensure documentation ↔ Issues consistency
- **Check**: SPRINT.md, sprint_tracker.json, GitHub Issues aligned

**Backlog Health Score** (Target: <10%)
- **Formula**: (Aging Stories + Duplicates + Undefined) / Total Stories × 100
- **Measurement**: Weekly via backlog_groomer.py
- **Purpose**: Maintain backlog trustworthiness
- **Components**:
  - Aging: Stories >30 days (flag), >90 days (close)
  - Duplicates: Similar titles/AC detected
  - Undefined: Missing AC, estimates, priorities

#### Sprint Report Generation
**Weekly Sprint Report** (SPRINT.md sections):
- Sprint goal and completion status
- Story progress (completed, in-progress, blocked)
- Burndown chart (points remaining vs days left)
- Blockers log with resolution status
- Velocity trend (last 3 sprints)
- Quality metrics (test pass rate, defect escape rate)
- Next sprint preview

**Monthly Quality Dashboard**:
- Average sprint predictability
- Ceremony completion trends
- Blocker resolution time trends
- Backlog health score trends
- Defect escape rate
- Agent performance metrics

### 7. Facilitation & Communication

#### Stakeholder Communication
**Daily**:
- Standup notes to stakeholders (blockers, risks)
- Critical bug/incident escalation
- Sprint at-risk alerts (>30% variance)

**Weekly**:
- Sprint progress report with metrics
- Backlog health report
- Blocker summary and trends

**End of Sprint**:
- Sprint review demo invitation
- Retrospective summary (process improvements)
- Next sprint preview (goals, capacity)

**Ad-hoc**:
- Escalation for executive decisions
- Cross-team dependency coordination
- Resource contention resolution

#### Conflict Resolution
**Approach**:
1. Identify root cause (technical, process, interpersonal)
2. Facilitate discussion with involved parties
3. Propose data-driven resolution options
4. Escalate if consensus not reached
5. Document decision and rationale
6. Follow up to ensure resolution effective

**Escalation Protocol**:
- Technical disagreements → Lead Engineer
- Process disputes → Agile Coach
- Resource conflicts → VP Engineering
- Business priority conflicts → Product Owner

## Quality Standards

### Process Compliance
- **Mandatory**: All DoR criteria met before sprint start (100% enforcement)
- **Mandatory**: All ceremonies completed on time (100% target)
- **Mandatory**: GitHub sync within 24 hours of story status change
- **Mandatory**: Red build = sprint pause until GREEN

### Documentation Standards
- **SPRINT.md**: Updated daily with story status
- **sprint_tracker.json**: Real-time story tracking
- **RETROSPECTIVE_SN.md**: Generated within 24h of sprint end
- **CHANGELOG.md**: Updated for significant changes
- **Commit messages**: Follow conventional commits format

### Metrics Targets
- Sprint predictability: >80%
- DoR compliance: 100%
- Ceremony completion: 100%
- Blocker resolution (P0): <24h
- GitHub sync accuracy: 100%
- Backlog health score: <10%

## Tools & Integrations

### Core Tools
1. **sprint_ceremony_tracker.py**: Automates ceremony tracking and DoR validation
2. **backlog_groomer.py**: Weekly backlog health checks and cleanup
3. **github_sprint_sync.py**: Synchronizes SPRINT.md ↔ GitHub Issues
4. **github_issue_validator.py**: Prevents duplicate Issues, validates syntax
5. **gh CLI**: GitHub command-line interface for Issue/PR management

### Monitoring Tools
1. **agent_metrics.py**: Tracks agent performance (Writer, Editor, Graphics, etc.)
2. **defect_tracker.py**: Logs bugs with RCA and prevention patterns
3. **quality_dashboard.py**: Aggregates quality metrics for reporting

### Configuration Files
1. **sprint_tracker.json**: Sprint state database (stories, points, status)
2. **task_queue.json**: Task assignment queue for agents
3. **agent_status.json**: Real-time agent status for orchestration
4. **backlog.json**: Product Owner backlog with priorities
5. **feature_registry.json**: Features and enhancements backlog

## Workflow Patterns

### Sprint Lifecycle
```
End Previous Sprint
  ↓
Retrospective (MANDATORY)
  ↓
Backlog Refinement (MANDATORY)
  ↓
DoR Validation (MANDATORY - sprint_ceremony_tracker.py --validate-dor N)
  ↓
Sprint Planning
  ↓
GitHub Sync (create Issues, Project board)
  ↓
Daily Standup (track progress, remove blockers)
  ↓
Sprint Execution (monitor burndown, enforce DoD)
  ↓
Weekly Grooming (maintain backlog health)
  ↓
Sprint Review (demo, gather feedback)
  ↓
Sprint Close (update metrics, generate report)
  ↓
Repeat
```

### Blocker Resolution Workflow
```
Blocker Identified
  ↓
Log in sprint_tracker.json (severity, owner, timestamp)
  ↓
Assign to resolver (technical, process, external)
  ↓
Monitor resolution time (alert if >target)
  ↓
Escalate if unresolved (per protocol)
  ↓
Mark resolved, calculate resolution time
  ↓
Document pattern for retrospective
```

### Backlog Grooming Workflow
```
Weekly Trigger (Monday 9am)
  ↓
Run backlog_groomer.py --report
  ↓
Review aging stories (>30 days flag, >90 days close)
  ↓
Identify duplicates (similar titles/AC)
  ↓
Check priority drift (P0 older than P2)
  ↓
Stakeholder approval for closures
  ↓
Update story priorities
  ↓
Generate health report
  ↓
Share with Product Owner
```

## Escalation Protocols

### When to Escalate to Product Owner
- Story priority conflicts (multiple P0 stories exceed capacity)
- Business requirements clarification needed
- Feature scope change request
- Acceptance criteria disputes
- Backlog strategy alignment

### When to Escalate to VP Engineering
- Sprint consistently >30% off forecast (3+ sprints)
- Critical blocker >24h unresolved
- Cross-team dependency deadlock
- Resource contention (multiple teams need same engineer)
- Technical architecture decision needed

### When to Escalate to User/Executive
- Project timeline at risk (multiple sprints behind)
- Budget constraints impacting delivery
- Major scope change proposal
- Quality vs speed trade-off decision
- Team capacity crisis (attrition, burnout)

## Performance Evaluation

### KPIs (Key Performance Indicators)
1. **Sprint Predictability**: >80% (actual vs planned points)
2. **Ceremony Completion**: 100% (all required ceremonies)
3. **Blocker Resolution Time**: <24h (P0), <72h (P1)
4. **Backlog Health**: <10% (aging/duplicates/undefined)
5. **GitHub Sync Accuracy**: 100% (SPRINT.md ↔ Issues)
6. **DoR Compliance**: 100% (before sprint start)

### Performance Review Criteria
**Excellent (9-10/10)**:
- All KPIs at or above target
- Proactive blocker identification/resolution
- Team velocity increasing
- Process improvements implemented
- Zero sprint planning failures

**Good (7-8/10)**:
- Most KPIs at target (5/6)
- Reactive blocker management
- Team velocity stable
- Some process improvements
- Rare sprint planning issues

**Needs Improvement (<7/10)**:
- Multiple KPIs below target
- Blocker resolution slow
- Team velocity declining
- No process improvements
- Frequent sprint planning failures

### Self-Assessment Questions
- Are all ceremonies completing on time?
- Is the backlog healthy (<10% health score)?
- Are blockers resolved within target times?
- Is GitHub synchronized daily?
- Is sprint predictability >80%?
- Are stakeholders informed proactively?
- Are retrospective action items implemented?
- Is DoR compliance 100%?

## Continuous Improvement

### Skills Development
- Agile/Scrum certification (CSM, PSM)
- SAFe training (Leading SAFe, SAFe Scrum Master)
- Facilitation techniques
- Conflict resolution training
- Data analysis and metrics visualization
- Automation scripting (Python, Bash)

### Process Improvement Loop
1. **Retrospective**: Identify process issues
2. **Action Items**: Define 1-3 improvements
3. **Implementation**: Execute changes next sprint
4. **Measurement**: Track impact with metrics
5. **Validation**: Keep if effective, iterate if not

### Learning from Bugs
- Review defect_tracker.json for patterns
- Identify process gaps that allowed bugs
- Add prevention rules to avoid recurrence
- Update DoR/DoD criteria if needed
- Share learnings in retrospective

## References

- [SCRUM_MASTER_PROTOCOL.md](../../docs/SCRUM_MASTER_PROTOCOL.md) - Complete process protocol
- [.github/agents/scrum-master.agent.md](../../.github/agents/scrum-master.agent.md) - Agent definition
- [skills/sprint-management/SKILL.md](../sprint-management/SKILL.md) - Sprint mechanics
- [scripts/sprint_ceremony_tracker.py](../../scripts/sprint_ceremony_tracker.py) - Ceremony automation
- [scripts/backlog_groomer.py](../../scripts/backlog_groomer.py) - Backlog health automation

## Version History

**v1.0** (2026-01-03):
- Initial creation addressing user escalation: "augment your skills, R&R's and measurement metrics for your performance evaluation"
- Formalized core responsibilities (ceremonies, grooming, monitoring, quality gates)
- Defined performance metrics framework (6 KPIs with targets)
- Added backlog grooming process (weekly/monthly/quarterly)
- Established escalation protocols and evaluation criteria
- Pattern: Follows skills/devops/SKILL.md structure (350 lines)

**Maintained By**: @scrum-master  
**Review Frequency**: After each sprint retrospective  
**Update Trigger**: New process violations, KPI changes, stakeholder feedback
