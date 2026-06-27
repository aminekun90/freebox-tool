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
- [x] **CLI `scripts/fbx-deploy.py` fonctionnel** : HTTP local + JSON-RPC `debug_qml_app` + lecture stdout/stderr. Params requis : `manifest_url`, `entry_point` (clé de `entryPoints`, ex `"main"`), `wait` (bool).
- [x] **CODE EXECUTION OBTENUE** : app QML exécutée sur le Player, sortie récupérée par réseau, rendu visible sur la TV. Zéro QtCreator.

### Carte du sandbox (Phase 2 — en cours)

- **OS** = `linux` (confirmé via `Qt.platform.os`).
- **`file://` totalement bloqué** : XHR sur `/proc/*`, `/etc/*` → *"Access prohibited"* (whitelist custom). Pas de lecture FS via QML XHR.
- App servie **depuis notre HTTP** (pas de dossier app local sur le FS device). `Qt.resolvedUrl` pointe sur notre serveur.
- Structure d'app valide : `import QtQuick 2.5` + `import fbx.application 1.0`, racine **`Application`** (framework Free, attend `handleUrl()`).
- **Module `fbx.application` — `Application` expose des propriétés privilégiées Free** (au-delà du Window Qt) :
  `accountId`, `profileId`, `consoleWidget`, `consoleState`, `appState`, `remoteMapping`, `contents`, `log`.
  → `console*` (console de debug ?) et `accountId/profileId` (infos compte) = à sonder.
- **Module QML absents** : `Qt.labs.folderlistmodel` non installé (Qt 5.8 minimal sur device).

### Carte du sandbox — RÉSULTATS (Phase 2 terminée)

- **Identité device** (via singleton `fbx.system/Device`) : `model=fbx7hd-delta`, `firmwareVersion=1.5.24.2`, `hdcpVersion=22`, `is4k=true`.
- **Chemin FS app** (leak via LocalStorage) : `/var/lib/databases/fbxqmltv/` — **non writable** par notre contexte. Runtime = `fbxqmltv`.
- **`Application` (fbx.application)** props natives : `accountId` (vide), `profileId` (présent), `appState=2`, `consoleState=0`, `consoleWidget=null`, `remoteMapping="default"`.
- **Modules chargeables en dev** (testés via `Qt.createQmlObject`) : `fbx.application`, `fbx.system`, `fbx.web`, `fbx.debug` (+ open-source : crypto/data/media/ui/hardware/async).
- **Contenu des modules** (qmldir [libfbxqml](https://github.com/fbx/libfbxqml)) : **libs JS/QML utilitaires** (Http, JsonRpc, Oauth, Rest, FreeboxOS, Aes/Sha1, AudioPlayer/VideoPlayer, Pointer…). `fbx.system/Device` = lecture seule. `fbx.debug/Tree` = widget.
- **Modules RESTREINTS** (doc) : `fbx.account`, `fbx.media`, `fbx.cdm` → exigent une **app signée/approuvée** (FreeStore). Non chargeables en dev simple.

### Verdict Phase 2 : pas d'évasion via l'API standard

Le sandbox QML **n'expose aucune primitive** fichier/exec/IPC privilégiée. `file://` bloqué, pas d'écriture, modules bénins.

- **`fbx.web`** = libs JS client (Http/Rest/JsonRpc/FreeboxOS), **pas de WebView**. Types non instanciables (appelés comme `Http.get()`).
- **XHR verrouillé à l'origine** (testé) : l'app n'atteint **que son serveur de manifest**. Player LAN `:80`, `127.0.0.1:80`, hosts publics → **tous status=0**. Donc **pas de SSRF / pas de pivot loopback** vers les services internes.
- `Application.contents` = simple liste des enfants UI.
- **Sandbox réseau + FS hermétique.** Code execution réelle mais confinée.

### Mécanisme de dispatch d'URL (`handleUrl` / `openUrlExternally`)

- L'app peut déclarer `function handleUrl(url)` → le **système lui envoie des actions**. Au lancement : reçoit **`"run"`**.
- `Qt.openUrlExternally(url)` renvoie `true` pour toute URL (`http`, `file://`, `fbx://`, schémas custom) **mais sans effet observable** (aucun navigateur système, notre serveur ne reçoit rien). Pas d'évasion directe constatée.
- Piste ouverte : **vocabulaire des schémas `fbx://`** (verbes privilégiés : install/launch/settings ?) — non documenté, effets non observables côté app. À fuzzer si on trouve un canal de retour.

### 🌐 Pivot navigateur système (WebKit) — via le chooser d'intent

`Qt.openUrlExternally(<http url>)` déclenche un **chooser système** sur la TV (navigateur / app / téléchargements). En choisissant **navigateur**, une page **qu'on sert nous-même** se charge et **exécute son JS** (callbacks GET reçus sur notre serveur).

- **Moteur** : `Mozilla/5.0 (Freebox; fbx7hd-delta/1.5.24.2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15` → **WebKit 605.1.15 / Safari 16**.
- Process distinct du runtime QML `fbxqmltv` → **surface plus large** que le sandbox app.
- `fetch("http://127.0.0.1:80/…")` depuis le navigateur → `Load failed` (loopback :80 non atteignable / bloqué).
- Cible « **mes téléchargements** » non encore testée → potentielle **primitive d'écriture fichier**.
- Capacités testées côté navigateur (matériel possédé) :
  - **`file://` bloqué** (`/etc/passwd`, `/proc/version` → status=0) — même politique que le QML.
  - **Loopback non atteignable** : scan de ~23 ports `127.0.0.1` → aucun `fetch` résolu (rien d'ouvert, ou blocage **Private Network Access** de Safari 16).
- → Le navigateur est un **vrai moteur WebKit** mais **bridé** par ses propres politiques (file://, PNA). Reste exploitable seulement via **bug moteur WebKit** (exploit-dev lourd) — hors périmètre des sondes simples.

### Pistes d'escalade restantes (Phase 3 — recherche)

- [ ] **`fbx.web`** : composant WebView/navigateur embarqué ? → surface browser (file://, bridge JS, exploits moteur web). À introspecter.
- [ ] **Plugin natif via `importPaths`** : le `.fbxproject` mentionne `importPaths`. Charger un plugin QML compilé (.so aarch64) servi par nous ? (probablement restreint aux chemins locaux).
- [ ] **Exploit du moteur Qt/QML** lui-même (corruption mémoire depuis QML/JS arbitraire) → code natif. Lourd.
- [ ] **Module restreint** : voie légitime = soumettre une app signée (FreeStore) — peu réaliste pour du root.
- [ ] **Pivot `fbx.web/FreeboxOS`** : API du Freebox Server (autre device) — hors scope Player.
- [x] ~~file://, exec, écriture FS, modules privilégiés~~ → fermés en dev.
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

## 🔓 FIRMWARE OTA — récupéré en clair (HTTP public)

Capture transparente (Mac = vraie passerelle via Partage Internet, **pas de MITM, pas de bip**) au reboot du Player → protocole OTA complet en **HTTP clair** sur **`fbx-firmware.proxad.net`** (Proxad = Free).

### Protocole de mise à jour

- Manifests JSON par composant : `GET /firmwares/fbx7hd/{boot0+bank0,boot1,bank1}/firmware_info_<MAC>.json?model=948902&mode=free&schema_version=1.0` (+ `.sign`).
- Config device : `GET /config/fbx7hd/cfg_<MAC>.json` (+ `.sign`).
- Chaque manifest contient `file_full_url` + `version` + `version_md5sum`.

### Images (téléchargeables publiquement, md5 vérifiés)

| Image | URL `…/firmwares/fbx7hd/files/` | Taille | Contenu |
|-|-|-|-|
| **bank1** (système) | `bank1/image-fbx7hd_bank1_1.5.24.2` | 137 Mo | kernel+dtbs+rootfs **CHIFFRÉS** |
| **boot0+bank0** | `boot0+bank0/boot0_42.20+bank0_1.2` | 28,8 Mo | **chaîne de boot EN CLAIR** |
| **boot1** | `boot1/boot1_42.20` | 8,4 Mo | bootchain (BOOTCHN) |

(Binaires non commités — gitignore. md5 bank1 `cd14f01adca7d80100569c8afd2bdcfc` ✓.)

### Analyse offline

- **bank1** : conteneur maison (magic `6e48d66b…`, build `rawoul@speedcore`), TOC = `kernel`(0x1000)/`qcom-dtbs`(0x5b3000)/`rootfs`(0x5c1000, 128 Mo). kernel/dtbs en conteneur **`SKRY`** signé ; **rootfs entropie 8.000 → chiffré (AES)**. → **système non reversable offline** sans la clé (TZ/QFPROM, device-bound).
- **boot0+bank0** : conteneur **`BOOTCHN`**, **non chiffré** → binwalk voit des dizaines d'ELF ARM64. Composants : **XBL/SBL1, ABL (UEFI), HYP, cmnlib, DevCfg, Sahara** + **AVB** (`avb+`). Build paths Qualcomm `Msm8998Pkg` (dev `rawoul`).
- **Banking A/B** : `bank0` peut être **forcé par GPIO** (`bank0 boot is forced`, `bank0 boot gpio active`) → **test point hardware de recovery** à identifier (recoupe la voie UART/EDL).

### Analyse secure-boot (1ère passe strings sur boot0+bank0)
Chaîne de confiance Qualcomm **complète et durcie** :
- **Vérif signature à chaque étage** : `ce_rsa_verify_signature`, `km_ecdsa_verify`, `qsee_rsa_verify_signature`, `VerifySignature` ; messages `DTB/kernel signature check failed`, `bad signature on GPT`.
- **Anti-rollback** : `/secboot/anti_rollback`, `KM_TAG_ROLLBACK_RESISTANT` → pas de downgrade vers firmware vulnérable.
- **Racine de confiance en fuses** : `macchiato_read_oem_pk_hash()` (hash clé OEM verified-boot), `QFPROM_CHIP_ID`, `pam_qfprom_rail` → clé OEM + état ancrés en **QFPROM (OTP)**.
- **État de verrouillage** : `is_unlocked: %u` lu via `CRI_CM_IOC_READ_DEVICE_INFO` (device-info custom). **Aucune commande `fastboot oem unlock`** → Free **n'expose PAS de déverrouillage** (pas de fastboot user).
- **`macchiato_*`** = service Qualcomm de provisioning/attestation de clés ECC.

→ **Verdict** : pas de soft-unlock. Bypass bootloader réaliste = **bug mémoire dans le parsing ABL/XBL** (Ghidra) **ou** EDL/Sahara hardware. Conforme à `ATTACK-ROADMAP.md`.

### Carte des composants de la chaîne de boot (extraits de `boot0+bank0`)
14 ELF carvés (program-headers) dans `firmware/bootchain/` (gitignoré). Étiquetés par strings :
| Comp | Offset | Bits | Taille | Rôle |
|-|-|-|-|-|
| **00** | `0x6000` | 64 | 2.6 Mo | **XBL/SBL1** (`sahara` → EDL) |
| 01 | `0x23c060` | 64 | 75 Ko | — |
| **02** | `0x29c000` | 64 | 1.9 Mo | ⭐ **Vérif signature** (`VerifySignature`, `oem_pk_hash`, `macchiato`) |
| 04 | `0x48a000` | 64 | 265 Ko | — |
| **06** | `0x4da000` | 64 | 56 Ko | **Keymaster** (TZ) |
| **11** | `0x5c5000` | 32 | 335 Ko | ⭐ **État unlock** (`is_unlocked`, keymaster) |
| 13 | `0x629000` | 64 | 173 Ko | — |

Pas de composant tagué `fastboot`/`avb_` → **pas de fastboot user** (confirmé).

### 🔬 Décompilation Ghidra (comp11, ARM32) — mécanisme d'unlock élucidé
Pipeline **Ghidra headless** opérationnel (`scripts/ghidra/`, scripts Java car Ghidra 12 = pas de Jython).
- **`FUN_0003b904`** (source de l'état) : appelle **`qsee_is_sw_fuse_blown(1,…)`** → **l'état `is_unlocked` = un fuse OTP QFPROM** (fuse #1). Blown=déverrouillé, sinon verrouillé. Hardware, irréversible.
- **`FUN_0001149c`** (handler de commande, réf. la string `is_unlocked` @ `0x498c6`) : trustlet **QSEE/TrustZone** (`qsee_log`, `qsee_err_fatal`). Vérifie l'état, refuse si déjà provisionné (`*pcVar10==1`), puis **copie un blob de `0x30` octets** (token/clé) — bornes et guards d'overflow présents. = **commande d'unlock/provisioning authentifiée**.
- → **Mécanisme complet** : unlock = blow du fuse QFPROM via une **commande TZ + token signé OEM** (0x30 o). **Pas de soft-unlock** sans la clé OEM. Restent : **bug mémoire** dans la chaîne (parser de `FUN_0001149c` ou vérif amont, comp02), ou **glitch/EDL hardware**.

Scripts : `FindAndDecompileJava.java` (string→xrefs→décompile), `DecompileAt.java` (fonction @ adresse). Usage : `analyzeHeadless <proj> n -import comp11_*.elf -processor ARM:LE:32:v8 -scriptPath scripts/ghidra -postScript FindAndDecompileJava.java is_unlocked -deleteProject` (AArch64 : omettre `-processor`, auto-détecté).

### 🔬 Décompilation comp02 (AArch64) — vérif signature
- **`FUN_1c07b9e4`** (`entering VerifySignature`) : ne traite que **RSA** (key type 0, sinon rejet), charge exp/mod, puis appelle **`ce_rsa_verify_signature`** = **vérif RSA par le moteur crypto matériel** (Qualcomm CE). Signature/data à offsets fixes (`+0x1a2`/`+0x1d6`/`+0x30`/`+0x38`). **Stack canary** présent, fonction propre.
- → **Cœur de vérif robuste (RSA HW)**, pas de faille évidente. La surface de bug réaliste = **parsers amont** (X.509/ASN.1, en-têtes d'image/cert) qui remplissent ces champs.

### Conclusion du fil reverse secure-boot (honnête)
Chaîne de confiance **solide de bout en bout** : vérif RSA HW + lock par **fuse QFPROM** + unlock par **token signé OEM**. **Aucun chemin software trivial.** Les seules ouvertures restantes (toutes lourdes) :
1. **Bug mémoire dans un parser** de la chaîne (X.509/ASN.1, headers d'image) — exploit-dev profond (Ghidra, semaines).
2. **Hardware** : glitch (voltage/EM) du fuse-check ou de la vérif, **EDL/Sahara**, **UART** (`ttyMSM0@115200`), **GPIO bank0**.
Le pipeline Ghidra est en place pour (1) ; (2) attend l'ouverture du boîtier (Eric).

### Cible offline riche (Phase 4) — prep Ghidra faite
La chaîne de boot en clair est extraite et cartographiée. Cibles Ghidra prioritaires :

- [ ] **comp02** (`0x29c000`, 64-bit) : logique `VerifySignature` + `oem_pk_hash` + `macchiato` → chercher un **bug de parsing** dans la vérif de signature.
- [ ] **comp11** (`0x5c5000`, 32-bit) : fonction lisant `is_unlocked` (`CRI_CM_IOC_READ_DEVICE_INFO`) → comprendre la source de l'état, chercher un contournement.
- [ ] **comp00** (`0x6000`, XBL/Sahara) : surface EDL (recoupe `ATTACK-ROADMAP.md`).
- [ ] **XBL/SBL1 + Sahara** : recoupe l'angle EDL (firehose) de `ATTACK-ROADMAP.md`.
- [ ] Trouver la **dérivation de clé** du rootfs (probable TZ → non extractible offline, mais comprendre le schéma).
- [ ] Localiser le **GPIO bank0-forced** → recovery hardware.

## 📚 Sources GPL — [floss.freebox.fr](https://floss.freebox.fr) (`freebox_player_delta/1.5.3`)
Portail de conformité GPL de Free. Seules les **parties open-source** sont publiées (pas de bootloader proprio, pas de runtime `fbxqmltv`, pas de clés). Version la plus proche de notre 1.5.24.2 = **`freebox_player_delta/1.5.3`**. Patch kernel récupéré en local (`firmware/gpl/`, gitignoré).

### Acquis structurants (patch `linux-4.4.302-fbx.patch`, 36 Mo)
- **Kernel = Linux 4.4.302** (BSP Qualcomm MSM8998) + patch Free. Userland **busybox + musl**.
- **Protection rootfs** :
  - **dm-verity** (`CONFIG_SYSTEM_TRUSTED_KEYS="verity.x509.pem"`) → intégrité signée.
  - **AES-HEH** (`heh(aes)`, wide-block) → chiffrement disque (explique l'entropie 8.0 du rootfs).
  - **initrd chiffré RC4** (`CONFIG_FBX_DECRYPT_INITRD`, `fbx_decrypt_initrd.o rc4.o`). ⚠️ Le `.c` de déchiffrement **n'est PAS publié** (Free l'a omis — seul l'appel dans `init/main.c` reste). Clé RC4 absente des sources GPL.
- **Drivers Freebox custom** :
  - `drivers/fbxgpio/` → GPIO Free (le **bank0-forced recovery** est piloté ici).
  - `drivers/mfd/fbx7hd-top-psoc.c` → **PSoC façade** (= la puce `XA9068N01` des photos d'Eric).
  - `drivers/misc/fbxserial_of.c` (`fbxserial.h`) → blob **identité/clés par device**.
- **Pas de LSM custom** (security/ = commoncap/lsm_audit standards). → **Le sandbox "Access prohibited" du QML est userland (runtime `fbxqmltv`), PAS kernel.** Conséquence : du **code natif hors-QML** (post-exploit) ne subirait pas cette restriction de chemin.

### Montage rootfs & boot (analyse du patch kernel)
- **dm-verity** via cmdline `dm="... verity payload=.. hashtree=.. alg=sha1"` (parser `init/do_mounts_dm.c`, style ChromeOS). **dm-verity = intégrité, pas chiffrement.**
- **`req-dm-crypt`** présent = dm-crypt Qualcomm via **ICE (Inline Crypto Engine)** → chiffrement disque HW possible. `heh(aes)` enregistré (mode wide-block). → rootfs prod probablement **verity + dm-crypt ICE**.
- ⚠️ **Cmdline baked dans le kernel = config DEV/USINE NFS** : `root=/dev/nfs ip=…eth0.41:dhcp dhcpclass=linux-fbx7hd earlycon=msm_serial_dm,0xc1b0000 console=ttyMSM0,115200,n8 androidboot.bootdevice=1da4000.ufshc`. → Free boote ses Players de dev **en NFS sur VLAN 41**. Le **cmdline de prod** (`dm=verity/crypt`, root-hash, **clé**) est **injecté par ABL au runtime** → **il faut reverser ABL** pour le schéma de clé (Phase A).
- 🔌 **UART = `ttyMSM0` @ `115200` 8n1** (base `0xc1b0000`) — **param exact pour la capture UART** (Eric / TP5-7).
- 💡 Le rootfs **sur le flash** = squashfs + verity (+ crypt ICE) ; l'image **OTA** est chiffrée séparément (SKRY/heh). Un **dump flash** (UART/EDL) pourrait donner le rootfs déchiffré par l'ICE au runtime — à confirmer.

### À exploiter (offline, sans hardware)
- [x] ~~Cmdline/montage dm-verity~~ → fait (cf. ci-dessus). Paramètres de prod = dans ABL.
- [ ] **CVE locales kernel 4.4.302** (EOL) → utiles SI on obtient un jour du code natif en userland.
- [ ] `fbxserial` : format du blob device (où sont stockées les clés/identité).
- [ ] Récupérer les **autres lignes** floss (`freebox_server_delta`, versions plus récentes) pour un kernel plus proche de 1.5.24.

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

## 🎛️ Namespace HTTP `/pub/*` du Player + télécommande réseau
Le Player expose un namespace `/pub/` (port 80). Énuméré sur le device (~40 candidats) :
- **`/pub/devel`** → 200 (JSON-RPC mode dev, cf. plus haut).
- **`/pub/remote_control`** → 403 sans code. **API télécommande réseau** : `GET /pub/remote_control?code=<CODE>&key=<KEY>` (code dans réglages Player ; codes touches : [dev.freebox.fr/sdk/freebox_player_codes.html](https://dev.freebox.fr/sdk/freebox_player_codes.html)).
- Tout le reste (`system/status/api/update/reboot/exec/shell/…`) → 404.

→ La télécommande réseau permet d'**injecter des touches** (navigation, lancement Netflix/YouTube, on/off) — **utile pour automatiser**, mais **pas un vecteur d'escalade**. Réf. plugin [homebridge-freebox-player-delta](https://github.com/securechicken/homebridge-freebox-player-delta) (détection ON/OFF via AirPlay:7000 ou UPnP:54243).

**Capacité confirmée** (2026-06-27) : avec le **code télécommande réseau** (réglages Player ; *non commité* — secret), `GET /pub/remote_control?code=<CODE>&key=<KEY>` → **HTTP 200**, on pilote le Player (testé `vol_inc`, `power`). Réutilisable pour automatiser des tests (navigation/apps).

### 🔴 Problème "Player orphelin" + objectif root concret
- Ligne Free **résiliée** + Player Devialet **non rattachable** à la box actuelle (Pop ; Free n'autorise que sur Ultra) → le Player reste **orphelin**, **LED façade allumée/clignotante en permanence** (recherche d'appairage), forte conso + pollution lumineuse.
- La touche réseau **`power` (veille) ne calme PAS la LED** : la LED est pilotée par le **PSoC `fbx7hd-top-psoc` / `fbxgpio`** selon l'état d'appairage, **indépendamment de la veille**. Aucun levier software sans root.
- **Sans root** : seul le **débranchement** coupe LED + conso.
- 🎯 **Objectif root concret & motivant** : piloter **`fbxgpio` / le PSoC façade** pour **éteindre la LED** (et idéalement booter un OS qui ne cherche pas d'appairage). Cas d'usage réel qui justifie le jailbreak au-delà d'Android.

## 🧭 Pistes restantes — carte honnête (2026-06-27)
Après reverse complet : root = pas de chemin facile. Voici **tout ce qui reste**, classé par réalisme.

### Software (sur le device, sans ouvrir le boîtier)
| Piste | État | Potentiel | Effort |
|-|-|-|-|
| **AirPlay/RAOP RCE** (daemon réseau on-device, `srcvers 220.68` legacy, `/playback-info` → **500**) | **JAMAIS exploré** | Foothold dans un **process système** (sandbox ≠ QML, peut-être plus faible) | moyen (fuzz/CVE) |
| **RTSP 554 `Freebox rtspd 1.2`** | non fuzzé | parser custom Free | moyen |
| **Bug parser chaîne de boot** (X.509/ASN.1, headers d'image) dans comp00/comp02 | pipeline Ghidra prêt | LE bypass secure-boot software | **élevé** (semaines) |
| **Sahara 0x13** (`XBLRamDumpLib/sbl1_sahara.c`, comp00) | décompilable | si vulnérable → EDL sans loader signé | élevé (analyse automate) |
| **Exploit moteur Qt 5.8 / WebKit 16.4** | écarté (dur, WASM off) | évasion sandbox QML/navigateur | très élevé |

### Hardware (ouvrir le boîtier — Eric)
UART `ttyMSM0@115200` (TP5-7) · EDL/Sahara · GPIO bank0 (recovery) · glitch du fuse-check/vérif RSA. Cf. `ERIC-HARDWARE-BRIEF.md`.

### La plus prometteuse non encore tentée
👉 **AirPlay/RAOP** : **service réseau on-device**, **AirPlay 1 legacy** (pas de pairing/FairPlay), endpoint qui **plante** (`/playback-info` 500). Un bug mémoire = **code exec dans un daemon système**, potentiellement **hors sandbox QML**.

**Sondage (2026-06-27)** : RTSP 5000 répond **sans auth** à `OPTIONS/ANNOUNCE/SETUP/RECORD/SET_PARAMETER/...` → **surface de parsing non authentifiée** (SDP, plist binaire, RTP, décodeur ALAC). AirPlay 7000 : `/server-info` 200, `/playback-info` 500 constant (état "no session"). 
- **Limite** : le binaire du daemon est dans le **rootfs chiffré** → pas de reverse offline. Exploitation = **fuzzing black-box** du device (ANNOUNCE/SETUP/plist) ou CVE RAOP/shairport proche de `220.68`. Effort réel, pas un quick win, mais **c'est la meilleure surface software non-bootloader restante**.

**Fuzzing — 1ère campagne (2026-06-27, `scripts/airplay-fuzz.py`)** :
- Harnais black-box opérationnel (mutations RTSP/SDP/Content-Length/format-string, mode fire-and-forget ~44 cas/s, détection crash par liveness).
- 1er run RTSP 5000 : 2 "crashes" détectés → **faux positifs** (liveness time-out sous la charge du fuzzing). **Rejeu isolé → daemon vivant** : pas de vrai crash. Le **format-string `%n%n%s` est géré** (pas de bug).
- **Détecteur durci** : ne loggue un crash que s'il **re-tue le daemon en rejeu isolé** (anti faux-positif de charge).
- **Verdict provisoire** : parser RAOP **robuste** sur ce premier passage. Un vrai résultat demanderait une **campagne longue** (≫30k cas) + mutations **grammar-aware** (SDP/plist), et idéalement le binaire (hors d'atteinte, chiffré). Surface réelle mais coûteuse.

## Annexes
- [homebridge-freebox-player-delta](https://github.com/securechicken/homebridge-freebox-player-delta) — contrôle local (télécommande réseau).
- [freebox_player_codes](https://dev.freebox.fr/sdk/freebox_player_codes.html) — codes touches télécommande réseau.
- [CVE - Qualcomm](https://www.cvedetails.com/vulnerability-list/vendor_id-153/Qualcomm.html) — pour l'angle bootloader/EDL.
