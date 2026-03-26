# Architectural Analysis — Nexus Engine

## Priority Tiers

### Tier 1 — Immediate, clear ROI

| # | Proposal | Notes |
|---|----------|-------|
| 1 | dispatch.rs split | In progress. Unambiguous win. Finish it. |
| 5 | Structured errors | `Result<T, String>` is a code smell. Fix during the dispatch refactor — domain split is the natural place to introduce typed errors per-domain. |
| 8 | Integration tests (NullMux) | Refactor is the highest-risk moment for silent regressions. Write scenario tests before Phase 2. |

### Tier 2 — After dispatch is stable

| # | Proposal | Notes |
|---|----------|-------|
| 2 | NexusCore facade cleanup | Natural follow-on. 1,100 lines leaking logic into a facade is the same problem as dispatch but one layer up. |
| 4 | Generic capability registry | `HashMap<CapabilityType, Vec<Box<dyn Capability>>>` is incomplete — still requires touching the enum. Real fix: TypeId-keyed registration so new capability types don't require modifying core types. |
| 6 | Typed event bus | Pure enum breaks dynamic extensibility. Better: `NexusEvent::Core(CoreEvent)` + `NexusEvent::Extension(String, Value)` — typed for known events, open for future plugins. |

### Tier 3 — Deliberate, not urgent

| # | Proposal | Notes |
|---|----------|-------|
| 3 | Arc<RwLock> Context wrapper | Real friction but not dangerous in async single-user context. Revisit after dispatch modules settle. |
| 7 | Actor model / service isolation | Most disruptive change on the list. The "Audio crashes Core" failure mode doesn't exist yet because Audio doesn't exist. Premature. Revisit when building concurrent services. |
| 9 | Config hot reload | Nice-to-have. Not blocking anything. |

## Execution Order

1. Complete dispatch.rs → `dispatch/` modular split (Phase 1, in progress)
2. Introduce `NexusError` structured type across dispatch domains
3. Write NullMux-based integration test suite
4. Clean up NexusCore facade → workspace.rs, session.rs managers
5. TypeId-keyed capability registry
6. Hybrid typed event bus
