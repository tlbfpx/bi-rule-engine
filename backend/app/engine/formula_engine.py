"""公式计算引擎 — 类 Excel DSL → Polars Expression 编译器（lark 实现，引擎 v2）。

用 lark 文法定义 DSL 语法与优先级，Transformer 自下而上把 AST 节点转为 Polars
表达式（或 Python 标量）。相比早期"正则预处理 + eval"，优先级由文法结构性保证
（不再有 AND/= 优先级 bug），且无 eval 攻击面，错误信息带行列定位。

公开 API（不变）：
- ``compile_formula(formula, columns) -> pl.Expr``
- ``evaluate_formula(df, formula) -> pl.Series``

DSL：IF/COALESCE/ROUND/SPLIT/CONTAINS/... 函数；+ - * /；= != > >= < <=；
AND OR NOT（大小写不敏感）；col IN (...)；col IS [NOT] NULL；列引用、数字、
单引号字符串、True/False/NULL 字面量。
"""
import ast
import math
import polars as pl
from loguru import logger
from lark import Lark, Transformer, UnexpectedInput, v_args

# ───────────────────────── 文法 ─────────────────────────
# 优先级（低→高）：OR < AND < NOT < 比较/IN/IS < +- < */ < 一元- < atom
# 关键字大小写不敏感（优先级 .2 高于 NAME）。
_GRAMMAR = r"""
?start: expr

?expr: logic_or
?logic_or: logic_and | logic_or OR_OP logic_and     -> or_
?logic_and: logic_not | logic_and AND_OP logic_not -> and_
?logic_not: NOT_OP logic_not -> not_ | comparison
?comparison: arith
    | arith EQ_OP arith  -> eq
    | arith NEQ_OP arith -> neq
    | arith GT_OP arith  -> gt
    | arith GTE_OP arith -> gte
    | arith LT_OP arith  -> lt
    | arith LTE_OP arith -> lte
    | arith IN_OP "(" args ")"        -> in_
    | arith IS_OP NOT_OP NULL_OP      -> is_not_null
    | arith IS_OP NULL_OP             -> is_null
?arith: term | arith ADD_OP term -> add | arith SUB_OP term -> sub
?term: factor | term MUL_OP factor -> mul | term DIV_OP factor -> div
?factor: SUB_OP factor -> neg | atom
?atom: NAME "(" args? ")" -> func | NAME -> column
       | NUMBER -> number | STRING -> string
       | TRUE_OP -> true_ | FALSE_OP -> false_ | NULL_OP -> null_
       | "(" expr ")" -> paren

args: expr ("," expr)*

OR_OP.2: /OR/i
AND_OP.2: /AND/i
NOT_OP.2: /NOT/i
IN_OP.2: /IN/i
IS_OP.2: /IS/i
NULL_OP.2: /NULL/i
TRUE_OP.2: /TRUE/i
FALSE_OP.2: /FALSE/i
EQ_OP: "="
NEQ_OP: "!="
GTE_OP: ">="
LTE_OP: "<="
GT_OP: ">"
LT_OP: "<"
ADD_OP: "+"
SUB_OP: "-"
MUL_OP: "*"
DIV_OP: "/"
NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
NUMBER: /(?:\d+\.\d+|\d+)(?:[eE][+-]?\d+)?/
STRING: /'([^'\\]|\\.)*'/

%import common.WS
%ignore WS
"""

_parser = Lark(_GRAMMAR, parser="lalr", maybe_placeholders=False)


# ───────────────────────── 函数实现（双模式 Expr/scalar） ─────────────────────────
def _when(cond, true_val, false_val=None):
    """IF(cond, true, false) → pl.when(cond).then(true).otherwise(false)"""
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
    return val.round(decimals)


def _abs(val):
    if not isinstance(val, pl.Expr):
        return abs(float(val)) if val is not None else None
    return val.abs()


def _ceil(val):
    if not isinstance(val, pl.Expr):
        return math.ceil(float(val)) if val is not None else None
    return val.ceil()


def _floor(val):
    if not isinstance(val, pl.Expr):
        return math.floor(float(val)) if val is not None else None
    return val.floor()


def _split(val, delimiter, index):
    idx = int(index) - 1
    if not isinstance(val, pl.Expr):
        parts = str(val).split(delimiter) if val else []
        return parts[idx] if 0 <= idx < len(parts) else None
    # map_elements 虽慢但安全，避免 list.get 越界
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
        return s[int(start):int(start) + int(length)]
    return val.cast(pl.Utf8).str.slice(int(start), int(length))


def _contains(val, substr):
    if not isinstance(val, pl.Expr):
        return str(substr) in str(val) if val else False
    return val.cast(pl.Utf8).str.contains(str(substr), literal=True)


def _starts_with(val, prefix):
    if not isinstance(val, pl.Expr):
        return str(val).startswith(str(prefix)) if val else False
    return val.cast(pl.Utf8).str.starts_with(str(prefix))


def _not_contains(val, substr):
    if not isinstance(val, pl.Expr):
        return str(substr) not in str(val) if val else True
    return ~val.cast(pl.Utf8).str.contains(str(substr), literal=True)


# 函数名（大写）→ 实现；别名（IFNULL/NVL）复用 _coalesce
FUNCS = {
    "IF": _when,
    "COALESCE": _coalesce, "IFNULL": _coalesce, "NVL": _coalesce,
    "ROUND": _round,
    "ABS": _abs, "CEIL": _ceil, "FLOOR": _floor,
    "SPLIT": _split,
    "UPPER": _upper, "LOWER": _lower, "TRIM": _trim, "LENGTH": _length,
    "REPLACE": _replace, "SUBSTR": _substr,
    "CONTAINS": _contains, "STARTS_WITH": _starts_with, "NOT_CONTAINS": _not_contains,
}


# ───────────────────────── Transformer（AST → Expr/scalar） ─────────────────────────
# 原生 Python 运算符对 polars Expr 和标量都正确分发（polars 重载了 + - * / == 等）。
@v_args(inline=True)
class _FormulaTransformer(Transformer):
    def or_(self, a, _op, b): return a | b
    def and_(self, a, _op, b): return a & b
    def not_(self, _op, x): return ~x

    def eq(self, a, _op, b): return a == b
    def neq(self, a, _op, b): return a != b
    def gt(self, a, _op, b): return a > b
    def gte(self, a, _op, b): return a >= b
    def lt(self, a, _op, b): return a < b
    def lte(self, a, _op, b): return a <= b

    def in_(self, a, _op, vals):
        targets = [str(v) for v in vals]
        return a.is_in(targets) if isinstance(a, pl.Expr) else (str(a) in targets)

    def is_null(self, a, _is, _null):
        return a.is_null() if isinstance(a, pl.Expr) else (a is None)

    def is_not_null(self, a, _is, _not, _null):
        return a.is_not_null() if isinstance(a, pl.Expr) else (a is not None)

    def add(self, a, _op, b): return a + b
    def sub(self, a, _op, b): return a - b
    def mul(self, a, _op, b): return a * b
    def div(self, a, _op, b): return a / b
    def neg(self, _op, x): return -x

    def column(self, name): return pl.col(str(name))
    def number(self, tok):
        s = str(tok)
        return float(s) if ("." in s or "e" in s or "E" in s) else int(s)
    def string(self, tok):
        # 用 literal_eval 解析单引号字符串字面量（UTF-8 安全、正确处理 \' \n 等转义）
        return ast.literal_eval(str(tok))
    def true_(self): return True
    def false_(self): return False
    def null_(self): return None
    def paren(self, x): return x

    def args(self, *items): return list(items)

    def func(self, name, args=None):
        fname = str(name).upper()
        fn = FUNCS.get(fname)
        if fn is None:
            raise ValueError(f"公式未知函数: {fname}")
        return fn(*(args or []))


_transformer = _FormulaTransformer()


# ───────────────────────── 公开 API ─────────────────────────
def compile_formula(formula: str, columns: list[str] | None = None) -> pl.Expr:
    """将 DSL 公式编译为 Polars Expression。

    columns 参数为兼容旧调用保留（实现不依赖它）。
    """
    try:
        tree = _parser.parse(formula)
    except UnexpectedInput as e:
        loc = f"line {e.line}, column {e.column}" if hasattr(e, "line") else str(e)
        raise ValueError(f"公式语法错误（{loc}）: {formula}") from e

    try:
        result = _transformer.transform(tree)
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"公式编译失败: {formula} → {e}")
        raise ValueError(f"公式编译失败: {e}") from e

    return result if isinstance(result, pl.Expr) else pl.lit(result)


def evaluate_formula(df: pl.DataFrame, formula: str) -> pl.Series:
    """执行公式，返回结果 Series"""
    expr = compile_formula(formula, df.columns)
    try:
        result = df.select(expr.alias("_result"))
        return result["_result"]
    except Exception as e:
        logger.error(f"公式执行失败: {formula} → {e}")
        raise
