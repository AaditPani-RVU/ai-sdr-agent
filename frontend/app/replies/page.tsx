"use client";
import { useState } from "react";
import { api, ReplyOut } from "../lib/api";

const CATEGORY_STYLE: Record<string, string> = {
  interested: "bg-green-900 text-green-300 border-green-700",
  not_now: "bg-yellow-900 text-yellow-300 border-yellow-700",
  out_of_office: "bg-gray-800 text-gray-400 border-gray-700",
  unsubscribe: "bg-red-900 text-red-300 border-red-700",
  other: "bg-gray-800 text-gray-400 border-gray-700",
};

export default function RepliesPage() {
  const [prospectId, setProspectId] = useState("");
  const [body, setBody] = useState("");
  const [result, setResult] = useState<ReplyOut | null>(null);
  const [loading, setLoading] = useState(false);

  const classify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await api.classifyReply(parseInt(prospectId), body);
      setResult(r);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Reply Classifier</h1>
      <p className="text-sm text-gray-500 mb-6">Paste a reply email to classify it and get a suggested next action.</p>
      <form onSubmit={classify} className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-4 max-w-xl mb-8">
        <input required placeholder="Prospect ID" value={prospectId} type="number"
          onChange={e => setProspectId(e.target.value)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500" />
        <textarea required placeholder="Paste the reply email body here..." value={body}
          onChange={e => setBody(e.target.value)} rows={6}
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500 resize-none" />
        <button type="submit" disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded px-4 py-2 text-sm font-medium transition-colors">
          {loading ? "Classifying..." : "Classify Reply"}
        </button>
      </form>

      {result && (
        <div className={`border rounded-lg p-5 max-w-xl ${CATEGORY_STYLE[result.category]}`}>
          <div className="flex items-center gap-2 mb-3">
            <span className="font-bold uppercase text-sm">{result.category.replace("_", " ")}</span>
          </div>
          <p className="text-sm mb-2">{result.summary}</p>
          <p className="text-xs opacity-80">Next action: {result.suggested_action}</p>
        </div>
      )}
    </div>
  );
}
