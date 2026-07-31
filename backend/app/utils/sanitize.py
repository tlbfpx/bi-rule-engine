"""
输入清理工具

提供 HTML 标签清理功能，防止存储型 XSS 攻击。
对用户输入的字符串字段（名称、标签、描述等）移除 <script>、<img>、<svg> 等潜在危险的 HTML 标签。

注意：本模块仅清理 HTML 标签，不做完全 XSS 防护。
真正的 XSS 防护依赖前端输出编码（React JSX 自动转义）。
后端清理作为纵深防御层。
"""
import re

# 危险 HTML 标签（完整标签 + 自闭合标签共享此列表）
_DANGEROUS_TAGS = (
    "script|iframe|object|embed|svg|math|style|link|meta|applet|form|base"
    "|video|audio|source|track|img|body|details|summary|marquee|keygen|isindex|plaintext"
)

# 匹配完整标签对（<script>...</script> 等，含内容）
TAG_PATTERN = re.compile(
    rf"<\s*(?:{_DANGEROUS_TAGS})\b[^>]*>.*?<\s*/\s*(?:{_DANGEROUS_TAGS})\s*>",
    re.IGNORECASE | re.DOTALL,
)

# 匹配自闭合或开放的危险标签（<img src=x>, <svg onload=...>, <body onload=...> 等）
SELF_CLOSING_TAG = re.compile(
    rf"<\s*(?:{_DANGEROUS_TAGS})\b[^>]*/?\s*>",
    re.IGNORECASE,
)

# 匹�� on* 事件属性（支持带引号和��带引号的值）
# 例如: onerror=alert(1), onload="malicious()", onclick='bad()'
EVENT_ATTR = re.compile(
    r"\bon\w+\s*=\s*(?:[\"'][^\"']*[\"']|\S+)",
    re.IGNORECASE,
)

# 匹配 javascript: / data: 协议 URL
JAVASCRIPT_URL = re.compile(
    r"""\b(?:javascript|data):[^\s"']+""",
    re.IGNORECASE,
)


def strip_html(text: str) -> str:
    """移除字符串中的危险 HTML 标签和事件属性。

    保留纯文本内容，只移除标签本身及其内容。
    清理策略：
    1. 移除 <script>...</script> 等完整标签（含内容）
    2. 移除自闭合/开放的危险标签（<img>, <svg>, <body> 等）
    3. 移除 on* 事件属性（包括无引号的值）
    4. 移除 javascript: / data: URL 协议

    Args:
        text: 待清理的字符串

    Returns:
        清理后的安全字符串
    """
    if not isinstance(text, str):
        return text

    # 移除完整标签对（含内容）
    text = TAG_PATTERN.sub("", text)
    # 移除自闭合/开放的危险标签
    text = SELF_CLOSING_TAG.sub("", text)
    # 移除事件属性
    text = EVENT_ATTR.sub("", text)
    # 移除 javascript: / data: 协议 URL
    text = JAVASCRIPT_URL.sub("", text)

    return text.strip()


def sanitize_user_input(value: str | None) -> str | None:
    """安全地清理用户输入字符串。

    Args:
        value: 用户输入的字符串或 None

    Returns:
        清理后的字符串，None 保持 None
    """
    if value is None:
        return None
    return strip_html(value)
