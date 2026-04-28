// SQLite table definitions.
// Migrations in migrations.ts apply these in order.

export const CREATE_DRAFTS_TABLE = `
  CREATE TABLE IF NOT EXISTS drafts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    agreement_id      INTEGER,
    scenario_id       TEXT    NOT NULL,
    title             TEXT    NOT NULL,
    step_index        INTEGER NOT NULL DEFAULT 0,
    party_a           TEXT    NOT NULL DEFAULT '{}',
    party_b           TEXT    NOT NULL DEFAULT '{}',
    subject_data      TEXT    NOT NULL DEFAULT '{}',
    synced            INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL
  );
`;

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
