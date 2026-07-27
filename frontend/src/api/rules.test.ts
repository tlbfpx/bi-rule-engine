import { describe, it, expect, vi, beforeEach } from 'vitest';
import { rulesApi } from './rules';
import client from './client';

// Mock client
vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('rulesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('调用 GET /rules 并传递 params', async () => {
      const mockData = { items: [], total: 0, page: 1, page_size: 20 };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      const params = { page: 1, page_size: 20, field_name: 'amount' };
      const result = await rulesApi.list(params);

      expect(client.get).toHaveBeenCalledWith('/rules', { params });
      expect(result).toEqual(mockData);
    });

    it('无参数时也正常调用', async () => {
      const mockData = { items: [], total: 0, page: 1, page_size: 20 };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      await rulesApi.list();

      expect(client.get).toHaveBeenCalledWith('/rules', { params: undefined });
    });

    it('支持 rule_type 筛选参数', async () => {
      vi.mocked(client.get).mockResolvedValueOnce({ data: { items: [], total: 0, page: 1, page_size: 20 } });

      await rulesApi.list({ rule_type: 'mapping', enabled: true });

      expect(client.get).toHaveBeenCalledWith('/rules', {
        params: { rule_type: 'mapping', enabled: true },
      });
    });
  });

  describe('get', () => {
    it('调用 GET /rules/:id', async () => {
      const mockRule = { id: 'r1', field_name: 'test' };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockRule });

      const result = await rulesApi.get('r1');

      expect(client.get).toHaveBeenCalledWith('/rules/r1');
      expect(result).toEqual(mockRule);
    });
  });

  describe('create', () => {
    it('调用 POST /rules 并发送创建数据', async () => {
      const mockRule = { id: 'r1', field_name: 'amount' };
      vi.mocked(client.post).mockResolvedValueOnce({ data: mockRule });

      const payload = {
        field_name: 'amount',
        rule_type: 'mapping' as const,
        priority: 1,
        enabled: true,
        config: {
          conditions: [],
          cleaning_steps: [],
          lookup_table_id: null,
          lookup_key_field: null,
          lookup_value_field: null,
          lookup_fallbacks: [],
          formula_expression: null,
          default_result: null,
        },
      };

      const result = await rulesApi.create(payload);

      expect(client.post).toHaveBeenCalledWith('/rules', payload);
      expect(result).toEqual(mockRule);
    });
  });

  describe('update', () => {
    it('调用 PUT /rules/:id 并发送更新数据', async () => {
      const mockRule = { id: 'r1', field_name: 'amount' };
      vi.mocked(client.put).mockResolvedValueOnce({ data: mockRule });

      const payload = { field_label: '金额字段', priority: 5 };
      const result = await rulesApi.update('r1', payload);

      expect(client.put).toHaveBeenCalledWith('/rules/r1', payload);
      expect(result).toEqual(mockRule);
    });
  });

  describe('delete', () => {
    it('调用 DELETE /rules/:id', async () => {
      vi.mocked(client.delete).mockResolvedValueOnce({ data: {} });

      await rulesApi.delete('r1');

      expect(client.delete).toHaveBeenCalledWith('/rules/r1');
    });
  });

  describe('batchPriority', () => {
    it('调用 PUT /rules/batch-priority 并发送批量数据', async () => {
      vi.mocked(client.put).mockResolvedValueOnce({ data: { updated: 3 } });

      const items = [
        { id: 'r1', priority: 1 },
        { id: 'r2', priority: 2 },
        { id: 'r3', priority: 3 },
      ];

      await rulesApi.batchPriority({ items });

      expect(client.put).toHaveBeenCalledWith('/rules/batch-priority', { items });
    });
  });

  describe('test', () => {
    it('调用 POST /rules/:id/test 并发送测试数据', async () => {
      const mockResult = {
        results: [],
        summary: { total: 0, matched: 0, defaulted: 0, errors: 0 },
      };
      vi.mocked(client.post).mockResolvedValueOnce({ data: mockResult });

      const testData = { test_rows: [{ field: 'value' }] };
      const result = await rulesApi.test('r1', testData);

      expect(client.post).toHaveBeenCalledWith('/rules/r1/test', testData);
      expect(result).toEqual(mockResult);
    });
  });
});
