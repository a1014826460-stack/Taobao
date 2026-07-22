# Crawler API Reference

## Authentication

Register with `POST /api/v1/auth/register`, then log in with
`POST /api/v1/auth/login`. Send the returned access token as
`Authorization: Bearer <JWT>`. Create automation credentials at
`POST /api/v1/tokens`; the returned `cap_` value is shown once only.

## Profiles

Create a named, encrypted Cookie profile:

```json
POST /api/v1/profiles/credentials
{"name":"tmall-main","platform":"tmall","purpose":"price checks","cookie":"_m_h5_tk=..."}
```

Create HTTP, HTTPS, or SOCKS5 proxy profiles at `/api/v1/profiles/proxies`.
Responses never contain Cookie, proxy username, or proxy password plaintext.

## Queue a crawler job

```json
POST /api/v1/crawls/tmall.sku-adjust
{
  "input":{"sku_id":"6277426546603"},
  "credential_profile_id":1,
  "proxy_profile_id":null
}
```

The API returns `202` and a job record. Poll `GET /api/v1/jobs/{id}`, then
read `GET /api/v1/jobs/{id}/result` after `status` becomes `succeeded`.

Supported crawler names: `taobao.item`, `taobao.shop`, `tmall.sku-adjust`,
`jd.item`, and `jd.ware-business`.

## Limits and errors

Trial tokens are limited to 10 requests/minute; formal users are limited to
60/minute. New users receive five successful job trials. `RATE_LIMITED`,
`TRIAL_QUOTA_EXHAUSTED`, `PROFILE_NOT_FOUND`, and `CRAWLER_FAILED` are stable
error codes. Failed and cancelled jobs do not consume trial quota.

## 中文说明

通过注册、登录获取 JWT，或创建只显示一次的 `cap_` API Token。Cookie 和代理配置会
加密保存；调用任务接口只传配置 ID。提交任务后轮询状态，再读取结果。试用账号有 5 次
成功任务额度，限制为每分钟 10 次；正式账号每分钟 60 次。
