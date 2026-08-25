"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Car, ClipboardList, Home } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { SCENARIOS } from "@/constants/scenarios";
import type { ComponentType } from "react";

const SCENARIO_ICON_MAP: Record<string, ComponentType<{ size?: number; className?: string; strokeWidth?: number }>> = {
  car: Car,
  home: Home,
};

export default function NewAgreementPage() {
  const router = useRouter();
  // null = nothing selected yet, "" = custom selected, string = scenarioId
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [customTitle, setCustomTitle] = useState("");

  const isCustom = selectedScenario === "";
  const canStart =
    selectedScenario !== null &&
    (!isCustom || customTitle.trim().length > 0);

  const createMutation = useMutation({
    mutationFn: () => {
      const scenario = SCENARIOS.find((s) => s.id === selectedScenario);
      const title = isCustom
        ? customTitle.trim()
        : (scenario?.label ?? "Agreement");
      return agreementsApi.create({
        title,
        scenario_template: selectedScenario || undefined,
      });
    },
    onSuccess: (agreement) => {
      router.push(`/agreements/${agreement.id}/parties`);
    },
  });

  return (
    <div className="max-w-xl">
      <div className="flex flex-col gap-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight">New agreement</h1>
          <p className="text-sm text-neutral-500 mt-1">
            Choose the type that best matches your transaction. This sets the
            required evidence and party roles.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedScenario(s.id)}
              className={`flex items-start gap-4 p-4 rounded-2xl border text-left transition-colors ${
                selectedScenario === s.id
                  ? "border-neutral-900 bg-neutral-50"
                  : "border-neutral-100 hover:border-neutral-200"
              }`}
            >
              {(() => {
                const Icon = SCENARIO_ICON_MAP[s.icon];
                return Icon ? (
                  <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-neutral-100 shrink-0">
                    <Icon size={20} className="text-neutral-600" strokeWidth={1.8} />
                  </span>
                ) : null;
              })()}
              <div>
                <p className="font-semibold text-sm">{s.label}</p>
                <p className="text-xs text-neutral-500 mt-0.5">{s.description}</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {s.evidenceRequirements.map((r) => (
                    <span
                      key={r}
                      className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-500"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              </div>
            </button>
          ))}

          {/* Custom / no template */}
          <button
            onClick={() => setSelectedScenario("")}
            className={`flex items-start gap-4 p-4 rounded-2xl border text-left transition-colors ${
              selectedScenario === ""
                ? "border-neutral-900 bg-neutral-50"
                : "border-neutral-100 hover:border-neutral-200"
            }`}
          >
            <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-neutral-100 shrink-0">
              <ClipboardList size={20} className="text-neutral-600" strokeWidth={1.8} />
            </span>
            <div>
              <p className="font-semibold text-sm">Custom agreement</p>
              <p className="text-xs text-neutral-500 mt-0.5">
                No predefined template — add parties and evidence you choose.
              </p>
            </div>
          </button>
        </div>

        {/* Custom title input — only shown when custom is selected */}
        {isCustom && (
          <div>
            <label className="text-sm font-medium text-neutral-700">
              Agreement title <span className="text-red-400">*</span>
            </label>
            <input
              autoFocus
              type="text"
              placeholder="e.g. Sale of laptop — Kwame & Abena"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              maxLength={255}
              className="form-control mt-1 px-4 py-2.5 focus:ring-emerald-500"
            />
            <p className="form-help-strong">
              Use names and the subject so both parties can identify it later.
            </p>
          </div>
        )}

        <button
          onClick={() => createMutation.mutate()}
          disabled={!canStart || createMutation.isPending}
          className="btn-primary w-fit"
        >
          {createMutation.isPending ? "Creating…" : (
            <><span>Start agreement</span><ArrowRight size={14} /></>
          )}
        </button>

        {createMutation.isError && (
          <p className="text-sm text-red-600">
            Could not create agreement. Try again.
          </p>
        )}
      </div>
    </div>
  );
}
