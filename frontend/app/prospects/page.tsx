"use client";
import { useEffect, useState } from "react";
import { api, Prospect, ResearchResult, EmailDraft, SendResult } from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-700 text-gray-300",
  researched: "bg-yellow-900 text-yellow-300",
  email_drafted: "bg-purple-900 text-purple-300",
  sent: "bg-blue-900 text-blue-300",
  replied: "bg-green-900 text-green-300",
  booked: "bg-emerald-900 text-emerald-300",
};

type EmailTab = "email1" | "followup1" | "followup2";

function DraftView({ draft }: { draft: EmailDraft }) {
  const [tab, setTab] = useState<EmailTab>("email1");
  const [copied, setCopied] = useState(false);

  const content: Record<EmailTab, { label: string; subject?: string; body: string }> = {
    email1: { label: "Email 1", subject: draft.subject, body: draft.body },
    followup1: { label: "Follow-up (Day 3)", body: draft.follow_up_1 },
    followup2: { label: "Break-up (Day 7)", body: draft.follow_up_2 },
  };
  const active = content[tab];

  const copyEmail = () => {
    const text = active.subject ? `Subject: ${active.subject}\n\n${active.body}` : active.body;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="mt-3 border-t border-gray-800 pt-3">
      <div className="flex gap-1 mb-3">
        {(["email1", "followup1", "followup2"] as EmailTab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-xs px-3 py-1 rounded-full transition-colors ${tab === t ? "bg-purple-800 text-purple-200" : "bg-gray-800 text-gray-500 hover:text-gray-300"}`}>
            {content[t].label}
          </button>
        ))}
      </div>

      {active.subject && (
        <div className="mb-2">
          <p className="text-xs text-gray-500 mb-0.5">Subject A</p>
          <p className="text-sm font-medium text-white bg-gray-800 rounded px-3 py-1.5">{active.subject}</p>
          {draft.subject_alt && (
            <>
              <p className="text-xs text-gray-500 mt-1.5 mb-0.5">Subject B</p>
              <p className="text-sm font-medium text-white bg-gray-800 rounded px-3 py-1.5">{draft.subject_alt}</p>
            </>
          )}
        </div>
      )}

      <div className="relative">
        <pre className="text-xs text-gray-300 bg-gray-800 rounded p-3 whitespace-pre-wrap font-sans leading-relaxed">
          {active.body}
        </pre>
        <button onClick={copyEmail}
          className="absolute top-2 right-2 text-xs bg-gray-700 hover:bg-gray-600 text-gray-400 hover:text-white px-2 py-1 rounded transition-colors">
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
    </div>
  );
}

function ResearchView({ research }: { research: ResearchResult }) {
  return (
    <div className="mt-3 border-t border-gray-800 pt-3 space-y-2">
      <p className="text-xs text-gray-400 leading-relaxed">{research.company_summary}</p>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Pain Points</p>
          <ul className="space-y-0.5">
            {research.pain_points.map((pt, i) => (
              <li key={i} className="text-xs text-gray-400">• {pt}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Hooks</p>
          <ul className="space-y-0.5">
            {research.personalization_hooks.map((h, i) => (
              <li key={i} className="text-xs text-gray-400">• {h}</li>
            ))}
          </ul>
        </div>
      </div>
      <p className="text-xs text-blue-400">Angle: {research.recommended_angle}</p>
    </div>
  );
}

type ViewMode = "none" | "research" | "draft";

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [research, setResearch] = useState<Record<number, ResearchResult>>({});
  const [drafts, setDrafts] = useState<Record<number, EmailDraft>>({});
  const [sendResults, setSendResults] = useState<Record<number, SendResult>>({});
  const [busy, setBusy] = useState<Record<number, string>>({});
  const [view, setView] = useState<Record<number, ViewMode>>({});

  useEffect(() => { api.getProspects().then(setProspects).catch(console.error); }, []);

  const runResearch = async (id: number) => {
    setBusy(b => ({ ...b, [id]: "researching" }));
    try {
      const result = await api.researchProspect(id);
      setResearch(r => ({ ...r, [id]: result }));
      setProspects(ps => ps.map(p => p.id === id ? { ...p, status: "researched" } : p));
      setView(v => ({ ...v, [id]: "research" }));
    } finally {
      setBusy(b => { const n = { ...b }; delete n[id]; return n; });
    }
  };

  const runDraft = async (id: number) => {
    setBusy(b => ({ ...b, [id]: "drafting" }));
    try {
      const draft = await api.draftEmail(id);
      setDrafts(d => ({ ...d, [id]: draft }));
      setProspects(ps => ps.map(p => p.id === id ? { ...p, status: "email_drafted" } : p));
      setView(v => ({ ...v, [id]: "draft" }));
    } finally {
      setBusy(b => { const n = { ...b }; delete n[id]; return n; });
    }
  };

  const runSend = async (id: number) => {
    setBusy(b => ({ ...b, [id]: "sending" }));
    try {
      const result = await api.sendEmail(id);
      setSendResults(s => ({ ...s, [id]: result }));
      setProspects(ps => ps.map(p => p.id === id ? { ...p, status: "sent" } : p));
    } finally {
      setBusy(b => { const n = { ...b }; delete n[id]; return n; });
    }
  };

  const toggleView = (id: number, mode: ViewMode) => {
    setView(v => ({ ...v, [id]: v[id] === mode ? "none" : mode }));
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Prospects</h1>
      <p className="text-sm text-gray-500 mb-6">
        Upload prospects via <code className="bg-gray-800 px-1 rounded text-xs">POST /prospects/bulk?campaign_id=1</code> with a CSV file.
      </p>

      {prospects.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-500 text-sm">No prospects yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prospects.map(p => (
            <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-white">{p.first_name} {p.last_name}</p>
                  <p className="text-xs text-gray-500">{p.role} at {p.company}</p>
                  <p className="text-xs text-gray-600">{p.email}</p>
                </div>

                <div className="flex items-center gap-2 flex-wrap justify-end">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[p.status] || "bg-gray-700 text-gray-300"}`}>
                    {p.status.replace("_", " ")}
                  </span>

                  {(research[p.id] || ["researched","email_drafted","sent","replied","booked"].includes(p.status)) && (
                    <button onClick={() => toggleView(p.id, "research")}
                      className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white px-2 py-1 rounded transition-colors">
                      {view[p.id] === "research" ? "Hide research" : "Research"}
                    </button>
                  )}

                  {(drafts[p.id] || ["email_drafted","sent","replied","booked"].includes(p.status)) && (
                    <button onClick={() => {
                      if (!drafts[p.id]) {
                        api.getDraft(p.id).then(d => {
                          setDrafts(prev => ({ ...prev, [p.id]: d }));
                          setView(v => ({ ...v, [p.id]: "draft" }));
                        });
                      } else {
                        toggleView(p.id, "draft");
                      }
                    }}
                      className="text-xs bg-purple-900 hover:bg-purple-800 text-purple-300 px-2 py-1 rounded transition-colors">
                      {view[p.id] === "draft" ? "Hide emails" : "View emails"}
                    </button>
                  )}

                  {p.status === "pending" && (
                    <button onClick={() => runResearch(p.id)} disabled={!!busy[p.id]}
                      className="text-xs bg-yellow-700 hover:bg-yellow-600 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {busy[p.id] === "researching" ? "Researching..." : "Research"}
                    </button>
                  )}

                  {p.status === "researched" && (
                    <button onClick={() => runDraft(p.id)} disabled={!!busy[p.id]}
                      className="text-xs bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {busy[p.id] === "drafting" ? "Drafting..." : "Draft Emails"}
                    </button>
                  )}

                  {p.status === "email_drafted" && (
                    <button onClick={() => runSend(p.id)} disabled={!!busy[p.id]}
                      className="text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {busy[p.id] === "sending" ? "Sending..." : "Send"}
                    </button>
                  )}

                  {sendResults[p.id]?.dry_run && (
                    <span className="text-xs text-yellow-500 bg-yellow-900/40 px-2 py-0.5 rounded">dry run</span>
                  )}
                </div>
              </div>

              {view[p.id] === "research" && research[p.id] && (
                <ResearchView research={research[p.id]} />
              )}
              {view[p.id] === "draft" && drafts[p.id] && (
                <DraftView draft={drafts[p.id]} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
