import client from './client';
import type { PaginatedResponse, Task, TaskCreatePayload, UploadPreviewResult, ExecuteResult } from '../types';

export const tasksApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    client.get<PaginatedResponse<Task>>('/tasks', { params }).then((r) => r.data),

  create: (data: TaskCreatePayload) =>
    client.post<Task>('/tasks', data).then((r) => r.data),

  uploadPreview: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return client.post<UploadPreviewResult>('/tasks/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data);
  },

  uploadExecute: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return client.post<ExecuteResult>('/tasks/upload/execute', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data);
  },

  getStatus: (id: string) => client.get<Task>(`/tasks/${id}/status`).then((r) => r.data),
};
