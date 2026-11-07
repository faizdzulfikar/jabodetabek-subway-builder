"""Serve only packaged assets on loopback; pmtiles provides Z/X/Y tiles."""
import functools
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text())


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

    def guess_type(self, path):
        if path.endswith('.gz'):
            return 'application/gzip'
        return super().guess_type(path)


def main():
    for name in ['JKT.pmtiles', 'JKT_foundations.pmtiles']:
        if not (ROOT / 'assets' / name).is_file():
            raise SystemExit(f'Missing map asset: {name}. Finish the build first.')
    executable = shutil.which('pmtiles')
    if not executable:
        raise SystemExit('Install pmtiles first: brew install pmtiles')
    server = http.server.ThreadingHTTPServer(
        ('127.0.0.1', CONFIG['data_port']),
        functools.partial(Handler, directory=str(ROOT / 'assets')))
    child = subprocess.Popen([
        executable, 'serve', str(ROOT / 'assets'), '--interface=127.0.0.1',
        f"--port={CONFIG['tile_port']}", '--cors=*', '--cache-size=32'])
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print('Jabodetabek asset server ready. Keep this window open while playing.', flush=True)
    try:
        child.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        child.terminate()
        child.wait()


if __name__ == '__main__':
    main()
