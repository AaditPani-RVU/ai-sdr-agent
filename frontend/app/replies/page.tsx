"use client";
import { useState } from "react";
import { api, InboxItem } from "../lib/api";

const CATEGORY_STYLE: Record<string, string> = {
  interested: "bg-green-900 text-green-300 border-green-700",
  not_now: "bg-yellow-900 text-yellow-300 border-yellow-700",
  out_of_office: "bg-gray-800 text-gray-400 border-gray-700",
  unsubscribe: "bg-red-900 text-red-300 border-red-700",
  other: "bg-gray-800 text-gray-400 border-gray-700",
};

const CATEGORY_LABEL: Record<string, string> = {
  interested: "Interested",
  not_now: "Not Now",
  out_of_office: "Out of Office",
  unsubscribe: "Unsubscribe",
  other: "Other",
};

export default function RepliesPage() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastPolled, setLastPolled] = useState<string | null>(null);

  const poll = async () => {
    setLoading(true);
    try {
      const results = await api.pollInbox();
      setItems(results);
      setLastPolled(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Reply Inbox</h1>
          {lastPolled && <p className="text-xs text-gray-500 mt-0.5">Last checked: {lastPolled}</p>}
        </div>
        <button onClick={poll} disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm px-4 py-2 rounded font-medium transition-colors">
          {loading ? "Checking..." : "Check Inbox"}
        </button>
      </div>

      {items.length === 0 && !loading && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-10 text-center">
          <p className="text-gray-500 text-sm">Click "Check Inbox" to poll Gmail for replies.</p>
          <p className="text-gray-600 text-xs mt-1">Requires Gmail OAuth setup and DRY_RUN=false in .env</p>
        </div>
      )}

      <div className="space-y-3">
        {items.map(item => (
          <div key={item.gmail_message_id}
            className={`border rounded-lg p-4 ${item.category ? CATEGORY_STYLE[item.category] : "bg-gray-900 border-gray-800 text-gray-300"}`}>
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="font-medium text-sm">{item.subject || "(no subject)"}</p>
                <p className="text-xs opacity-70">{item.prospect_name ?? item.from_email}</p>
              </div>
              {item.category && (
                <span className="text-xs font-bold uppercase tracking-wide">
                  {CATEGORY_LABEL[item.category] ?? item.category}
                </span>
              )}
            </div>

            <p className="text-xs opacity-80 leading-relaxed mb-2">{item.body_snippet}</p>

            {item.suggested_action && (
              <p className="text-xs opacity-60 border-t border-current/20 pt-2 mt-2">
                Next: {item.suggested_action}
              </p>
            )}

            {!item.prospect_id && (
              <p className="text-xs text-gray-500 mt-1">Unknown sender — not matched to any prospect</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
