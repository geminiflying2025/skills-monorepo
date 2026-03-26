# CAPTCHA Solver Design

## Background
用户希望在本地 agent 访问网页的流程中，自动识别图形字符验证码并填写。目标场景是自有系统或测试环境。

## Goal
构建一个本地可运行的验证码识别工具链，实现：
1. 自动打开网页并抓取验证码图片
2. 本地 OCR 识别验证码字符串
3. 自动填充并提交
4. 支持失败重试与调试日志

## Scope
### In Scope
- Playwright 自动化网页交互
- 本地 Python OCR HTTP 服务
- 配置化页面选择器
- CLI 一键运行
- 基础单元测试（文本后处理）

### Out of Scope
- 规避第三方站点反自动化机制
- 云端 OCR 服务对接
- 滑块/点选类验证码

## Architecture
- `skills/captcha-solver/ocr_service.py`
  - FastAPI 服务，提供 `/health` 与 `/solve`
  - 预处理图像（灰度、阈值、降噪）
  - 调用 Tesseract 做 OCR
- `skills/captcha-solver/agent_runner.py`
  - 使用 Playwright 打开页面
  - 按选择器定位验证码并截图
  - 调用 OCR 服务拿识别结果
  - 填写验证码并提交，按策略重试
- `skills/captcha-solver/config.example.yaml`
  - URL、验证码图片选择器、输入框、提交按钮、刷新按钮等
- `skills/captcha-solver/run.py`
  - 命令行入口，执行自动化流程

## Data Flow
1. 读取配置文件和运行参数
2. 启动浏览器并进入目标 URL
3. 捕获验证码区域截图
4. 发起 OCR `/solve`
5. 清洗识别文本后写入输入框
6. 提交并检查失败提示
7. 成功结束或失败重试直到上限

## Error Handling
- 选择器不存在：抛出明确错误并建议检查配置
- OCR 返回空字符串：刷新验证码并重试
- 页面提示验证码错误：等待刷新并重试
- 网络/超时：按重试策略处理并落日志

## Security
- 默认不把验证码图片上传外网
- 不引入任何 API Key
- 配置文件不含敏感凭据

## Validation
- 单元测试：验证码文本清洗函数
- 手工验证：`--headless false` 下可观察完整流程
- 干跑模式：仅识别不提交（用于调试）

## Acceptance Criteria
1. 可通过 `python run.py --config config.yaml` 运行
2. 对目标验证码页面可自动完成抓图、识别、填充
3. 错误时可重试并输出结构化日志
4. 提供最小测试用例且通过
