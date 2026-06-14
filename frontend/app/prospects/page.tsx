"use client";
import { useEffect, useRef, useState } from "react";
import { api, Campaign, Prospect, ResearchResult, EmailDraft, SendResult, ContactCandidate } from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-700 text-gray-300",
  researched: "bg-yellow-900 text-yellow-300",
  email_drafted: "bg-purple-900 text-purple-300",
  sent: "bg-blue-900 text-blue-300",
  replied: "bg-green-900 text-green-300",
  booked: "bg-emerald-900 text-emerald-300",
  unsubscribed: "bg-red-900 text-red-300",
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
            {research.pain_points.map((pt, i) => <li key={i} className="text-xs text-gray-400">• {pt}</li>)}
          </ul>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1 font-medium">Hooks</p>
          <ul className="space-y-0.5">
            {research.personalization_hooks.map((h, i) => <li key={i} className="text-xs text-gray-400">• {h}</li>)}
          </ul>
        </div>
      </div>
      <p className="text-xs text-blue-400">Angle: {research.recommended_angle}</p>
    </div>
  );
}

const DEFAULT_ROLES = "CEO, VP of Sales, VP of Marketing, CTO, Head of Growth";

function FindContactsPanel({
  campaigns,
  onAdded,
}: {
  campaigns: Campaign[];
  onAdded: () => void;
}) {
  const [company, setCompany] = useState("");
  const [website, setWebsite] = useState("");
  const [rolesInput, setRolesInput] = useState(DEFAULT_ROLES);
  const [campaignId, setCampaignId] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [candidates, setCandidates] = useState<ContactCandidate[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    setCandidates([]);
    setSelected(new Set());
    try {
      const roles = rolesInput.split(",").map(r => r.trim()).filter(Boolean);
      const results = await api.findContacts({
        company,
        website_url: website || undefined,
        roles,
        campaign_id: campaignId !== "" ? Number(campaignId) : undefined,
      });
      setCandidates(results);
      if (results.length === 0) setMsg("No contacts found — try a different company or roles.");
    } catch (err: unknown) {
      setMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const toggle = (i: number) =>
    setSelected(s => { const n = new Set(s); n.has(i) ? n.delete(i) : n.add(i); return n; });

  const confirmAdd = async () => {
    const toAdd = candidates
      .filter((_, i) => selected.has(i))
      .filter(c => c.email)
      .map(c => ({
        first_name: c.first_name,
        last_name: c.last_name,
        email: c.email!,
        role: c.role,
        company: c.company,
        website_url: c.website_url,
        linkedin_url: c.linkedin_url,
        campaign_id: campaignId !== "" ? Number(campaignId) : undefined,
        followups_sent: 0,
      }));
    if (!toAdd.length) { setMsg("Select at least one contact with an email."); return; }
    setSaving(true);
    try {
      const added = await api.confirmContacts(toAdd);
      setMsg(`Added ${added.length} prospect(s).`);
      setCandidates([]);
      setSelected(new Set());
      setCompany(""); setWebsite("");
      onAdded();
    } catch (err: unknown) {
      setMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
      <h2 className="text-sm font-semibold text-gray-300 mb-1">Find Contacts by Company</h2>
      <p className="text-xs text-gray-500 mb-3">Enter a company name and we'll search the web for key contacts to add as prospects.</p>
      <form onSubmit={search} className="flex flex-wrap gap-3 items-end mb-4">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Company *</label>
          <input value={company} onChange={e => setCompany(e.target.value)} required placeholder="Acme Corp"
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white w-44" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Website</label>
          <input value={website} onChange={e => setWebsite(e.target.value)} placeholder="https://acme.com"
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white w-52" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Target roles (comma-separated)</label>
          <input value={rolesInput} onChange={e => setRolesInput(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white w-80" />
        </div>
        <div>
          <label className="text-xs text-gray-500 block mb-1">Campaign</label>
          <select value={campaignId} onChange={e => setCampaignId(e.target.value === "" ? "" : Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white">
            <option value="">None</option>
            {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <button type="submit" disabled={loading}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
          {loading ? "Searching…" : "Find Contacts"}
        </button>
      </form>

      {candidates.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-400">{candidates.length} contact(s) found — select to add</p>
            <div className="flex gap-2">
              <button onClick={() => setSelected(new Set(candidates.map((_, i) => i)))}
                className="text-xs text-gray-400 hover:text-white">Select all</button>
              <button onClick={() => setSelected(new Set())}
                className="text-xs text-gray-400 hover:text-white">Clear</button>
            </div>
          </div>
          <div className="space-y-1.5 mb-3">
            {candidates.map((c, i) => (
              <label key={i} className={`flex items-start gap-3 p-3 rounded-lg cursor-pointer border transition-colors ${
                selected.has(i) ? "bg-indigo-950 border-indigo-700" : "bg-gray-800 border-gray-700 hover:border-gray-600"
              }`}>
                <input type="checkbox" checked={selected.has(i)} onChange={() => toggle(i)} className="mt-0.5" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm text-white font-medium">{c.first_name} {c.last_name}</span>
                    <span className="text-xs text-gray-400">{c.role}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                      c.confidence >= 0.7 ? "bg-green-900 text-green-300" : "bg-yellow-900 text-yellow-300"
                    }`}>{Math.round(c.confidence * 100)}% confidence</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {c.email ? (
                      <span className={c.confidence < 0.7 ? "text-yellow-500" : "text-gray-400"}>
                        {c.email}{c.confidence < 0.7 ? " (inferred)" : ""}
                      </span>
                    ) : (
                      <span className="text-red-500">No email — won't be added</span>
                    )}
                  </p>
                  {c.linkedin_url && (
                    <a href={c.linkedin_url} target="_blank" rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:text-blue-400">LinkedIn</a>
                  )}
                </div>
              </label>
            ))}
          </div>
          <button onClick={confirmAdd} disabled={saving || selected.size === 0}
            className="bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
            {saving ? "Adding…" : `Add ${selected.size} selected`}
          </button>
        </div>
      )}

      {msg && (
        <p className={`text-xs mt-3 ${msg.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>{msg}</p>
      )}
    </div>
  );
}

type ViewMode = "none" | "research" | "draft";

export default function ProspectsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [selectedCampaign, setSelectedCampaign] = useState<number | undefined>();
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [research, setResearch] = useState<Record<number, ResearchResult>>({});
  const [drafts, setDrafts] = useState<Record<number, EmailDraft>>({});
  const [sendResults, setSendResults] = useState<Record<number, SendResult>>({});
  const [busy, setBusy] = useState<Record<number, string>>({});
  const [view, setView] = useState<Record<number, ViewMode>>({});

  // CSV upload
  const [uploadCampaignId, setUploadCampaignId] = useState<number | "">("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Bulk action
  const [bulkStatus, setBulkStatus] = useState("");

  const loadProspects = (campaignId?: number) =>
    api.getProspects(campaignId).then(setProspects).catch(console.error);

  useEffect(() => {
    api.getCampaigns().then(cs => {
      setCampaigns(cs);
    }).catch(console.error);
    loadProspects();
  }, []);

  const handleCampaignFilter = (id: number | undefined) => {
    setSelectedCampaign(id);
    loadProspects(id);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || uploadCampaignId === "") return;
    setUploading(true);
    setUploadMsg("");
    try {
      const added = await api.uploadProspects(Number(uploadCampaignId), uploadFile);
      setUploadMsg(`Uploaded ${added.length} prospect(s).`);
      setUploadFile(null);
      if (fileRef.current) fileRef.current.value = "";
      loadProspects(selectedCampaign);
    } catch (err: unknown) {
      setUploadMsg(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploading(false);
    }
  };

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

  const toggleView = (id: number, mode: ViewMode) =>
    setView(v => ({ ...v, [id]: v[id] === mode ? "none" : mode }));

  // Bulk: run action on all eligible prospects sequentially
  const bulkRun = async (action: "research" | "draft" | "send") => {
    const eligible = prospects.filter(p =>
      action === "research" ? p.status === "pending" :
      action === "draft" ? p.status === "researched" :
      p.status === "email_drafted"
    );
    if (eligible.length === 0) return;
    setBulkStatus(`Running ${action} on ${eligible.length} prospects…`);
    let done = 0;
    for (const p of eligible) {
      try {
        if (action === "research") await runResearch(p.id);
        else if (action === "draft") await runDraft(p.id);
        else await runSend(p.id);
      } catch { /* individual failures don't stop the batch */ }
      done++;
      setBulkStatus(`${action}: ${done}/${eligible.length} done`);
    }
    setBulkStatus(`Done — ${done}/${eligible.length} ${action}ed.`);
  };

  const pending = prospects.filter(p => p.status === "pending").length;
  const researched = prospects.filter(p => p.status === "researched").length;
  const drafted = prospects.filter(p => p.status === "email_drafted").length;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Prospects</h1>

      {/* Find Contacts */}
      <FindContactsPanel campaigns={campaigns} onAdded={() => loadProspects(selectedCampaign)} />

      {/* CSV Upload */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-300 mb-3">Upload Prospects (CSV)</h2>
        <p className="text-xs text-gray-500 mb-3">
          CSV columns: <code className="bg-gray-800 px-1 rounded">first_name, last_name, email, role, company, website_url, linkedin_url</code>
        </p>
        <form onSubmit={handleUpload} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Campaign</label>
            <select
              value={uploadCampaignId}
              onChange={e => setUploadCampaignId(e.target.value === "" ? "" : Number(e.target.value))}
              required
              className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white">
              <option value="">Select campaign…</option>
              {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">CSV file</label>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              required
              onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
              className="text-sm text-gray-300 file:mr-3 file:bg-gray-700 file:text-gray-300 file:border-0 file:rounded file:px-3 file:py-1 file:text-xs file:cursor-pointer"
            />
          </div>
          <button type="submit" disabled={uploading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
            {uploading ? "Uploading…" : "Upload"}
          </button>
          {uploadMsg && (
            <span className={`text-xs ${uploadMsg.startsWith("Error") ? "text-red-400" : "text-green-400"}`}>
              {uploadMsg}
            </span>
          )}
        </form>
      </div>

      {/* Filters + Bulk actions */}
      <div className="flex flex-wrap items-center gap-3 mb-5">
        <div>
          <select
            value={selectedCampaign ?? ""}
            onChange={e => handleCampaignFilter(e.target.value === "" ? undefined : Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white">
            <option value="">All campaigns</option>
            {campaigns.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <div className="flex gap-2 ml-auto">
          {pending > 0 && (
            <button onClick={() => bulkRun("research")}
              className="text-xs bg-yellow-800 hover:bg-yellow-700 text-yellow-200 px-3 py-1.5 rounded font-medium transition-colors">
              Research all ({pending})
            </button>
          )}
          {researched > 0 && (
            <button onClick={() => bulkRun("draft")}
              className="text-xs bg-purple-800 hover:bg-purple-700 text-purple-200 px-3 py-1.5 rounded font-medium transition-colors">
              Draft all ({researched})
            </button>
          )}
          {drafted > 0 && (
            <button onClick={() => bulkRun("send")}
              className="text-xs bg-green-800 hover:bg-green-700 text-green-200 px-3 py-1.5 rounded font-medium transition-colors">
              Send all ({drafted})
            </button>
          )}
        </div>
      </div>

      {bulkStatus && (
        <p className="text-xs text-blue-400 mb-4">{bulkStatus}</p>
      )}

      {prospects.length === 0 ? (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-8 text-center">
          <p className="text-gray-500 text-sm">No prospects yet. Upload a CSV above to get started.</p>
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
                  {p.status === "sent" && p.followups_sent < 2 && (
                    <p className="text-xs text-blue-500 mt-0.5">
                      {p.followups_sent === 0 ? "Awaiting follow-up 1" : "Awaiting follow-up 2"}
                    </p>
                  )}
                  {p.followups_sent > 0 && (
                    <p className="text-xs text-gray-600 mt-0.5">{p.followups_sent} follow-up{p.followups_sent > 1 ? "s" : ""} sent</p>
                  )}
                  {p.status === "booked" && p.booked_at && (
                    <p className="text-xs text-emerald-400 mt-0.5">
                      Meeting: {new Date(p.booked_at).toLocaleString()}
                      {p.calendly_event_url && (
                        <a href={p.calendly_event_url} target="_blank" rel="noopener noreferrer"
                          className="ml-2 text-emerald-500 hover:text-emerald-300 underline">Calendly</a>
                      )}
                    </p>
                  )}
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
                      {busy[p.id] === "researching" ? "Researching…" : "Research"}
                    </button>
                  )}

                  {p.status === "researched" && (
                    <button onClick={() => runDraft(p.id)} disabled={!!busy[p.id]}
                      className="text-xs bg-purple-700 hover:bg-purple-600 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {busy[p.id] === "drafting" ? "Drafting…" : "Draft Emails"}
                    </button>
                  )}

                  {p.status === "email_drafted" && (
                    <button onClick={() => runSend(p.id)} disabled={!!busy[p.id]}
                      className="text-xs bg-green-700 hover:bg-green-600 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {busy[p.id] === "sending" ? "Sending…" : "Send"}
                    </button>
                  )}

                  {sendResults[p.id]?.dry_run && (
                    <span className="text-xs text-yellow-500 bg-yellow-900/40 px-2 py-0.5 rounded">dry run</span>
                  )}
                </div>
              </div>

              {view[p.id] === "research" && research[p.id] && <ResearchView research={research[p.id]} />}
              {view[p.id] === "draft" && drafts[p.id] && <DraftView draft={drafts[p.id]} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
