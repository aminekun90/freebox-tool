# freebox-tool — Claude Context

Rétro-ingénierie d'un **Freebox Delta Player (Devialet)** possédé, rendu inutile sans
abonnement TV. North star : y faire tourner Android en jailbreak 100 % software. Replis
acceptés : un shell, ou une enceinte AirPlay autonome. Dépôt **public**.

## Lire ça d'abord, dans cet ordre

1. **`ETAT-DES-LIEUX.md`** — la synthèse. Ce qui est prouvé, ce qui bloque, les options
   classées par coût, et les pistes déjà écartées. Aucune session ne devrait commencer
   ailleurs.
2. **`SNAPL-TESTMODE.md`** — le détail du mode test de `snapl`.
3. `FINDINGS.md` (708 l.) — le journal brut. À consulter par recherche, pas à lire.

Le reste (`PLAN*.md`, `ATTACK-ROADMAP.md`, `WEBKIT-LEAD.md`, `ERIC-HARDWARE-BRIEF.md`)
est du contexte historique.

## L'état du projet en trois phrases

Le blocage n'est **plus cryptographique**. `snapl` (`comp08`, bootloader maison de Free,
2019) a un mode test sélectionné par le **GPIO TLMM 29** qui accepte un noyau non signé.
Ce qui bloque maintenant, c'est `fbxauthd` (UDP 25234, `MD5(nonce ‖ K)`) dont la clé `K`
de 16 octets est scellée dans le trustlet TrustZone `fbxta` — et l'accès physique au PCB.

## Pièges

**La branche de travail a été fusionnée et supprimée.** PR #1 a été *squashée* dans
`main` le 19 août 2026 : `main` porte tout le contenu, en un seul commit. Une copie locale
de `recon/snapl-testmode` peut traîner sur une machine avec un `origin/…` fantôme — un
`git fetch --prune` la fait disparaître. **Partir de `main`**, et ne pas croire un
`git log origin/main..recon/snapl-testmode` qui affichera dix commits déjà fusionnés.

**`PRIVATE-*` ne doit jamais être commité.** `.gitignore` les couvre
(`PRIVATE-handoff.md`, `PRIVATE-snapl-notes.md` sont présents sur disque). Ils portent une
piste pré-authentification non aboutie, non divulguée à Free. Ne jamais les citer, les
recopier, ni en publier le contenu dans un fichier suivi — le dépôt est public.

**`firmware/*` est ignoré**, sauf `.gitkeep` et `readme`. Les images (`bootchain/`,
`image-fbx7hd_bank1_1.5.24.2`, `rootfs.enc`, `abl.elf`) sont sur disque mais hors dépôt.
Les scripts en dépendent : sur un clone frais, **rien de ce qui suit ne tourne** tant que
`capture-ota.sh` n'a pas reconstitué `firmware/`.

**Ne pas laisser le Player joindre Internet.** Le firmware **1.5.25** est déployé ; une
mise à jour écraserait l'état analysé (bootchain **42.20**, système 1.5.24.2). Câble
débranché ou segment sans route. C'est la seule erreur irréversible du projet.

**Aucun flash sans dump de secours.** `snapl` n'écrit rien au boot — c'est *prouvé*
statiquement (`boot_lun_switch` @ `0x9fa02490`, un seul appelant, gardé par `reason == 1`
**et** `bank == 1`) — mais le Linux de `bank0` est chiffré, donc son comportement est
inconnu.

**GPIO 29 : tirer à 1,8 V, jamais 3,3 ni 5 V.** Strap ~1 kΩ. UART `ttyMSM0` @ 115200 sur
TP5/6/7, **1,8 V** également.

**`capstone` n'est pas installé sur cette machine** (`import capstone` → ImportError).
Le désassemblage veut un venv (`pip install capstone`). En revanche `xref-aarch64.py`
n'a besoin que de Python standard — c'est lui qu'on utilise en premier.

**capstone s'arrête au premier bloc de données.** Pour un graphe d'appels, décoder les
`BL` directement plutôt que de faire confiance au flot linéaire.

**Ghidra n'est pas requis** malgré `scripts/ghidra/*.java` : ces deux scripts sont là pour
qui en dispose. La méthode du projet est sans Ghidra.

## Commandes (vérifiées ici, firmware présent sur disque)

```bash
# Retrouver le code qui touche une chaîne, dans un ELF AArch64 strippé sans sections
python3 scripts/xref-aarch64.py firmware/bootchain/comp08_0x523000_64bit.elf "test-mode"
#   0x009fa17cb0  'test-mode'
#       xref @ 0x009fa0a188   (in func ~0x009fa09aa0)     <- boot_from_tag

# Rejouer hors ligne les portes de boot_from_tag sur une image
python3 scripts/mkimagetag.py verify firmware/image-fbx7hd_bank1_1.5.24.2 --mode 1
#   toutes les portes [OK ], puis : verify_signature() APPELE
python3 scripts/mkimagetag.py verify firmware/image-fbx7hd_bank1_1.5.24.2 --mode 0
#   VERDICT : signature requise
#   ^ normal : l'image de prod porte flags bit0 = 1, elle se DÉCLARE signée.
#     C'est tout l'intérêt du mode 0 — le bit est dans l'image qu'on fournit,
#     donc une image forgée sans --signed-flag passe en mode 0 et pas en mode 1.

python3 scripts/mkimagetag.py build --kernel Image --dtb board.dtb -o bank.img
python3 scripts/fbx-deploy.py <app_dir> --player <ip> --seconds <n>   # app QML, mode dev
./scripts/recon.sh 192.168.1.0/24 [<ip>]                              # scan non destructif
```

`mkimagetag.py verify` est une réimplémentation fidèle de `boot_from_tag()`
(`comp08` @ `0x9fa09aa0`), porte par porte, validée contre l'image de production de Free.

## Repères mémoire de `snapl`

```
0x9f9fffe0   pile (SP_EL1, croît vers le bas)
0x9fa00000   image (.text)          <- base de chargement
0x9fa1b000   data/bss
0x9fa1e000   tas — 4 MiB, dlmalloc sur sbrk séquentiel
0x9fe1e000   fin du tas
```
**EL1, pas d'ASLR, monothread** : l'état mémoire est déterministe et reproductible d'un
boot à l'autre. C'est ce qui rend le timing d'une injection de faute exploitable.

## Ne pas refaire — pistes déjà écartées
MITM / faux serveur OTA · downgrade par replay de manifest · programme bêta (fermé aux
Player Devialet) · exploit WebKit (16.4-16.6, WASM désactivé) · fuzzing AirPlay/RAOP
(~5000 cas, 0 crash) · ARP-spoofing (détecté par le Player) · parser DHCP de `snapl`
(correctement borné) · **casser `K`** (2¹²⁸, MD5 non cassé en préimage, secret en suffixe
donc pas d'extension de longueur, et aucune paire (nonce, digest) observable).

Le détail des verdicts est dans `ETAT-DES-LIEUX.md` — le relire avant de proposer une de
ces pistes.

## Périmètre
Matériel **possédé**, réseau personnel. Recon non destructive. Pas d'attaque de tiers, pas
de contournement de DRM à fin de piratage, pas de scan d'appareils qu'on ne possède pas.
**Ne pas solliciter l'infrastructure de Free** — explicitement hors périmètre. La demande
de sources GPL a été écartée par le propriétaire.
