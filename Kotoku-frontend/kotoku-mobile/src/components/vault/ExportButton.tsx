import { downloadAsync, deleteAsync, cacheDirectory } from "expo-file-system/legacy";
import * as Sharing from "expo-sharing";
import { Loader } from "lucide-react-native";
import { useState } from "react";
import { Text, View } from "react-native";

import { Button } from "@/components/ui";
import { colors } from "@/theme/tokens";
import type { PdfStatus } from "@/types/vault";

interface ExportButtonProps {
  pdfStatus: PdfStatus;
  pdfUrl: string | null;
  onRequestExport: () => void;
  isRequesting: boolean;
}

export function ExportButton({
  pdfStatus,
  pdfUrl,
  onRequestExport,
  isRequesting,
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
    } catch (err) {
      console.warn("[DEBUG] SAVE ERROR:", err);
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
      <View className="gap-xs">
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
        {saveError && (
          <Text className="text-xs text-semantic-error text-center">
            {saveError}
          </Text>
        )}
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
        {shareError && (
          <Text className="text-xs text-semantic-error text-center">
            {shareError}
          </Text>
        )}
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
