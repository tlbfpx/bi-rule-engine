import client from './client';
import type {
  PaginatedResponse,
  DataSource,
  DataSourceCreatePayload,
  DataSourceUpdatePayload,
  DataSourceTestPayload,
  DataSourcePreviewResult,
} from '../types';

export const dataSourcesApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<DataSource>>('/data-sources', { params }).then((r) => r.data),

  listAll: () =>
    client.get<{ items: { id: string; name: string; enabled: boolean }[] }>('/data-sources/all').then((r) => r.data),

  get: (id: string) => client.get<DataSource>(`/data-sources/${id}`).then((r) => r.data),

  create: (data: DataSourceCreatePayload) =>
    client.post<DataSource>('/data-sources', data).then((r) => r.data),

  update: (id: string, data: DataSourceUpdatePayload) =>
    client.put<DataSource>(`/data-sources/${id}`, data).then((r) => r.data),

  delete: (id: string) => client.delete(`/data-sources/${id}`),

  testConnection: (data: DataSourceTestPayload) =>
    client.post<{ ok: boolean }>('/data-sources/test-connection', data).then((r) => r.data),

  preview: (id: string, limit?: number) =>
    client.post<DataSourcePreviewResult>(`/data-sources/${id}/preview`, null, { params: { limit } }).then((r) => r.data),
};
