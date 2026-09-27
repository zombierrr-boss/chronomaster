# Skills — Arbeitsliste (Phase 2)

> Stand 2026-09-19. Entstanden aus den Konzepttabellen in `plan.md`, Abschnitt 2.4.
> **Alle `D_Attributes.*`-Pfade in diesem Dokument sind aus dem OpenBLCMM-Datenpaket verifiziert**
> (`blcmm_data_BL2-2023-04-20-01.jar`, `data/BL2/dumps/`), jeweils belegt durch den Zer0-Skill in der
> Spalte *Vorlage*. Was nicht belegt ist, steht unter „Offene Fragen" — nicht in den Tabellen.
> Zahlen sind Startwerte, keine Balance (Balance ist Phase 7).

---

## 1. Wie die Zahlen zu lesen sind

Ein `SkillEffectDefinitions`-Eintrag hat drei Zahlen, die zusammengehören (Anatomie: `../borderlands 2 mod/docs/datenmodell.md`, 2.4):

| Feld | Bedeutung | Beispiel Headsh0t |
|---|---|---|
| `BaseModifierValue.BaseValueConstant` | Wert bei Rang 1 | `0.04` |
| `PerGradeUpgrade.BaseValueConstant` | Zuwachs je weiterem Rang | `0.04` |
| `ModifierType` | `MT_Scale` = prozentual, `MT_PostAdd`/`MT_PreAdd` = absolut | `MT_Scale` |

In den Tabellen steht deshalb nur **eine** Zahl je Skill („je Rang") — Rang 1 und Zuwachs sind bei linearen Skills identisch, so wie bei Zer0. Die Spalte *Rang 5* ist die Summe, also nur zur Kontrolle.

**Vorzeichenfallen** (aus den Dumps, häufigste Fehlerquelle):

| Wirkung | Attribut | Vorzeichen |
|---|---|---|
| schneller schießen | `D_Attributes.Weapon.WeaponFireInterval` | **negativ** (Intervall wird kleiner) |
| schneller nachladen | `D_Attributes.Weapon.WeaponReloadSpeed` | **negativ** |
| genauer zielen | `D_Attributes.AccuracyResourcePool.AccuracyMinValue`, `…MaxValue`, `D_Attributes.Weapon.WeaponSpread` | **negativ** |
| weniger Schaden nehmen | `D_Attributes.DamageSourceModifiers.Received*DamageModifier` | **negativ** |
| Cooldown schneller | `D_Attributes.ActiveSkillCooldownResource.ActiveSkillCooldownConsumptionRate` | **positiv** (Verbrauchsrate steigt) |

**`DurationType` entscheidet, wer den Skill wieder ausmacht** (gelernt 2026-09-19, siehe unten):

| `DurationType` | Verhalten | Wofür bei uns |
|---|---|---|
| `DURATION_Timed` + `InitialDuration` | läuft nach N Sekunden **von selbst** ab | *Nachwirkung* (8 s), *Ausbruch* (3 s), *Kein Zurück* (10 s) — das Modul aktiviert nur, die Engine räumt auf |
| `DURATION_Infinite` | läuft, bis jemand ihn deaktiviert | *Stabilisator*, *Gespannte Zeit*, *Abstand* — alles, was an einen Zustand gekoppelt ist. **Das Modul muss selbst abschalten** |

Belegt an Zer0: `Skill_Speed` ist `DURATION_Timed 0.75` (deshalb war er im Test nach einem Befehl schon wieder aus), `Innervate` und `Headsh0t` sind `DURATION_Infinite`.

**Die Zahl und der Text auf der Skillkarte sind getrennt.** `SkillEffectDefinitions` wirkt, `SkillEffectPresentations` → `AttributePresentationDefinition` zeigt an. Wer nur eins ändert, hat eine lügende Skillkarte. Das gilt für jeden Eintrag unten.

**In-Game-Texte ohne Umlaute** (`CLAUDE.md`): Die Spalte *Name (Karte)* ist der Text, der ins Spiel geht.

## 2. Attribut-Baukasten

Alles, was die 36 Skills brauchen, mit dem Zer0-Skill, aus dem es abgeschrieben ist:

| Wirkung | Attribut | Typ | Beleg (Zer0-Skill, Wert) |
|---|---|---|---|
| Waffenschaden | `D_Attributes.Weapon.WeaponDamage` | `MT_Scale` | Vel0city 0.02, Fearless 0.03, Innervate 0.02 |
| Kritschaden | `D_Attributes.GameplayAttributes.PlayerCriticalHitBonus` | `MT_Scale` | Headsh0t 0.04, Killer 0.10, Vel0city 0.03 |
| Feuerrate | `D_Attributes.Weapon.WeaponFireInterval` | `MT_Scale` | Fearless −0.05 |
| Nachladetempo | `D_Attributes.Weapon.WeaponReloadSpeed` | `MT_Scale` | Fast Hands −0.05, Killer −0.15 |
| Waffenwechsel | `D_Attributes.Weapon.WeaponSwapTimeMultiplier` | `MT_Scale` | Fast Hands −0.10 |
| Magazingröße | `D_Attributes.Weapon.WeaponClipSize` | `MT_Scale` | — *(Attribut verifiziert, Zer0 nutzt es nicht)* |
| Genauigkeit | `D_Attributes.AccuracyResourcePool.AccuracyMinValue` / `AccuracyMaxValue`, `D_Attributes.Weapon.WeaponSpread` | `MT_Scale` | Precisi0n −0.05 / −0.05 / −0.04 |
| Zielgeschwindigkeit / Ruhe | `D_Attributes.Weapon.WeaponZoomEndFOV`, `D_Attributes.Weapon.WeaponPerShotAccuracyImpulse` | `MT_Scale` | 0ptics −0.03, −0.12 |
| Projektiltempo | `D_Attributes.Weapon.WeaponProjectileSpeedMultiplier` | `MT_Scale` | Vel0city 0.20 |
| Bewegungstempo | `D_Attributes.GameplayAttributes.FootSpeed` | `MT_Scale` | Innervate 0.07, Skill_Speed 0.25 |
| Hinterhalt-Bonus | `D_Attributes.DamageEnhancementModifiers.PlayerAttackUnsuspectingTargetModifier` | `MT_Scale` | Ambush 0.04 |
| Nahkampfschaden | `D_Attributes.DamageSourceModifiers.InstigatedMeleeDamageModifier` | `MT_Scale` | Ir0n Hand 0.03 |
| Maximalleben | `D_Attributes.HealthResourcePool.HealthMaxValue_Player` | `MT_Scale` | Ir0n Hand 0.03 |
| Lebensregeneration | `D_Attributes.HealthResourcePool.HealthActiveRegenerationRate` | `MT_Scale` | Innervate 0.008 |
| Schildregeneration | `D_Attributes.ShieldResourcePool.ShieldPassiveRegenerationRate` | `MT_Scale` | Grim 0.007 |
| Cooldown-Rate | `D_Attributes.ActiveSkillCooldownResource.ActiveSkillCooldownConsumptionRate` | `MT_Scale` | Grim 0.015 |
| Schadensresistenz | `D_Attributes.DamageSourceModifiers.ReceivedBulletDamageModifier` | `MT_Scale` | — *(verifiziert; „alle Quellen" braucht je einen Eintrag für Bullet, Melee, Grenade, Rocket, StatusEffect)* |
| Granatenschaden | `D_Attributes.DamageSourceModifiers.InstigatedGrenadeDamageModifier` | `MT_Scale` | — *(verifiziert)* |

**Muster für Stack-Skills:** `CriticalAscention` + `CriticalAscention_Stack` — der sichtbare Skill trägt Name und Text, ein zweiter, unsichtbarer Skill trägt den Effekt pro Stack (dort `BaseValueConstant=0.0`, `PerGradeUpgrade=0.5`). Jeder Stack aktiviert den Stack-Skill einmal. Das ist die Vorlage für *Gespannte Zeit*, *Abstand*, *Wiederkehr*.

## 3. Umsetzungsklassen — wer macht die Arbeit

Die Mod hat zwei Hälften (`CLAUDE.md`, Arbeitsteilung): **Hotfixes tragen Daten**, das **SDK-Modul trägt Logik**. Jeder Skill gehört in eine der beiden — oder in beide. Das ist die Spalte *Kl.* in den Tabellen.

| Klasse | Wer macht's | Was das heißt | Beispiel | Anzahl |
|---|---|---|---|---|
| **H** | nur Daten | Ein Wert in `SkillEffectDefinitions`, sonst nichts. Das Spiel wertet ihn selbst aus. Billig und sicher. | *Hinterhalt* — das Attribut `PlayerAttackUnsuspectingTargetModifier` existiert und tut genau das; Zer0s *Ambush* ist derselbe Skill. | 13 |
| **H+S** | Daten + Code | Der Wert existiert, aber jemand muss ihn ein- und ausschalten oder Stacks setzen. Das Spiel kennt unseren Zustand „Bombe liegt" nicht — das weiß nur das Modul. | *Stabilisator* — Resistenz als Attribut, aber nur solange die Bombe liegt. | 12 |
| **S** | nur Code | Es gibt kein Attribut dafür; die Wirkung entsteht im Modul (Zustand, Zeit, Entfernung, Schadensbuchhaltung). Teuer und fehleranfällig. | *Paradoxon* — verlangt ein Schadensbuch pro Ziel über das ganze Fenster. | 11 |

**Warum das zählt:** H ist fast geschenkt, S kostet echte Arbeit und echtes Absturzrisiko. Deshalb die Obergrenze von ~12 S-Skills aus dem Plan.

**S-Bilanz:** Der Plan nennt ~12 als Obergrenze; wir liegen bei 11. Erreicht durch die Kürzungen in Abschnitt 7.

---

## 4. Action Skill: Zeitbombe

> **Stand 2026-09-20: Schritte 1–4 sind im Spiel bestätigt, der Skill ist spielbar.** Legen/Zünden/Verpuffen, 20-s-Fenster (gemessen 19,99 / 20,00 s), Cooldown 35 s bzw. 17,5 s beim Verpuffen, ohne Unsichtbarkeit und ohne blaue Gegner-Markierung — Zer0 durchgehend unverändert. **Offen ist Schritt 5:** das Aussehen der Bombe (4.1) samt dem Skilltext, der noch vom Hologramm spricht.

`MaxGrade=1`, `SkillType=SKILL_TYPE_Action`, `DurationType=DURATION_Timed`, **`InitialDuration=20.0`** (Fenster; Zer0 hat 6.5). Vorlage: `GD_Assassin_Skills.ActionSkill.Skill_Deception`, als Laufzeit-Kopie `Skill_Zeitbombe` / `ActionSkill_Zeitbombe`.

**Name (Karte):** `Zeitbombe` · **Text (so im Spiel, `SKILL_TEXT` im Modul, Stand v1.33):** `[skill]Action Skill.[-skill] Druecke <StringAliasMap:Action.ActionSkill>, um eine [skill]Zeitbombe[-skill] zu legen: sie speichert diesen Moment - Ort, Leben, Schild, Magazin. Druecke erneut, um zu ihr zurueckzukehren, mit allem, was du hattest. Wartest du zu lange, verpufft sie - dann nur der halbe Cooldown.` (dazu Fenster und Cooldown als Zahlen).

> **Seit dem Wurf (v1.19–v1.33, D10) wieder leicht überholt:** Die Bombe wird *geworfen*, und der Ort ist der **Landepunkt**, nicht der Moment des Drückens. Leben, Schild und Magazin stimmen. Vorschlag für die nächste Textrunde (Kartentext → Spielneustart): „… um eine Zeitbombe zu werfen: wo sie liegen bleibt, ist dein Rueckkehrpunkt. Sie speichert Leben, Schild und Magazin dieses Moments. …“ — offen, nicht gebaut.

### Zustandsautomat

| Zustand | Eintritt durch | Was gilt | Austritt |
|---|---|---|---|
| **bereit** | Start, Cooldown abgelaufen | nichts | Skilltaste → *gelegt* |
| **gelegt** | `ActionSkill:OnActionSkillStarted` (POST) | Anker gespeichert (Karte, Blick, Leben, Schild, Magazin, Granaten); **seit v1.19 wird die Bombe geworfen, ihr Landepunkt ersetzt den Ort** (bis zur Landung gilt der Wurfpunkt, D10); die Bombe liegt sichtbar da (4.1); Fenster läuft 20 s | Skilltaste → *gezündet* · Ablauf → *verpufft* · Tod/Kartenwechsel → *verworfen* |
| **gezündet** | `WillowPlayerController:StartActionSkill` (PRE, blockiert) bei Zustand *gelegt* | Teleport + Werte zurück; Bombe weg; `pc.ResetActionSkill()`; **Cooldown selbst setzen** (ResetActionSkill löscht ihn) | sofort → *Cooldown* |
| **verpufft** | `ActionSkill:OnActionSkillEnded` (POST) bei Zustand *gelegt* | Anker und Bombe weg, keine Rückkehr | → *Cooldown*, aber **nur halber** (35 s → 17,5 s) |
| **Cooldown** | nach Zünden (35 s) oder Verpuffen (17,5 s) | Skilltaste tut nichts | Ablauf → *bereit* |
| **blockiert** | Fahrzeug (`in_vehicle()`), FFYL, Menü | Legen und Zünden abgelehnt, Log-Hinweis | Bedingung entfällt |
| **verworfen** | Kartenwechsel, Tod, Modul-Deaktivierung | Anker gelöscht, Bombe weg, kein Cooldown-Bonus | → *bereit* |

Alle vier Hooks sind in Spike B belegt (`docs/spikes.md`). Der Anker-Inhalt steht in `plan.md`, Anhang A, Frage 4: **Munitionsreserve gehört nicht dazu** — nur das Magazin (sonst wäre Zünden eine Gratis-Munitionskiste; *Volle Rückerstattung* lockert es gegen Skillpunkte).

### Was am Wirtsskill entkernt wird

| Was | Wo | Wert |
|---|---|---|
| Nahkampf-Dash aus | `GD_Assassin_Skills.ActionSkill.ActionSkill_Deception.bDisableExecuteAbility` | `True` |
| Fenster | `Skill_Deception.InitialDuration` | `20.0` |
| Unsichtbarkeit ab | `Skill_Stealth` per PRE-Hook auf `Behavior_ActivateSkill:ApplyBehaviorToContext` **blockieren** (v0.35). Er wird aus drei BPD-Knoten gestartet (`ActionSkill_Deception:…_12`/`_14`, `Skill_Deception:…_207`) — und die BPDs gehören Zer0, unsere Kopien verweisen nur darauf | Block statt Feld |
| ~~„endet beim ersten Schuss" ab~~ | Steht an **zwei** Stellen: `Skill_Deception.SkillEffectDefinitions(9)` *und* `Skill_Stealth.SkillEffectDefinitions(1)`. Der Stealth-Block nimmt die zweite mit. **Im Test 2026-09-20 beendete ein Schuss das Fenster ohnehin nicht** (Zünden nach 14,73 s belegt) — kein Handlungsbedarf | erledigt |
| Name/Text | `SkillName`, `SkillDescription` | siehe oben |

**Der Decoy-Spawn geht weg** (D9, 2026-09-20): Er war ein Erbstück aus Decepti0n, kein Entwurf. An den Anker gehört ein Gerät, kein Doppelgänger — siehe 4.1. Das Hologramm kehrt als *Zeitkapsel* (Baum 2, Tier 3) zurück, für Skillpunkte.

### 4.1 Wie die Bombe aussieht — entschieden (2026-09-20, v0.44–v0.50)

**Gewählt: `Prop_CesiumCharge.Meshes.CesiumCharge`** — ein flacher, kantiger Kasten mit leuchtendem Auge, liegt sauber auf dem Boden, Größe 1,0. Wahl des Nutzers aus fünf im Spiel gespawnten Kandidaten (Screenshots im Changelog v0.45/v0.46).

> **Offen (Nutzer, 2026-09-20 abends):** Die Bombe **hat Kollision, und die bleibt nach dem Verschwinden** — `SetCollision(False, False, False)` reicht nicht, und `Destroy()` greift vermutlich nicht (`bDeleteMe=False`). Erster Handgriff der nächsten Sitzung, `plan.md` 0b.

**So wird sie gespawnt (im Spiel bestätigt):** `pc.Spawn(DynamicSMActor_Spawnable, SpawnLocation, SpawnRotation, bNoCollisionFail=True)` → `actor.StaticMeshComponent.SetStaticMesh(mesh, True)` → `SetCollision(False, False, False)`. Position: `pawn.Location.Z − CylinderComponent.CollisionHeight` (Bodenhöhe). Entfernen: `SetHidden(True)` + `Destroy()`. Der Actor wird per `WeakPointer` gehalten (Kartenwechsel entsorgt ihn). `Actor.Spawn` ist `native noexport` und trotzdem per SDK erreichbar. Code: `bombe_setzen()` / `bombe_weg()` im Modul.

**Gelernt dabei:**
- `FX_CharacterAbilities.Smesh.DigistructCube_Group_Smesh` und `…DeathCube_Digistruct` sind **Wolken aus dutzenden Würfeln** (Zer0s Auflöseeffekt), kein Gerät. Die ursprüngliche Empfehlung war falsch.
- `StaticMesh.Bounds` reicht das SDK nicht durch — Größe ist Augenmaß, ggf. `SetDrawScale`.
- `Prop_*`/`FX_*`-Pakete gibt es **nicht als `.upk`**; `load_package` täte nichts. Was da ist, zeigt `zb meshes FILTER` (738 Meshes in Sanctuary). Die Caesium-Ladung war in Sanctuary und Three Horns geladen; zur Sicherheit wird das Mesh beim ersten Fund gerootet (`RF_RootSet`).
- Taschenuhr und Uhr (`Prop_PocketWatch`, `FX_InteractiveObjects.ClockMesh`) sind kartengebunden und nirgends geladen — für Phase 8 nur mit anderem Weg erreichbar.

**Zer0s Reste, alle abgehängt:** das Hologramm (hing an `Skill_Stealth`, seit v0.35 geblockt), der Ton-Dämpfer (Wwise-State `Ake_FX_Player_Assassin.Ak_Set_State_FX_Assassin_ActionSkill_On`) und das Ambiente (`…ActionSkill_Start`, 40× im 100-ms-Takt, plus `…ActionSkill_Loop`) — per `Block` auf `GearboxFramework.Behavior_PostAkEvent:ApplyBehaviorToContext`, nur beim Chronomant. Ein eigener Klang für die Zeitbombe ist Phase 8.

---

## 5. Die drei Bäume

Layout je Baum `2-2-3-2-2-1` = 12 Skills, 6 Tiers, `PointsToUnlockNextTier=5` (Tier 6: 1). Struktur: `SkillTreeBranchDefinition.Tiers(n)`, siehe Datenmodell 2.3.

> **Gebaut 2026-09-20 (v0.52–v0.55), alle 36 auf einmal** — Bauplan im Modul, Abschnitt „Phase 4-6" (Tabellen `BAUM_*`, Bauarten H / KILL / HS / S). **Zwei Funde dabei:** (1) Zer0s Äste sind **2-2-3-1-1-1 = 10 Skills**; welche Zelle des 3×6-Rasters ein Kästchen bekommt, sagt ein eigenes `SkillTreeBranchLayoutDefinition` (`Tiers(n).bCellIsOccupied`, 3 Bools). Unser 12er-Layout ist eine eigene Kopie `Layout_Chronomaster` — die Oberfläche zeichnet die 12 Zellen anstandslos (Screenshot v0.53). (2) Der Rang eines Baum-Skills kommt von **`WillowPlayerController.GetSkillGrade(Definition)`**, nicht vom `PlayerSkillTree` (der hat nur `GetSkillState`). Die H+S-Kette (Baum-Skill → Rang → `<Name>_Wirkung` per `ActivateSkill(grade)`) ist im Spiel bestätigt (Ausbruch, Stabilisator).

### Baum 1 — Vergangenheit (`BranchName=VERGANGENHEIT`)

| T | Name (Karte) | Rang | Wirkung | je Rang | Rang 5 | Kl. | Attribut / Mechanik | Vorlage |
|---|---|---|---|---|---|---|---|---|
| 1 | `Gedaechtnis` | 5 | Kritschaden und Magazin | +4 % Krit, +5 % Magazin | +20 / +25 % | H | `PlayerCriticalHitBonus`, `WeaponClipSize` | Headsh0t |
| 1 | `Nachwirkung` | 5 | 8 s nach dem Zünden mehr Waffenschaden | +4 % | +20 % | H+S | `WeaponDamage`, eigener Skill `DURATION_Timed 8.0`, vom SDK beim Zünden aktiviert | Killer |
| 2 | `Gespannte Zeit` | 5 | Je Sekunde mit liegender Bombe 1 Stack (max 10): mehr Waffenschaden | +1 % je Stack | +5 % × 10 = +50 % | H+S | Stack-Skill (`WeaponDamage`), SDK zählt sekündlich, leert bei Zünden/Verpuffen | CriticalAscention_Stack |
| 2 | `Deja-vu` | 5 | Kill Skill: Feuerrate und Nachladetempo. **Zünden frischt alle Kill Skills auf** | −4 % Intervall, −5 % Nachladen | −20 / −25 % | H+S | `WeaponFireInterval`, `WeaponReloadSpeed`; `SkillType=SKILL_TYPE_Kill`; SDK löst beim Zünden neu aus | Killer |
| 3 | `Vorbelastung` | 5 | Getroffene Gegner sind markiert: 8 s nach dem Zünden mehr Schaden von dir | +5 % | +25 % | H+S | Markierung nach Muster `DeathMark` / `DeathMark_Marked` | DeathMark |
| 3 | `Wiederholung` | 5 | Kill Skill: Kritschaden | +6 % | +30 % | H | `PlayerCriticalHitBonus`, `SKILL_TYPE_Kill` | Killer |
| 3 | `Nachhall` | 1 | Zünden stößt Gegner im Umkreis von 6 m zurück und staggert sie | — | — | S | SDK: Umkreissuche am Ankunftsort, Impuls + Stagger | — |
| 4 | `Erinnerung` | 1 | Der Anker speichert Kill-Skill-Zustände und Stacks; beim Zünden sind sie wieder da | — | — | S | SDK: aktive Skills beim Legen merken, beim Zünden neu aktivieren | — |
| 4 | `Wiederkehr` | 5 | Nach dem Zünden je Kill mit liegender Bombe mehr Waffenschaden (max 10), 10 s | +2 % je Kill | +10 % × 10 | H+S | Stack-Skill (`WeaponDamage`), SDK zählt Kills im Fenster | CriticalAscention_Stack |
| 5 | `Langzeitgedaechtnis` | 5 | Längeres Fenster; mit liegender Bombe mehr Kritschaden | +2 s, +4 % Krit | +10 s, +20 % | H+S | `PlayerCriticalHitBonus` (SDK schaltet mit dem Zustand), Fenster = `InitialDuration` zur Laufzeit | — |
| 5 | `Zeitwirbel` (Objekt `Zeitspur`; bis v1.04 „verlangsamen“, an Bodengegnern unmöglich — Spike A) | 1 | Solange die Bombe liegt: alle 2 s ein Schock-Impuls am Anker, wenn Gegner in 8 m sind, 1× Granatenschaden (v1.05, Nutzerentscheidung 2026-09-26) | — | — | S | SDK: Ticker + `explodieren(versatz=, mitte=)` am Anker | — |
| **6** | `Paradoxon` | 1 | **Aller Schaden, den du mit liegender Bombe verursacht hast, trifft beim Zünden dieselben Gegner noch einmal — zu 50 %** | — | — | S | SDK: Schadensbuch pro Ziel, Kappe je Ziel, nur lebende Ziele, verfällt beim Verpuffen | — |

### Baum 2 — Rückkehr (`BranchName=RUECKKEHR`)

| T | Name (Karte) | Rang | Wirkung | je Rang | Rang 5 | Kl. | Attribut / Mechanik | Vorlage |
|---|---|---|---|---|---|---|---|---|
| 1 | `Auffrischung` | 5 | Zünden stellt zusätzlich Leben und Schild her — über den Ankerwert hinaus | +4 % Max | +20 % | H+S | SDK liest den Rang, setzt die Pools beim Zünden (Pools setzen ist in Spike B belegt) | — |
| 1 | `Bereitschaft` | 5 | Cooldown-Rate und Schildaufladung | +2 % / +1,5 % | +10 / +7,5 % | H | `ActiveSkillCooldownConsumptionRate`, `ShieldPassiveRegenerationRate` | Grim |
| 2 | `Volle Rueckerstattung` | 5 | Zünden erstattet einen Teil der seit dem Legen verbrauchten Munitionsreserve | 20 % | 100 % | S | SDK: Reserve beim Legen merken, Differenz beim Zünden gutschreiben | — |
| 2 | `Stabilisator` | 5 | Mit liegender Bombe weniger Schaden | −2 % | −10 % | H+S | `ReceivedBulletDamageModifier` (+ die vier weiteren Received-Attribute), SDK schaltet mit dem Zustand | — |
| 3 | `Reinigung` | 1 | Zünden entfernt alle Statuseffekte; 2 s Schadensimmunität nach der Ankunft | — | — | S | SDK | — |
| 3 | `Zweite Meinung` | 5 | Verbündete um den Anker bekommen beim Zünden Schild | +6 % ihres Max | +30 % | S | SDK setzt die Pools direkt — **nicht** `TARGET_Allies` (trifft laut FL4K-Projekt immer auch den Spieler) | — |
| 3 | `Zeitkapsel` | 5 | **Am Anker erscheint zusätzlich ein Hologramm von dir**, das Feuer auf sich zieht und Verbündeten in 8 m Leben regeneriert | +0,8 %/s | +4 %/s | H+S | Decoy-Spawn (der in D9 abgeschaltete Weg, hier gezielt wieder an) + `HealthActiveRegenerationRate` als Aura | Innervate |
| 4 | `Es war nie passiert` | 1 | Fällst du in Fight-for-your-Life, während eine Bombe liegt, zündet sie automatisch | — | — | S | SDK: FFYL-Zustand beobachten | — |
| 4 | `Nachbild` | 5 | Beim Zünden bleibt am Absprungpunkt ein Nachbild, das Feuer auf sich zieht | 2 s + 1 s | 7 s | S | SDK: zweiter Decoy-Spawn (Muster aus Spike B) | — |
| 5 | `Sprengsatz` | 1 | Beim Zünden eine gewaltige Explosion am Absprungpunkt — Element der ausgerüsteten Granate, 5× Granatenschaden, Radius 10 m, kein Stoß/Stagger (neu seit v0.94, Nutzerwunsch 2026-09-26) | — | — | S | SDK: eigener `Behavior_Explode` vor dem Teleport, `ExplosionDefinition` je Element (explosiv = `Explosion_Nukem`) | — |
| 5 | `Gemeinsame Rueckkehr` | 5 | Verbündete um deinen Ankunftsort werden geheilt | +5 % ihres Max | +25 % | S | SDK, wie *Zweite Meinung* | — |
| **6** | `Schattenanker` | 1 | **Auch ohne gelegte Bombe merkt sich der Skill laufend einen Anker von vor 5 s.** Taste halten = Schattenzündung (1,5× Cooldown) | — | — | S | SDK: Ringpuffer im Tick; *Es war nie passiert* greift damit auch ohne Bombe | — |

### Baum 3 — Ausflug (`BranchName=AUSFLUG`)

| T | Name (Karte) | Rang | Wirkung | je Rang | Rang 5 | Kl. | Attribut / Mechanik | Vorlage |
|---|---|---|---|---|---|---|---|---|
| 1 | `Weite` | 5 | Bewegungstempo und Zielgeschwindigkeit | +3 % / −2 % FOV-Zeit | +15 / −10 % | H | `FootSpeed`, `WeaponZoomEndFOV` | Innervate, 0ptics |
| 1 | `Abstand` | 5 | Mehr Waffenschaden je 10 m Entfernung zum Anker (max 5 Stufen) | +2 % je Stufe | +10 % × 5 = +50 % | H+S | Stack-Skill (`WeaponDamage`), SDK misst die Entfernung und setzt Stacks | CriticalAscention_Stack |
| 2 | `Vorstoss` | 5 | Kill Skill: Bewegungstempo und Nachladetempo | +4 % / −4 % | +20 / −20 % | H | `FootSpeed`, `WeaponReloadSpeed`, `SKILL_TYPE_Kill` | Killer |
| 2 | `Sicherer Abstand` | 5 | Weiter als 15 m vom Anker: weniger Schaden | −2 % | −10 % | H+S | wie *Stabilisator*, Auslöser ist die Entfernung | — |
| 3 | `Ausbruch` | 1 | Legen gibt 3 s lang +50 % Bewegungstempo | — | — | H+S | `FootSpeed`, eigener Skill `DURATION_Timed 3.0` | **Skill_Speed** (0.25 fest, Muster passt exakt) |
| 3 | `Hinterhalt` | 5 | Mehr Kritschaden gegen Gegner, die nicht auf dich zielen | +4 % | +20 % | H | `PlayerAttackUnsuspectingTargetModifier` | **Ambush** (identisch) |
| 3 | `Weitschuss` | 5 | Genauigkeit und Projektilgeschwindigkeit | −4 % Streuung, +15 % Tempo | −20 / +75 % | H | `WeaponSpread`, `WeaponProjectileSpeedMultiplier` | Precisi0n, Vel0city |
| 4 | `Kurs halten` | 5 | Kills mit liegender Bombe verlängern das Fenster | +1 s | +5 s | S | SDK: Kill-Ereignis im Zustand *gelegt* | — |
| 4 | `Rueckenwind` (Objekt `RuecksprungDetonation`; bis v0.96 Explosion am Absprungpunkt — doppelte *Sprengsatz*) | 5 | Nach dem Zünden 10 s mehr Feuerrate und Nachladetempo, je weiter vom Anker desto mehr (voll ab 50 m); Dauer fest | +20 % | +100 % | HS | SDK: Effekt-Skill (passive Vorlage, 2 Effekte, −0,01 Intervall je Grad), Grad = round(100·b/(1+b)), Modul schaltet nach 10 s ab (v0.97, Nutzerwunsch 2026-09-26) | — |
| 5 | `Grenzgaenger` | 5 | Weiter als 30 m vom Anker: Feuerrate und Magazin | −3 % Intervall, +4 % Magazin | −15 / +20 % | H+S | `WeaponFireInterval`, `WeaponClipSize`, SDK schaltet nach Entfernung | — |
| 5 | `Kein Zurueck` | 1 | Verpufft die Bombe ungenutzt: 10 s +25 % Waffenschaden und **voller** Cooldown-Erlass | — | — | H+S | `WeaponDamage`, Skill `DURATION_Timed 10.0`; SDK setzt den Cooldown | — |
| **6** | `Zeitsprung` | 1 | **Beim Zünden werden alle Gegner auf der Linie zwischen dir und dem Anker verletzt und gestaggert**; Schaden nach Entfernung. 1 s Unverwundbarkeit nach der Ankunft | — | — | S | SDK: Linienabfrage zwischen Absprung und Anker | — |

---

## 6. Die technischen Fragen — **alle drei beantwortet (2026-09-19)**

Sie betrafen zusammen 23 der 36 Skills und waren die Voraussetzung für Phase 4–6. Belege und Messwerte: `docs/spikes.md`, Spikes D und E.

### 6.1 Wie aktiviert das SDK einen Skill? — **beantwortet 2026-09-19** ✔

**`pc.GetSkillManager()` liefert einen `SkillEffectManager`.** Gemessen: `ActivateSkill(pc, Skill_Speed)` hebt `FootSpeed` von 440.0 auf 550.0 (+25 %). Der Instigator ist der **Controller**, nicht der Pawn.

Damit sind alle 12 H+S-Skills technisch möglich — und drei Mechanismen, die im Entwurf noch als teuer galten, werden billig:

| Brauchen wir für | Funktion | Status |
|---|---|---|
| Skill an/aus („solange die Bombe liegt") | `ActivateSkill` / `DeactivateSkill` | gemessen |
| Startrang (Skillrang des Spielers) | `ActivateSkill(pc, Def, None, Grade)` — der Rang wirkt sofort | gemessen |
| **Stacks** (Gespannte Zeit, Abstand, Wiederkehr) | `UpdateSkillGrade(pc, Def, Grade)` **+ `RefreshSkillsForInstigator(pc)`** | gemessen |
| Aufräumen bei Kartenwechsel/Tod | `DeactivateAllSkillsForInstigator(pc)` | gemessen |
| **Kill Skills auffrischen** (Déjà-vu) | `NotifySkillEvent(...)` | offen |

**Die Falle:** `UpdateSkillGrade` allein gibt `True` zurück und tut nichts Sichtbares — der Attributwert bleibt stehen, bis `RefreshSkillsForInstigator` läuft. Im Modul sind die beiden deshalb in `skill_grad()` zusammengefasst und werden nie getrennt.

Vollständige Signaturen, die drei Stack-Wege und ihre Messwerte: `docs/spikes.md`, Spike E.

### 6.2 Wie kommen die Skill-Werte an die Objekte? — **beantwortet 2026-09-19** ✔

**Alles als Laufzeit-Kopien, keine Hotfixes.** Im Spiel bestätigt (Screenshot): eigener Ast „VERGANGENHEIT" mit einer eigenen Skill-Kopie, deren Wert die Skillkarte als **+50 %** ausweist, während Zer0s Original seine 7 % behält. `plan.md` D4 und D6 sind daraufhin geändert; `src/hotfixes.txt` und `exec zeitbombe.txt` werden nicht mehr gebraucht.

**Das Rezept für jeden Skill** (Einzelheiten und Messwerte in `docs/spikes.md`, Spike D):

```python
neu = _copy("SkillDefinition", "<Vorlage>", "<Outer-Paket>", "<Name>")   # gerootet
neu.SkillEffectDefinitions[0].BaseModifierValue.BaseValueConstant = 0.04  # haelt direkt
neu.SkillEffectDefinitions[0].PerGradeUpgrade.BaseValueConstant  = 0.04
tier = ast.Tiers[0]; skills = list(tier.Skills); skills[0] = neu; tier.Skills = skills
```

| Was | Ergebnis |
|---|---|
| `SkillEffectDefinitions` (Struct-Array) | elementweise direkt beschreibbar — **kein** Neusetzen des ganzen Arrays nötig |
| `Tiers` (Struct-Array), `Children` (Objekt-Array) | ebenso |
| `SkillTreePath` | ein **String** — einfach auf das eigene Wurzelobjekt zeigen lassen |
| Wurzelobjekt `SkillTree_*` | existiert **nie** im Speicher; ohne Vorlage bauen (`_neu`), es trägt nur `Root` |

> Die Hotfix-Regel „Struct-Felder in Arrays greifen nicht einzeln, immer das ganze Array setzen" (`CLAUDE.md`) gilt **nur für `set`/Hotfixes**, nicht für den SDK-Zugriff.

**Die eine Bedingung:** Alle Objekte müssen existieren, **bevor** der Charakter geladen wird — also in `ensure_seventh_character`, Stufe 1, wie schon die Klasse.

### 6.3 Greift `Tiers` zur Laufzeit? — **erledigt** ✔

Hat sich nebenbei beantwortet: Die Tier-Änderung war nach dem Neuladen des Spielstands wirksam (der Testskill stand im Menü). Ob sie auch *ohne* Neuladen greift, ist ungeprüft — und für uns belanglos, weil die Objekte künftig beim Modulstart entstehen, lange bevor jemand den Baum liest.

---

## 7. Was gekürzt wurde (und warum)

Der Entwurf in `plan.md` kam auf 16 S-Skills, die Obergrenze liegt bei ~12. Gekürzt wurde ausschließlich in Baum 2, weil er mit 8 S-Skills doppelt so teuer war wie die anderen:

| Vorher | Jetzt | Grund |
|---|---|---|
| *Auffrischung* als reiner SDK-Heal | H+S: SDK liest nur den Rang und setzt die Pools beim Zünden | Pools setzen ist in Spike B schon belegt — kein neuer Mechanismus |
| *Zeitkapsel* als SDK-Aura | H+S: Attribut-Aura am Decoy nach Muster Innervate | Vorlage vorhanden |
| *Stabilisator* als SDK-Resistenz | H+S: Attribute, SDK schaltet nur den Zustand | dasselbe Muster wie *Sicherer Abstand* — einmal bauen, zweimal nutzen |

*Zweite Meinung* und *Gemeinsame Rückkehr* bleiben getrennt (der Plan schlug vor, sie zusammenzulegen): Sie teilen sich im SDK dieselbe Funktion „heile Verbündete im Umkreis von X um Punkt Y", nur mit anderem Punkt und anderem Pool. Der Sparbetrag wäre gering, der Verlust an Baumbreite groß.

**Nicht enthalten:** Zeitschuld (Anhang A, Frage 3: raus). Falls sie zurückkommt, passt sie als 2–3 Skills in Ausflug.

---

## 7b. Englische Namen (v1.34, Nutzerwahl 2026-09-26)

Sichtbar ist seit v1.34 nur noch Englisch. **Die Objektnamen (erste Spalte im Modul, `_S("Gedaechtnis", …)`) bleiben deutsch** — Spielstände speichern Skillpunkte unter ihnen. Ebenso bleiben `Skill_Zeitbombe`/`ActionSkill_Zeitbombe` (`SKILL_OBJ`), die Klassen-ID `Chronomant` und die Astobjekte `Branch_Chronomaster_*`.

| Deutsch (Objekt/alt) | Englisch (sichtbar) |
|---|---|
| Chronomant (Klasse) | **Timekeeper** (Charakter bleibt *Chronomaster*) |
| Zeitbombe · Legen/Zünden · Anker · Verpuffen · Schattenzündung | **Time Bomb** · throw/detonate · anchor · expire · shadow detonation |
| VERGANGENHEIT · RUECKKEHR · AUSFLUG | **HINDSIGHT** · **REWIND** · **DETOUR** |
| Gedaechtnis, Nachwirkung, Gespannte Zeit, Deja-vu, Vorbelastung, Wiederholung, Nachhall, Erinnerung, Wiederkehr, Langzeitgedaechtnis, Zeitwirbel, Paradoxon | Memory, Aftermath, Tension, Deja Vu, Prior Record, Encore, Reverberation, Recollection, Recurrence, Long-Term Memory, Time Vortex, Paradox |
| Auffrischung, Bereitschaft, Volle Rueckerstattung, Stabilisator, Reinigung, Zweite Meinung, Zeitkapsel, Es war nie passiert, Nachbild, Sprengsatz, Gemeinsame Rueckkehr, Schattenanker | Refresh, Standby, Full Refund, Stabilizer, Cleanse, Second Opinion, Time Capsule, It Never Happened, Afterimage, Parting Gift, Homecoming, Shadow Anchor |
| Weite, Abstand, Vorstoss, Sicherer Abstand, Ausbruch, Hinterhalt, Weitschuss, Kurs halten, Rueckenwind, Grenzgaenger, Kein Zurueck, Zeitsprung | Open Road, Distance, Push Forward, Safe Distance, Breakout, Ambush, Long Shot, Stay the Course, Tailwind, Borderlander, Point of No Return, Time Skip |

Die deutschen Namen in diesem Dokument und in `plan.md`/`CHANGELOG.md` bleiben als Arbeitsnamen stehen.

## 8. Status je Skill

Stand 2026-09-26 abends (v1.33). Ein Skill ist erst „gemessen", wenn der Wert im Spiel abgelesen wurde (`CLAUDE.md`, Regel 3).

> **Zusammenfassung 2026-09-26 (v1.33) — die Tabelle unten ist die Geschichte mit Nachträgen, diese Liste der aktuelle Stand.**
> - **0 Platzhalter, keine offenen Hälften.** Umgebaut auf Nutzerwunsch: *Sprengsatz* (Explosion beim Zünden, Element der Granate), *Ruecksprung-Detonation* → **Rueckenwind** (Feuerrate/Nachladen nach Sprungweite), *Zeitspur* → **Zeitwirbel** (Schock-Impuls am Anker), *Nachhall* (Schockwelle mit Schaden statt Rückstoß), die drei **Kill Skills** (*Deja-vu*, *Wiederholung*, *Vorstoss*) stapeln unbegrenzt mit HUD-Zahl.
> - **Neu gemessen in dieser Sitzung:** *Nachbild*, *Sprengsatz*, *Schattenanker*, *Rueckenwind*, *Zeitwirbel*, *Reinigung* (mit Immunität), *Zeitkapsel*-Heilung, *Zweite Meinung*, *Gemeinsame Rueckkehr* (beide nur mit `zb koop selbst`), *Nachhall*, Kill-Stacks (Krit +0,040 je Stack).
> - **Gebaut, nicht eigens gemessen:** *Zeitsprung*-Immunität (dieselbe Funktion wie *Reinigung*), *Deja-vu*/*Vorstoss*-Werte je Stack (dieselbe Funktion wie *Wiederholung*), echter Koop als Client.
> - **Gemessen (v1.18, abends):** HUD-Zahl für *Gespannte Zeit* (+2,31 Waffenschaden je Sekunde bei Rang 5), *Abstand* (+4,62 je Stufe, baut sich beim Zurücklaufen ab), *Wiederkehr* (Timed-Vorlage stapelt echte Instanzen, Sichtprüfung).
> - **Action Skill: die Bombe wird geworfen** (v1.19–v1.33, D10). Alle Anker-Skills messen seitdem zum **Landepunkt**: *Abstand*, *Sicherer Abstand*, *Grenzgaenger*, *Rueckenwind*, *Zeitwirbel*, *Zeitsprung*, *Zeitkapsel* (Hologramm erscheint erst bei der Landung). Balance-Folge: 7–13 m Wurfweite. **Mit Wurf nicht eigens im Spiel geprüft:** *Zeitkapsel*-Hologramm am Landepunkt, *Schattenanker* (Taste halten, während die Bombe fliegt), Zünden im Flug (→ Wurfpunkt). Gebaut, im Log noch ohne Beleg.
> - **Balance ruht bis zu Tester-Rückmeldungen (Nutzer, 2026-09-26).** `GrenadeDamage` ist der Kartenwert der Granate (gemessen: Karte 301 → 300,5) und trägt *Sprengsatz* (5×), *Nachhall* (2×), *Zeitwirbel* (1×); Sonder-Granaten wie die *Sky Rocket* liefern wenig (138).

| Status | Bedeutung | Anzahl | Skills |
|---|---|---|---|
| gemessen | Wirkung im Spiel belegt (Datum + Wert im Changelog) | 17 | *Nachbild* (7 s am Absprungpunkt, Screenshot + Log, Leiche seit v0.93 versteckt; 2026-09-26), *Weite* (FootSpeed 440 → 506, 5 Punkte), *Ausbruch* (440 → 660 = +50 %), *Langzeitgedaechtnis* (Fenster 30 s), *Kein Zurueck* (Cooldown 35 s → 0 s nach dem Verpuffen), *Abstand* (Stufen 1–5, +10 % Basis je Stufe), *Wiederholung*³ (Krit 2,884 → 3,484 = +30 %), *Gespannte Zeit* (10/10 = +50 %), *Wiederkehr* (3 Kills → +30 % Basis, 10 s), *Deja-vu*¹ (`UpdateKillSkills(True)`, Kill-Skills aus → an; v0.70), **neu:** *Volle Rueckerstattung* (R5 = 100 %: verbraucht 756, zurück 756; v0.76), *Zeitsprung*⁵ (Ziel 135 → tot, Stoß → Tempo 565, Stagger; v0.76), *Paradoxon* (gebucht 251 → 126 nachgereicht = exakt 50 %; v0.86), *Vorbelastung* (R5 = +25 %: Treffer ~58 → Nachschlag 14, 8 s; v0.86), *Kurs halten* (R5, 4 Kills → Fenster 40 s, verpufft nach 40,5 s; v0.90), *Es war nie passiert* (FFYL → automatisch aufstehen, Teleport zum Anker, Leben 1 → 1.755.466; v0.90) |
| gebaut | Objekt im Baum, Mechanik läuft, Wirkung nicht (vollständig) gemessen | 16 | H: *Gedaechtnis*, *Bereitschaft*, *Hinterhalt*, *Weitschuss* · KILL: *Vorstoss*⁴ · HS geschaltet: *Stabilisator*, *Nachwirkung*², *Auffrischung*², *Sicherer Abstand*, *Grenzgaenger* · **S, neu:** *Erinnerung*⁶, *Reinigung*⁷, *Ruecksprung-Detonation*⁸, *Nachhall*⁹, *Zeitspur*¹⁰ · **Hologramme (v0.92):** *Zeitkapsel* (Hologramm am Anker, zieht Feuer — Heilung fehlt), *Sprengsatz*¹¹ (neu seit v0.94: Explosion beim Zünden, Nutzer: „funktioniert super") |
| Platzhalter | Baum-Skill ohne Effekt | 0 | — (seit v0.95 alle gebaut). **Nachtrag v0.97:** *Schattenanker* gemessen (Taste F gelernt, 0,5 s halten → Anker von vor 5,0 s, Cooldown 52,5 s; v0.95). *Zweite Meinung*, *Gemeinsame Rueckkehr* gebaut, ungeprüft (Koop; Testhilfe `zb koop selbst`). *Rueckenwind* (ex *Ruecksprung-Detonation*) gemessen (v0.99: Feuerintervall und Nachladezeit bei R5/50 m+ exakt halbiert, 10 s). Die Zählung oben ist noch v0.94. **Stand v0.99: 19 gemessen, 17 gebaut, 0 Platzhalter.** **v1.11:** *Zeitwirbel* (ex *Zeitspur*) gemessen (−160 je Impuls über ein Projektil am Anker, Kill beim dritten) → **20 gemessen, 16 gebaut.** **v1.12:** *Reinigung* vollständig gemessen (Immunität 2 s: Schadensfaktor 1,0 → 0,01), *Zeitsprung* hat seine 1 s Immunität (dieselbe Funktion, nicht eigens gemessen). **Messlauf 12:09:** *Zeitkapsel* (+4 %/s), *Zweite Meinung* (+30 % Schild), *Gemeinsame Rueckkehr* (+25 % Leben; beide mit `zb koop selbst`, echter Koop ungeprüft), *Sprengsatz* (−710 bzw. Kill) gemessen → **Stand: 25 gemessen, 11 gebaut, 0 Platzhalter.** |

**Technik von *Kurs halten* / *Es war nie passiert* (v0.89/v0.90):** das Fenster lebt an der Skill-Instanz (`SkillEffectManager.GetActiveSkillForInstigatorByDefinition`) als `Duration`/`DurationBaseValue`, Ende = `StartTime + Duration`, laufend nachgerechnet. Fight for your Life bricht den Action Skill ab — darum verpufft, wer *Es war nie passiert* hat, erst nach 0,5 s; ausgelöst wird über `WillowPlayerPawn:SetInjuredState`, aufgerichtet mit `GoFromInjuredToHealthy()`.

**Karten (v0.87):** die neun S-Skills mit Mechanik tragen den Platzhalter-Hinweis nicht mehr; wo etwas fehlt, sagt die Karte genau das (`S_GEBAUT` im Modul).

¹ Gemessen ist der Teil „Zünden frischt alle Kill Skills auf" (v0.70). Der Weg über `NotifySkillEvent(11 = SEVT_KilledEnemy, …)` ist **durchgefallen** — Charakter-Kill-Skills tragen kein `KillEvents`-Feld (`docs/spikes.md`, Spike E). Der Zahlenteil (Feuerrate, Nachladetempo) ist weiterhin ungemessen.
² Im Log geschaltet; der Wert (Waffenschaden bzw. Heilung) ist nicht messbar, solange der Testcharakter (Stufe 80) keinen Schaden nimmt.
³ Effekt von Hand aktiviert (`zb skill an 5`), nicht über einen Kill.
⁴ Blieb beim `UpdateKillSkills`-Test aus — **geklärt (v0.71): `Vorstoss=aus(R0)`, keine Punkte**, kein Defekt.
⁵ Schaden seit v0.79: der **größere** Wert aus Waffenschaden × Sprungweite/10 m und **5 % des Ziel-Lebens je 20 m Sprung** (höchstens 35 %) — damit er auf OP 10 zählt (Nutzerwunsch). Diese neue Formel selbst ist noch nicht an einem großen Ziel gemessen. Die 1 s Unverwundbarkeit fehlt (am Spieler-Pawn gibt es keine Invulnerability-Funktion).
⁶ `Kill Skills beim Legen aktiv` → beim Zünden `wiederhergestellt`, Nutzer: „funktioniert". Aber zwischen Legen und Zünden lagen nur 8 s, die Kill-Skills liefen noch — „aus → an" ist nicht nachgewiesen.
⁷ `RemoveAllStatusEffects()` läuft fehlerfrei; ob ein Statuseffekt verschwindet, ist am Testcharakter nicht zu sehen. Die 2 s Immunität fehlen (wie ⁵).
⁸ Trifft (`WillowAIPawn_7 auf 5.2 m -> Schaden 198`), gleiche Trefferlogik wie *Zeitsprung*; die Lebensdifferenz ist für diesen Skill selbst noch nicht abgelesen.
⁹ Umkreis, Treffer und **Stagger wirken** (drei Testziele, v0.77). **Der Rückstoß ist geparkt:** fliegende Gegner fliegen 4,3–5,4 m, Bodengegner bleiben stehen (`PHYS_NavMeshWalking`) — die ganze Messreihe in `docs/spikes.md`, „Rückstoß an Gegnern".
¹⁰ Umkreis, Frist und Rücksetzung laufen (`CustomTimeDilation 0.5` → nach 3 s `1.0`), **aber die Verlangsamung selbst ist offen:** Nutzer sah keine Zeitlupe; `zb zeitlupe` maß an Bodengegnern 0,0 m/s statt 2,5 (eher Einfrieren als Verlangsamen), Rakks unbeeinflusst, `GroundSpeed` unzuverlässig. Zwei Stichproben — Nutzerbeobachtung steht aus.

¹¹ `Behavior_Explode` mit `Explosion_IncendiaryMaster` (Brandgranate erkannt), Schaden 689 = 5 × `GrenadeDamage` 138, Radius 10 m; Nutzer sah Explosion und Wirkung. **Im Log nicht abgelesen:** die Nachmessung läuft im selben Frame und fand 0 von 11 mit Lebensverlust — der Schaden kommt offenbar erst danach an. Für „gemessen" die Nachmessung um 1 s verzögern. Offen auch, ob `GrenadeDamage` (138) der skalierte Wert ist — bei Stufe 80 wirkt er klein.

**Offen fuers Aussehen (Phase 8, Nutzerwunsch 2026-09-23):** *Zeitsprung* und *Nachhall* wirken, zeigen aber nichts — es fehlen Partikel/VFX (Linie, Explosion, Druckwelle). Zurückgestellt, bis die Mechanik steht; Einzelheiten in `plan.md`, „Geparkt und offen".

**Messregel (v0.60):** Scale-Modifikatoren **addieren** sich auf die Basis (Innervate: 440 × (1 + 0,15 + 0,35) = 660). „+10 % Waffenschaden" heißt +10 % der Waffen-Basis (22,17 je Kugel bei der Test-Flinte), nicht des angezeigten Endwerts — der enthält schon alle anderen Boni.

**Abweichung vom Entwurf:** *Stabilisator* und *Sicherer Abstand* decken vier Schadensquellen (Kugel, Nahkampf, Granate, Rakete), nicht fünf — die Vorlage Precisi0n hat vier Effektplätze, und Struct-Arrays lassen sich per SDK kürzen, nicht verlängern.
