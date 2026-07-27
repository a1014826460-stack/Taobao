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

## Crawler contracts

Each crawler is submitted through `POST /api/v1/crawls/{crawler}` and returns
the same `202` job response. The job result is available only after the job
status is `succeeded`.

### `taobao.item`

Uses the server-side `FANB_API_KEY` and `FANB_API_SECRET` gateway settings.

```json
{"input":{"item_id":"652874751412"},"proxy_profile_id":null}
```

`item_id` (or `num_iid`) is required. Optional inputs: `item_api`
(`item_get` or `item_get_pro`), `is_promotion`, and `lang`.

### `taobao.shop`

```json
{"input":{"shop_id":"517932711","seller_id":"2200684271326","page":1}}
```

`shop_id` and `seller_id` are required. `page` defaults to 1; `sort`, `cache`,
and `lang` are optional.

### `tmall.sku-adjust`

```json
{"input":{"sku_id":"6277426546603"},"credential_profile_id":1}
```

`sku_id` and a Tmall Cookie credential profile are required. The response is
the signed MTop payload, including `skuCore.sku2info` when supplied upstream.

### `jd.item`

Uses the server-side `FANB_API_KEY` and `FANB_API_SECRET` gateway settings.

```json
{"input":{"item_id":"10025990353889"}}
```

`item_id`, `sku_id`, or `num_iid` is required. `cache` and `lang` are optional.

### `jd.ware-business`

```json
{
  "input": {
    "sku_id":"10207466352379",
    "signed_url":"https://api.m.jd.com/?functionId=pc_detailpage_wareBusiness&..."
  },
  "credential_profile_id":2
}
```

`signed_url` must be a freshly captured `https://api.m.jd.com/` wareBusiness
URL. Its signature is browser-session-bound and expires; the service does not
persist or fabricate device fingerprints. A JD Cookie profile is optional but
may be needed by the upstream response.

### Job response and result

```json
{"id":42,"crawler":"tmall.sku-adjust","status":"queued","error_code":null,"error_message":null,"created_at":"2026-07-23T10:00:00Z"}
```

Poll `GET /api/v1/jobs/42`; then fetch `GET /api/v1/jobs/42/result`:

```json
{"id":42,"status":"succeeded","result":{"http_status":200,"payload":{}}}
```

## Limits and errors

Trial tokens are limited to 10 requests/minute; formal users are limited to
60/minute. New users receive five successful job trials. `RATE_LIMITED`,
`TRIAL_QUOTA_EXHAUSTED`, `PROFILE_NOT_FOUND`, and `CRAWLER_FAILED` are stable
error codes. Failed and cancelled jobs do not consume trial quota.

## 中文说明

通过注册、登录获取 JWT，或创建只显示一次的 `cap_` API Token。Cookie 和代理配置会
加密保存；调用任务接口只传配置 ID。提交任务后轮询状态，再读取结果。试用账号有 5 次
成功任务额度，限制为每分钟 10 次；正式账号每分钟 60 次。
