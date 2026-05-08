export interface ConsentRecord {
  id: number;
  party_id: number;
  party_phone: string;
  channel: string;
  granted: boolean;
  granted_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface ConsentStatus {
  agreement_id: number;
  all_consented: boolean;
  records: ConsentRecord[];
}
