# Findings — Freebox Delta Player recon

> Rempli au fur et à mesure. But : jailbreak software → Android.

## Device
- Modèle : Freebox Delta Player (Devialet)
- MAC : `34:27:92:8E:F3:38` — vendor **FREEBOX SAS**
- IP : `192.168.1.173`
- Hostname mDNS : `freebox-player.home` / `Freebox-Player.local`
- Date branchement réseau : 2026-06-26

## Ports ouverts (TCP)
| Port | Service | Bannière / version | Notes |
|-|-|-|-|
| 80 | http | nginx | racine = 404, aucun chemin courant trouvé |
| 554 | rtsp | Freebox rtspd 1.2 | OPTIONS: DESCRIBE/SETUP/PLAY/PAUSE/TEARDOWN |
| 5000 | rtsp (RAOP/AirPlay audio) | srcvers 220.68 | ANNOUNCE/RECORD/SET_PARAMETER… framing binaire `\0\0\0P` |
| 7000 | http (serveur AirPlay) | HTTP/1.0 | `/server-info` répond (plist), `/info` = 404 |
| 8080 | http | nginx | racine = 404, aucun chemin trouvé |

Scan complet `-p-` : seuls ces 5 ports (195 autres = filtered). ADB **5555 fermé**.

## Services mDNS / UPnP annoncés
- `_airplay._tcp` → **Freebox Player** @ `Freebox-Player.local:7000`
  - `deviceid=34:27:92:8E:F3:38 features=0x12BFFEBB model=AppleTV3,2 srcvers=220.68 flags=0x44 pk=764648ca…fc5d35 vv=2`
- `_raop._tcp` → **3427928EF338@Freebox Player** @ `:5000`
  - `vs=220.68 ch=2 sr=44100 ss=16 pw=false et=0,1,3,5 ek=1 tp=TCP,UDP am=AppleTV3,2 cn=0,1,2,3 md=0,1,2 ft=0x12BFFEBB sv=false da=true`
- **Pas** de `_devialet._tcp`, `_googlecast._tcp`, `_spotify-connect._tcp`, `_adb._tcp`, `_ssh._tcp`.

### AirPlay `/server-info` (port 7000)
```
deviceid 34:27:92:8E:F3:38 · features 314572475 (0x12BFFEBB)
model AppleTV3,2 · protovers 1.0 · srcvers 220.68 · vv 2
```
`model=AppleTV3,2` = identité AirPlay émulée (pas un vrai Apple TV).

## ADB (port 5555)
- État : **fermé** (filtered, pas de réponse)
- Aucune piste Android exposée côté réseau.

## Pistes d'entrée identifiées
- [x] ~~ADB réseau~~ → fermé
- [ ] Shell (telnet/ssh) → aucun port/mDNS, à confirmer via UART/console
- [ ] Web admin / dev caché → nginx présent mais 404 partout (fuzzing chemins à faire : `ffuf`/`gobuster`)
- [x] ~~API locale Devialet (Spark)~~ → pas de `_devialet._tcp` annoncé
- [ ] RTSP `Freebox rtspd 1.2` (port 554) → surface custom Free, à fuzzer (DESCRIBE/SETUP)
- [ ] AirPlay RAOP (5000/7000) `srcvers 220.68` → pile legacy, chercher CVE shairport/RAOP connues

## Hypothèses sur l'OS sous-jacent
- **Linux** très probable (nginx + `Freebox rtspd` + récepteur RAOP soft). Pas Android exposé.
- Appliance verrouillée : surface réseau minimale, tout en 404, services applicatifs custom Free.

## Acquis immédiat (repli « enceinte »)
- **`pw=false`** → streaming **AirPlay audio sans mot de passe fonctionne dès maintenant**.
  Codecs `cn=0,1,2,3` (PCM/ALAC/AAC/AAC-ELD), 44100/16/2ch. → usage enceinte AirPlay OK.

## Prochaines actions
1. Fuzzer les chemins nginx 80/8080 (`ffuf -w common.txt`) — l'UI Free vit peut-être sur un vhost/Host header.
2. Tester un `Host:` header Free (ex. `Host: mafreebox.freebox.fr`) sur 80/8080.
3. Fuzzer RTSP 554 (`Freebox rtspd 1.2`) — surface custom, potentiel parsing bug.
4. Chercher CVE/exploits RAOP `srcvers 220.68` (récepteur AirPlay legacy).
5. Hardware : repérer un **UART/console série** sur la carte (repli si réseau = cul-de-sac).
</content>
</invoke>
