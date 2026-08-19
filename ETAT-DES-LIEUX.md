# État des lieux — 2026-08-19

> Synthèse du projet pour quelqu'un qui arrive **sans contexte** : ce qui est prouvé,
> ce qui bloque, et les options restantes classées par coût.
> À lire en premier, puis [`SNAPL-TESTMODE.md`](./SNAPL-TESTMODE.md) pour le détail.

## TL;DR

Le README d'origine concluait « cul-de-sac software ». **C'était vrai pour la chaîne
Qualcomm, pas pour le bootloader maison de Free.**

Un composant du firmware, `comp08` = **`snapl`** (`SNAPLDR`, `rawoul@speedcore`, 2019),
n'avait jamais été regardé. C'est du C artisanal, 107 Ko, écrit par une personne. Il
contient un **mode test réseau qui accepte un noyau non signé**.

**Le projet n'est plus bloqué par la cryptographie.** Plus de RSA à casser, plus de
fuse QFPROM, plus de token OEM. Il est bloqué par **une clé de 16 octets scellée en
TrustZone**, et par **l'accès physique au PCB**.

## Ce qui est prouvé

| Acquis | Preuve |
|-|-|
| La vérification de signature de `snapl` est **opt-in** | branchement `0x9fa09c8c` ; bit 0 des `flags` de la partition kernel, **dans l'image qu'on fournit** |
| `boot_from_tag` n'a que **2 appelants** | `0x9fa0a40c` (`mode=1`, flash, signature exigée) et `0x9fa0acd0` (`mode=0`, test-mode, non signé accepté) |
| Le test mode est sélectionné par le **GPIO TLMM 29** | lecture @ `0x9fa00680` **+** DTS GPL (`test-mode` / `force_test_mode`) |
| Polarité : **tirer HAUT** (1,8 V) | `bias-pull-down` dans le DTS, cohérent avec `cbz w20, normal_boot` |
| **Aucun garde-fou de production** | aucune écriture de `w20` entre `0x9fa006c4` et `0x9fa007c4` |
| **Aucun anti-rollback** | seul `version == 2` est testé ; une image signée est acceptée quel que soit son âge |
| **`snapl` n'écrit rien au boot** | `boot_lun_switch` (`0x9fa02490`) a 1 appelant, gardé par `reason == 1` **et** `bank == 1` |
| `bank0` est forçable par le **bouton Factory Reset** | TLMM 18 = `force_bank0`, DTS `apq8098-freebox-batfish.dts` |
| Le bypass fonctionne | `scripts/mkimagetag.py` — même image : rejetée en `mode 1`, acceptée en `mode 0` |

L'outil de vérification est validé **contre l'image de production de Free** : toutes les
portes passent, CRC inclus, et le verdict est bien « signature requise ».

## Le verrou

```
GPIO 29 haut au reset
  └─> snapl entre en test-mode
       └─> DHCP  (on est le serveur, OK)
            └─> fbxauthd   ← ❌ BLOQUÉ ICI
                 └─> tftpboot d'un imagetag non signé
                      └─> boot_from_tag(mode=0) ne vérifie rien
```

`fbxauthd` : UDP **25234**, magic `0x89892df8`. Le Player émet un nonce de 16 o et exige
`MD5(nonce ‖ K)` en retour. `K` (16 o) est fournie par le **trustlet TrustZone `fbxta`**
(`0x9fa0aa14` → `0x9fa08e80`, cmd 2, key_id 1). **Non extractible hors ligne.**

Le chemin d'échec est propre (retour `-1`), pas de confusion de signe exploitable.

## Options restantes

### Offline — rien à allumer, rien à ouvrir

| Option | Intérêt | Note |
|-|-|-|
| **ARP / ICMP** | dernières surfaces pré-auth non auditées | pourrait donner une meilleure primitive |
| **comp00 (XBL) / Sahara** | surface EDL ; c'est lui qui lit le GPIO 18 et remplit `0x9fa00024` | jamais analysé en profondeur |
| **Portage DTS → mainline** | prépare le Linux custom | ne débloque rien, mais sera nécessaire |

### Allumer, sans ouvrir

| Option | Intérêt |
|-|-|
| **`bank0`** (bouton reset maintenu au boot) | système **v1.2** complet (kernel 3,6 Mo + rootfs 16,7 Mo), ~7 ans d'écart de correctifs, surface jamais cartographiée. Ne contourne **aucune** vérification (`mode=1`), mais c'est du code de 2019 |
| **QML debugger** (`qml_port` de `debug_qml_app`) | REPL JS live sur le device, jamais exploré à fond |

### Ouvrir le boîtier

| Option | Intérêt |
|-|-|
| **UART** (`ttyMSM0` @ 115200, TP5/6/7, **1,8 V**) | la visibilité. Sans console, on est aveugle sur tout le reste. **À faire en premier** |
| **GPIO 29** | active le test mode ; strap ~1 kΩ vers **1,8 V** (⚠️ jamais 3,3 ou 5 V) |
| **🎯 Glitch sur l'auth** | **la seule voie qui lève `K` sans exécution de code** |

### Pourquoi le glitch est la piste la plus sérieuse

```
bl   fbxauth              ; 0x9fa0ac28
tbnz w0, #0x1f, echec     ; 0x9fa0ac2c   <- un seul bit à faire sauter
```

et à l'intérieur, un `memcmp` de 16 octets suivi d'un `cbnz`. **Pas besoin de connaître
`K`** : il suffit de corrompre la comparaison au bon instant. `snapl` n'a **aucune
contre-mesure** — pas de double vérification, pas de redondance temporelle, pas de
compteur. Code de bootloader écrit sans modèle de menace fault-injection.

Coût : ChipWhisperer (~300 €) ou glitcher maison + patience sur le timing.

### ⛔ Ne perds pas de temps à essayer de casser `K`

`K` fait 16 octets et est utilisée dans `MD5(nonce ‖ K)`. Elle est **hors d'atteinte**,
pour quatre raisons cumulatives :

| Attaque | Verdict |
|-|-|
| Force brute | 2¹²⁸ — pas « difficile », **impossible** |
| Préimage MD5 | MD5 est cassé en *collision*, **pas en préimage** (~2¹²³ au mieux) |
| Extension de longueur | **Inapplicable** : le secret est en **suffixe** (`nonce ‖ K`). L'attaque exige `K ‖ msg` |
| Cryptanalyse hors ligne | **Aucun matériel à attaquer** : pas une seule paire (nonce, digest valide) |

Ce dernier point est le plus définitif : le Player calcule le digest et le compare **en
interne**, il ne le révèle jamais. Obtenir une paire valide supposerait de connaître déjà
`K`. Et le trustlet `fbxta` qui la détient vit sur une **partition UFS**, pas dans le
bootchain téléchargeable.

### Pourquoi la comparaison, elle, est attaquable

Le réflexe : **on n'attaque pas la primitive cryptographique, on attaque son
implémentation**. Les 128 bits de sécurité se réduisent à l'exécution à une branche :

```
digest = MD5(nonce ‖ K)
memcmp(digest, response+0x14, 16)
cbnz w0, "auth failed !"        ; un bit de décision
```

Trois propriétés rendent cette cible plus favorable que la moyenne en fault injection :

1. **Déterminisme total** — pas d'ASLR, monothread, même séquence d'allocations à chaque
   boot : le timing est reproductible.
2. **Trigger réseau propre** — c'est *toi* qui envoies la réponse UDP, et le `memcmp`
   s'exécute quelques µs plus tard, à délai fixe. Pas besoin de deviner un instant dans
   le boot : on se synchronise sur son propre paquet.
3. **Réessais illimités** — une seule chance d'auth par boot (les 4 retries de
   `0x9fa0ddf8` ne couvrent que le `ETIMEDOUT`, pas l'échec de comparaison), mais rien
   n'empêche de rebooter en boucle.

## Pistes explorées et écartées (ne pas refaire)

| Piste | Verdict |
|-|-|
| Injection de firmware custom via MITM / faux serveur OTA | ❌ manifests signés + `version_md5sum`, **et surtout** signature revérifiée au boot (`mode=1`). Le réseau est hors du périmètre de confiance |
| Downgrade par replay d'un ancien manifest | ❌ il faudrait un ancien manifest signé ; Free ne sert que la version courante |
| Programme bêta (`mode=beta`) | ❌ inscriptions **fermées** aux Player Devialet ([FS#40872](https://dev.freebox.fr/bugs/task/40872)) |
| Exploit WebKit | ❌ moteur mesuré 16.4-16.6, WASM désactivé — cf. [`WEBKIT-LEAD.md`](./WEBKIT-LEAD.md) |
| Fuzzing AirPlay / RAOP | ❌ ~5000 cas, 0 crash réel — parser robuste |
| ARP-spoofing | ❌ détecté par le Player (mise en sécurité + bip) |
| Parser DHCP de `snapl` | ❌ audité, correctement borné |
| Demande de sources GPL à Free | écartée par le propriétaire (choix personnel) |
| Sollicitation de l'infra de Free | **hors périmètre** — ne pas faire |

## ⚠️ Pièce manquante

Une **piste supplémentaire existe mais n'est pas dans ce dépôt**, sur décision du
propriétaire : elle concerne la fenêtre **pré-authentification** de `snapl` et
permettrait de contourner `fbxauthd`.

Son exploitation n'est **pas** aboutie (analyse faite jusqu'à la modélisation du tas ;
la primitive obtenue est un écrasement linéaire vers l'avant, pas une prise de contrôle
du flot fiable). Elle reste privée tant qu'elle n'est pas exploitable, et Free n'a pas
été notifié.

**Si tu reprends le projet : demande ces notes au propriétaire du dépôt.** Ne republie
rien à ce sujet sans son accord explicite.

## Précautions

1. **Ne pas laisser le Player joindre Internet.** Le firmware **1.5.25** est déployé ; une
   MAJ écraserait l'état analysé. Câble débranché, ou segment sans route.
2. Surveiller la version du **bootchain** (**42.20**), pas celle du système (1.5.24.2) :
   c'est elle qui porte `snapl`, et elle se met à jour séparément.
3. **Aucun flash** sans dump de secours. `snapl` ne fait rien écrire au boot (prouvé),
   mais le Linux de `bank0` est chiffré donc son comportement est inconnu.
4. Recon non destructive d'abord, sur **son propre** matériel uniquement.

## Outils du dépôt

| Outil | Usage |
|-|-|
| `scripts/xref-aarch64.py` | xrefs ADRP/ADD dans un ELF AArch64 strippé sans sections — **Ghidra non requis** |
| `scripts/mkimagetag.py` | forge un imagetag et rejoue les portes de `boot_from_tag` hors ligne |
| `scripts/fbx-deploy.py` | déploie/exécute une app QML via le mode dev |
| `scripts/recon.sh` | scan réseau non destructif |
| `scripts/airplay-fuzz.py` | harnais de fuzzing RTSP/RAOP |

```bash
# retrouver n'importe quelle fonction depuis une chaîne
python3 scripts/xref-aarch64.py firmware/bootchain/comp08_0x523000_64bit.elf "test-mode"

# vérifier une image hors ligne, dans les deux modes
python3 scripts/mkimagetag.py verify <image> --mode 1
python3 scripts/mkimagetag.py verify <image> --mode 0
```

## Environnement de reverse

Pas de Ghidra sur la machine d'origine. Le désassemblage se fait avec **capstone**
(`pip install capstone` dans un venv) ; `xref-aarch64.py` n'a besoin que de Python.
Attention : capstone s'arrête au premier bloc de données, donc **décoder les `BL`
directement** pour construire un graphe d'appels (méthode utilisée dans le projet).

Repères mémoire de `snapl` :

```
0x9f9fffe0   pile (SP_EL1, croît vers le bas)
0x9fa00000   image (.text)          <- base de chargement
0x9fa1b000   data/bss
0x9fa1e000   tas — 4 MiB, dlmalloc sur sbrk séquentiel
0x9fe1e000   fin du tas
```

`snapl` tourne en **EL1**, sans ASLR, monothread : l'état mémoire est **déterministe et
reproductible d'un boot à l'autre**.
