# Veridian Assist — 10-Slide Presentation Outline
## Assignment 2: Agentic AI Factory — Technical Defense & Walkthrough

---

### Slide 1: Title & Executive Overview
* **Slide Title**: Veridian Assist: Enterprise IT Service Agent
* **Subtitle**: Individual Submission — Assignment 2 (Agentic AI Factory)
* **Presenter**: Prince Jha
* **Core Value Proposition**: An agentic IT support system that automates tier-1 resolutions, enforces deterministic policy compliance, asks targeted follow-up questions, escalates high-risk requests, and maintains an immutable audit trail.
* **Key Highlights**:
  - Authoritative Data Pack ground truth
  - Strict decoupling of LLM from Policy Authority
  - Next.js + FastAPI + SQLite micro-architecture
  - Production-ready auditability and defensible decision logs

---

### Slide 2: The Enterprise IT Challenge & Problem Statement
* **Slide Title**: Challenges in Enterprise IT Tier-1 Support
* **Key Pain Points**:
  - High ticket volume of routine, repetitive inquiries (password resets, software requests, standard hardware setups).
  - Risk of human or LLM hallucinations when interpreting corporate compliance rules.
  - Failure to collect mandatory troubleshooting parameters up-front, causing excessive back-and-forth email loops.
  - Inconsistent escalation paths and lack of transparent audit trails for security-sensitive actions.
* **Goal**: Build an autonomous, compliant service agent that resolves safe requests, enforces rigorous governance, and creates structured tickets with full traceability.

---

### Slide 3: Core Engineering Principle: Decoupling LLM from Policy Authority
* **Slide Title**: Architectural Governance: Why the LLM is Not the Policy Engine
* **The Danger**: Treating an LLM as the ultimate authority introduces non-deterministic hallucinations, policy bypasses, and security vulnerabilities.
* **The Solution — Four-Layer Separation**:
  - **LLM Responsibility**: Semantic comprehension, intent classification, entity extraction, conversational phrasing.
  - **Policy Engine Responsibility**: Deterministic rule evaluation, permission checking, escalation triggers.
  - **Workflow Engine**: Enforcing state transitions (`ASK_FOLLOW_UP`, `RESOLVE`, `ESCALATE`, `CREATE_TICKET`).
  - **Database**: Immutable records of policies, requests, tickets, and audit logs.

---

### Slide 4: End-to-End System Architecture
* **Slide Title**: System Architecture & Request Lifecycle
* **Visual Components**:
  - Next.js Web Portal (Employee Chat, Ticket Queue, Audit Explorer)
  - FastAPI Gateway with Pydantic validation
  - Pluggable LLM Provider Abstraction (Gemini / OpenAI / Mock)
  - Deterministic Policy & Decision Engine
  - Structured Ticket Manager & Append-Only Audit Trail
* **Flow**: Request Arrival → Intent Classification → Authoritative Policy Check → Action Decision → Response & Ticket Creation → Audit Recording.

---

### Slide 5: The Authoritative Knowledge Layer (Data Pack)
* **Slide Title**: Authoritative Knowledge: Zero Hallucination Policy
* **Data Source**: `Assignment_2_DataPack.pdf` (Veridian Corp Knowledge-Base & Policies).
* **Integrity & Governance Rules**:
  - Strict preservation of the original source document.
  - Zero synthetic or invented policies, approval chains, or SLAs.
  - When facts are missing from the Data Pack, the system refuses to guess and safely escalates.
  - Every answer returned to an employee explicitly cites the specific policy ID and clause.

---

### Slide 6: Intelligent Dialogue & Follow-Up Question Engine
* **Slide Title**: Active Information Gathering: Asking the Right Questions
* **The Mechanism**:
  - Policies often demand specific parameters (e.g. Asset Tag, Employee ID, Software License Name, Department Code).
  - Rather than rejecting requests or giving vague generic advice, the system identifies missing critical parameters.
  - Initiates the `ASK_FOLLOW_UP` action with targeted questions before evaluating final policy resolution.
* **Example Scenario**: Employee asks "Can I install software X?" → Agent identifies missing operating system and device asset tag → Prompts for exact missing details.

---

### Slide 7: Deterministic Escalation & Risk Mitigation
* **Slide Title**: Risk Control: Automated Escalation Logic
* **Escalation Triggers**:
  - Administrative privileges and security bypass requests.
  - Hardware replacements exceeding tier thresholds.
  - Unclear or out-of-scope employee requests.
  - Unapproved external cloud storage access.
* **Outcome**:
  - Instant transition to `ESCALATE` action.
  - Automatic generation of a structured IT ticket (`HIGH` or `CRITICAL` severity).
  - Clear rationale provided to the employee with assigned queue and escalation notes.

---

### Slide 8: Structured Ticket Lifecycle & Queue Management
* **Slide Title**: Ticket Management & Operational Handoff
* **Structured Data Contract**:
  - Ticket ID (`TCK-YYYY-XXXX`)
  - Employee ID & Department
  - Category, Severity, and Policy Reference
  - Action Taken & Escalation Justification
* **Status Transitions**: `OPEN` → `IN_PROGRESS` → `RESOLVED` / `ESCALATED` → `CLOSED`.
* **Seamless IT Operations**: IT staff can review, filter, and take over tickets directly from the queue with full historical context.

---

### Slide 9: Immutable Audit Trail & Regulatory Compliance
* **Slide Title**: Full Traceability: Every Action Audited
* **Audit Architecture**:
  - Append-only event log capturing every request, extraction, evaluation, and transition.
  - Key fields: Event ID, UTC Timestamp, Actor, Event Type, Policy Citation, State Payload.
* **Compliance Value**:
  - Complete defense against security audits.
  - Eliminates "black box" AI concerns by recording exact inputs, extracted facts, and matched policy clauses.
  - Verifiable evidence for compliance frameworks (ISO/IEC 42001, SOC 2).

---

### Slide 10: Live Demonstration, Tech Stack & Roadmap
* **Slide Title**: Technology Implementation & Production Roadmap
* **Tech Stack**:
  - **Frontend**: Next.js 15, TypeScript, Tailwind CSS
  - **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, SQLite
  - **LLM Layer**: Pluggable provider abstraction with Gemini / OpenAI support
* **Phase Progression**:
  - Phase 1: Foundation, Architecture & Scaffolding (Completed)
  - Phase 2: Authoritative Knowledge Extraction & Policy Engine
  - Phase 3: Agentic Reasoning & Decision Engine
  - Phase 4: Frontend UI & Interactive Chat Interface
  - Phase 5: Verification, Defense Walkthrough & Video Recording
