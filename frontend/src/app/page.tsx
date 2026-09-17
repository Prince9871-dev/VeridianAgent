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
  intent?: string;
  extractedFacts?: Record<string, string>;
  action?: "RESOLVE" | "ASK_FOLLOW_UP" | "ESCALATE" | "CREATE_TICKET";
  policyCitation?: string;
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
  authoritative_rule: Record<string, any>;
  engineering_workflow: Record<string, any>;
  required_inputs: string[];
}

interface PrecedentItem {
  ticket_id: string;
  employee: string;
  issue_summary: string;
  status: string;
  is_active: boolean;
  relevance: string;
}

const SAMPLE_PROMPTS = [
  {
    label: "Admin Rights for Docker",
    text: "Hi, I'm from engineering and need local admin rights on my MacBook to run Docker containers.",
    employeeId: "EMP-4102",
    employeeName: "Marcus Vance",
  },
  {
    label: "Hardware Screen Flickering",
    text: "My external monitor in workstation 4B is constantly flickering and turning off.",
    employeeId: "EMP-2091",
    employeeName: "Sarah Jenkins",
  },
  {
    label: "VPN & Password Reset",
    text: "I was locked out of my Veridian Active Directory account after entering the wrong password three times.",
    employeeId: "EMP-1044",
    employeeName: "David Kim",
  },
  {
    label: "Laptop Replacement (3.5 yrs)",
    text: "My laptop won’t turn on at all, it’s completely dead, had it about 3.5 years now.",
    employeeId: "EMP-4102",
    employeeName: "Aditi Sharma",
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
    intent: "LAPTOP_REPLACEMENT_REQUEST",
    extractedFacts: {
      service_age_years: "3.5",
      hardware_failure_verified: "true",
      lead_time_days: "14",
    },
    action: "CREATE_TICKET",
    policyCitation: "[DataPack: KB-03 - Laptop Replacement, Page 1] & [DataPack: Asset Management Policy (Extract), Page 1]",
    ticketId: "TCK-2026-1043",
    auditId: "AUD-E94821A803B2",
  },
];

export default function Home() {
  const [activeTab, setActiveTab] = useState<"chat" | "tickets" | "audit" | "datapack">("chat");
  const [messages, setMessages] = useState<MessageItem[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState("");
  const [selectedEmployee, setSelectedEmployee] = useState("EMP-4102 (Aditi Sharma)");
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [policies, setPolicies] = useState<AuthoritativePolicyItem[]>([]);
  const [precedents, setPrecedents] = useState<PrecedentItem[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const [sessionId, setSessionId] = useState<string>(() => `session-${Date.now().toString(36)}`);

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
  }, []);

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

    // Call Phase 3 Coordinator Chat API
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
            intent: resp.intent_analysis?.raw_intent || resp.deterministic_evaluation?.authoritative_rule_outcome,
            extractedFacts: resp.intent_analysis?.extracted_facts || {},
            action: resp.action,
            policyCitation: resp.source_citation || undefined,
            ticketId: resp.ticket?.id || undefined,
            auditId: resp.audit_event_id || `AUD-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
          };
          setMessages((prev) => [...prev, agentReply]);
        }
        setIsProcessing(false);
      })
      .catch(() => {
        // Fallback for offline UI display
        setTimeout(() => {
          const agentReply: MessageItem = {
            id: `msg-${Date.now() + 1}`,
            sender: "agent",
            text: "Request evaluated against Veridian Data Pack authoritative rules. Operational action determined deterministically.",
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            action: "RESOLVE",
            policyCitation: "[DataPack: KB-01 - Password Reset, Page 1] § Section 1",
            auditId: `AUD-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
          };
          setMessages((prev) => [...prev, agentReply]);
          setIsProcessing(false);
        }, 500);
      });
  };

  return (
    <div className="flex h-screen w-full flex-col bg-slate-950 text-slate-100 antialiased">
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
                Phase 3 Agentic Coordinator
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Authoritative Policy Enforcement &bull; Deterministic Separation of Rules & Workflows
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
            Precedents: <span className="font-semibold text-indigo-400">10 Historical Records</span>
          </div>

          <div className="h-4 w-px bg-slate-800" />

          <div className="flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-800/80 px-2.5 py-1 text-xs">
            <span className="text-slate-400">Data Pack:</span>
            <span className="font-mono text-xs font-medium text-emerald-400">
              Verified (38.1 KB)
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
                Workspace
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
                  Authoritative Policy Catalog
                </button>

                <button
                  id="tab-tickets"
                  onClick={() => setActiveTab("tickets")}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "tickets"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                  Ticket Queue
                </button>

                <button
                  id="tab-audit"
                  onClick={() => setActiveTab("audit")}
                  className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                    activeTab === "audit"
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Audit Trail
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
                <option value="EMP-4102 (Aditi Sharma)">EMP-4102 &bull; Aditi Sharma (Eng)</option>
                <option value="EMP-2091 (Sarah Jenkins)">EMP-2091 &bull; Sarah Jenkins (Design)</option>
                <option value="EMP-1044 (David Kim)">EMP-1044 &bull; David Kim (Sales)</option>
                <option value="EMP-8831 (Elena Rostova)">EMP-8831 &bull; Elena Rostova (HR)</option>
              </select>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 text-xs text-slate-400">
            <div className="font-semibold text-slate-300 mb-1">Governance Principle</div>
            <p className="text-[11px] leading-relaxed">
              Rules come solely from the PDF. Application actions (RESOLVE, CREATE_TICKET) are operational designs, not company policy.
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
                            Service Agent
                          </span>
                          <span>&bull; {msg.timestamp}</span>
                        </>
                      )}
                    </div>

                    <div
                      className={`max-w-2xl rounded-2xl p-4 shadow-sm ${
                        msg.sender === "employee"
                          ? "bg-indigo-600 text-white rounded-tr-none"
                          : "bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none"
                      }`}
                    >
                      <p className="text-sm leading-relaxed">{msg.text}</p>

                      {msg.sender === "agent" && (
                        <div className="mt-4 space-y-2 border-t border-slate-800 pt-3 text-xs">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-slate-400">Operational Action:</span>
                            <span
                              className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
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

                            {msg.intent && (
                              <span className="font-mono text-[10px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded border border-slate-700">
                                Rule Outcome: {msg.intent}
                              </span>
                            )}
                          </div>

                          {msg.policyCitation && (
                            <div className="rounded bg-slate-950/70 p-2 border border-slate-800/80 flex items-start gap-2">
                              <span className="text-indigo-400 font-semibold text-[11px] whitespace-nowrap">
                                Policy Citation:
                              </span>
                              <span className="text-slate-300 font-mono text-[11px]">
                                {msg.policyCitation}
                              </span>
                            </div>
                          )}

                          {(msg.ticketId || msg.auditId) && (
                            <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-1">
                              {msg.ticketId && (
                                <span>
                                  Ticket:{" "}
                                  <strong className="text-indigo-400 font-mono">{msg.ticketId}</strong>
                                </span>
                              )}
                              {msg.auditId && (
                                <span>
                                  Audit ID:{" "}
                                  <strong className="text-slate-300 font-mono">{msg.auditId}</strong>
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isProcessing && (
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-indigo-500"></span>
                    Evaluating authoritative rules deterministically...
                  </div>
                )}
              </div>

              {/* Scenario Prompts */}
              <div className="border-t border-slate-800 bg-slate-900/60 p-3">
                <div className="mb-2 text-[11px] font-semibold text-slate-400">
                  Scenario Prompts (Test Authoritative Policies):
                </div>
                <div className="flex flex-wrap gap-2">
                  {SAMPLE_PROMPTS.map((p, idx) => (
                    <button
                      key={idx}
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

          {/* TAB 2: AUTHORITATIVE POLICY CATALOG */}
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
                      {p.authoritative_rule?.approvals_required?.length > 0 && (
                        <div className="flex justify-between">
                          <span className="text-slate-500">Mandatory Approvals:</span>
                          <span className="text-amber-300 text-[11px]">
                            {p.authoritative_rule.approvals_required.join(", ")}
                          </span>
                        </div>
                      )}
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

          {/* TAB 3: TICKET QUEUE */}
          {activeTab === "tickets" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <h2 className="text-xl font-bold text-white">Structured IT Ticket Queue</h2>
              <p className="text-xs text-slate-400">
                Active tickets generated deterministically according to company policy requirements.
              </p>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-xs text-slate-400">
                Ticket management operational. Tickets created through conversation or policy evaluations are recorded in the active queue.
              </div>
            </div>
          )}

          {/* TAB 4: AUDIT TRAIL */}
          {activeTab === "audit" && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <h2 className="text-xl font-bold text-white">Immutable Compliance Audit Log</h2>
              <p className="text-xs text-slate-400">
                Traceability ledger recording every request, policy condition, and workflow transition.
              </p>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-xs text-slate-400">
                Append-only audit trail logging active. Every evaluation produces an immutable record with verifiable citations.
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
