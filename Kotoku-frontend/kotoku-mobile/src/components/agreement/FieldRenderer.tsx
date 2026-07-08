import { Controller, Control } from "react-hook-form";
import { CalendarDays, CheckCircle2, Coins, Hash, ListFilter } from "lucide-react-native";
import { Pressable, Switch, Text, View } from "react-native";

import { TextInput } from "@/components/ui";
import { colors } from "@/theme/tokens";
import type { FieldDefinition } from "@/types/template";

interface FieldRendererProps {
  name: string;
  field: FieldDefinition;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: Control<any>;
  error?: string;
  // Provide current form values so conditional fields can evaluate
  watchValues?: Record<string, unknown>;
}

export function FieldRenderer({
  name,
  field,
  control,
  error,
  watchValues = {},
}: FieldRendererProps) {
  // Evaluate conditional visibility
  if (field.conditionalOn) {
    const { field: condField, value: condValue } = field.conditionalOn;
    if (watchValues[condField] !== condValue) return null;
  }

  return (
    <Controller
      control={control}
      name={name}
      render={({ field: { value, onChange, onBlur } }) => {
        const wrapField = (content: React.ReactNode, helper?: React.ReactNode) => (
          <View className="gap-sm rounded-2xl border border-border-subtle bg-surface-subtle p-md">
            {content}
            {helper}
          </View>
        );

        switch (field.type) {
          case "text":
            return wrapField(
              <TextInput
                label={field.label}
                placeholder={field.placeholder}
                hint={field.hint}
                value={value ?? ""}
                onChangeText={onChange}
                onBlur={onBlur}
                error={error}
                required={field.required}
              />,
            );

          case "textarea":
            return wrapField(
              <TextInput
                label={field.label}
                placeholder={field.placeholder}
                hint={field.hint}
                value={value ?? ""}
                onChangeText={onChange}
                onBlur={onBlur}
                error={error}
                required={field.required}
                multiline
                numberOfLines={3}
                style={{ minHeight: 80, textAlignVertical: "top" }}
              />,
            );

          case "number":
            return wrapField(
              <TextInput
                label={field.label}
                placeholder={field.placeholder}
                hint={field.hint}
                keyboardType="number-pad"
                value={value != null ? String(value) : ""}
                onChangeText={(t) => onChange(t === "" ? undefined : Number(t))}
                onBlur={onBlur}
                error={error}
                required={field.required}
              />,
            );

          case "currency":
            return wrapField(
              <View>
                {field.label && (
                  <View className="flex-row mb-xs">
                    <Text className="text-sm font-medium text-ink-secondary">
                      {field.label}
                    </Text>
                    {field.required && (
                      <Text className="text-sm text-semantic-error ml-xs">*</Text>
                    )}
                  </View>
                )}
                <View className="flex-row items-center overflow-hidden rounded-xl border border-border-subtle bg-surface-card">
                  <View className="flex-row items-center gap-xs border-r border-border-subtle bg-surface-subtle px-md py-sm">
                    <Coins size={14} color={colors.inkMuted} strokeWidth={1.8} />
                    <Text className="text-md text-ink-secondary font-medium">GHS</Text>
                  </View>
                  <TextInput
                    placeholder={field.placeholder ?? "0.00"}
                    hint={field.hint}
                    keyboardType="decimal-pad"
                    value={value != null ? String(value) : ""}
                    onChangeText={(t) =>
                      onChange(t === "" ? undefined : parseFloat(t))
                    }
                    onBlur={onBlur}
                    error={error}
                    className="flex-1 border-0"
                  />
                </View>
              </View>,
            );

          case "date":
            return wrapField(
              <TextInput
                label={field.label}
                placeholder={field.placeholder ?? "YYYY-MM-DD"}
                hint={field.hint}
                keyboardType="numbers-and-punctuation"
                value={value ?? ""}
                onChangeText={onChange}
                onBlur={onBlur}
                error={error}
                required={field.required}
                maxLength={10}
              />,
              <View className="flex-row items-center gap-xs">
                <CalendarDays size={13} color={colors.inkMuted} strokeWidth={1.8} />
                <Text className="text-[11px] text-ink-muted">
                  Use the agreed date exactly as it should appear in the final record.
                </Text>
              </View>,
            );

          case "select":
            return wrapField(
              <View>
                {field.label && (
                  <View className="flex-row mb-sm">
                    <Text className="text-sm font-medium text-ink-secondary">
                      {field.label}
                    </Text>
                    {field.required && (
                      <Text className="text-sm text-semantic-error ml-xs">*</Text>
                    )}
                  </View>
                )}
                <View className="flex-row flex-wrap gap-sm">
                  {(field.options ?? []).map((opt) => {
                    const selected = value === opt.value;
                    return (
                      <Pressable
                        key={opt.value}
                        onPress={() => onChange(opt.value)}
                        className={[
                          "flex-row items-center gap-xs rounded-pill border px-md py-sm",
                          selected
                            ? "bg-brand-primary border-brand-primary"
                            : "bg-surface-card border-border-subtle",
                        ].join(" ")}
                      >
                        {selected ? (
                          <CheckCircle2 size={13} color="#fff" strokeWidth={2} />
                        ) : (
                          <ListFilter size={13} color={colors.inkMuted} strokeWidth={1.8} />
                        )}
                        <Text
                          className={
                            selected
                              ? "text-sm font-medium text-white"
                              : "text-sm text-ink-primary"
                          }
                        >
                          {opt.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>
                {error && (
                  <Text className="mt-xs text-xs text-semantic-error">{error}</Text>
                )}
              </View>,
            );

          case "boolean":
            return wrapField(
              <View className="flex-row items-center justify-between">
                <Text
                  className="text-md text-ink-primary flex-1 pr-lg"
                  numberOfLines={2}
                >
                  {field.label}
                </Text>
                <Switch
                  value={Boolean(value)}
                  onValueChange={onChange}
                  trackColor={{
                    false: colors.borderSubtle,
                    true: colors.brandPrimary,
                  }}
                  thumbColor={colors.bgCard}
                />
              </View>,
            );

          default:
            return <View />;
        }
      }}
    />
  );
}
