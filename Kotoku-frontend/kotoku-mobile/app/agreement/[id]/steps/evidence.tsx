import { useLocalSearchParams, useRouter } from "expo-router";
import { Camera, Images } from "lucide-react-native";
import { useState } from "react";
import { ScrollView, Text, View } from "react-native";

import { UploadSourceSheet } from "@/components/evidence/UploadSourceSheet";
import { Button, NoticeCard, ScreenLoader } from "@/components/ui";
import { PhotoSlot } from "@/components/evidence/PhotoSlot";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useEvidenceUpload } from "@/features/evidence/useEvidenceUpload";
import { useTemplate } from "@/features/agreements/useAgreementDraft";

interface UploadSheetState {
  slotId: string;
  evidenceType: string;
  title: string;
  body: string;
  guidance: string;
}

export default function EvidenceStep() {
  const router = useRouter();
  const { id, scenarioId: urlScenarioId } = useLocalSearchParams<{ id: string; scenarioId?: string }>();
  const storeScenarioId = useAgreementStore((s) => s.scenarioId);
  const scenarioId = storeScenarioId ?? urlScenarioId ?? null;
  const { goToStep, prevStep, stepIndex } = useAgreementStore();
  const template = useTemplate(scenarioId);
  const agreementId = Number(id);

  const { items, pickImage, retryUpload, error } = useEvidenceUpload(agreementId);
  const [uploadSheet, setUploadSheet] = useState<UploadSheetState | null>(null);

  if (!template) return <ScreenLoader />;

  const { slots, minimumPhotoCount } = template.evidenceRequirements;
  const photoSlots = slots.filter((s) => s.fileType === "photo");

  const uploadedPhotoCount = photoSlots.filter(
    (s) => items[s.id]?.uploadStatus === "uploaded",
  ).length;
  const requiredPhotosUploaded = photoSlots
    .filter((s) => s.required)
    .every((s) => items[s.id]?.uploadStatus === "uploaded");
  const canProceed = uploadedPhotoCount >= minimumPhotoCount && requiredPhotosUploaded;

  const handleNext = () => {
    goToStep(3);
    router.push(`/agreement/${id}/steps/review?scenarioId=${scenarioId}`);
  };

  const handleSourcePick = async (source: "camera" | "library") => {
    if (!uploadSheet) return;
    const current = uploadSheet;
    setUploadSheet(null);
    await pickImage(current.slotId, current.evidenceType, { source, cameraType: "back" });
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      contentContainerStyle={{ paddingBottom: 60 }}
    >
      <View className="gap-md rounded-3xl bg-ink-primary p-lg">
        <View className="flex-row items-start gap-md">
          <View className="h-11 w-11 items-center justify-center rounded-2xl bg-white/10">
            <Images size={22} color="#fff" strokeWidth={1.8} />
          </View>
          <View className="flex-1 gap-xs">
            <Text className="text-[11px] font-semibold uppercase tracking-[2px] text-white/60">
              Step 3
            </Text>
            <Text className="text-xl font-semibold text-white">Capture the evidence</Text>
            <Text className="text-sm leading-relaxed text-white/75">
              Add clear photos that show the asset, its condition, and anything either party may later rely on.
            </Text>
          </View>
        </View>
      </View>

      {/* Photos */}
      <View className="gap-md rounded-2xl border border-border-subtle bg-surface-card p-lg">
        <View>
          <Text className="text-lg font-semibold text-ink-primary">Photos</Text>
          <Text className="text-sm text-ink-secondary mt-xs">
            Minimum {minimumPhotoCount} photos required.
          </Text>
        </View>

        <View className="flex-row flex-wrap gap-sm">
          {photoSlots.map((slot) => {
            const item = items[slot.id];
            return (
              <View key={slot.id} style={{ width: "47%" }}>
                <PhotoSlot
                  label={slot.label}
                  required={slot.required}
                  localUri={item?.localUri}
                  status={item?.uploadStatus}
                  error={item?.error}
                  failedActionLabel={item?.retryable === false ? "Replace" : "Retry"}
                  onPress={() => {
                    if (item?.uploadStatus === "failed") {
                      if (item.retryable === false) {
                        setUploadSheet({
                          slotId: slot.id,
                          evidenceType: slot.id,
                          title: slot.label,
                          body: "Add a clear evidence photo using the camera or your gallery.",
                          guidance:
                            "Use well-lit images that clearly show the asset, its condition, and any details the parties may later rely on.",
                        });
                        return;
                      }
                      void retryUpload(slot.id);
                      return;
                    }
                    setUploadSheet({
                      slotId: slot.id,
                      evidenceType: slot.id,
                      title: slot.label,
                      body: "Add a clear evidence photo using the camera or your gallery.",
                      guidance:
                        "Prefer wide shots first, then capture close details, defects, serial numbers, or other identifying marks.",
                    });
                  }}
                />
              </View>
            );
          })}
        </View>
      </View>

      {error && (
        <NoticeCard
          variant="error"
          title="Evidence upload needs attention"
          body={error}
          compact
        />
      )}

      {!canProceed && (
        <NoticeCard
          variant="info"
          icon={Camera}
          title="What to capture"
          body={`Upload at least ${minimumPhotoCount} photo${minimumPhotoCount !== 1 ? "s" : ""}. Prioritize clear wide shots, visible defects, and identifying details.`}
          compact
        />
      )}

      <View className="flex-row gap-sm">
        {stepIndex > 0 && (
          <View style={{ flex: 1 }}>
            <Button
              title="Back"
              variant="secondary"
              size="lg"
              onPress={() => {
                prevStep();
                router.replace(`/agreement/${id}/steps/${STEPS[stepIndex - 1]}`);
              }}
            />
          </View>
        )}
        <View style={{ flex: 2 }}>
          <Button
            title="Proceed"
            variant="primary"
            size="lg"
            disabled={!canProceed}
            onPress={handleNext}
          />
        </View>
      </View>
      <UploadSourceSheet
        visible={Boolean(uploadSheet)}
        onClose={() => setUploadSheet(null)}
        title={uploadSheet?.title ?? "Add evidence photo"}
        body={uploadSheet?.body ?? "Choose how to add this evidence photo."}
        guidance={uploadSheet?.guidance}
        onPickCamera={() => {
          void handleSourcePick("camera");
        }}
        onPickLibrary={() => {
          void handleSourcePick("library");
        }}
      />
    </ScrollView>
  );
}
