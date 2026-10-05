"""跨平台启动器：自动安装锁定依赖，并以单进程启动前后端。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def verified_wheels(folder):
    """本地安装前核对随部署包提供的官方 wheel 下载结果。"""
    manifest = folder / 'SHA256SUMS.json'
    if not manifest.is_file():
        raise SystemExit('依赖包校验清单缺失，请重新下载完整部署包。')
    entries = json.loads(manifest.read_text())
    for filename, expected in entries.items():
        if Path(filename).name != filename:
            raise SystemExit('依赖包文件名不合法。')
        file = folder / filename
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise SystemExit('依赖包校验失败，请重新下载完整部署包。')
    return folder

def prepare():
    if sys.version_info < (3, 11):
        raise SystemExit('请安装 Python 3.11 或更新版本，推荐 Python 3.12。')
    env = ROOT / '.venv'
    python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('正在创建项目虚拟环境…', flush=True)
        venv.create(env, with_pip=True)
    lock = ROOT / 'requirements.lock'
    marker = env / '.relay-dependencies'
    wanted = hashlib.sha256(lock.read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text().strip() != wanted:
        bundled = ROOT / 'wheels' / 'windows-py312'
        windows312 = os.name == 'nt' and sys.version_info[:2] == (3,12) and platform.machine().lower() in ('amd64','x86_64')
        if windows312 and bundled.is_dir():
            print('正在校验并安装随包提供的 Windows 依赖…', flush=True)
            verified_wheels(bundled)
            source = ['--no-index', '--find-links', str(bundled)]
        else:
            print('正在安装锁定依赖（首次启动需要联网）…', flush=True)
            source = ['--index-url', 'https://pypi.org/simple']
        subprocess.run([str(python), '-m', 'pip', 'install', *source, '-r', str(lock)], check=True)
        marker.write_text(wanted)
    return python

def main():
    parser = argparse.ArgumentParser(description='启动 Relay 共创')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--install-only', action='store_true')
    args = parser.parse_args()
    python = prepare()
    if args.install_only:
        print('依赖安装完成。')
        return
    url = f'http://127.0.0.1:{args.port}'
    process = subprocess.Popen([str(python), '-m', 'uvicorn', 'app.main:app', '--host', args.host, '--port', str(args.port)], cwd=ROOT)
    stop = threading.Event()
    if not args.no_browser:
        def open_when_ready():
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(60):
                if stop.wait(.5) or process.poll() is not None:
                    return
                try:
                    with opener.open(url+'/api/health', timeout=1) as response:
                        if response.status == 200:
                            webbrowser.open(url)
                            return
                except OSError:
                    pass
        threading.Thread(target=open_when_ready, daemon=True).start()
    print(f'服务地址：{url}；按 Ctrl+C 停止。', flush=True)
    try:
        raise SystemExit(process.wait())
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        print('\n服务已停止。')
    finally:
        stop.set()

if __name__ == '__main__':
    main()
