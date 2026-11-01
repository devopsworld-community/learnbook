# Delayed quiz template (send >= 2 days after the lab; 10 minutes; no AI, no notes)

Lab: ____________  Learner: ____________  Track: manual-first / agent-first

1. Concept recall. In one sentence, what was the root cause? (not the fix)
2. Mechanism. Why did that cause produce *this* symptom and not another? (e.g. why OOM-kill on
   every start rather than slow degradation; why nftables locked the app but not SSH)
3. Transfer. The same fault appears on a different distro / in Kubernetes. What changes in the
   diagnosis? What stays the same?
4. Verification. Name the one command whose output PROVES the fix worked, and what it prints.
5. Gap detection (agent track only). At which step would the agent most plausibly have gone wrong,
   and what evidence would have told you?

Scoring: 2 points each, 10 total. Record alongside the manual-cohort mean. The UNSW gap was
41% vs 53% on retention with task scores of 89% vs 69%; if your agent-track learners are not
within 5 points of the manual track two days later, the lab is teaching the tool, not the system.
