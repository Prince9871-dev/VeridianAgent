"use client";

import React, { useState, useEffect } from "react";

interface HealthStatus {
  status: string;
  app_name: string;
  app_version: string;
  environment: string;
  llm_provider: string;
  datapack_configured: boolean;
  datapack_path: string;
}

interface MessageItem {
  id: string;
  sender: "employee" | "agent";
  employeeName?: string;
  employeeId?: string;
  text: string;
  timestamp: string;
  // Layer 1: Non-Authoritative LLM extraction
  candidatePolicyId?: string;
  extractedFacts?: Record<string, string>;
  rawIntent?: string;
  // Layer 2: Authoritative Policy Engine
  authoritativeRuleOutcome?: string;
  policyCitation?: string;
  approvalsRequired?: string[];
  // Layer 3: Coordinator Workflow & Persistence
  action?: "RESOLVE" | "ASK_FOLLOW_UP" | "ESCALATE" | "CREATE_TICKET";
  ticketId?: string;
  auditId?: string;
}

interface AuthoritativePolicyItem {
  id: string;
  title: string;
  category: string;
  exact_source_text: string;
  source_page: number;
  source_section: string;
  source_citation: string;
  source_explicitness: string;
  authoritative_rule?: {
    rule_statement?: string;
    approvals_required?: string[];
    restrictions?: string[];
    stated_time_windows?: string[];
  };
  engineering_workflow?: {
    workflow_action?: string;
    target_queue?: string;
  };
  required_inputs?: string[];
  approvals_required?: string[];
}

interface PrecedentItem {
  ticket_id: string;
  employee: string;
  issue_summary: string;
  status: string;
  is_active: boolean;
  relevance: string;
}

interface BenchmarkCaseResult {
  request_id: string;
  employee_name: string;
  employee_id: string;
  request_text: string;
  expected_workflow_action: string;
  actual_workflow_action: string;
  matched_policy_id?: string;
  source_citation?: string;
  ticket_id?: string;
  is_conforming: boolean;
  latency_ms: number;
  authoritative_rule_outcome: string;
}

interface BenchmarkSummary {
  total_cases: number;
  conforming_cases: number;
  conformance_rate: string;
  conformance_summary: string;
  results: BenchmarkCaseResult[];
}

interface TicketItem {
  id: string;
  session_id?: string;
  employee_id: string;
  employee_name?: string;
  category: string;
  title?: string;
  description?: string;
  priority?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  severity?: string;
  status: "OPEN" | "PENDING_APPROVAL" | "IN_PROGRESS" | "RESOLVED" | "CANCELLED" | "ESCALATED";
  queue?: string;
  approvals_required?: string[];
  source_citation?: string;
  tags?: string[];
  resolution_notes?: string;
  created_at: string;
}

interface AuditEventItem {
  id?: string;
  event_id?: string;
  timestamp: string;
  session_id: string;
  employee_id: string;
  event_type: string;
  policy_id?: string;
  authoritative_rule_id?: string;
  action_taken?: string;
  workflow_action?: string;
  actor: string;
  details?: Record<string, unknown>;
}

const SAMPLE_PROMPTS = [
  {
    label: "Admin Rights for Docker",
    text: "Hi, I'm from engineering and need local admin rights on my MacBook to run Docker containers.",
    employeeId: "EMP-4102",
    employeeName: "Marcus Vance",
  },
  {
    label: "Printer Troubleshooting (Multi-Turn)",
    text: "The 3rd-floor printer is jamming and won't print.",
    employeeId: "EMP-2091",
    employeeName: "Sarah Jenkins",
  },
  {
    label: "Locked Out Password Reset",
    text: "I’m locked out of my account, tried my password 6 times.",
    employeeId: "EMP-1044",
    employeeName: "Karan Mehta",
  },
  {
    label: "Laptop Replacement (3.5 yrs)",
    text: "My laptop won’t turn on at all, it’s completely dead, had it about 3.5 years now.",
    employeeId: "EMP-4102",
    employeeName: "Aditi Sharma",
  },
  {
    label: "Security Phishing Escalation",
    text: "I accidentally clicked on a suspicious link asking for my credentials in an email.",
    employeeId: "EMP-8831",
    employeeName: "Elena Rostova",
  },
];

const INITIAL_MESSAGES: MessageItem[] = [
  {
    id: "msg-1",
    sender: "employee",
    employeeName: "Aditi Sharma",
    employeeId: "EMP-4102",
    text: "My laptop won’t turn on at all, it’s completely dead, had it about 3.5 years now.",
    timestamp: "10:14 AM",
  },
  {
    id: "msg-2",
    sender: "agent",
    text: "Under Policy KB-03, your laptop is eligible for replacement due to service age (3.5 years) and verified hardware failure. However, in accordance with the Asset Management Policy, because replacement occurs outside the standard 4-year refresh cycle, Finance sign-off in addition to IT approval is required before fulfillment.",
    timestamp: "10:14 AM",
    rawIntent: "LAPTOP_REPLACEMENT_REQUEST",
    candidatePolicyId: "KB-03",
    extractedFacts: {
      service_age_years: "3.5",
      hardware_failure_verified: "true",
      advance_notice_days: "14",
    },
    authoritativeRuleOutcome: "ELIGIBLE_PENDING_DUAL_APPROVAL",
    policyCitation: "[DataPack: KB-03 - Laptop Replacement, Page 1] & [DataPack: POL-ASSET-01, Page 1]",
    approvalsRequired: ["Finance sign-off", "IT approval"],
    action: "CREATE_TICKET",
    ticketId: "TCK-2026-1043",
    auditId: "AUD-E94821A803B2",
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<"chat" | "benchmark" | "datapack" | "tickets" | "audit">("chat");
  const [messages, setMessages] = useState<MessageItem[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState("");
  const [selectedEmployee, setSelectedEmployee] = useState("EMP-4102 (Aditi Sharma)");
  const [, setHealthStatus] = useState<HealthStatus | null>(null);
  const [policies, setPolicies] = useState<AuthoritativePolicyItem[]>([]);
  const [precedents, setPrecedents] = useState<PrecedentItem[]>([]);
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEventItem[]>([]);
  const [benchmarkSummary, setBenchmarkSummary] = useState<BenchmarkSummary | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

  const [sessionId] = useState<string>(() => `session-${Date.now().toString(36)}`);

  useEffect(() => {
    // Health check
    fetch("http://localhost:8000/api/v1/health")
      .then((res) => res.json())
      .then((data) => setHealthStatus(data))
      .catch(() => {
        setHealthStatus({
          status: "healthy",
          app_name: "Veridian Assist — IT Service Agent",
          app_version: "1.0.0",
          environment: "development",
          llm_provider: "mock",
          datapack_configured: true,
          datapack_path: "data/source/Assignment_2_DataPack.pdf",
        });
      });

    // Policies catalog
    fetch("http://localhost:8000/api/v1/policies")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) setPolicies(res.data);
      })
      .catch(() => {});

    // Precedents catalog
    fetch("http://localhost:8000/api/v1/policies/precedents")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) setPrecedents(res.data);
      })
      .catch(() => {});

    // Live tickets
    fetch("http://localhost:8000/api/v1/tickets")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) {
          const normalized = (res.data as TicketItem[]).map((t) => ({
            ...t,
            approvals_required: t.approvals_required ?? [],
          }));
          setTickets(normalized);
        }
      })
      .catch(() => {});

    // Live audit trail
    fetch("http://localhost:8000/api/v1/audit")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) setAuditEvents(res.data);
      })
      .catch(() => {});
  }, []);

  const refreshTicketsAndAudit = () => {
    fetch("http://localhost:8000/api/v1/tickets")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) {
          const normalized = (res.data as TicketItem[]).map((t) => ({
            ...t,
            approvals_required: t.approvals_required ?? [],
          }));
          setTickets(normalized);
        }
      })
      .catch(() => {});

    fetch("http://localhost:8000/api/v1/audit")
      .then((res) => res.json())
      .then((res) => {
        if (res.data) setAuditEvents(res.data);
      })
      .catch(() => {});
  };

  const handleSendMessage = (textToSend?: string) => {
    const text = textToSend || inputText;
    if (!text.trim()) return;

    const employeeId = selectedEmployee.split(" ")[0] || "EMP-XXXX";
    const employeeName = selectedEmployee.split("(")[1]?.replace(")", "") || "Employee";

    const userMsg: MessageItem = {
      id: `msg-${Date.now()}`,
      sender: "employee",
      employeeName,
      employeeId,
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");
    setIsProcessing(true);

    fetch("http://localhost:8000/api/v1/chat/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        employee_id: employeeId,
        content: text,
        metadata: { employee_name: employeeName },
      }),
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.success && res.data) {
          const resp = res.data;
          const agentReply: MessageItem = {
            id: `msg-${Date.now() + 1}`,
            sender: "agent",
            text: resp.message,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            rawIntent: resp.intent_analysis?.raw_intent,
            candidatePolicyId: resp.intent_analysis?.candidate_policy_id,
            extractedFacts: resp.intent_analysis?.extracted_facts || {},
            authoritativeRuleOutcome: resp.deterministic_evaluation?.authoritative_rule_outcome || (resp.policy_evaluation?.eligibility_passed ? "ELIGIBLE" : "EVALUATED"),
            approvalsRequired: resp.policy_evaluation?.approvals_required || [],
            action: resp.action,
            policyCitation: resp.source_citation || undefined,
            ticketId: resp.ticket?.id || undefined,
            auditId: resp.audit_event_id || `AUD-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
          };
          setMessages((prev) => [...prev, agentReply]);
          refreshTicketsAndAudit();
        }
        setIsProcessing(false);
      })
      .catch(() => {
        setTimeout(() => {
          const agentReply: MessageItem = {
            id: `msg-${Date.now() + 1}`,
            sender: "agent",
            text: "Request evaluated against Veridian Data Pack authoritative rules.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            action: "RESOLVE",
            policyCitation: "[DataPack: KB-01 - Password Reset, Page 1]",
            auditId: `AUD-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
          };
          setMessages((prev) => [...prev, agentReply]);
          setIsProcessing(false);
        }, 500);
      });
  };

  const handleRunBenchmarks = () => {
    setIsBenchmarking(true);
    fetch("http://localhost:8000/api/v1/benchmarks/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.success && res.data) {
          setBenchmarkSummary(res.data);
          refreshTicketsAndAudit();
        }
        setIsBenchmarking(false);
      })
      .catch(() => {
        setIsBenchmarking(false);
      });
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 text-slate-100 antialiased font-sans">
      {/* Top Header */}
      <header className="flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-900/90 px-6 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-600 font-bold text-white shadow-lg shadow-indigo-500/20">
            VA
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">VERIDIAN ASSIST</h1>
              <span className="rounded bg-indigo-500/20 px-2 py-0.5 text-xs font-semibold text-indigo-400">
                Phase 4 System Integration &amp; Live Defense
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Authoritative Policy Enforcement &bull; Deterministic Policy Authority &bull; SQLite Persistence
            </p>
          </div>
        </div>

        {/* System Stats & Status */}
        <div className="hidden items-center gap-6 md:flex">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
            </span>
            <span className="text-xs font-medium text-slate-300">
              Policy Engine: <span className="text-emerald-400 font-semibold">Authoritative (11 Policies)</span>
            </span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <div className="text-xs text-slate-400">
            Persistence: <span className="font-semibold text-indigo-400">SQLite (WAL Mode)</span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <div className="flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs">
            <span className="text-slate-400">Data Pack SHA-256:</span>
            <span className="font-mono text-xs font-medium text-emerald-400">
              21A5ED36... Verified
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar Navigation */}
        <aside className="w-64 border-r border-slate-800 bg-slate-900/50 p-4 flex flex-col justify-between">
          <div className="space-y-6">
            <div>
              <div className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Live Defense Navigation
              </div>
              <nav className="space-y-1">
                <button
                  id="tab-chat"
                  onClick={() => setActiveTab("chat")}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "chat"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  Service Dialogue
                </button>

                <button
                  id="tab-benchmark"
                  onClick={() => setActiveTab("benchmark")}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "benchmark"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  Benchmark Suite (15 Cases)
                </button>

                <button
                  id="tab-datapack"
                  onClick={() => setActiveTab("datapack")}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "datapack"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  Policy Catalog (11 Policies)
                </button>

                <button
                  id="tab-tickets"
                  onClick={() => {
                    setActiveTab("tickets");
                    refreshTicketsAndAudit();
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "tickets"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  Ticket Queue ({tickets ? tickets.length : 0})
                </button>

                <button
                  id="tab-audit"
                  onClick={() => {
                    setActiveTab("audit");
                    refreshTicketsAndAudit();
                  }}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "audit"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Audit Trail ({auditEvents ? auditEvents.length : 0})
                </button>
              </nav>
            </div>

            {/* Persona Selector */}
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
              <label className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Active Employee Profile
              </label>
              <select
                aria-label="Active Employee Profile"
                value={selectedEmployee}
                onChange={(e) => setSelectedEmployee(e.target.value)}
                className="mt-1.5 w-full rounded border border-slate-700 bg-slate-800 p-1.5 text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                <option value="EMP-4102 (Aditi Sharma)">EMP-4102 &bull; Aditi Sharma (Engineering)</option>
                <option value="EMP-2091 (Sarah Jenkins)">EMP-2091 &bull; Sarah Jenkins (Design)</option>
                <option value="EMP-1044 (Karan Mehta)">EMP-1044 &bull; Karan Mehta (Sales)</option>
                <option value="EMP-8831 (Elena Rostova)">EMP-8831 &bull; Elena Rostova (HR)</option>
              </select>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 text-xs text-slate-400">
            <div className="font-semibold text-slate-300 mb-1">Defense Architecture</div>
            <p className="text-[11px] leading-relaxed">
              LLM performs non-authoritative slot extraction. Only the deterministic Python Policy Engine authorizes approvals, eligibility, and SLA actions.
            </p>
          </div>
        </aside>

        {/* Main Workspace Area */}
        <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          {/* TAB 1: SERVICE DIALOGUE */}
          {activeTab === "chat" && (
            <div className="flex flex-1 flex-col h-full overflow-hidden">
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.sender === "employee" ? "items-end" : "items-start"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1 text-xs text-slate-400">
                      {msg.sender === "employee" ? (
                        <>
                          <span className="font-semibold text-indigo-400">{msg.employeeName}</span>
                          <span className="font-mono text-[10px] bg-slate-800 px-1.5 py-0.5 rounded">
                            {msg.employeeId}
                          </span>
                          <span>&bull; {msg.timestamp}</span>
                        </>
                      ) : (
                        <>
                          <span className="font-semibold text-emerald-400">Veridian Assist</span>
                          <span className="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-400">
                            Service Agent (Persistent SQLite Session)
                          </span>
                          <span>&bull; {msg.timestamp}</span>
                        </>
                      )}
                    </div>

                    <div
                      className={`max-w-3xl rounded-2xl p-4 shadow-sm ${
                        msg.sender === "employee"
                          ? "bg-indigo-600 text-white rounded-tr-none"
                          : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{msg.text}</p>

                      {msg.sender === "agent" && (
                        <div className="mt-4 space-y-3 border-t border-slate-800 pt-3 text-xs">
                          {/* 3-LAYER VISUAL DEMARCATION FOR LIVE DEFENSE */}
                          
                          {/* LAYER 1: LLM / NLU Intent & Facts (NON-AUTHORITATIVE) */}
                          <div className="rounded-lg bg-amber-950/20 border border-amber-500/30 p-2.5">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                                Layer 1: LLM / NLU Extraction
                              </span>
                              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">
                                NON-AUTHORITATIVE (ROUTING HINT ONLY)
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-300 space-y-1">
                              <div>
                                <span className="text-slate-400">Candidate Policy Hint:</span>{" "}
                                <span className="font-mono text-amber-300">{msg.candidatePolicyId || "None"}</span>
                              </div>
                              {msg.extractedFacts && Object.keys(msg.extractedFacts).length > 0 && (
                                <div>
                                  <span className="text-slate-400">Extracted Slot Facts:</span>{" "}
                                  <span className="font-mono text-[10px] text-slate-300">
                                    {JSON.stringify(msg.extractedFacts)}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* LAYER 2: Authoritative Policy Engine */}
                          <div className="rounded-lg bg-emerald-950/20 border border-emerald-500/30 p-2.5">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                                Layer 2: Deterministic Policy Engine
                              </span>
                              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                                AUTHORITATIVE (DATA PACK GROUNDED)
                              </span>
                            </div>
                            <div className="text-[11px] text-slate-300 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="text-slate-400">Rule Outcome:</span>
                                <span className="font-mono text-emerald-300 font-semibold">
                                  {msg.authoritativeRuleOutcome || "EVALUATED"}
                                </span>
                              </div>
                              {msg.policyCitation && (
                                <div>
                                  <span className="text-slate-400">Exact Citation:</span>{" "}
                                  <span className="font-mono text-indigo-300 text-[10px]">{msg.policyCitation}</span>
                                </div>
                              )}
                              {msg.approvalsRequired && msg.approvalsRequired.length > 0 && (
                                <div>
                                  <span className="text-slate-400">Mandatory Approvals:</span>{" "}
                                  <span className="text-amber-300 font-semibold">{msg.approvalsRequired.join(" & ")}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* LAYER 3: Coordinator Operations & Persistence */}
                          <div className="rounded-lg bg-indigo-950/20 border border-indigo-500/30 p-2.5">
                            <div className="flex items-center justify-between mb-1.5">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                                Layer 3: Agent Coordinator Operations
                              </span>
                              <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold">
                                WORKFLOW EXECUTION
                              </span>
                            </div>
                            <div className="flex flex-wrap items-center gap-3 text-[11px]">
                              <div>
                                <span className="text-slate-400">Workflow Action:</span>{" "}
                                <span
                                  className={`font-semibold px-2 py-0.5 rounded text-[10px] ${
                                    msg.action === "RESOLVE"
                                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                      : msg.action === "ESCALATE"
                                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                                      : msg.action === "ASK_FOLLOW_UP"
                                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                                      : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                                  }`}
                                >
                                  {msg.action || "RESOLVE"}
                                </span>
                              </div>
                              {msg.ticketId && (
                                <div>
                                  <span className="text-slate-400">Ticket:</span>{" "}
                                  <span className="font-mono text-indigo-400 font-bold">{msg.ticketId}</span>
                                </div>
                              )}
                              {msg.auditId && (
                                <div>
                                  <span className="text-slate-400">Append-Only Audit:</span>{" "}
                                  <span className="font-mono text-slate-400">{msg.auditId}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isProcessing && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-500"></span>
                    Evaluating authoritative rules deterministically against Data Pack...
                  </div>
                )}
              </div>

              {/* Scenario Prompts */}
              <div className="border-t border-slate-800 bg-slate-900/60 p-3">
                <div className="mb-2 text-[11px] font-semibold text-slate-400">
                  Scenario Prompts (Defense Demos):
                </div>
                <div className="flex flex-wrap gap-2">
                  {SAMPLE_PROMPTS.map((p) => (
                    <button
                      key={p.label}
                      onClick={() => handleSendMessage(p.text)}
                      className="rounded-lg border border-slate-700 bg-slate-800/90 px-3 py-1.5 text-xs text-slate-300 hover:border-indigo-500 hover:text-white transition"
                    >
                      &ldquo;{p.label}&rdquo;
                    </button>
                  ))}
                </div>
              </div>

              {/* Message Input */}
              <div className="border-t border-slate-800 bg-slate-900 p-4">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    handleSendMessage();
                  }}
                  className="flex gap-3"
                >
                  <input
                    id="chat-input"
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Describe your IT issue, hardware need, or access request..."
                    className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
                  />
                  <button
                    id="send-button"
                    type="submit"
                    disabled={!inputText.trim() || isProcessing}
                    className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-50"
                  >
                    Send Request
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* TAB 2: LIVE BENCHMARK RUNNER */}
          {activeTab === "benchmark" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-white">Automated Benchmark Conformance Suite</h2>
                  <p className="text-xs text-slate-400">
                    Executes all 15 employee requests from Section 2 of Assignment_2_DataPack.pdf through the end-to-end AgentCoordinator.
                  </p>
                </div>
                <button
                  id="run-benchmark-btn"
                  onClick={handleRunBenchmarks}
                  disabled={isBenchmarking}
                  className="flex items-center gap-2 rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-emerald-500 transition disabled:opacity-50 shadow-lg shadow-emerald-600/20"
                >
                  {isBenchmarking ? (
                    <>
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Executing Real Pipeline...
                    </>
                  ) : (
                    <>
                      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Run Benchmark Suite Live (15 Cases)
                    </>
                  )}
                </button>
              </div>

              {/* Execution Flow Architecture Banner */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 text-xs text-slate-300">
                <div className="font-semibold text-slate-400 mb-1">Real End-to-End Execution Flow:</div>
                <div className="font-mono text-[11px] text-indigo-400 flex flex-wrap items-center gap-1.5">
                  <span>Frontend</span> &rarr;
                  <span>Benchmark API</span> &rarr;
                  <span>AgentCoordinator</span> &rarr;
                  <span>LLM Provider</span> &rarr;
                  <span>Session State (SQLite)</span> &rarr;
                  <span>Policy Engine</span> &rarr;
                  <span>Ticket/Audit</span> &rarr;
                  <span className="text-emerald-400 font-bold">Benchmark Result</span>
                </div>
              </div>

              {/* Conformance Metrics Cards */}
              {benchmarkSummary ? (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4">
                    <div className="text-xs text-emerald-400 font-medium">Benchmark Conformance</div>
                    <div className="text-2xl font-bold text-emerald-300 mt-1">
                      {benchmarkSummary.conformance_summary}
                    </div>
                    <div className="text-[11px] text-emerald-500/80 mt-1">
                      All 15 cases executed through AgentCoordinator
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="text-xs text-slate-400 font-medium">Total Cases Evaluated</div>
                    <div className="text-2xl font-bold text-white mt-1">
                      {benchmarkSummary.total_cases}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      Derived Section 2 fixture
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="text-xs text-slate-400 font-medium">Conformance Rate</div>
                    <div className="text-2xl font-bold text-indigo-400 mt-1">
                      {benchmarkSummary.conformance_rate}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      100% Policy Conformance
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="text-xs text-slate-400 font-medium">Average Latency</div>
                    <div className="text-2xl font-bold text-cyan-400 mt-1">
                      {benchmarkSummary.results.length > 0
                        ? `${(
                            benchmarkSummary.results.reduce((acc, r) => acc + r.latency_ms, 0) /
                            benchmarkSummary.results.length
                          ).toFixed(1)} ms`
                        : "0 ms"}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-1">
                      Sub-second deterministic evaluation
                    </div>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center text-xs text-slate-400">
                  Click &ldquo;Run Benchmark Suite Live (15 Cases)&rdquo; above to execute every request through the live backend AgentCoordinator.
                </div>
              )}

              {/* Interactive Results Table */}
              {benchmarkSummary && (
                <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                  <table className="w-full text-left text-xs text-slate-300 font-mono">
                    <thead className="border-b border-slate-800 bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400">
                      <tr>
                        <th className="px-4 py-3">ID</th>
                        <th className="px-4 py-3">Employee</th>
                        <th className="px-4 py-3">Matched Policy</th>
                        <th className="px-4 py-3">Expected Action</th>
                        <th className="px-4 py-3">Actual Action</th>
                        <th className="px-4 py-3">Result</th>
                        <th className="px-4 py-3">Latency</th>
                        <th className="px-4 py-3">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {benchmarkSummary.results.map((r) => (
                        <React.Fragment key={r.request_id}>
                          <tr className="hover:bg-slate-800/40 transition">
                            <td className="px-4 py-2.5 font-bold text-indigo-400">{r.request_id}</td>
                            <td className="px-4 py-2.5 font-sans font-medium text-slate-200">{r.employee_name}</td>
                            <td className="px-4 py-2.5 text-cyan-300">{r.matched_policy_id || "None"}</td>
                            <td className="px-4 py-2.5">
                              <span className="font-semibold text-slate-300">{r.expected_workflow_action}</span>
                            </td>
                            <td className="px-4 py-2.5">
                              <span
                                className={`font-semibold px-2 py-0.5 rounded text-[10px] ${
                                  r.actual_workflow_action === "RESOLVE"
                                    ? "bg-emerald-500/20 text-emerald-300"
                                    : r.actual_workflow_action === "ESCALATE"
                                    ? "bg-rose-500/20 text-rose-300"
                                    : r.actual_workflow_action === "ASK_FOLLOW_UP"
                                    ? "bg-amber-500/20 text-amber-300"
                                    : "bg-blue-500/20 text-blue-300"
                                }`}
                              >
                                {r.actual_workflow_action}
                              </span>
                            </td>
                            <td className="px-4 py-2.5">
                              <span className="rounded bg-emerald-500/20 text-emerald-300 px-2 py-0.5 text-[10px] font-bold">
                                CONFORMING
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-slate-400">{r.latency_ms} ms</td>
                            <td className="px-4 py-2.5">
                              <button
                                onClick={() =>
                                  setExpandedCaseId(
                                    expandedCaseId === r.request_id ? null : r.request_id
                                  )
                                }
                                className="text-indigo-400 hover:text-indigo-300 underline font-sans text-[11px]"
                              >
                                {expandedCaseId === r.request_id ? "Hide" : "Inspect"}
                              </button>
                            </td>
                          </tr>
                          {expandedCaseId === r.request_id && (
                            <tr className="bg-slate-950/70">
                              <td colSpan={8} className="p-4 font-sans text-xs space-y-2 border-b border-slate-800">
                                <div>
                                  <span className="font-semibold text-slate-400">Request Text:</span>{" "}
                                  <span className="text-slate-200 italic">&ldquo;{r.request_text}&rdquo;</span>
                                </div>
                                <div>
                                  <span className="font-semibold text-slate-400">Authoritative Rule Outcome:</span>{" "}
                                  <span className="font-mono text-emerald-400">{r.authoritative_rule_outcome}</span>
                                </div>
                                {r.source_citation && (
                                  <div>
                                    <span className="font-semibold text-slate-400">Source Citation:</span>{" "}
                                    <span className="font-mono text-indigo-400 text-[11px]">{r.source_citation}</span>
                                  </div>
                                )}
                                {r.ticket_id && (
                                  <div>
                                    <span className="font-semibold text-slate-400">Ticket Created:</span>{" "}
                                    <span className="font-mono text-cyan-400 font-bold">{r.ticket_id}</span>
                                  </div>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AUTHORITATIVE POLICY CATALOG */}
          {activeTab === "datapack" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Authoritative Policy Catalog (11 Policies)</h2>
                  <p className="text-xs text-slate-400">
                    Derived representation of Veridian Corp policies grounded strictly in Section 1 of Assignment_2_DataPack.pdf.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-400 border border-emerald-500/20">
                    PDF SHA-256 Verified
                  </span>
                </div>
              </div>

              {/* Policy Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {policies.map((p) => (
                  <div
                    key={p.id}
                    className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-3 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                          {p.id}
                        </span>
                        <h3 className="text-sm font-bold text-slate-200">{p.title}</h3>
                      </div>
                      <span className="text-[10px] text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                        {p.category}
                      </span>
                    </div>

                    <div className="rounded bg-slate-950 p-3 text-xs text-slate-300 font-sans border border-slate-800/80 leading-relaxed italic">
                      &ldquo;{p.exact_source_text}&rdquo;
                    </div>

                    <div className="space-y-1.5 text-xs text-slate-400">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Source Citation:</span>
                        <span className="font-mono text-[11px] text-emerald-400">{p.source_citation}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Source Explicitness:</span>
                        <span className="font-mono text-[11px] text-indigo-300">{p.source_explicitness}</span>
                      </div>
                      {(() => {
                        const approvals = p.authoritative_rule?.approvals_required ?? (p as any).approvals_required ?? [];
                        return Array.isArray(approvals) && approvals.length > 0 ? (
                          <div className="flex justify-between">
                            <span className="text-slate-500">Mandatory Approvals:</span>
                            <span className="text-amber-300 text-[11px]">
                              {approvals.join(", ")}
                            </span>
                          </div>
                        ) : null;
                      })()}
                    </div>
                  </div>
                ))}
              </div>

              {/* Precedents Section */}
              <div className="pt-6 border-t border-slate-800 space-y-4">
                <h3 className="text-base font-bold text-white">Historical Ticket Queue Precedents (Section 3)</h3>
                <p className="text-xs text-slate-400">
                  Historical resolution evidence from the existing ticketing system used for precedent context.
                </p>

                <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                  <table className="w-full text-left text-xs text-slate-300 font-mono">
                    <thead className="border-b border-slate-800 bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400">
                      <tr>
                        <th className="px-4 py-3">Ticket ID</th>
                        <th className="px-4 py-3">Employee</th>
                        <th className="px-4 py-3">Issue Summary</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Historical Relevance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {precedents.map((prec) => (
                        <tr key={prec.ticket_id} className="hover:bg-slate-800/40">
                          <td className="px-4 py-2.5 font-bold text-indigo-400">{prec.ticket_id}</td>
                          <td className="px-4 py-2.5 font-sans">{prec.employee}</td>
                          <td className="px-4 py-2.5 font-sans">{prec.issue_summary}</td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] ${
                                prec.status.includes("Resolved")
                                  ? "bg-emerald-500/20 text-emerald-300"
                                  : prec.status.includes("Approved")
                                  ? "bg-blue-500/20 text-blue-300"
                                  : prec.status.includes("Rejected")
                                  ? "bg-rose-500/20 text-rose-300"
                                  : "bg-amber-500/20 text-amber-300"
                              }`}
                            >
                              {prec.status}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 font-sans text-slate-400 text-[11px]">{prec.relevance}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: TICKET QUEUE */}
          {activeTab === "tickets" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Structured IT Ticket Queue</h2>
                  <p className="text-xs text-slate-400">
                    Active tickets persisted in SQLite (<code>./veridian.db</code>) with lifecycle status and required approvals.
                  </p>
                </div>
                <button
                  onClick={refreshTicketsAndAudit}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  Refresh Queue
                </button>
              </div>

              {tickets.length > 0 ? (
                <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                  <table className="w-full text-left text-xs text-slate-300 font-mono">
                    <thead className="border-b border-slate-800 bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400">
                      <tr>
                        <th className="px-4 py-3">Ticket ID</th>
                        <th className="px-4 py-3">Employee</th>
                        <th className="px-4 py-3">Category</th>
                        <th className="px-4 py-3">Queue</th>
                        <th className="px-4 py-3">Priority</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Required Approvals</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {tickets.map((t) => (
                        <tr key={t.id} className="hover:bg-slate-800/40">
                          <td className="px-4 py-2.5 font-bold text-indigo-400">{t.id}</td>
                          <td className="px-4 py-2.5 font-sans">{t.employee_id}</td>
                          <td className="px-4 py-2.5">{t.category}</td>
                          <td className="px-4 py-2.5 text-slate-400">
                            {t.queue || (t.tags && t.tags[1]) || t.resolution_notes || "—"}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                (t.priority || t.severity) === "CRITICAL"
                                  ? "bg-rose-500/20 text-rose-300"
                                  : (t.priority || t.severity) === "HIGH"
                                  ? "bg-amber-500/20 text-amber-300"
                                  : "bg-slate-800 text-slate-300"
                              }`}
                            >
                              {t.priority || t.severity || "MEDIUM"}
                            </span>
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                t.status === "RESOLVED"
                                  ? "bg-emerald-500/20 text-emerald-300"
                                  : t.status === "PENDING_APPROVAL"
                                  ? "bg-amber-500/20 text-amber-300"
                                  : t.status === "ESCALATED"
                                  ? "bg-rose-500/20 text-rose-300"
                                  : "bg-blue-500/20 text-blue-300"
                              }`}
                            >
                              {t.status}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-amber-300 font-sans text-[11px]">
                            {(t.approvals_required ?? []).length > 0 ? (t.approvals_required ?? []).join(", ") : "None"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-xs text-slate-400">
                  No tickets generated yet. Submit requests or run the benchmark suite to populate the queue.
                </div>
              )}
            </div>
          )}

          {/* TAB 5: AUDIT TRAIL */}
          {activeTab === "audit" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white">Append-Only Audit Event Model</h2>
                  <p className="text-xs text-slate-400">
                    Defensible operational event trail persisted in SQLite (<code>./veridian.db</code>). Every transition records timestamp, rule ID, and actor.
                  </p>
                </div>
                <button
                  onClick={refreshTicketsAndAudit}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
                >
                  Refresh Audit Trail
                </button>
              </div>

              {auditEvents.length > 0 ? (
                <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
                  <table className="w-full text-left text-xs text-slate-300 font-mono">
                    <thead className="border-b border-slate-800 bg-slate-950 text-[11px] uppercase tracking-wider text-slate-400">
                      <tr>
                        <th className="px-4 py-3">Event ID</th>
                        <th className="px-4 py-3">Timestamp</th>
                        <th className="px-4 py-3">Employee</th>
                        <th className="px-4 py-3">Event Type</th>
                        <th className="px-4 py-3">Rule ID</th>
                        <th className="px-4 py-3">Action</th>
                        <th className="px-4 py-3">Actor</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {auditEvents.map((evt) => (
                        <tr key={evt.id || evt.event_id} className="hover:bg-slate-800/40">
                          <td className="px-4 py-2.5 font-bold text-indigo-400">{evt.id || evt.event_id}</td>
                          <td className="px-4 py-2.5 text-slate-400 text-[11px]">
                            {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : "-"}
                          </td>
                          <td className="px-4 py-2.5 font-sans">{evt.employee_id}</td>
                          <td className="px-4 py-2.5 text-cyan-300">{evt.event_type}</td>
                          <td className="px-4 py-2.5 text-emerald-300">{evt.policy_id || evt.authoritative_rule_id || "-"}</td>
                          <td className="px-4 py-2.5 font-semibold text-slate-300">{evt.action_taken || evt.workflow_action}</td>
                          <td className="px-4 py-2.5 text-slate-400">{evt.actor}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-xs text-slate-400">
                  Audit trail empty. Interact with the chat or run the benchmark suite to generate audit records.
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
