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
- [ ] **EDL mode / Qualcomm 9008** (USB) — point d'entrée classique SD835. Besoin d'un *firehose programmer* signé pour ce board (souvent extrait par device). Permet dump/flash du stockage.
- [ ] **UART / console série** sur la carte — repérer le shell U-Boot/LK. **Test points candidats : TP5 / TP6 / TP7** (TX/RX/GND) d'après [EricBlanquer/freebox-devialet-hack](https://github.com/EricBlanquer/freebox-devialet-hack). Adaptateur CP2102.
- [ ] CVE chaîne de boot Qualcomm 835-class (LK / aboot / XBL) pour déverrouillage bootloader.

### Référence communautaire — [EricBlanquer/freebox-devialet-hack](https://github.com/EricBlanquer/freebox-devialet-hack)
Autre projet de root du Player Devialet (motivation : réparer Alexa). **Même mur : ni root ni shell à ce jour.** Apports hardware (corroborent + complètent) :
- SoC **APQ8098** confirmé indépendamment.
- Stockage = **UFS 32 Go** (⚠️ pas eMMC — corrige notre hypothèse ; impacte la méthode de dump physique : ISP UFS ≠ ISP eMMC).
- RAM LPDDR4 2 Go. Wi-Fi/BT **QCA6174** suspecté. Ethernet + codec audio **Realtek**.
- **UART : TP5/TP6/TP7**. Connecteur USB-C parfois dessoudé d'usine (à ressouder).
- Même plan d'attaque que nous : nmap → ADB/fastboot → UART → EDL.
- → **Contributeur potentiel à contacter** pour mutualiser l'effort.

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
- [x] ~~Chercher une image firmware **publiée**~~ → inexistante. Pas de dump public, pas de récup USB ([FS#29071](https://dev.freebox.fr/bugs/task/29071)), firmware auth par MAC + par device enregistré ([forum](https://forum.universfreebox.com/viewtopic.php?t=78584)).
- [ ] **⭐ Capturer le canal OTA de SON Player** (MITM/sniff LAN) : le device télécharge l'image après auth MAC → interception légale sur son réseau = seul moyen non-invasif d'obtenir le binaire. Identifier URL serveur + format (`fbxupdate` ? chiffré/signé ?), puis `binwalk`.
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

## ⭐⭐ VOIE PRIORITAIRE — Mode développeur officiel + Remote debugger (`fbx-devel`)
Découvert via un scan DHCP/mDNS/UPnP tiers (2026-06-26) :
- **DHCP Vendor Class Identifier = `linux-fbx7hd`** → confirme **Linux**, codename board/firmware `fbx7hd`.
- **Service mDNS `_fbx-devel._tcp` nommé "Remote debugger"** → résolu à `Freebox-Player.local:0`.
  Port **0 = dormant** (service annoncé mais pas en écoute). Aucun TXT. Tous les ports debug (23/1234/5555/9000…) filtered.
- Services supplémentaires actifs : `spotify-connect` (:56071), `hid` (:24322 udp, télécommande), UPnP MediaRenderer (AVTransport/RenderingControl).

### Ce que c'est : le SDK Player officiel de Free
- `_fbx-devel._tcp` "Remote debugger" = endpoint utilisé par le **plugin Freebox pour QtCreator** ([github.com/fbx/freebox-qtcreator-plugin](https://github.com/fbx/freebox-qtcreator-plugin)) pour découvrir un Player en **mode développeur** et y faire du **remote debug (gdb)**.
- **SDK Player officiel** : [dev.freebox.fr/sdk/player.html](https://dev.freebox.fr/sdk/player.html). Apps **Qt/QML** + module proprio `fbx`. Déploiement/exécution/debug depuis QtCreator. Packaging TAR. Publication via FreeStore/FreeFactory.
- **Activation** : menu réglages système du Player, à la télécommande. → fait passer `fbx-devel` de port 0 à un **port réel en écoute**.

### Pourquoi c'est la voie prioritaire (devant l'EDL)
- **Exécution de code sur l'appareil**, légale, non-invasive, sans déverrouillage bootloader.
- Apps Qt = **C++ compilé** sous le capot → si le sandbox autorise du natif, ≈ exécution arbitraire dans le contexte de l'app → base pour explorer le FS et tenter une **élévation de privilèges** vers root.
- Remote debugger = **gdbserver** → contrôle mémoire/process.

### Protocole du plugin (lu dans les sources `freebox-qtcreator-plugin/src`)
- `_fbx-devel._tcp` annonce **port 0** même mode dev activé (beacon de présence ; pas de port debug fixe en écoute — confirmé par scan : aucun nouveau port TCP ouvert).
- `runcontrol.cc` : l'IDE ouvre un serveur local (`mServer.listen()`) puis **se connecte au Player** pour streamer `stdout`/`stderr` de l'app (`connectToHost(mAddress, out/err)`). Ports **négociés dynamiquement** (`canAutoDetectPorts`).
- `debugger.cc` : debug au niveau **QML** (`qmlServerPort`), pas gdbserver natif exposé.
- Déploiement par **TAR** (`tar.cc`, `freestorepackager.cc`). Transport **TCP maison** (pas SSH).
- → Modèle : l'IDE **upload un TAR → le Player l'exécute comme process → streame la sortie**. C'est de l'**exécution de code sur l'appareil**. Pas de port fixe à scanner : il faut **piloter via le plugin**.

### 🎯 PROTOCOLE DE DÉPLOIEMENT REVERSÉ + CONFIRMÉ EN LIVE (mode dev actif)
Endpoint de contrôle **`http://<player>/pub/devel`** (port 80) = **JSON-RPC 2.0**, actif uniquement en mode dev.
Confirmé live : un GET renvoie `{"jsonrpc":"2.0","error":{"message":"go learn about json-rpc",...}}`.

Découverte du device : **SSDP** (UPnP, `239.255.255.250:1900`, device type **`fbx:devel`**) — pas seulement mDNS.

**Méthode utile : `debug_qml_app`** (les autres → `method not found`, pas d'introspection) :
```
POST http://<player>/pub/devel
{"jsonrpc":"2.0","id":1,"method":"debug_qml_app","params":{"manifest_url":"http://<NOTRE-IP>:<port>/manifest.json"}}
→ {"qml_port":N,"stdout_port":N,"stderr_port":N}
```
Modèle (d'après `remote/remoteqml.cc`) : **on héberge l'app chez nous** (HTTP local servant `manifest.json` + QML), le Player la **fetch, l'exécute, et ouvre 3 ports** auxquels on se connecte pour récupérer `stdout`/`stderr` + le canal de debug QML.

`manifest.json` (format, cf. template SDK) :
```
{"name","identifier","description","entryPoints":{"main":{"file":"<Main.qml>","default":true}}}
```

**Conséquence : on peut tout piloter en Python pur. QtCreator/Qt 5.8 INUTILES pour du QML.**

### ✅ Acquis mode dev
- [x] Mode développeur activé sur le Player.
- [x] `_fbx-devel._tcp` reste port 0 (beacon SSDP), le vrai canal est `/pub/devel` JSON-RPC.
- [x] Protocole `debug_qml_app` reversé depuis les sources LGPL + confirmé live.
- [ ] Construire le CLI de déploiement (`scripts/fbx-deploy.py`) : HTTP local + JSON-RPC + lecture stdout/stderr.
- [ ] Déployer une app de sonde QML (Phase 2 : lire `/proc`, FS, uid via XMLHttpRequest file://).
- [ ] Installer QtCreator + plugin Freebox + lib QML `fbx`. Déployer une app test.
- [ ] Sonder le **contexte d'exécution** de l'app : accès FS, lancement de process, code C++ natif autorisé ? user/uid ? → cartographier la surface d'évasion du sandbox.
- [ ] Récupérer les **sources GPL** correspondant à `fbx7hd` (kernel/toolchain) → cross-compile.

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

## ⚠️ Le Player détecte le MITM (anti-ARP-spoof / intégrité réseau)
**Test reproduit 2x (2026-06-26)** : un ARP-spoof bettercap ciblant le Player provoque, après ~10-30 s, une **mise en sécurité avec bip audible toutes les 5-10 s**. L'arrêt du spoof (restauration ARP) fait cesser le bip.
- Le MITM L2 capture bien les paquets (~150 sur un essai), mais le Player **réagit** : soit protection anti-MITM, soit perte de sa session TLS authentifiée au serveur Free.
- **Conséquence : l'ARP-spoofing est inutilisable** pour capturer l'OTA.
- **Note DHCP** : le Player change d'IP au reboot (`.173` → `.174`). L'identifier par **MAC** (`34:27:92:8E:F3:38`), pas par IP. Script `scripts/capture-ota.sh` résout l'IP via le MAC.

### Méthode de capture propre à privilégier
Devenir la **vraie passerelle** du Player (pas de spoof) → aucune anomalie détectable :
- **Partage Internet macOS** : Player en Ethernet sur adaptateur USB-Eth du Mac ; Mac = DHCP+NAT+gateway, uplink Wi-Fi vers Freebox. `tcpdump` sur l'iface du Player.
- Alternative : switch manageable avec **port mirroring** entre Player et Freebox.

### État : voie réseau software ÉPUISÉE (2026-06-26)
- Reset usine testé → **aucune** nouvelle surface (mêmes 5 ports, nginx 404, ADB 5555 toujours filtered).
- ARP-spoof → bip sécurité (cf. ci-dessus). Inutilisable.
- Capture propre (vraie passerelle) **bloquée faute de matériel** : pas d'adaptateur USB-Ethernet ni de switch manageable côté testeur.
- **Déblocage peu coûteux pour un contributeur** : un **adaptateur USB-Ethernet (~10-15 €)** OU un **switch manageable avec port mirroring** rouvre immédiatement la capture OTA non-invasive (activation, hostnames serveurs Free, format firmware). C'est la dernière piste software propre avant le hardware.

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
