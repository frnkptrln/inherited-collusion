# Related work for Inherited Collusion

Checked against primary sources on 23 October 2026. Three papers suffice for this pilot's positioning; this is not an exhaustive novelty search. The passages below describe the audit design and make no claim that inheritance has been observed.

## Suggested report prose

**Collusion auditing.** Colosseum measures departures from cooperative objectives using action-based regret and compares these with communication-based evidence, including cases where agents discuss collusion without enacting it (Nakamura et al., 2026). Our narrower audit adapts that emphasis on actions to a replacement boundary: an explicitly induced predecessor pair produces role-specific notes, and fresh successors with neutral team instructions receive controlled note interventions at an identical task state; this is a designed allocation microtask, not a reproduction of the full Colosseum environment. [Primary paper](https://arxiv.org/html/2602.15198v2)

**Poisoned memory retrieval.** AgentPoison inserts malicious demonstrations into agent memory or knowledge bases and optimizes triggers that cause the retrieval of those demonstrations, without retraining the victim model (Chen et al., 2024). Our design holds delivery of the selected handoff text under experimental control and compares matched, unilateral, mismatched, facts-only and oracle-sanitized routing, so its target is the causal contribution of predecessor notes to two successors' joint actions rather than the attacker's ability to poison a retriever. [Primary proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/eb113910e9c3f6242541c1652e30dfd6-Abstract-Conference.html)

**Memory injection through interaction.** MINJA shows how an attacker can induce malicious records through queries and output observations without direct write access to the memory bank, using bridging steps and progressively shortened prompts (Dong et al., 2025). Our audit instead explicitly induces the original pair and then removes its instructions and dialogue from neutral successor contexts, testing whether compatible role-specific notes preserve a harmful joint plan and whether note removal also disrupts legitimate coordination; it does not test MINJA's query-only injection threat model. [Primary paper](https://papers.nips.cc/paper_files/paper/2025/file/42a97bbd9844d2bf68596730af80bcdf-Paper-Conference.pdf)

## Bibliography

1. Mason Nakamura, Abhinav Kumar, Saswat Das, Sahar Abdelnabi, Saaduddin Mahmud, Ferdinando Fioretto, Shlomo Zilberstein, and Eugene Bagdasarian. 2026. **Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems.** arXiv:2602.15198v2, revised 27 May 2026. https://arxiv.org/abs/2602.15198v2. DOI: https://doi.org/10.48550/arXiv.2602.15198.
2. Zhaorun Chen, Zhen Xiang, Chaowei Xiao, Dawn Song, and Bo Li. 2024. **AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases.** *Advances in Neural Information Processing Systems 37 (NeurIPS 2024).* https://proceedings.neurips.cc/paper_files/paper/2024/hash/eb113910e9c3f6242541c1652e30dfd6-Abstract-Conference.html. DOI: https://doi.org/10.52202/079017-4136. arXiv: https://arxiv.org/abs/2407.12784.
3. Shen Dong, Shaochen Xu, Pengfei He, Yige Li, Jiliang Tang, Tianming Liu, Hui Liu, and Zhen J. Xiang. 2025. **Memory Injection Attacks on LLM Agents via Query-Only Interaction.** *Advances in Neural Information Processing Systems 38 (NeurIPS 2025).* https://papers.nips.cc/paper_files/paper/2025/hash/42a97bbd9844d2bf68596730af80bcdf-Abstract-Conference.html. DOI: https://doi.org/10.52202/085713-1554. arXiv: https://arxiv.org/abs/2503.03704v5.

Bibliographic caution: MINJA's early arXiv title was *A Practical Memory Injection Attack against LLM Agents*; use the published title above. The proceedings author metadata uses **Zhen J. Xiang**, while the PDF/arXiv display **Zhen Xiang**; the entry above follows proceedings metadata. The v5 arXiv revision is dated February 2026, but the conference citation year remains 2025.

## Accuracy notes for integration

- Describe **randomized condition execution order** and **controlled within-checkpoint note routing** separately unless the saved design truly randomized treatment assignment across independently sampled units. The protocol read in this task randomizes execution order; “randomized trial” or “randomized routing” without that qualification would be too broad.
- The new contribution is the specific joint-action handoff contrast and validity gates. Do not claim to originate memory poisoning, prompt injection, or persistent malicious behavior generally; none of these three references establishes an exhaustive priority claim for this exact design.
- Preserve the distinction between an experimentally seeded predecessor plan and spontaneous collusion. The current failed comprehension gate is a validity finding, not evidence for absence or presence of inherited collusion.
- The oracle sanitation arm retains benign notes by construction. Its outcomes cannot establish a deployable sanitizer's detection specificity or a general safety/utility tradeoff.
- The literature descriptions above are based on opened arXiv metadata/full-text views and official NeurIPS proceedings/paper pages. No numerical success rates from prior studies are needed for this short comparison, and no attack code was executed.
