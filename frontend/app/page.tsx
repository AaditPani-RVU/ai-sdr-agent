"use client";
import { useEffect, useState } from "react";
import { api, Campaign } from "./lib/api";

export default function DashboardPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);

  useEffect(() => { api.getCampaigns().then(setCampaigns).catch(console.error); }, []);

  const totals = campaigns.reduce(
    (acc, c) => ({
      prospects: acc.prospects + c.total_prospects,
      sent: acc.sent + c.sent,
      replied: acc.replied + c.replied,
      booked: acc.booked + c.booked,
    }),
    { prospects: 0, sent: 0, replied: 0, booked: 0 }
  );

  const replyRate = totals.sent > 0 ? ((totals.replied / totals.sent) * 100).toFixed(1) : "0";
  const bookRate = totals.replied > 0 ? ((totals.booked / totals.replied) * 100).toFixed(1) : "0";

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
        {[
          { label: "Total Prospects", value: totals.prospects },
          { label: "Emails Sent", value: totals.sent },
          { label: "Reply Rate", value: `${replyRate}%` },
          { label: "Meetings Booked", value: totals.booked },
        ].map((stat) => (
          <div key={stat.label} className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{stat.label}</p>
            <p className="text-3xl font-bold text-white">{stat.value}</p>
          </div>
        ))}
      </div>

      <h2 className="text-lg font-semibold mb-4">Active Campaigns</h2>
      {campaigns.length === 0 ? (
        <p className="text-gray-500 text-sm">No campaigns yet. <a href="/campaigns" className="text-blue-400 underline">Create one</a></p>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <div key={c.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-white">{c.name}</p>
                <p className="text-xs text-gray-500">{c.sender_email}</p>
              </div>
              <div className="flex gap-6 text-sm text-center">
                <div><p className="text-gray-400">{c.total_prospects}</p><p className="text-xs text-gray-600">prospects</p></div>
                <div><p className="text-gray-400">{c.sent}</p><p className="text-xs text-gray-600">sent</p></div>
                <div><p className="text-green-400">{c.replied}</p><p className="text-xs text-gray-600">replied</p></div>
                <div><p className="text-blue-400">{c.booked}</p><p className="text-xs text-gray-600">booked</p></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
