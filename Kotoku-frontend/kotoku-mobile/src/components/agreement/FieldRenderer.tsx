import { Controller, Control } from "react-hook-form";
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
        switch (field.type) {
          case "text":
            return (
              <TextInput
                label={field.label}
                placeholder={field.placeholder}
                hint={field.hint}
                value={value ?? ""}
                onChangeText={onChange}
                onBlur={onBlur}
                error={error}
                required={field.required}
              />
            );

          case "textarea":
            return (
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
              />
            );

          case "number":
            return (
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
              />
            );

          case "currency":
            return (
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
                <View className="flex-row items-center border border-border-subtle rounded-md bg-surface-card overflow-hidden">
                  <View className="px-md py-sm bg-surface-subtle border-r border-border-subtle">
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
              </View>
            );

          case "date":
            return (
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
              />
            );

          case "select":
            return (
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
                          "px-md py-sm rounded-pill border",
                          selected
                            ? "bg-brand-primary border-brand-primary"
                            : "bg-surface-card border-border-subtle",
                        ].join(" ")}
                      >
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
              </View>
            );

          case "boolean":
            return (
              <View className="flex-row items-center justify-between py-sm">
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
              </View>
            );

          default:
            return <View />;
        }
      }}
    />
  );
}
