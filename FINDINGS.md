# Findings — Freebox Delta Player recon

> Rempli au fur et à mesure. But : jailbreak software → Android.

## Device
- Modèle : Freebox Delta Player (Devialet), lancé 2018
- MAC : `34:27:92:8E:F3:38` — vendor **FREEBOX SAS**
- IP : `192.168.1.173`
- Hostname mDNS : `freebox-player.home` / `Freebox-Player.local`
- Date branchement réseau : 2026-06-26

## Hardware (specs publiques)
| Composant | Détail |
|-|-|
| **SoC** | **Qualcomm Snapdragon APQ8098** (= MSM8998 / SD835 sans modem, Quad-core ARMv8 64-bit) |
| RAM | 2 Go |
| Flash | 32 Go (eMMC probable) |
| Vidéo | 4K HDR10, HDMI 2.1, HDCP 2.2, e-ARC |
| Réseau | WiFi 802.11ac 2x2 MU-MIMO, BT 4.1, NFC |
| OS d'origine | **Interface maison Free** (Linux custom), **pas** Android TV |

### Implication Android
- L'APQ8098 = même puce que Pixel 2 / OnePlus 5 / Galaxy S8 → **fait tourner Android nativement**. Aucune limite matérielle.
- Verrou réel = **logiciel/crypto** : bootloader Qualcomm verrouillé (Secure Boot / QFuse), firmware signé, aucune ROM AOSP/Lineage existante pour ce board (port complet à faire : kernel + device tree + drivers Devialet/HDMI).
- Références bug tracker Free (toutes refusées) :
  - [FS#33524](https://dev.freebox.fr/bugs/task/33524) — « Player delta Devialet sous Android TV », sans suite.
  - [FS#34632](https://dev.freebox.fr/bugs/task/34632) — « Passer la Freebox Devialet à Android TV ou Google TV ». **Clos « Ne sera pas implémenté »** (Thibaut, 2021-05-04). Les users notent le hardware *capable* d'Android TV + ~7 bugs ouverts depuis 2018 (Disney+, Netflix 5.1, Chromecast non fonctionnel).
  - → Aucune voie officielle ne viendra. Le jailbreak communautaire est la **seule** option. Free n'a Android TV que sur Pop (Amlogic S905X2) et V9.

### Pistes hardware d'entrée (toutes légales sur matériel possédé)
- [ ] **EDL mode / Qualcomm 9008** (USB) — point d'entrée classique SD835. Besoin d'un *firehose programmer* signé pour ce board (souvent extrait par device). Permet dump/flash eMMC.
- [ ] **UART / console série** sur la carte — repérer le shell U-Boot/LK.
- [ ] CVE chaîne de boot Qualcomm 835-class (LK / aboot / XBL) pour déverrouillage bootloader.

### Exploits / techniques publiques applicables au MSM8998/APQ8098
| Piste | Détail | Applicabilité Player Devialet |
|-|-|-|
| **EDL Sahara 0x13** ([Aleph Security](https://alephsecurity.com/2018/01/22/qualcomm-edl-1/)) | Buffer overflow dans la state machine Sahara du PBL (ROM) → bypass du hash des program headers. Générique MSM8916→MSM8998. | **Prometteur** : attaque le PBL en ROM, en amont du firmware signé Free. À tester via EDL 9008. |
| **EDL Peek/Poke** ([ALEPH-2017028](https://alephsecurity.com/vulns/aleph-2017028)) | Firehose programmers exposent primitives lecture/écriture mémoire arbitraire. | Nécessite un firehose **signé pour ce board** d'abord. |
| **CVE-2021-1931** ([xperable](https://xdaforums.com/t/xz1c-xz1-xzp-xperable-xperia-abl-fastboot-exploit-cve-2021-1931.4771931/)) | Exploit fastboot ABL sur MSM8998 — **Sony Yoshino/Tama uniquement** (ABL spécifique). | Probablement **non** : ABL Free ≠ ABL Sony. À étudier si surface fastboot exposée. |

### Verrous à lever, dans l'ordre
1. **Entrer en EDL** (9008) : test points sur la carte (court-circuit au boot) OU commande logicielle si shell obtenu. → identifier les test points au teardown.
2. **Obtenir/contourner le firehose** : soit firehose Free signé (à extraire/leak), soit exploit Sahara 0x13 pour bypasser la signature.
3. **Dump eMMC complet** → reverse du firmware d'origine (partitions, clés, U-Boot/LK, rootfs Free).
4. **Bootloader unlock** : analyser aboot/XBL dumpé, chercher faille de vérif signature, ou état QFuse `OEM unlock`.
5. **Port AOSP** : device tree + kernel + drivers Devialet (audio/HDMI) — le gros du travail une fois le boot ouvert.

> Blocage matériel : **aucun** (APQ8098 = Android-native). Blocage = chaîne de boot signée. Chemin = EDL/Sahara + teardown pour test points/UART.

### ⚠️ Analyse protocole EDL — le verrou se réduit à UN artefact
Après lecture Aleph Security + bkerler/edl loader management :
- **Firehose signé obligatoire** : bkerler matche le loader par **hardware-ID + hash de clé publique**. Secure Boot actif (cas opérateur quasi certain) ⇒ il faut le firehose **signé par Free pour ce board précis**. Pas de loader générique MSM8998 si secure boot ON.
- **Peek/Poke EL3** ([ALEPH-2017028](https://alephsecurity.com/vulns/aleph-2017028)) = bypass complet Secure Boot (dump PBL, défait chain of trust) **mais POST-auth** : nécessite un firehose **déjà en exécution**.
- **PBL extraction sans loader signé** (niveau Sahara) : démontré seulement sur MSM8994/8937/8953/8974 — **PAS le MSM8998**. Donc EDL seul ≠ bypass sur APQ8098.

**→ Tout le projet se ramène à : obtenir le firehose Free signé du Player Devialet.**
Avec lui : peek/poke → EL3 → contrôle total (dump eMMC, patch aboot, flash Android). Sans lui : EDL inerte.

### Pistes pour récupérer le firehose Free (légales)
- [ ] Chercher une **image OTA / firmware Player Devialet** publiée par Free (le `prog_firehose_*.elf` est parfois embarqué dans les outils d'usine, rarement dans l'OTA).
- [ ] **Dump eMMC hors EDL** : ISP/chip-off de l'eMMC, ou shell via UART → `dd` des partitions. Bypasse le besoin de firehose (lecture directe du flash).
- [ ] Vérifier si un firehose MSM8998 d'un **autre device** passe (peu probable si Secure Boot, mais à tester : certains boards ont QFuse non blown en prod).
- [ ] **UART en priorité** : si un shell root est accessible au boot, on lit le firmware directement et on saute toute la problématique EDL.

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

### AirPlay HTTP (port 7000) — endpoints sondés
```
deviceid 34:27:92:8E:F3:38 · features 314572475 (0x12BFFEBB)
model AppleTV3,2 · protovers 1.0 · srcvers 220.68 · vv 2
```
`model=AppleTV3,2` = identité AirPlay émulée (pas un vrai Apple TV).

| Endpoint | Code | Note |
|-|-|-|
| `/server-info` | 200 | plist device info (ci-dessus) |
| `/slideshow-features` | 200 | thèmes **Carrousel/Fondu/Zoom/SlideLeft/SlideRight** → support photo/slideshow AirPlay |
| `/playback-info` | **500** | erreur interne sans session — endroit à fuzzer (parsing) |
| `/pair-setup` `/pair-verify` `/fp-setup` `/auth-setup` | 404 | **absents** → AirPlay **1 legacy**, pas de pairing ni FairPlay |
| `/info` (GET et POST plist) | 404 | pas d'API AirPlay 2 |

→ Récepteur **AirPlay 1** type shairport, httpd custom (pas de header `Server`).
RTSP 5000 OPTIONS confirme : `OPTIONS, ANNOUNCE, SETUP, RECORD, SET_PARAMETER, GET_PARAMETER, FLUSH, TEARDOWN, POST, GET`. RTSP 554 : pas de réponse à OPTIONS/DESCRIBE.

### Web nginx (80/8080) — impasse à ce stade
- `Host:` header (mafreebox.freebox.fr, player.freebox.fr, localhost, …) → **tous 404** (len=146, page nginx standard). Pas de vhost.
- ~40 chemins courants (api/v8, system, status, firmware, debug, spark, devialet, player…) → **tous 404** sur 80 ET 8080.
- nginx route donc sur des routes internes très spécifiques (hash/proxy). Fuzzing wordlist large (`ffuf`) requis pour aller plus loin.

## ADB (port 5555)
- État : **fermé** (filtered, pas de réponse)
- Aucune piste Android exposée côté réseau.

## Pistes d'entrée identifiées
- [x] ~~ADB réseau~~ → fermé
- [ ] Shell (telnet/ssh) → aucun port/mDNS, à confirmer via UART/console
- [~] Web admin / dev caché → nginx 404 sur ~40 chemins + tous les `Host:` testés. Pas de vhost. Reste : fuzzing wordlist large (`ffuf`/`gobuster` + `common.txt`/`raft`).
- [x] ~~API locale Devialet (Spark)~~ → pas de `_devialet._tcp` annoncé
- [ ] RTSP `Freebox rtspd 1.2` (port 554) → ne répond pas à OPTIONS/DESCRIBE basiques, surface custom à creuser
- [~] AirPlay RAOP (5000/7000) `srcvers 220.68` → AirPlay 1 legacy, sans pairing/FairPlay. `/playback-info` renvoie **500** → point de fuzzing prioritaire. Chercher CVE shairport/RAOP.

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
