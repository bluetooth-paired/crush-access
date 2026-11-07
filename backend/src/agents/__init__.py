"""Agent 包：唯一 Agent 实例及其统一服务入口。"""
from agents.agent import build_agent
from agents.service import AgentService, AdvisorError, get_agent_service

__all__ = ["build_agent", "AgentService", "AdvisorError", "get_agent_service"]
