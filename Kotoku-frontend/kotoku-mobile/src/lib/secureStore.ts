import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY  = "kotoku_access_token";
const REFRESH_TOKEN_KEY = "kotoku_refresh_token";
const PHONE_KEY         = "kotoku_auth_phone";
const ACCOUNT_ID_KEY    = "kotoku_auth_account_id";

export async function saveSession(
  accessToken: string,
  refreshToken: string,
  phone: string,
  accountId: number,
): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
  await SecureStore.setItemAsync(PHONE_KEY, phone);
  await SecureStore.setItemAsync(ACCOUNT_ID_KEY, String(accountId));
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function saveAccessToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

export async function getPhone(): Promise<string | null> {
  return SecureStore.getItemAsync(PHONE_KEY);
}

export async function getAccountId(): Promise<number | null> {
  const id = await SecureStore.getItemAsync(ACCOUNT_ID_KEY);
  return id ? Number(id) : null;
}

export async function clearSession(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  await SecureStore.deleteItemAsync(PHONE_KEY);
  await SecureStore.deleteItemAsync(ACCOUNT_ID_KEY);
}
