# Brief hardware — pour EricBlanquer/freebox-devialet-hack

> Synthèse destinée à un contributeur qui peut **ouvrir le boîtier**. Tout le software
> a été cartographié (cf. `FINDINGS.md`) ; le root passera par le hardware. Voici les
> infos concrètes pour démarrer efficacement.

## Ce que le software nous a appris (et qui aide le hardware)
- **SoC** Qualcomm APQ8098 (MSM8998), stockage **UFS**, kernel **Linux 4.4.302-fbx**, userland busybox/musl.
- **UART confirmé par le firmware** : `console=ttyMSM0,115200,n8`, `earlycon=msm_serial_dm,0xc1b0000`. → **115200 8N1**, niveau **1.8 V**. Test points candidats **TP5/TP6/TP7** (tes photos).
- **Chaîne de boot** (récupérée en clair via OTA) : XBL/SBL1 → ABL (UEFI) → HYP → kernel. **Sahara** présent (EDL). **AVB** actif.
- **Lock state = fuse QFPROM** (`qsee_is_sw_fuse_blown`), unlock = token signé OEM. Pas de soft-unlock.
- **Banking A/B** : `bank0` **forçable par GPIO** (`bank0 boot gpio active`) → mode recovery/factory à localiser. Driver `drivers/fbxgpio/`.
- **Boot dev = NFS** : le kernel a un cmdline d'usine `root=/dev/nfs ip=…eth0.41:dhcp dhcpclass=linux-fbx7hd` → Free flashe/boote ses unités de dev en NFS sur VLAN 41.

## Pistes hardware par ordre de rendement
### 1. UART (le plus rentable, le moins risqué)
- Pads **TP5/TP6/TP7**, **115200 8N1**, adaptateur 1.8 V (CP2102 + level shifter si besoin).
- Capturer le **log de boot** : versions XBL/ABL, et surtout chercher une **interruption bootloader** (touche), un **prompt shell**, ou des **commandes cachées**.
- Si shell : `dd` des partitions → on a alors le **rootfs déchiffré au runtime** (l'ICE déchiffre en lecture) = ce que l'OTA chiffré ne donne pas.

### 2. EDL (mode 9008) + Sahara
- Test points EDL (court-circuit au boot) → `Qualcomm HS-USB 9008`.
- `edl.py` (bkerler) : dump du **hello Sahara** (hardware-ID, état secure boot).
- ⚠️ Sur MSM8998, EDL exige un **firehose signé** (cf. `FINDINGS.md`). On a le XBL en clair (`firmware/bootchain/comp00`) → **analyse possible de l'implémentation Sahara** pour vérifier l'applicabilité du bug 0x13 (à faire en Ghidra).

### 3. GPIO bank0 (recovery)
- Localiser le **GPIO `bank0-forced`** → booter bank0 (mode dégradé, parfois plus permissif : vérifs relâchées, fastboot ?).

### 4. Fault injection (glitch) — expert
- Glitch (voltage/EM) sur le **check du fuse** (`qsee_is_sw_fuse_blown`) ou la **vérif RSA** → sauter la vérification. Nécessite équipement (ChipWhisperer-like).

## Objectif "rapide" non-Android (motivant)
Même sans Android : avec un **shell** (UART), on peut piloter **`fbxgpio`/le PSoC façade (`fbx7hd-top-psoc`)** pour **éteindre la LED** d'un Player orphelin (résilié) — vrai cas d'usage (conso + pollution lumineuse).

## Ce que je fournis côté software
- Outil **`fbx-deploy.py`** (code exec QML via mode dev) — utile pour automatiser des tests une fois un foothold obtenu.
- **Firmware + chaîne de boot extraite** (`firmware/bootchain/`, 14 ELF étiquetés) prête pour Ghidra.
- **Pipeline Ghidra** (`scripts/ghidra/`) pour décompiler à la demande.
