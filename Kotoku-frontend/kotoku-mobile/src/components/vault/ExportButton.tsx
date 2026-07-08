import { AlertCircle } from "lucide-react-native";
import { downloadAsync, deleteAsync, cacheDirectory } from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { Loader } from "lucide-react-native";
import { useState } from "react";
import { Text, View } from "react-native";

import { Button, NoticeCard } from "@/components/ui";
import { colors } from "@/theme/tokens";
import type { PdfStatus } from "@/types/vault";

interface ExportButtonProps {
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  onRequestExport: () => void;
  onRetryExport: () => void;
  isRequesting: boolean;
  isRetrying: boolean;
}

export function ExportButton({
  pdfStatus,
  pdfUrl,
  onRequestExport,
  onRetryExport,
  isRequesting,
  isRetrying,
}: ExportButtonProps) {
  const [saving, setSaving] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [shareError, setShareError] = useState<string | null>(null);
  const handleSaveToDevice = async () => {
    if (!pdfUrl) return;
    setSaving(true);
    setSaveError(null);
    let downloadedUri: string | null = null;
    try {
      const result = await downloadAsync(pdfUrl, cacheDirectory + "agreement.pdf");
      downloadedUri = result.uri;
      await Sharing.shareAsync(downloadedUri, {
        mimeType: "application/pdf",
        dialogTitle: "Save agreement PDF",
        UTI: "com.adobe.pdf",
      });
    } catch {
      setSaveError("Could not save to device. Please try again.");
    } finally {
      setSaving(false);
      if (downloadedUri) {
        try {
          await deleteAsync(downloadedUri);
        } catch {}
      }
    }
  };

  const handleShare = async () => {
    if (!pdfUrl) return;
    setSharing(true);
    setShareError(null);
    let downloadedUri: string | null = null;
    try {
      const result = await downloadAsync(pdfUrl, cacheDirectory + "agreement.pdf");
      downloadedUri = result.uri;
      await Sharing.shareAsync(downloadedUri, {
        mimeType: "application/pdf",
        dialogTitle: "Share agreement PDF",
      });
    } catch {
      setShareError("Could not download the PDF. Please try again.");
    } finally {
      setSharing(false);
      if (downloadedUri) {
        try {
          await deleteAsync(downloadedUri);
        } catch {}
      }
    }
  };

  const isBusy = saving || sharing;

  if (pdfStatus === "ready" && pdfUrl) {
    return (
      <View className="gap-sm">
        <NoticeCard
          variant="success"
          title="PDF ready"
          body="Save the sealed agreement to your device or share it securely with the other party."
        />
        <Button
          title={saving ? "Saving…" : "Save to Device"}
          variant="primary"
          size="md"
          fullWidth
          loading={saving}
          disabled={isBusy}
          onPress={handleSaveToDevice}
          accessibilityLabel="Save PDF to device"
        />
        {saveError && <NoticeCard variant="error" title="Save failed" body={saveError} />}
        <Button
          title={sharing ? "Preparing…" : "Share PDF"}
          variant="secondary"
          size="md"
          fullWidth
          loading={sharing}
          disabled={isBusy}
          onPress={handleShare}
          accessibilityLabel="Share agreement PDF"
        />
        {shareError && <NoticeCard variant="error" title="Share failed" body={shareError} />}
      </View>
    );
  }

  if (pdfStatus === "generating") {
    return (
      <View className="flex-row items-center justify-center gap-sm bg-surface-subtle rounded-lg p-md">
        <Loader size={16} color={colors.inkMuted} />
        <Text className="text-sm text-ink-secondary">Preparing PDF…</Text>
      </View>
    );
  }

  if (pdfStatus === "failed") {
    return (
      <View className="gap-sm">
        <NoticeCard
          variant="error"
          title="PDF generation failed"
          body="Kotoku could not prepare the agreement PDF. Retry to generate a fresh copy."
        />
        <Button
          title={isRetrying ? "Retrying…" : "Retry"}
          variant="secondary"
          size="md"
          fullWidth
          loading={isRetrying}
          onPress={onRetryExport}
        />
      </View>
    );
  }

  return (
    <Button
      title={isRequesting ? "Requesting…" : "Get PDF"}
      variant="secondary"
      size="md"
      fullWidth
      loading={isRequesting}
      onPress={onRequestExport}
    />
  );
}
