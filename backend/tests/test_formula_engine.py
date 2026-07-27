"""测试公式引擎对 ar_balance 规则的处理"""
import polars as pl
from app.engine.formula_engine import evaluate_formula, compile_formula

# ─── 测试数据 ───────────────────────────────────────────
df = pl.DataFrame({
    "pay_amount": [1000.0, 500.0, None, 2000.0],
    "sum_fin_ar": [800.0, 600.0, 100.0, None],
})

print("测试数据:")
print(df)
print()

# ─── 测试 1: ar_balance 公式 ───────────────────────────
formula = "IF(pay_amount > sum_fin_ar, COALESCE(pay_amount, 0) - sum_fin_ar, 0)"

print(f"公式: {formula}")
print()

try:
    result = evaluate_formula(df, formula)
    df_result = df.with_columns(result.alias("ar_balance"))
    print("结果:")
    print(df_result)
    print()

    # 验证
    expected = [200.0, 0.0, -100.0, 0.0]
    actual = df_result["ar_balance"].to_list()
    for i, (e, a) in enumerate(zip(expected, actual)):
        status = "✅" if abs((a or 0) - e) < 0.01 else "❌"
        print(f"  Row {i}: expected={e}, actual={a} {status}")

except Exception as e:
    print(f"❌ 错误: {e}")

# ─── 测试 2: sum_fin_ar 公式 ───────────────────────────
print("\n" + "="*50)
print("测试 sum_fin_ar 公式:")

df2 = pl.DataFrame({
    "company_segment_code": ["930000", "840000", "970100", "972400"],
    "sum_fin_rev": [1000.0, 2000.0, 3000.0, 4000.0],
})

formula2 = "IF(company_segment_code.is_in(['930000', '840000']), sum_fin_rev, ROUND(sum_fin_rev * 1.06, 2))"
print(f"公式: {formula2}")

try:
    result2 = evaluate_formula(df2, formula2)
    df2_result = df2.with_columns(result2.alias("sum_fin_ar"))
    print("结果:")
    print(df2_result)
except Exception as e:
    print(f"❌ 错误: {e}")
    # 尝试替代写法
    print("\n尝试替代写法...")
    alt = "IF((company_segment_code == '930000') | (company_segment_code == '840000'), sum_fin_rev, ROUND(sum_fin_rev * 1.06, 2))"
    print(f"公式: {alt}")
    try:
        result2 = evaluate_formula(df2, alt)
        df2_result = df2.with_columns(result2.alias("sum_fin_ar"))
        print("结果:")
        print(df2_result)
    except Exception as e2:
        print(f"❌ 替代也失败: {e2}")
