import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const zh = {
  title: "云析 API", nav: { products: "接口能力", docs: "开发文档", console: "控制台", profiles: "凭据与代理", login: "登录", register: "免费开始" },
  hero: { eyebrow: "淘宝 · 天猫 · 京东数据接口", title: "让每一次商品数据请求，都清晰可控。", description: "为团队提供安全的异步爬虫 API、加密凭据档案与可追踪任务结果。", primary: "进入控制台", secondary: "查看接口文档" },
  landing: { trust: "凭据 AES-256-GCM 加密 · 异步任务 · 细粒度 API Token", supported: "已支持的平台与接口", supportedText: "统一的任务、凭据与代理工作流；按需接入各平台数据能力。", usage: "三步开始调用", step1: "注册并获取访问令牌", step2: "保存 Cookie 或代理配置档", step3: "提交任务并轮询结果", apiFirst: "为开发者而建", apiFirstText: "标准 REST 接口、OpenAPI 文档、请求示例和稳定错误码，前端与自动化流程都可直接使用。" },
  common: { loading: "加载中…", save: "保存", submit: "提交任务", logout: "退出登录", copy: "复制", required: "必填", optional: "可选", cancel: "取消", error: "请求失败", success: "操作成功", language: "English" },
  auth: { loginTitle: "登录控制台", registerTitle: "创建你的账号", email: "邮箱", password: "密码", login: "登录", register: "注册并开始试用", noAccount: "还没有账号？", haveAccount: "已有账号？", trial: "新账户默认拥有 5 次成功任务试用额度。" },
  dashboard: { title: "控制台", greeting: "开始新的数据任务", remaining: "剩余试用次数", formal: "正式账户", trial: "试用账户", run: "立即调用", recent: "最近任务", noJobs: "尚未提交任务。请选择一个接口开始调用。", completed: "任务已完成", failed: "任务失败" },
  playground: { title: "接口调试台", description: "选择接口，填写 JSON 参数，提交后自动追踪任务状态。", choose: "选择爬虫接口", input: "请求参数", credential: "Cookie 配置档", proxy: "代理配置档", none: "不使用", result: "任务结果", queued: "已进入队列", running: "正在执行", succeeded: "执行成功", failed: "执行失败", loginRequired: "请先登录后再调用接口。", invalidJson: "请求参数必须是有效的 JSON 对象。" },
  profiles: { title: "凭据与代理", description: "Cookie 和代理密码仅在提交时发送，并以 AES-256-GCM 加密保存；保存后不会再次展示。", credential: "Cookie 配置档", proxy: "代理配置档", createCredential: "新增 Cookie 配置", createProxy: "新增代理配置", name: "配置名称", platform: "平台", purpose: "用途说明", cookie: "Cookie", protocol: "协议", host: "主机", port: "端口", username: "用户名", proxyPassword: "密码", emptyCredentials: "暂无 Cookie 配置档", emptyProxies: "暂无代理配置档" },
  docs: { title: "开发者文档", subtitle: "五类接口均使用统一的异步任务协议。", authentication: "认证", authenticationText: "注册后使用 JWT，或在后续版本的 Token 管理页创建长期 API Token。请求头使用 Authorization: Bearer <token>。", submit: "提交任务", poll: "查询结果", examples: "接口与示例", response: "成功响应", errors: "常见错误" },
};

const en = {
  title: "Yunxi API", nav: { products: "Products", docs: "Docs", console: "Console", profiles: "Profiles", login: "Log in", register: "Get started" },
  hero: { eyebrow: "TAOBAO · TMALL · JD DATA APIs", title: "Every product data request, clearly in control.", description: "Secure asynchronous crawler APIs, encrypted profiles, and traceable job results for your team.", primary: "Open console", secondary: "Read docs" },
  landing: { trust: "AES-256-GCM encryption · Async jobs · Scoped API tokens", supported: "Supported platforms and APIs", supportedText: "One workflow for jobs, profiles, and proxies across data sources.", usage: "Three steps to start", step1: "Register and obtain access", step2: "Save cookie or proxy profiles", step3: "Submit and poll a job", apiFirst: "Designed for developers", apiFirstText: "REST endpoints, OpenAPI docs, examples, and stable error codes for products and automations." },
  common: { loading: "Loading…", save: "Save", submit: "Submit job", logout: "Log out", copy: "Copy", required: "Required", optional: "Optional", cancel: "Cancel", error: "Request failed", success: "Saved", language: "中文" },
  auth: { loginTitle: "Sign in to console", registerTitle: "Create your account", email: "Email", password: "Password", login: "Log in", register: "Register and start", noAccount: "New here?", haveAccount: "Already have an account?", trial: "New accounts receive five successful job trials." },
  dashboard: { title: "Console", greeting: "Start a new data job", remaining: "Trials remaining", formal: "Formal account", trial: "Trial account", run: "Run crawler", recent: "Recent jobs", noJobs: "No jobs yet. Select an API to get started.", completed: "Job completed", failed: "Job failed" },
  playground: { title: "API playground", description: "Choose an API, enter JSON input, and track the asynchronous job.", choose: "Crawler API", input: "Request input", credential: "Cookie profile", proxy: "Proxy profile", none: "None", result: "Job result", queued: "Queued", running: "Running", succeeded: "Succeeded", failed: "Failed", loginRequired: "Please log in before calling an API.", invalidJson: "Input must be a valid JSON object." },
  profiles: { title: "Credentials and proxies", description: "Cookies and proxy passwords are sent only to save, encrypted with AES-256-GCM, and never shown again.", credential: "Cookie profiles", proxy: "Proxy profiles", createCredential: "Add cookie profile", createProxy: "Add proxy profile", name: "Profile name", platform: "Platform", purpose: "Purpose", cookie: "Cookie", protocol: "Protocol", host: "Host", port: "Port", username: "Username", proxyPassword: "Password", emptyCredentials: "No cookie profiles", emptyProxies: "No proxy profiles" },
  docs: { title: "Developer docs", subtitle: "All five APIs share one asynchronous job protocol.", authentication: "Authentication", authenticationText: "Use the JWT returned at login; a long-lived API token manager follows in the console. Send Authorization: Bearer <token>.", submit: "Submit a job", poll: "Poll a result", examples: "APIs and examples", response: "Success response", errors: "Common errors" },
};

i18n.use(initReactI18next).init({ lng: "zh-CN", fallbackLng: "zh-CN", interpolation: { escapeValue: false }, resources: { "zh-CN": { translation: zh }, "en-US": { translation: en } } });

export default i18n;
