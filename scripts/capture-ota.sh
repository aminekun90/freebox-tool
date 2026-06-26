#!/bin/bash
# Capture OTA du Freebox Player — tout-en-un.
# Usage : sudo bash scripts/capture-ota.sh [duree_secondes]
# Cible UNIQUEMENT ton Player. Légal sur ton propre réseau.
set -u

PLAYER_MAC="34:27:92:8e:f3:38"  # MAC FIXE du Player (identifiant stable, ≠ IP DHCP)
SUBNET="192.168.1.0/24"
OUT="/Users/amine/Projects/freebox-tool/ota-capture.pcap"
DUR="${1:-240}"
IFACE="$(route -n get default 2>/dev/null | awk '/interface/{print $2}')"
BETTERCAP="$(command -v bettercap)"
NMAP="$(command -v nmap)"
TCPDUMP="/usr/sbin/tcpdump"
BC=""; TD=""

if [ "$(id -u)" != "0" ]; then echo "❌ lance avec sudo"; exit 1; fi
[ -z "$IFACE" ] && { echo "❌ interface réseau introuvable"; exit 1; }
[ -z "$BETTERCAP" ] && { echo "❌ bettercap absent (brew install bettercap)"; exit 1; }

# --- Détection de l'IP courante du Player via son MAC (robuste au DHCP) ---
resolve_player_ip() {
  # 1) déjà dans le cache ARP ?
  local ip
  ip="$(arp -an | grep -i "$PLAYER_MAC" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  if [ -z "$ip" ] && [ -n "$NMAP" ]; then
    # 2) sinon, ping sweep pour peupler l'ARP puis re-grep
    "$NMAP" -sn "$SUBNET" >/dev/null 2>&1
    ip="$(arp -an | grep -i "$PLAYER_MAC" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  fi
  echo "$ip"
}

echo "→ recherche du Player (MAC $PLAYER_MAC) sur $SUBNET…"
PLAYER="$(resolve_player_ip)"
[ -z "$PLAYER" ] && { echo "❌ Player introuvable. Allumé ? Branché au LAN ?"; exit 1; }
echo "→ Player détecté à l'IP $PLAYER"

OLD_FWD="$(sysctl -n net.inet.ip.forwarding)"

cleanup() {
  echo ""; echo "→ nettoyage (restauration ARP + forwarding)…"
  [ -n "$TD" ] && kill "$TD" 2>/dev/null
  [ -n "$BC" ] && kill "$BC" 2>/dev/null
  [ -n "$BC" ] && wait "$BC" 2>/dev/null
  sysctl -w net.inet.ip.forwarding="$OLD_FWD" >/dev/null
  echo "✅ réseau restauré. Paquets : $($TCPDUMP -r "$OUT" -nn 2>/dev/null | wc -l | tr -d ' ')  →  $OUT"
}
# Ctrl-C ou fin = nettoyage garanti (plus jamais de spoof bloqué)
trap cleanup EXIT INT TERM

echo "→ interface=$IFACE  cible=$PLAYER  durée=${DUR}s  sortie=$OUT"
echo "→ NE PAS rebooter le Player (ça change son IP). On capture son trafic normal."
rm -f "$OUT"

sysctl -w net.inet.ip.forwarding=1 >/dev/null

# 1) ARP-spoof du Player (redirige son trafic via ce Mac)
"$BETTERCAP" -iface "$IFACE" -no-colors -silent -eval \
  "set arp.spoof.targets $PLAYER; set arp.spoof.fullduplex true; net.probe on; arp.spoof on" \
  >/tmp/bettercap-ota.log 2>&1 &
BC=$!
echo "→ poisoning actif (5s)…"; sleep 5

# 2) Capture (-U = flush immédiat → lisible en direct)
echo "→ capture en cours ${DUR}s. Laisse le Player allumé, ne touche à rien."
"$TCPDUMP" -i "$IFACE" -nn -s0 -U -w "$OUT" "host $PLAYER" 2>/tmp/tcpdump-ota.log &
TD=$!
sleep "$DUR"
# cleanup() appelé automatiquement via trap EXIT
