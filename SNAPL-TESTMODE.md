# snapl — bypass de secure-boot par le mode test (analyse statique)

> Reverse de `comp08` (= **`snapl`**, le bootloader maison de Free) extrait de
> `boot0+bank0`. Analyse **100 % offline** sur firmware public déjà téléchargé.
> Matériel possédé, aucune écriture, aucun flash.

## TL;DR

`snapl` contient un **mode test réseau, sélectionné par un GPIO**, qui **accepte un
noyau non signé**. La vérification de signature n'est pas inconditionnelle : elle est
**opt-in, pilotée par un bit de flag dans l'image qu'on fournit soi-même**, et le
chemin de boot réseau désactive cette exigence.

Le verrou n'est donc plus « casser RSA / brûler un fuse ». Il s'est déplacé sur
**un handshake `fbxauthd` en MD5 dont la clé de 16 octets vit dans un trustlet
TrustZone**. Et ce handshake arrive **après** que le bootloader ait déjà parsé des
paquets entièrement contrôlés par l'attaquant — 🔒 un résultat existe sur cette
fenêtre pré-auth, non publié (divulgation en cours).

## Identification du composant

`comp08_0x523000_64bit.elf`, 120 Ko, AArch64, `PT_LOAD` @ `0x9fa00000`, entry `0x9fa00000`.

| Indice | Valeur |
|-|-|
| Bannière | `SNAPLDR`, ASCII-art `snapl` |
| Build | `rawoul@speedcore`, `Fri Feb  8 14:48:43 UTC 2019` |
| Entrée | `ipl_main() returned with %d` |
| Nature | **code Freebox**, pas Qualcomm — pile réseau, GPT, UFS, i2c, SPI, PCIe maison |

C'est le maillon qui charge kernel + DTB et applique le FDT. Beaucoup plus petit et
plus artisanal que XBL/ABL — surface d'audit tractable.

## Format conteneur des images de bank

En-tête de `image-fbx7hd_bank1_1.5.24.2` (décodé, big-endian) :

| Offset | Champ |
|-|-|
| `+0x00` | CRC32 de `[+0x04, 0x214[` |
| `+0x04` | magic `0x3658382b` |
| `+0x08` | version, doit valoir `2` |
| `+0x0c` | taille totale déclarée |
| `+0xb4` | nombre de partitions, **max 8** |
| `+0xbc` | table de partitions, stride `0x2c` |

Entrée de partition : `{u32 offset, u32 size, u32 type, u32 flags, …, char name[16]}`.
Types observés : `0` = kernel, `1` = (optionnel), `3` = DTB. Table réelle du bank1 :

| Nom | Offset | Taille |
|-|-|-|
| `kernel` | `0x00001000` | 5 970 424 |
| `qcom-dtbs` | `0x005b3000` | 56 952 |
| `rootfs` | `0x005c1000` | 130 990 080 |

`kernel` et `qcom-dtbs` sont enveloppés dans un conteneur **`SKRY`** (600 o d'en-tête) ;
`rootfs` est du chiffré brut. Structure `SKRY` déduite :

| Offset | Taille | Contenu |
|-|-|-|
| `0x000` | 16 | `SKRY`, version 3, taille en-tête `0x258`, taille payload |
| `0x014` | 256 | blob de clé AES enveloppé RSA-2048 |
| `0x114` | 64 | empreinte SHA-512 |
| `0x154` | 4 | sous-magic `SK31` |
| `0x158` | 256 | signature RSA-2048 |

## Le bypass

### `boot_from_tag(tag, size, mode)` @ `0x9fa09aa0`

Deux appelants, **et un seul passe `mode = 0`** :

| Site | `mode` | Chemin |
|-|-|-|
| `0x9fa0a40c` | `1` | boot flash normal — signature **exigée** |
| `0x9fa0acd0` | `0` | boot réseau test-mode — non signé **accepté** |

La sémantique de `mode` est confirmée indépendamment par le patcheur FDT
(`0x9fa0a174`) qui écrit la propriété `fbx,boot-mode` : `0` → `"test-mode"`,
`1` → `"bank0"` / `"bank0-forced"`.

### Le branchement, @ `0x9fa09c8c`

```
ldr  w0, [x29, #0x60]      ; flags de la partition kernel
and  w0, w0, #1            ; bit0 = "signée"
cbz  w22, #0x9fa09cb4      ; mode == 0 ?
cbz  w0,  #0x9fa09ca4      ; mode != 0 et non signée -> "bad kernel or DTB for current bootmode."
...
0x9fa09cb4: cbz w0, #0x9fa09cec   ; mode == 0 ET non signée -> SAUTE la vérif
0x9fa09cd0: bl  0x9fa0acdc        ; verify_signature()  <- jamais atteint
0x9fa09cdc: adr x0, "kernel signature check failed."
```

Même schéma pour le DTB en `0x9fa09d30` (`tbz w0, #0` → saute la vérif).

**Conséquence** : en mode test, une image dont la partition kernel a le bit 0 de
`flags` à zéro n'est **jamais vérifiée**. Le contrôle de signature est déclaratif.

### Sélection du mode test, @ `0x9fa00680`

```
ldr w0,[x19,#8] ; cmp w0,#0x1d      ; le contrôleur doit avoir > 29 pins
ops->set_direction(dev, 29, 0)       ; pin 29 en entrée
w20 = ops->get(dev, 29)              ; lecture du niveau
...
0x9fa007c0: cbz w20, normal_boot     ; BAS  -> boot flash normal
0x9fa007c4: bl  test_mode_boot       ; HAUT -> boot réseau
```

**GPIO 29 au niveau haut au reset ⇒ boot réseau.** À corréler avec `drivers/fbxgpio/`
des sources GPL et avec le GPIO `bank0-forced` déjà repéré — ce sont deux pins
distincts, celui-ci n'avait pas été identifié.

### ✅ GPIO 29 confirmé par les sources GPL

Le DTS du board (`arch/arm/boot/dts/qcom/apq8098-freebox-batfish.dts`, publié par Free
sur floss.freebox.fr) nomme le signal explicitement :

```dts
test-mode {
        name = "test-mode";
        gpio = <&tlmm 29 GPIO_ACTIVE_LOW>;
        input;
};

force_test_mode: force_test_mode {
        mux    { pins = "gpio29"; function = "gpio"; };
        config { pins = "gpio29"; drive-strength = <2>; bias-pull-down; };
};
```

Deux sources indépendantes concordent donc : **TLMM 29**, littéralement appelé
`test-mode` / `force_test_mode`.

**Polarité** : `bias-pull-down` → au repos la broche lit **0** = boot normal. Il faut
donc **tirer la broche au niveau HAUT** pour entrer en test mode, ce qui correspond
exactement au `cbz w20, normal_boot` de `snapl`. Le `GPIO_ACTIVE_LOW` du nœud
`fbxgpio` n'est que la convention du driver Linux **après** le boot, pas ce que lit
le bootloader.

> ⚠️ Les TLMM du MSM8998 sont en **1,8 V**. Un strap vers 3,3 V ou 5 V détruit la
> broche. Il faut une résistance (~1 kΩ) vers le rail 1,8 V de la carte, assez basse
> pour vaincre le pull-down interne.

Variantes de board présentes dans les DTS : `batfish`, `oarfish`, `proto` — ce sont
les mêmes noms que les modes de boot énumérés par `snapl`. Le Player Delta est
probablement un *batfish* (`unknown fish detected %02x, assume it's a bat`, lu sur
l'EEPROM i2c du carrier).

### ✅ Aucun garde-fou de production

Vérifié instruction par instruction : **aucune écriture de `w20`** entre la lecture
du GPIO (`0x9fa006c4`) et le branchement vers `test_mode_boot` (`0x9fa007c4`).
`w20` conserve la valeur brute de la broche. Aucun fuse, aucun flag `fbxserial`,
aucune condition de production ne désactive le mode test — c'est une porte d'usine
laissée active en série.

### Aucun anti-rollback

Toutes les occurrences de « version » dans `snapl` sont des contrôles de **format**
(`tag version == 2`, version GPT, version de protocole `fbxauthd`) — jamais une
comparaison monotone ni un index de rollback. `boot_from_tag` teste `version == 2`
et rien d'autre : **une image correctement signée est acceptée quel que soit son âge**.

### Layout mémoire de `snapl`

`heap_init()` @ `0x9fa115ac` :

```
base         = 0x9fa1e248 & ~0xFFF = 0x9fa1e000
[0x9fa1b428] = base                      ; heap_start
[0x9fa1b420] = base + (0x400 << 12)      ; heap_end = base + 4 MiB
[0x9fa1b418] = base                      ; brk courant
```

`0x9fa115d4` = `sbrk()` séquentiel (borne basse/haute, avance le brk, retourne
l'ancien). L'allocateur est **dlmalloc** (seuil `0xe8`, `MIN_CHUNK_SIZE` 32,
alignement 16, en-tête de 16 o, contrôle `unlink` avec panic `malloc abort`).

Pile : `0x9fa001c8` → `x1 = &image - 0x20` → **`SP_EL1 = 0x9f9fffe0`**,
`SP_EL0 = 0x9f9ffbe0`, croissance vers le bas.

```
0x9f9fffe0   pile (croît vers le BAS)
0x9fa00000   image snapl (.text)
0x9fa1a5d8   fin .text
0x9fa1b000   data/bss
0x9fa1d000   fin bss
0x9fa1e000   tas (4 MiB)
0x9fe1e000   fin tas
```

`snapl` tourne en **EL1** (seuls des registres `_EL1` sont écrits : `MAIR`, `TCR`,
`TTBR0`, `SCTLR`, `VBAR`). Base fixe, pas d'ASLR, allocateur séquentiel, monothread :
l'état mémoire est **entièrement déterministe et reproductible d'un boot à l'autre**.

### `test_mode_boot` @ `0x9fa0aab0`

```
"## Booting in test mode."
  -> VLAN 41 sur atl0  (atl0.41)   <-- même VLAN que la cmdline NFS des sources GPL
  -> DHCP
  -> paquet fbxdp
  -> fbxauth        (0x9fa0dcc4)   <-- LE verrou
  -> "Auth successfull, tftpboot ..."
  -> tftp_load(..., 0xa0000000, &size)
  -> boot_from_tag(0xa0000000, size, 0)
```

## Le verrou restant : `fbxauthd`

Protocole reversé (`0x9fa0dcc4`) :

| Élément | Valeur |
|-|-|
| Transport | UDP, port **25234** (`0x6292`) |
| Magic | `0x89892df8` |
| Requête | 42 octets — MAC à `+0x14`, **nonce aléatoire de 16 o** à `+0x1a` |
| Réponse | 36 octets exactement, mêmes magic/version/type |
| Réessais | 4, timeout `ETIMEDOUT` |

Vérification (`0x9fa0de8c`) :

```
digest = MD5( nonce[16] || K[16] )
memcmp(digest, response + 0x14, 16) == 0
```

Le nonce est **généré par le Player** et envoyé en clair — on le connaît. Tout tient
donc sur `K`, obtenue par `0x9fa0aa14(1, buf, 16)` → `0x9fa08e80`, qui construit
`{cmd = 2, key_id = 1, len = 16, out}` et l'envoie sur le **canal QSEE du trustlet
`fbxta`**. `K` est donc **scellée en TrustZone** : pas d'extraction offline, pas de
constante en dur dans `snapl`.

Le chemin d'échec est propre (retour `-1`, pas de confusion de signe exploitable).

## Où est la vraie ouverture maintenant

L'authentification arrive **après** que `snapl` ait déjà traité des paquets
entièrement contrôlés par l'attaquant. Ordre réel : DHCP → fbxdp → **auth**.
Tout ce qui est parsé dans cette fenêtre est de la surface d'attaque non
authentifiée, en EL1, sans ASLR.

🔒 **Un résultat existe sur cette surface. Il n'est pas publié.**

L'audit statique de cette fenêtre pré-auth a abouti. Les détails restent privés le
temps d'une **divulgation responsable auprès de Free** : il s'agit d'un produit
actuellement en service. Voir la section divulgation de [`FINDINGS.md`](./FINDINGS.md).

Vous possédez un Player Delta et vous voulez contribuer sur ce point ? Ouvrez une
issue ou écrivez-moi — l'analyse est partagée en privé avec les chercheurs qui ont
le matériel.

Note complémentaire, sans rapport avec ce qui précède : le parser d'imagetag
(`boot_from_tag`) traite lui aussi un blob 100 % contrôlé **avant** la vérification
de signature — mais il est situé **derrière** l'auth, donc moins intéressant.

## Chaîne visée

```
GPIO 29 haut au reset
   └─> snapl entre en test-mode (boot réseau)
        └─> on répond au DHCP (on est le serveur)
             └─> auth fbxauthd : MD5(nonce||K), K scellée en TrustZone
                  └─> tftpboot d'un imagetag dont la partition kernel
                      se déclare NON SIGNÉE
                       └─> boot_from_tag(mode=0) ne vérifie rien
                            └─> kernel arbitraire
```

Ce chemin ne demande **aucun bug** — il est supporté par le design de `snapl`.
Il ne demande que `K`. (Une seconde voie, non publiée, retire cette exigence.)

## Prochaines actions

- [x] ~~Identifier le GPIO~~ → **TLMM 29**, confirmé par `snapl` **et** par le DTS GPL.
- [ ] **Localiser le pad physique du TLMM 29** sur le PCB. C'est un strap à tirer au
      niveau **haut** (1,8 V, ~1 kΩ) au reset — non destructif et réversible.
      ⚠️ Faire l'UART **d'abord** : sans console série on ne peut pas savoir si le
      mode test a été atteint (`## Booting in test mode.`).
- [ ] Compiler un kernel + DTB et l'emballer avec `scripts/mkimagetag.py`.
      **Viser mainline** (MSM8998 supporté depuis 6.0, ports postmarketOS existants sur
      le même SoC) plutôt que le `linux-4.4.302-fbx` de Free, qui est EOL et dont on n'a
      que la 1.5.3. Porter `apq8098-freebox-batfish.dts` par-dessus.
      Le DTB doit porter le bon `compatible`, sinon `No DTB could boot kernel: tried:`.
      Premier objectif : **console UART + réseau**, rien d'autre.
- [ ] Surveiller la version du **bootchain** (42.20), pas celle du système : c'est elle
      qui porte `snapl`.
- [x] ~~Auditer statiquement la surface réseau pré-auth de `snapl`~~ → 🔒 fait,
      résultat **non publié** (divulgation en cours, cf. [`FINDINGS.md`](./FINDINGS.md)).
- [ ] Confirmer le layout exact des flags de partition (bit 0 = signé) en croisant
      avec l'imagetag réel du bank1.
- [ ] Vérifier si le trustlet `fbxta` (cmd 2 / key_id 1) est atteignable depuis
      Linux via `qseecom` — si oui, `K` devient extractable **une fois** qu'on a du
      code natif, ce qui referme la boucle pour les prochains boots.

## Outils

`scripts/xref-aarch64.py` — trouve les xrefs ADRP/ADD vers une chaîne dans un ELF
AArch64 strippé sans sections. Ghidra n'est pas requis pour ce travail.

```bash
python3 scripts/xref-aarch64.py firmware/bootchain/comp08_0x523000_64bit.elf "test-mode" "signature check"
```
