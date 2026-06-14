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
  getStats: (campaignId?: number) =>
    req<Record<string, number>>(`/prospects/stats${campaignId ? `?campaign_id=${campaignId}` : ""}`),
  createProspect: (data: ProspectCreate) =>
    req<Prospect>("/prospects/", { method: "POST", body: JSON.stringify(data) }),
  uploadProspects: async (campaignId: number, file: File): Promise<Prospect[]> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/prospects/bulk?campaign_id=${campaignId}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) throw new Error(`Upload error ${res.status}: ${await res.text()}`);
    return res.json();
  },
  researchProspect: (id: number) =>
    req<ResearchResult>(`/prospects/${id}/research`, { method: "POST" }),
  draftEmail: (id: number) =>
    req<EmailDraft>(`/prospects/${id}/draft`, { method: "POST" }),
  getDraft: (id: number) =>
    req<EmailDraft>(`/prospects/${id}/draft`),

  classifyReply: (prospectId: number, emailBody: string) =>
    req<ReplyOut>("/replies/classify", {
      method: "POST",
      body: JSON.stringify({ prospect_id: prospectId, email_body: emailBody }),
    }),
  sendEmail: (id: number) =>
    req<SendResult>(`/prospects/${id}/send`, { method: "POST" }),
  sendFollowUp: (id: number) =>
    req<SendResult>(`/prospects/${id}/send-followup`, { method: "POST" }),
  triggerFollowups: () =>
    req<{ triggered: number; details: { prospect_id: number; followup: number }[] }>(
      "/prospects/trigger-followups", { method: "POST" }
    ),
  pollInbox: () => req<InboxItem[]>("/replies/inbox"),

  findContacts: (data: ContactFinderRequest) =>
    req<ContactCandidate[]>("/prospects/find-contacts", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  confirmContacts: (contacts: ProspectCreate[]) =>
    req<Prospect[]>("/prospects/confirm-contacts", {
      method: "POST",
      body: JSON.stringify(contacts),
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
  sent_at?: string; followups_sent: number;
  booked_at?: string; calendly_event_url?: string;
}

export interface ContactFinderRequest {
  company: string;
  website_url?: string;
  roles?: string[];
  campaign_id?: number;
}

export interface ContactCandidate {
  first_name: string; last_name: string; email?: string; role: string;
  company: string; website_url?: string; linkedin_url?: string;
  confidence: number; source?: string;
}
export interface ProspectCreate extends Omit<Prospect, "id" | "status"> { campaign_id?: number; linkedin_url?: string; }
export interface ResearchResult {
  prospect_id: number; company_summary: string; pain_points: string[];
  personalization_hooks: string[]; recommended_angle: string;
  thinking_trace?: string; confidence_score: number;
}
export interface EmailDraft {
  prospect_id: number; subject: string; subject_alt: string;
  body: string; follow_up_1: string; follow_up_2: string;
}
export interface ReplyOut {
  prospect_id: number; category: string; summary: string; suggested_action: string;
}
export interface SendResult {
  prospect_id: number; status: string; message_id?: string; dry_run: boolean;
}
export interface InboxItem {
  gmail_message_id: string; from_email: string; subject: string; body_snippet: string;
  prospect_id?: number; prospect_name?: string; category?: string; suggested_action?: string;
}
