import client from './client';
import type {
  PaginatedResponse,
  Rule,
  RuleCreatePayload,
  RuleUpdatePayload,
  RuleTestRequest,
  RuleTestResult,
  BatchPriorityUpdate,
} from '../types';

export const rulesApi = {
  list: (params?: { page?: number; page_size?: number; field_name?: string; rule_type?: string; enabled?: boolean; rule_set_id?: string }) =>
    client.get<PaginatedResponse<Rule>>('/rules', { params }).then((r) => r.data),

  get: (id: string) => client.get<Rule>(`/rules/${id}`).then((r) => r.data),

  create: (data: RuleCreatePayload) => client.post<Rule>('/rules', data).then((r) => r.data),

  update: (id: string, data: RuleUpdatePayload) => client.put<Rule>(`/rules/${id}`, data).then((r) => r.data),

  delete: (id: string) => client.delete(`/rules/${id}`),

  batchPriority: (data: BatchPriorityUpdate) => client.put('/rules/batch-priority', data).then((r) => r.data),

  test: (id: string, data: RuleTestRequest) =>
    client.post<RuleTestResult>(`/rules/${id}/test`, data).then((r) => r.data),
};
