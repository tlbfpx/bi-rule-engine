# BI Rule Engine — Python → Spring Boot 技术架构方案

> 将现有 FastAPI + Polars + APScheduler 后端迁移为 Spring Boot 3.x 工程

---

## 1. 现有 Python 架构概览

| 层 | 技术 | 核心模块 |
|---|---|---|
| Web 框架 | FastAPI (async) | 9 个 domain router + WebSocket |
| ORM | SQLAlchemy 2.0 async | Rule, RuleSet, DataSource, TargetTable, ETLJob, ETLJobRun, ExecutionTask, AuditLog, LookupTable |
| 数据处理 | Polars DataFrame | 条件映射 / 清洗 / 字典查找 / 公式计算 |
| 公式引擎 | Lark 语法解析器 → Polars Expression | IF/COALESCE/ROUND/SPLIT/CONTAINS 等 17 个函数 |
| 调度器 | APScheduler AsyncIO | cron 表达式, coalesce, max_instances |
| 加密 | cryptography AES-GCM 256 | 数据源/目标表密码加密 |
| 日志 | Loguru + contextvar | trace_id 全链路传播, 3 sink 轮转 |
| 迁移 | Alembic | 2 个版本文件 |
| 基础设施 | MySQL 8 + Redis 7 + MinIO | Docker Compose |

---

## 2. 技术选型对照表

| 维度 | Python (现有) | Spring Boot (目标) | 说明 |
|---|---|---|---|
| **语言** | Python 3.12 | Java 21 (LTS) | record / sealed / pattern matching / virtual threads |
| **框架** | FastAPI | Spring Boot 3.4 | Servlet 容器, 内嵌 Tomcat |
| **异步模型** | async/await (asyncio) | Virtual Threads (Loom) | `spring.threads.virtual.enabled=true` |
| **ORM** | SQLAlchemy 2.0 async | Spring Data JPA + Hibernate 6 | Repository 模式, Specifications 动态查询 |
| **数据访问** | SQLAlchemy text() | JdbcTemplate + NamedParameterJdbcTemplate | ETL 批量读写, 动态 SQL |
| **数据迁移** | Alembic | Flyway 10 | SQL-based, 版本化管理 |
| **数据处理** | Polars DataFrame | 自研 Row/DataSet 抽象 | 见 §4 详细设计 |
| **公式引擎** | Lark LALR 解析器 | ANTLR4 | 同文法, Transformer 模式迁移 |
| **调度** | APScheduler AsyncIO | Quartz Scheduler | cron trigger, misfire policy |
| **任务队列** | Celery (未启用) | Spring @Async + ThreadPoolTaskExecutor | 轻量异步, 无需额外 broker |
| **配置管理** | pydantic-settings | @ConfigurationProperties + application.yml | profile 隔离 |
| **校验** | Pydantic | Jakarta Bean Validation (Hibernate Validator) | @NotBlank, @Valid, @Validated |
| **加密** | cryptography AES-GCM | JCA (javax.crypto) AES-GCM | 等价算法, 密文格式兼容 |
| **日志** | Loguru + contextvar | SLF4J + Logback + MDC | trace_id 通过 MDC 传播 |
| **CORS** | FastAPI CORSMiddleware | Spring WebMvcConfigurer | addCorsMappings |
| **WebSocket** | FastAPI WebSocket | Spring WebSocket (HandlerAdapter) | TextWebSocketHandler |
| **API 文档** | FastAPI Swagger (自动) | springdoc-openapi (Swagger UI) | 注解驱动 |
| **测试** | 可运行脚本 | JUnit 5 + Spring Boot Test + Testcontainers | 集成测试用容器 |
| **构建** | pip + pyproject.toml | Maven / Gradle | 推荐 Maven |

---

## 3. 工程目录结构

```
bi-rule-engine-spring/
├── pom.xml
├── docker-compose.yml
├── src/
│   ├── main/
│   │   ├── java/com/bi/ruleengine/
│   │   │   ├── BiRuleEngineApplication.java          # @SpringBootApplication
│   │   │   │
│   │   │   ├── config/                               # 配置类
│   │   │   │   ├── AppConfig.java                    # @ConfigurationProperties
│   │   │   │   ├── DataSourceConfig.java             # HikariCP 连接池
│   │   │   │   ├── JpaConfig.java                    # JPA + EnableJpaRepositories
│   │   │   │   ├── QuartzConfig.java                 # 调度器配置
│   │   │   │   ├── WebSocketConfig.java              # WS 端点注册
│   │   │   │   ├── WebMvcConfig.java                 # CORS + 拦截器
│   │   │   │   ├── AsyncConfig.java                  # @EnableAsync + 虚拟线程
│   │   │   │   └── OpenApiConfig.java                # Swagger 配置
│   │   │   │
│   │   │   ├── controller/                           # REST 控制器
│   │   │   │   ├── RuleController.java
│   │   │   │   ├── RuleSetController.java
│   │   │   │   ├── DataSourceController.java
│   │   │   │   ├── TargetTableController.java
│   │   │   │   ├── EtlJobController.java
│   │   │   │   ├── LookupTableController.java
│   │   │   │   ├── TaskController.java
│   │   │   │   ├── LogController.java                # 前端错误上报
│   │   │   │   └── HealthController.java
│   │   │   │
│   │   │   ├── websocket/
│   │   │   │   ├── TaskProgressWebSocketHandler.java
│   │   │   │   └── WebSocketSessionManager.java
│   │   │   │
│   │   │   ├── service/                              # 业务服务层
│   │   │   │   ├── RuleService.java
│   │   │   │   ├── RuleSetService.java
│   │   │   │   ├── DataSourceService.java
│   │   │   │   ├── TargetTableService.java
│   │   │   │   ├── EtlJobService.java
│   │   │   │   ├── LookupTableService.java
│   │   │   │   ├── SchedulerService.java             # Quartz 管理
│   │   │   │   └── AuditLogService.java
│   │   │   │
│   │   │   ├── entity/                               # JPA 实体
│   │   │   │   ├── Rule.java
│   │   │   │   ├── RuleSet.java
│   │   │   │   ├── DataSource.java                   # @Convert(PasswordConverter)
│   │   │   │   ├── TargetTable.java
│   │   │   │   ├── EtlJob.java
│   │   │   │   ├── EtlJobRun.java
│   │   │   │   ├── LookupTable.java
│   │   │   │   ├── ExecutionTask.java
│   │   │   │   └── AuditLog.java
│   │   │   │
│   │   │   ├── repository/                           # Spring Data JPA
│   │   │   │   ├── RuleRepository.java
│   │   │   │   ├── RuleSetRepository.java
│   │   │   │   ├── DataSourceRepository.java
│   │   │   │   ├── TargetTableRepository.java
│   │   │   │   ├── EtlJobRepository.java
│   │   │   │   ├── EtlJobRunRepository.java
│   │   │   │   └── LookupTableRepository.java
│   │   │   │
│   │   │   ├── dto/                                  # 请求/响应 DTO
│   │   │   │   ├── request/
│   │   │   │   └── response/
│   │   │   │
│   │   │   ├── converter/                            # JPA AttributeConverter
│   │   │   │   └── PasswordConverter.java            # AES-GCM 加解密
│   │   │   │
│   │   │   ├── engine/                               # ★ 核心引擎 (纯 Java, 无 Spring 依赖)
│   │   │   │   ├── model/                            # 引擎内部数据模型
│   │   │   │   │   ├── RuleConfig.java               # record
│   │   │   │   │   ├── ConditionGroup.java           # record
│   │   │   │   │   ├── ConditionRow.java             # record
│   │   │   │   │   └── RuleExecutionStats.java
│   │   │   │   ├── parser/
│   │   │   │   │   └── RuleParser.java               # JSON → RuleConfig
│   │   │   │   ├── executor/
│   │   │   │   │   ├── RuleExecutor.java             # 按层级执行
│   │   │   │   │   ├── MappingStrategy.java          # 条件映射
│   │   │   │   │   ├── CleaningStrategy.java         # 数据清洗
│   │   │   │   │   ├── LookupStrategy.java           # 字典查找
│   │   │   │   │   └── ComputedStrategy.java         # 公式计算
│   │   │   │   ├── formula/                          # ★ ANTLR4 公式引擎
│   │   │   │   │   ├── Formula.g4                    # ANTLR 文法文件
│   │   │   │   │   ├── FormulaEvaluator.java         # 入口 API
│   │   │   │   │   ├── FormulaVisitor.java           # AST → 值计算
│   │   │   │   │   └── Functions.java                # IF/COALESCE/ROUND/...
│   │   │   │   ├── dependency/
│   │   │   │   │   └── TopologicalSorter.java        # Kahn's algorithm
│   │   │   │   ├── dataset/                          # ★ 替代 Polars DataFrame
│   │   │   │   │   ├── Row.java                      # LinkedHashMap<String, Object>
│   │   │   │   │   ├── DataSet.java                  # List<Row> + 列操作
│   │   │   │   │   └── ColumnType.java               # 类型推断
│   │   │   │   └── etl/
│   │   │   │       ├── EtlRunner.java                # 抽取→转换→加载
│   │   │   │       ├── Extractor.java                # JDBC 读取
│   │   │   │       ├── Loader.java                   # JDBC 批量写入
│   │   │   │       └── SafeIdentifier.java           # SQL 注入防护
│   │   │   │
│   │   │   ├── scheduler/                            # Quartz 调度
│   │   │   │   ├── EtlJobQuartzListener.java         # ApplicationListener
│   │   │   │   └── EtlJobTrigger.java                # JobDetail + Trigger
│   │   │   │
│   │   │   ├── filter/                               # Servlet Filter
│   │   │   │   ├── TraceIdFilter.java                # MDC trace_id
│   │   │   │   └── SecurityHeadersFilter.java
│   │   │   │
│   │   │   ├── exception/                            # 全局异常
│   │   │   │   ├── GlobalExceptionHandler.java       # @ControllerAdvice
│   │   │   │   ├── BusinessException.java            # 400
│   │   │   │   └── CyclicDependencyException.java
│   │   │   │
│   │   │   └── util/
│   │   │       ├── CryptoUtils.java                  # AES-GCM
│   │   │       └── ExportUtils.java                  # CSV/Excel 导出
│   │   │
│   │   └── resources/
│   │       ├── application.yml                       # 主配置
│   │       ├── application-dev.yml                   # 开发环境
│   │       ├── application-prod.yml                  # 生产环境
│   │       ├── logback-spring.xml                    # 日志配置
│   │       └── db/migration/                         # Flyway
│   │           ├── V1__initial_schema.sql
│   │           └── V2__add_dts_tables.sql
│   │
│   └── test/
│       └── java/com/bi/ruleengine/
│           ├── engine/
│           │   ├── FormulaEvaluatorTest.java
│           │   ├── RuleExecutorTest.java
│           │   └── TopologicalSorterTest.java
│           ├── controller/
│           │   └── RuleControllerTest.java
│           └── service/
│               └── EtlJobServiceTest.java
```

---

## 4. 核心难点迁移设计

### 4.1 Polars DataFrame → 自研 DataSet 抽象

当前 Python 使用 Polars DataFrame 进行向量化数据操作。Java 生态没有等价的轻量 DataFrame 库（Tablesaw 功能不全，Spark 过重）。设计方案：

**核心思路：用 `List<Row>` + 逐行操作替代向量化操作**

```java
// Row — 一行数据的抽象
public class Row {
    private final Map<String, Object> values;

    public Object get(String field) { return values.get(field); }
    public void put(String field, Object value) { values.put(field, value); }
    public String getAsString(String field) { ... }
    public Double getAsDouble(String field) { ... }
    public boolean isNull(String field) { ... }
}

// DataSet — 数据集抽象 (替代 pl.DataFrame)
public class DataSet {
    private final List<Row> rows;
    private final List<String> columns;
    private final Map<String, ColumnType> columnTypes;

    // 条件过滤 (替代 pl.when().then().otherwise())
    public DataSet filter(Predicate<Row> predicate) { ... }

    // 列操作 (替代 pl.col().cast() 等)
    public void setColumn(String name, Function<Row, Object> mapper) { ... }

    // 添加列
    public void addColumn(String name, Object defaultValue) { ... }

    // 聚合
    public DataSet groupBy(String... keys) { ... }
}
```

**性能考量**：
- 当前 ETL 批量大小为 10000 行/批，最大 200 万行
- 逐行 Java 操作对 1-2 万行/批完全可行（毫秒级）
- 对于 200 万行上限，需流式处理：按批读取 → 按批转换 → 按批写入，不全量加载
- 如果后续性能不足，可引入 Apache Arrow / DuckDB JNI 作为加速选项

### 4.2 Lark 公式引擎 → ANTLR4

当前 Python 使用 Lark 定义 DSL 文法，Transformer 将 AST 转为 Polars Expression。迁移方案：

**ANTLR4 文法文件 (Formula.g4)** — 直接移植 Lark 文法：

```antlr
grammar Formula;

formula : expr ;

expr    : logic_or ;
logic_or : logic_and (OR logic_and)* ;
logic_and : logic_not (AND logic_not)* ;
logic_not : NOT logic_not | comparison ;
comparison : arith (EQ_OP | NEQ_OP | GT_OP | GTE_OP | LT_OP | LTE_OP) arith
           | arith IN '(' args ')'
           | arith IS NOT? NULL ;
arith   : term (('+' | '-') term)* ;
term    : factor (('*' | '/') factor)* ;
factor  : '-' factor | atom ;
atom    : NAME '(' args? ')'    # func
        | NAME                   # column
        | NUMBER                 # number
        | STRING                 # string
        | TRUE                   # true
        | FALSE                  # false
        | NULL                   # null
        | '(' expr ')'           # paren ;

args    : expr (',' expr)* ;

OR : [Oo][Rr] ; AND : [Aa][Nn][Dd] ; NOT : [Nn][Oo][Tt] ;
IN : [Ii][Nn] ; IS : [Ii][Ss] ; NULL : [Nn][Uu][Ll][Ll] ;
TRUE : [Tt][Rr][Uu][Ee] ; FALSE : [Ff][Aa][Ll][Ss][Ee] ;
EQ_OP : '=' ; NEQ_OP : '!=' ; GT_OP : '>' ; GTE_OP : '>=' ;
LT_OP : '<' ; LTE_OP : '<=' ;
NAME : [a-zA-Z_] [a-zA-Z0-9_]* ;
NUMBER : [0-9]+ ('.' [0-9]+)? ([eE] [+-]? [0-9]+)? ;
STRING : '\'' (~'\'' | '\\'.)* '\'' ;
WS : [ \t\r\n]+ -> skip ;
```

**Visitor 模式求值** — 替代 Lark Transformer，直接对 Row 求值（不再生成中间表达式）：

```java
public class FormulaVisitor extends FormulaBaseVisitor<Object> {
    private final Row row;

    public Object visitColumn(FormulaParser.ColumnContext ctx) {
        return row.get(ctx.NAME().getText());
    }

    public Object visitFunc(FormulaParser.FuncContext ctx) {
        String name = ctx.NAME().getText().toUpperCase();
        List<Object> args = evaluateArgs(ctx.args());
        return Functions.invoke(name, args);
    }
    // ... 其他 visit 方法
}
```

**关键差异**：Python 版本将公式编译为 Polars Expression（向量化），Java 版本改为逐行求值。对于公式计算场景，逐行计算完全可接受（公式通常只涉及算术和字符串操作）。

### 4.3 APScheduler → Quartz

| APScheduler 概念 | Quartz 对应 |
|---|---|
| AsyncIOScheduler | Scheduler (Spring 自动配置) |
| CronTrigger | CronTrigger (quartz CronExpression) |
| job_defaults.coalesce | @DisallowConcurrentExecution |
| job_defaults.max_instances | SchedulerFactory threadCount |
| misfire_grace_time | trigger.misfireInstruction |

**cron 表达式差异**：APScheduler 用 5 字段 (min hour day month day_of_week)，Quartz 用 6 字段 (sec min hour day month day_of_week)。迁移时需在前面补 `0`。

### 4.4 AES-GCM 加密兼容

Python 端密文格式：`aes256gcm:{base64(nonce[12] + ciphertext)}`

Java 端保持完全相同的密文格式：

```java
public class CryptoUtils {
    private static final String PREFIX = "aes256gcm:";
    private final SecretKey key;  // SHA-256(ENCRYPTION_KEY) → AES-256

    public String encrypt(String plaintext) {
        byte[] nonce = new byte[12];
        new SecureRandom().nextBytes(nonce);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key,
            new GCMParameterSpec(128, nonce));
        byte[] ct = cipher.doFinal(plaintext.getBytes(UTF_8));
        // nonce(12) + ciphertext → base64
        byte[] combined = new byte[12 + ct.length];
        System.arraycopy(nonce, 0, combined, 0, 12);
        System.arraycopy(ct, 0, combined, 12, ct.length);
        return PREFIX + Base64.getEncoder().encodeToString(combined);
    }
    // decrypt: 反向操作, 读取前 12 字节为 nonce
}
```

**兼容性**：Java 加密的密文可以被 Python 解密，反之亦然（相同算法 + 相同密钥 + 相同格式）。

### 4.5 TraceId 链路追踪

| Python | Spring Boot |
|---|---|
| contextvar 存 trace_id | MDC (Mapped Diagnostic Context) |
| TraceMiddleware 注入 | OncePerRequestFilter |
| 响应头 X-Trace-Id | HttpServletResponse.setHeader |

```java
@Component
public class TraceIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req,
            HttpServletResponse resp, FilterChain chain) {
        String traceId = req.getHeader("X-Trace-Id");
        if (traceId == null || traceId.isBlank()) {
            traceId = UUID.randomUUID().toString().replace("-", "");
        }
        MDC.put("trace_id", traceId);
        resp.setHeader("X-Trace-Id", traceId);
        try {
            chain.doFilter(req, resp);
        } finally {
            MDC.clear();
        }
    }
}
```

logback-spring.xml 中用 `%X{trace_id}` 引用 MDC 值。

---

## 5. 数据库迁移

### 5.1 Alembic → Flyway

现有 Alembic 两个版本：
- `dd33dfdbc598_initial_schema.py` — 初始 schema
- `91d3e8135c84_add_dts_tables.py` — DTS 表

迁移为 Flyway SQL 脚本：
```
db/migration/
├── V1__initial_schema.sql      # 从 Alembic 版本 1 提取 DDL
└── V2__add_dts_tables.sql      # 从 Alembic 版本 2 提取 DDL
```

**策略**：直接使用已有 SQL 备份文件 (`bi_rule_engine_backup_20260727.sql`) 中的 DDL，不通过 Alembic Python 迁移逻辑。

### 5.2 实体映射

| Python Model | JPA Entity | 主键策略 | 特殊处理 |
|---|---|---|---|
| Rule | @Entity Rule | UUID String | config 字段用 `@Convert(JsonConverter)` |
| RuleSet | @Entity RuleSet | UUID String | |
| DataSource | @Entity DataSource | UUID String | db_password 用 `@Convert(PasswordConverter)` |
| TargetTable | @Entity TargetTable | UUID String | 同上 |
| ETLJob | @Entity EtlJob | UUID String | @ManyToOne fetch LAZY |
| ETLJobRun | @Entity EtlJobRun | UUID String | |
| LookupTable | @Entity LookupTable | UUID String | data 字段 JSON |
| ExecutionTask | @Entity ExecutionTask | UUID String | |
| AuditLog | @Entity AuditLog | UUID String | |

**UUID 策略**：Python 端用 `uuid.uuid4()` 生成，Java 端用 `UUID.randomUUID().toString()` — 生成方式等价。

**JSON 字段**：MySQL JSON 列 → Hibernate `@JdbcTypeCode(SqlTypes.JSON)` 或自定义 AttributeConverter。

---

## 6. API 路由映射

| FastAPI Router | Spring Controller | 路径前缀 |
|---|---|---|
| rules.router | RuleController | /api/v1/rules |
| rule_sets.router | RuleSetController | /api/v1/rule-sets |
| lookup_tables.router | LookupTableController | /api/v1/lookup-tables |
| tasks.router | TaskController | /api/v1/tasks |
| data_sources.router | DataSourceController | /api/v1/data-sources |
| target_tables.router | TargetTableController | /api/v1/target-tables |
| etl_jobs.router | EtlJobController | /api/v1/etl-jobs |
| logs.router | LogController | /api/v1/logs |
| ws.router | WebSocketHandler | /ws/tasks/{taskId}/progress |
| (health) | HealthController | /api/health |

前端不需要任何改动 — API 路径和响应格式完全保持一致。

---

## 7. 关键设计决策

### 7.1 为什么不用 Spring WebFlux (Reactive)？

| 维度 | WebFlux (Reactive) | WebMVC + Virtual Threads |
|---|---|---|
| 异步模型 | Reactor Mono/Flux | Loom 虚拟线程 |
| 学习成本 | 高（响应式编程范式） | 低（同步代码风格） |
| JPA 兼容 | 不兼容（需 R2DBC） | 完全兼容 |
| 调试难度 | 高（栈追踪不直观） | 低 |
| 性能 | 高并发下优 | 虚拟线程下接近 Reactive |

**决策**：用 WebMVC + Virtual Threads。原因：
1. JPA (Hibernate) 是阻塞的，用 Reactive 会被 JPA 阻塞线程
2. 虚拟线程在 Java 21 已 GA，可处理万级并发
3. 团队不需要学响应式编程

### 7.2 为什么不用 Apache Spark 做数据处理？

- 当前 ETL 最大 200 万行，单机内存足够
- Spark 启动开销 ~10s，对于交互式 API 调用不可接受
- Spark 依赖 JVM + Scala 运行时，运维复杂度高
- 自研 DataSet 抽象 + JDBC 流式读写完全满足需求

### 7.3 为什么选 Quartz 而不是 Spring Scheduling？

| 维度 | Spring @Scheduled | Quartz |
|---|---|---|
| cron 动态注册 | 不支持（编译期固定） | 支持 scheduler.scheduleJob() |
| 持久化 | 无 | JDBC JobStore |
| misfire 策略 | 无 | 可配置 |
| 集群支持 | 无 | 支持 |

**决策**：用 Quartz。ETL 调度需要运行时动态增删任务（API 创建 ETL Job → 注册到调度器），Spring @Scheduled 做不到。

### 7.4 为什么选 Maven 而不是 Gradle？

- ANTLR4 Maven 插件成熟稳定
- Spring Boot 官方 Maven 插件功能完整
- 团队通常对 Maven 更熟悉
- 如果团队偏好 Gradle，方案同样适用（换 `build.gradle.kts`）

---

## 8. 迁移阶段规划

### Phase 1: 骨架搭建 (基础设施层)
- Spring Boot 项目初始化 + Maven 配置
- HikariCP 连接池 + JPA 实体定义
- Flyway 迁移脚本 (从 SQL 备份提取)
- application.yml 多环境配置
- Logback 日志 + TraceIdFilter
- GlobalExceptionHandler
- Docker Compose 更新 (替换 api service)

### Phase 2: CRUD API 层
- 所有 Repository + Service + Controller
- Bean Validation DTO
- springdoc-openapi Swagger 文档
- WebSocket Handler
- 前端对接验证 (API 契约一致)

### Phase 3: 核心引擎迁移
- RuleParser (JSON → RuleConfig)
- TopologicalSorter (Kahn's algorithm)
- RuleExecutor (4 种策略: mapping/cleaning/lookup/computed)
- DataSet / Row 抽象
- SafeIdentifier (SQL 注入防护)
- EtlRunner (Extractor → Transformer → Loader)
- CryptoUtils (AES-GCM, 兼容 Python 密文格式)

### Phase 4: 公式引擎迁移
- ANTLR4 文法定义 (Formula.g4)
- FormulaVisitor 求值器
- 17 个内置函数实现
- 单元测试: 对比 Python 版本输出

### Phase 5: 调度器集成
- Quartz 配置 + 动态任务注册
- EtlJobTrigger (QuartzJobBean)
- 应用启动时加载已启用的 ETL Job
- misfire 策略配置

### Phase 6: 测试 + 切换
- 单元测试: 引擎核心 (对比 Python 输出)
- 集成测试: Testcontainers (MySQL + Redis)
- E2E 测试: 复用前端 Playwright 用例
- 数据迁移: 共用同一 MySQL (元数据不迁移)
- 灰度切换: Nginx upstream 切换

---

## 9. 风险评估

| 风险 | 等级 | 影响 | 缓解措施 |
|---|---|---|---|
| **Polars 向量化 → Java 逐行操作性能下降** | 高 | 大数据量 ETL 变慢 | 流式批处理 (1万行/批), 必要时引入 DuckDB JNI |
| **公式 DSL 语义偏差** | 中 | 规则计算结果不一致 | 编写 Python/Java 双端对照测试 (同输入同输出) |
| **Quartz cron 5→6 字段转换** | 低 | 调度时间错误 | 自动补 `0` 秒位 + 单元测试验证 |
| **AES-GCM 跨语言兼容** | 中 | 数据源密码无法解密 | 提前编写跨语言加解密验证测试 |
| **JSON 字段类型映射** | 中 | Hibernate JSON 支持可能不一致 | 用自定义 AttributeConverter + Jackson |
| **前端 API 契约一致性** | 中 | 前端功能异常 | 逐接口对比 OpenAPI spec, 复用 Playwright E2E |
| **异步任务行为差异** | 低 | ETL 执行上下文丢失 | Virtual Threads + MDC 上下文传播 (InheritableThreadLocal) |
| **数据库连接池配置差异** | 低 | 连接泄漏或超时 | HikariCP 默认值已优化, 显式配置 leakDetectionThreshold |

---

## 10. pom.xml 核心依赖清单

```xml
<dependencies>
    <!-- Spring Boot -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-websocket</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-quartz</artifactId>
    </dependency>

    <!-- Database -->
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
    </dependency>
    <dependency>
        <groupId>org.flywaydb</groupId>
        <artifactId>flyway-mysql</artifactId>
    </dependency>
    <dependency>
        <groupId>com.zaxxer</groupId>
        <artifactId>HikariCP</artifactId>
    </dependency>

    <!-- Formula Engine -->
    <dependency>
        <groupId>org.antlr</groupId>
        <artifactId>antlr4-runtime</artifactId>
        <version>4.13.1</version>
    </dependency>

    <!-- JSON -->
    <dependency>
        <groupId>com.fasterxml.jackson.core</groupId>
        <artifactId>jackson-databind</artifactId>
    </dependency>

    <!-- API Docs -->
    <dependency>
        <groupId>org.springdoc</groupId>
        <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
        <version>2.6.0</version>
    </dependency>

    <!-- Lombok (可选) -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- Test -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>mysql</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.testcontainers</groupId>
        <artifactId>junit-jupiter</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

---

## 11. application.yml 核心配置

```yaml
spring:
  application:
    name: bi-rule-engine

  threads:
    virtual:
      enabled: true                    # Java 21 虚拟线程

  datasource:
    url: jdbc:mysql://${DB_HOST:localhost}:${DB_PORT:3306}/${DB_NAME:bi_rule_engine}?charset=utf8mb4&useSSL=false&serverTimezone=Asia/Shanghai
    username: ${DB_USER:bi_rule}
    password: ${DB_PASSWORD:bi_rule_pass}
    hikari:
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      leak-detection-threshold: 60000

  jpa:
    hibernate:
      ddl-auto: none                   # Flyway 管理 schema
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQLDialect
        format_sql: false

  flyway:
    enabled: true
    locations: classpath:db/migration
    baseline-on-migrate: true

  quartz:
    job-store-type: memory             # 初期内存, 后续可切 JDBC
    properties:
      org.quartz.threadPool.threadCount: 3
      org.quartz.scheduler.instanceName: bi-rule-engine-scheduler

  jackson:
    default-property-inclusion: non_null
    serialization:
      write-dates-as-timestamps: false

app:
  encryption-key: ${ENCRYPTION_KEY:change-me-32-bytes-key-here!!}
  etl:
    batch-size: 10000
    max-query-rows: 2000000
    query-timeout-seconds: 600
  scheduler:
    timezone: Asia/Shanghai
    coalesce: true
    max-instances: 3
  cors:
    origins: "*"
  audit-log-enabled: false
  frontend-error-log-enabled: true

logging:
  level:
    root: ${LOG_LEVEL:INFO}
    com.bi.ruleengine: DEBUG
  pattern:
    console: "%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level [%X{trace_id}] %logger{36} - %msg%n"
```

---

## 12. 总结

本次迁移的核心挑战不在 Web 层（FastAPI → Spring MVC 是直接映射），而在于：

1. **Polars DataFrame → 自研 DataSet**：从向量化操作降级为逐行操作，需用流式批处理保证性能
2. **Lark 公式引擎 → ANTLR4**：文法直接移植，但求值方式从"编译为表达式"变为"逐行求值"
3. **AES-GCM 跨语言兼容**：密文格式和密钥派生方式必须严格一致
4. **Quartz 调度动态注册**：需要在运行时增删 cron 任务

前端完全不需要改动 — API 路径、响应格式、WebSocket 端点全部保持一致。数据库 schema 不需要迁移 — Flyway 直接使用已有 DDL。
