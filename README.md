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
├── README.md           # ce fichier — contexte & onboarding
├── FINDINGS.md         # journal des découvertes (réseau, hardware, mode dev, sandbox)
├── PLAN.md             # plan d'exécution code-execution → sondage sandbox → escalade
├── ATTACK-ROADMAP.md   # voie hardware/EDL/bootloader (plan B)
├── app/
│   └── probe/          # app QML de sondage du sandbox (manifest.json + Main.qml)
└── scripts/
    ├── fbx-deploy.py   # ⭐ déploie/exécute une app QML sur le Player (mode dev)
    └── recon.sh        # scan réseau non destructif (nmap + mDNS + SSDP)
```

## 🔥 État actuel — CODE EXECUTION obtenue (2026-06-26)

**Percée** : le Player a un **mode développeur officiel** (réglages → système) qui
active un endpoint **JSON-RPC `http://<player>/pub/devel`**. Protocole reversé depuis
le plugin LGPL `freebox-qtcreator-plugin` et réimplémenté dans **`scripts/fbx-deploy.py`**
(Python pur, sans QtCreator) : on sert un manifest+QML en HTTP local, le Player **fetch
l'app, l'exécute, et streame stdout/stderr**.

| Constat | Détail |
|-|-|
| SoC | **Qualcomm APQ8098** (Snapdragon 835), 2 Go RAM, 32 Go UFS |
| OS | Linux (`linux-fbx7hd`), runtime QML `fbxqmltv` |
| Modèle / firmware | **`fbx7hd-delta`** / **`1.5.24.2`** (lu via `fbx.system/Device`) |
| Surface réseau | 80/8080 (nginx), 554 (rtspd), 5000+7000 (AirPlay) ; ADB/SSH fermés |
| **Mode dev** | `/pub/devel` JSON-RPC `debug_qml_app` → **exécution d'apps QML** ✅ |
| Sandbox | **hermétique** : `file://` bloqué, pas d'exec, XHR limité à l'origine, modules privilégiés réservés aux apps signées |

**Conclusion** : on exécute du code (QML/JS) sur le Player, mais confiné. L'évasion vers
root demande un cran de plus (exploit moteur Qt, module restreint, ou voie hardware).

## 🎯 Objectifs (du plus simple au plus ambitieux)

1. ~~Cartographier la surface d'attaque~~ ✅
2. ~~Trouver un point d'entrée logiciel~~ ✅ (mode dev `/pub/devel`)
3. ~~Activer un mode développeur sans flash~~ ✅
4. **Évader le sandbox QML** → exécution non confinée / shell (en cours).
5. **Stretch** : booter un OS custom / Android.

## 🧩 Pistes d'évasion recherchées (où contribuer)

- [ ] **Exploit du moteur Qt/QML** (5.8) — corruption mémoire depuis QML/JS arbitraire → code natif.
- [ ] **Plugin natif via `importPaths`** — charger un `.so` aarch64 (probablement restreint au local).
- [ ] **Client du QML debugger** (`qml_port` renvoyé par `debug_qml_app`) — REPL JS live sur le device.
- [ ] **Voie hardware** : UART (`TP5/TP6/TP7`) / EDL — cf. [`ATTACK-ROADMAP.md`](./ATTACK-ROADMAP.md).
- [ ] **Dump firmware** `1.5.24.2` (capture OTA transparente) → reverse hors-ligne.

## 🚀 Reproduire / contribuer

Pré-requis : `python3`, `nmap`, `dns-sd`. **Active le mode développeur** sur ton Player
(réglages → système) — c'est ce qui ouvre `/pub/devel`.

```bash
git clone git@github.com:aminekun90/freebox-tool.git
cd freebox-tool

# Déploie l'app de sondage sur TON Player (détecté par MAC, ou --player <ip>)
python3 scripts/fbx-deploy.py app/probe

# Recon réseau (optionnel)
./scripts/recon.sh 192.168.1.0/24 <player-ip>
```

`fbx-deploy.py` sert l'app en HTTP local, appelle `debug_qml_app`, et affiche le
`stdout`/`stderr` de l'app exécutée sur le Player. Reportez vos résultats dans
`FINDINGS.md` puis ouvrez une **PR**.

### Conventions

- Commits **Conventional Commits** (`docs(recon): …`, `feat(scripts): …`).
- Recon **non destructive** d'abord ; pas de fuzzing agressif avant d'avoir compris la surface.
- Documenter chaque étape pour rester réversible (tant qu'on ne flashe rien).
- Ne committez **jamais** de secrets (tokens API Freebox, clés).

## ⚠️ Réalité connue (honnêteté d'entrée)

- Aucune méthode publique vérifiée pour installer Android sur le Player Delta.
- Le Player Delta tourne un **OS maison Free** (Linux, runtime QML `fbxqmltv`), ≠ Android TV du Player Pop.
- **Le matériel n'est PAS le problème** : APQ8098 = Snapdragon 835, Android-natif. Le verrou est **logiciel** (chaîne de boot signée + sandbox app).
- **Acquis** : exécution de code QML/JS sur le Player via le mode dev officiel (`fbx-deploy.py`).
- **Mur actuel** : le sandbox QML est hermétique ; l'évasion vers root reste à faire (exploit moteur, ou voie hardware UART/EDL — cf. [`ATTACK-ROADMAP.md`](./ATTACK-ROADMAP.md)).
</content>
