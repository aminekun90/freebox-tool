#!/usr/bin/env python3
"""
fbx-deploy — déploie et exécute une app QML sur un Freebox Player en mode développeur.

Protocole (reversé depuis freebox-qtcreator-plugin, LGPL) :
  1. On sert localement le dossier de l'app (manifest.json + QML) via HTTP.
  2. POST JSON-RPC `debug_qml_app` sur http://<player>/pub/devel avec manifest_url.
  3. Le Player fetch l'app, l'exécute, renvoie {qml_port, stdout_port, stderr_port}.
  4. On se connecte à stdout_port/stderr_port et on affiche la sortie de l'app.

Usage : python3 scripts/fbx-deploy.py <app_dir> [--player <ip>]
Le Player est sinon détecté par son MAC. Légal : matériel possédé, SDK officiel.
"""
import argparse, http.server, json, socket, sys, threading, urllib.request, subprocess, re, time

PLAYER_MAC = "34:27:92:8e:f3:38"

def find_player_ip():
    try:
        subprocess.run(["nmap", "-sn", "192.168.1.0/24"], capture_output=True, timeout=40)
    except Exception:
        pass
    out = subprocess.run(["arp", "-an"], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if PLAYER_MAC in line.lower():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                return m.group(1)
    return None

def local_ip_facing(player_ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((player_ip, 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

def serve_app(app_dir, bind_ip):
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(*a, directory=app_dir, **k)
    httpd = http.server.ThreadingHTTPServer((bind_ip, 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port

def jsonrpc(player_ip, method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(f"http://{player_ip}/pub/devel", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def stream_port(player_ip, port, label):
    if not port:
        return
    try:
        s = socket.create_connection((player_ip, port), timeout=10)
    except Exception as e:
        print(f"[{label}] connexion port {port} échouée: {e}"); return
    f = s.makefile("r", encoding="utf-8", errors="replace")
    for line in f:
        print(f"[{label}] {line.rstrip()}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir")
    ap.add_argument("--player", default=None)
    ap.add_argument("--seconds", type=int, default=20,
                    help="durée pendant laquelle servir l'app + lire la sortie")
    args = ap.parse_args()

    player = args.player or find_player_ip()
    if not player:
        sys.exit("Player introuvable (MAC %s). Allumé ? mode dev actif ?" % PLAYER_MAC)
    bind = local_ip_facing(player)
    print(f"→ Player={player}  notre IP={bind}  app={args.app_dir}")

    httpd, port = serve_app(args.app_dir, bind)
    manifest_url = f"http://{bind}:{port}/manifest.json"
    print(f"→ manifest servi: {manifest_url}")

    print("→ appel JSON-RPC debug_qml_app…")
    rep = jsonrpc(player, "debug_qml_app",
                  {"manifest_url": manifest_url, "entry_point": "main", "wait": False})
    if "error" in rep:
        print("✗ erreur:", json.dumps(rep["error"], ensure_ascii=False)); return
    res = rep.get("result", {})
    print("✓ lancé:", res)
    out_p, err_p = res.get("stdout_port"), res.get("stderr_port")

    threads = [threading.Thread(target=stream_port, args=(player, out_p, "stdout"), daemon=True),
               threading.Thread(target=stream_port, args=(player, err_p, "stderr"), daemon=True)]
    for t in threads: t.start()
    print(f"→ lecture stdout/stderr {args.seconds}s (Ctrl-C pour arrêter)…")
    try:
        time.sleep(args.seconds)
    except KeyboardInterrupt:
        pass
    print("→ fin.")

if __name__ == "__main__":
    main()
