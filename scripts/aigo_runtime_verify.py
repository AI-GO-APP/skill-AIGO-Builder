"""
aigo_runtime_verify.py — Custom App Runtime 端到端驗證

在 preview（compile 後）和 publish 後，驗證 App 實際可運行：
1. Compile 產物驗證（HTML/JS/CSS 有效性）
2. Custom Data CRUD（讀寫刪查）
3. Server Action 呼叫
4. published_vfs 與 vfs_state 一致性
"""
import json
import time
from typing import Any


def verify_compile_output(compile_result: dict) -> dict:
    """
    驗證 Compile API 回傳的產物是否有效。

    Args:
        compile_result: compile_app() 的回傳值

    Returns:
        驗證報告 dict
    """
    checks = []
    html = compile_result.get("html", "")
    js = compile_result.get("bundle_js", "")
    css = compile_result.get("css", "")

    checks.append(("compile_success", compile_result.get("success") is True))
    checks.append(("html_not_empty", len(html) > 50))
    checks.append(("html_has_doctype", "<!DOCTYPE" in html or "<!doctype" in html))
    checks.append(("html_has_root_div", 'id="root"' in html))
    checks.append(("bundle_js_not_empty", len(js) > 500))
    checks.append(("bundle_js_has_react", "React" in js or "react" in js or "createElement" in js))
    checks.append(("css_not_empty", len(css) > 50))

    all_pass = all(ok for _, ok in checks)
    return {
        "passed": all_pass,
        "checks": checks,
        "html_size": len(html),
        "js_size": len(js),
        "css_size": len(css),
    }


def verify_custom_data_crud(base_url: str, token: str, table_id: str) -> dict:
    """
    對指定 Custom Data 表執行完整 CRUD 驗證（建→讀→刪→確認刪除）。

    Args:
        base_url: API 根 URL
        token: JWT access_token
        table_id: Custom Data 表的 UUID

    Returns:
        驗證報告 dict
    """
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    checks = []
    record_id = None

    try:
        # CREATE
        resp = httpx.post(
            f"{base_url}/api/v1/data/objects/{table_id}/records",
            headers=headers,
            json={"data": {"name": f"E2E_verify_{int(time.time())}", "email": "e2e@verify.test"}},
            timeout=15,
        )
        create_ok = resp.status_code in (200, 201)
        checks.append(("create_record", create_ok))
        if create_ok:
            record_id = resp.json().get("id")
            checks.append(("create_has_id", bool(record_id)))

        # READ — 二次 GET 確認寫入
        resp2 = httpx.get(
            f"{base_url}/api/v1/data/objects/{table_id}/records",
            headers=headers, timeout=15,
        )
        records = resp2.json() if resp2.status_code == 200 else []
        found = any(r.get("id") == record_id for r in records)
        checks.append(("read_confirms_create", found))

        # DELETE
        if record_id:
            resp3 = httpx.delete(
                f"{base_url}/api/v1/data/records/{record_id}",
                headers=headers, timeout=15,
            )
            delete_ok = resp3.status_code in (200, 204)
            checks.append(("delete_record", delete_ok))

            # 二次 GET 確認刪除
            resp4 = httpx.get(
                f"{base_url}/api/v1/data/objects/{table_id}/records",
                headers=headers, timeout=15,
            )
            records_after = resp4.json() if resp4.status_code == 200 else []
            not_found = not any(r.get("id") == record_id for r in records_after)
            checks.append(("read_confirms_delete", not_found))

    except Exception as e:
        checks.append(("crud_exception", False))

    all_pass = all(ok for _, ok in checks)
    return {"passed": all_pass, "checks": checks}


def verify_server_action(base_url: str, token: str, app_id: str,
                          action_name: str, params: dict = None) -> dict:
    """
    呼叫 Server Action 並驗證回傳結果。

    Args:
        base_url: API 根 URL
        token: Builder JWT token
        app_id: App UUID
        action_name: Action 名稱
        params: 傳入 Action 的參數

    Returns:
        驗證報告 dict
    """
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    resp = httpx.post(
        f"{base_url}/api/v1/actions/apps/{app_id}/run/{action_name}",
        headers=headers,
        json={"params": params or {}},
        timeout=30,
    )

    checks = []
    checks.append(("http_200", resp.status_code == 200))

    if resp.status_code == 200:
        data = resp.json()
        checks.append(("has_execution_id", bool(data.get("execution_id"))))
        checks.append(("status_success", data.get("status") == "success"))
        checks.append(("has_result", data.get("result") is not None))
        checks.append(("no_error", data.get("error") is None))
        duration = data.get("duration_ms", 0)
        checks.append(("under_30s", duration < 30000))
    else:
        checks.append(("response_body", False))

    all_pass = all(ok for _, ok in checks)
    return {
        "passed": all_pass,
        "checks": checks,
        "response": resp.json() if resp.status_code == 200 else {"status_code": resp.status_code},
    }


def verify_publish_consistency(base_url: str, token: str, app_id: str) -> dict:
    """
    驗證 published_vfs 與 vfs_state 的一致性。

    Args:
        base_url: API 根 URL
        token: JWT access_token
        app_id: App UUID

    Returns:
        驗證報告 dict
    """
    from aigo_auth import get_app_info
    app = get_app_info(base_url, token, app_id)

    vfs = app.get("vfs_state", {})
    pvfs = app.get("published_vfs", {})
    status = app.get("status", "")
    pub_at = app.get("published_at", "")

    checks = []
    checks.append(("status_published", status == "published"))
    checks.append(("published_at_exists", bool(pub_at)))
    checks.append(("published_vfs_not_empty", len(pvfs) > 0))
    checks.append(("file_count_match", len(pvfs) == len(vfs)))

    # 逐檔比對
    if pvfs and vfs:
        vfs_paths = set(vfs.keys())
        pvfs_paths = set(pvfs.keys())
        checks.append(("paths_match", vfs_paths == pvfs_paths))

        content_match = all(pvfs.get(p) == vfs.get(p) for p in pvfs_paths)
        checks.append(("content_match", content_match))

        if vfs_paths != pvfs_paths:
            missing = vfs_paths - pvfs_paths
            extra = pvfs_paths - vfs_paths
            if missing:
                checks.append(("missing_in_published", False))
            if extra:
                checks.append(("extra_in_published", False))

    all_pass = all(ok for _, ok in checks)
    return {"passed": all_pass, "checks": checks, "vfs_files": len(vfs), "published_files": len(pvfs)}


def run_full_runtime_verification(
    base_url: str, token: str, app_id: str, slug: str,
    table_id: str = "", action_name: str = ""
) -> dict:
    """
    執行完整的 preview + publish 端到端運行驗證。

    Args:
        base_url: API 根 URL
        token: JWT token
        app_id: App UUID
        slug: App slug
        table_id: Custom Data 表 UUID（可選）
        action_name: Server Action 名稱（可選）

    Returns:
        完整驗證報告 dict
    """
    from aigo_compile import compile_app

    results = {}
    all_pass = True

    # 1. Compile 產物驗證（Preview 狀態）
    compile_result = compile_app(base_url, token, slug, dev=True)
    r1 = verify_compile_output(compile_result)
    results["compile_output"] = r1
    if not r1["passed"]:
        all_pass = False

    # 2. Publish 一致性驗證
    r2 = verify_publish_consistency(base_url, token, app_id)
    results["publish_consistency"] = r2
    if not r2["passed"]:
        all_pass = False

    # 3. Custom Data CRUD（如果提供 table_id）
    if table_id:
        r3 = verify_custom_data_crud(base_url, token, table_id)
        results["custom_data_crud"] = r3
        if not r3["passed"]:
            all_pass = False

    # 4. Server Action（如果提供 action_name）
    if action_name:
        r4 = verify_server_action(base_url, token, app_id, action_name)
        results["server_action"] = r4
        if not r4["passed"]:
            all_pass = False

    results["all_passed"] = all_pass
    return results


def format_verification_report(results: dict) -> str:
    """格式化驗證報告為可讀文字"""
    lines = []
    lines.append("═" * 55)
    lines.append("  Custom App Runtime 端到端驗證報告")
    lines.append("═" * 55)

    section_names = {
        "compile_output": "📦 Compile 產物驗證",
        "publish_consistency": "🚀 Publish 一致性",
        "custom_data_crud": "📊 Custom Data CRUD",
        "server_action": "⚡ Server Action",
    }

    for key, label in section_names.items():
        if key not in results:
            continue
        r = results[key]
        icon = "✅" if r["passed"] else "❌"
        lines.append(f"\n{icon} {label}")
        for name, ok in r["checks"]:
            flag = "  ✓" if ok else "  ✗"
            lines.append(f"  {flag} {name}")
        # 額外資訊
        if key == "compile_output":
            lines.append(f"    HTML={r.get('html_size',0):,} JS={r.get('js_size',0):,} CSS={r.get('css_size',0):,}")

    overall = "✅ 全部通過" if results.get("all_passed") else "❌ 有項目失敗"
    lines.append(f"\n{'═' * 55}")
    lines.append(f"  結果：{overall}")
    lines.append("═" * 55)
    return "\n".join(lines)
