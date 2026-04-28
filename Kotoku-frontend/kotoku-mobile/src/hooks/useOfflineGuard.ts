import { useNetworkStatus } from "./useNetworkStatus";

/**
 * Returns true when the device is definitely offline.
 * Use to disable actions that require connectivity or show the offline banner.
 */
export function useOfflineGuard(): boolean {
  const { isConnected, isInternetReachable, isReady } = useNetworkStatus();
  if (!isReady) return false; // optimistic until we know
  return !isConnected || !isInternetReachable;
}
