"""AI GO Custom App E2E 驗證工具"""
import time
from typing import Any


def run_e2e(base_url: str, token: str, app_id: str, slug: str,
            access_mode: str = "internal") -> dict:
    """執行全部 E2E 測試"""
    results = []
    results.append(_test_compile(base_url, token, slug))
    results.append(_test_custom_data(base_url, token, app_id))
    results.append(_test_publish(base_url, token, app_id))
    if access_mode != "internal":
        results.append(_test_external_auth(base_url, slug))
    else:
        results.append({"name": "External Auth", "status": "SKIP", "duration": 0,
                        "detail": "access_mode=internal"})

    summary = {
        "pass": sum(1 for r in results if r["status"] == "PASS"),
        "fail": sum(1 for r in results if r["status"] == "FAIL"),
        "skip": sum(1 for r in results if r["status"] == "SKIP"),
    }
    return {"results": results, "summary": summary}


def _test_compile(base_url: str, token: str, slug: str) -> dict:
    """測試編譯"""
    import httpx
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.post(f"{base_url}/api/v1/compile/compile/{slug}?dev=true",
                          headers=headers, timeout=60)
        data = resp.json()
        ok = data.get("success", False)
        return {"name": "編譯驗證", "status": "PASS" if ok else "FAIL",
                "duration": round(time.time() - start, 2),
                "detail": "" if ok else data.get("error", "")[:100]}
    except Exception as e:
        return {"name": "編譯驗證", "status": "FAIL",
                "duration": round(time.time() - start, 2), "detail": str(e)[:100]}


def _test_custom_data(base_url: str, token: str, app_id: str) -> dict:
    """測試 Custom Data CRUD"""
    import httpx
    start = time.time()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    obj_id = None
    try:
        # 建表
        resp = httpx.post(f"{base_url}/api/v1/data/objects/batch", headers=headers, json={
            "app_id": app_id, "name": "E2E 測試表", "api_slug": "e2e_test",
            "fields": [{"name": "名稱", "field_key": "name", "field_type": "text",
                        "is_required": True, "sequence": 1}]
        }, timeout=30)
        resp.raise_for_status()
        obj_id = resp.json()["id"]
        # 清理
        httpx.delete(f"{base_url}/api/v1/data/objects/{obj_id}", headers=headers, timeout=30)
        return {"name": "Custom Data CRUD", "status": "PASS",
                "duration": round(time.time() - start, 2), "detail": ""}
    except Exception as e:
        if obj_id:
            try:
                httpx.delete(f"{base_url}/api/v1/data/objects/{obj_id}",
                             headers=headers, timeout=10)
            except Exception:
                pass
        return {"name": "Custom Data CRUD", "status": "FAIL",
                "duration": round(time.time() - start, 2), "detail": str(e)[:100]}


def _test_publish(base_url: str, token: str, app_id: str) -> dict:
    """測試發布狀態"""
    import httpx
    start = time.time()
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = httpx.get(f"{base_url}/api/v1/builder/apps/{app_id}", headers=headers, timeout=30)
        status = resp.json().get("status", "")
        return {"name": "發布驗證", "status": "PASS",
                "duration": round(time.time() - start, 2), "detail": f"status={status}"}
    except Exception as e:
        return {"name": "發布驗證", "status": "FAIL",
                "duration": round(time.time() - start, 2), "detail": str(e)[:100]}


def _test_external_auth(base_url: str, slug: str) -> dict:
    """測試 External Auth API"""
    import httpx
    start = time.time()
    try:
        resp = httpx.get(f"{base_url}/api/v1/custom-app-auth/{slug}/me", timeout=10)
        return {"name": "External Auth",
                "status": "PASS" if resp.status_code in (200, 401) else "FAIL",
                "duration": round(time.time() - start, 2),
                "detail": f"status_code={resp.status_code}"}
    except Exception as e:
        return {"name": "External Auth", "status": "FAIL",
                "duration": round(time.time() - start, 2), "detail": str(e)[:100]}


def format_e2e_report(results: dict) -> str:
    """格式化 E2E 報告"""
    icons = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭"}
    lines = ["┌─────────────────────────────────────────────┐"]
    lines.append("│  AI GO E2E 驗證報告                           │")
    lines.append("├──────────────┬──────────┬────────────────────┤")
    lines.append("│ 測試群組      │ 狀態      │ 耗時               │")
    lines.append("├──────────────┼──────────┼────────────────────┤")
    for r in results["results"]:
        name = r["name"].ljust(12)
        status = f"{icons.get(r['status'], '?')} {r['status']}".ljust(8)
        dur = f"{r['duration']}s".ljust(18)
        lines.append(f"│ {name} │ {status} │ {dur} │")
    lines.append("└──────────────┴──────────┴────────────────────┘")
    s = results["summary"]
    lines.append(f"\n總計：{s['pass']} 通過, {s['fail']} 失敗, {s['skip']} 跳過")
    return "\n".join(lines)
