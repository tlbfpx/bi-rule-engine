import { describe, it, expect, vi, beforeEach } from 'vitest';
import { dataSourcesApi } from './dataSources';
import client from './client';

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('dataSourcesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('调用 GET /data-sources 并传递分页参数', async () => {
      const mockData = { items: [], total: 0, page: 1, page_size: 20 };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      const result = await dataSourcesApi.list({ page: 1, page_size: 20 });

      expect(client.get).toHaveBeenCalledWith('/data-sources', { params: { page: 1, page_size: 20 } });
      expect(result).toEqual(mockData);
    });
  });

  describe('listAll', () => {
    it('调用 GET /data-sources/all', async () => {
      const mockData = { items: [{ id: 'ds1', name: '源1', enabled: true }] };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockData });

      const result = await dataSourcesApi.listAll();

      expect(client.get).toHaveBeenCalledWith('/data-sources/all');
      expect(result).toEqual(mockData);
    });
  });

  describe('get', () => {
    it('调用 GET /data-sources/:id', async () => {
      const mockDs = { id: 'ds1', name: '源1' };
      vi.mocked(client.get).mockResolvedValueOnce({ data: mockDs });

      const result = await dataSourcesApi.get('ds1');

      expect(client.get).toHaveBeenCalledWith('/data-sources/ds1');
      expect(result).toEqual(mockDs);
    });
  });

  describe('create', () => {
    it('调用 POST /data-sources 并发送创建数据', async () => {
      const mockDs = { id: 'ds1', name: '新源' };
      vi.mocked(client.post).mockResolvedValueOnce({ data: mockDs });

      const payload = {
        name: '新源',
        db_host: 'localhost',
        db_port: 3306,
        db_name: 'test_db',
        db_username: 'root',
        db_password: 'secret',
      };

      const result = await dataSourcesApi.create(payload);

      expect(client.post).toHaveBeenCalledWith('/data-sources', payload);
      expect(result).toEqual(mockDs);
    });
  });

  describe('update', () => {
    it('调用 PUT /data-sources/:id 并发送更新数据', async () => {
      const mockDs = { id: 'ds1', name: '更新后' };
      vi.mocked(client.put).mockResolvedValueOnce({ data: mockDs });

      const payload = { name: '更新后' };
      const result = await dataSourcesApi.update('ds1', payload);

      expect(client.put).toHaveBeenCalledWith('/data-sources/ds1', payload);
      expect(result).toEqual(mockDs);
    });
  });

  describe('delete', () => {
    it('调用 DELETE /data-sources/:id', async () => {
      vi.mocked(client.delete).mockResolvedValueOnce({ data: {} });

      await dataSourcesApi.delete('ds1');

      expect(client.delete).toHaveBeenCalledWith('/data-sources/ds1');
    });
  });

  describe('testConnection', () => {
    it('调用 POST /data-sources/test-connection 并发送测试数据', async () => {
      vi.mocked(client.post).mockResolvedValueOnce({ data: { ok: true } });

      const payload = {
        db_host: 'localhost',
        db_port: 3306,
        db_name: 'test_db',
        db_username: 'root',
        db_password: 'secret',
      };

      const result = await dataSourcesApi.testConnection(payload);

      expect(client.post).toHaveBeenCalledWith('/data-sources/test-connection', payload);
      expect(result).toEqual({ ok: true });
    });
  });

  describe('preview', () => {
    it('调用 POST /data-sources/:id/preview 并传递 limit 参数', async () => {
      const mockPreview = {
        sql: 'SELECT * FROM test',
        total_rows: 100,
        columns: ['id', 'name'],
        preview_rows: [],
      };
      vi.mocked(client.post).mockResolvedValueOnce({ data: mockPreview });

      const result = await dataSourcesApi.preview('ds1', 50);

      expect(client.post).toHaveBeenCalledWith('/data-sources/ds1/preview', null, { params: { limit: 50 } });
      expect(result).toEqual(mockPreview);
    });

    it('不传 limit 时 params.limit 为 undefined', async () => {
      vi.mocked(client.post).mockResolvedValueOnce({
        data: { sql: '', total_rows: 0, columns: [], preview_rows: [] },
      });

      await dataSourcesApi.preview('ds1');

      expect(client.post).toHaveBeenCalledWith('/data-sources/ds1/preview', null, { params: { limit: undefined } });
    });
  });
});
