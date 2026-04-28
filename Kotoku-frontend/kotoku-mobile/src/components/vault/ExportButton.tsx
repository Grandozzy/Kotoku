import { cacheDirectory, downloadAsync } from "expo-file-system/legacy";
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
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleShare = async () => {
    if (!pdfUrl) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      // Download to app cache directory then share
      const filename = `kotoku-agreement-${Date.now()}.pdf`;
      const localUri = `${cacheDirectory}${filename}`;
      await downloadAsync(pdfUrl, localUri);
      await Sharing.shareAsync(localUri, {
        mimeType: "application/pdf",
        dialogTitle: "Share agreement PDF",
      });
    } catch {
      setDownloadError("Could not download the PDF. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  if (pdfStatus === "ready" && pdfUrl) {
    return (
      <View className="gap-xs">
        <Button
          title={downloading ? "Preparing…" : "Share PDF"}
          variant="primary"
          size="md"
          fullWidth
          loading={downloading}
          onPress={handleShare}
          accessibilityLabel="Share agreement PDF"
        />
        {downloadError && (
          <Text className="text-xs text-semantic-error text-center">
            {downloadError}
          </Text>
        )}
      </View>
    );
  }

  if (pdfStatus === "pending") {
    return (
      <View className="flex-row items-center justify-center gap-sm bg-surface-subtle rounded-lg p-md">
        <Loader size={16} color={colors.inkMuted} />
        <Text className="text-sm text-ink-secondary">Preparing PDF…</Text>
      </View>
    );
  }

  // failed or not yet requested
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
