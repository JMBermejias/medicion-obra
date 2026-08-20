#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Medicion Obra - Servidor Windows (.exe)
# Copyright (C) 2026 JMBernabeu - GPL-3.0-or-later
import json, os, sqlite3, sys, threading, webbrowser, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(sys._MEIPASS, 'assets')
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ASSETS_DIR = os.path.join(BASE_DIR)

WEB_DIR = ASSETS_DIR
APPDATA = os.path.join(os.environ.get('APPDATA', BASE_DIR), 'MedicionObra')
DB_PATH = os.path.join(APPDATA, 'medicion.db')
HOST = '127.0.0.1'
PORT = 8080
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
        pass

def open_browser():
    time.sleep(1.0)
    webbrowser.open('http://127.0.0.1:%d' % PORT)

def main():
    os.makedirs(APPDATA, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=open_browser, daemon=True).start()
    print('===========================================')
    print('  Medicion Obra - Control de Medicion')
    print('===========================================')
    print('  Servidor:  http://127.0.0.1:%d' % PORT)
    print('  Base datos: %s' % DB_PATH)
    print('  Web:       %s' % WEB_DIR)
    print('===========================================')
    print('  Pulsa Ctrl+C para cerrar')
    print('===========================================')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nServidor detenido.')
        server.server_close()

if __name__ == '__main__':
    main()
