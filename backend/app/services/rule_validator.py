"""规则配置完整性校验"""


def validate_rule_config(rule_type: str, config: dict) -> list[str]:
    """校验规则配置，返回错误列表（空列表表示配置完整）"""
    errors: list[str] = []

    if rule_type == "mapping":
        conditions: list = config.get("conditions", [])
        if not conditions:
            errors.append("至少需要 1 个条件组")
            return errors

        for gi, g in enumerate(conditions):
            gp = f"条件组{gi + 1}"
            rows: list = g.get("rows", [])
            if not rows:
                errors.append(f"{gp}: 至少需要 1 个条件行")
                continue

            for ri, row in enumerate(rows):
                rp = f"{gp}/行{ri + 1}"
                if not row.get("field"):
                    errors.append(f"{rp}: 字段名未填写")
                if not row.get("operator"):
                    errors.append(f"{rp}: 操作符未选择")
                op = row.get("operator", "")
                val = row.get("value")
                if op not in ("is_null", "is_not_null") and val in (None, ""):
                    errors.append(f"{rp}: 比较值未填写")

            result_val = g.get("result_value")
            # 结果值允许为空——可能由 default_result 兜底，此处不强制

        # 检查是否有默认值兜底（所有条件组都没命中时的保底值）
        has_default = config.get("default_result") not in (None, "")
        has_group_results = any(
            g.get("result_value") not in (None, "") for g in conditions
        )
        if not has_default and not has_group_results:
            errors.append("所有条件组均未设置结果值，且没有默认值兜底")

    elif rule_type == "cleaning":
        steps: list = config.get("cleaning_steps", [])
        if not steps:
            errors.append("至少需要 1 个清洗步骤")
        else:
            for si, step in enumerate(steps):
                if not step.get("action"):
                    errors.append(f"步骤{si + 1}: 操作类型未选择")

    elif rule_type == "lookup":
        tid = config.get("lookup_table_id")
        if not tid:
            errors.append("需要选择字典表")
        kf = config.get("lookup_key_field")
        if not kf:
            errors.append("需要指定匹配键字段")
        vf = config.get("lookup_value_field")
        if not vf:
            errors.append("需要指定取值字段")

    elif rule_type == "computed":
        expr: str = config.get("formula_expression", "")
        if not expr or not expr.strip():
            errors.append("需要填写计算公式")

    return errors
