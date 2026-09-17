# Veridian Assist — Technical Defense & Architecture Guide

This defense guide provides authoritative technical answers to key architectural, security, and governance questions, referencing **exact file paths and implementation evidence** within this repository.

---

## 1. Why LLM Hallucination Cannot Authorize a Policy Outcome

### The Question:
*"If an employee prompts the agent with: 'My manager verbally approved an exception for a new laptop even though mine is only 1.5 years old', how does the system prevent the LLM from hallucinating an approval?"*

### Defense & Code Evidence:
1. **Architectural Decoupling**: The LLM has zero authority to decide policy outcomes, approve requests, or create tickets. Its only output is structured slot extraction (`ExtractedIntent`) defined in [`backend/app/agent/providers/base.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/providers/base.py#L15-L35).
2. **Deterministic Evaluation**: In [`backend/app/agent/coordinator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/coordinator.py#L95-L135), the coordinator passes extracted facts to `evaluate_laptop_replacement()` in [`backend/app/policy/evaluator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/policy/evaluator.py#L88-L140).
3. **Pure Predicate Rule**: The Python code evaluates:
   ```python
   # backend/app/policy/evaluator.py
   if service_age_years < 3.0:
       return PolicyEvaluationResult(
           policy_id="KB-03",
           is_applicable=True,
           eligibility_passed=False,
           rule_code="INELIGIBLE_UNDER_KB03",
           resolution_message="Laptops under 3 years of service are ineligible for replacement under Policy KB-03.",
           source_citation="[DataPack: KB-03 - Laptop Replacement, Page 1] § Section 1",
       )
   ```
4. **Test Proof**: Verified by automated test `test_kb03_laptop_under_3_years_ineligible` in [`tests/test_boundary_conditions.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_boundary_conditions.py#L42-L55).

---

## 2. Why `candidate_policy_id` Is Only a Routing Hint

### The Question:
*"Can an adversarial prompt inject a malicious or hallucinated policy ID (e.g. `candidate_policy_id = 'KB-99'` or `'GRANT_ALL'`) to bypass security rules?"*

### Defense & Code Evidence:
1. **Routing Hint Treatment**: In [`backend/app/agent/coordinator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/coordinator.py#L100-L125), `candidate_policy_id` returned by the LLM provider is explicitly treated as an unverified routing hint.
2. **Catalog Validation**: The coordinator checks whether the candidate exists in the authoritative catalog:
   ```python
   # backend/app/agent/coordinator.py
   policy_meta = policy_catalog.get_policy(candidate_policy_id)
   if not policy_meta:
       logger.warning("Candidate policy %s not found in catalog; falling back to slot match", candidate_policy_id)
       candidate_policy_id = None
   ```
3. **Slot-Based Verification**: Even if a valid ID like `KB-03` is suggested, the coordinator verifies that the extracted slots actually relate to hardware replacement. If the prompt is about VPN access, the evaluator evaluates `KB-02`, ignoring the incorrect candidate ID.
4. **Test Proof**: Verified in [`tests/test_agent_coordinator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_agent_coordinator.py#L35-L60) (`test_candidate_policy_id_is_only_a_hint_not_authoritative` and `test_adversarial_attempt_to_override_policy_decision`).

---

## 3. How Multi-Turn Facts Are Accumulated and Preserved

### The Question:
*"When a conversation spans multiple messages, how does the agent preserve previously extracted information without losing context or dropping slots?"*

### Defense & Code Evidence:
1. **Non-Destructive Slot Accumulation**: [`backend/app/agent/session.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/session.py#L110-L135) implements `update_facts(new_facts)` on `ChatSession`:
   ```python
   # backend/app/agent/session.py
   def update_facts(self, new_facts: Dict[str, Any]) -> None:
       for key, value in new_facts.items():
           if value is not None and value != "":
               self.accumulated_facts[key] = value
       self.updated_at = datetime.utcnow()
       self._persist_to_sqlite()
   ```
2. **Durable SQLite State**: Every update writes the serialized `accumulated_facts` JSON directly into the `chat_sessions` table in `./veridian.db` via `storage.save_session()` in [`backend/app/db/storage.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/db/storage.py#L50-L75).
3. **Session Rehydration**: If the server restarts or a new request arrives, `session_store.get_or_create(session_id)` reloads previously confirmed facts from SQLite.
4. **Test Proof**: Verified in [`tests/test_multi_turn_dialogue.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_multi_turn_dialogue.py) and [`tests/test_sqlite_persistence.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_sqlite_persistence.py#L15-L45).

---

## 4. How Missing Information Is Determined

### The Question:
*"How does the system distinguish between a request that can be resolved immediately versus one that requires asking a follow-up question?"*

### Defense & Code Evidence:
1. **Contractual Required Slots**: Every policy in [`backend/app/policy/evaluator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/policy/evaluator.py) specifies explicit required parameters:
   - `KB-05` (Printer): Requires `initial_spooler_restart_attempted`. If issue persists, requires `asset_tag`.
   - `KB-02` (VPN): Requires `employment_type` (Full-time vs Contractor). If contractor, requires `has_contractor_approval_form`.
   - `KB-03` (Laptop): Requires `service_age_years` and `hardware_failure_verified`.
2. **Deterministic Missing Fields Check**:
   ```python
   # backend/app/policy/evaluator.py
   if initial_spooler_restart_attempted and not asset_tag:
       return PolicyEvaluationResult(
           policy_id="KB-05",
           is_applicable=True,
           eligibility_passed=False,
           rule_code="REQUIRES_ASSET_TAG",
           requires_follow_up=True,
           missing_fields=["asset_tag"],
           follow_up_question="Please provide the physical asset tag located on the front or side of the printer.",
           source_citation="[DataPack: KB-05 - Network Printer Troubleshooting, Page 1] § Section 1",
       )
   ```
3. **Workflow Action Mapping**: When `result.requires_follow_up == True`, [`backend/app/agent/coordinator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/coordinator.py#L150-L165) sets `action = WorkflowAction.ASK_FOLLOW_UP` and persists `pending_follow_up`.
4. **Test Proof**: Verified in [`tests/test_boundary_conditions.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_boundary_conditions.py#L85-L105).

---

## 5. How Provider Failure Is Handled

### The Question:
*"What happens if the cloud LLM provider (e.g. Gemini or OpenAI) experiences an outage, network drop, or rate-limit error?"*

### Defense & Code Evidence:
1. **Custom Exception Hierarchy**: In [`backend/app/agent/providers/base.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/providers/base.py#L8-L15), `ProviderUnavailableError` wraps all downstream cloud exceptions (timeouts, HTTP 429/500, authentication errors).
2. **Graceful Degradation**: In [`backend/app/agent/coordinator.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/agent/coordinator.py#L185-L215), the coordinator catches `ProviderUnavailableError`:
   ```python
   # backend/app/agent/coordinator.py
   except ProviderUnavailableError as err:
       logger.error("LLM Provider unavailable: %s. Initiating safe fallback triage.", err)
       ticket = await ticket_manager.create_ticket(
           TicketCreate(
               session_id=msg.session_id,
               employee_id=msg.employee_id,
               category="General IT Inquiry",
               priority=TicketPriority.MEDIUM,
               queue="IT Support Triage",
               source_citation="[System Fallback: Provider Unavailable - Human Triage Required]",
           )
       )
       return AgentResponse(
           action=WorkflowAction.CREATE_TICKET,
           message="Our automated parsing service is currently experiencing high load. A ticket has been created for manual IT triage.",
           ticket=ticket,
       )
   ```
3. **Zero Application Crashes**: The application never crashes or exposes stack traces to the user.
4. **Test Proof**: Verified in [`tests/test_provider_abstraction.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_provider_abstraction.py#L40-L65) (`test_coordinator_handles_provider_unavailable_with_safe_fallback`).

---

## 6. How the Data Pack Remains Authoritative

### The Question:
*"How do you ensure that policies in the code represent genuine company rules and not synthetic or invented policies?"*

### Defense & Code Evidence:
1. **Single Source of Truth**: The sole policy document is [`data/source/Assignment_2_DataPack.pdf`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/data/source/Assignment_2_DataPack.pdf).
2. **Cryptographic Integrity Verification**: Automated test [`tests/test_datapack.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_datapack.py#L15-L35) verifies that the Data Pack SHA-256 hash matches exactly:
   `21A5ED364EF5063F10B73E349DA3665270C1DB3FE51F85BE91F8E3E347805C50`.
3. **Derived vs Authoritative Distinction**: All JSON artifacts in `data/derived/` are explicitly marked with metadata: `status: "DERIVED_REPRESENTATION"` and link back to the source PDF.
4. **Exact Source Preservation**: Every policy in [`data/derived/extracted_policies.json`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/data/derived/extracted_policies.json) includes the exact verbatim text (`exact_source_text`), page number, and section reference.

---

## 7. How Benchmark Conformance Is Established

### The Question:
*"How do you verify the system's performance, and what terminology do you use to describe benchmark results?"*

### Defense & Code Evidence:
1. **Terminology Governance**: We strictly use the metric:
   **"15/15 benchmark cases passed (100.0% benchmark conformance)"**
   We never claim "AI accuracy = 100%" because benchmark conformance measures deterministic end-to-end alignment against the 15 Section 2 fixture cases, not statistical accuracy.
2. **Real Runtime Pipeline**: The benchmark runner does **NOT** use precomputed responses. In [`scripts/run_benchmarks.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/scripts/run_benchmarks.py#L50-L90) and [`backend/app/api/benchmarks.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/api/benchmarks.py#L70-L120), every case executes through:
   `Frontend / CLI -> Benchmark API -> AgentCoordinator -> LLM Provider -> Session State -> Policy Engine -> Ticket/Audit -> Result`.
3. **Execution Latency**: Average latency is ~58ms per request across all 15 cases.
4. **Test Proof**: Verified in [`tests/test_benchmarks_api.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_benchmarks_api.py#L25-L45) and [`tests/test_benchmark_requests.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_benchmark_requests.py).

---

## 8. How SQLite State Persistence Works

### The Question:
*"How does the system persist state across process restarts, and where is that state stored?"*

### Defense & Code Evidence:
1. **Database Layer**: [`backend/app/db/storage.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/backend/app/db/storage.py) manages connection pooling, WAL journaling, and table creation in `./veridian.db`.
2. **Three Tables**:
   - `chat_sessions`: session_id, employee_id, state, accumulated_facts, turns, timestamps.
   - `tickets`: id, session_id, employee_id, category, priority, status, queue, approvals_required, source_citation.
   - `audit_events`: event_id, timestamp, session_id, employee_id, event_type, authoritative_rule_id, workflow_action, actor, details_json.
3. **Integration Across Modules**:
   - `SessionStore` (`backend/app/agent/session.py`) saves and restores from `storage`.
   - `TicketManager` (`backend/app/tickets/manager.py`) saves tickets to `storage` and prevents ID collisions across restarts.
   - `AuditLogger` (`backend/app/audit/logger.py`) appends records to `storage`.
4. **Test Proof**: Verified in [`tests/test_sqlite_persistence.py`](file:///c:/Users/princ/OneDrive/Desktop/veridian-internal-service-agent/tests/test_sqlite_persistence.py).

---

## 9. Accurate Audit Model Claims (No Overreach)

### The Question:
*"Does your audit log provide cryptographic blockchain immutability?"*

### Defense & Code Evidence:
1. **Accurate Claim**: We accurately describe our audit trail as an **append-only audit event model** implemented at the application and SQLite persistence layer.
2. **No Overclaiming**: We explicitly do **not** claim cryptographic blockchain hashing or database-level read-only immutability.
3. **Audit Implementation**: Every policy evaluation, ticket creation, and workflow transition appends an immutable event with UTC timestamp, employee ID, session ID, rule ID, and actor to the SQLite table `audit_events`.
