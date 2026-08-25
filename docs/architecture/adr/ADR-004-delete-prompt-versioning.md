# ADR-004: 删除提示词版本管理和影子测试

**状态**：已接受  
**日期**：2026-08-20

## 背景

项目曾实现提示词版本管理（version_manager.py）和影子测试（shadow_recorder.py），包含 9 个 API 端点、DB 表、前端页面。

## 决策

**删除**提示词版本管理和影子测试功能。

## 理由

1. **过度工程化**：实际使用中从未启用影子测试，版本管理用 git 管理 .j2 模板即可
2. **维护负担**：9 个 API 端点 + 2 个前端页面 + 3 个测试文件，增加维护成本
3. **简单替代**：prompt/templates/*.j2 用 git 管理版本，PromptEngine 加载优先级：.j2 文件 > DB 热修 > 代码 fallback
4. **保留核心**：prompt_engine.py 核心渲染逻辑保留，DB 热修能力保留（prompt_templates 表）

## 删除内容

- 后端：version_manager.py (276行) + shadow_recorder.py (115行) + prompt_pipeline.py (255行)
- API：9 个 /prompts 端点
- 前端：prompt.vue + shadowTest.vue
- 测试：test_version_manager.py + test_shadow_recorder.py + test_prompt_integration.py

## 保留内容

- prompt/templates/*.j2（4 个模板文件，RAG 引擎直接使用）
- prompt_engine.py 核心渲染逻辑
- prompt_templates 表（DB 热修能力）