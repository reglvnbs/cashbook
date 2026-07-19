# 账本

一个面向单人使用的简体中文账本。应用提供总览、流水和预算三个响应式页面，支持手动记账、DeepSeek 自然语言草稿、流水组合筛选与月度预算；数据保存在本机 SQLite 中。

## 配置

普通配置统一保存在 `config.json`，包括服务地址、数据库、日志、分页和 DeepSeek 请求参数。`SECRET_KEY`、`DEEPSEEK_API_KEY` 和 `CASHBOOK_API_TOKEN` 只通过环境变量提供，变量说明见 `.env.example`。

未提供 DeepSeek Key 时只禁用 AI 记账；未提供自动化 Token 时只禁用 Bearer Token 单笔新增接口，手动记账不受影响。

## 本地运行与测试

开发和测试优先使用 Python 3.13，并且只通过隔离脚本启动；未安装 3.13 时会显示警告并自动回退到系统 `python3`：

```text
./test.sh
./test.sh --local
```

脚本会将项目同步到 `build/test/`，数据库、日志、虚拟环境和缓存不会写入源码目录。完整参数和排查方式见 [测试与本地运行指南](<docs/7. testing-guide.md>)。

## 部署

应用通过 Gunicorn 和 Docker 离线部署：

```text
./pack.sh --tag 1.0.0
```

镜像打包、数据卷、更新及迁移步骤见 [离线部署指南](<docs/9. deployment-guide.md>)；工程、接口和页面规则分别见 `docs/0. engineering-design.md` 与 `docs/2. interface-design.md`。
