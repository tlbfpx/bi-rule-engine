import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ruleSetsApi } from '../api/ruleSets';

function invalidateRuleSets(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ['ruleSets'], exact: false });
}

export function useRuleSets(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['ruleSets', params],
    queryFn: () => ruleSetsApi.list(params),
  });
}

export function useAllRuleSets() {
  return useQuery({
    queryKey: ['ruleSets', 'all'],
    queryFn: () => ruleSetsApi.all(),
  });
}

export function useCreateRuleSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ruleSetsApi.create,
    onSuccess: () => invalidateRuleSets(qc),
  });
}

export function useUpdateRuleSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof ruleSetsApi.update>[1] }) =>
      ruleSetsApi.update(id, data),
    onSuccess: () => invalidateRuleSets(qc),
  });
}

export function useDeleteRuleSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ruleSetsApi.delete,
    onSuccess: () => invalidateRuleSets(qc),
  });
}
