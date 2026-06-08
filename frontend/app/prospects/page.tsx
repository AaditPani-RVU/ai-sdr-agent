"use client";
import { useEffect, useState } from "react";
import { api, Prospect, ResearchResult } from "../lib/api";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-700 text-gray-300",
  researched: "bg-yellow-900 text-yellow-300",
  email_drafted: "bg-purple-900 text-purple-300",
  sent: "bg-blue-900 text-blue-300",
  replied: "bg-green-900 text-green-300",
  booked: "bg-emerald-900 text-emerald-300",
};

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [research, setResearch] = useState<Record<number, ResearchResult>>({});
  const [researching, setResearching] = useState<number | null>(null);

  useEffect(() => { api.getProspects().then(setProspects).catch(console.error); }, []);

  const runResearch = async (id: number) => {
    setResearching(id);
    try {
      const result = await api.researchProspect(id);
      setResearch(r => ({ ...r, [id]: result }));
      setProspects(ps => ps.map(p => p.id === id ? { ...p, status: "researched" } : p));
    } catch (e) {
      console.error(e);
    } finally {
      setResearching(null);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Prospects</h1>
      {prospects.length === 0 ? (
        <p className="text-gray-500 text-sm">No prospects yet. Upload a CSV via the API at <code className="bg-gray-800 px-1 rounded">POST /prospects/bulk</code></p>
      ) : (
        <div className="space-y-3">
          {prospects.map(p => (
            <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-medium text-white">{p.first_name} {p.last_name}</p>
                  <p className="text-xs text-gray-500">{p.role} at {p.company}</p>
                  <p className="text-xs text-gray-600">{p.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[p.status] || "bg-gray-700 text-gray-300"}`}>
                    {p.status}
                  </span>
                  {p.status === "pending" && (
                    <button onClick={() => runResearch(p.id)} disabled={researching === p.id}
                      className="text-xs bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-3 py-1 rounded transition-colors">
                      {researching === p.id ? "Researching..." : "Research"}
                    </button>
                  )}
                </div>
              </div>
              {research[p.id] && (
                <div className="mt-3 border-t border-gray-800 pt-3 space-y-2">
                  <p className="text-xs text-gray-300">{research[p.id].company_summary}</p>
                  <div className="flex gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Pain Points</p>
                      <ul className="space-y-0.5">
                        {research[p.id].pain_points.map((pt, i) => (
                          <li key={i} className="text-xs text-gray-400">- {pt}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Hooks</p>
                      <ul className="space-y-0.5">
                        {research[p.id].personalization_hooks.map((h, i) => (
                          <li key={i} className="text-xs text-gray-400">- {h}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  <p className="text-xs text-blue-400">Angle: {research[p.id].recommended_angle}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
