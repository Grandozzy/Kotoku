import { useState, useEffect } from 'react';
import { apiClient } from '@/api/client';

export interface Dispute {
  id: number;
  agreement_id: number;
  agreement_type: string;
  agreement_sealed_at: string;
  raised_by_party_id: number;
  raised_by_display_name: string;
  reason: string;
  status: 'open' | 'investigating' | 'resolved' | 'dismissed';
  resolution?: string;
  created_at: string;
}

export function useDisputes(agreementId?: number) {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDisputes() {
      try {
        setLoading(true);
        const url = agreementId 
          ? `/v1/agreements/${agreementId}/disputes`
          : '/v1/disputes';
        const response = await apiClient.get(url);
        setDisputes(response.data.disputes || []);
      } catch (e: any) {
        setError(e.message || 'Failed to load disputes');
      } finally {
        setLoading(false);
      }
    }
    fetchDisputes();
  }, [agreementId]);

  return { disputes, loading, error };
}