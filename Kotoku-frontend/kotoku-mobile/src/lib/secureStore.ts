import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY  = "kotoku_access_token";
const REFRESH_TOKEN_KEY = "kotoku_refresh_token";
const SESSION_ID_KEY    = "kotoku_session_id";
const PHONE_KEY         = "kotoku_auth_phone";
const ACCOUNT_ID_KEY    = "kotoku_auth_account_id";
const PIN_CONFIGURED_KEY = "kotoku_pin_configured";

export async function saveSession(
  accessToken: string,
  refreshToken: string,
  sessionId: string,
  phone: string,
  accountId: number,
  pinConfigured: boolean,
): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken),
    SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken),
    SecureStore.setItemAsync(SESSION_ID_KEY, sessionId),
    SecureStore.setItemAsync(PHONE_KEY, phone),
    SecureStore.setItemAsync(ACCOUNT_ID_KEY, String(accountId)),
    SecureStore.setItemAsync(PIN_CONFIGURED_KEY, pinConfigured ? "true" : "false"),
  ]);
}

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function getRefreshToken(): Promise<string | null> {
  return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
}

export async function getSessionId(): Promise<string | null> {
  return SecureStore.getItemAsync(SESSION_ID_KEY);
}

export async function saveAccessToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, token);
}

export async function saveTokens(
  accessToken: string,
  refreshToken: string,
  sessionId: string,
): Promise<void> {
  await Promise.all([
    SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken),
    SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken),
    SecureStore.setItemAsync(SESSION_ID_KEY, sessionId),
  ]);
}

export async function getPhone(): Promise<string | null> {
  return SecureStore.getItemAsync(PHONE_KEY);
}

export async function getAccountId(): Promise<number | null> {
  const id = await SecureStore.getItemAsync(ACCOUNT_ID_KEY);
  return id ? Number(id) : null;
}

export async function getPinConfigured(): Promise<boolean> {
  const val = await SecureStore.getItemAsync(PIN_CONFIGURED_KEY);
  return val === "true";
}

export async function savePinConfigured(configured: boolean): Promise<void> {
  await SecureStore.setItemAsync(PIN_CONFIGURED_KEY, configured ? "true" : "false");
}

export async function clearSession(): Promise<void> {
  await Promise.all([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    SecureStore.deleteItemAsync(SESSION_ID_KEY),
    SecureStore.deleteItemAsync(PHONE_KEY),
    SecureStore.deleteItemAsync(ACCOUNT_ID_KEY),
    SecureStore.deleteItemAsync(PIN_CONFIGURED_KEY),
  ]);
}
