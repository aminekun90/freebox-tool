# Piste software : moteur WebKit du navigateur système

> Seule voie **software pure** restante pour évader le sandbox QML. Analyse de
> tangibilité (CVE connues + PoC publics). **Aucun exploit n'est écrit ici** — c'est
> une cartographie de surface d'attaque sur du matériel possédé, à but de documentation.

## Canal de livraison (acquis)
Depuis notre app QML (mode dev), `Qt.openUrlExternally(<http>)` ouvre un **chooser système**
→ choix **navigateur** → charge une **page qu'on sert** → exécute notre JS/HTML/WASM,
avec **retour réseau** vers notre serveur. Donc on peut faire tourner du code dans le
moteur web et observer le résultat. (Démontré : `app/browserprobe/`.)

## Moteur cible
- User-Agent : `Mozilla/5.0 (Freebox; fbx7hd-delta/1.5.24.2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15`
- → **Safari 16.0** (≈ septembre 2022). `605.1.15` = build string générique (peu discriminant).
- **Hypothèse clé** : le WebKit embarqué d'une appliance n'est **quasi jamais mis à jour** → probablement figé au niveau 16.0, donc vulnérable aux RCE corrigées **après** 16.0.
- Arch : **aarch64** (comme iOS/Apple Silicon) → la majorité des PoC publics ciblent arm64 = portage facilité.

## CVE candidates (RCE renderer, JavaScriptCore) — si moteur figé à 16.0
| CVE | Type | Corrigé dans | 16.0 vulnérable ? | PoC public |
|-|-|-|-|-|
| **CVE-2022-42856** | Type confusion FTL JIT, **exploité ITW** | Safari **16.2** | ✅ **oui** | writeups (Jamf, sploitem) |
| CVE-2023-23529 | Type confusion, zero-day | 16.3.1 | ✅ oui | analyses publiques |
| CVE-2023-37450 | Type confusion | RSR 16.5.1 | ✅ oui | PoC sur commit WebKit précis |
| CVE-2024-23222 | Type confusion JSC (addr/fakeobj) | iOS 17.3 | ✅ oui | tutoriel + PoC |
| Coruna « terrorbird » | Type confusion (chaîne) | 16.2–16.5.1 | ✅ oui | reconstruction publique |

→ **Meilleur candidat : CVE-2022-42856** (corrigé en 16.2, donc un moteur 16.0 est non patché ; weaponisé en conditions réelles, writeups dispos).

## Limites / réalité
- **Fingerprint à confirmer** : l'UA `16.0` peut être custom/spoofé. Il faut **détecter la vraie version du moteur JSC** par feature-detection (non destructif) avant de parier sur une CVE.
- **RCE renderer ≠ root** : un bug JSC donne du code natif dans le **process navigateur**, toujours soumis au **sandbox OS du navigateur** (SBX). Il faut ensuite une **évasion de sandbox** (souvent un 2e bug). Sur cette appliance, ce sandbox est peut-être plus faible que sur iOS — à évaluer.
- **Effort** : porter/écrire un exploit JSC = vrai exploit-dev (semaines), incertain.

## ✅ Fingerprint réalisé (mesuré sur le device)
Feature-detection depuis notre page chargée dans le navigateur du Player :
| Feature | Présent | Borne |
|-|-|-|
| `structuredClone`, `findLast`, `bigInt64Array` | ✅ | ≥ 15.4 |
| `toSorted`, `toSpliced`, `Array.prototype.with`, `reportError` | ✅ | **≥ 16.4** |
| `Array.fromAsync`, `OffscreenCanvas` | ❌ | build custom (features retirées) |
| `RegExp /v` (unicodeSets) | ❌ | **< 17.0** |
| **WebAssembly** | ❌ | **DÉSACTIVÉ** |
| `SharedArrayBuffer` | ❌ | pas de cross-origin isolation |

→ **Moteur réel ≈ Safari 16.4–16.6** (l'UA `16.0` est trompeur / figé), **build custom**, **WASM off**.

## Verdict révisé (honnête)
- Les CVE **faciles/anciennes ne s'appliquent pas** : CVE-2022-42856 (corrigé 16.2) ❌, CVE-2023-23529 (16.3.1) ❌.
- Candidats restants = bugs JSC **16.4–16.5.1** : ex. **CVE-2023-37450** (corrigé RSR post-16.5.1, PoC public sur commit précis), Coruna « terrorbird ». À confirmer si moteur ≤ 16.5.1.
- **WASM désactivé** = on perd les primitives d'exploit WASM-backed (fakeobj/RW via WASM memory) très utilisées dans les PoC modernes → exploitation **plus difficile** (il reste les primitives JIT/Array, plus délicates).
- **Toujours besoin d'un SBX** (évasion du sandbox du process navigateur) après une RCE renderer.

## Conclusion
La piste WebKit est **tangible mais nettement plus dure** qu'espéré : moteur récent (16.4+), WASM coupé, et il faut un PoC 16.4–16.5.1 sans WASM + une évasion de sandbox. **Probabilité faible** sans un travail d'exploit-dev conséquent. Documenté comme telle ; ce n'est pas un quick win.

## Étapes restantes (si on poursuit cette voie)
1. Resserrer la version (≤ 16.5.1 ?) via d'autres marqueurs → confirme l'applicabilité de CVE-2023-37450.
2. Évaluer la solidité du **sandbox du process navigateur** sur l'appliance (souvent plus faible que sur iOS).
3. Sinon : prioriser la voie **bootloader (ABL en clair) / hardware (UART, GPIO bank0)**.

## Sources
- CVE-2022-42856 : <https://nvd.nist.gov/vuln/detail/CVE-2022-42856> · <https://www.jamf.com/blog/webkit-vulnerability-cve-2022-42856-jamf-threat-labs-investigation/>
- CVE-2023-37450 (PoC sur commit) · CVE-2024-23222 (tutoriel JSC) · Coruna reconstruction (chaînes iOS 16/17).
