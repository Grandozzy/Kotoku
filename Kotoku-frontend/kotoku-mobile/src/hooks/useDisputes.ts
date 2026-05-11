import { useQuery } from "@tanstack/react-query";
import { getDispute, listDisputes, listDisputesForAgreement, type Dispute } from "@/api/disputes";

export type { Dispute };

export function useDisputes(agreementId?: number) {
  return useQuery({
    queryKey: agreementId ? ["disputes", "agreement", agreementId] : ["disputes"],
    queryFn: () =>
      agreementId ? listDisputesForAgreement(agreementId) : listDisputes(),
  });
}

export function useDisputeDetail(disputeId: number) {
  return useQuery({
    queryKey: ["disputes", disputeId],
    queryFn: () => getDispute(disputeId),
  });
}
