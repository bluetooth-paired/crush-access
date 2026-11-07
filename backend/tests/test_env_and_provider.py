"""运行环境测试：.env 加载与模型配置解析（不发起任何真实模型调用）。"""
from __future__ import annotations

import os

import pytest

import env_loader
from llm.provider import (
    DEEPSEEK_BASE_URL,
    DEEPSEEK_DEFAULT_MODEL,
    MOONSHOT_BASE_URL,
    MOONSHOT_DEFAULT_MODEL,
    LLMConfigError,
    resolve_llm_config,
)

_LLM_KEYS = (
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "MOONSHOT_API_KEY",
    "MOONSHOT_BASE_URL",
    "MOONSHOT_MODEL",
    "COZE_WORKLOAD_IDENTITY_API_KEY",
    "COZE_INTEGRATION_MODEL_BASE_URL",
)


@pytest.fixture()
def clean_llm_env(monkeypatch: pytest.MonkeyPatch):
    for key in _LLM_KEYS:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


# ---------------------------------------------------------------------------
# .env 加载
# ---------------------------------------------------------------------------
def test_env_file_is_loaded_and_does_not_override_existing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CRUSH_ENV_TEST_A=from-file\nCRUSH_ENV_TEST_B=from-file\n", encoding="utf-8")

    monkeypatch.delenv("CRUSH_ENV_TEST_A", raising=False)
    monkeypatch.setenv("CRUSH_ENV_TEST_B", "from-process")
    monkeypatch.setattr(env_loader, "_LOADED", False)
    monkeypatch.setattr(env_loader, "_candidate_files", lambda: [env_file])

    env_loader.load_project_env()

    assert os.environ["CRUSH_ENV_TEST_A"] == "from-file"      # 文件值被加载
    assert os.environ["CRUSH_ENV_TEST_B"] == "from-process"   # 不覆盖显式环境变量


def test_env_loading_is_idempotent(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CRUSH_ENV_TEST_C=first\n", encoding="utf-8")

    monkeypatch.delenv("CRUSH_ENV_TEST_C", raising=False)
    monkeypatch.setattr(env_loader, "_LOADED", False)
    monkeypatch.setattr(env_loader, "_candidate_files", lambda: [env_file])
    env_loader.load_project_env()
    assert os.environ["CRUSH_ENV_TEST_C"] == "first"

    env_file.write_text("CRUSH_ENV_TEST_C=second\n", encoding="utf-8")
    env_loader.load_project_env()  # 第二次调用不应重新读取
    assert os.environ["CRUSH_ENV_TEST_C"] == "first"


def test_missing_env_file_does_not_break_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(env_loader, "_LOADED", False)
    monkeypatch.setattr(env_loader, "_candidate_files", lambda: [tmp_path / "missing.env"])
    env_loader.load_project_env()  # 不抛异常即通过


# ---------------------------------------------------------------------------
# 模型名称与端点解析
# ---------------------------------------------------------------------------
def test_deepseek_config_uses_deepseek_model_not_file_default(clean_llm_env):
    clean_llm_env.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    cfg = resolve_llm_config()

    assert cfg.provider == "deepseek"
    assert cfg.model == DEEPSEEK_DEFAULT_MODEL == "deepseek-chat"
    assert cfg.base_url == DEEPSEEK_BASE_URL
    assert cfg.send_thinking_body is False  # DeepSeek 不支持思考强度参数


def test_deepseek_model_can_be_overridden(clean_llm_env):
    clean_llm_env.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    clean_llm_env.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    assert resolve_llm_config().model == "deepseek-reasoner"


def test_moonshot_config_uses_current_kimi_model(clean_llm_env):
    clean_llm_env.setenv("MOONSHOT_API_KEY", "sk-moonshot-test")
    cfg = resolve_llm_config()

    assert cfg.provider == "moonshot"
    assert cfg.model == MOONSHOT_DEFAULT_MODEL == "kimi-k3"
    assert cfg.base_url == MOONSHOT_BASE_URL
    assert cfg.send_thinking_body is False


def test_moonshot_model_can_be_overridden(clean_llm_env):
    clean_llm_env.setenv("MOONSHOT_API_KEY", "sk-moonshot-test")
    clean_llm_env.setenv("MOONSHOT_MODEL", "kimi-k2.6")
    assert resolve_llm_config().model == "kimi-k2.6"


def test_explicit_openai_compatible_config(clean_llm_env):
    clean_llm_env.setenv("LLM_API_KEY", "sk-explicit")
    clean_llm_env.setenv("LLM_BASE_URL", "https://example.com/v1")
    clean_llm_env.setenv("LLM_MODEL", "my-model")
    cfg = resolve_llm_config()

    assert cfg.provider == "openai-compatible"
    assert cfg.model == "my-model"
    assert cfg.base_url == "https://example.com/v1"


def test_missing_all_credentials_raises_config_error(clean_llm_env):
    with pytest.raises(LLMConfigError):
        resolve_llm_config()


def test_explicit_deepseek_endpoint_infers_model(clean_llm_env):
    """只填 LLM_API_KEY + DeepSeek 端点时，不能把配置文件里的豆包模型名发过去。"""
    clean_llm_env.setenv("LLM_API_KEY", "sk-explicit")
    clean_llm_env.setenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    cfg = resolve_llm_config()

    assert cfg.provider == "openai-compatible"
    assert cfg.model == DEEPSEEK_DEFAULT_MODEL


def test_explicit_moonshot_endpoint_infers_model(clean_llm_env):
    clean_llm_env.setenv("LLM_API_KEY", "sk-explicit")
    clean_llm_env.setenv("LLM_BASE_URL", "https://api.moonshot.cn/v1")
    cfg = resolve_llm_config()

    assert cfg.model == MOONSHOT_DEFAULT_MODEL


def test_explicit_key_without_base_or_model_fails_fast(clean_llm_env):
    """缺少端点与模型名时明确报错，而不是静默请求 OpenAI 官方端点后 401。"""
    clean_llm_env.setenv("LLM_API_KEY", "sk-explicit")
    with pytest.raises(LLMConfigError):
        resolve_llm_config()


def test_deepseek_output_tokens_are_clamped(clean_llm_env):
    """配置文件里的 10000 只适用于平台网关，DeepSeek 需要收敛到端点上限。"""
    clean_llm_env.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    clean_llm_env.setenv("LLM_MAX_COMPLETION_TOKENS", "10000")
    assert resolve_llm_config().max_completion_tokens == 8192


def test_moonshot_output_tokens_are_clamped(clean_llm_env):
    clean_llm_env.setenv("MOONSHOT_API_KEY", "sk-moonshot-test")
    clean_llm_env.setenv("LLM_MAX_COMPLETION_TOKENS", "10000")
    assert resolve_llm_config().max_completion_tokens == 8192
