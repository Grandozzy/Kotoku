import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "kotoku_auth_token";
const PHONE_KEY = "kotoku_auth_phone";
const ACCOUNT_ID_KEY = "kotoku_auth_account_id";

export async function saveSession(token: string, phone: string, accountId: number): Promise<void> {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
  await SecureStore.setItemAsync(PHONE_KEY, phone);
  await SecureStore.setItemAsync(ACCOUNT_ID_KEY, String(accountId));
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function getPhone(): Promise<string | null> {
  return SecureStore.getItemAsync(PHONE_KEY);
}

export async function getAccountId(): Promise<number | null> {
  const id = await SecureStore.getItemAsync(ACCOUNT_ID_KEY);
  return id ? Number(id) : null;
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(PHONE_KEY);
  await SecureStore.deleteItemAsync(ACCOUNT_ID_KEY);
}
