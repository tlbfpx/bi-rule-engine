import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tasksApi } from '../api/tasks';
import type { TaskCreatePayload } from '../types';

export function useTasks(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: ['tasks', params],
    queryFn: () => tasksApi.list(params),
  });
}

export function useCreateTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreatePayload) => tasksApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'], exact: false }),
  });
}

export function useUploadPreview() {
  return useMutation({
    mutationFn: (file: File) => tasksApi.uploadPreview(file),
  });
}

export function useUploadExecute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => tasksApi.uploadExecute(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'], exact: false }),
  });
}

export function useTaskStatus(id: string | null) {
  return useQuery({
    queryKey: ['tasks', id, 'status'],
    queryFn: () => tasksApi.getStatus(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') return 2000;
      return false;
    },
  });
}
