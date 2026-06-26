# Plan d'exécution — Code execution via mode développeur (SDK Player)

> Objectif global : obtenir de l'exécution de code sur le Freebox Delta Player via le
> **mode développeur officiel** (déjà activé), puis **sonder le sandbox** pour évaluer
> une **élévation de privilèges** vers un shell/root, étape vers Android.
>
> Périmètre : matériel possédé, SDK officiel Free, 100 % légal. Aucun flash, aucune
> opération destructive tant qu'on n'a pas dumpé/compris le système.

## État de départ (acquis)
- Mode dev **activé** sur le Player (`192.168.x` — identifier par MAC `34:27:92:8E:F3:38`).
- SoC APQ8098, Linux (`linux-fbx7hd`), stockage UFS.
- Service `_fbx-devel._tcp` "Remote debugger" (beacon, port 0). Canal piloté par QtCreator + plugin Freebox.
- Modèle de déploiement : **TAR uploadé → exécuté comme process → stdout/stderr streamés** (TCP maison, debug QML).

---

## Phase 0 — Préparer l'environnement (host Mac)
**But** : chaîne QtCreator + plugin Freebox + lib QML `fbx` fonctionnelle.

- [ ] Installer **Qt** (version ciblée par le SDK Player — probablement Qt 5.x) + **QtCreator**.
- [ ] Installer le **plugin Freebox pour QtCreator** ([fbx/freebox-qtcreator-plugin](https://github.com/fbx/freebox-qtcreator-plugin)).
- [ ] Installer la **lib QML `fbx`** (objets Freebox) depuis [dev.freebox.fr/sdk/player.html](https://dev.freebox.fr/sdk/player.html).
- [ ] Vérifier que QtCreator **découvre le Player** (mDNS `_fbx-devel._tcp`) en mode dev.

**Go/No-Go** : le Player apparaît comme device cible dans QtCreator → Phase 1.
Si KO : capturer les logs du plugin, vérifier mDNS (`dns-sd -B _fbx-devel._tcp`), même sous-réseau.

---

## Phase 1 — "Hello World" déployé et exécuté
**But** : valider la boucle deploy → run → sortie, et capturer le **contexte d'exécution**.

- [ ] Créer un projet **template Freebox** minimal (QML) avec `manifest.json`.
- [ ] Déployer + lancer sur le Player. Confirmer l'affichage à l'écran + retour stdout/stderr.
- [ ] **Première sonde de contexte** dès le hello world (via QML/JS ou un petit binaire) :
  - Quel **uid/gid** ? (`id`, ou lecture `/proc/self/status`)
  - **CWD** et chemin d'installation de l'app ? (`/proc/self/cwd`, `/proc/self/maps`)
  - Variables d'**environnement** ? (`/proc/self/environ`)

**Go/No-Go** : l'app tourne et on récupère sa sortie → Phase 2.

---

## Phase 2 — Sonder le sandbox (la phase clé)
**But** : cartographier ce que le contexte de l'app autorise. Déterminer s'il existe une
voie d'évasion vers le système. **Batterie de tests, du moins au plus intrusif.**

> Implémentation : si le package autorise du **C++ natif** (Qt = C++), on écrit une petite
> app qui exécute ces tests et logge le résultat sur stdout. Sinon, on voit jusqu'où va QML/JS.

### 2.1 Capacité d'exécution native
- [ ] Le package accepte-t-il du **code C++ compilé** (pas seulement QML) ? → si oui, exécution quasi-arbitraire dans le contexte app.
- [ ] Architecture/ABI du binaire attendu (aarch64 ? toolchain ?).

### 2.2 Système de fichiers (lecture)
- [ ] Lister `/`, `/etc`, `/proc`, `/sys`, `/data`, `/var`, le home de l'app.
- [ ] Lire des fichiers sensibles **en lecture seule** : `/etc/passwd`, `/proc/version`, `/proc/cpuinfo`, `/proc/mounts`, `/proc/cmdline` (→ bootargs, secure boot), `/proc/filesystems`.
- [ ] Repérer les **partitions** (`/proc/mounts`, `/dev/block/...`), le type de FS, ce qui est monté `ro`/`rw`.
- [ ] Chercher des **binaires utiles** : `busybox`, `sh`, `toybox`, `gdbserver`, `adbd`, `su`, `mount`.

### 2.3 Système de fichiers (écriture)
- [ ] Où peut-on **écrire** ? (home app, `/tmp`, `/data/...`).
- [ ] Peut-on écrire un binaire et le marquer **exécutable** (`chmod +x`) puis le lancer ?

### 2.4 Process & exec
- [ ] Peut-on **spawn un process** (`fork`/`exec`, `QProcess`) ? Lancer `sh`/`busybox` ?
- [ ] Lister les **process** du système (`/proc/*/cmdline`) → quels services tournent, sous quels uid.
- [ ] Voir les **capabilities** (`/proc/self/status` CapEff), SELinux/AppArmor (`/proc/self/attr/current`, `getenforce`).

### 2.5 Réseau & IPC
- [ ] Ouvrir des **sockets** (déjà partiellement : stdio TCP). Sockets UNIX locales ? Accès au bus IPC interne de Free ?
- [ ] Repérer des **sockets/services locaux** (`/proc/net/unix`, `netstat`) → surface d'attaque interne (le rtspd, l'API Free locale, etc.).

### 2.6 Surface noyau
- [ ] Version **kernel** exacte (`/proc/version`) → chercher CVE locales d'élévation (kernel 835-era).
- [ ] `/proc/kallsyms` lisible ? modules (`/proc/modules`) ? `/dev` accessibles ?

**Livrable Phase 2** : un tableau "capacité → autorisé/refusé → preuve", consigné dans `FINDINGS.md`.

---

## Phase 3 — Décider la voie d'escalade
**But** : à partir de la carte du sandbox, choisir l'angle.

Branches possibles (selon résultats Phase 2) :
- **A. Sandbox permissif** (exec + écriture + uid non trivial) → installer un busybox/dropbear, ouvrir un **shell**, explorer, viser root via service/IPC local mal protégé.
- **B. CVE kernel locale** (si kernel ancien + `/proc` lisible) → exploit d'élévation user→root depuis l'app.
- **C. Abus d'un service local** (rtspd, API Free, IPC) atteignable depuis l'app et tournant en root.
- **D. Sandbox hermétique** → repli sur la voie **hardware** (UART/EDL, cf. `ATTACK-ROADMAP.md`), en combinant avec Eric.

**Go/No-Go** : un shell ou une primitive root identifiée → Phase 4. Sinon → repli D.

---

## Phase 4 — Foothold → exploration système → Android (long terme)
- [ ] Avec un shell : **dump** des partitions lisibles (firmware, bootloader, clés) pour reverse hors-ligne.
- [ ] Comprendre la **chaîne de boot** et le **secure boot** depuis l'intérieur (bootargs, fuses lisibles ?).
- [ ] Évaluer la faisabilité réelle d'un **boot Android** (device tree, drivers) — cf. roadmap.

---

## Règles de sécurité (à chaque phase)
- Aucune écriture sur partitions système tant qu'on n'a pas un **dump de secours**.
- Pas de flash bootloader avant compréhension complète + plan de récupération (EDL).
- Documenter chaque test (commande → résultat) dans `FINDINGS.md`, commits atomiques.
- Si le Player se met en sécurité (bip) ou se dégrade : **arrêter**, documenter, restaurer.

## Partage communauté
- Mettre à jour l'**issue #1** chez Eric avec la voie mode-dev dès la Phase 1 validée.
- Publier les résultats Phase 2 (carte du sandbox) — c'est réutilisable par tout possesseur de Player.
