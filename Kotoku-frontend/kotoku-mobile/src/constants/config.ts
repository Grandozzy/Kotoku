import { Platform } from "react-native";

// Android emulator routes 10.0.2.2 → host machine; iOS simulator uses localhost.
// For physical devices set EXPO_PUBLIC_API_URL to your machine's LAN IP, e.g.:
//   EXPO_PUBLIC_API_URL=http://192.168.x.x:8000 npx expo start
const _defaultUrl =
  Platform.OS === "android"
    ? "http://10.0.2.2:8000"
    : "http://localhost:8000";

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? _defaultUrl;

export const OTP_EXPIRY_SECONDS = 600; // 10 minutes
export const OTP_MAX_ATTEMPTS = 3;
export const FREE_RETENTION_DAYS = 60; // 2 months
export const MAX_EVIDENCE_FILE_SIZE_MB = 50;
