// ============ 规则相关类型 ============

export type RuleType = 'mapping' | 'cleaning' | 'lookup' | 'computed';

export type OperatorType =
  | 'eq' | 'neq' | 'contains' | 'matches'
  | 'starts_with' | 'ends_with' | 'in' | 'between'
  | 'gt' | 'gte' | 'lt' | 'lte'
  | 'is_null' | 'is_not_null';

export interface ConditionRow {
  id: string;
  field: string;
  operator: OperatorType;
  value: unknown;
}

export interface ConditionGroup {
  id: string;
  priority: number;
  logic: 'AND' | 'OR';
  rows: ConditionRow[];
  result_type: 'constant' | 'field_value' | 'keep_original';
  result_value: unknown;
}

export interface CleaningStep {
  id: string;
  action: 'fill_null' | 'replace_string' | 'regex_extract' | 'trim' | 'case_convert';
  params: Record<string, unknown>;
}

export interface LookupFallback {
  id: string;
  condition_field: string;
  condition_operator: OperatorType;
  condition_value: unknown;
  fallback_value: unknown;
}

export interface RuleConfig {
  conditions: ConditionGroup[];
  cleaning_steps: CleaningStep[];
  lookup_table_id: string | null;
  lookup_key_field: string | null;
  lookup_value_field: string | null;
  lookup_fallbacks: LookupFallback[];
  formula_expression: string | null;
  default_result: unknown;
}

export interface Rule {
  id: string;
  rule_set_id?: string | null;
  rule_set_name?: string | null;
  field_name: string;
  field_label: string | null;
  rule_type: RuleType;
  priority: number;
  enabled: boolean;
  config: RuleConfig;
  lookup_table_id: string | null;
  depends_on: string[];
  description: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuleCreatePayload {
  rule_set_id?: string | null;
  field_name: string;
  field_label?: string;
  rule_type: RuleType;
  priority: number;
  enabled: boolean;
  config: RuleConfig;
  lookup_table_id?: string;
  depends_on?: string[];
  description?: string;
}

export interface RuleUpdatePayload {
  rule_set_id?: string | null;
  field_label?: string;
  rule_type?: RuleType;
  priority?: number;
  enabled?: boolean;
  config?: RuleConfig;
  lookup_table_id?: string | null;
  depends_on?: string[];
  description?: string;
}

export interface RuleTestRequest {
  test_rows: Record<string, unknown>[];
}

export interface RuleTestResult {
  results: {
    row_index: number;
    input_data: Record<string, unknown>;
    output_value: unknown;
    status: 'matched' | 'defaulted' | 'error';
  }[];
  summary: {
    total: number;
    matched: number;
    defaulted: number;
    errors: number;
  };
}

export interface BatchPriorityUpdate {
  items: { id: string; priority: number }[];
}

// ============ 字典表相关类型 ============

export interface LookupTable {
  id: string;
  name: string;
  description: string | null;
  source_type: 'manual' | 'upload';
  columns: { key_col: string; value_col: string };
  data: Record<string, string>;
  row_count: number;
  created_at: string;
  updated_at: string;
}

// ============ 任务相关类型 ============

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Task {
  id: string;
  task_name: string;
  source_id: string | null;
  template_id: string | null;
  query_params: Record<string, unknown>;
  executed_sql: string | null;
  status: TaskStatus;
  output_format: string;
  output_file: string | null;
  input_rows: number | null;
  output_rows: number | null;
  error_rows: number;
  stats: Record<string, unknown>;
  error_log: unknown[];
  duration_ms: number | null;
  created_by: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface TaskCreatePayload {
  task_name?: string;
  source_id?: string;
  template_id?: string;
  query_params?: Record<string, unknown>;
  output_format: string;
}

export interface ColumnProfile {
  distinct_count: number;
  top_values: { value: string | null; count: number }[];
  sample_values: string[];
  null_rate: number;
  dtype: string;
}

export interface UploadPreviewResult {
  filename: string;
  total_rows: number;
  total_columns: number;
  columns: string[];
  preview_rows: Record<string, unknown>[];
  null_stats: Record<string, { null_count: number; null_rate: number }>;
  column_profiles?: Record<string, ColumnProfile>;
}

export interface ExecuteResult {
  task_id: string;
  status: string;
  input_rows: number;
  output_rows: number;
  error_rows: number;
  stats: Record<string, unknown>;
  duration_ms: number;
  preview_rows: Record<string, unknown>[];
  columns: string[];
}

// ============ 数据源类型 ============

export type ExtractMode = 'table' | 'sql';

export interface DataSource {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  db_host: string;
  db_port: number;
  db_name: string;
  db_username: string;
  extract_mode: ExtractMode;
  extract_sql: string | null;
  extract_table: string | null;
  incremental_column: string | null;
  incremental_value: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataSourceCreatePayload {
  name: string;
  description?: string;
  enabled?: boolean;
  db_host: string;
  db_port?: number;
  db_name: string;
  db_username: string;
  db_password: string;
  extract_mode?: ExtractMode;
  extract_sql?: string;
  extract_table?: string;
  incremental_column?: string;
  incremental_value?: string;
}

export interface DataSourceUpdatePayload {
  name?: string;
  description?: string;
  enabled?: boolean;
  db_host?: string;
  db_port?: number;
  db_name?: string;
  db_username?: string;
  db_password?: string;
  extract_mode?: ExtractMode;
  extract_sql?: string;
  extract_table?: string;
  incremental_column?: string;
  incremental_value?: string;
}

export interface DataSourceTestPayload {
  db_host: string;
  db_port: number;
  db_name: string;
  db_username: string;
  db_password: string;
}

export interface DataSourcePreviewResult {
  sql: string;
  total_rows: number;
  columns: string[];
  preview_rows: Record<string, unknown>[];
  column_profiles?: Record<string, ColumnProfile>;
}

// ============ 目标表类型 ============

export type WriteMode = 'append' | 'truncate_insert' | 'upsert';

export interface TargetTable {
  id: string;
  name: string;
  description: string | null;
  enabled: boolean;
  db_host: string;
  db_port: number;
  db_name: string;
  db_username: string;
  table_name: string;
  write_mode: WriteMode;
  upsert_keys: string[];
  auto_create_table: boolean;
  created_at: string;
  updated_at: string;
}

export interface TargetTableCreatePayload {
  name: string;
  description?: string;
  enabled?: boolean;
  db_host: string;
  db_port?: number;
  db_name: string;
  db_username: string;
  db_password: string;
  table_name: string;
  write_mode?: WriteMode;
  upsert_keys?: string[];
  auto_create_table?: boolean;
}

export interface TargetTableUpdatePayload {
  name?: string;
  description?: string;
  enabled?: boolean;
  db_host?: string;
  db_port?: number;
  db_name?: string;
  db_username?: string;
  db_password?: string;
  table_name?: string;
  write_mode?: WriteMode;
  upsert_keys?: string[];
  auto_create_table?: boolean;
}

export interface TargetTableTestPayload {
  db_host: string;
  db_port: number;
  db_name: string;
  db_username: string;
  db_password: string;
  table_name: string;
  write_mode?: WriteMode;
}

// ============ ETL 调度任务类型 ============

export interface ETLJob {
  id: string;
  job_name: string;
  description: string | null;
  enabled: boolean;
  data_source_id: string;
  target_table_id: string;
  rule_set_id?: string | null;
  cron_expression: string;
  timezone: string;
  error_retry_count: number;
  timeout_seconds: number;
  last_run_at: string | null;
  last_run_status: TaskStatus | null;
  last_run_error: string | null;
  created_at: string;
  updated_at: string;
  data_source?: DataSource;
  target_table?: TargetTable;
}

export interface ETLJobCreatePayload {
  job_name: string;
  description?: string;
  enabled?: boolean;
  data_source_id: string;
  target_table_id: string;
  cron_expression: string;
  timezone?: string;
  error_retry_count?: number;
  timeout_seconds?: number;
}

export interface ETLJobUpdatePayload {
  job_name?: string;
  description?: string;
  enabled?: boolean;
  data_source_id?: string;
  target_table_id?: string;
  cron_expression?: string;
  timezone?: string;
  error_retry_count?: number;
  timeout_seconds?: number;
}

export interface ETLJobRun {
  id: string;
  etl_job_id: string;
  status: TaskStatus;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  input_rows: number | null;
  output_rows: number | null;
  error_rows: number;
  executed_sql: string | null;
  error_log: Record<string, unknown>;
  stats: Record<string, unknown>;
  created_at: string;
  etl_job?: ETLJob;
}

// ============ 规则集 ============

export interface RuleSet {
  id: string;
  name: string;
  description?: string | null;
  data_source_id?: string | null;
  color: string;
  sort_order: number;
  enabled: boolean;
  rule_count?: number;
  created_at: string;
  updated_at: string;
}

// ============ 通用类型 ============

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  detail: string;
}
