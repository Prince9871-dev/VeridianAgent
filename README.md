# Veridian Assist — Internal IT Service Agent

> **Assignment 2: Agentic AI Factory**  
> **Individual Submission by Prince Jha**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15+-black.svg?style=flat&logo=next.js)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg?style=flat&logo=typescript)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC.svg?style=flat&logo=tailwind-css)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg?style=flat&logo=python)](https://python.org)

---

## 1. Project Overview

**Veridian Assist** is an internal IT service assistant built for **Veridian Corp**. The system processes employee support requests through an intelligent, policy-governed workflow that:

1. **Understands the employee's issue** using natural language understanding and parameter extraction.
2. **Finds the relevant company policy or resolution** deterministically from the company's knowledge base.
3. **Asks sensible follow-up questions** when mandatory troubleshooting or policy information is missing.
4. **Resolves simple, authorized requests** directly without manual intervention.
5. **Escalates risky or sensitive requests** (e.g. privilege escalation, unapproved software/hardware) to human IT teams.
6. **Escalates unclear or unsupported requests** rather than hallucinating answers.
7. **Creates structured tracking tickets** (`TCK-YYYY-XXXX`) with categorized severity and tags.
8. **Displays the exact authoritative source citation** used for every resolution or decision.
9. **Maintains an immutable audit trail** recording all state changes and rationale.

---

## 2. Core Engineering Principle: Decoupling LLM from Policy Authority

```
┌─────────────────────────────────────────────────────────────┐
│                    VERIDIAN ASSIST ARCHITECTURE             │
└─────────────────────────────────────────────────────────────┘
                               │
       ┌───────────────────────┴───────────────────────┐
       ▼                                               ▼
┌───────────────────────────────┐     ┌───────────────────────────────┐
│       LLM RESPONSIBILITIES     │     │     POLICY & DECISION ENGINE  │
├───────────────────────────────┤     ├───────────────────────────────┤
│ • Natural Language Input      │     │ • Authoritative Policy Rules  │
│ • Intent Classification       │     │ • Deterministic Conditions    │
│ • Entity & Fact Extraction    │     │ • Permission Validation       │
│ • Missing Info Identification │     │ • Mandatory Escalation Logic  │
│ • Conversational Synthesis    │     │ • Resolution Authority        │
└───────────────────────────────┘     └───────────────────────────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   ▼
                      ┌─────────────────────────┐
                      │     WORKFLOW ACTIONS    │
                      ├─────────────────────────┤
                      │ • ASK_FOLLOW_UP         │
                      │ • RESOLVE               │
                      │ • ESCALATE              │
                      │ • CREATE_TICKET         │
                      └─────────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │    DATABASE & AUDIT     │
                      ├─────────────────────────┤
                      │ • SQLite State Store    │
                      │ • Immutable Audit Logs  │
                      │ • Structured Tickets    │
                      └─────────────────────────┘
```

> **CRITICAL ARCHITECTURAL BOUNDARY:**  
> The Large Language Model (LLM) is **NOT** the authority on company policy. The LLM understands and extracts; the Policy Engine validates and dictates permissions; the Workflow Engine enacts actions; the Audit Engine preserves the evidence.

---

## 3. Authoritative Knowledge Layer

* **Source Document**: `data/source/Assignment_2_DataPack.pdf`
* **Integrity**: Preserved byte-for-byte (`SHA-256: 21A5ED364EF5063F10B73E349DA3665270C1DB3FE51F85BE91F8E3E347805C50`).
* **Zero Synthetic Policies**: No fabricated policies, SLAs, or permissions are introduced. If a request cannot be verified from the Data Pack, it triggers an escalation rather than a hallucination.

---

## 4. Repository Structure

```
veridian-internal-service-agent/
│
├── frontend/                     # Next.js App Router + TypeScript + Tailwind CSS
│   ├── src/
│   │   ├── app/                  # UI routes and portal layout
│   │   └── components/           # UI components (Chat, Tickets, Audit, Policy)
│   ├── public/                   # Static assets
│   ├── Dockerfile                # Production frontend container
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                      # Python FastAPI Backend
│   ├── app/
│   │   ├── agent/                # LLM provider abstraction (Base, Gemini, OpenAI, Mock)
│   │   ├── policy/               # Deterministic Policy & Decision Engine
│   │   ├── tickets/              # Ticket lifecycle management
│   │   ├── audit/                # Immutable audit event logging
│   │   ├── models/               # Pydantic schemas (common, ticket, audit, request)
│   │   ├── db/                   # Async SQLite database session
│   │   ├── api/                  # FastAPI routers (health, tickets, audit)
│   │   ├── config.py             # BaseSettings configuration
│   │   └── main.py               # Application entrypoint & CORS middleware
│   ├── requirements.txt          # Pinned backend dependencies
│   └── Dockerfile                # Production backend container
│
├── data/
│   └── source/
│       └── Assignment_2_DataPack.pdf  # Authoritative Veridian Corp Data Pack
│
├── docs/
│   ├── ARCHITECTURE.md           # Full architectural specification with diagrams
│   └── SLIDES_OUTLINE.md         # 10-slide technical defense presentation outline
│
├── tests/                        # Automated unit and integration tests
│   ├── test_datapack.py          # Data Pack existence & integrity validation
│   └── test_foundation.py        # Backend health, config & API validation
│
├── .env.example                  # Documented environment template
├── .gitignore                    # Comprehensive ignore rules
├── docker-compose.yml            # Multi-service local orchestration
└── README.md                     # This document
```

---

## 5. Quickstart & Local Setup

### Prerequisites
* Python 3.12+
* Node.js 20+ & npm
* Git

### Option A: Local Development

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd veridian-internal-service-agent
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env and supply your LLM_PROVIDER and API key
   ```

3. **Backend Setup**:
   ```bash
   python -m venv .venv
   # Windows:
   .\.venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r backend/requirements.txt
   uvicorn backend.app.main:app --reload --port 8000
   ```
   API Docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)  
   Health endpoint: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

4. **Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Portal interface available at: [http://localhost:3000](http://localhost:3000)

### Option B: Docker Compose

```bash
docker-compose up --build
```

---

## 6. Running Automated Tests

```bash
# Run tests using the virtual environment
.\.venv\Scripts\pytest tests -v
```

---

## 7. Development Roadmap

- [x] **Phase 1: Foundation & Architecture**
  - Authoritative Data Pack preservation & checksum verification
  - FastAPI modular backend with clean LLM provider abstraction
  - Strict separation of concerns (LLM vs Policy Engine vs Workflow vs Database)
  - Next.js + TypeScript + Tailwind CSS portal foundation
  - Comprehensive documentation & 10-slide defense outline
- [ ] **Phase 2: Authoritative Knowledge Layer & Policy Extraction**
- [ ] **Phase 3: Agentic Reasoning & Policy Decision Engine**
- [ ] **Phase 4: Employee Portal UI & Interactive Dialogue**
- [ ] **Phase 5: Technical Defense, Video Demonstration & Final Submission**
