---
layout: post
title: "No Dress Rehearsal: The Ruinous Logic of Skipping Staging Environments"
date: 2026-07-15
author: Ouray Viney
categories:
 - Quality Engineering
 - Software Engineering
description: "Sixty percent of organisations ship untested code to production. The bill arrives not as a line item, but as a $20 million annual catastrophe."
image: ""
---

<!-- HERO IMAGE — generate an image from the prompt below, then replace this whole comment with it (see output/posts/<slug>.image_prompt.md):

Generate an editorial illustration for the article "No Dress Rehearsal: The Ruinous Logic of Skipping Staging Environments".

Subject: An Economist-style editorial illustration of a developer triumphantly pressing a deploy button while production servers burn behind them, reflected in the dark glass of an unpowered, abandoned staging-environment rack
Editorial framing: Skipping the rehearsal does not make the performance cheaper — it makes the cancellation catastrophic.

Palette: Economist red #E3120B, deep navy, off-white, one accent
Aspect ratio: 1792x1024 (landscape hero)
Constraints: no text, no words, no captions, no logos in the image itself
Style: bold, high-contrast graphic editorial illustration (not painterly, not photorealistic)
-->

Cutting the staging environment is the software industry's version of skipping dress rehearsals to save on theatre hire. A slim budget line disappears; catastrophe fills the gap. Sixty percent of global organisations are shipping code to production without fully testing it, according to the Tricentis 2026 Quality Transformation Report — a survey of more than 2,500 chief information officers, DevOps leads and quality-assurance directors published in June 2026. That proportion has barely moved from 63% the year before. What has shifted is the cost of being wrong: one in five of those organisations now reports losing more than $1 million annually from poor software quality, with a further 45% estimating losses between $500,000 and $1 million. Skipping staging is not a velocity strategy. It is a bet against the house — and the house has been collecting for years.

## The Unpaid Infrastructure Tax

A staging environment is, at its most reductive, a mirror of production that nobody deploys to customers. That makes it easy to defund. Engineering managers watching quarterly budgets see compute costs, licensing fees and maintenance burden; they do not see the defects intercepted before they reached users. This asymmetry of visibility is precisely what makes staging cuts look rational on a spreadsheet and disastrous in an incident post-mortem. Evidence predates the cloud era. Research Triangle Institute, contracted by the National Institute of Standards and Technology in 2002, estimated that software errors cost the American economy $59.5 billion annually — and that more than half of all defects went undetected until after release. Improved pre-release testing infrastructure, the report found, could have eliminated approximately $22 billion of that cost. That study is ageing; the conclusion is not. The Tricentis 2025 Quality Transformation Report, surveying 2,750 practitioners across ten countries, found that 66% of global organisations face significant risk of a major software outage within the next year, with nearly a quarter rating themselves "extremely at risk." Release-cycle pressure, cited by 46% of respondents, and accidental deployment of untested code, cited by 40%, are the dominant causes — precisely the failure modes a staging environment intercepts. The chart below illustrates both trends simultaneously: incident frequency climbing while pre-production coverage shrinks. As the chart makes clear, organisations are not choosing speed over quality as a calculated risk — they are failing to notice the inverse correlation until the damage accumulates.

## The $794,000 Penalty

When untested code reaches production and breaks something customer-facing, the price is no longer theoretical. A PagerDuty survey of 500 IT leaders across the United States, the United Kingdom and Australia, published in June 2024, put the average cost of a customer-facing incident at roughly $794,000 — calculated at $4,537 per minute over an average resolution time of 175 minutes. Fifty-nine percent of those leaders reported that such incidents had risen by an average of 43% in the past twelve months. Organisations average twenty-five high-priority incidents a year; the accumulated annual tally reaches approximately $20 million per organisation. That $20 million figure is what makes the staging calculus so peculiar. A well-provisioned staging environment for a mid-sized engineering team rarely costs more than a few hundred thousand dollars a year in compute and personnel. Engineers at organisations that maintain proper pre-production gates do not treat staging as overhead; they treat its absence as an unbudgeted liability that surfaces at 2 a.m. on a Saturday. The sectors most exposed are those where uptime is a commercial covenant: financial services, e-commerce, healthcare, and SaaS businesses whose contractual SLAs have teeth. For these organisations, a single major incident can exceed the entire annual cost of maintaining a staging environment by a factor of ten or more. Framing staging costs as "savings" is the kind of arithmetic that looks elegant until the incident bridge opens.

## The Elite Minority Who Refused to Cut Corners

Google's DORA *Accelerate State of DevOps 2024* report — drawing on responses from thousands of engineering practitioners worldwide — found that elite-performing teams carry a change failure rate eight times lower than their low-performing counterparts. Only 19% of surveyed teams qualify as elite. Elite teams share a structural feature that the data cannot explain away: robust pre-production gates that catch regressions before they touch customers. For these teams, staging environments are not an overhead line item. They are the mechanism by which speed and stability co-exist rather than trade off. The DORA data contains a troubling subplot. Rising AI adoption — which accelerates raw code output — is associated with a 7.2% reduction in delivery stability. Developers producing more code faster, without commensurate investment in pre-production infrastructure, are widening the attack surface for production incidents rather than narrowing it. Elite teams are not distinguished by rejecting AI tooling. They are distinguished by refusing to let throughput outrun their verification capacity — a discipline that starts, structurally, with maintaining an environment that mirrors production before code ever reaches it.

## AI Pours Petrol on a Smouldering Fire

Here is where the story turns from expensive to structurally alarming. According to the Tricentis 2026 Quality Transformation Report, the share of organisations knowingly deploying untested code is now driven not merely by impatience but by structural constraint: 32% cite leadership pressure to prioritise speed over quality, and 30% report that the sheer volume of AI-generated code has grown too large to test fully. Faster code generation without a staging buffer is not an engineering philosophy. It is a pressure accumulator with no release valve — and as AI tooling accelerates output still further, the accumulator is being loaded faster than most engineering organisations can discharge it through manual review alone. Software organisations that treat staging as dispensable are not saving money. They are running a theatre in which every performance is also opening night, every defect a visible catastrophe, and the audience — customers, regulators, investors — increasingly unwilling to buy a second ticket. Organisations that navigate the next decade of AI-accelerated development will not be those that shipped the most code. They will be the ones that made certain it worked before their customers had to find out it did not. 
![Chart](/assets/charts/no-dress-rehearsal-staging-environments.png)

## References

1. PagerDuty / Censuswide. "Study: The Cost of Incidents." Survey of 500 IT leaders, US, UK and Australia. June 2024. https://www.pagerduty.com/newsroom/study-cost-of-incidents/
2. Tricentis. *2026 Quality Transformation Report.* Survey of 2,500+ CIOs, CTOs, DevOps and QA leaders. June 2026. https://www.tricentis.com/news/2026-quality-transformation-report
3. Tricentis. *2025 Quality Transformation Report.* Survey of 2,750 respondents across 10 countries. May 2025. https://www.businesswire.com/news/home/20250513499311/en/Two-Thirds-of-Global-Organisations-Significantly-at-Risk-of-Software-Outage-Within-Next-Year
4. Google. *Accelerate State of DevOps Report 2024.* DORA research programme. https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report
5. Research Triangle Institute for NIST. "The Economic Impacts of Inadequate Infrastructure for Software Testing." NIST Planning Report 02-3. May 2002. https://www.nist.gov/document/samate-document-greg-tasseys-summary-pdf-nists-2002-report-economic-impacts-inadequate