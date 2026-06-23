"""AI GO Custom App 現有程式碼 Review 工具"""
import json
import re
from typing import Any

# SDK 保護清單
SDK_FILES = {"src/api.ts", "src/db.ts", "src/action.ts"}
INJECTED_FILES = {"src/data.json", "src/db.json", "src/actions.json"}
PROTECTED_FILES = SDK_FILES | INJECTED_FILES


def review_app(base_url: str, token: str, app_id: str) -> dict:
    """取得 App 資訊並執行完整 Review"""
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(f"{base_url}/api/v1/builder/apps/{app_id}", headers=headers, timeout=30)
    resp.raise_for_status()
    app_info = resp.json()
    analysis = analyze_vfs(app_info.get("vfs_state", {}))
    return {"app_info": app_info, "analysis": analysis}


def analyze_vfs(vfs_state: dict) -> dict:
    """分析 VFS 結構"""
    files_info = []
    for path, content in sorted(vfs_state.items()):
        tag = "[SDK]" if path in SDK_FILES else "[INJ]" if path in INJECTED_FILES else "[APP]"
        files_info.append({"path": path, "size": len(content), "tag": tag})

    # 解析路由
    routes = []
    app_tsx = vfs_state.get("src/App.tsx", "")
    for m in re.finditer(r'path=["\'](/[^"\']*)["\']', app_tsx):
        routes.append(m.group(1))
    for m in re.finditer(r'path=["\'](\*)["\']', app_tsx):
        routes.append(m.group(1))

    # 解析 manifest
    pages = []
    manifest_str = vfs_state.get("src/pages/_manifest.json", "")
    if manifest_str:
        try:
            manifest = json.loads(manifest_str)
            pages = manifest.get("pages", [])
        except json.JSONDecodeError:
            pass

    # 解析 Custom Tables
    tables = []
    data_json_str = vfs_state.get("src/data.json", "")
    if data_json_str and data_json_str != "{}":
        try:
            data_json = json.loads(data_json_str)
            for name, info in data_json.items():
                tables.append({
                    "name": name,
                    "slug": info.get("slug", ""),
                    "fields_count": len(info.get("fields", [])),
                    "records_count": len(info.get("records", [])),
                })
        except json.JSONDecodeError:
            pass

    # 解析 Actions
    actions = []
    actions_manifest = vfs_state.get("actions/manifest.json", "")
    if actions_manifest:
        try:
            am = json.loads(actions_manifest)
            for name, info in am.items():
                actions.append({"name": name, "description": info.get("description", "")})
        except json.JSONDecodeError:
            pass

    # CSS 檢查
    css_content = vfs_state.get("src/App.css", "")
    css_issues = check_css_compliance(css_content)

    # 路由類型偵測
    router_type = "HashRouter" if "HashRouter" in app_tsx else "BrowserRouter" if "BrowserRouter" in app_tsx else "none"

    return {
        "files": files_info,
        "total_files": len(files_info),
        "routes": routes,
        "router_type": router_type,
        "pages": pages,
        "tables": tables,
        "actions": actions,
        "css_issues": css_issues,
    }


def check_css_compliance(css_content: str) -> list[str]:
    """檢查 CSS 是否符合 Shadow DOM 規範"""
    issues = []
    lines = css_content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if re.match(r'^:root\s*\{', stripped) and ':host' not in stripped:
            prev_line = lines[i - 2].strip() if i >= 2 else ""
            if ':host' not in prev_line:
                issues.append(f"第 {i} 行: ':root {{' 缺少 ':host' 配對 → 應改為 ':host, :root {{'")
        if re.match(r'^html\s*\{', stripped) and ':host' not in stripped:
            prev_line = lines[i - 2].strip() if i >= 2 else ""
            if ':host' not in prev_line:
                issues.append(f"第 {i} 行: 'html {{' 缺少 ':host' 配對 → 應改為 'html, :host {{'")
    return issues


def format_review_report(app_info: dict, analysis: dict) -> str:
    """格式化 Review 報告"""
    lines = []
    lines.append("═" * 55)
    lines.append("  AI GO Custom App Review 報告")
    lines.append("═" * 55)
    lines.append("")
    lines.append("📋 App 元資料")
    lines.append(f"  名稱：{app_info.get('name', 'N/A')}")
    lines.append(f"  ID：{app_info.get('id', 'N/A')}")
    lines.append(f"  Slug：{app_info.get('slug', 'N/A')}")
    lines.append(f"  狀態：{app_info.get('status', 'N/A')} | 模式：{app_info.get('access_mode', 'N/A')}")
    lines.append(f"  VFS 版本：{app_info.get('vfs_version', 'N/A')} | 檔案數：{analysis['total_files']}")
    lines.append("")
    lines.append("📁 VFS 檔案結構")
    for f in analysis["files"]:
        lines.append(f"  {f['tag']} {f['path']} ({f['size']:,} chars)")
    lines.append("")
    if analysis["routes"]:
        lines.append(f"🗺️ 路由結構（{analysis['router_type']}，{len(analysis['routes'])} 條路由）")
        for r in analysis["routes"]:
            lines.append(f"  {r}")
        lines.append("")
    if analysis["tables"]:
        lines.append(f"📊 Custom Tables（{len(analysis['tables'])} 張）")
        for t in analysis["tables"]:
            lines.append(f"  {t['slug']} ({t['fields_count']} 欄位, {t['records_count']} 記錄) — {t['name']}")
        lines.append("")
    if analysis["actions"]:
        lines.append(f"⚡ Server Actions（{len(analysis['actions'])} 個）")
        for a in analysis["actions"]:
            lines.append(f"  {a['name']} — {a['description']}")
        lines.append("")
    css_status = "✅ 通過" if not analysis["css_issues"] else "❌ 有問題"
    lines.append(f"🎨 CSS 規範 {css_status}")
    for issue in analysis["css_issues"]:
        lines.append(f"  ⚠️ {issue}")
    lines.append("")
    lines.append("═" * 55)
    return "\n".join(lines)
