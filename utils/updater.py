# -*- coding: utf-8 -*-
# utils/updater.py
import os, sys, json, shutil, tempfile, zipfile, hashlib
from urllib.request import urlopen

VERSION_FILE = os.path.join(os.path.dirname(__file__), '..', 'version.json')

def get_local_version() -> str:
    try:
        with open(VERSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f).get('version', '0.0.0')
    except Exception:
        return '0.0.0'

def fetch_manifest(manifest_url: str) -> dict:
    with urlopen(manifest_url, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def apply_zip(zip_path: str, target_dir: str):
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(target_dir)

def check_and_update(manifest_url: str, app_root: str) -> bool:
    """
    回傳 True 表示已更新且應重啟。
    manifest.json 例：
    {
      "latest": "1.2.3",
      "download_url": "https://your.domain/app_1.2.3.zip",
      "sha256": "abc123..."
    }
    """
    local = get_local_version()
    m = fetch_manifest(manifest_url)
    latest = m.get('latest')
    if not latest or latest <= local:
        return False

    dl = m['download_url']
    tmpdir = tempfile.mkdtemp()
    try:
        zpath = os.path.join(tmpdir, 'update.zip')
        with urlopen(dl, timeout=30) as r, open(zpath, 'wb') as w:
            shutil.copyfileobj(r, w)

        if m.get('sha256'):
            if sha256(zpath).lower() != m['sha256'].lower():
                raise RuntimeError("更新檔校驗失敗")

        # 解壓到臨時資料夾，再覆蓋
        unpack_dir = os.path.join(tmpdir, 'unpacked')
        os.makedirs(unpack_dir, exist_ok=True)
        apply_zip(zpath, unpack_dir)

        # 複製（略過自身與執行中檔案）
        for root, _, files in os.walk(unpack_dir):
            rel = os.path.relpath(root, unpack_dir)
            dst_root = os.path.join(app_root, rel) if rel != '.' else app_root
            os.makedirs(dst_root, exist_ok=True)
            for f in files:
                src = os.path.join(root, f)
                dst = os.path.join(dst_root, f)
                if os.path.abspath(dst) == os.path.abspath(__file__):
                    continue
                shutil.copy2(src, dst)
        return True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
