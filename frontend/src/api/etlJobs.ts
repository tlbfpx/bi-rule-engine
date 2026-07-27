import client from './client';
import type {
  PaginatedResponse,
  ETLJob,
  ETLJobCreatePayload,
  ETLJobUpdatePayload,
  ETLJobRun,
} from '../types';

export const etlJobsApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<ETLJob>>('/etl-jobs', { params }).then((r) => r.data),

  get: (id: string) => client.get<ETLJob>(`/etl-jobs/${id}`).then((r) => r.data),

  create: (data: ETLJobCreatePayload) =>
    client.post<ETLJob>('/etl-jobs', data).then((r) => r.data),

  update: (id: string, data: ETLJobUpdatePayload) =>
    client.put<ETLJob>(`/etl-jobs/${id}`, data).then((r) => r.data),

  delete: (id: string) => client.delete(`/etl-jobs/${id}`),

  run: (id: string) =>
    client.post<{ run_id: string; status: string }>(`/etl-jobs/${id}/run`).then((r) => r.data),

  toggle: (id: string, enabled: boolean) =>
    client.post<ETLJob>(`/etl-jobs/${id}/toggle`, null, { params: { enabled } }).then((r) => r.data),

  listRuns: (id: string, params?: { page?: number; page_size?: number }) =>
    client.get<PaginatedResponse<ETLJobRun>>(`/etl-jobs/${id}/runs`, { params }).then((r) => r.data),

  getRun: (runId: string) =>
    client.get<ETLJobRun>(`/etl-jobs/runs/${runId}`).then((r) => r.data),

  listAllRuns: (params?: { page?: number; page_size?: number; status?: string }) =>
    client.get<PaginatedResponse<ETLJobRun>>('/etl-jobs/runs', { params }).then((r) => r.data),
};
