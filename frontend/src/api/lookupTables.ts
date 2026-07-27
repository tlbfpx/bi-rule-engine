import client from './client';
import type { PaginatedResponse, LookupTable } from '../types';

export const lookupTablesApi = {
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    client.get<PaginatedResponse<LookupTable>>('/lookup-tables', { params }).then((r) => r.data),

  get: (id: string) => client.get<LookupTable>(`/lookup-tables/${id}`).then((r) => r.data),

  create: (data: { name: string; description?: string; source_type: string; columns: Record<string, string>; data: Record<string, string> }) =>
    client.post<LookupTable>('/lookup-tables', data).then((r) => r.data),

  upload: (name: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return client.post<LookupTable>(`/lookup-tables/upload?name=${encodeURIComponent(name)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data);
  },

  update: (id: string, data: Partial<LookupTable>) =>
    client.put<LookupTable>(`/lookup-tables/${id}`, data).then((r) => r.data),

  delete: (id: string) => client.delete(`/lookup-tables/${id}`),
};
