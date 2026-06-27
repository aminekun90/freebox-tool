#!/usr/bin/env python3
"""
airplay-fuzz — fuzzer black-box du récepteur AirPlay/RAOP du Freebox Player.

Cible la surface de parsing NON authentifiée (AirPlay 1 legacy) :
  - RTSP 5000 (RAOP) : OPTIONS/ANNOUNCE/SETUP/SET_PARAMETER (headers, SDP, Content-Length)
  - HTTP 7000 (AirPlay) : /playback-info, plists

Détecte les crashes par perte de liveness (le daemon meurt → port ne répond plus),
sauve le reproducteur exact, puis attend la reprise du service.

Usage : python3 scripts/airplay-fuzz.py [--player IP] [--port 5000|7000] [-n N] [--seed S]
Matériel possédé, recherche sécurité. Le Player orphelin peut crasher/redémarrer le daemon.
"""
import argparse, random, socket, subprocess, re, sys, time, os

PLAYER_MAC = "34:27:92:8e:f3:38"
OUTDIR = os.path.join(os.path.dirname(__file__), "..", "firmware", "fuzz-crashes")

def find_player():
    try: subprocess.run(["nmap","-sn","192.168.1.0/24"], capture_output=True, timeout=40)
    except Exception: pass
    out = subprocess.run(["arp","-an"], capture_output=True, text=True).stdout
    for l in out.splitlines():
        if PLAYER_MAC in l.lower():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", l)
            if m: return m.group(1)
    return None

def send_raw(ip, port, data, timeout=2, read=True):
    """Envoie data. Si read=False : fire-and-forget (débit max pour le fuzzing)."""
    try:
        s = socket.create_connection((ip, port), timeout=timeout)
        s.sendall(data)
        if not read:
            s.close()
            return True, b""
        s.settimeout(timeout)
        resp = b""
        try:
            resp = s.recv(2048)
        except socket.timeout:
            pass
        s.close()
        return True, resp
    except Exception as e:
        return False, str(e).encode()

def alive(ip, port):
    """Liveness : OPTIONS RTSP (5000) ou GET /server-info (7000)."""
    if port == 7000:
        ok, r = send_raw(ip, port, b"GET /server-info HTTP/1.1\r\nHost: x\r\n\r\n")
        return ok and b"200" in r[:20]
    ok, r = send_raw(ip, port, b"OPTIONS * RTSP/1.0\r\nCSeq: 1\r\n\r\n")
    return ok and b"RTSP/1.0 200" in r

# --- corpus de seeds (requêtes valides à muter) ---
def seeds(ip, port):
    if port == 7000:
        return [
            b"GET /server-info HTTP/1.1\r\nHost: %s\r\n\r\n" % ip.encode(),
            b"GET /playback-info HTTP/1.1\r\nHost: %s\r\n\r\n" % ip.encode(),
            b"POST /play HTTP/1.1\r\nHost: %s\r\nContent-Type: application/x-apple-binary-plist\r\nContent-Length: 8\r\n\r\nbplist00" % ip.encode(),
        ]
    sdp = (b"v=0\r\no=iTunes 1 0 IN IP4 %s\r\ns=iTunes\r\nc=IN IP4 %s\r\nt=0 0\r\n"
           b"m=audio 0 RTP/AVP 96\r\na=rtpmap:96 AppleLossless\r\n"
           b"a=fmtp:96 352 0 16 40 10 14 2 255 0 0 44100\r\n") % (ip.encode(), ip.encode())
    return [
        b"OPTIONS * RTSP/1.0\r\nCSeq: 1\r\n\r\n",
        b"ANNOUNCE rtsp://%s/1 RTSP/1.0\r\nCSeq: 2\r\nContent-Type: application/sdp\r\nContent-Length: %d\r\n\r\n%s"
            % (ip.encode(), len(sdp), sdp),
        b"SETUP rtsp://%s/1 RTSP/1.0\r\nCSeq: 3\r\nTransport: RTP/AVP/UDP;unicast;control_port=6001;timing_port=6002\r\n\r\n" % ip.encode(),
        b"SET_PARAMETER rtsp://%s/1 RTSP/1.0\r\nCSeq: 4\r\nContent-Type: text/parameters\r\nContent-Length: 12\r\n\r\nvolume: -20\n" % ip.encode(),
    ]

NASTY = [b"A"*4096, b"%n%n%n%s%s", b"../"*64, b"\x00"*256, b"-1", b"99999999999",
         b"\xff"*128, b"%99999d", b"\r\n"*64, b";id;", b"\x80\x00\x00\x00"]

def mutate(data, rng):
    b = bytearray(data)
    strat = rng.randint(0, 5)
    if strat == 0 and len(b) > 4:            # bit flips
        for _ in range(rng.randint(1, 16)):
            b[rng.randrange(len(b))] ^= 1 << rng.randint(0, 7)
    elif strat == 1:                          # injecter un payload nasty
        ins = rng.choice(NASTY)
        pos = rng.randrange(len(b)+1)
        b[pos:pos] = ins
    elif strat == 2:                          # casser Content-Length
        b = bytearray(re.sub(rb"Content-Length: \d+",
                             b"Content-Length: %d" % rng.choice([0,1,999999,-1,2**31]), bytes(b)))
    elif strat == 3 and len(b) > 8:           # tronquer
        b = b[:rng.randrange(1, len(b))]
    elif strat == 4:                          # dupliquer/allonger un header
        b = bytes(b).replace(b"\r\n\r\n", (b"\r\nX-F: " + rng.choice(NASTY) + b"\r\n\r\n"), 1)
        b = bytearray(b)
    else:                                     # CSeq/valeur géante
        b = bytearray(re.sub(rb"CSeq: \d+", b"CSeq: " + rng.choice(NASTY), bytes(b)))
    return bytes(b)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", default=None)
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("-n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--continue-on-crash", action="store_true")
    args = ap.parse_args()
    ip = args.player or find_player()
    if not ip: sys.exit("Player introuvable")
    os.makedirs(OUTDIR, exist_ok=True)
    rng = random.Random(args.seed)
    base = seeds(ip, args.port)
    print(f"→ cible {ip}:{args.port}  cas={args.n}  seed={args.seed}")
    if not alive(ip, args.port):
        sys.exit("service déjà KO au départ — réessaie plus tard")
    crashes = 0
    for i in range(args.n):
        case = mutate(rng.choice(base), rng)
        send_raw(ip, args.port, case, read=False)   # fire-and-forget
        if i % 25 == 0:                       # liveness périodique
            # 1) suspicion : liveness perdue (peut être juste la charge)
            if not alive(ip, args.port) and not alive(ip, args.port):
                # 2) laisser le daemon respirer (la charge retombe)
                recovered = False
                for _ in range(30):
                    time.sleep(2)
                    if alive(ip, args.port): recovered = True; break
                if not recovered:
                    print(f"⚠️ service mort et non revenu @ cas {i} (vrai crash dur ?) — arrêt");
                    fn = os.path.join(OUTDIR, f"hardcrash_{args.port}_{i}_{int(time.time())}.bin")
                    open(fn, "wb").write(case); break
                # 3) CONFIRMATION : rejouer le cas isolément ; ne compter que si ça RE-tue
                send_raw(ip, args.port, case, read=False)
                time.sleep(0.5)
                if not alive(ip, args.port) and not alive(ip, args.port):
                    crashes += 1
                    fn = os.path.join(OUTDIR, f"crash_{args.port}_{i}_{int(time.time())}.bin")
                    open(fn, "wb").write(case)
                    print(f"💥 CRASH REPRODUIT @ cas {i} → {fn} ({len(case)} o)")
                    for _ in range(30):
                        time.sleep(2)
                        if alive(ip, args.port): break
                    if not args.__dict__["continue_on_crash"]:
                        print("→ stop sur 1er crash confirmé"); break
                # sinon : faux positif (charge), on continue silencieusement
        if i % 500 == 0 and i: print(f"  …{i} cas, {crashes} crash(es)")
    print(f"✓ terminé. {crashes} crash(es). Reproducteurs dans {OUTDIR}/")

if __name__ == "__main__":
    main()
