#!/usr/bin/env bash
#
# Non-destructive network recon for the Freebox Delta Player (owned device).
#
# Usage:
#   ./recon.sh 192.168.1.0/24            # discover hosts (ping sweep + ARP)
#   ./recon.sh 192.168.1.0/24 <ip>       # full scan of a target
#
# Tools: nmap, adb, nc, dns-sd (macOS). Run host discovery / -sn with sudo to
# get MAC vendors. Results are printed and appended to recon-<ip>-<date>.log.
set -uo pipefail

SUBNET="${1:-192.168.1.0/24}"
TARGET="${2:-}"

mdns_browse() {
  # dns-sd has no built-in timeout; run it bounded.
  local svc="$1" secs="${2:-4}"
  dns-sd -B "$svc" local. & local pid=$!
  sleep "$secs"; kill "$pid" 2>/dev/null
}

if [ -z "$TARGET" ]; then
  echo ">> Ping sweep $SUBNET (hosts up)"
  nmap -sn "$SUBNET" -oG - | awk '/Up$/{print $2, $3}'
  echo
  echo ">> ARP table (look for the Devialet/Freebox host)"
  arp -a | grep -iE "freebox|devialet" || arp -a
  echo
  echo ">> Advertised mDNS service TYPES on the LAN (Devialet gear is chatty here):"
  mdns_browse "_services._dns-sd._udp" 5
  echo
  echo "Next: ./recon.sh $SUBNET <player-ip>"
  exit 0
fi

LOG="recon-${TARGET}-$(date +%Y%m%d-%H%M).log"
exec > >(tee -a "$LOG") 2>&1
echo "=================================================================="
echo "Recon target: $TARGET   $(date)"
echo "=================================================================="

echo; echo ">> [1/6] Full TCP port scan (-p- -Pn)"
nmap -p- -T4 -Pn "$TARGET"

echo; echo ">> [2/6] Service/version + default scripts on open TCP ports"
nmap -sV -sC -Pn "$TARGET"

echo; echo ">> [3/6] Key UDP ports (DNS, SSDP/UPnP, mDNS, SNMP)"
nmap -sU -Pn -p 53,67,123,161,1900,5353 "$TARGET"

echo; echo ">> [4/6] mDNS service instances (AirPlay/Cast/Spotify/Devialet/RAOP)"
for s in _airplay._tcp _raop._tcp _googlecast._tcp _spotify-connect._tcp \
         _devialet._tcp _http._tcp _adb._tcp _ssh._tcp _workstation._tcp; do
  echo "--- $s ---"; dns-sd -B "$s" local. & p=$!; sleep 2; kill "$p" 2>/dev/null
done

echo; echo ">> [5/6] SSDP/UPnP description probe"
printf 'M-SEARCH * HTTP/1.1\r\nHOST:239.255.255.250:1900\r\nMAN:"ssdp:discover"\r\nMX:2\r\nST:ssdp:all\r\n\r\n' \
  | nc -u -w 3 239.255.255.250 1900 2>/dev/null | grep -iE "LOCATION|SERVER" | sort -u || echo "(no SSDP reply)"

echo; echo ">> [6/6] ADB probe (the 'is there Android underneath' test)"
if nc -z -G 2 "$TARGET" 5555 2>/dev/null; then
  echo "port 5555 OPEN — trying adb connect"
  adb connect "${TARGET}:5555" && adb devices && adb -s "${TARGET}:5555" shell getprop 2>/dev/null | head -40
else
  echo "port 5555 closed"
fi

echo; echo "Done. Saved to $LOG"
