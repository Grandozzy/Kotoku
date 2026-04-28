export const SCENARIOS = [
  {
    id: "used_vehicle_sale",
    label: "Used vehicle sale",
    shortDescription: "Record the sale of a used car or motorbike between two people.",
    helperText:
      "Use this when you are buying or selling a used vehicle privately. Kotoku helps you capture the details of the vehicle, the agreed price and payment terms, and evidence such as photos and IDs so both sides have a record of what was agreed.",
  },
  {
    id: "rental_agreement",
    label: "Room or house rental",
    shortDescription: "Record a simple rent agreement between landlord and tenant.",
    helperText:
      "Use this when you agree to rent a room, apartment, or house. Kotoku helps you record the property details, rent amount, deposit, and basic responsibilities, plus IDs and photos, so there is proof of what both sides agreed.",
  },
] as const;

export type ScenarioId = (typeof SCENARIOS)[number]["id"];
