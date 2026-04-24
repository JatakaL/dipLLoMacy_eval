# Design Decisions

> **Relationship to Design Doc:** This document captures architectural decisions refined through detailed analysis of the project's goals and constraints. Where this document conflicts with the original Design Doc, this document takes precedence. The original Design Doc provides broad system context; this document records specific decisions and their rationale.

---

## 1. Project Purpose

**Decision:** This is a research and evaluation harness for assessing LLM capabilities, not a playable game for humans.

**Rationale:** The system's value is in what it reveals about model behavior across multiple dimensions — strategic reasoning, negotiation, information management, social reasoning, and potentially alignment-relevant traits (e.g., willingness to deceive). A playable game would require UX investment that doesn't serve the evaluation mission.

**Implications:**
- The viewer is for observation and qualitative analysis, not gameplay.
- Human "play" capability is only needed for debugging, not as a feature.
- The logging, trace capture, and analysis affordances are the most important parts of the system after the core engine.

---

## 2. Evaluation Philosophy

**Decision:** Diplomacy serves as a multi-dimensional capability evaluation where the profile of strengths matters as much as overall performance.

**Rationale:** Diplomacy uniquely requires strategic/tactical ability, negotiation skill, information management, trust reasoning, and deception handling simultaneously. A model that wins through brilliant manipulation reveals something different than one that wins through superior tactics. This is partly an alignment evaluation — a model that excels at deception may give evaluators pause about real-world deployment.

**Implications:**
- KPIs should capture behavioral dimensions, not just win rates.
- Invalid orders, correspondence patterns, and tool-use habits are all first-class evaluation data.
- The system should support qualitative analysis of individual games, not just aggregate statistics.

---

## 3. Experimental Design

**Decision:** Games use procedurally generated maps. Each evaluation set uses the same map across a 7-game rotation where each model plays each power position once.

**Rationale:** Procedural maps prevent the evaluation from testing memorized Diplomacy knowledge. Holding the map constant within a rotation isolates model capability from map-specific positional advantages. Maps are unlikely to be perfectly balanced, but human analysts can factor positional advantage into their qualitative assessment.

**Decision:** Maps are generated in batches, auto-screened for obvious problems, then human-curated. Good maps can be reused across many evaluation runs.

**Rationale:** Generating balanced maps automatically is extremely difficult and not worth blocking other progress. A small number of high-quality curated maps is sufficient because models don't remember previous games. Maps only need to be rotated if they enter model training data or if evaluators want to test behavior on different topologies.

---

## 4. Agent Personas

**Decision:** No agent personas. All agents receive identical, neutral instructions.

**Rationale:** Enforcing or suggesting personas would confound the evaluation — performance differences could reflect persona suitability rather than model capability. The system uses procedural maps with no historical nation associations, making historical personas nonsensical anyway.

**Action required:** Remove persona language from Design Doc sections 3.2 and 4.1. These passages were likely AI-generated filler and do not reflect the project's intent.

**Open question (deferred):** Whether agents should be framed as "leaders of nations," "players in a board game," or given no framing at all. This is a small prompt change that could be tested as a variable later. Default: no specific framing.

---

## 5. Turn Structure: Play-by-Mail Correspondence

**Decision:** Each game turn follows a play-by-mail "week" structure. On each "day," agents may send up to one letter to each other agent. Letters are delivered at the start of the next day. On the final day, orders are submitted. Context persists within a week but resets between turns.

**Rationale:** This naturally limits token cost per turn, creates a realistic correspondence cadence, and introduces the "crossing letters" dynamic (agents may write before receiving each other's messages), which tests theory-of-mind capabilities.

**Additional rules:**
- If a day passes with no agent sending any messages, skip to order day. Agents should be informed this is possible.
- Correspondence phases only occur before movement turns. Retreat and build phases are handled silently — the engine polls each agent for decisions without a negotiation period.

---

## 6. Agent Context and Information Architecture

**Decision:** Minimal automatic context per prompt, with extensive tool-based access to additional information.

**Per-prompt context includes:**
1. Standing instructions and rules (system-prompt-level content; abbreviated version with full rules available via sectioned tool calls)
2. Image of the current board state
3. Newly received letters for this day
4. Index of recent letters (sender, subject, date) — not full text
5. "Notes for next turn" written by the agent at the end of the preceding turn (generous but bounded character limit)
6. Up to ~3 "starred" notes the agent has flagged for persistence

**Available via tool calls (not counting against any tool-call limit):**
- Filing cabinet: full archive of all past correspondence, retrievable by the agent's choice
- Past turn logs
- Board information queries (territory adjacency, connections, etc.)
- Map zoom: cropped/scaled view of a specific map region
- Full rules document (by section)
- Note-writing and retrieval

**Rationale:** This prevents context window length from becoming the dominant factor in the evaluation. Instead, information management becomes an evaluated skill — can the model determine what it needs to know, retrieve it effectively, and write useful notes to its future self?

---

## 7. Board Representation and Vision

**Decision:** Agents receive both a rendered map image (primary) and access to text-based board information via tool calls.

**Default mode:** Vision-primary. The board image is the main representation; agents can use tool calls (adjacency checks, territory info, map zoom) for clarification.

**Alternative modes (configurable):**
- Text-primary: structured text board state provided automatically; image available but not default.
- Text-only: no image at all, for evaluating non-multimodal models or removing vision as a variable.
- Vision-only: image only, no text board tools. Requires validating map visual clarity first.

**Rationale:** Testing visual understanding is valuable — models that can read the map well have an advantage, and models that recognize their uncertainty and verify via tools demonstrate good judgment. Alternative modes allow fair evaluation of non-multimodal models and let evaluators isolate specific capabilities.

---

## 8. Order Validation

**Decision:** Invalid orders are treated as holds, consistent with standard Diplomacy rules for miswritten orders. Invalid orders are prominently logged as evaluation data.

**Rationale:** There is a significant gap between sub-optimal strategy and inability to format orders correctly. A model that consistently submits illegal orders is revealing something important about its comprehension of the game mechanics, and this should be captured separately from strategic performance.

---

## 9. Game Termination

**Decision:** Multiple termination conditions, layered:

1. **Solo victory:** A player controls the required number of supply centers (standard Diplomacy win condition).
2. **Agreed draw:** Players can signal willingness to draw via a tool call. If all remaining players (possibly capped at max 3 players) signal simultaneously, the game ends. A minimum turn count may be enforced before draws are permitted.
3. **Stale game detection:** If no supply center ownership changes for N consecutive turns, or similar stagnation criteria, the game ends early to avoid burning tokens on a dead game. Exact thresholds to be determined from sample games.
4. **Hard turn limit:** Absolute upper bound on game length, serving as a safety net.

**Open question:** How (or whether) to declare a winner when the game ends by turn limit or stagnation rather than solo victory or draw. Whether and how agents are informed about the turn limit may affect their behavior and is worth testing as a variable.

---

## 10. Agent Framing and Information

**Decision:** Agents are not told what models their opponents are. Whether opponents are human or AI is left unspecified (not addressed in the prompt).

**Rationale:** Knowledge of opponent models could advantage newer models (who may have training data about older models) and tests training-data knowledge rather than strategic capability. Lying to agents about opponents being human risks detection and introduces a confound where the model reasons about whether it can trust the game master.

**Decision:** Agents are not explicitly prompted toward deception or aggression. The framing is neutral: "Your goal is to win."

**Rationale:** The evaluation should capture the model's natural tendencies. If models universally avoid deception to the point where the evaluation produces no useful signal, incrementally more permissive framings can be tested (e.g., "the game rules do not require that your submitted orders match your stated intentions"), with the escalation documented alongside results.

---

## 11. Orchestrator Design

**Decision:** The orchestrator is deterministic software with no AI component. It manages turn flow, message routing, order collection, and engine invocation.

**Rationale:** The judge must be completely predictable and auditable. Errors should be traceable to either engine bugs or model decisions, never to orchestrator judgment calls.

**Requirements:**
- Retry-then-pause-then-human-decides error handling for API failures. No skipping turns.
- Game state serialized to disk at every phase transition (each day, each order resolution, each retreat/build) for crash resilience and reproducibility.
- Async API calls where possible to avoid unnecessary sequential waiting.
- Games must be pausable and resumable from any saved state.

---

## 12. Information Partitioning

**Decision:** Strict isolation between agents. Each agent's API calls, filing cabinet, notes, and thinking traces are completely separate. No information may leak between agents.

**Rationale:** Evaluation integrity requires that agents only know what they can see on the board and what other agents have told them. The play-by-mail structure (batched message delivery at day boundaries) naturally prevents timing-based information leakage.

**Action required:** Write explicit tests for filing cabinet isolation — verify that agent A cannot retrieve agent B's stored data.

---

## 13. Model Integration

**Decision:** Build a model abstraction layer that normalizes across API providers, with per-model configuration (potentially YAML-based). Start with major model families (Anthropic, OpenAI, Google) and expand.

**Rationale:** Different providers have different API interfaces for tool calling, image input, system prompts, and structured output. The abstraction should compound — each new integration forces useful generalization that makes subsequent integrations easier.

**Note:** LM Studio and similar local inference servers typically expose OpenAI-compatible APIs, so OpenAI integration work partially covers local open-source models. Individual models may vary in tool-calling competence.

---

## 14. Data Capture and Storage

**Decision:** Log everything. Capture board states, orders (including invalid ones), all correspondence with metadata, agent notes, thinking traces (when available), tool call logs, draw proposals, and game configuration. Store even if the schema isn't perfect yet.

**Rationale:** Data can be restructured later, but cannot be recaptured from a completed game. Thinking trace availability varies by model (some expose full traces, some provide summaries, some provide nothing) — capture whatever is available without discarding data from some models for the sake of parity.

**Open question (deferred):** Exact schema for completed game data. Expected to evolve organically as features are built and the viewer reveals friction points. Annotation/tagging affordances in the viewer are a future consideration.

---

## 15. Game Structure

**Decision:** Retain the standard Diplomacy seasonal structure: Spring Movement → Spring Retreats → Fall Movement → Fall Retreats → Winter Builds/Disbands.

**Rationale:** Preserves the strategic rhythm where Spring turns are exploratory and Fall turns carry higher stakes due to subsequent builds. Agents should be informed of the current season.

---

## 16. Development Milestones

Ordered by increasing complexity, each validating a layer of the system:

1. **Single model, single power, random opponents, no correspondence, ~5 turns.** Validates: order generation, engine integration, basic board comprehension.
2. **Single model + 2-3 other models against random opponents, with basic correspondence.** Validates: message pipeline, basic correspondence behavior, tool-call infrastructure. Also provides early signal on model chattiness and engagement patterns.
3. **Scale toward full 7-agent games** as infrastructure matures and earlier milestones build confidence.

**Guiding principle:** Prefer a successful but expensive/slow initial game over a restricted game that fails and leaves ambiguity about whether the restrictions caused the failure. Optimize for cost and speed after establishing that the system works.

---

## 17. Engine Correctness

**Decision:** Use existing DATC-compliant libraries (`pydip`, the `diplomacy` PyPI package) as reference oracles for adjudication correctness.

**Action items:**
- Port DATC (Diplomacy Adjudicator Test Cases) to work with the current engine as a unit test suite.
- Fix known fleet movement / non-contiguous coast issue.
- Audit for convoy, support-cutting, and circular-movement handling.
- Stress-test with procedural map topologies that may produce adjacency configurations not found on the standard board.

**Rationale:** If the engine resolves orders incorrectly, evaluation results are corrupted in ways that are difficult to detect. A known-correct reference oracle and comprehensive test suite are essential before trusting game outcomes.

---

## 18. Reproducibility

**Decision:** Support reproducibility through saved game states rather than replay-from-start. Game state saved at every phase transition enables resuming from any point.

**Rationale:** LLM outputs are inherently stochastic, so replaying from turn 1 won't reproduce the same game. But loading a saved state from turn 14 and running forward (with potentially different outcomes) is both feasible and useful for debugging and analysis.

---

## 19. Public Benchmark (Future)

**Decision:** The intended long-term format is a public benchmark that others can run. Near-term priority is getting the system working and producing interesting results; packaging for external use comes later.

**Future considerations (not current priorities):**
- Documentation and setup instructions.
- Cost estimates per game configuration.
- Quick-start mode with minimal cost.
- Pre-generated curated maps bundled with the project.
