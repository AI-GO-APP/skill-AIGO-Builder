---
name: aigo-builder
description: >
  AI GO Custom App 開發者工具。引導用戶完成帳號設定、現有 Code Review、專案建立、
  前端 (React 18 + TypeScript) 與後端 (Python Server-Side Actions) 開發、
  雲端部署及 E2E 驗證的完整流程。全域安裝，可跨多專案使用。
---

# AI GO Custom App Builder

本 Skill 協助 AI Agent 開發 AI GO Custom App。支援 Antigravity / Claude Code / Cursor。

## Phase 0：Review 現有 Code（★ 強制步驟）

> **每次開始任何開發工作前，必須先執行此步驟。**

### 流程

1. 確認 `.aigo/config.json` 中 `email` 和 `app_id` 已設定
2. 請用戶臨時提供密碼（不儲存）
3. 呼叫 Login API 取得 JWT
4. `GET /api/v1/builder/apps/{app_id}` 取得完整 App 資訊含 VFS
5. 分析 VFS 結構並輸出 Review 報告：
   - 列出所有檔案及大小
   - 標記 SDK 檔案 `[SDK]`（不可修改：api.ts, db.ts, action.ts）
   - 標記 Runtime 注入檔 `[INJ]`（不可修改：data.json, db.json, actions.json）
   - 解析 App.tsx 路由結構
   - 解析 _manifest.json 頁面清單
   - 解析 data.json Custom Table 定義
   - 解析 actions/manifest.json
   - 檢查 App.css Shadow DOM 相容性
6. **確認已完全理解現有結構後，才可進入開發**

可使用 `scripts/aigo_review.py` 的 `review_app()` 和 `format_review_report()` 輔助。

## Phase 1：環境設定

### 配置檔 `.aigo/config.json`

```json
{
  "base_url": "https://ai-go.app",
  "email": "",
  "app_id": "",
  "app_slug": "",
  "app_name": "",
  "access_mode": "internal"
}
```

### 設定流程

1. 檢查專案目錄下 `.aigo/config.json` 是否存在
2. 不存在 → 建立骨架（可用 `scripts/aigo_auth.py` 的 `init_config()`）
3. 引導用戶：
   - 前往 AI GO 後台 (https://ai-go.app/dashboard)
   - 確認帳號具備 `builder.access` 權限
   - 進入 Builder → Custom Apps → 記下 App 的 UUID (`app_id`)
   - 填入 `.aigo/config.json` 的 `email` 和 `app_id`
4. 驗證連線：用戶臨時輸入密碼 → Login API → GET App → 自動回填 `slug`、`name`、`access_mode`
5. **密碼不儲存到任何檔案中**

## Phase 2：專案腳手架

基於 Phase 0 Review 結果決定策略：

- **VFS 為空**：生成全新專案結構
  - 詢問用戶：單頁 App 或多頁 App？
  - 單頁：直接渲染，不使用 Router
  - 多頁：HashRouter + Sidebar 導航
  - 可用 `scripts/aigo_scaffold.py` 的 `scaffold_new_project()`

- **VFS 有內容**：下載到本地進行增量開發
  - 將雲端 VFS 下載為本地檔案結構
  - 保留現有所有程式碼
  - 可用 `scripts/aigo_scaffold.py` 的 `download_vfs_to_local()`

## Phase 3：開發指引

### 核心規則（必須嚴格遵守）

1. **框架**：React 18 + TypeScript
2. **路由**：多頁用 `HashRouter`（禁用 `BrowserRouter`）；單頁可不用 Router
3. **CSS**：全域 `App.css`，不支援 CSS Modules / Tailwind
4. **CSS 變數**：必須用 `:host, :root { }` 雙選擇器
5. **HTML 重設**：必須用 `html, :host { }` 雙選擇器
6. **入口點**：必須是 `src/main.tsx`，且 `import "./App.css"`
7. **Layout**：最外層容器必須 `height: 100vh; overflow-y: auto`
8. **Runtime 模組**：react, react-dom, lucide-react, react-router-dom, react-hot-toast 由 Runtime 提供，不可自行安裝
9. **SDK 不可修改**：api.ts, db.ts, action.ts, data.json, db.json, actions.json
10. **Server-Side Actions**：Python，放在 `actions/` 目錄，定義 `execute(ctx)` 函式
11. **Shadow DOM 限制**：`confirm()` / `alert()` / `prompt()` 不可用 → 改用 React state 或 react-hot-toast
12. **db.update() Bug**：需用 `{"data": {...}}` 包裝 payload（直接 fetch，不走 SDK）
13. **db.insert() Bug**：同上，需用 `{"data": {...}}` 包裝
14. **VFS 限制**：最多 200 檔案、單檔 ≤ 1MB、編譯超時 30 秒
15. **完整程式碼原則**：每次更新 VFS 檔案必須提供 100% 完整內容，禁止 `// ...省略` 佔位符
16. **不支援動態 import**：`import()` 語法不支援（lazy loading 除外，esbuild 支援 code splitting）
17. **不支援 Node.js 原生模組**：fs, path, crypto 等無法使用

### Server-Side Action 撰寫

```python
def execute(ctx):
    # ctx.params — 前端傳入的參數
    # ctx.db.query(table, limit=N) — 查詢
    # ctx.db.insert(table, data) — 新增
    # ctx.http.call(service, endpoint) — 外部 API
    # ctx.secrets.get(key) — 金鑰
    # ctx.response.json(data) — 回應
    # ctx.csv.export(rows) — CSV 匯出
    data = ctx.params.get("key", "default")
    ctx.response.json({"result": data})
```

安全限制：白名單模組（json, math, re, datetime, httpx 等）、禁止 exec/eval/open、超時 30 秒。

### 前端呼叫 Action

```typescript
import { runAction, downloadFile } from "../action";
const { data, file } = await runAction("my_action", { key: "value" });
if (file) downloadFile(file);
```

## Phase 4：部署

### 流程

1. **同步 VFS**：讀取本地檔案 → PATCH `/api/v1/builder/apps/{id}/source/files`
2. **編譯**：POST `/api/v1/compile/compile/{slug}?dev=true`
3. **編譯失敗**：解析錯誤 → 嘗試自動修復 → 重新同步 → 重新編譯（最多 5 次）
4. **編譯成功**：POST `/api/v1/builder/apps/{id}/publish`

### 樂觀鎖

- GET App 時記錄 `vfs_version`
- PATCH 時帶入 `expected_version`
- 409 → 重新 GET → 合併 → 重試

### 自動修復策略

| 偵測問題 | 自動修復 |
|---------|--------|
| `:root {` 無 `:host` | → `:host, :root {` |
| `html {` 無 `:host` | → `html, :host {` |
| BrowserRouter | → HashRouter |
| 缺少 `import "./App.css"` | → 在 main.tsx 頂部加入 |

可使用 `scripts/aigo_sync.py`、`aigo_compile.py`、`aigo_publish.py`。

## Phase 5：E2E 驗證

6 大測試群組：

1. **編譯驗證** — 確認 `success: true`
2. **Custom Data CRUD** — 建表 → 寫入 → 查詢 → 更新 → 刪除 → 清理
3. **Server Action** — 注入測試 Action → 編譯 → 呼叫 → 清理
4. **發布驗證** — 確認 `status: published`
5. **External Auth**（可選）— 註冊 → 登入 → 取得用戶 → 登出
6. **Public 匿名**（可選）— 設定公開 → pub/ API 讀取 → 確認寫入被拒

可使用 `scripts/aigo_e2e.py`。

## 錯誤處理速查

| 錯誤 | 解法 |
|------|------|
| 白屏 | 確認 `src/main.tsx` 正確掛載 React |
| 路由不動 | 使用 `HashRouter`，不可用 `BrowserRouter` |
| 頁面無法捲動 | Layout 需 `height: 100vh; overflow-y: auto` |
| CSS 不生效 | 確認 `main.tsx` 中 `import "./App.css"` |
| CSS 變數遺失 | `:root` 改為 `:host, :root` |
| `db.update()` 400 | 用 `{"data": {...}}` 包裝 payload |
| `db.ts` 500 | 確認 Data Reference 已建立並發布 |
| 401 | Token 過期，重新登入 |
| 409 Conflict | VFS 版本衝突，重新 GET 後重試 |
| 423 Locked | 有待審核的發布，等待或取消 |
| Action 超時 | 控制在 30 秒內 |
| pub/ API 403 | 確認 `allow_anonymous_access=true` |

## 參考文件

詳細 API 規格和進階功能請查閱 `references/custom-app-dev-guide.md`。
