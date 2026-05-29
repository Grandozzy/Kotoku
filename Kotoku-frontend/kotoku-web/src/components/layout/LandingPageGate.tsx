"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/store/sessionStore";

export function LandingPageGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const accessToken = useSessionStore((s) => s.accessToken);
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const isBootstrapping = useSessionStore((s) => s.isBootstrapping);
  const isRecoveringSession = hasHydrated && isAuthenticated && !accessToken;

  useEffect(() => {
    if (!hasHydrated || isBootstrapping || isRecoveringSession) return;
    if (isAuthenticated) router.replace("/dashboard");
  }, [hasHydrated, isAuthenticated, isBootstrapping, isRecoveringSession, router]);

  if (!hasHydrated || isBootstrapping || isRecoveringSession || isAuthenticated) return null;

  return <>{children}</>;
}
