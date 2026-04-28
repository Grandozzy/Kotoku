import NetInfo, { NetInfoState } from "@react-native-community/netinfo";
import { useEffect, useState } from "react";

interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean;
  // false during the initial check before NetInfo responds
  isReady: boolean;
}

export function useNetworkStatus(): NetworkStatus {
  const [state, setState] = useState<NetworkStatus>({
    isConnected: true,
    isInternetReachable: true,
    isReady: false,
  });

  useEffect(() => {
    // Fetch current state immediately
    NetInfo.fetch().then((s: NetInfoState) => {
      setState({
        isConnected: s.isConnected ?? true,
        isInternetReachable: s.isInternetReachable ?? true,
        isReady: true,
      });
    });

    const unsubscribe = NetInfo.addEventListener((s: NetInfoState) => {
      setState({
        isConnected: s.isConnected ?? true,
        isInternetReachable: s.isInternetReachable ?? true,
        isReady: true,
      });
    });

    return unsubscribe;
  }, []);

  return state;
}
