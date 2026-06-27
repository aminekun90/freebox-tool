# Plan — Phase suivante : bootloader (ABL) + hardware

> Reprise après l'épuisement de la voie software pure (cf. `WEBKIT-LEAD.md`,
> `FINDINGS.md`). Les vraies pistes sont maintenant **bootloader (firmware en clair)**
> et **hardware (UART/EDL/GPIO)**. Matériel possédé, recherche légale, aucun flash
> avant dump de secours.

## Acquis qui rendent ça possible
- **Firmware complet récupéré** (OTA HTTP public, md5 vérifiés) — local, gitignoré.
- **`boot0+bank0` (28 Mo) EN CLAIR** : conteneur `BOOTCHN`, ELF ARM64 (XBL/ABL/HYP/Sahara, AVB).
- Système (kernel+rootfs) **chiffré** → clé en TZ/QFPROM, non extractible offline.
- Indices : **`bank0` forçable par GPIO** (recovery), Sahara présent (EDL).

---

## Volet A — Reverse du bootloader ABL (offline, sur le firmware)
**But** : comprendre la chaîne de confiance et chercher un défaut de vérification / une commande d'unlock.

### A1. Extraire les composants de `boot0+bank0`
- [ ] Parser le conteneur `BOOTCHN` (header `424f4f54 43484e00` = "BOOTCHN") → table des sous-images (xbl, abl, hyp, tz, devcfg, cmnlib, bank0…).
- [ ] `binwalk -e` + carve manuel par offset. Isoler **ABL** (le bootloader UEFI Android) et **XBL/SBL1**.

### A1bis. Composants déjà extraits (prep faite)
14 ELF carvés dans `firmware/bootchain/` (gitignoré), via program-headers. Cibles :
| Fichier | Bits | Base load | Contient | Adresses utiles |
|-|-|-|-|-|
| `comp11_0x5c5000_32bit.elf` | ARM32 | PT_LOAD `0x0` | **`is_unlocked`** | string @ vaddr **`0x398c6`** → chercher xrefs (ADR Thumb) = fonction de lecture lock-state |
| `comp02_0x29c000_64bit.elf` | AArch64 | (cf. phdr) | **`VerifySignature`, `oem_pk_hash`, `macchiato`** | logique de vérif signature |
| `comp00_0x6000_64bit.elf` | AArch64 | (cf. phdr) | **`sahara`** (XBL) | surface EDL |

**Import Ghidra** : ouvrir le `.elf` directement (Ghidra lit les program headers ; ELF stripped sans sections → désassemblage via segments PT_LOAD). Langage : `ARM:LE:32:v8` (comp11) / `AARCH64:LE:64:v8` (comp02/00). Puis *Search → For Strings* → `is_unlocked` / `VerifySignature` → *References to* → remonter à la fonction.

### A2. Désassembler ABL (Ghidra)
- [ ] Charger ABL (ELF AArch64) dans **Ghidra**. C'est un module **UEFI** (PE/TE sections possibles).
- [ ] Cibler :
  - la **vérification de signature** des images (boot/recovery) — y a-t-il un chemin où elle est sautée ?
  - la gestion **`unlock` / device state** (verrouillé/déverrouillé), fuses lus.
  - le **parsing fastboot** (commandes OEM, variables) — surface d'entrée classique de bugs.
  - **AVB** (Android Verified Boot) : version, rollback index, clés.
- [ ] Chercher un **bug mémoire** dans le parsing (fastboot, partitions, image headers) exploitable pour exécution dans ABL (EL1/EL2).

### A3. XBL / Sahara → recoupe l'EDL
- [ ] Identifier la version exacte XBL/SBL1 → relier aux vulns EDL/Sahara connues (cf. `ATTACK-ROADMAP.md`).
- [ ] Déterminer si le **firehose** Free est embarqué quelque part / dérivable.

### A4. Schéma de chiffrement du rootfs
- [ ] Dans XBL/TZ : localiser la **dérivation de clé** (HW key + QFPROM ?) du conteneur `SKRY`/rootfs. But : comprendre (pas forcément casser) — confirme si une clé device-bound bloque tout dump exploitable hors device.

---

## Volet B — Hardware (nécessite d'ouvrir le boîtier — pour Eric / plus tard)
**But** : accès bas-niveau direct (shell de boot, EDL, recovery).

### B1. UART (le plus rentable)
- [ ] Souder/sonder **TP5 / TP6 / TP7** (TX/RX/GND, 1.8 V) — pinout d'après [EricBlanquer/freebox-devialet-hack].
- [ ] Adaptateur **CP2102**, `picocom -b 115200` (tester 115200/921600).
- [ ] Capturer le **log de boot** (XBL→ABL→kernel) : versions, éventuel **prompt shell** ou interruption bootloader (touche).
- [ ] Si shell : `dd` des partitions lisibles, lecture conf, recoupe avec le firmware.

### B2. Recovery bank0 par GPIO
- [ ] Identifier le **GPIO `bank0-forced`** (strings : `bank0 boot gpio active`, `bank0 boot is forced`) → quel test point/pad force le boot bank0 (mode recovery/factory).
- [ ] Observer ce que bank0 expose (mode dégradé = parfois plus permissif : fastboot ouvert, vérifs relâchées).

### B3. EDL (mode 9008)
- [ ] Court-circuiter les **test points EDL** au boot → énumération `Qualcomm HS-USB 9008`.
- [ ] `edl.py` (bkerler) : dump du hello Sahara (hardware-ID, état secure boot). Voir `ATTACK-ROADMAP.md`.

---

## Arbre de décision
```
Firmware ABL en clair → reverse Ghidra (Volet A)
├── Faille de vérif signature / unlock trouvée → flash image custom (avec dump de secours)
├── Bug fastboot/parsing → exécution ABL → désactiver vérifs → boot non signé
└── Rien d'exploitable offline → Volet B (hardware)
        ├── UART : shell de boot ? interruption bootloader ?
        ├── GPIO bank0 : recovery plus permissif ?
        └── EDL : dump + analyse, recoupe Sahara
```

## Règles
- **Aucun flash** avant : (1) dump complet de secours via EDL/UART, (2) plan de récupération validé (le GPIO bank0 / EDL = filet).
- Documenter chaque étape (offsets, commandes, logs) dans `FINDINGS.md`.
- Pas de redistribution de binaires firmware/clés (gitignore en place).

## Outils
| Outil | Usage |
|-|-|
| Ghidra | désassemblage ABL/XBL (AArch64/UEFI) |
| binwalk / unblob | carve des conteneurs BOOTCHN/SKRY |
| bkerler/edl | Sahara/Firehose (EDL) |
| picocom + CP2102 | capture UART |
| QEMU (option) | émulation partielle d'ABL pour fuzzing |

## Priorité conseillée
1. **A1+A2** (reverse ABL) — faisable **maintenant**, sur le firmware déjà téléchargé, sans hardware.
2. **B1** (UART) — quand le boîtier est ouvert (Eric).
3. B2/B3 selon résultats.
