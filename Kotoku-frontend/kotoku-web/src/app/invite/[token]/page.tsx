"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  ScanFace,
  ShieldCheck,
  Upload,
  UserCheck,
} from "lucide-react";
import { Amplify } from "aws-amplify";
import { FaceLivenessDetector } from "@aws-amplify/ui-react-liveness";
import "@aws-amplify/ui-react/styles.css";

import { authApi } from "@/api/auth";
import { evidenceApi } from "@/api/evidence";
import { invitesApi, type InviteDetail } from "@/api/invites";
import { KotokuLogo } from "@/components/brand/KotokuLogo";
import { isValidE164Phone } from "@/lib/phone";
import { useSessionStore } from "@/store/sessionStore";

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

type Step = "loading" | "error" | "preview" | "login" | "verify_otp" | "upload" | "liveness" | "done";

async function sha256Hex(file: File): Promise<string> {
  const buf = await file.arrayBuffer();
  const hashBuf = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hashBuf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function uploadCard(agreementId: number, role: string, side: "front" | "back", file: File) {
  const evidenceType = `${role}_ghana_card_${side}`;
  const mimeType = file.type || "image/jpeg";
  const checksum = await sha256Hex(file);

  const { upload_url, file_key, headers } = await evidenceApi.requestUploadUrl(agreementId, {
    evidence_type: evidenceType,
    mime_type: mimeType,
    size_bytes: file.size,
    checksum_sha256: checksum,
  });

  const putRes = await fetch(upload_url, {
    method: "PUT",
    headers: { ...headers, "Content-Type": mimeType },
    body: file,
  });
  if (!putRes.ok) throw new Error("Failed to upload image to storage.");

  await evidenceApi.confirm(agreementId, {
    file_key,
    evidence_type: evidenceType,
    mime_type: mimeType,
    checksum_sha256: checksum,
  });
}

export default function InvitePage() {
  const params = useParams<{ token: string }>();
  const token = params.token;

  const isAuthenticated = useSessionStore((s) => s.isAuthenticated);
  const hasHydrated = useSessionStore((s) => s.hasHydrated);
  const setSession = useSessionStore((s) => s.setSession);

  const [step, setStep] = useState<Step>("loading");
  const [invite, setInvite] = useState<InviteDetail | null>(null);
  const [inviteError, setInviteError] = useState<string | null>(null);

  // After claim
  const [agreementId, setAgreementId] = useState<number | null>(null);
  const [role, setRole] = useState<string | null>(null);

  // Login step
  const [localDigits, setLocalDigits] = useState("");
  const [otp, setOtp] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState(false);
  const phone = `+233${localDigits}`;
  const isValidPhone = localDigits.length === 9 && isValidE164Phone(phone);

  // Upload step
  const [frontFile, setFrontFile] = useState<File | null>(null);
  const [backFile, setBackFile] = useState<File | null>(null);
  const [frontPreview, setFrontPreview] = useState<string | null>(null);
  const [backPreview, setBackPreview] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [cardsUploaded, setCardsUploaded] = useState(false);

  // Liveness step
  const [livenessSessionId, setLivenessSessionId] = useState<string | null>(null);
  const [livenessRegion, setLivenessRegion] = useState("eu-west-1");
  const [livenessError, setLivenessError] = useState<string | null>(null);
  const [livenessLoading, setLivenessLoading] = useState(false);

  const claimInProgress = useRef(false);

  // Fetch invite detail on mount
  useEffect(() => {
    if (!token) {
      setInviteError("This invite link is missing required information.");
      setStep("error");
      return;
    }
    invitesApi
      .getDetail(token)
      .then((detail) => {
        setInvite(detail);
        setStep("preview");
      })
      .catch((err) => {
        setInviteError(
          err instanceof Error ? err.message : "This invite link is invalid or has expired.",
        );
        setStep("error");
      });
  }, [token]);

  async function handleContinue() {
    if (!hasHydrated) return;
    if (!isAuthenticated) {
      setStep("login");
      return;
    }
    await doClaim();
  }

  async function doClaim() {
    if (claimInProgress.current || !token) return;
    claimInProgress.current = true;
    setAuthError(null);
    try {
      const result = await invitesApi.claim(token);
      setAgreementId(result.agreement_id);
      setRole(result.role);
      setStep("upload");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not start the identity check.";
      if (msg.toLowerCase().includes("phone number")) {
        setAuthError(
          "This invite was sent to a different phone number. Log in with the number that received the SMS.",
        );
      } else {
        setAuthError(msg);
      }
      setStep("preview");
    } finally {
      claimInProgress.current = false;
    }
  }

  async function handleSendOtp(e: React.FormEvent) {
    e.preventDefault();
    if (!isValidPhone) return;
    setAuthError(null);
    setResendSuccess(false);
    setAuthLoading(true);
    try {
      await authApi.requestOtp(phone);
      setStep("verify_otp");
    } catch {
      setAuthError("Could not send OTP. Check the number and try again.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault();
    if (otp.length < 6) return;
    setAuthError(null);
    setAuthLoading(true);
    try {
      const res = await authApi.verifyOtp(phone, otp);
      if (!res.user.account_id) throw new Error("Account not linked.");
      setSession(res.access, res.user.account_id, res.user.phone);
      await doClaim();
    } catch {
      setAuthError("Invalid or expired code. Try again.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleResendOtp() {
    if (!isValidPhone) return;
    setOtp("");
    setAuthError(null);
    setResendSuccess(false);
    setAuthLoading(true);
    try {
      await authApi.requestOtp(phone);
      setResendSuccess(true);
    } catch {
      setAuthError("Could not resend OTP.");
    } finally {
      setAuthLoading(false);
    }
  }

  function handleFileSelect(side: "front" | "back", file: File | null) {
    if (!file) return;
    const url = URL.createObjectURL(file);
    if (side === "front") {
      setFrontFile(file);
      if (frontPreview) URL.revokeObjectURL(frontPreview);
      setFrontPreview(url);
    } else {
      setBackFile(file);
      if (backPreview) URL.revokeObjectURL(backPreview);
      setBackPreview(url);
    }
  }

  async function handleUpload() {
    if (!frontFile || !backFile || !agreementId || !role) return;
    setUploadLoading(true);
    setUploadError(null);
    try {
      await Promise.all([
        uploadCard(agreementId, role, "front", frontFile),
        uploadCard(agreementId, role, "back", backFile),
      ]);
      setCardsUploaded(true);
      await startLiveness();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Upload failed. Check your connection and try again.",
      );
    } finally {
      setUploadLoading(false);
    }
  }

  async function startLiveness() {
    if (!agreementId || !role) return;
    setLivenessLoading(true);
    setLivenessError(null);
    try {
      const { session_id, region } = await invitesApi.createLivenessSession(agreementId, role);
      setLivenessSessionId(session_id);
      setLivenessRegion(region);
      setStep("liveness");
    } catch {
      setLivenessError("Could not start face check. Please try again.");
      setStep("upload");
    } finally {
      setLivenessLoading(false);
    }
  }

  async function handleLivenessComplete() {
    if (!agreementId || !role) return;
    try {
      await invitesApi.submitLivenessResult(agreementId, role);
      setStep("done");
    } catch {
      setLivenessError(
        "Face check completed but we could not confirm your result. Tap below to try again.",
      );
      setLivenessSessionId(null);
      setStep("upload");
    }
  }

  function handleLivenessError(error: unknown) {
    const state = (error as { state?: string }).state;
    setLivenessError(
      state
        ? `Face check failed: ${state}. Please try again.`
        : "Face check failed. Please try again.",
    );
    setLivenessSessionId(null);
    setStep("upload");
  }

  // --- Render helpers ---

  const shell = (children: React.ReactNode) => (
    <main className="min-h-screen bg-neutral-50 px-5 py-10">
      <div className="mx-auto max-w-xl space-y-5">
        <KotokuLogo />
        {children}
      </div>
    </main>
  );

  if (step === "loading") {
    return shell(
      <div className="flex h-48 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-200 border-t-blue-600" />
      </div>,
    );
  }

  if (step === "error") {
    return shell(
      <div className="rounded-3xl border border-red-100 bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center gap-4 py-6 text-center">
          <AlertCircle size={44} className="text-red-500" strokeWidth={1.5} />
          <h1 className="text-2xl font-bold text-neutral-900">Invite unavailable</h1>
          <p className="text-sm leading-6 text-neutral-600">
            {inviteError ?? "This invite link is invalid or has expired. Ask the agreement creator to resend."}
          </p>
        </div>
      </div>,
    );
  }

  if (step === "preview") {
    return shell(
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5">
        <div className="flex flex-col items-center gap-3 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
            <UserCheck size={32} color="#2563EB" strokeWidth={1.5} />
          </div>
          <h1 className="text-2xl font-bold text-neutral-900">Identity verification</h1>
          <p className="text-sm text-neutral-500">
            You have been invited to verify your identity for
          </p>
          <p className="text-lg font-semibold text-neutral-900">{invite!.agreement_title}</p>
          <p className="text-sm text-neutral-500">
            as {invite!.role} ({invite!.party_name})
          </p>
        </div>

        <div className="rounded-2xl border border-neutral-100 bg-neutral-50 p-4">
          <div className="flex items-start gap-3">
            <Clock size={16} className="mt-0.5 shrink-0 text-neutral-400" strokeWidth={1.8} />
            <p className="text-sm text-neutral-600">
              You will upload your Ghana Card (front and back) and complete a quick face liveness check. This takes about 2 minutes.
            </p>
          </div>
        </div>

        {authError && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{authError}</p>
        )}

        {!isAuthenticated && (
          <p className="rounded-xl bg-blue-50 px-4 py-3 text-sm text-blue-700">
            You will need to log in with the phone number that received this invite.
          </p>
        )}

        <button
          onClick={() => void handleContinue()}
          className="btn-primary w-full"
        >
          {isAuthenticated ? "Start verification" : "Log in to continue"}
          <ArrowRight size={14} />
        </button>
      </div>,
    );
  }

  if (step === "login") {
    return shell(
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Sign in</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Enter the phone number that received this invite.
          </p>
        </div>

        <form onSubmit={(e) => void handleSendOtp(e)} className="flex flex-col gap-4">
          <div>
            <label htmlFor="phone" className="text-sm font-medium text-neutral-700">
              Phone number
            </label>
            <div className="mt-1 flex rounded-lg border border-neutral-200 focus-within:ring-2 focus-within:ring-blue-500">
              <span className="flex items-center rounded-l-lg border-r border-neutral-200 bg-neutral-50 px-3 text-sm text-neutral-500 select-none">
                🇬🇭 +233
              </span>
              <input
                id="phone"
                type="tel"
                placeholder="XX XXX XXXX"
                maxLength={9}
                value={localDigits}
                onChange={(e) => {
                  const d = e.target.value.replace(/\D/g, "");
                  setLocalDigits(d.slice(0, 9));
                  if (authError) setAuthError(null);
                }}
                className="flex-1 rounded-r-lg bg-white px-4 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
              />
            </div>
          </div>
          {authError && <p className="text-sm text-red-600">{authError}</p>}
          <button type="submit" disabled={authLoading || !isValidPhone} className="btn-primary w-full">
            {authLoading ? "Sending…" : <><span>Send code</span><ArrowRight size={14} /></>}
          </button>
        </form>
      </div>,
    );
  }

  if (step === "verify_otp") {
    return shell(
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Enter your code</h1>
          <p className="mt-1 text-sm text-neutral-500">
            We sent a 6-digit code to <span className="font-semibold text-neutral-700">{phone}</span>. It expires in 10 minutes.
          </p>
        </div>

        <form onSubmit={(e) => void handleVerifyOtp(e)} className="flex flex-col gap-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={6}
            placeholder="000000"
            value={otp}
            onChange={(e) => {
              setOtp(e.target.value.replace(/\D/g, "").slice(0, 6));
              if (authError) setAuthError(null);
            }}
            className="form-control px-3 py-3 text-center font-mono text-2xl tracking-[0.4em]"
          />
          {authError && <p className="text-sm text-red-600">{authError}</p>}
          <button type="submit" disabled={authLoading || otp.length < 6} className="btn-primary w-full">
            {authLoading ? "Verifying…" : <><span>Confirm</span><ArrowRight size={14} /></>}
          </button>
        </form>

        <div className="flex flex-col items-center gap-2">
          <p className="text-sm text-neutral-500">Didn&apos;t receive a code?</p>
          <button
            type="button"
            onClick={() => void handleResendOtp()}
            disabled={authLoading}
            className="inline-flex items-center gap-1 text-sm font-medium text-blue-600 disabled:text-neutral-400"
          >
            {resendSuccess ? <><CheckCircle2 size={14} />Code sent</> : "Resend code"}
          </button>
        </div>
      </div>,
    );
  }

  if (step === "upload") {
    const cardSlot = (
      side: "front" | "back",
      label: string,
      file: File | null,
      preview: string | null,
    ) => (
      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-2xl border-2 border-dashed border-neutral-200 bg-neutral-50 p-4 transition hover:border-blue-400 hover:bg-blue-50">
        {preview ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview} alt={label} className="h-28 w-full rounded-xl object-cover" />
        ) : (
          <div className="flex h-28 w-full flex-col items-center justify-center gap-2 text-neutral-400">
            <Upload size={24} strokeWidth={1.5} />
            <span className="text-xs font-medium">Tap to add</span>
          </div>
        )}
        <span className="text-xs font-semibold text-neutral-600">{label}</span>
        {file && <span className="text-xs text-neutral-400">{file.name}</span>}
        <input
          type="file"
          accept="image/jpeg,image/png"
          capture="environment"
          className="sr-only"
          onChange={(e) => handleFileSelect(side, e.target.files?.[0] ?? null)}
        />
      </label>
    );

    return shell(
      <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm space-y-5">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">
            {cardsUploaded ? "Face check" : "Upload your Ghana Card"}
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            {cardsUploaded
              ? "Your Ghana Card was uploaded. Tap below to retry the face check."
              : "Take a clear photo of both sides. Make sure all edges are visible and there is no glare."}
          </p>
        </div>

        {!cardsUploaded && (
          <div className="grid grid-cols-2 gap-3">
            {cardSlot("front", "Front", frontFile, frontPreview)}
            {cardSlot("back", "Back", backFile, backPreview)}
          </div>
        )}

        {uploadError && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{uploadError}</p>
        )}
        {livenessError && (
          <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{livenessError}</p>
        )}

        {cardsUploaded ? (
          <button
            onClick={() => void startLiveness()}
            disabled={livenessLoading}
            className="btn-primary w-full"
          >
            {livenessLoading ? "Starting…" : <><ScanFace size={16} /><span>Retry face check</span></>}
          </button>
        ) : (
          <button
            onClick={() => void handleUpload()}
            disabled={!frontFile || !backFile || uploadLoading || livenessLoading}
            className="btn-primary w-full"
          >
            {uploadLoading
              ? "Uploading…"
              : livenessLoading
                ? "Starting face check…"
                : <><ScanFace size={16} /><span>Continue to face check</span></>}
          </button>
        )}
      </div>,
    );
  }

  if (step === "liveness" && livenessSessionId) {
    return (
      <main className="min-h-screen bg-neutral-50">
        <div className="mx-auto max-w-xl px-5 pt-6">
          <KotokuLogo />
          <p className="mt-4 text-sm text-neutral-500">
            Follow the on-screen prompts to complete the face check.
          </p>
        </div>
        <div className="mt-4">
          <FaceLivenessDetector
            sessionId={livenessSessionId}
            region={livenessRegion}
            onAnalysisComplete={handleLivenessComplete}
            onError={handleLivenessError}
          />
        </div>
      </main>
    );
  }

  if (step === "done") {
    return shell(
      <div className="rounded-3xl border border-emerald-100 bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center gap-4 py-6 text-center">
          <CheckCircle2 size={48} className="text-emerald-500" strokeWidth={1.5} />
          <h1 className="text-2xl font-bold text-neutral-900">Verification submitted</h1>
          <p className="text-sm leading-6 text-neutral-600">
            Your Ghana Card and face check have been submitted for{" "}
            <span className="font-semibold">{invite?.agreement_title}</span>. The agreement creator will be notified once verification is complete.
          </p>
          <div className="flex items-center gap-1.5 text-xs text-neutral-400">
            <ShieldCheck size={12} strokeWidth={2} />
            Recognised under Ghana&apos;s Electronic Transactions Act (Act 772)
          </div>
        </div>
      </div>,
    );
  }

  return null;
}
