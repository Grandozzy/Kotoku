"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Amplify } from "aws-amplify";
import { FaceLivenessDetector } from "@aws-amplify/ui-react-liveness";
import "@aws-amplify/ui-react/styles.css";

Amplify.configure({
  Auth: {
    Cognito: {
      identityPoolId: "eu-west-1:869e47c6-53c0-4dbc-9379-bcae17769346",
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
      onError={(error) =>
        postToNative({
          type: "error",
          message: String((error as { state?: string }).state ?? error),
        })
      }
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
