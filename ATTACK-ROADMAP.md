# Attack Roadmap — Freebox Delta Player → Android

> Dossier d'attaque pour développeurs open source. Objectif : ouvrir la chaîne de
> boot du **Freebox Delta Player (Devialet)** afin d'y porter Android (AOSP/LineageOS).
>
> La recon **réseau** est terminée et c'est un cul-de-sac (voir `FINDINGS.md`).
> Ce document décrit la voie **bootloader / EDL / hardware**, qui est désormais
> la seule réaliste, et où chaque contributeur peut prendre le relais.

## TL;DR — où en est-on

- **Hardware 100 % capable** : SoC **Qualcomm APQ8098** (= MSM8998 / Snapdragon 835 sans modem), 2 Go RAM, 32 Go eMMC. Même puce que Pixel 2 / OnePlus 5 / Galaxy S8 → Android tourne nativement.
- **Verrou = chaîne de boot signée**, pas le matériel. Secure Boot Qualcomm + firmware Free signé.
- **Le projet se ramène à UN artefact** : le **firehose programmer signé par Free** pour ce board. Avec lui, l'exploit peek/poke d'Aleph donne EL3 → contrôle total. Sans lui, l'EDL est inerte sur MSM8998.

## Pourquoi l'EDL seul ne suffit pas (sur ce SoC)

| Fait établi | Source |
|-|-|
| L'EDL (mode 9008) exige un firehose **signé**, matché par hardware-ID + hash de clé publique | [bkerler/edl loader mgmt](https://deepwiki.com/bkerler/edl/3.5-loader-management) |
| Le bypass Secure Boot peek/poke (EL3, dump PBL) est **post-authentification** : il faut un firehose **déjà en exécution** | [ALEPH-2017028](https://alephsecurity.com/vulns/aleph-2017028) |
| L'extraction PBL *sans* loader signé (niveau Sahara) n'est démontrée que sur MSM8994/8937/8953/8974 — **pas MSM8998** | [Aleph EDL series](https://alephsecurity.com/2018/01/22/qualcomm-edl-1/) |

→ Conclusion : sur APQ8098 avec Secure Boot actif, **brancher l'EDL sans le firehose Free ne donne rien**.

## Arbre de décision

```
Obtenir un accès bas-niveau ?
├── (A) Firehose Free signé récupéré ?
│      ├── OUI → edl.py + peek/poke (ALEPH-2017028) → EL3 → dump eMMC + patch aboot → flash Android
│      └── NON → voir (B) / (C)
├── (B) Shell root au boot via UART ?
│      └── OUI → dd des partitions, lire aboot/XBL, analyser secure boot → bypass logiciel
└── (C) Lecture physique de l'eMMC (ISP / chip-off) ?
       └── OUI → dump firmware complet → reverse hors ligne → chercher faille de vérif signature
```

## Tâches ouvertes (par coût croissant, toutes légales sur matériel possédé)

### Tier 0 — Pure recherche doc (aucun hardware requis)
- [ ] **Localiser un firmware/OTA Free du Player Devialet.** Le `prog_firehose_*.elf` est rarement dans l'OTA (outil d'usine), mais vérifier : serveurs OTA Free, dumps communautaires, forums `lafibre.info`, `freebox.toosurtoo.com`, archives.
- [ ] **Identifier le hardware-ID / MSM-ID exact** du board (utile pour matcher un firehose). Visible via Sahara hello en EDL, ou dans le firmware.
- [ ] **Recenser les firehose MSM8998 publics** (autres devices SD835) et tester s'ils passent — improbable si QFuse blown, mais certains boards de prod ont le secure boot non verrouillé. Liste : [XDA firehose loaders](https://xdaforums.com/t/identifying-edl-firehose-loaders.4525079/).
- [ ] **Veille CVE chaîne de boot MSM8998** : XBL/ABL/LK, anti-rollback, Sahara. Réévaluer [CVE-2021-1931](https://xdaforums.com/t/xz1c-xz1-xzp-xperable-xperia-abl-fastboot-exploit-cve-2021-1931.4771931/) (Sony-only aujourd'hui) si une surface fastboot apparaît.

### Tier 1 — Investigation hardware non destructive (besoin du board ouvert)
- [ ] **Repérer l'UART** (TX/RX/GND, souvent 1.8 V) sur la carte. Capturer le log de boot (U-Boot/LK) → révèle bootloader, version, éventuel shell.
- [ ] **Repérer les test points EDL** : court-circuiter au GND au boot jusqu'à énumérer `Qualcomm HS-USB 9008`. Documenter leur position (photo annotée).
- [ ] **Dumper le hello Sahara** avec `edl.py` une fois en 9008 → hardware-ID, PK hash, état secure boot.

### Tier 2 — Extraction (plus invasif)
- [ ] **Si shell UART root** : `dd` des partitions (`aboot`, `xbl`, `boot`, `system`) → upload pour reverse collectif.
- [ ] **Sinon ISP eMMC** (pads ISP) ou chip-off en dernier recours → dump complet.

### Tier 3 — Portage Android (après ouverture du boot)
- [ ] Construire le **device tree** APQ8098 pour ce board (basé sur un device SD835 mainline proche : OnePlus 5 `cheeseburger`, etc.).
- [ ] Drivers spécifiques : audio Devialet, HDMI, WiFi/BT.
- [ ] Cibler **LineageOS** ou AOSP minimal, puis Android TV.

## Outils de référence

| Outil | Usage |
|-|-|
| [`bkerler/edl`](https://github.com/bkerler/edl) | client Sahara/Firehose (dump, flash, peek/poke) |
| [`strongtz/edl-ng`](https://github.com/strongtz/edl-ng) | variante moderne (baseline ≥ MSM8998) |
| Aleph **Firehorse** | framework d'exploitation EDL (peek/poke → EL3) |
| `picocom` / analyseur logique | capture UART |
| `binwalk` / `unblob` | reverse des dumps firmware |

## Ce dont les contributeurs ont besoin

1. **Un Player Delta Devialet possédé** (jamais sur du matériel tiers).
2. Câble **UART-USB 1.8 V**, multimètre, éventuellement adaptateur **ISP eMMC**.
3. Reporter **photos annotées** (UART/test points), **dumps Sahara hello**, **logs de boot** dans une issue/PR.

## Ce qu'on NE fait pas

- Pas de redistribution de firmware/clés propriétaires Free dans le dépôt (liens/hashes OK, binaires non).
- Pas de contournement de DRM commercial, pas d'attaque d'infra Free distante.
- Tout sur **son propre** appareil, à but de réappropriation matérielle.
