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

白名單模組：json, math, re, datetime, httpx 等。超時 30 秒、256MB 記憶體。

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
