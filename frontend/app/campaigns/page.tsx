"use client";
import { useEffect, useState } from "react";
import { api, Campaign, CampaignCreate } from "../lib/api";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [form, setForm] = useState<CampaignCreate>({ name: "", sender_name: "", sender_email: "" });
  const [creating, setCreating] = useState(false);

  const load = () => api.getCampaigns().then(setCampaigns).catch(console.error);
  useEffect(() => { load(); }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    await api.createCampaign(form);
    setForm({ name: "", sender_name: "", sender_email: "" });
    await load();
    setCreating(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Campaigns</h1>
      <form onSubmit={submit} className="bg-gray-900 border border-gray-800 rounded-lg p-5 mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <input required placeholder="Campaign name" value={form.name}
          onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500" />
        <input required placeholder="Sender name" value={form.sender_name}
          onChange={e => setForm(f => ({ ...f, sender_name: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500" />
        <input required type="email" placeholder="Sender email" value={form.sender_email}
          onChange={e => setForm(f => ({ ...f, sender_email: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500" />
        <button type="submit" disabled={creating}
          className="md:col-span-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors">
          {creating ? "Creating..." : "Create Campaign"}
        </button>
      </form>

      <div className="space-y-3">
        {campaigns.map(c => (
          <div key={c.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="font-medium text-white">{c.name}</p>
              <span className="text-xs text-gray-500">ID: {c.id}</span>
            </div>
            <p className="text-xs text-gray-500 mb-3">{c.sender_name} &lt;{c.sender_email}&gt;</p>
            <div className="grid grid-cols-4 gap-3 text-center text-sm">
              {[["Prospects", c.total_prospects, "text-gray-300"], ["Sent", c.sent, "text-gray-300"], ["Replied", c.replied, "text-green-400"], ["Booked", c.booked, "text-blue-400"]].map(([label, val, cls]) => (
                <div key={label as string} className="bg-gray-800 rounded p-2">
                  <p className={`font-bold ${cls}`}>{val}</p>
                  <p className="text-xs text-gray-600">{label}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
