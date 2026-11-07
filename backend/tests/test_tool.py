"""回归测试：防止 @tool 函数名遮蔽服务函数，导致 StructuredTool 不可调用。

背景：@tool 装饰后函数会变成 StructuredTool 对象，若工具函数与导入的服务函数同名，
函数体内部调用会解析到 StructuredTool 本身，触发
'StructuredTool' object is not callable。
"""
from langchain_core.tools import StructuredTool


def test_tool_does_not_shadow_service_function():
    import tools.analyze_conversation_tool as mod

    # 1. 模块顶层的 analyze_conversation 是交给 Agent 的 StructuredTool
    assert isinstance(mod.analyze_conversation, StructuredTool)

    # 2. 工具函数内部实际调用的 run_conversation_analysis 是普通可调用函数，
    #    且不是 StructuredTool（避免同名遮蔽）
    assert callable(mod.run_conversation_analysis)
    assert not isinstance(mod.run_conversation_analysis, StructuredTool)

    # 3. 两者不是同一个对象
    assert mod.run_conversation_analysis is not mod.analyze_conversation


def test_tool_internal_call_returns_structured_result():
    import tools.analyze_conversation_tool as mod

    # 非 JSON 输入走内部逻辑（不触发 LLM），验证内部调用不再报
    # 'StructuredTool' object is not callable
    out = mod.analyze_conversation.func("not a json")
    assert isinstance(out, str)
    assert "INVALID_CONVERSATION" in out