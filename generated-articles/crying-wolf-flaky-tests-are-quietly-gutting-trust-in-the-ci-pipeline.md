---
layout: post
title: "Crying Wolf: Flaky Tests Are Quietly Gutting Trust in the CI Pipeline"
date: 2026-07-14
author: Ouray Viney
categories:
 - Quality Engineering
 - Test Automation
 - Software Engineering
description: "Flaky tests that randomly pass and fail are eroding developer trust in CI pipelines, wasting engineering time, and masking genuine regressions."
image: ""
---

A green checkmark is supposed to be an engineering guarantee. Pass the tests; ship the code; sleep soundly. Except that guarantee has been quietly hollowed out, and the culprit is not underfunded QA teams or careless developers. It is the flaky test — the automated check that passes on Tuesday and fails on Thursday against identical code — and it has grown so pervasive that continuous integration, the discipline designed to give teams confidence, now produces noise as readily as signal. This is not a forecast. Flakiness is already reshaping how engineers read CI results: with suspicion, fatigue, and a learned helplessness that is eroding the social contract of the automated build. When a pipeline fails, the first question is no longer "what broke?" but "was this real?" That cognitive shift — from trust to doubt — is more corrosive than any individual bug, and it is happening at scale.

## Flakiness Has Scaled From Edge Case to Epidemic

Nearly 16% of Google's 4.2 million automated tests exhibit some degree of flakiness, with developers spending between 2% and 16% of compute resources on reruns, according to Google Research. That figure alone warrants attention. What makes it alarming is the trajectory. An analysis of more than 10 million CI builds, reported by Bitrise in SD Times, found that the share of engineering teams experiencing test flakiness grew from 10% in 2022 to 26% in 2025 — a 160% increase in three years, coinciding with a 23% rise in pipeline complexity over the same period. Flakiness scales with sophistication. The more parallelism, microservices, and asynchronous dependencies a pipeline introduces, the more surfaces a non-deterministic test can exploit. Race conditions, port conflicts, timezone sensitivities, and shared state in test fixtures are all grist for the flakiness mill — and each new architectural pattern that speeds up delivery tends to add at least one of them. The chart below illustrates how steeply that trajectory has climbed. As the chart makes clear, this is not approaching a plateau; the upward bend correlates precisely with the adoption of distributed architectures and containerised test environments, both of which trade determinism for throughput. Developers are not unaware. A peer-reviewed IEEE survey of software practitioners found that 56% encounter flaky tests on a daily, weekly, or monthly basis. Flakiness has become the prevailing weather of software delivery — not an occasional storm to be weathered, but the default atmospheric condition under which engineers operate. And when the measurement instrument is unreliable, every reading it produces — pass or fail — carries an asterisk.

## A False Green Light Is More Dangerous Than a Red One

When Atlassian's engineers analysed the Jira Frontend repository, they found that flaky tests caused up to 21% of all master-branch build failures. Across the entire engineering organisation, reruns driven by flakiness consume more than 150,000 developer hours per year — roughly the equivalent of 75 engineers spending their entire annual capacity investigating failures that are, in a meaningful sense, fictional. But the deeper damage is not wasted time; it is what repeated false alarms do to judgment. A study of the Chromium CI pipeline found an average of 178 flaky test failures per build. More troubling still, research on the Chromium CI published on arXiv found that even state-of-the-art flaky-detection methods operating at 99.2% precision still misclassify 76.2% of genuine regression faults as flakiness. Engineers are not merely losing time to noise — they are systematically suppressing real bugs under the assumption that another false positive has arrived. This is the paradox at the heart of flakiness: the more common false positives become, the more rational it is for engineers to rerun rather than investigate. Each rerun reinforces the lesson that CI failures do not necessarily signal something broken. Each lesson makes the next genuine regression slightly harder to catch. A pipeline suffering from widespread flakiness is not merely noisy; it is actively training the humans who use it to distrust their own tooling. That is a cultural wound that no quarantine policy, on its own, can fully heal.

## The Price of Crying Wolf

A five-year industrial case study of 30 developers working across approximately one million lines of code, presented at IEEE ICST 2024, put a precise figure on the damage. Flaky tests consume at least 2.5% of total productive developer time: 1.1% investigating spurious failures, 1.3% repairing the tests themselves, and 0.1% constructing the monitoring tooling required to manage the problem at all. The cost arithmetic is equally stark: allowing a pipeline to fail without an auto-rerun costs $5.67 in manual investigation time; an automatic rerun costs $0.0002. At scale, the choice between investing in flakiness infrastructure and tolerating the status quo is, financially, no contest. Yet engineering teams outside Google and Atlassian largely tolerate the status quo — not from ignorance but from the misapprehension that flakiness is a technical nuisance rather than a strategic liability. Atlassian recognised the gap and built a dedicated internal tool to detect and quarantine flaky tests, shielding the main CI signal from contamination. Google has invested in detection infrastructure at a scale few companies can match. For everyone else, the compound interest of deferred trust debt accumulates silently — in every standup where a developer says, for the third time that week, "the pipeline failed again, probably nothing," in every release where the team ships a little faster, a little more anxious, a little less certain. Flakiness is not a problem that resolves itself through increased reruns and collective optimism. The CI pipeline that has cried wolf often enough will find, one quiet Friday afternoon, that nobody checks the alerts — and the wolf, for once, will be real. 
![Chart](/assets/charts/crying-wolf-flaky-tests-ci-pipeline.png)

## References

1. Google Research. *The State of Continuous Integration Testing at Google*. https://research.google/pubs/the-state-of-continuous-integration-testing-google/

2. Bitrise / SD Times. *Why Flaky Tests Are Increasing and What You Can Do About It* (2025). https://sdtimes.com/bitrise/why-flaky-tests-are-increasing-and-what-you-can-do-about-it/

3. Atlassian Engineering. *Taming Test Flakiness: How We Built a Scalable Tool to Detect and Manage Flaky Tests*. https://www.atlassian.com/blog/atlassian-engineering/taming-test-flakiness-how-we-built-a-scalable-tool-to-detect-and-manage-flaky-tests

4. Parry et al. *A Study of Flaky Tests in the Chromium CI* (2023). arXiv:2302.10594. https://arxiv.org/abs/2302.10594

5. IEEE ICST 2024 Industry Track. *Cost of Flaky Tests in CI: An Industrial Case Study*. https://conf.researchr.org/details/icst-2024/icst-2024-industry/1/Cost-of-Flaky-Tests-in-CI-An-Industrial-Case-Study

6. IEEE Transactions on Software Engineering. *An Empirical Study of Flaky Tests in Python* — survey of software practitioners. https://ieeexplore.ieee.org/document/9787854/