# -*- coding: utf-8 -*-
"""零外部依赖的本机 SQLite 页面浏览计数服务（供阿里云 ECS 部署替代 api.counterapi.dev）。

仅监听 127.0.0.1:9001，由 Nginx / Cloudflare Tunnel 反向代理 `location = /api/visits/up`。
响应格式 `{"value": <int>}` 与前端 `js/visits.js` 的 `extractCount` 完全兼容。
"""
from __future__ import print_function

import argparse
from contextlib import closing
import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_DB = "/var/lib/competition-search/visits.db"


class CounterStore(object):
    def __init__(self, db_path, initial=0):
        self.db_path = db_path
        self._lock = threading.Lock()
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.isdir(parent):
            os.makedirs(parent, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS counters ("
                "  name TEXT PRIMARY KEY,"
                "  value INTEGER NOT NULL"
                ")"
            )
            conn.execute(
                "INSERT OR IGNORE INTO counters (name, value) VALUES ('pageviews', ?)",
                (int(initial),),
            )
            conn.commit()

    def increment(self):
        with self._lock, closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "UPDATE counters SET value = value + 1 WHERE name = 'pageviews'"
            )
            row = conn.execute(
                "SELECT value FROM counters WHERE name = 'pageviews'"
            ).fetchone()
            conn.commit()
            return int(row[0]) if row else 1

    def current(self):
        with self._lock, closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT value FROM counters WHERE name = 'pageviews'"
            ).fetchone()
            return int(row[0]) if row else 0


def make_handler(store):
    class CounterHandler(BaseHTTPRequestHandler):
        def _send_cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def _send_json(self, status, payload):
            body = (json.dumps(payload) + "\n").encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._send_cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors()
            self.end_headers()

        def do_GET(self):
            path = self.path.split("?", 1)[0].rstrip("/")
            if path in ("/up", "/api/visits/up"):
                self._send_json(200, {"value": store.increment()})
            elif path in ("/get", "/api/visits"):
                self._send_json(200, {"value": store.current()})
            else:
                self._send_json(404, {"error": "not found"})

        def log_message(self, format_str, *args):
            pass

    return CounterHandler


def main():
    parser = argparse.ArgumentParser(description="本机 SQLite 页面浏览计数服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9001)
    parser.add_argument("--db", default=os.environ.get("VISITS_DB", DEFAULT_DB))
    parser.add_argument("--initial", type=int, default=0, help="首次建库时的初始计数值")
    args = parser.parse_args()

    store = CounterStore(args.db, initial=args.initial)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print("visit_counter listening on http://%s:%d (db=%s)" % (args.host, args.port, args.db))
    server.serve_forever()


if __name__ == "__main__":
    main()
