import { useEffect, useRef } from "react";
import { Modal, TouchableOpacity, View } from "react-native";
import { WebView, type WebViewMessageEvent } from "react-native-webview";
import { X } from "lucide-react-native";

import { WEB_BASE_URL } from "@/constants/config";

const WATCHDOG_MS = 3 * 60 * 1000; // 3 minutes — generous upper bound for the full liveness flow

interface Props {
  sessionId: string;
  region: string;
  onComplete: () => void;
  onError: (message: string) => void;
  onClose: () => void;
}

export function LivenessWebView({ sessionId, region, onComplete, onError, onClose }: Props) {
  const settled = useRef(false);
  const uri = `${WEB_BASE_URL}/liveness?session_id=${encodeURIComponent(sessionId)}&region=${encodeURIComponent(region)}`;

  // Watchdog: if the Amplify component crashes or the network drops mid-session,
  // neither onAnalysisComplete nor onError fires and postToNative never runs.
  // After WATCHDOG_MS with no resolution, surface an error so the user isn't
  // stranded in the full-screen modal.
  useEffect(() => {
    const timer = setTimeout(() => {
      if (settled.current) return;
      settled.current = true;
      onError("The face check timed out. Please try again.");
    }, WATCHDOG_MS);
    return () => clearTimeout(timer);
    // onError identity is stable for the lifetime of this modal mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleMessage(event: WebViewMessageEvent) {
    if (settled.current) return;
    try {
      const data = JSON.parse(event.nativeEvent.data) as { type: string; message?: string };
      if (data.type === "done") {
        settled.current = true;
        onComplete();
      } else if (data.type === "error") {
        settled.current = true;
        onError(data.message ?? "Face check failed. Please try again.");
      }
    } catch {
      // ignore non-JSON messages from page scripts
    }
  }

  return (
    <Modal visible animationType="slide" presentationStyle="fullScreen" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: "#000" }}>
        <WebView
          source={{ uri }}
          onMessage={handleMessage}
          allowsInlineMediaPlayback
          mediaPlaybackRequiresUserAction={false}
          mediaCapturePermissionGrantType="grant"
          javaScriptEnabled
          domStorageEnabled
        />
        <TouchableOpacity
          onPress={onClose}
          style={{
            position: "absolute",
            top: 52,
            right: 16,
            zIndex: 100,
            width: 36,
            height: 36,
            borderRadius: 18,
            backgroundColor: "rgba(0,0,0,0.5)",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <X size={20} color="#fff" strokeWidth={2} />
        </TouchableOpacity>
      </View>
    </Modal>
  );
}
