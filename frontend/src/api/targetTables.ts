import client from './client';
import type {
  PaginatedResponse,
  TargetTable,
  TargetTableCreatePayload,
  TargetTableUpdatePayload,
  TargetTableTestPayload,
} from '../types';

export const targetTablesApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<TargetTable>>('/target-tables', { params }).then((r) => r.data),

  listAll: () =>
    client.get<{ items: { id: string; name: string; table_name: string; enabled: boolean }[] }>('/target-tables/all').then((r) => r.data),

  get: (id: string) => client.get<TargetTable>(`/target-tables/${id}`).then((r) => r.data),

  create: (data: TargetTableCreatePayload) =>
    client.post<TargetTable>('/target-tables', data).then((r) => r.data),

  update: (id: string, data: TargetTableUpdatePayload) =>
    client.put<TargetTable>(`/target-tables/${id}`, data).then((r) => r.data),

  delete: (id: string) => client.delete(`/target-tables/${id}`),

  testConnection: (data: TargetTableTestPayload) =>
    client.post<{ ok: boolean }>('/target-tables/test-connection', data).then((r) => r.data),

  syncSchema: (id: string) =>
    client.post(`/target-tables/${id}/sync-schema`).then((r) => r.data),
};
