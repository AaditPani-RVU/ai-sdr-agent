const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

export const api = {
  getCampaigns: () => req<Campaign[]>("/campaigns/"),
  createCampaign: (data: CampaignCreate) =>
    req<Campaign>("/campaigns/", { method: "POST", body: JSON.stringify(data) }),

  getProspects: (campaignId?: number) =>
    req<Prospect[]>(`/prospects/${campaignId ? `?campaign_id=${campaignId}` : ""}`),
  createProspect: (data: ProspectCreate) =>
    req<Prospect>("/prospects/", { method: "POST", body: JSON.stringify(data) }),
  researchProspect: (id: number) =>
    req<ResearchResult>(`/prospects/${id}/research`, { method: "POST" }),

  classifyReply: (prospectId: number, emailBody: string) =>
    req<ReplyOut>("/replies/classify", {
      method: "POST",
      body: JSON.stringify({ prospect_id: prospectId, email_body: emailBody }),
    }),
};

export interface Campaign {
  id: number; name: string; description?: string;
  sender_name: string; sender_email: string;
  total_prospects: number; sent: number; replied: number; booked: number;
}
export interface CampaignCreate { name: string; sender_name: string; sender_email: string; description?: string; }
export interface Prospect {
  id: number; first_name: string; last_name: string; email: string;
  role: string; company: string; website_url?: string; status: string;
}
export interface ProspectCreate extends Omit<Prospect, "id" | "status"> { campaign_id?: number; linkedin_url?: string; }
export interface ResearchResult {
  prospect_id: number; company_summary: string; pain_points: string[];
  personalization_hooks: string[]; recommended_angle: string;
  thinking_trace?: string; confidence_score: number;
}
export interface ReplyOut {
  prospect_id: number; category: string; summary: string; suggested_action: string;
}
