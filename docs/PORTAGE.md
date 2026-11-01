# Portage du trainer V165 vers le hde.exe d'origine

Copie séparée du trainer `HDFinalAdvancedV165_JOURNAL_RAPIDE` (projet
`HD_Radar_Project`, qui n'a pas été modifié). Cette copie vise **uniquement**
le `hde.exe` d'origine de H&D Deluxe 1.50 :

| | hde.exe moddé (Ultimate Mod 5.0.7) | hde.exe d'origine |
|---|---|---|
| Taille | 1 138 796 octets | 1 073 197 octets |
| Horodatage PE | `0x6A5958A8` (2026) | `0x3F7D64C4` (2003) |
| SizeOfImage | `0x11B000` | `0x10A000` |

Exécutable produit : `build\vs2026-x86\Release\HDFinalAdvancedV165_ORIGINAL.exe`.

## Pourquoi le trainer moddé ne marche pas sur l'original

Le trainer écrit dans la mémoire de `hde.exe` à des **adresses fixes** et lit
les objets du jeu à des **offsets fixes**. Le `hde.exe` du mod est une
recompilation des sources de 2002 avec des ajouts de NilsZ ; l'original est la
build officielle de 2003. Conséquences mesurées :

- 35 adresses de code ou de données sur 36 sont différentes.
- Les variables globales sont toutes déplacées (`0x10Axxx` → `0x0FAxxx`).
- `C_human` / `C_player` : NilsZ a inséré 0x14 octets avant `0x178`, donc
  tous les champs de `0x178` à `0x2E4` sont 0x14 plus bas dans l'original.
- `C_automobile` : identique jusqu'à `0x25C`, puis −8.
- Les vtables des soldats ont 8 méthodes virtuelles de plus dans le mod
  (76 entrées contre 68), insérées à partir du rang `0x80`.
- `i3d2.dll` (frames, scènes, visuels) : offsets identiques.

## Sécurité ajoutée

`TrainerProcess::RefreshConnection` lit l'en-tête PE du processus et refuse
tout `hde.exe` dont l'horodatage ou la taille ne sont pas ceux de l'original
(erreur `ERROR_REVISION_MISMATCH`, message affiché dans la barre d'état).
Vérifié : le trainer porté refuse le `hde.exe` moddé en cours d'exécution.

Les réglages sont rangés sous `HKCU\Software\HDPhase1_Original` pour ne jamais
toucher ceux du trainer du mod (`HKCU\Software\HDPhase1`).

## Correspondances appliquées

Toutes sont dans `tools/apply_port.py` (rejouable sur la copie de base).

### Données globales

| Constante | Mod | Original |
|---|---|---|
| Mission / HDTickClass | `0x10AD4C` | `0x0FA7E4` |
| GameConfiguration / GameMode | `0x1086E0` | `0x0F8A68` |
| Tables d'inventaire / armes | `0x10AAD0` | `0x0FA570` |
| NetHost / NetJoin | `0x10ABE4/5` | `0x0FA69C/D` |
| Table de collision | `0x10AC04` | `0x0FA6BC` |
| Scène d'inventaire | `0x10AC08` | `0x0FA6C0` |
| Taux de braquage d'origine | `0x4F66C0` | `0x4E77A4` |

### Code

| Point | Mod | Original | Remarque |
|---|---|---|---|
| ProcessCheat (déclencheur sur le thread du jeu) | `0x9FC10` | `0x96360` | prologue `83 EC 38 53 55`, rejoué tel quel |
| SetSelectedItem | `0x76E0` | `0x6F40` | prologue avec `+0x244` |
| DeleteAllItems | `0x62E80` | `0x58EB0` | identique |
| WatchVectorErase | `0x39CB0` | `0x32FB0` | identique |
| C_human::Die | `0x208B0` | `0x1C520` | identique |
| C_map_manager::Tick (radar, carte) | `0xB1AD0` | `0xA5320` | `mov eax,[004FA580]` |
| C_inventory::AddItem | motif | `0x59E10` | déjà trouvé par motif |

### Rangs de vtable

| Méthode | Mod | Original |
|---|---|---|
| SetActive, CbProc, Add/DelProgram | inchangés | inchangés |
| IsEnemy (C_player, C_enemy) | `0xA4` | `0x9C` |
| Hit | `0x104` | `0xEC` |
| Explode | `0xDC` | `0xD0` (prologue différent, 10 octets mis à jour) |
| C_player::Die | `0x100` (méthode ajoutée par le mod) | `0xE8` |

### Champs des soldats (−0x14)

`MoveDirection 0x198`, `FallSpeed 0x1A4`, `CurrentPose 0x1A8`,
`BrestFrame 0x1B0`, `HeadFrame 0x1B4`, `AimDirection 0x1BC`, `AimCount 0x1D4`,
`NetworkSyncPosition 0x1F0`, `EquippedWeapon 0x230`, `UsingItem 0x23C`,
`StayMode 0x240`, `SelectedItem 0x244`, `ShootCountdown 0x24C`,
`Falling 0x250`, `CollisionTestCountdown 0x260`, `Voice 0x26C`,
`Program 0x270`, `ProgramBegin/End 0x274/0x278`, `ProgramDirty 0x27C`,
`CommandNew 0x27D`, `HoldingFire 0x27E`, `ActorEnumCount 0x280`,
`HoldingFire (installé) 0x282`, `WatchActors 0x284`, `WatchVector 0x288`,
`PlayerMode 0x2A0`, `ActivePlayer 0x2A4`, `NoHitCheat 0x2C0`,
`InitResistance 0x2C4`.

## Pas encore porté (refusera de s'activer, sans rien écrire)

Ces fonctions vérifient les octets du jeu avant d'écrire ; avec les valeurs du
mod, la vérification échoue sur l'original et la fonction reste inactive.

| Point | Fonctions concernées | Pourquoi |
|---|---|---|
| CreateActor (hook), ResolvedCollision, FinishCallbackFrame | suivi des balles | le code posé dépend de la disposition propre au mod de `S_gun_shoot_init` (power à +0x3C) et de l'intérieur d'`Evaluate` ; dans l'original, `Finish` est intégré à `C_gun_shoot::Tick` (`0x43E0F0`) et ses champs sont à −4 |
| `HD_AI_AUTHORITY_*` | coop LAN | non traité |

## Deuxième et troisième étapes (`apply_port_etape2.py`, `apply_port_etape3.py`)

| Point | Mod | Original | Remarque |
|---|---|---|---|
| C_human::Tick (noclip, ranimer) | `0x1A560` | `0x16FD0` | rang +0x14 des deux vtables ; cadre `348h` au lieu de `36Ch` |
| Après `model == nullptr` (vie illimitée, chute) | `0x1A583` | `0x16FF3` | cible du même saut, `mov ecx,[ebx+1A8h]` |
| Noclip : publication réseau | `0x1BC4E` | `0x18087` | adresses internes `0x18092` / `0x1822B` |
| NM_HUMAN_POS (masque de position) | `0x1BD97` | `0x181CE` | `lea eax,[ebx+1FCh]` |
| C_camera::Tick (aimbot) | `0x5E510` | `0x54600` | champs +14h..+1Ch identiques, cadre `24Ch` |
| LoadModels (cache inventaire) | `0x62F75` | `0x58FA5` | + `0x592B1`, `0x593E5` |
| C_automobile::Tick (noclip véhicule) | `0x4E540` | `0x464E0` | cadre `98h` |
| Vitesse véhicule | `0x4F1F3` / `0x4F22C` | `0x47125` / `0x4715E` | `fmul [ecx*4+...]` rejoué tel quel |
| Braquage | `0x552E9` | `0x4C276` | `ESI` reste le véhicule (`mov ecx,esi` juste après) |
| Véhicule invulnérable | `0x4FC80` | `0x47AE0` | octets et `ret 10h` identiques |
| Vitesse du jeu | `0xCD787` | `0xBE481` | octets identiques, `tc` en `[esp+14h]` |
| Tir rapide (UseItem) | `0xA02E` | `0x986E` | instruction rejouée `mov eax,[ebx+1A8h]` |
| C_player::Die (protection) | rang `0x100` (ajout du mod) | rang `0xE8` | patch de 11 octets (`kPlayerDieHookPatchSize`) |
| Offsets en dur du noclip / suivi des balles | `0x1AC..0x274` | −0x14 | `move_dir`, `fall_speed`, `falling`, collision, `stay_mode`, `frm_head`, `shoot_countdown` |

### Signature de `cbProc` et numéros de messages

- Dans l'original, **tous** les `cbProc` des acteurs prennent **trois**
  arguments (`ret 0Ch`, vérifié sur 24 vtables) au lieu de quatre (`ret 10h`).
  Le mot `reserved` n'est plus empilé (6 appels).
- Messages : identiques jusqu'à 27 (`CB_CHEAT 14`, `CB_SETINVENTORY 17`,
  `CB_SETFOCUS 21`, `CB_SET_RESISTANCE 26`) ; décalés de −1 au-delà de 33.
  `CB_USE_AUTO` : 43 → 42.
- Triches de `CB_CHEAT` : `14` (immortalité) identique. `9` (fullhands) est
  traitée par `C_human` et, dans l'original, ignore le paramètre « ligne de
  catalogue » : elle donne toujours le kit standard (sans doublon).

### Contrôle hors jeu

`tools/verify_hooks.py` relit les 28 points de hook dans le `hde.exe` d'origine
et compare avec les octets attendus par le trainer porté : 28/28 conformes.
`CreateActor` (apparition de soldats) et `SetFrame` sont trouvés à l'exécution
par motif ; chacun a un seul candidat valide dans l'original.

## Audit complet (1er novembre)

Chaque fonction du trainer a été reprise, avec ce qu'elle lit ou écrit dans
le jeu, et contrôlée sur le `hde.exe` et l'`i3d2.dll` d'origine.

| Contrôle | Résultat |
|---|---|
| Points de hook (`verify_hooks.py`) | 28/28 conformes |
| Tous les motifs d'octets du code source (48) | tous présents dans l'original |
| Adresses absolues du mod restantes dans le code | aucune |
| Offsets de soldat écrits en dur (0x178..0x2E8) | tous portés (−0x14) |
| Appels à `cbProc` (6) | tous à 3 arguments ; messages 14, 17, 21, 42 |
| Sous-code 13 de `CB_USE_AUTO` (arrêt du véhicule) | même traitement |
| `AddProgram` / `DelProgram` (+0x24 / +0x28) | même code, `ret 10h` / `ret 8`, programme à +0x2C |
| Fonctions gardées du bandeau (SetHealth…) | uniques, mêmes conventions de retour |
| Driver i3d (création de modèles) | global `0x4FA6C0` unique (14 sites) |
| Numéros de propriétés des tables (8, 9, 65, 74, 96 ; arme 12) | identiques |
| Mission : scène +0x10, acteurs +0x68, carte +0xA0/+0xA4 | identiques |
| `i3d2.dll` : build différent (2003 contre 2024) | mêmes vtables, mêmes champs (99,3 % des accès), `I3D_frame::Update` au même endroit |

**Corrigé** : `GetTable` (lecture de la fiche d'un soldat, utilisée par la
création de soldats et les menus) est au rang `0xAC` de la vtable dans
l'original, hors de la plage `0xB0..0xC0` balayée. La plage commence
maintenant à `0xA8` ; la fiche est à `+0x190`.

**Corrigé** : un échec du suivi des balles coupait aussi l'aimbot.

Vérifié en jeu (journal du 1er novembre) : vitesse du jeu, les quatre gardes
de la protection absolue, filtre de dégâts, `CreateActor`, `menu_id`, radar,
ESP.

## Tester

Le jeu d'origine est lancé en administrateur (`RUNASADMIN`), donc le trainer
doit l'être aussi pour pouvoir ouvrir le processus. Le journal
`hdradar_diag.log` s'écrit à côté de l'exe du trainer.

## Outils (dossier `tools/`, Python + capstone + pefile)

- `bindiff_lite.py` : associe les fonctions des deux exe (code normalisé,
  graphe d'appels, vtables).
- `resolve_targets.py` : traduit chaque adresse de code du trainer.
- `map_operands.py`, `actor_fields.py` : votes des adresses globales et des
  offsets de champs, par classe.
- `vtable_pairs.py`, `vtable_slots.py`, `vtable_prologues.py` : vtables.
- `hook_sites.py` : octets aux points de hook, côte à côte.
- `apply_port.py`, `apply_port_etape2.py`, `apply_port_etape3.py` :
  appliquent les correspondances vérifiées, dans cet ordre.
- `cb_messages.py` : associe les numéros de messages `cbProc`.
- `verify_hooks.py` : contrôle les points de hook dans l'original.
