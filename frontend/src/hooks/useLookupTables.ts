import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { lookupTablesApi } from '../api/lookupTables';

export function useLookupTables(params?: { page?: number; page_size?: number; search?: string }) {
  return useQuery({
    queryKey: ['lookup-tables', params],
    queryFn: () => lookupTablesApi.list(params),
  });
}

export function useLookupTable(id: string | null) {
  return useQuery({
    queryKey: ['lookup-tables', id],
    queryFn: () => lookupTablesApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateLookupTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: lookupTablesApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lookup-tables'], exact: false }),
  });
}

export function useUploadLookupTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, file }: { name: string; file: File }) => lookupTablesApi.upload(name, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lookup-tables'], exact: false }),
  });
}

export function useUpdateLookupTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => lookupTablesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lookup-tables'], exact: false }),
  });
}

export function useDeleteLookupTable() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => lookupTablesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lookup-tables'], exact: false }),
  });
}
