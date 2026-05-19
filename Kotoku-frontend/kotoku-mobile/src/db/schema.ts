// SQLite table definitions.
// Migrations in migrations.ts apply these in order.

// action_type values: CREATE_DRAFT | UPDATE_DRAFT | UPLOAD_EVIDENCE | CONFIRM_OTP | SEAL
// status values:      pending | in_flight | failed_permanent
export const CREATE_SYNC_QUEUE_TABLE = `
  CREATE TABLE IF NOT EXISTS sync_queue (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type      TEXT    NOT NULL,
    payload          TEXT    NOT NULL,
    status           TEXT    NOT NULL DEFAULT 'pending',
    retry_count      INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL,
    last_attempted_at TEXT
  );
`;
