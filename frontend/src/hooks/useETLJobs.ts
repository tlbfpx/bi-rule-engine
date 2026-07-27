import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { etlJobsApi } from '../api/etlJobs';
import type { ETLJobCreatePayload, ETLJobUpdatePayload } from '../types';

export function useETLJobs(params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['etlJobs', params],
    queryFn: () => etlJobsApi.list(params),
  });
}

export function useETLJob(id: string | null) {
  return useQuery({
    queryKey: ['etlJobs', id],
    queryFn: () => etlJobsApi.get(id!),
    enabled: !!id,
  });
}

export function useCreateETLJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ETLJobCreatePayload) => etlJobsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['etlJobs'], exact: false }),
  });
}

export function useUpdateETLJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: ETLJobUpdatePayload }) =>
      etlJobsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['etlJobs'], exact: false }),
  });
}

export function useDeleteETLJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => etlJobsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['etlJobs'], exact: false }),
  });
}

export function useRunETLJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => etlJobsApi.run(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['etlJobs'], exact: false });
      qc.invalidateQueries({ queryKey: ['etlJobRuns'], exact: false });
    },
  });
}

export function useToggleETLJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      etlJobsApi.toggle(id, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['etlJobs'], exact: false }),
  });
}

export function useETLJobRuns(id: string | null, params?: { page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ['etlJobRuns', id, params],
    queryFn: () => etlJobsApi.listRuns(id!, params),
    enabled: !!id,
  });
}

export function useETLJobRun(runId: string | null) {
  return useQuery({
    queryKey: ['etlJobRuns', runId],
    queryFn: () => etlJobsApi.getRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'running' || data?.status === 'pending') return 2000;
      return false;
    },
  });
}

export function useAllETLJobRuns(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: ['etlJobRuns', 'all', params],
    queryFn: () => etlJobsApi.listAllRuns(params),
  });
}
