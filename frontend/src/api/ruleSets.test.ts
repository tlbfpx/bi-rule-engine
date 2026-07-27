import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ruleSetsApi } from './ruleSets';
import client from './client';

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('ruleSetsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('调用 GET /rule-sets 并传递分页参数', async () => {
      const mockData = { items: [], total: 0, page: 1, page_size: 20 };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      const result = await ruleSetsApi.list({ page: 1, page_size: 20 });

      expect(client.get).toHaveBeenCalledWith('/rule-sets', { params: { page: 1, page_size: 20 } });
      expect(result).toEqual(mockData);
    });

    it('无参数时正常调用', async () => {
      vi.mocked(client.get).mockResolvedValueOnce({ data: { items: [], total: 0, page: 1, page_size: 20 } });

      await ruleSetsApi.list();

      expect(client.get).toHaveBeenCalledWith('/rule-sets', { params: undefined });
    });
  });

  describe('all', () => {
    it('调用 GET /rule-sets/all', async () => {
      const mockData = { items: [{ id: 'rs1', name: 'test' }] };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      const result = await ruleSetsApi.all();

      expect(client.get).toHaveBeenCalledWith('/rule-sets/all');
      expect(result).toEqual(mockData);
    });
  });

  describe('get', () => {
    it('调用 GET /rule-sets/:id', async () => {
      const mockRuleSet = { id: 'rs1', name: '测试' };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockRuleSet });

      const result = await ruleSetsApi.get('rs1');

      expect(client.get).toHaveBeenCalledWith('/rule-sets/rs1');
      expect(result).toEqual(mockRuleSet);
    });
  });

  describe('create', () => {
    it('调用 POST /rule-sets 并发送创建数据', async () => {
      const mockRuleSet = { id: 'rs1', name: '新业务线' };
      vi.mocked(client.post).mockResolvedValueOnce({ data: mockRuleSet });

      const payload = { name: '新业务线', description: '描述', color: '#1677ff' };
      const result = await ruleSetsApi.create(payload);

      expect(client.post).toHaveBeenCalledWith('/rule-sets', payload);
      expect(result).toEqual(mockRuleSet);
    });
  });

  describe('update', () => {
    it('调用 PUT /rule-sets/:id 并发送更新数据', async () => {
      const mockRuleSet = { id: 'rs1', name: '更新后' };
      vi.mocked(client.put).mockResolvedValueOnce({ data: mockRuleSet });

      const payload = { name: '更新后' };
      const result = await ruleSetsApi.update('rs1', payload);

      expect(client.put).toHaveBeenCalledWith('/rule-sets/rs1', payload);
      expect(result).toEqual(mockRuleSet);
    });
  });

  describe('delete', () => {
    it('调用 DELETE /rule-sets/:id', async () => {
      vi.mocked(client.delete).mockResolvedValueOnce({ data: { id: 'rs1' } });

      await ruleSetsApi.delete('rs1');

      expect(client.delete).toHaveBeenCalledWith('/rule-sets/rs1');
    });
  });
});
