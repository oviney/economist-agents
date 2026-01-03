# GitHub Features Training - Team Onboarding

**Goal**: Learn to use GitHub's native web interface for all project tracking and reporting.

**No external tools, no local files, everything online!** 🎉

---

## What's Changed?

### ❌ Old Way (What We're Replacing)
- External project management tools (Jira, Asana, etc.)
- Local markdown files for tracking
- Manual report generation
- Scattered information

### ✅ New Way (What We're Using Now)
- **GitHub Projects** - Live Kanban boards
- **GitHub Insights** - Real-time graphs and charts
- **GitHub Milestones** - Live sprint progress
- **Bookmarked URLs** - Instant access to dashboards

**Everything updates automatically as we work!**

---

## Week 1: Getting Started

### Day 1: Setup Your Dashboards (30 minutes)

**Task 1: Create Bookmarks Folder**
1. Open your browser
2. Create folder: "GitHub Dashboards"
3. Bookmark these 5 essential URLs:

```
🎯 My Work
https://github.com/issues/assigned/@me

👀 My Reviews  
https://github.com/pulls/review-requested/@me

📋 Sprint Board
https://github.com/users/oviney/projects/1

🎯 Sprint Progress
https://github.com/oviney/economist-agents/milestone/9

📊 Team Activity
https://github.com/oviney/economist-agents/pulse
```

**Task 2: Test Your Bookmarks**
- Click each bookmark
- Verify it loads correctly
- Pin the "Sprint Board" tab in your browser

**✅ Success Criteria**: All 5 bookmarks working

---

### Day 2-5: Daily Practice (5 minutes/day)

**Morning Routine**:
1. Open "🎯 My Work" bookmark
   - What issues am I assigned?
   - What should I work on today?

2. Open "👀 My Reviews" bookmark
   - Any PRs need my review?
   - Schedule time to review them

3. Open "📋 Sprint Board" bookmark
   - Move yesterday's cards to "Done"
   - Check team progress

**End of Day**:
1. Close finished issues
2. Move completed cards on board
3. Add comments to blocked work

**✅ Success Criteria**: Can navigate dashboards without help

---

## Week 2: Explore Insights

### Daily: View Live Metrics (3 minutes)

**Monday**: Open "📊 Team Activity" (Pulse)
- See last week's PRs and issues
- Who was most active?
- Share wins in standup!

**Wednesday**: Open Contributors Graph
```
https://github.com/oviney/economist-agents/graphs/contributors
```
- See commit trends
- Check team velocity

**Friday**: Check Sprint Progress
```
https://github.com/oviney/economist-agents/milestone/9
```
- Progress bar shows completion %
- Are we on track for sprint goal?
- Discuss in retrospective

**✅ Success Criteria**: Comfortable finding and reading graphs

---

## Week 3: Master Projects

### Customize Your Project Board

**Task 1: Create Personal View** (10 minutes)
1. Open sprint board
2. Click "+ New view" (top tabs)
3. Name it "My Work"
4. Add filters:
   ```
   Assignee: is @me
   Status: is not Done
   ```
5. Save view

**Task 2: Practice Moving Cards** (5 minutes)
1. Open sprint board
2. Find your work
3. Drag cards between columns:
   - Todo → In Progress (when you start)
   - In Progress → Review (when PR opens)
   - Review → Done (when PR merges)

**Task 3: Use Table View** (5 minutes)
1. Click "Table" tab
2. Try filtering:
   ```
   priority:P0 status:"In Progress"
   ```
3. Try sorting:
   - Click "Priority" column header
   - Click "Status" column header

**✅ Success Criteria**: Can customize views and move cards

---

## Week 4: Share Knowledge

### Team Exercise: Dashboard Review (30 minutes)

**Activity**: Each person shares their screen

**Person 1**: Show morning routine
- Open bookmarks
- Explain what you look for
- Tips and tricks you learned

**Person 2**: Show sprint board
- Demonstrate dragging cards
- Show custom views
- Explain filters

**Person 3**: Show insights
- Navigate to Contributors graph
- Show Code Frequency
- Explain what metrics mean

**Person 4**: Show search tricks
- Filter issues by label
- Find old PRs
- Search by author

**✅ Success Criteria**: Everyone learns at least 1 new trick

---

## Quick Reference Card

**Print or save this for your desk!**

### Essential URLs

| Dashboard | URL |
|-----------|-----|
| 🎯 My Work | `github.com/issues/assigned/@me` |
| 👀 My Reviews | `github.com/pulls/review-requested/@me` |
| 📋 Sprint Board | `github.com/users/oviney/projects/1` |
| 🎯 Sprint Progress | `github.com/oviney/economist-agents/milestone/9` |
| 📊 Team Pulse | `github.com/oviney/economist-agents/pulse` |
| 📈 Velocity | `github.com/oviney/economist-agents/graphs/contributors` |

### Daily Checklist

**Morning** (5 min):
- [ ] Check "My Work" - what am I doing today?
- [ ] Check "My Reviews" - any PRs to review?
- [ ] Check "Sprint Board" - move yesterday's cards

**Evening** (3 min):
- [ ] Close finished issues
- [ ] Move completed cards
- [ ] Comment on blockers

**Friday** (15 min):
- [ ] Review Team Pulse - how was our week?
- [ ] Check Sprint Progress - are we on track?
- [ ] Review Velocity graph - trending up or down?

### Search Tricks

**Find issues**:
```
is:open assignee:@me              # My open issues
is:open label:P0-critical         # Critical items
is:open no:assignee label:sprint-9 # Unassigned work
```

**Find PRs**:
```
is:pr is:open review-requested:@me # Need my review
is:pr is:open author:@me           # My PRs
is:pr is:merged merged:>2026-01-01 # Merged this year
```

### Browser Shortcuts

- Press `/` - Focus search bar
- Press `g i` - Go to Issues
- Press `g p` - Go to Pull Requests
- Press `?` - Show all shortcuts

---

## Getting Help

### Documentation

**Complete guides** (bookmark these too!):
- **Skills Guide**: `skills/github-features/SKILL.md`
- **Navigation Guide**: `docs/GITHUB_WEB_UI_NAVIGATION.md`
- **Tutorial**: `docs/GITHUB_FEATURES_TUTORIAL.md`
- **Quick Reference**: `docs/GITHUB_REPORTING_QUICK_REFERENCE.md`

### Common Questions

**Q: I don't see the Projects tab?**
A: Projects need to be enabled. Ask repository admin.

**Q: Progress bar not updating?**
A: Make sure issues are assigned to the milestone (check right sidebar).

**Q: Can't find my assigned issues?**
A: Use bookmark: `github.com/issues/assigned/@me`

**Q: How do I add issues to project board?**
A: Open project → Click "+ Add item" → Search issue number

**Q: Can I access this from my phone?**
A: Yes! Download GitHub mobile app or use mobile browser.

### Getting Help from Team

**Slack/Teams**: `#github-help` channel
**In person**: Ask anyone who completed Week 4
**Documentation**: Check the guides above

---

## Success Metrics

### Individual Success
- ✅ Can find assigned issues in <10 seconds
- ✅ Can update project board daily
- ✅ Can view sprint progress without help
- ✅ Bookmarks are used daily

### Team Success
- ✅ Sprint board updated daily by all members
- ✅ Sprint milestone progress visible to all
- ✅ Team discusses insights in retrospectives
- ✅ No one asks "where do I track my work?"

---

## Congratulations! 🎉

After 4 weeks, you should be comfortable with:
- ✅ Using bookmarks to access dashboards
- ✅ Viewing live metrics and graphs
- ✅ Updating project boards
- ✅ Finding information quickly
- ✅ Sharing progress with team

**You're now a GitHub power user!** 💪

---

**Need a refresher?** Re-read this document anytime.

**Found a better way?** Share it with the team!

**Questions?** Check the documentation or ask in `#github-help`.

---

**Last Updated**: 2026-01-03
**Version**: 1.0
**Audience**: All team members (developers, QA, PM, scrum master)
