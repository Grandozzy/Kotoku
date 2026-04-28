export type FieldType =
  | "text"
  | "number"
  | "currency"
  | "date"
  | "select"
  | "boolean"
  | "textarea";

export interface FieldOption {
  value: string;
  label: string;
}

export interface FieldDefinition {
  type: FieldType;
  label: string;
  placeholder?: string;
  required: boolean;
  options?: FieldOption[]; // select type only
  dataPath: string;
  hint?: string;
  // Show this field only when another field equals a value
  conditionalOn?: { field: string; value: unknown };
}

export interface EvidenceSlot {
  id: string;
  label: string;
  fileType: "photo" | "voice_note";
  required: boolean;
}

export interface EvidenceRequirements {
  slots: EvidenceSlot[];
  minimumPhotoCount: number;
}

export interface DetailSection {
  title: string;
  fields: string[]; // keys into ScenarioTemplate.fields
}

export interface ScenarioTemplate {
  scenarioId: string;
  version: string;
  title: string;
  // Labels for the two main roles, e.g. ["Seller", "Buyer"]
  partyRoles: [string, string];
  detailSections: DetailSection[];
  fields: Record<string, FieldDefinition>;
  evidenceRequirements: EvidenceRequirements;
}
