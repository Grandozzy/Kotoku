"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Car, Check, ChevronRight, ClipboardList, Home } from "lucide-react";
import { agreementsApi } from "@/api/agreements";
import { SCENARIOS } from "@/constants/scenarios";
import type { ComponentType } from "react";

const SCENARIO_ICON_MAP: Record<string, ComponentType<{ size?: number; className?: string; strokeWidth?: number }>> = {
  car: Car,
  home: Home,
};

type Step = "scenario" | "details";

export default function NewAgreementPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("scenario");
  const [selectedScenario, setSelectedScenario] = useState<string>("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const createMutation = useMutation({
    mutationFn: () =>
      agreementsApi.create({
        title: title.trim(),
        description: description.trim(),
        scenario_template: selectedScenario || undefined,
      }),
    onSuccess: (agreement) => {
      router.push(`/agreements/${agreement.id}/parties`);
    },
  });

  function handleScenarioNext() {
    // Auto-fill a sensible title placeholder
    if (!title && selectedScenario) {
      const s = SCENARIOS.find((s) => s.id === selectedScenario);
      if (s) setTitle(s.label);
    }
    setStep("details");
  }

  return (
    <div className="max-w-xl">
      {/* Progress */}
      <div className="flex items-center gap-2 mb-8">
        {(["scenario", "details"] as Step[]).map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-6 h-6 rounded-full text-xs flex items-center justify-center font-semibold ${
                step === s
                  ? "bg-neutral-900 text-white"
                  : i < ["scenario", "details"].indexOf(step)
                  ? "bg-emerald-500 text-white"
                  : "bg-neutral-100 text-neutral-400"
              }`}
            >
              {i < ["scenario", "details"].indexOf(step) ? <Check size={10} strokeWidth={3} /> : i + 1}
            </div>
            <span
              className={`text-sm ${step === s ? "font-medium text-neutral-900" : "text-neutral-400"}`}
            >
              {s === "scenario" ? "Choose scenario" : "Details"}
            </span>
            {i < 1 && <ChevronRight size={14} className="text-neutral-200 mx-1" strokeWidth={2} />}
          </div>
        ))}
      </div>

      {/* Step 1: Scenario */}
      {step === "scenario" && (
        <div className="flex flex-col gap-5">
          <div>
            <h1 className="text-xl font-bold tracking-tight">New agreement</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Choose the type of agreement. This sets the required evidence and roles.
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
                selectedScenario === "" && step === "scenario"
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
                  No predefined template — just title, parties, and evidence you choose.
                </p>
              </div>
            </button>
          </div>

          <button
            onClick={handleScenarioNext}
            className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-700 transition-colors w-fit"
          >
            Next <ArrowRight size={14} />
          </button>
        </div>
      )}

      {/* Step 2: Details */}
      {step === "details" && (
        <div className="flex flex-col gap-5">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Agreement details</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Give this agreement a clear title so both parties can identify it.
            </p>
          </div>

          {selectedScenario && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-neutral-50 border border-neutral-100">
              {(() => {
                const iconId = SCENARIOS.find((s) => s.id === selectedScenario)?.icon ?? "";
                const Icon = SCENARIO_ICON_MAP[iconId];
                return Icon ? (
                  <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-neutral-200 shrink-0">
                    <Icon size={16} className="text-neutral-600" strokeWidth={1.8} />
                  </span>
                ) : null;
              })()}
              <div>
                <p className="text-sm font-medium">
                  {SCENARIOS.find((s) => s.id === selectedScenario)?.label}
                </p>
                <button
                  onClick={() => setStep("scenario")}
                  className="text-xs text-neutral-400 hover:text-neutral-600 underline"
                >
                  Change
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-neutral-700">
              Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Sale of 2018 Toyota Corolla — Kwame & Abena"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={255}
              className="mt-1 w-full rounded-lg border border-neutral-200 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="mt-1 text-xs text-neutral-400">
              Use names and the subject so it&apos;s easy to find later.
            </p>
          </div>

          <div>
            <label className="text-sm font-medium text-neutral-700">
              Description{" "}
              <span className="font-normal text-neutral-400">(optional)</span>
            </label>
            <textarea
              rows={3}
              placeholder="Any additional context…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 w-full rounded-lg border border-neutral-200 px-4 py-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !title.trim()}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-neutral-900 text-white text-sm font-medium disabled:opacity-50 hover:bg-neutral-700 transition-colors"
            >
              {createMutation.isPending ? "Creating…" : (
                <><span>Create agreement</span><ArrowRight size={14} /></>
              )}
            </button>
            <button
              onClick={() => setStep("scenario")}
              className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full border border-neutral-200 text-sm font-medium hover:bg-neutral-50"
            >
              <ArrowLeft size={14} /> Back
            </button>
          </div>
          {createMutation.isError && (
            <p className="text-sm text-red-600">
              Could not create agreement. Try again.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
