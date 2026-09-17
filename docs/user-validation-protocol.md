# External user validation protocol

## Status: PENDING -- not yet run

No external user testing has happened. This document specifies the protocol so it can be run later; nothing here should be read as a reported result. Any future report that includes this testing must clearly separate what actual participants did from what this document merely planned.

## Participants (bounded set, per project scope)

Two non-technical users, two students, one product manager, one developer, one researcher, one marketer.

## Tasks

Each participant is given one request in their own words (not pre-written by this project) and asked to, using only `groundspec create` (guided mode) and `groundspec validate`/`audit`:

1. **Explain a vague request** -- state, before seeing any output, what they think the tool needs to know that they haven't said yet.
2. **Understand the resulting contract** -- read the generated `.toml` file and explain, in their own words, what it says the goal, deliverables, and acceptance criteria are.
3. **Correct a wrong assumption** -- the facilitator seeds one deliberately-wrong `scope.assumptions` entry beforehand; the participant is asked to find and fix it.
4. **Run validation** -- run `groundspec validate` and `groundspec audit` themselves and interpret the output.
5. **Compile a usable Skill or prompt** -- run `groundspec compile --target generic` (or `claude-code`/`codex` if they have the corresponding tool) and judge whether they'd feel comfortable handing the result to an AI assistant.
6. **Understand remaining uncertainty** -- read the `status` section (pre-filled with a realistic partial example) and explain what's still unknown.
7. **Identify what the system did not guarantee** -- after reading the README's "What does it not guarantee?" section, explain it back in their own words.

## What is measured

- Task completion (did they finish each of the 7 steps without facilitator intervention?).
- Time to first usable output.
- Number and nature of facilitator interventions needed.
- Verbatim quotes on confusion points, especially around schema terms (`hard constraint`, `soft objective`, `evidence label`) -- these should be understandable without prior knowledge of PRDs, JSON Schema, acceptance criteria, or agent evaluation, per this project's usability requirement.
- Whether the participant's own explanation of "what this doesn't guarantee" matches the README's actual claims.

## What would count as a failure signal

- A participant cannot explain the compiled contract back in their own words.
- A participant believes the tool verified something it explicitly labels as "needs human/model judgment."
- A participant needed more than one facilitator intervention to get through guided-mode `create`.
- A participant came away believing the tool guarantees correctness, safety, or that it replaces professional review for the high-stakes example.

## Reporting discipline

When this is actually run, results must be labeled `HUMAN-REVIEWED` (for facilitator-scored completion/confusion data) or `VERIFIED` (for objective facts like elapsed time), never `MODEL-EVALUATED` or `PROPOSED`, and must include the raw participant count and task-by-task breakdown, not just an aggregate impression. Until then, this section and this whole document remain `PENDING EXTERNAL VALIDATION`.
