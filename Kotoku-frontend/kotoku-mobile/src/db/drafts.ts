import type { SQLiteBindValue } from "expo-sqlite";

import { getDb } from "./migrations";
import type { PartyDraft } from "@/features/agreements/agreementStore";

export interface DraftRow {
  id: number;
  agreement_id: number | null;
  scenario_id: string;
  title: string;
  step_index: number;
  party_a: PartyDraft;
  party_b: PartyDraft;
  subject_data: Record<string, unknown>;
  synced: boolean;
  created_at: string;
  updated_at: string;
}

type RawRow = Omit<DraftRow, "party_a" | "party_b" | "subject_data" | "synced"> & {
  party_a: string;
  party_b: string;
  subject_data: string;
  synced: number;
};

function parseRow(raw: RawRow): DraftRow {
  return {
    ...raw,
    party_a: JSON.parse(raw.party_a),
    party_b: JSON.parse(raw.party_b),
    subject_data: JSON.parse(raw.subject_data),
    synced: raw.synced === 1,
  };
}

const now = () => new Date().toISOString();

export async function saveDraft(draft: {
  scenarioId: string;
  title: string;
  stepIndex: number;
  partyA: PartyDraft;
  partyB: PartyDraft;
  subjectData: Record<string, unknown>;
  agreementId?: number;
}): Promise<number> {
  const db = await getDb();
  const result = await db.runAsync(
    `INSERT INTO drafts
       (agreement_id, scenario_id, title, step_index, party_a, party_b,
        subject_data, synced, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)`,
    [
      draft.agreementId ?? null,
      draft.scenarioId,
      draft.title,
      draft.stepIndex,
      JSON.stringify(draft.partyA),
      JSON.stringify(draft.partyB),
      JSON.stringify(draft.subjectData),
      now(),
      now(),
    ],
  );
  return result.lastInsertRowId;
}

export async function updateDraft(
  localId: number,
  patch: Partial<{
    stepIndex: number;
    partyA: PartyDraft;
    partyB: PartyDraft;
    subjectData: Record<string, unknown>;
    agreementId: number;
    synced: boolean;
  }>,
): Promise<void> {
  const db = await getDb();
  const sets: string[] = ["updated_at = ?"];
  const values: SQLiteBindValue[] = [now()];

  if (patch.stepIndex !== undefined) { sets.push("step_index = ?"); values.push(patch.stepIndex); }
  if (patch.partyA !== undefined) { sets.push("party_a = ?"); values.push(JSON.stringify(patch.partyA)); }
  if (patch.partyB !== undefined) { sets.push("party_b = ?"); values.push(JSON.stringify(patch.partyB)); }
  if (patch.subjectData !== undefined) { sets.push("subject_data = ?"); values.push(JSON.stringify(patch.subjectData)); }
  if (patch.agreementId !== undefined) { sets.push("agreement_id = ?"); values.push(patch.agreementId); }
  if (patch.synced !== undefined) { sets.push("synced = ?"); values.push(patch.synced ? 1 : 0); }

  values.push(localId);
  await db.runAsync(`UPDATE drafts SET ${sets.join(", ")} WHERE id = ?`, values);
}

export async function getDraft(localId: number): Promise<DraftRow | null> {
  const db = await getDb();
  const raw = await db.getFirstAsync<RawRow>(
    "SELECT * FROM drafts WHERE id = ?",
    [localId],
  );
  return raw ? parseRow(raw) : null;
}

export async function getDraftByAgreementId(agreementId: number): Promise<DraftRow | null> {
  try {
    const db = await getDb();
    const raw = await db.getFirstAsync<RawRow>(
      "SELECT * FROM drafts WHERE agreement_id = ? ORDER BY updated_at DESC LIMIT 1",
      [agreementId],
    );
    return raw ? parseRow(raw) : null;
  } catch {
    return null;
  }
}

export async function listDrafts(): Promise<DraftRow[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<RawRow>(
    "SELECT * FROM drafts WHERE synced = 0 ORDER BY updated_at DESC",
  );
  return rows.map(parseRow);
}

export async function deleteDraft(localId: number): Promise<void> {
  const db = await getDb();
  await db.runAsync("DELETE FROM drafts WHERE id = ?", [localId]);
}

export async function clearAllLocalDrafts(): Promise<void> {
  const db = await getDb();
  await db.runAsync("DELETE FROM drafts");
}
