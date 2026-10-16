# LinkedIn Part 2 — Ready-to-publish pack (16 October 2026)

**Status:** PREPARED — NOT published by this chat. Obtain final live LinkedIn URL after publication.

**Image to attach:** `retail_returns_intelligence_part2.png` (data-grounded standalone graphic).

**Source:** `docs/PART2_CASE_STUDY.md`, read-only rerun against recovered SQLite, plus clearly separate fictional simulation.

---

**A higher cancellation value doesn't always mean more returns. Here's what I found.**

For Part 2 of my independent **Multi-Brand Returns Operations Intelligence** portfolio project, I investigated cancellation-marked transactions using Python and SQLite.

The initial comparison was interesting:

📈 Cancellation-marked value: **£221,407 → £286,990 (+29.6%)**

📉 Eligible cancellation lines: **8,286 → 7,658 (−7.6%)**

⚠️ Cancellation-value ratio: **2.57% → 3.23%**

*Comparable January–November 2010 and 2011 periods, UCI Online Retail II.*

At first glance, the higher value ratio could be mistaken for worsening returns performance.

**But a deeper SQL investigation changed the question.**

One product accounted for approximately **27%** of 2011 cancellation-marked value. Drilling into the records identified a **£77,183.60 sale** followed just **16 minutes later** by an equal-and-opposite cancellation entry for the same product, quantity, price and recorded customer.

When I ran a **sensitivity test** excluding *both* offsetting records, the 2011 value ratio moved from **3.23% to 2.38%**, while net recorded merchandise value was unchanged.

That **doesn't** mean 2.38% is the corrected KPI. The original 3.23% stays. And it **doesn't** prove that a parcel was physically returned or why the cancellation occurred.

**The operational lesson:** investigate high-value exceptions before designing solutions around an aggregate metric.

I also built a separate, explicitly **synthetic** 5,000-case returns-logistics simulator, with fictional carrier, warehouse, event timestamps and SLA outcomes, to demonstrate how an operational monitoring model could work when appropriate data exists. Those simulated results are **not real-world performance**.

I've documented the read-only SQL investigation, reproducible Python model, test checks and limitations on GitHub:

🔗 https://github.com/Busayosage/multi-brand-returns-operations-intelligence

**A dashboard shows the increase. A useful analyst investigates what is driving it—and what the data cannot prove.**

What checks would you perform before treating cancellation data as a physical-returns KPI?

#DataAnalytics #SQL #Python #LogisticsAnalytics #ReturnsManagement #ContinuousImprovement #BusinessIntelligence

---

**Publication notes:** Use Anyone/Public; upload the PNG; do not attach the original database, row-level file or confidential material; link to the verified Part 1 post only if useful. Do not imply affiliations with any company. Verify publication and save the direct LinkedIn URL. No automated publishing action is available in this chat.
