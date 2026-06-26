# AI GO Custom App 開發者指南（精簡版）

> 完整文件：https://www.ai-go.app/zh-TW/docs/custom-app-dev

## 1. 什麼是 Custom App

- VFS（Virtual File System）：以 JSON `{"路徑": "內容"}` 儲存原始碼
- esbuild 編譯器：React TSX → JS bundle
- Runtime 沙箱：在 Shadow DOM 隔離環境中執行
- 三種模式：Internal（組織內部）/ External（對外客戶）/ Public（匿名檢視）

## 2. 認證與連線

```http
POST https://ai-go.app/api/v1/auth/login
{"email": "...", "password": "..."}
→ {"access_token": "...", "refresh_token": "...", "expires_in": 3600}
```

所有 Builder API 需帶 `Authorization: Bearer {access_token}`。Token 有效期 1 小時。

## 3. VFS 標準檔案樹

```
package.json
src/main.tsx          ★ 入口點
src/App.tsx           路由 + Layout
src/App.css           全域樣式
src/api.ts            [SDK] Custom Data CRUD
src/db.ts             [SDK] DB Proxy
src/action.ts         [SDK] Server Action
src/data.json         [INJ] Custom Table 定義
src/db.json           [INJ] Data Reference
src/actions.json      [INJ] Action 清單
src/pages/            頁面元件
src/components/       共用元件
actions/manifest.json Action 註冊
actions/*.py          Action 實作
```

## 4. 程式碼注入 API

| 操作 | 方法 | 端點 |
|------|------|------|
| 取得 App | GET | `/api/v1/builder/apps/{slug_or_id}` |
| 局部更新 | PATCH | `/api/v1/builder/apps/{id}/source/files` |
| 刪除檔案 | DELETE | `/api/v1/builder/apps/{id}/source/files` |
| 全量覆寫 | PUT | `/api/v1/builder/apps/{id}/source` |

樂觀鎖：帶入 `expected_version`，版本不匹配回傳 409。

## 5. 編譯 API

```http
POST /api/v1/compile/compile/{slug}?dev=true
→ {"success": true, "html": "...", "bundle_js": "...", "css": "..."}
→ {"success": false, "error": "..."}
```

限制：200 檔案、1MB 單檔、30 秒超時。
External 模組（不需安裝）：react, react-dom, lucide-react, react-router-dom, react-hot-toast

## 6. 內建 SDK

### Custom Data (api.ts)

```typescript
import { listRecords, submitRecord, updateRecord, deleteRecord } from "../api";
```

### DB Proxy (db.ts)

```typescript
import { query, queryAdvanced, insert, update, remove } from "../db";
```

⚠️ `update()` 和 `insert()` 需用 `{"data": {...}}` 包裝（SDK bug）。

### Server Action (action.ts)

```typescript
import { runAction, downloadFile } from "../action";
const { data, file } = await runAction("name", params);
```

## 7. Server-Side Actions

```python
def execute(ctx):
    ctx.params          # 前端參數
    ctx.db.query(t)     # 查詢
    ctx.db.insert(t, d) # 新增
    ctx.http.call(s, e) # 外部 API
    ctx.secrets.get(k)  # 金鑰
    ctx.response.json(d)# 回應
    ctx.csv.export(r)   # CSV
```


## 8. 發布

```http
POST /api/v1/builder/apps/{app_id}/publish
{"published_assets": {}}
```

## 9. Shadow DOM CSS 規範

```css
/* ✅ 正確 */
:host, :root { --primary: #2563eb; }
html, :host { line-height: 1.5; }

/* ❌ 錯誤 */
:root { --primary: #2563eb; }
```

JS API 限制：confirm()→false, alert()→不顯示, prompt()→null。
容器必須：`height: 100vh; overflow-y: auto`。

## 10. VFS 注入規範

- 每次注入必須提供完整的檔案內容（raw string）
- 禁止字串拼接或模板佔位符
- 禁止 `// ... 省略` 之類的佔位

## 11. Custom Table API

```http
POST /api/v1/data/objects/batch
{"app_id": "...", "name": "...", "api_slug": "...", "fields": [...]}
```

欄位類型：text, number, date, relation。
api_slug：`^[a-z0-9]([a-z0-9_]*[a-z0-9])?$`。
限制：20 表/App、50 欄/表。

## 12. Storage API

- POST `/api/v1/ext/storage/upload`（multipart/form-data）
- GET `/api/v1/ext/storage/url?path={path}`
- GET `/api/v1/ext/storage/list?folder={folder}`
- DELETE `/api/v1/ext/storage/file?path={path}`

需 Custom App Token (`window.__APP_TOKEN__`)。單檔 100MB 上限。

## 13. Runtime 全域變數

| 變數 | 說明 |
|------|------|
| `window.__APP_TOKEN__` | JWT Token |
| `window.__APP_SLUG__` | App slug |
| `window.__APP_ID__` | App UUID |
| `window.__API_BASE__` | API 基底 URL |
| `window.__IS_AUTHENTICATED__` | 是否已認證 |
| `window.__IS_EXTERNAL__` | 是否為 External 模式 |

## 14. External Auth API

端點前綴：`/api/v1/custom-app-auth/{slug}/`

- POST `.../register` → 註冊
- POST `.../login` → 登入
- GET `.../me` → 當前用戶
- POST `.../refresh` → 刷新 Token
- POST `.../logout` → 登出

Auth SDK：`window.__auth__.login()`, `.register()`, `.logout()`, `.getToken()`

## 15. Public 匿名 API

啟用條件：`allow_anonymous_access=true` + `is_public_readable=true`

- GET `/api/v1/pub/data/{slug}/objects`
- GET `/api/v1/pub/data/{slug}/objects/{table}/records`
- POST `/api/v1/pub/proxy/{slug}/{table}/query`

Rate Limit：120 次/分鐘 per IP。

## 16. 套件管理

Runtime 內建：react ^18.x, react-dom ^18.x, react-router-dom ^6.x, lucide-react latest, react-hot-toast latest
不支援：CSS Modules, Tailwind, styled-components, @mui/material, 動態 import, Node.js 原生模組

## 17. 常見問題速查

| 問題 | 解法 |
|------|------|
| 白屏 | 檢查 main.tsx 掛載和 App.css import |
| 路由不動 | HashRouter，非 BrowserRouter |
| 無法捲動 | Layout height:100vh + overflow-y:auto |
| CSS 變數無效 | :host, :root 雙選擇器 |
| db.update 400 | {"data": {...}} 包裝 |
| 401 | Token 過期，重新登入 |
| 409 | VFS 版本衝突，重新 GET |
| 423 | 有待審核發布，等待/取消 |

## 18. 核心策略：app_domain 標籤

### 概念

每個 Custom App 在寫入 SaaS 表（Data Reference）時，必須在 `custom_data` JSONB 中標記 `app_domain`，
用於標識該筆資料由哪個 App 建立，實現多 App 共用同一張表但資料隔離。

### 格式

- snake_case，如 `patent_os`、`crm_leads`、`inventory_mgr`
- 記錄在 `.aigo/config.json` 的 `app_domain` 欄位

### 寫入規範

所有 `db.insert()` 和 `db.update()` 呼叫，payload 的 `custom_data` 中必須包含：

```json
{
  "custom_data": {
    "app_domain": "<config 中的值>",
    "...其他欄位": "..."
  }
}
```

### 讀取規範

讀取 SaaS 表資料時，應用 `app_domain` 過濾，僅處理本 App 建立的資料：

```typescript
const myRecords = allRecords.filter(
  r => r.custom_data?.app_domain === APP_DOMAIN
);
```

### 實例

```json
{
  "name": "AI溢流防護裝置",
  "custom_data": {
    "app_domain": "patent_os",
    "case_no": "IP-E2E-FULL-001",
    "status": "待檢索",
    "country": "TW",
    "patent_type": "發明",
    "inventor": "王大明、李小華"
  }
}
```

## 19. Data Reference vs Custom Table 選擇指引

### 決策流程

1. 用 Refs API 查詢所有可用 SaaS 表（見 §20），確認是否有結構相似的表
2. 用 Refs API 查詢該表欄位，確認是否有 `custom_data`（JSONB）欄位可擴充
3. 確認權限（read/create/update/delete）是否滿足需求
4. 在 AI GO Builder 後台將選定的表加入 Data Reference，使其出現在 `db.json`

### 選擇矩陣

| 條件 | 選擇 | 說明 |
|------|------|------|
| SaaS 表有適合的主表結構 + JSONB 欄位 | **Data Reference** | 用 `custom_data` 存放 App 特有資料 |
| SaaS 表結構部分適用 | **Data Reference + Custom Table** | 主資料用 SaaS 表，輔助資料用 Custom Table |
| 需要完全自訂的獨立資料結構 | **Custom Table** | 最後手段 |
| 需要與其他 SaaS 功能整合 | **Data Reference**（優先） | 與看板、專案等功能共用資料 |

### SaaS 表常見結構

SaaS 表通常包含以下標準欄位：

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | UUID | 主鍵 |
| `name` | VARCHAR | 名稱 |
| `active` | BOOLEAN | 啟用狀態 |
| `description` | TEXT | 描述 |
| `custom_data` | JSONB | **App 擴充資料**（app_domain + 自訂欄位） |
| `user_id` | UUID | 負責人 |
| `customer_id` | UUID | 客戶 |
| `stage_id` | UUID | 階段 |
| `created_at` | TIMESTAMP | 建立時間 |
| `updated_at` | TIMESTAMP | 更新時間 |

## 20. Data Reference 探索 API

用於在開發規劃階段（Phase 1.5）探索所有可用的 SaaS 表，決定哪些表適合作為 Data Reference。

### 20.1 查詢可用資料表清單

```http
GET /api/v1/refs/available-tables
Authorization: Bearer {access_token}
```

功能：列出資料庫中所有目前可以被 Custom App 引用的資料表名稱與備註。自動排除系統敏感黑名單表。

權限限制：帳號必須擁有 `builder.access` 權限。

回應範例：

```json
[
  {"name": "customers", "comment": "客戶/夥伴"},
  {"name": "sale_orders", "comment": "銷售訂單"},
  {"name": "project_projects", "comment": "專案"},
  {"name": "project_tasks", "comment": "專案任務"},
  {"name": "account_invoices", "comment": "發票"},
  {"name": "product_templates", "comment": "產品模板"}
]
```

### 20.2 查詢特定資料表欄位

```http
GET /api/v1/refs/tables/{table_name}/columns
Authorization: Bearer {access_token}
```

功能：列出指定資料表下可用的欄位資訊（含欄位名稱、資料型別、是否可為 Null、是否為系統欄位）。

權限限制：帳號必須擁有 `builder.access` 權限。

回應範例：

```json
[
  {"name": "id", "type": "UUID", "nullable": false, "is_system": true},
  {"name": "tenant_id", "type": "UUID", "nullable": false, "is_system": true},
  {"name": "name", "type": "VARCHAR(255)", "nullable": false, "is_system": false},
  {"name": "email", "type": "VARCHAR(255)", "nullable": true, "is_system": false},
  {"name": "phone", "type": "VARCHAR(50)", "nullable": true, "is_system": false},
  {"name": "custom_data", "type": "JSONB", "nullable": true, "is_system": false},
  {"name": "created_at", "type": "TIMESTAMP", "nullable": false, "is_system": true},
  {"name": "updated_at", "type": "TIMESTAMP", "nullable": false, "is_system": true}
]
```

欄位說明：

| 欄位 | 說明 |
|------|------|
| `name` | 欄位名稱 |
| `type` | 資料型別（UUID, VARCHAR, TEXT, INTEGER, BOOLEAN, NUMERIC, JSONB, DATE, TIMESTAMP 等） |
| `nullable` | 是否可為 NULL |
| `is_system` | 是否為系統欄位（id, tenant_id, created_at, updated_at 等，不可手動寫入） |

### 20.3 典型使用流程

```
Phase 1.5 實作計畫時：

1. GET /api/v1/refs/available-tables
   → 取得所有可用 SaaS 表清單

2. 對每個候選表 GET /api/v1/refs/tables/{name}/columns
   → 確認欄位結構、是否有 custom_data (JSONB)

3. 決定資料架構：哪些需求用 SaaS 表、哪些用 Custom Table

4. 在 AI GO Builder 後台將選定的 SaaS 表加入 Data Reference
   → 表即出現在 VFS 的 db.json 中

5. 重新 Phase 0 Review 確認 db.json 已包含所需的表
```

> **重要**：`available-tables` 僅列出可用表名，實際將表加入 App 的 Data Reference 需在 AI GO Builder 後台操作。
> 加入後，該表的完整 schema 和資料會自動注入到 `src/db.json`。
