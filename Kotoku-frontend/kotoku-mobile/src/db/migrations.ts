import * as SQLite from "expo-sqlite";

import { CREATE_DRAFTS_TABLE, CREATE_SYNC_QUEUE_TABLE } from "./schema";

let db: SQLite.SQLiteDatabase | null = null;

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (db) return db;
  db = await SQLite.openDatabaseAsync("kotoku.db");
  return db;
}

/**
 * Run all DDL migrations idempotently (CREATE TABLE IF NOT EXISTS).
 * Call once at app startup from the root layout.
 */
export async function runMigrations(): Promise<void> {
  const database = await getDb();
  await database.execAsync(CREATE_DRAFTS_TABLE);
  await database.execAsync(CREATE_SYNC_QUEUE_TABLE);
}
