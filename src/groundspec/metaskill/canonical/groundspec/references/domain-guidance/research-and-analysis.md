# Domain guidance: research and analysis

Select `--domain research`. The pack expects an explicit, answerable research question (not a vague topic), primary sources preferred over secondary summaries, recency checked against the task's needs, citations placed next to the claim they support (not only in a bibliography), contradictory evidence surfaced rather than silently resolved, inference labeled distinctly from directly observed evidence, and quotation kept short.

Practical tips specific to this Skill's workflow:

- If `brief.goal` reads like a topic ("look into X") rather than a question ("does X exceed Y, and by how much"), that's a `blocking` clarification per `clarification-policy.md` -- ask for the actual question before researching.
- Groundspec has no built-in ability to fetch external sources itself; whatever tools are actually available in this session (web search, document reading, etc.) do that work, and their outputs go into `status.verified_facts` with a source and access date. Do not claim a source was checked if it wasn't.
- Number of sources is not a quality signal by itself -- one authoritative primary source beats five secondary summaries repeating each other.
- When sources disagree, record both positions and which one you judge more reliable and why, rather than picking one silently -- see `examples/02-market-research` for the shape this takes in a contract's acceptance criteria.
- If the question touches medical, legal, financial, or safety territory, add the `high_stakes_regulated` risk overlay (see `routing-and-risk.md`) even though the domain pack is `research` -- the two are independent axes.
