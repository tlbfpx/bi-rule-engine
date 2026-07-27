import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { rulesApi } from '../api/rules';
import type { RuleCreatePayload, RuleUpdatePayload, RuleTestRequest } from '../types';

function invalidateRules(qc: ReturnType<typeof useQueryClient>) {
  // React Query v5: invalidateQueries with exact:false to match all ['rules', ...] keys
  qc.invalidateQueries({ queryKey: ['rules'], exact: false });
}

export function useRules(params?: { page?: number; page_size?: number; field_name?: string; rule_type?: string; enabled?: boolean; rule_set_id?: string }) {
  return useQuery({
    queryKey: ['rules', params],
    queryFn: () => rulesApi.list(params),
  });
}

export function useRule(id: string | null) {
  return useQuery({
    queryKey: ['rules', id],
    queryFn: () => rulesApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RuleCreatePayload) => rulesApi.create(data),
    onSuccess: () => {
      invalidateRules(qc);
      // 刷新规则集列表（rule_count 会变化）
      qc.invalidateQueries({ queryKey: ['ruleSets'], exact: false });
    },
  });
}

export function useUpdateRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RuleUpdatePayload }) => rulesApi.update(id, data),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useDeleteRule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => rulesApi.delete(id),
    onSuccess: () => {
      invalidateRules(qc);
      qc.invalidateQueries({ queryKey: ['ruleSets'], exact: false });
    },
  });
}

export function useBatchPriority() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: { id: string; priority: number }[]) => rulesApi.batchPriority({ items }),
    onSuccess: () => invalidateRules(qc),
  });
}

export function useTestRule() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RuleTestRequest }) => rulesApi.test(id, data),
  });
}
