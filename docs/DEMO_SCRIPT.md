# Veridian Assist — Live Technical Demonstration Script

**Target Video / Defense Duration**: 5–7 Minutes  
**Demonstrator**: Prince Jha  
**System Under Demo**: Veridian Assist (Next.js Frontend on `localhost:3000` + FastAPI Backend on `localhost:8000` + SQLite `./veridian.db`)  
**Operating Mode**: Default Offline Defense Mode (`MockLLMProvider`, 100% deterministic, zero network dependencies)

---

## Preparation Checklist
1. **Start Backend**:
   ```powershell
   cd c:\Users\princ\OneDrive\Desktop\veridian-internal-service-agent
   .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Start Frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```
3. Open Browser at `http://localhost:3000`.

---

## Segment 1: System Overview & Data Pack Integrity (0:00 – 1:00)

### Spoken Narration:
> *"Hello, my name is Prince Jha, and today I am presenting Veridian Assist, an enterprise internal IT service agent for Veridian Corp.
>
> In enterprise IT, allowing an unconstrained LLM to authorize approvals or make policy decisions creates severe governance and security risks. Veridian Assist solves this by strictly decoupling the LLM into a non-authoritative natural language parser, while delegating all policy decisions, approvals, and ticket workflows to a deterministic Python Policy Engine grounded exclusively in the company Data Pack.
>
> In our top header, notice the verified cryptographic SHA-256 hash of the authoritative Data Pack: `21A5ED36...`. All 11 policies from Section 1 are cataloged with zero synthetic inventions, and all session state is persisted to SQLite in WAL mode."*

### Visual Actions:
- Point cursor to top status bar: "Policy Engine: Authoritative (11 Policies)", "Persistence: SQLite (WAL Mode)", "Data Pack SHA-256 Verified".
- Click on **"Policy Catalog (11 Policies)"** tab. Briefly highlight `KB-01` to `KB-10` and `POL-ASSET-01`. Show the exact source quotes and section citations.

---

## Segment 2: Multi-Turn Missing Information & Diagnostic Flow (1:00 – 2:15)

### Scenario:
Employee Sarah Jenkins has a malfunctioning printer (`KB-05`). The system must enforce mandatory self-service spooler restart before creating a hardware ticket, and must collect the mandatory asset tag.

### Step 2A: Turn 1 (Incomplete Request)
- Switch to **"Service Dialogue"** tab.
- Set Active Employee Profile: `EMP-2091 • Sarah Jenkins (Design)`.
- Click scenario prompt or type:
  ```text
  The 3rd-floor printer is jamming and won't print.
  ```
- Click **Send Request**.

### Expected Agent Behavior to Highlight:
- The Agent replies under `KB-05` that before a technician can be dispatched, the employee must perform the mandatory initial troubleshooting step: restarting the local print spooler service.
- **Show 3-Layer Defense Demarcation**:
  - **Layer 1 (LLM Extraction)**: Tagged `NON-AUTHORITATIVE (ROUTING HINT ONLY)`. Shows candidate policy `KB-05` and extracted slot `device_type: printer`.
  - **Layer 2 (Policy Engine)**: Tagged `AUTHORITATIVE`. Outcome: `INITIAL_DIAGNOSTIC_REQUIRED`. Citation: `[DataPack: KB-05 - Network Printer Troubleshooting, Page 1] § Section 1`.
  - **Layer 3 (Coordinator)**: Workflow action: `ASK_FOLLOW_UP`.

### Step 2B: Turn 2 (Clarification & Asset Tag Request)
- Type response as Sarah:
  ```text
  I restarted the spooler service like you said, but it's still not printing.
  ```
- Click **Send Request**.
- The Agent retains the accumulated context from Turn 1 (persisted in SQLite), detects that spooler troubleshooting was attempted, and now asks for the physical printer asset tag.

### Step 2C: Turn 3 (Asset Tag Provided -> Ticket Created)
- Type response:
  ```text
  The asset tag on the printer is PRN-FL3-02.
  ```
- Click **Send Request**.
- The Agent recognizes that all mandatory requirements for `KB-05` are now satisfied:
  - Action: `CREATE_TICKET`.
  - Queue: `Hardware Support`.
  - Ticket ID: `TCK-2026-XXXX`.
  - State persisted to SQLite.

---

## Segment 3: Source Citation & Dual Approvals (2:15 – 3:30)

### Scenario:
Employee Aditi Sharma requests a replacement for a 3.5-year-old laptop with a dead motherboard (`KB-03` + `POL-ASSET-01`).

### Action:
- Set Employee Profile: `EMP-4102 • Aditi Sharma (Engineering)`.
- Click scenario prompt:
  ```text
  My laptop won’t turn on at all, it’s completely dead, had it about 3.5 years now.
  ```
- Click **Send Request**.

### Expected Behavior to Highlight:
- Point out the deterministic policy evaluation:
  - Laptop age is 3.5 years (>= 3.0 years eligibility threshold under `KB-03`).
  - Hardware failure is verified (completely dead).
  - However, under the Asset Management Policy (`POL-ASSET-01`), the standard refresh cycle is 4.0 years.
  - Therefore, early replacement requires dual sign-offs: **Finance sign-off** in addition to **IT approval**.
- Ticket is generated with status `PENDING_APPROVAL`.
- Point out both exact citations displayed in the UI:
  `[DataPack: KB-03 - Laptop Replacement, Page 1] & [DataPack: POL-ASSET-01, Page 1]`.

---

## Segment 4: Boundary Enforcement & Storage Quota Disallowance (3:30 – 4:15)

### Scenario:
Employee requests an 80GB cloud storage quota (`KB-06`).

### Action:
- Type in chat:
  ```text
  I am running a big project and need to increase my cloud storage quota to 80GB.
  ```
- Click **Send Request**.

### Expected Behavior to Highlight:
- Under `KB-06`, the default quota is 25GB. Increases up to 50GB require manager approval.
- An increase to 80GB exceeds the 50GB policy cap and is **strictly disallowed**.
- **Defense Highlight**: The Agent does NOT hallucinate an exception or create an approval ticket. The deterministic policy engine marks the request `DISALLOWED`, and the coordinator resolves the dialogue with a clear policy explanation and citation.

---

## Segment 5: Security Incident Immediate Escalation (4:15 – 4:55)

### Scenario:
Employee Elena Rostova reports clicking a phishing link (`KB-09`).

### Action:
- Set Employee Profile: `EMP-8831 • Elena Rostova (HR)`.
- Click scenario prompt:
  ```text
  I accidentally clicked on a suspicious link asking for my credentials in an email.
  ```
- Click **Send Request**.

### Expected Behavior to Highlight:
- The system immediately triggers `KB-09` (Security Incident Reporting).
- Action: **`ESCALATE`**.
- Target Queue: `Security Operations`.
- Priority: `CRITICAL` (Sev-1).
- Stated SLA: **15-minute response window**.
- Immediate advice provided to the employee (disconnect device / reset credentials) while the ticket is routed directly to SecOps.

---

## Segment 6: Live 1-Click Benchmark Suite Execution (4:55 – 6:00)

### Spoken Narration:
> *"Now let us look at our empirical verification. We will run all 15 benchmark requests from Section 2 of the Data Pack live through the actual end-to-end coordinator."*

### Action:
- Click on the **"Benchmark Suite (15 Cases)"** tab.
- Point out the real execution flow banner: `Frontend -> Benchmark API -> AgentCoordinator -> LLM Provider -> Session State (SQLite) -> Policy Engine -> Ticket/Audit -> Benchmark Result`.
- Click the green **"Run Benchmark Suite Live (15 Cases)"** button.
- Watch the live execution complete in under 1 second.

### Results to Highlight:
- Conformance Banner: **"15/15 benchmark cases passed (100.0% benchmark conformance)"**.
- Highlight that we use rigorous engineering terminology, never claiming "AI accuracy = 100%".
- Total cases: 15. Conforming: 15 (100.0%). Average latency: ~58ms per case.
- Click **"Inspect"** on REQ-01 (Aditi Sharma) and REQ-13 (Aman Gupta) to show the underlying request text, authoritative rule outcome, citation, and generated ticket.

---

## Segment 7: SQLite Persistence & Audit Trail Inspection (6:00 – 6:45)

### Action:
1. Click on **"Ticket Queue"** tab:
   - Show all structured tickets created during our live interactions and benchmark run.
   - Point out priorities, queues (`Hardware Support`, `Security Operations`), and required approvals (`Finance sign-off`, `IT approval`).
2. Click on **"Audit Trail"** tab:
   - Highlight the **Append-Only Audit Event Model**.
   - Show chronological log of events with event IDs, timestamps, employee IDs, policy rule IDs, actions, and actors.
   - Clarify that these records are stored in SQLite table `audit_events` in `./veridian.db`.

---

## Segment 8: Conclusion & Q&A Readiness (6:45 – 7:00)

### Spoken Narration:
> *"To conclude: Veridian Assist demonstrates how enterprise AI can be deployed safely in IT operations. By treating the LLM strictly as a non-authoritative parser and delegating all policy enforcement to a deterministic Python engine grounded in the Data Pack, we eliminate hallucination, guarantee 100% benchmark conformance, and maintain a durable SQLite audit trail.
>
> Thank you. I am now open for technical defense questions."*
