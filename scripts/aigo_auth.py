"""
aigo_auth.py — AI GO Custom App Builder 認證與配置管理模組

提供登入、設定檔管理、App 資訊查詢等功能。
"""

import json
import os
from pathlib import Path
from typing import Any

import httpx

# === 常數 ===
AIGO_BASE_URL = "https://ai-go.app"
API_V1 = f"{AIGO_BASE_URL}/api/v1"

# 設定檔目錄與檔名
CONFIG_DIR = ".aigo"
CONFIG_FILE = "config.json"

# 設定檔必填欄位
REQUIRED_FIELDS = ["base_url", "email", "app_id", "app_slug"]


def init_config(project_path: str) -> dict:
    """
    建立 .aigo/config.json 骨架。

    若檔案已存在則直接讀取並回傳，不覆寫。

    Args:
        project_path: 專案根目錄路徑

    Returns:
        config 字典
    """
    config_dir = Path(project_path) / CONFIG_DIR
    config_file = config_dir / CONFIG_FILE

    if config_file.exists():
        return load_config(project_path)

    # 建立骨架
    config: dict[str, Any] = {
        "base_url": AIGO_BASE_URL,
        "email": "",
        "app_id": "",
        "app_slug": "",
        "app_name": "",
        "access_mode": "internal",
    }

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ 已建立設定檔：{config_file}")
    return config


def load_config(project_path: str) -> dict:
    """
    讀取 .aigo/config.json。

    Args:
        project_path: 專案根目錄路徑

    Returns:
        config 字典

    Raises:
        FileNotFoundError: 設定檔不存在
        json.JSONDecodeError: JSON 格式錯誤
    """
    config_file = Path(project_path) / CONFIG_DIR / CONFIG_FILE

    if not config_file.exists():
        raise FileNotFoundError(
            f"❌ 找不到設定檔：{config_file}\n"
            f"   請先執行 init_config() 或手動建立設定檔。"
        )

    raw = config_file.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"❌ 設定檔 JSON 格式錯誤：{e.msg}",
            e.doc,
            e.pos,
        )


def validate_config(config: dict) -> list[str]:
    """
    檢查必填欄位，回傳缺少的欄位名稱清單。

    Args:
        config: 設定字典

    Returns:
        缺少的欄位名稱列表（空列表表示全部通過）
    """
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        value = config.get(field, "")
        if not value or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def login(base_url: str, email: str, password: str) -> dict:
    """
    呼叫 POST /api/v1/auth/login 取得 JWT Token。

    Args:
        base_url: API 根 URL（例如 https://ai-go.app）
        email: 使用者 Email
        password: 使用者密碼

    Returns:
        包含 access_token, refresh_token, expires_in 的字典

    Raises:
        httpx.HTTPStatusError: 登入失敗（401 等）
    """
    url = f"{base_url}/api/v1/auth/login"
    payload = {"email": email, "password": password}

    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_in": data.get("expires_in", 0),
        "token_type": data.get("token_type", "Bearer"),
    }


def get_app_info(base_url: str, token: str, app_id: str) -> dict:
    """
    呼叫 GET /api/v1/builder/apps/{app_id} 取得 App 資訊。

    Args:
        base_url: API 根 URL
        token: JWT access_token
        app_id: App ID 或 slug

    Returns:
        App 資訊字典（包含 id, name, slug, vfs_state, vfs_version, status, access_mode 等）

    Raises:
        httpx.HTTPStatusError: API 回應錯誤
    """
    url = f"{base_url}/api/v1/builder/apps/{app_id}"
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()

    return resp.json()


def print_setup_guide() -> None:
    """印出設定指引，幫助使用者完成初始化。"""
    guide = """
╔══════════════════════════════════════════════════════════════╗
║               AI GO Custom App Builder 設定指引              ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  1. 執行 init_config("./my-project") 建立設定檔骨架          ║
║                                                              ║
║  2. 編輯 .aigo/config.json，填入以下資訊：                    ║
║     - email:       你的 AI GO 帳號 Email                     ║
║     - app_id:      目標 App 的 UUID                          ║
║     - app_slug:    目標 App 的 Slug                          ║
║     - app_name:    App 顯示名稱（選填）                       ║
║     - access_mode: internal / external（選填）                ║
║                                                              ║
║  3. 執行 login() 取得 access_token                           ║
║                                                              ║
║  4. 使用 get_app_info() 驗證連線是否正常                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(guide)


# === 主程式入口 ===
if __name__ == "__main__":
    print_setup_guide()
