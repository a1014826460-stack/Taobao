# 淘宝浏览器抓包爬虫设计

**日期：** 2026-08-13  
**状态：** 已获用户确认，待书面审阅后进入实现计划

## 目标

使用已安装的 `camoufox-reverse-mcp` / Camoufox 浏览器，构建淘宝和天猫浏览器抓包采集器：按关键词抓取搜索页商品，进入全部商品详情页，保存商品、评论、商家及相关 JSON 响应到独立 SQLite 数据库。采集过程支持多账号独立浏览器实例、任务表恢复、人工化浏览节奏和账号级风控暂停。

## 已确认范围

- 平台：淘宝 + 天猫
- 每个关键词：最多 3 个搜索页
- 详情：搜索结果中的全部商品
- 评论：首屏及页面自然加载出的 JSON，不额外无限翻页
- 账号：每账号独立浏览器实例，任务按账号轮换
- 风控：暂停问题账号、记录原因、继续其他账号
- 原始数据：保留脱敏后的完整响应 JSON
- 浏览器：默认可见，提供 `--headless`
- 输入：命令行关键词和数据库任务表均支持
- 数据库：独立 `data/taobao_browser_crawler.db`

## 非目标

- 不自动破解验证码、滑块或人机验证
- 不把 Cookie、Authorization、Set-Cookie 或签名秘密写入数据库、日志或导出文件
- 不通过无界限并发、无限重试或固定高频请求扩大采集规模
- 不覆盖现有淘宝直连接口爬虫和工作区未提交修改

## 架构

采用单进程、多浏览器实例轮换。调度器从 CLI 或任务表读取任务，为每个账号维护独立 Camoufox browser/context 和 Cookie 状态；同一账号不并发执行任务。浏览器抓包字段与 `camoufox-reverse-mcp` 的 `network_capture`、`list_network_requests`、`get_network_request` 对齐。

```text
CLI / 任务表
    ↓
TaskScheduler（状态、账号分配、运行边界）
    ↓
AccountBrowserPool（每账号独立 browser/context/Cookie）
    ↓
TaobaoBrowserCrawler（搜索、详情、人工化浏览、抓包）
    ↓
ResponseNormalizer（脱敏、分类、标准字段提取）
    ↓
SQLiteRepository（幂等写入与恢复）
```

开发和侦察阶段使用 MCP 工具定位实际请求；正式采集器通过本地 Python Camoufox/Playwright 模块运行，避免依赖聊天会话中的长期 MCP 连接，同时保持相同抓包和脱敏协议。

## 模块划分

```text
src/taobao/browser/
  accounts.py        # Cookie 解析、账号状态
  browser_pool.py    # 独立浏览器实例生命周期
  human_behavior.py  # 停留、滚动、鼠标轨迹、随机等待
  network_capture.py # 抓包、响应筛选和脱敏
  crawler.py         # 搜索/详情采集流程
  risk_control.py    # 登录失效、验证码、风控识别
  repository.py      # SQLite 表、迁移、幂等写入
  cli.py             # CLI 入口
```

## 数据库设计

数据库位于 `data/taobao_browser_crawler.db`，与现有 API 爬虫数据库隔离。

### `accounts`

保存本地账号元数据，不保存 Cookie 内容：`account_id`、`cookie_source`、`status`（`available/busy/paused/expired`）、`pause_reason`、`last_used_at`、成功/失败计数和时间戳。

### `crawl_tasks`

支持 `keyword` 和 `detail` 两类任务：`task_id`、`keyword`、`item_id`、`platform`、`page_no`、`status`（`pending/running/success/failed/paused`）、分配账号、尝试次数、脱敏错误、`next_run_at`、`run_id`。

唯一约束：搜索任务使用 `(task_type, keyword, page_no)`；详情任务使用 `(task_type, platform, item_id)`。

### 业务表

- `search_products`：平台、关键词、页码、商品 ID、标题、价格、销量、店铺、URL、标准字段和 `raw_json`。
- `product_details`：商品 ID、标题、描述 JSON、SKU JSON、图片 JSON 和 `raw_json`。
- `product_comments`：商品 ID、评论 ID、评分、内容、脱敏作者、`raw_json`。
- `seller_infos`：商品 ID、卖家/店铺 ID、店铺名、等级、评分 JSON 和 `raw_json`。

### `network_records`

保存 `run_id`、账号、页面类型、脱敏 URL、方法、状态码、资源类型、脱敏响应头、响应体、SHA-256 和时间戳。无法分类的 JSON 归类为 `unknown_json`，仍保留原始响应。

### `crawl_runs`

保存启动/结束时间、输入来源、关键词范围、页数、账号数量、成功/失败/暂停统计和脱敏错误摘要，作为可恢复运行边界。

## 任务与数据流

1. CLI 参数或任务表产生关键词任务。
2. 每个关键词创建最多 3 个页任务。
3. 成功的搜索响应解析出商品并幂等写入 `search_products`。
4. 每个新商品生成详情任务；已成功详情不重复抓取。
5. 详情页自然加载商品、评论、商家 JSON 并写入对应业务表及 `network_records`。
6. 程序重启时将遗留 `running` 任务恢复为 `pending`；`success` 不重抓；`paused` 账号不再分配。

## 浏览行为与限速

每个页面执行：开启网络捕获、导航、等待、随机停留 10–30 秒、多段随机滚动、有限随机鼠标轨迹、等待自然请求完成、停止捕获和持久化。

默认全局串行页面任务；同账号不并发。账号连续任务之间有额外冷却。CLI 提供 `--min-delay`、`--max-delay`，默认 10 和 30 秒。默认可见浏览器，`--headless` 显式启用无头模式。浏览器实例数量受限以避免资源耗尽。

鼠标轨迹只在页面可见区域内移动，不点击敏感控件；页面高度不足时不强制滚动。

## 抓包与 JSON 分类

筛选 `xhr`、`fetch` 或 JSON 文档响应；优先接受 JSON `Content-Type`，同时尝试解析可识别的 JSON 文本。通过 URL、请求方法、响应头和 JSON 结构特征识别：`search`、`product_detail`、`comments`、`seller`、`unknown_json`。不依赖固定接口名称，便于淘宝接口变化时保留原始证据。

敏感字段脱敏包括请求/响应头中的 `Cookie`、`Set-Cookie`、`Authorization`、`x-token`，以及 URL 中的 token/sign 参数。Cookie 仅注入浏览器上下文，不写数据库、日志或导出文件。

## 账号与 Cookie

兼容以下 Cookie 文件格式：`name=value; ...`、Netscape 文件、JSON Cookie 数组和包含 `cookies` 数组的 JSON 对象。测试账号使用项目根目录的 `cookies.txt`；多账号目录默认为 `cookies/accounts/`，例如 `account_01.txt`。

每个账号拥有独立浏览器实例和上下文。账号池按可用状态、最近使用时间和冷却时间轮换账号，不在账号之间共享 Cookie、storage 或页面。

## 风控与错误处理

### 账号级错误

登录失效、验证码/滑块、人机验证、风控页面、连续 401/403/429、关键登录 Cookie 缺失时，将账号标记 `paused`，记录原因和页面证据摘要，当前任务重新排队并继续其他账号。不自动尝试破解挑战。

### 任务级错误

单页超时、详情不存在、响应为空或解析失败时进行有限固定次数重试；超过上限标记 `failed`，保留脱敏错误和抓包证据。

### 系统级错误

浏览器启动失败、数据库错误或依赖缺失时，先写入运行边界并安全退出，不删除已有数据。

## CLI

```powershell
# 关键词模式
python -m src.taobao.browser.cli --db data/taobao_browser_crawler.db --cookie-dir cookies/accounts --keyword "手机壳" --keyword "蓝牙耳机" --pages 3

# 任务表模式
python -m src.taobao.browser.cli --db data/taobao_browser_crawler.db --cookie-dir cookies/accounts --from-tasks

# 无头模式
python -m src.taobao.browser.cli --db data/taobao_browser_crawler.db --cookie-dir cookies/accounts --from-tasks --headless

# 仅搜索，不执行详情任务
python -m src.taobao.browser.cli --db data/taobao_browser_crawler.db --cookie-dir cookies/accounts --keyword "手机壳" --pages 3 --search-only
```

## 测试策略

不访问真实淘宝的单元测试覆盖 Cookie 解析与脱敏、JSON 分类和字段提取、任务状态迁移、幂等 upsert、账号轮换/暂停、随机延时范围和敏感字段清理。

浏览器集成测试使用本地 HTML/HTTP fixture，验证搜索/详情模拟 JSON 抓包、滚动/停留、风控页暂停和重启恢复。测试输出不包含 Cookie 值。

## 验收标准

- 两种输入模式都能创建、恢复和完成任务。
- 淘宝和天猫每个关键词最多处理 3 个搜索页。
- 搜索商品全部生成详情任务，成功详情不重复抓取。
- 商品、评论、商家及未分类 JSON 均可追溯到 `network_records`。
- 每账号独立浏览器上下文；账号风控只暂停该账号。
- 默认可见运行，`--headless` 可用。
- 页面间隔满足配置范围，且包含停留、滚动和鼠标轨迹。
- Cookie/Authorization 等敏感值不出现在数据库、日志和错误信息中。
- 现有项目测试与未相关工作区修改不被覆盖。
