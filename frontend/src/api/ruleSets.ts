import client from './client';
import type { PaginatedResponse, RuleSet } from '../types';

export const ruleSetsApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<RuleSet>>('/rule-sets', { params }).then((r) => r.data),

  all: () =>
    client.get<{ items: RuleSet[] }>('/rule-sets/all').then((r) => r.data),

  get: (id: string) =>
    client.get<RuleSet>(`/rule-sets/${id}`).then((r) => r.data),

  create: (data: { name: string; description?: string; color?: string; sort_order?: number }) =>
    client.post<RuleSet>('/rule-sets', data).then((r) => r.data),

  update: (id: string, data: Partial<RuleSet>) =>
    client.put<RuleSet>(`/rule-sets/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    client.delete(`/rule-sets/${id}`).then((r) => r.data),
};
