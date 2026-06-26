# Freebox Tool — Devialet/Freebox Delta Player reverse-engineering

> Reprise de contrôle logicielle d'un **Freebox Delta Player (conçu par Devialet)**,
> devenu inutile sans abonnement TV Free. **North star : faire tourner Android
> dessus, en jailbreak 100 % software.** Repli accepté : obtenir un shell, ou
> réutiliser la machine en **enceinte AirPlay autonome**.

Projet **open source** — recon, notes et outils sont publics pour que d'autres
propriétaires de Player Delta puissent reproduire, vérifier et avancer ensemble.

## ⚖️ Éthique & périmètre

Démarche de **rétro-ingénierie sur du matériel possédé, sur son propre réseau**.

- ✅ Recon non destructive, lecture de services exposés sur le LAN, doc des résultats.
- ❌ Pas d'attaque de tiers, pas de contournement de DRM pour du piratage, pas de
  scan d'appareils qu'on ne possède pas.

Ne contribuez avec des résultats que sur **votre propre** Player Delta.

## 📦 Structure du dépôt

```
freebox-tool/
├── README.md        # ce fichier — contexte & onboarding
├── FINDINGS.md      # journal des découvertes (ports, services, mDNS, pistes)
└── scripts/
    └── recon.sh     # scan réseau non destructif (nmap + mDNS + SSDP + sonde ADB)
```

## 🔎 État actuel (2026-06-26)

Premier scan réseau effectué sur un Player Delta réel (détails dans `FINDINGS.md`) :

| Constat | Détail |
|-|-|
| Vendor MAC | `FREEBOX SAS` (`34:27:92:…`) |
| Ports ouverts | 80/8080 (nginx), 554 (`Freebox rtspd 1.2`), 5000+7000 (AirPlay/RAOP) |
| ADB 5555 | **fermé** |
| SSH / telnet | absents |
| AirPlay | `srcvers 220.68`, **`pw=false`** → streaming audio ouvert (enceinte OK) |
| OS sous-jacent | **Linux** probable (nginx + rtspd + récepteur RAOP soft), pas Android exposé |

**Conclusion provisoire :** appliance Linux verrouillée, surface réseau minimale.
La voie « Android par le réseau » est étroite. Pistes encore ouvertes ci-dessous.

## 🎯 Objectifs (du plus simple au plus ambitieux)

1. **Cartographier la surface d'attaque** : ports, services, bannières, mDNS/UPnP.
2. **Trouver un point d'entrée logiciel** : ADB, shell, web/dev caché, API Free/Devialet.
3. **Activer un mode développeur** sans flash (debug, services cachés).
4. **Obtenir un shell**.
5. **Stretch** : booter un OS custom / Android, OU exposer proprement l'audio.

## 🧩 Pistes recherchées (où contribuer)

- [ ] **Fuzzing chemins nginx** (80/8080) — l'UI Free vit peut-être sur un vhost / `Host` header (`mafreebox.freebox.fr`).
- [ ] **RTSP `Freebox rtspd 1.2`** (554) — surface custom Free, parsing à analyser.
- [ ] **RAOP `srcvers 220.68`** — chercher CVE/exploits sur récepteurs AirPlay legacy.
- [ ] **Console série / UART** sur la carte — repli matériel si le réseau est un cul-de-sac.
- [ ] **Dumps firmware** / analyse du SoC (modèle, bootloader, signature).

## 🚀 Reproduire / contribuer

Pré-requis (macOS) : `nmap`, `adb`, `nc`, `dns-sd`.

```bash
git clone git@github.com:aminekun90/freebox-tool.git
cd freebox-tool

# 1) Trouver l'IP de TON player (Freebox OS → DHCP/Appareils, ou ping sweep)
./scripts/recon.sh 192.168.1.0/24

# 2) Scan complet d'une cible que tu possèdes
./scripts/recon.sh 192.168.1.0/24 <player-ip>
```

Le scan écrit un log `recon-<ip>-<date>.log`. Reportez les résultats notables
dans `FINDINGS.md` puis ouvrez une **PR** ou une **issue**.

### Conventions

- Commits **Conventional Commits** (`docs(recon): …`, `feat(scripts): …`).
- Recon **non destructive** d'abord ; pas de fuzzing agressif avant d'avoir compris la surface.
- Documenter chaque étape pour rester réversible (tant qu'on ne flashe rien).
- Ne committez **jamais** de secrets (tokens API Freebox, clés).

## ⚠️ Réalité connue (honnêteté d'entrée)

- Aucune méthode publique vérifiée pour installer Android sur le Player Delta.
- Le Player Delta tourne un **OS maison Free** (≠ Android TV du Player Pop).
- Bootloader probablement verrouillé/signé → l'angle **flash hardware est hostile**.
- L'angle **services réseau** reste le point de départ le moins coûteux.
</content>
