import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dataSourcesApi } from '../api/dataSources';
import type { DataSourceCreatePayload, DataSourceUpdatePayload } from '../types';

export function useDataSources(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['dataSources', params],
    queryFn: () => dataSourcesApi.list(params),
  });
}

export function useAllDataSources() {
  return useQuery({
    queryKey: ['dataSources', 'all'],
    queryFn: () => dataSourcesApi.listAll(),
  });
}

export function useDataSource(id: string | null) {
  return useQuery({
    queryKey: ['dataSources', id],
    queryFn: () => dataSourcesApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateDataSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: DataSourceCreatePayload) => dataSourcesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataSources'], exact: false }),
  });
}

export function useUpdateDataSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: DataSourceUpdatePayload }) =>
      dataSourcesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataSources'], exact: false }),
  });
}

export function useDeleteDataSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => dataSourcesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dataSources'], exact: false }),
  });
}

export function useTestDataSourceConnection() {
  return useMutation({
    mutationFn: (data: Parameters<typeof dataSourcesApi.testConnection>[0]) =>
      dataSourcesApi.testConnection(data),
  });
}

export function usePreviewDataSource() {
  return useMutation({
    mutationFn: ({ id, limit }: { id: string; limit?: number }) =>
      dataSourcesApi.preview(id, limit),
  });
}
