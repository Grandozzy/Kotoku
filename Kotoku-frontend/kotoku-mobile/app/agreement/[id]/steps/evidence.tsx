import { useLocalSearchParams, useRouter } from "expo-router";
import { Mic, MicOff } from "lucide-react-native";
import { ScrollView, Text, View } from "react-native";

import { Button } from "@/components/ui";
import { PhotoSlot } from "@/components/evidence/PhotoSlot";
import { useAgreementStore, STEPS } from "@/features/agreements/agreementStore";
import { useEvidenceUpload } from "@/features/evidence/useEvidenceUpload";
import { useTemplate } from "@/features/agreements/useAgreementDraft";
import { colors } from "@/theme/tokens";

export default function EvidenceStep() {
  const router = useRouter();
  const { id, scenarioId: urlScenarioId } = useLocalSearchParams<{ id: string; scenarioId?: string }>();
  const storeScenarioId = useAgreementStore((s) => s.scenarioId);
  const scenarioId = storeScenarioId ?? urlScenarioId ?? null;
  const { nextStep, prevStep, stepIndex } = useAgreementStore();
  const template = useTemplate(scenarioId);
  const agreementId = Number(id);

  const { items, pickImage, retryUpload, error } = useEvidenceUpload(agreementId);

  if (!template) return null;

  const { slots, minimumPhotoCount } = template.evidenceRequirements;
  const photoSlots = slots.filter((s) => s.fileType === "photo");
  const voiceSlots = slots.filter((s) => s.fileType === "voice_note");

  const uploadedPhotoCount = photoSlots.filter(
    (s) => items[s.id]?.uploadStatus === "uploaded",
  ).length;
  const requiredPhotosUploaded = photoSlots
    .filter((s) => s.required)
    .every((s) => items[s.id]?.uploadStatus === "uploaded");
  const canProceed = uploadedPhotoCount >= minimumPhotoCount && requiredPhotosUploaded;

  const handleNext = () => {
    nextStep();
    router.push(`/agreement/${id}/steps/review?scenarioId=${scenarioId}`);
  };

  return (
    <ScrollView
      className="flex-1 bg-surface-canvas"
      contentContainerClassName="px-lg py-xl gap-xl"
      contentContainerStyle={{ paddingBottom: 60 }}
    >
      {/* Photos */}
      <View className="gap-md">
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
                  onPress={() => {
                    if (item?.uploadStatus === "failed") {
                      void retryUpload(slot.id);
                      return;
                    }
                    void pickImage(slot.id, slot.id);
                  }}
                />
              </View>
            );
          })}
        </View>
      </View>

      {/* Voice notes */}
      {voiceSlots.length > 0 && (
        <View className="gap-md">
          <Text className="text-lg font-semibold text-ink-primary">
            Voice summary
          </Text>
          <Text className="text-sm text-ink-secondary">
            Optional — record a brief spoken summary of the agreement.
          </Text>
          {voiceSlots.map((slot) => {
            const recorded = items[slot.id]?.uploadStatus === "uploaded";
            return (
              <View
                key={slot.id}
                className="flex-row items-center justify-between bg-surface-card rounded-lg p-lg border border-border-subtle"
              >
                <Text className="text-md text-ink-primary">{slot.label}</Text>
                {recorded ? (
                  <Mic size={22} color={colors.brandPrimary} />
                ) : (
                  <MicOff size={22} color={colors.inkMuted} />
                )}
              </View>
            );
          })}
          <Text className="text-xs text-ink-muted">
            Voice recording will be available in the next update.
          </Text>
        </View>
      )}

      {error && (
        <Text className="text-sm text-semantic-error">{error}</Text>
      )}

      {!canProceed && (
        <Text className="text-xs text-ink-muted text-center">
          Upload at least {minimumPhotoCount} photo{minimumPhotoCount !== 1 ? "s" : ""}, including all required ID photos, to continue.
        </Text>
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
    </ScrollView>
  );
}
