# Freebox Delta Player — Software Jailbreak Project

## Ambition

> **But du projet : jailbreaker le Devialet Player (Freebox Delta) et y installer Android.**

Redonner vie à un **Freebox Delta Player (conçu par Devialet)** acheté ~450 € et
devenu inutile sans abonnement TV Free. Le **north star** = faire tourner
**Android** dessus, via un **jailbreak 100 % software** (aucune modif hardware au
départ). Repli acceptable si Android s'avère hors d'atteinte : obtenir un shell /
réutiliser la machine en **enceinte Devialet autonome** (protocoles audio).

C'est **mon matériel, acheté, sur mon réseau** — démarche de rétro-ingénierie et
de recon défensive sur un appareil que je possède. Pas d'attaque de tiers, pas de
contournement de DRM pour du piratage : reprise de contrôle de ma propre machine.

## Objectifs (du plus simple au plus ambitieux)

1. **Cartographier la surface d'attaque** : IP, ports ouverts (TCP/UDP), services,
   bannières, interfaces de debug/dev.
2. **Trouver un point d'entrée logiciel** : ADB réseau (5555), shell (telnet/ssh),
   web admin/dev caché, API locale Devialet/Free, UPnP, endpoints non protégés.
3. **Activer des flags / mode développeur** sans flash : debug, ADB, services cachés.
4. **Obtenir un shell** sur la machine.
5. **Stretch** : booter un OS custom / Android, OU exposer proprement l'audio
   (AirPlay/Cast/Spotify Connect/DLNA) pour un usage enceinte.

## Réalité connue (honnêteté d'entrée)

- Aucune méthode publique vérifiée pour installer Android sur le Player Delta.
- Le Player Delta tourne un **OS maison Free** (≠ Android TV du Player Pop).
- Bootloader probablement verrouillé/signé → l'angle **flash hardware est hostile**.
- **MAIS** l'angle **services réseau** est inexploré et c'est là qu'on commence :
  un appareil Devialet expose en général beaucoup de services LAN (mDNS, UPnP,
  API Spark Devialet…). Le test décisif « y a-t-il un Android/Linux ouvert
  dessous » = **port 5555 (ADB)** et la présence d'un shell.

## Pré-requis (déjà prêts)

- `nmap`, `adb` installés (Homebrew), `nc`, `dns-sd` (macOS).
- Accès API Freebox (token en cache dans `../k8s-project/scripts/.fbx_token.json`,
  droit *settings*) → permet de **lister les baux DHCP** pour trouver l'IP du Player.

## Plan pour demain (device branché)

1. Brancher le Player au réseau (Ethernet de préférence, plus stable pour le scan).
2. **Trouver son IP** :
   - Freebox OS → Paramètres → DHCP / Appareils, repérer l'hôte Devialet/Freebox,
   - ou `./scripts/recon.sh 192.168.1.0/24` (ping sweep + ARP).
3. **Scanner** : `./scripts/recon.sh 192.168.1.0/24 <player-ip>` (full TCP + UDP
   clés + version + mDNS + SSDP + sonde ADB).
4. Noter **tout** dans `FINDINGS.md`.
5. Selon les ports trouvés, choisir l'angle (ADB connect, web, telnet, API audio).

## Sécurité / garde-fous

- Recon **non destructive** d'abord (scan, lecture). Pas de fuzzing agressif tant
  qu'on n'a pas compris la surface.
- Tout est réversible tant qu'on ne flashe rien.
- On documente chaque étape pour pouvoir revenir en arrière.
