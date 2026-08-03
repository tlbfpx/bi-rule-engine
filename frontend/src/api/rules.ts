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

  /** 导出规则集所有规则为 Excel 文件 */
  exportExcel: async (ruleSetId: string, ruleSetName?: string) => {
    const resp = await fetch(`/api/v1/rules/export?rule_set_id=${encodeURIComponent(ruleSetId)}`);
    if (!resp.ok) throw new Error('导出失败');
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rules_${ruleSetName || ruleSetId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
};
