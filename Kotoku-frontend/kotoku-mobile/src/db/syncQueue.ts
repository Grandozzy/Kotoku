import { getDb } from "./migrations";

export type ActionType =
  | "CREATE_DRAFT"
  | "UPDATE_DRAFT"
  | "UPLOAD_EVIDENCE"
  | "CONFIRM_OTP"
  | "SEAL";

export type QueueStatus = "pending" | "in_flight" | "failed_permanent";

export interface QueueRow {
  id: number;
  action_type: ActionType;
  payload: Record<string, unknown>;
  status: QueueStatus;
  retry_count: number;
  created_at: string;
  last_attempted_at: string | null;
}

type RawRow = Omit<QueueRow, "payload"> & { payload: string };

function parseRow(raw: RawRow): QueueRow {
  return { ...raw, payload: JSON.parse(raw.payload) };
}

const now = () => new Date().toISOString();

export async function enqueue(
  actionType: ActionType,
  payload: Record<string, unknown>,
): Promise<number> {
  const db = await getDb();
  const result = await db.runAsync(
    `INSERT INTO sync_queue (action_type, payload, status, retry_count, created_at)
     VALUES (?, ?, 'pending', 0, ?)`,
    [actionType, JSON.stringify(payload), now()],
  );
  return result.lastInsertRowId;
}

export async function getPendingItems(): Promise<QueueRow[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<RawRow>(
    "SELECT * FROM sync_queue WHERE status = 'pending' ORDER BY created_at ASC",
  );
  return rows.map(parseRow);
}

export async function markInFlight(id: number): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    "UPDATE sync_queue SET status = 'in_flight', last_attempted_at = ? WHERE id = ?",
    [now(), id],
  );
}

export async function markComplete(id: number): Promise<void> {
  const db = await getDb();
  await db.runAsync("DELETE FROM sync_queue WHERE id = ?", [id]);
}

export async function markFailed(id: number, permanent = false): Promise<void> {
  const db = await getDb();
  if (permanent) {
    await db.runAsync(
      "UPDATE sync_queue SET status = 'failed_permanent', last_attempted_at = ? WHERE id = ?",
      [now(), id],
    );
  } else {
    await db.runAsync(
      `UPDATE sync_queue
       SET status = 'pending', retry_count = retry_count + 1, last_attempted_at = ?
       WHERE id = ?`,
      [now(), id],
    );
  }
}

export async function getPermanentlyFailed(): Promise<QueueRow[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<RawRow>(
    "SELECT * FROM sync_queue WHERE status = 'failed_permanent' ORDER BY created_at DESC",
  );
  return rows.map(parseRow);
}
