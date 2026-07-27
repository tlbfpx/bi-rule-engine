import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { targetTablesApi } from '../api/targetTables';
import type { TargetTableCreatePayload, TargetTableUpdatePayload } from '../types';

export function useTargetTables(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['targetTables', params],
    queryFn: () => targetTablesApi.list(params),
  });
}

export function useAllTargetTables() {
  return useQuery({
    queryKey: ['targetTables', 'all'],
    queryFn: () => targetTablesApi.listAll(),
  });
}

export function useTargetTable(id: string | null) {
  return useQuery({
    queryKey: ['targetTables', id],
    queryFn: () => targetTablesApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateTargetTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TargetTableCreatePayload) => targetTablesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targetTables'], exact: false }),
  });
}

export function useUpdateTargetTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: TargetTableUpdatePayload }) =>
      targetTablesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targetTables'], exact: false }),
  });
}

export function useDeleteTargetTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => targetTablesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targetTables'], exact: false }),
  });
}

export function useTestTargetTableConnection() {
  return useMutation({
    mutationFn: (data: Parameters<typeof targetTablesApi.testConnection>[0]) =>
      targetTablesApi.testConnection(data),
  });
}
