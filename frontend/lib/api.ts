/**
 * API utility for connecting Next.js frontend to the FastAPI backend.
 * Uses fetch for robust streaming and data fetching.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface TraceEntry {
  step: string;
  status: 'PASS' | 'FAIL' | 'WARNING' | 'SKIP' | 'ERROR' | 'PENDING';
  details?: Record<string, any>;
  duration_ms?: number;
  timestamp?: string;
}

export interface ConfidenceBreakdown {
  extraction_confidence: number;
  rule_confidence: number;
  fraud_doc_quality: number;
  final_confidence: number;
}

export interface ClaimDecisionOutput {
  claim_id: string;
  decision: 'APPROVED' | 'REJECTED' | 'PARTIAL' | 'MANUAL_REVIEW' | 'PENDING';
  approved_amount: number;
  rejection_reasons: string[];
  rejected_items: string[];
  confidence_score: number;
  fraud_score: number;
  notes: string;
  next_steps: string;
  is_cashless_approved: boolean;
  network_discount: number;
  deductions: Record<string, number>;
  trace_summary: TraceEntry[];
  confidence_breakdown?: ConfidenceBreakdown;
}

export interface InvestigatorReportData {
  claim_summary: Record<string, any>;
  coverage_analysis: Record<string, any>;
  limit_analysis: Record<string, any>;
  fraud_analysis: Record<string, any>;
  decision_rationale: Record<string, any>;
  what_if_analysis: Record<string, any>;
  policy_references: any[];
  full_report_text: string;
}

export const api = {
  /**
   * Submit a claim (direct JSON version for demo).
   * In a real system, you'd use formData for file uploads.
   */
  async submitClaim(data: any): Promise<ClaimDecisionOutput> {
    const res = await fetch(`${API_BASE_URL}/claims/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to submit claim');
    }
    return res.json();
  },

  /**
   * Upload claim documents (Multipart FormData).
   */
  async uploadClaim(formData: FormData): Promise<ClaimDecisionOutput> {
    const res = await fetch(`${API_BASE_URL}/claims/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Failed to upload claim documents');
    }
    return res.json();
  },

  /**
   * Fetch a claim's status.
   */
  async getClaimStatus(claimId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/claims/${claimId}/status`);
    if (!res.ok) throw new Error('Claim not found');
    return res.json();
  },

  /**
   * List claims (for dashboard).
   */
  async listClaims(): Promise<any[]> {
    const res = await fetch(`${API_BASE_URL}/claims`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.claims || [];
  },

  /**
   * Review claim (Adjuster override).
   */
  async reviewClaim(claimId: string, actionData: any): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/review/${claimId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(actionData),
    });
    if (!res.ok) throw new Error('Failed to review claim');
    return res.json();
  },

  /**
   * RAG Policy Assistant Chat
   */
  async askPolicy(question: string, claimId?: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/policy/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, claim_id: claimId }),
    });
    if (!res.ok) throw new Error('Failed to query policy assistant');
    return res.json();
  }
};
