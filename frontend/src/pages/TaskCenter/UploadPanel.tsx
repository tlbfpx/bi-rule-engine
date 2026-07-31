import { useState } from 'react';
import { Upload, Button, Table, Typography, Statistic, Row, Col, Card, App, Progress, Tag } from 'antd';
import { InboxOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useUploadPreview, useUploadExecute } from '../../hooks/useTasks';
import { useRuleEditorStore } from '../../stores/ruleStore';
import type { UploadPreviewResult, ExecuteResult } from '../../types';

const { Dragger } = Upload;

export default function UploadPanel() {
  const { message } = App.useApp();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<UploadPreviewResult | null>(null);
  const [executeResult, setExecuteResult] = useState<ExecuteResult | null>(null);

  const uploadPreview = useUploadPreview();
  const uploadExecute = useUploadExecute();
  const setDataContext = useRuleEditorStore((s) => s.setDataContext);

  const handleBeforeUpload = (f: File) => {
    const isValid = f.name.endsWith('.csv') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls');
    if (!isValid) {
      message.error('仅支持 CSV 和 Excel 文件');
      return false;
    }
    setFile(f);
    setPreview(null);
    setExecuteResult(null);

    uploadPreview.mutate(f, {
      onSuccess: (data) => {
        setPreview(data);
        // 将列画像推入全局 store，供规则编辑器使用
        if (data.column_profiles) {
          setDataContext({
            columnProfiles: data.column_profiles,
            previewRows: data.preview_rows,
            totalRows: data.total_rows,
          });
        }
      },
    });
    return false; // 阻止自动上传
  };

  const handleExecute = () => {
    if (!file) return;
    uploadExecute.mutate(file, {
      onSuccess: (data) => setExecuteResult(data),
    });
  };

  const previewColumns = preview?.columns.map((col) => ({
    title: col,
    dataIndex: col,
    key: col,
    width: 150,
    ellipsis: true,
  })) || [];

  return (
    <div>
      <Dragger
        accept=".csv,.xlsx,.xls"
        maxCount={1}
        beforeUpload={handleBeforeUpload}
        showUploadList={false}
        style={{ marginBottom: 16 }}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持 CSV 和 Excel (.xlsx/.xls) 格式</p>
      </Dragger>

      {uploadPreview.isPending && (
        <Progress percent={50} status="active" strokeColor={{ from: '#1677ff', to: '#52c41a' }} />
      )}

      {preview && (
        <Card title="数据预览" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic title="文件名" value={preview.filename} />
            </Col>
            <Col span={6}>
              <Statistic title="总行数" value={preview.total_rows.toLocaleString()} />
            </Col>
            <Col span={6}>
              <Statistic title="总列数" value={preview.total_columns} />
            </Col>
            <Col span={6}>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleExecute}
                loading={uploadExecute.isPending}
                block
                style={{ marginTop: 4 }}
              >
                执行转换
              </Button>
            </Col>
          </Row>

          {/* 空值统计 */}
          <div style={{ marginBottom: 12 }}>
            <Typography.Text strong>空值率统计：</Typography.Text>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
              {Object.entries(preview.null_stats).map(([col, stat]) => (
                <Tag key={col} color={stat.null_rate > 0.5 ? 'red' : stat.null_rate > 0.1 ? 'orange' : 'green'}>
                  {col}: {(stat.null_rate * 100).toFixed(1)}%
                </Tag>
              ))}
            </div>
          </div>

          <Table
            rowKey={(_, idx) => String(idx)}
            columns={previewColumns}
            dataSource={preview.preview_rows}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            bordered
          />
        </Card>
      )}

      {executeResult && (
        <Card title="转换结果" size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic title="输入行数" value={executeResult.input_rows.toLocaleString()} />
            </Col>
            <Col span={6}>
              <Statistic title="输出行数" value={executeResult.output_rows.toLocaleString()} />
            </Col>
            <Col span={6}>
              <Statistic title="错误行数" value={executeResult.error_rows} valueStyle={{ color: executeResult.error_rows > 0 ? '#ff4d4f' : undefined }} />
            </Col>
            <Col span={6}>
              <Statistic title="耗时" value={`${(executeResult.duration_ms / 1000).toFixed(2)}s`} />
            </Col>
          </Row>

          {executeResult.stats && Object.keys(executeResult.stats).length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <Typography.Text strong>各字段统计：</Typography.Text>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                {Object.entries(executeResult.stats).map(([field, stat]: [string, unknown]) => {
                  const s = stat as Record<string, number>;
                  return (
                    <Tag key={field} color="blue">
                      {field}: 命中 {s.matched || 0} / 默认 {s.defaulted || 0} / 错误 {s.errors || 0}
                    </Tag>
                  );
                })}
              </div>
            </div>
          )}

          <Table
            rowKey={(_, idx) => String(idx)}
            columns={executeResult.columns.map((col) => ({ title: col, dataIndex: col, key: col, width: 150, ellipsis: true }))}
            dataSource={executeResult.preview_rows}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            bordered
          />
        </Card>
      )}
    </div>
  );
}
