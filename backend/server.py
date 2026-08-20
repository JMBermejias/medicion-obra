#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Servidor integrado (estaticos + API SQLite)
# Copyright (C) 2026 JMBernabeu
# License: GNU General Public License v3.0 or later (see LICENSE)
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

WEB_DIR = os.environ.get('MEDICION_WEB', '/var/www/medicion-obra')
DB_PATH = os.environ.get('MEDICION_DB', '/var/lib/medicion-obra/medicion.db')
HOST = os.environ.get('MEDICION_HOST', '0.0.0.0')
PORT = int(os.environ.get('MEDICION_PORT', '80'))
COLLECTIONS = ['materials', 'mediciones', 'empresas', 'obras', 'zonas', 'subcontratas']

SCHEMA = (
    'CREATE TABLE IF NOT EXISTS appdata ('
    'collection TEXT PRIMARY KEY,'
    'data TEXT NOT NULL,'
    'updated_at TEXT NOT NULL DEFAULT (datetime(\'now\'))'
    ')'
)

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.txt': 'text/plain; charset=utf-8',
    '.pdf': 'application/pdf',
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def load_data():
    conn = get_conn()
    rows = conn.execute('SELECT collection, data FROM appdata').fetchall()
    conn.close()
    data = {}
    for r in rows:
        try:
            data[r['collection']] = json.loads(r['data'])
        except (ValueError, TypeError):
            data[r['collection']] = []
    return data


def save_data(payload):
    conn = get_conn()
    try:
        for c in COLLECTIONS:
            if c in payload:
                value = json.dumps(payload[c], ensure_ascii=False)
                conn.execute(
                    'INSERT INTO appdata (collection, data) VALUES (?, ?) '
                    'ON CONFLICT(collection) DO UPDATE SET '
                    'data=excluded.data, updated_at=datetime(\'now\')',
                    (c, value),
                )
        conn.commit()
    finally:
        conn.close()


class Handler(BaseHTTPRequestHandler):

    def _send_json(self, code, body):
        data = body if isinstance(body, bytes) else json.dumps(
            body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        mime = MIME_TYPES.get(ext, 'application/octet-stream')
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            if ext == '.html' or filepath.endswith('sw.js'):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            else:
                self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self._serve_index()

    def _serve_index(self):
        index = os.path.join(WEB_DIR, 'mediotec.html')
        self._send_file(index)

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode('utf-8'))

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith('/api/data'):
            try:
                data = load_data()
                self._send_json(200, {c: data.get(c, []) for c in COLLECTIONS})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        elif path.startswith('/api/health'):
            self._send_json(200, {'ok': True, 'db': DB_PATH})
        else:
            filepath = os.path.join(WEB_DIR, path.lstrip('/'))
            if os.path.isfile(filepath):
                self._send_file(filepath)
            else:
                self._serve_index()

    def do_POST(self):
        path = urlparse(self.path).path
        if path.startswith('/api/data'):
            try:
                payload = self._read_json()
                save_data(payload)
                self._send_json(200, {'ok': True})
            except Exception as e:
                self._send_json(500, {'error': str(e)})
        else:
            self._send_json(404, {'error': 'not found'})

    def log_message(self, fmt, *args):
        sys.stderr.write('%s - %s\n' % (self.address_string(), fmt % args))


def main():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError:
        pass
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    sys.stderr.write(
        'Medicion Obra en http://%s:%d (web: %s, db: %s)\n'
        % (HOST, PORT, WEB_DIR, DB_PATH))
    server.serve_forever()


if __name__ == '__main__':
    main()
