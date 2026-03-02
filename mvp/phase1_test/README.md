# sen-tang-speech MVP - Phase 1

最小可运行 FastAPI 服务，提供 `/mock/report` 输出固定结构的 mock ReportResponse。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python -m app.main
```

### 3. 访问端点

- 健康检查：http://127.0.0.1:8000/health
- Mock Report：http://127.0.0.1:8000/mock/report
- Step4 Demo：http://127.0.0.1:8000/pipeline/step4_demo
- Step5 Demo：http://127.0.0.1:8000/pipeline/step5_demo

### 4. 运行测试

```bash
pytest -q
```

## 项目结构

```
phase1_test/
  app/
    __init__.py
    main.py
    mock_report.py
    rule_engine/
      __init__.py
      top1_ranker.py
    pipeline/
      __init__.py
      step4_rule_engine.py
      step5_llm_feedback.py
    llm/
      __init__.py
      prm_v0_1.py
      redaction.py
      trace.py
      schema_validate.py
      template_fallback.py
      client.py
  tests/
    test_mock_report_pol.py
    test_top1_ranker_unit.py
    test_determinism_smoke.py
    test_llm_fallback_unit.py
    test_llm_live_integration.py
  eval/
    __init__.py
    canonical.py
    min_regression_v0.jsonl
    run_min_regression.py
    run_determinism.py
  scripts/
    run_llm_live_smoke.py
  artifacts/
    mock_report.json
    step4_demo_report.json
    step5_demo_report.json
    regression/
    determinism/
  requirements.txt
  README.md
```

## 启动日志示例

```
startup ok
mock report generated path=d:\code\AI\startUp\sen-tang-speech\mvp\phase1_test\artifacts\mock_report.json
```

## API 响应示例

### GET /health

```json
{"status": "ok"}
```

### GET /mock/report

```json
{
  "pol_version": "POL-v0.1",
  "session": {
    "session_id": "uuid-string",
    "task_type": "IMPROV_60S",
    "language": "zh",
    "generated_at": "2026-03-01T00:00:00+00:00"
  },
  "scores": {
    "overall": 80
  },
  "rule_engine": {
    "triggers": [...],
    "top_trigger_id": "BR-OPP-001-R-TASK-001",
    "next_target": null
  },
  "llm_feedback": {
    "suggestions": []
  },
  "warnings": []
}
```

## LLM 实时测试（可选）

### 环境变量配置

运行 LLM 实时测试需要配置以下环境变量：

```bash
# 必需
export QWEN_API_KEY="your-api-key"
export QWEN_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"

# 可选
export QWEN_MODEL_PRIMARY="qwen-plus"
export QWEN_MODEL_BACKUP="qwen-turbo"
```

### 运行方式

**方式 1：pytest 标记**

```bash
# 运行所有 integration 测试
pytest -q -m integration

# 运行所有测试（integration 测试在无 env var 时自动 skip）
pytest -q
```

**方式 2：CLI 脚本**

```bash
python scripts/run_llm_live_smoke.py
```

### 退出码

- 0: 成功（LLM 通路正常，输出有效）
- 1: 失败（缺少环境变量、输出无效或 fallback 触发）
