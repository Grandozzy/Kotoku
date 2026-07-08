import { Platform } from "react-native";

/**
 * Networking guide
 * ────────────────
 * ┌─────────────────────┬────────────────────────────────────┐
 * │ Target              │ What to do                         │
 * ├─────────────────────┼────────────────────────────────────┤
 * │ Android emulator    │ Leave .env blank — auto-detected   │
 * │ iOS simulator       │ Leave .env blank — auto-detected   │
 * │ Physical phone      │ Set EXPO_PUBLIC_API_URL in .env    │
 * │                     │ to http://<YOUR_LAN_IP>:8000       │
 * └─────────────────────┴────────────────────────────────────┘
 *
 * Android emulator maps 10.0.2.2 → host machine.
 * iOS simulator shares the host's network stack (localhost works).
 * Physical devices need your LAN IP (e.g. 192.168.100.19).
 *
 * To find your LAN IP:
 *   Windows: ipconfig | findstr /i "IPv4"
 *   macOS:   ipconfig getifaddr en0
 *   Linux:   hostname -I | awk '{print $1}'
 */

const EMULATOR_ANDROID = "http://10.0.2.2:8000";
const SIMULATOR_IOS = "http://localhost:8000";
const EMULATOR_ANDROID_WEB = "http://10.0.2.2:3000";
const SIMULATOR_IOS_WEB = "http://localhost:3000";

function _defaultApiUrl(): string {
  if (Platform.OS === "android") return EMULATOR_ANDROID;
  return SIMULATOR_IOS;
}

function _defaultWebUrl(): string {
  if (Platform.OS === "android") return EMULATOR_ANDROID_WEB;
  return SIMULATOR_IOS_WEB;
}

const envUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
const envWebUrl = process.env.EXPO_PUBLIC_WEB_URL?.trim();

export const API_BASE_URL = envUrl && envUrl.length > 0
  ? envUrl
  : _defaultApiUrl();

function _deriveWebUrlFromApiUrl(apiUrl: string): string {
  try {
    const parsed = new URL(apiUrl);
    if (parsed.port === "8000") parsed.port = "3000";
    else if (parsed.hostname.startsWith("api.")) parsed.hostname = parsed.hostname.slice(4);
    parsed.pathname = "";
    parsed.search = "";
    parsed.hash = "";
    return parsed.toString().replace(/\/$/, "");
  } catch {
    return _defaultWebUrl();
  }
}

export const WEB_BASE_URL = envWebUrl && envWebUrl.length > 0
  ? envWebUrl
  : _deriveWebUrlFromApiUrl(API_BASE_URL);

// In production builds (Expo sets __DEV__ = false), enforce HTTPS.
// Tokens transmitted over plain HTTP can be intercepted by a network
// observer — this is a hard fail so a misconfigured production env is
// caught immediately rather than silently leaking credentials.
if (!__DEV__ && API_BASE_URL.startsWith("http://")) {
  throw new Error(
    `[Kotoku] EXPO_PUBLIC_API_URL must use https:// in production builds.\n` +
    `Current value: "${API_BASE_URL}"`
  );
}

if (!__DEV__ && WEB_BASE_URL.startsWith("http://")) {
  throw new Error(
    `[Kotoku] EXPO_PUBLIC_WEB_URL must use https:// in production builds.\n` +
    `Current value: "${WEB_BASE_URL}"`
  );
}

export const OTP_EXPIRY_SECONDS = 600;
export const OTP_MAX_ATTEMPTS = 3;
export const FREE_RETENTION_DAYS = 60;
export const MAX_EVIDENCE_FILE_SIZE_MB = 50;
