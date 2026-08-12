# JD 黄小米商品评论采集设计

**日期：** 2026-08-10

## 目标

从 `data/jd_huangxiaomi_item_details.sqlite3` 的 `jd_item_state.status='success'` 读取已成功商品，为每个商品调用固定 `page=1` 的评论接口，并保存完整响应和可恢复状态。

## 接口和凭证

- URL：`http://115.29.242.83:8000/jdpl/get_item`
- 参数：`token`、`itemid`、`page=1`
- `.env` 保存：`JD_COMMENT_TOKEN`
- 运行日志、异常、测试和数据库均不得输出 token。

## 数据库

独立库 `data/jd_huangxiaomi_comments.sqlite3`：

- `jd_item_comments(itemid PRIMARY KEY, page, raw_json, created_at, updated_at)`
- `jd_comment_state(itemid PRIMARY KEY, status, last_error, created_at, updated_at)`

状态为 `pending`、`success` 或 `error`。默认跳过 `success` 项；`--reset-items` 才会重新请求。每项仅固定页码 1；可设置固定上限重试和延迟。

## 脚本

新增 `src/jd/direct/comment.py`，并通过 `src/jd_comment_crawler.py` 提供兼容入口。CLI 从详情数据库加载成功 ID；支持 `--detail-db`、`--db`、`--limit`、`--delay`、`--retries`、`--reset-items`。

## 验证

单元测试覆盖请求 URL、状态持久化、续跑跳过、错误继续及读取成功详情 ID。部署时先用 `--limit 1` 真实请求验证响应，再将完整 2,431 个成功商品作为后台可恢复任务运行。
