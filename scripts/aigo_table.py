"""AI GO Custom Table 管理工具"""
import re
from typing import Any, Optional


def validate_slug(slug: str) -> bool:
    """驗證 api_slug 格式"""
    return bool(re.match(r'^[a-z0-9]([a-z0-9_]*[a-z0-9])?$', slug))


def list_tables(base_url: str, token: str, app_id: str) -> list[dict]:
    """列出 Custom Tables"""
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.get(f"{base_url}/api/v1/data/objects", headers=headers,
                     params={"app_id": app_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def create_table_batch(base_url: str, token: str, app_id: str,
                       name: str, api_slug: str, fields: list[dict]) -> dict:
    """Batch 建表 + 欄位"""
    if not validate_slug(api_slug):
        raise ValueError(f"api_slug '{api_slug}' 格式不合法。僅允許小寫英文、數字和底線。")
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = httpx.post(f"{base_url}/api/v1/data/objects/batch", headers=headers, json={
        "app_id": app_id, "name": name, "api_slug": api_slug, "fields": fields
    }, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    # ★ 二次 GET 驗證
    new_id = result.get('id')
    if new_id:
        tables = list_tables(base_url, token, app_id)
        found = any(t.get('id') == new_id for t in tables)
        if not found:
            raise RuntimeError(f'建表驗證失敗：id={new_id} 未出現在表清單中')
    return result


def delete_table(base_url: str, token: str, obj_id: str, app_id: str = '') -> bool:
    """刪除資料表"""
    import httpx
    headers = {"Authorization": f"Bearer {token}"}
    resp = httpx.delete(f"{base_url}/api/v1/data/objects/{obj_id}", headers=headers, timeout=30)
    ok = resp.status_code in (200, 204)
    # ★ 二次 GET 驗證
    if ok and app_id:
        tables = list_tables(base_url, token, app_id)
        still_exists = any(t.get('id') == obj_id for t in tables)
        if still_exists:
            raise RuntimeError(f'刪除驗證失敗：id={obj_id} 仍存在於表清單中')
    return ok


def add_field(base_url: str, token: str, obj_id: str, field: dict) -> dict:
    """新增欄位"""
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = httpx.post(f"{base_url}/api/v1/data/objects/{obj_id}/fields",
                      headers=headers, json=field, timeout=30)
    resp.raise_for_status()
    return resp.json()
