#!/bin/bash
# Capture transparente — le Mac est la VRAIE passerelle du Player (Partage Internet).
# Aucun ARP-spoof → aucune alarme/bip. Usage : sudo bash scripts/capture-gw.sh [secondes]
set -u

PLAYER_MAC="34:27:92:8e:f3:38"
IFACE="bridge100"
OUT="/Users/amine/Projects/freebox-tool/gw-capture.pcap"
DUR="${1:-180}"
TCPDUMP="/usr/sbin/tcpdump"

[ "$(id -u)" != "0" ] && { echo "❌ lance avec sudo"; exit 1; }
IP="$(arp -an | grep -i "$PLAYER_MAC" | grep -oE '192\.168\.2\.[0-9]+' | head -1)"
[ -z "$IP" ] && { echo "❌ Player introuvable sur $IFACE (branché ? Partage actif ?)"; exit 1; }

echo "→ Player=$IP  iface=$IFACE  durée=${DUR}s  sortie=$OUT"
echo "→ capture en cours. POWER-CYCLE le Player maintenant (pour forcer le check OTA)."
rm -f "$OUT"
"$TCPDUMP" -i "$IFACE" -nn -s0 -U -w "$OUT" "host $IP" 2>/dev/null &
TD=$!
trap 'kill $TD 2>/dev/null; echo "→ stop."' EXIT INT TERM
sleep "$DUR"
kill "$TD" 2>/dev/null
echo "✅ terminé. Paquets : $($TCPDUMP -r "$OUT" -nn 2>/dev/null | wc -l | tr -d ' ')  →  $OUT"
