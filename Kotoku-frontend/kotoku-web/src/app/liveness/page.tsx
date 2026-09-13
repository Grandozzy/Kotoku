"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Amplify } from "aws-amplify";
import { FaceLivenessDetector } from "@aws-amplify/ui-react-liveness";
import "@aws-amplify/ui-react/styles.css";

Amplify.configure({
  Auth: {
    Cognito: {
      identityPoolId:
        process.env.NEXT_PUBLIC_AMPLIFY_IDENTITY_POOL_ID ??
        "eu-west-1:869e47c6-53c0-4dbc-9379-bcae17769346",
      allowGuestAccess: true,
    },
  },
});

type NativeBridgeWindow = Window &
  typeof globalThis & {
    ReactNativeWebView?: {
      postMessage: (message: string) => void;
    };
  };

const LIVENESS_ERROR_MESSAGES: Record<string, string> = {
  CAMERA_ACCESS_DENIED: "Camera access was denied. Please allow camera permission and try again.",
  TIMEOUT: "The face check timed out. Please try again.",
  SERVER_ERROR: "A server error occurred during the face check. Please try again.",
  RUNTIME_ERROR: "An unexpected error occurred during the face check. Please try again.",
  FACE_DISTANCE_TOO_FAR_AT_START: "Please position your face closer to the camera and try again.",
  MOBILE_LANDSCAPE_MODE: "Please hold your phone upright (portrait mode) and try again.",
  FRESHNESS_TIMEOUT: "Face check timed out. Try again in better lighting.",
};

function postToNative(data: Record<string, unknown>) {
  if (typeof window === "undefined") return;

  const nativeWindow = window as NativeBridgeWindow;
  nativeWindow.ReactNativeWebView?.postMessage(JSON.stringify(data));
}

function LivenessDetector() {
  const params = useSearchParams();
  const sessionId = params.get("session_id") ?? "";
  const region = params.get("region") ?? "eu-west-1";

  if (!sessionId) {
    return (
      <div className="flex h-screen items-center justify-center text-sm text-neutral-500">
        Missing session ID. Return to the app and try again.
      </div>
    );
  }

  return (
    <FaceLivenessDetector
      sessionId={sessionId}
      region={region}
      onAnalysisComplete={async () => {
        postToNative({ type: "done" });
      }}
      onError={(error) => {
        const state = (error as { state?: string }).state ?? "";
        console.error("[Liveness] onError state=%s error=%o", state, error);
        postToNative({
          type: "error",
          message: LIVENESS_ERROR_MESSAGES[state] ?? "Face check failed. Please try again.",
        });
      }}
    />
  );
}

export default function LivenessPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center text-sm text-neutral-400">
          Loading face check…
        </div>
      }
    >
      <LivenessDetector />
    </Suspense>
  );
}
