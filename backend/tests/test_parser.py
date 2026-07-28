"""规则解析器 (parser) 测试：JSON 配置 → RuleConfig。"""
from app.engine.parser import RuleParser, RuleConfig, ConditionGroup


def test_parse_mapping_rule():
    rule_dict = {
        "rule_id": "r1",
        "field_name": "rate",
        "field_label": "税率",
        "rule_type": "mapping",
        "priority": 2,
        "enabled": True,
        "config": {
            "conditions": [
                {
                    "id": "g1", "priority": 1, "logic": "AND",
                    "rows": [{"id": "c1", "field": "code", "operator": "in", "value": ["930000"]}],
                    "result_type": "constant", "result_value": 0,
                }
            ],
            "default_result": 0.06,
        },
        "depends_on": ["code"],
        "description": "税率映射",
    }
    rc = RuleParser.parse(rule_dict)
    assert isinstance(rc, RuleConfig)
    assert rc.field_name == "rate"
    assert rc.rule_type == "mapping"
    assert rc.priority == 2
    assert rc.default_result == 0.06
    assert rc.depends_on == ["code"]
    assert len(rc.conditions) == 1
    assert isinstance(rc.conditions[0], ConditionGroup)
    assert rc.conditions[0].rows[0].operator == "in"
    assert rc.conditions[0].rows[0].value == ["930000"]


def test_parse_computed_rule_with_formula():
    rule_dict = {
        "field_name": "ar_balance",
        "rule_type": "computed",
        "priority": 11,
        "enabled": True,
        "config": {"formula_expression": "IF(a > b, a - b, 0)"},
        "depends_on": ["a", "b"],
    }
    rc = RuleParser.parse(rule_dict)
    assert rc.rule_type == "computed"
    assert rc.formula_expression == "IF(a > b, a - b, 0)"
    assert rc.depends_on == ["a", "b"]
    assert rc.conditions == []


def test_parse_cleaning_rule():
    rule_dict = {
        "field_name": "code",
        "rule_type": "cleaning",
        "priority": 5,
        "enabled": True,
        "config": {"cleaning_steps": [{"action": "fill_null", "params": {"fill_value": "972400"}}]},
    }
    rc = RuleParser.parse(rule_dict)
    assert rc.rule_type == "cleaning"
    assert rc.cleaning_steps[0]["action"] == "fill_null"


def test_parse_defaults_for_missing_fields():
    """缺省字段应安全回退（不抛错）。"""
    rc = RuleParser.parse({"field_name": "x", "rule_type": "mapping"})
    assert rc.priority == 0
    assert rc.enabled is True
    assert rc.conditions == []
    assert rc.depends_on == []
    assert rc.default_result is None
