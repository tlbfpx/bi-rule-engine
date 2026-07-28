"""增强版公式计算引擎 — 类 Excel DSL → Polars 表达式编译器

支持的语法：
- IF(condition, true_val, false_val) → pl.when(cond).then(true).otherwise(false)
- COALESCE(val1, val2, ...) → pl.coalesce([val1, val2, ...])
- ROUND(val, decimals) → val.round(decimals)
- SPLIT(str, delimiter, index) → str.cast(Utf8).str.split(delimiter).list.get(index-1)
- ABS(val) → val.abs()
- CEIL(val) → val.ceil()
- FLOOR(val) → val.floor()
- UPPER(str) → str.cast(Utf8).str.to_uppercase()
- LOWER(str) → str.cast(Utf8).str.to_lowercase()
- TRIM(str) → str.cast(Utf8).str.strip_chars()
- LENGTH(str) → str.cast(Utf8).str.len_chars()
- REPLACE(str, old, new) → str.cast(Utf8).str.replace(old, new)
- SUBSTR(str, start, length) → str.cast(Utf8).str.slice(start, length)
- CONTAINS(str, substr) → str.cast(Utf8).str.contains(substr, literal=True)
- 列引用: col_name → pl.col("col_name")
- 算术: + - * / > < >= <= == !=
- 逻辑: AND → &, OR → |
- 字面量: 数字, '字符串', True/False, None
"""
import re
import io
import tokenize
import polars as pl
from loguru import logger


# 比较运算符（DSL `=` 已在预处理中转为 `==`）
_CMP_OPS = {'==', '!=', '>=', '<=', '>', '<'}
_OPEN_BRACKETS = {'(', '['}
_CLOSE_BRACKETS = {')', ']'}


def wrap_comparisons(expr: str) -> str:
    """给每个比较子表达式 (a == b / a > b / ...) 加括号。

    DSL 把 AND/OR → &/|、`=` → `==`，但 Python 中 `&`/`|` 优先级高于比较运算符，
    导致 ``A AND B = C`` 被解析为 ``(A & B) == C``（bitand str 报错或语义错误）。
    在 eval 前把每个比较子式括起来即可修正优先级，对任意深度（含 IF 参数内）生效。

    用 tokenize 做括号/字符串感知的词法扫描，鲁棒且不依赖正则。
    """
    try:
        meaningful = [
            t for t in tokenize.generate_tokens(io.StringIO(expr).readline)
            if t.type not in (
                tokenize.NEWLINE, tokenize.NL, tokenize.COMMENT,
                tokenize.ENCODING, tokenize.ENDMARKER,
                tokenize.INDENT, tokenize.DEDENT,
            )
        ]
    except tokenize.TokenizeError:
        return expr  # 无法分词则原样返回，交给 eval 报原错误

    wraps = []  # (start_offset, end_offset)
    for k, tok in enumerate(meaningful):
        if tok.type == tokenize.OP and tok.string in _CMP_OPS:
            li = _operand_lhs(meaningful, k)
            ri = _operand_rhs(meaningful, k)
            if li is None or ri is None:
                continue
            wraps.append((meaningful[li].start[1], meaningful[ri].end[1]))

    if not wraps:
        return expr

    # 去重重叠（比较不应重叠；保险）
    wraps.sort()
    dedup = []
    last_end = -1
    for s, e in wraps:
        if s >= last_end:
            dedup.append((s, e))
            last_end = e

    # 收集插入点（左括号在 start，右括号在 end），从右往左应用
    inserts = []
    for s, e in dedup:
        inserts.append((s, '('))
        inserts.append((e, ')'))
    out = expr
    for off, ch in sorted(inserts, key=lambda x: -x[0]):
        out = out[:off] + ch + out[off:]
    return out


def _operand_lhs(toks, k):
    """从比较运算符 toks[k] 向左扫描，返回左操作数最左 token 的 index。"""
    depth = 0
    i = k - 1
    while i >= 0:
        t = toks[i]
        if t.type == tokenize.OP:
            s = t.string
            if s in _CLOSE_BRACKETS:
                depth += 1
            elif s in _OPEN_BRACKETS:
                if depth == 0:
                    return i + 1
                depth -= 1
            elif depth == 0 and (s in _CMP_OPS or s in ('&', '|', ',')):
                return i + 1
        i -= 1
    return 0


def _operand_rhs(toks, k):
    """从比较运算符 toks[k] 向右扫描，返回右操作数最右 token 的 index。"""
    depth = 0
    i = k + 1
    n = len(toks)
    while i < n:
        t = toks[i]
        if t.type == tokenize.OP:
            s = t.string
            if s in _OPEN_BRACKETS:
                depth += 1
            elif s in _CLOSE_BRACKETS:
                if depth == 0:
                    return i - 1
                depth -= 1
            elif depth == 0 and (s in _CMP_OPS or s in ('&', '|', ',')):
                return i - 1
        i += 1
    return n - 1


def compile_formula(formula: str, columns: list[str]) -> pl.Expr:
    """将 DSL 公式编译为 Polars Expression"""

    # ─── Step 0: 预处理 ───────────────────────────────────
    expr = formula.strip()

    # 0a: 先把 col IN (a, b) 替换为 col.is_in([a, b])
    # 匹配模式: 标识符 IN (值列表)
    expr = re.sub(
        r'\b(\w+)\s+IN\s*\(([^)]+)\)',
        r'\1.IS_IN([\2])',
        expr,
        flags=re.IGNORECASE
    )

    # 0a2: IS NOT NULL → .is_not_null(), IS NULL → .is_null()
    expr = re.sub(r'\bIS\s+NOT\s+NULL\b', '.IS_NOT_NULL()', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bIS\s+NULL\b', '.IS_NULL()', expr, flags=re.IGNORECASE)

    # 0b: 将列���引用替换为 pl.col("col_name")
    for col in sorted(columns, key=len, reverse=True):
        # 替换独立的列名标识符
        # 列名后可以跟: 空格、运算符、逗号、右括号、.IS_IN
        expr = re.sub(
            rf'(?<![.\"\w])({re.escape(col)})(?=\s*\.IS_IN|\s*\.IS_NOT_NULL|\s*\.IS_NULL|\s*[+\-*/><=!&|,)]|$)',
            rf'pl.col("{col}")',
            expr
        )

    # 0c: 把 .IS_IN 替换为 .is_in（Polars 原生方法）
    expr = expr.replace('.IS_IN(', '.is_in(')
    # .IS_NOT_NULL() → .is_not_null(), .IS_NULL() → .is_null()
    expr = expr.replace('.IS_NOT_NULL()', '.is_not_null()')
    expr = expr.replace('.IS_NULL()', '.is_null()')

    # 将 AND / OR 替换为 & / |（只在顶级/条件中使用）
    expr = re.sub(r'\bAND\b', '&', expr, flags=re.IGNORECASE)
    expr = re.sub(r'\bOR\b', '|', expr, flags=re.IGNORECASE)

    # ─── Step 1: 注册函数映射 ────────────────────────────
    # 将 DSL 函数转换为 Python 可调用的 lambda
    # 关键：所有函数必须返回 Polars Expression 或可链式调用的对象

    def _col(name: str) -> pl.Expr:
        return pl.col(name)

    def _when(cond, true_val, false_val=None):
        """IF(cond, true, false) → pl.when(cond).then(true).otherwise(false)"""
        # 确保非 Polars Expression 的值被包装为 pl.lit
        if not isinstance(true_val, pl.Expr):
            true_val = pl.lit(true_val)
        result = pl.when(cond).then(true_val)
        if false_val is not None:
            if not isinstance(false_val, pl.Expr):
                false_val = pl.lit(false_val)
            result = result.otherwise(false_val)
        return result

    def _coalesce(*args):
        """COALESCE(v1, v2, ...) → 链式 fill_null"""
        result = args[0] if args else pl.lit(None)
        for a in args[1:]:
            if isinstance(result, pl.Expr):
                result = result.fill_null(a)
            elif result is None:
                result = a
        return result if isinstance(result, pl.Expr) else pl.lit(result)

    def _round(val, decimals=2):
        if not isinstance(val, pl.Expr):
            return round(float(val), decimals) if val is not None else None
        # 数字字面量：直接 Python round
        return val.round(decimals)

    def _abs(val):
        if not isinstance(val, pl.Expr):
            return abs(float(val)) if val is not None else None
        return val.abs()

    def _ceil(val):
        if not isinstance(val, pl.Expr):
            import math; return math.ceil(float(val)) if val is not None else None
        return val.ceil()

    def _floor(val):
        if not isinstance(val, pl.Expr):
            import math; return math.floor(float(val)) if val is not None else None
        return val.floor()

    def _split(val, delimiter, index):
        idx = int(index) - 1
        if not isinstance(val, pl.Expr):
            parts = str(val).split(delimiter) if val else []
            return parts[idx] if 0 <= idx < len(parts) else None
        # map_elements 虽然慢但安全，避免 Polars list.get 越界
        return val.cast(pl.Utf8).map_elements(
            lambda s: s.split(delimiter)[idx] if s and len(s.split(delimiter)) > idx else None,
            return_dtype=pl.Utf8,
        )

    def _upper(val):
        if not isinstance(val, pl.Expr):
            return str(val).upper() if val else val
        return val.cast(pl.Utf8).str.to_uppercase()

    def _lower(val):
        if not isinstance(val, pl.Expr):
            return str(val).lower() if val else val
        return val.cast(pl.Utf8).str.to_lowercase()

    def _trim(val):
        if not isinstance(val, pl.Expr):
            return str(val).strip() if val else val
        return val.cast(pl.Utf8).str.strip_chars()

    def _length(val):
        if not isinstance(val, pl.Expr):
            return len(str(val)) if val else 0
        return val.cast(pl.Utf8).str.len_chars()

    def _replace(val, old, new):
        if not isinstance(val, pl.Expr):
            return str(val).replace(str(old), str(new)) if val else val
        return val.cast(pl.Utf8).str.replace(str(old), str(new))

    def _substr(val, start, length):
        if not isinstance(val, pl.Expr):
            s = str(val) if val else ""
            return s[int(start):int(start)+int(length)]
        return val.cast(pl.Utf8).str.slice(int(start), int(length))

    def _contains(val, substr):
        if not isinstance(val, pl.Expr):
            return str(substr) in str(val) if val else False
        return val.cast(pl.Utf8).str.contains(str(substr), literal=True)

    def _starts_with(val, prefix):
        """STARTS_WITH(str, prefix) → str.starts_with(prefix)"""
        if not isinstance(val, pl.Expr):
            return str(val).startswith(str(prefix)) if val else False
        return val.cast(pl.Utf8).str.starts_with(str(prefix))

    def _not_contains(val, substr):
        """NOT_CONTAINS(str, substr) → NOT str.contains(substr)"""
        if not isinstance(val, pl.Expr):
            return str(substr) not in str(val) if val else True
        return ~val.cast(pl.Utf8).str.contains(str(substr), literal=True)

    # ─── Step 2: 构建 eval 环境 ──────────────────────────

    # 重要：在 eval 之前，需要将 = 替换为 ==（DSL 中 = 表示相等比较）
    # 避免单 = 被 Python 解析为赋值语句
    expr = re.sub(r'(?<![=!<>])=(?!=)', '==', expr)

    # 比较子式加括号：修正 AND/OR(→&/|) 与比较运算符的优先级
    # （Python 中 & 优先级高于 ==，故 `A AND B = C` 会被误解析为 `(A & B) == C`）
    expr = wrap_comparisons(expr)

    local_env = {
        "pl": pl,
        "NULL": None,
        "TRUE": True,
        "FALSE": False,
        "col": _col,
        "IF": _when,
        "COALESCE": _coalesce,
        "IFNULL": _coalesce,
        "NVL": _coalesce,
        "ROUND": _round,
        "ABS": _abs,
        "CEIL": _ceil,
        "FLOOR": _floor,
        "SPLIT": _split,
        "UPPER": _upper,
        "LOWER": _lower,
        "TRIM": _trim,
        "LENGTH": _length,
        "REPLACE": _replace,
        "SUBSTR": _substr,
        "CONTAINS": _contains,
        "STARTS_WITH": _starts_with,
        "NOT_CONTAINS": _not_contains,
    }

    try:
        result = eval(expr, {"__builtins__": {}}, local_env)
        if isinstance(result, pl.Expr):
            return result
        # 常量
        return pl.lit(result)
    except Exception as e:
        logger.error(f"公式编译失败: {formula} → {e}")
        raise ValueError(f"公式编译失败: {e}")


def evaluate_formula(df: pl.DataFrame, formula: str) -> pl.Series:
    """执行公式，返回结果 Series"""
    expr = compile_formula(formula, df.columns)
    try:
        result = df.select(expr.alias("_result"))
        return result["_result"]
    except Exception as e:
        logger.error(f"公式执行失败: {formula} → {e}")
        raise
