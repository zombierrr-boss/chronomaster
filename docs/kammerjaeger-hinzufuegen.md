# Einen weiteren Kammerjäger hinzufügen (7., 8., … Slot)

> Stand 2026-09-19. Bewiesen mit dem Chronomaster (`sdk/chronomaster/__init__.py`, v0.13–v0.15): eigene Kachel, eigene Klasse, eigener Spielstand, überlebt Neustart. Vorbild: Nisha-Mod von LJBreeze (Nexus 654, GPL v3). Alle Objektpfade hier sind im Spiel verifiziert.

## Das Prinzip in einem Absatz

Borderlands 2 kennt keine feste Charakterliste. Die Auswahl entsteht aus drei Quellen, die alle zur Laufzeit erweiterbar sind: (1) der **Objektkette** eines Charakters — Klasse, Klassen-ID, Namens-ID, Standardprofil; (2) der **Charakterliste des DLC-Managers** (`WillowDownloadableContentManager.Characters`), aus der die Engine ihre Klassentabelle baut — so wurden Gaige und Krieg nachgerüstet; (3) der **Flash-Oberfläche**, die beim Befüllen (`CommitSelectableCharacters`) für jeden zusätzlichen Eintrag eine Kachel anlegt. Ein SDK-Modul kann alle drei bedienen — ohne `.upk`, mit Laufzeit-Kopien vorhandener Objekte. Der Spielstand speichert die Klasse als Pfadstring; das Modul muss die Objekte deshalb **vor** dem Laden eines Spielstands wieder erzeugen (beim Aktivieren des Moduls).

## Rezept

### 1. Vorlage wählen

Jeder neue Charakter ist eine Kopie eines vorhandenen: das bestimmt Modell, Animationen, Stimme, Action-Skill-Kern und Skill-Objekte. Vorlage = der Vault Hunter, dem der neue am nächsten kommt.

| Vorlage | Klasse | ClassId | NameId | Profil |
|---|---|---|---|---|
| Zer0 | `GD_Assassin.Character.CharClass_Assassin` | `GD_PlayerClassId.Assassin` | `GD_PlayerNameId.Assassin` | `GD_DefaultProfiles.Assassin.Profile_Assassin` |
| Axton | `GD_Soldier.Character.CharClass_Soldier` | `GD_PlayerClassId.Soldier` | `GD_PlayerNameId.Soldier` | `GD_DefaultProfiles.Soldier.Profile_Soldier` |
| Maya | `GD_Siren.Character.CharClass_Siren` | `GD_PlayerClassId.Siren` | `GD_PlayerNameId.Siren` | `GD_DefaultProfiles.Siren.Profile_Siren` |
| Salvador | `GD_Mercenary.Character.CharClass_Mercenary` | `GD_PlayerClassId.Mercenary` | `GD_PlayerNameId.Mercenary` | `GD_DefaultProfiles.Mercenary.Profile_Mercenary` |
| Gaige | `GD_Tulip_Mechromancer.Character.CharClass_Mechromancer` | `GD_TulipPackageDef.PlayerClassId.Mechromancer` | `GD_TulipPackageDef.PlayerNameId.Mechromancer` | `GD_TulipPackageDef.Profiles.Profile_Mechromancer` |
| Krieg | `GD_Lilac_PlayerClass.Character.CharClass_LilacPlayerClass` | `GD_LilacPackageDef.PlayerClassId.Psycho` | `GD_LilacPackageDef.PlayerNameId.LilacPlayerClass` | `GD_LilacPackageDef.Profiles.Profile_LilacPlayerClass` |

Nur die Zer0-Zeile ist im Spiel getestet; die anderen Pfade stammen aus dem OpenBLCMM-Datenpaket. **Achtung bei Gaige/Krieg als Vorlage:** ihre Pakete (`GD_TulipPackageDef`, `GD_LilacPackageDef`) sind beim Modulstart noch nicht geladen — dann muss auch Stufe 1 ins Auswahlmenü verschoben oder das Paket vorher geladen werden (siehe Fallen).

### 2. Stufe 1 — Objektkette beim Modulstart (Basisspiel-Vorlagen)

Vier Objekte per `unrealsdk.construct_object(Klasse, Outer, Name, template_obj=Vorlage)`, **jedes gerootet** (`obj.ObjectFlags |= 0x4000`), dann verknüpft:

```python
name_id   = copy("PlayerNameIdentifierDefinition",  "GD_PlayerNameId.Assassin",              "GD_PlayerNameId",           "MeinHeld")
class_def = copy("PlayerClassDefinition",           "GD_Assassin.Character.CharClass_Assassin", "GD_Assassin.Character",  "CharClass_MeinHeld")
class_id  = copy("PlayerClassIdentifierDefinition", "GD_PlayerClassId.Assassin",             "GD_PlayerClassId",          "MeineKlasse")
profile   = copy("PlayerSaveGame",                  "GD_DefaultProfiles.Assassin.Profile_Assassin", "GD_DefaultProfiles.Assassin", "Profile_MeinHeld")

name_id.CharacterName = "MeinHeld"            # Vorgabe im Namensfeld
name_id.LocalizedCharacterName = "MeinHeld"   # Infokarte
name_id.UISortOrder = 6                       # Kachelreihenfolge: 0-5 sind vergeben, 7 = achter Charakter usw.
name_id.CharacterClassId = class_id
name_id.DefaultSaveGame = profile
class_id.ClassName = "MeineKlasse"
class_id.LocalizedClassName = "MEINEKLASSE"   # Infokarte, Lade-Menü
class_id.LocalizedClassNameNonCaps = "MeineKlasse"
class_id.DlcCharacterDef = None
class_def.CharacterNameId = name_id
profile.PlayerClassDefinition = class_def
```

Der Objektname (dritter/vierter Parameter) wird Teil des Pfads, den der Spielstand speichert (`GD_Assassin.Character.CharClass_MeinHeld`). **Nie mehr ändern**, sonst laden alte Spielstände nicht.

### 3. Stufe 2 — DLC-Registrierung (braucht ein DLC-Paket)

```python
package_def  = copy("DownloadablePackageDefinition",   "GD_TulipPackageDef.PackageDef_Tulip",   "GD_TulipPackageDef", "PackageDef_MeinHeld")
registration = copy("DownloadableCharacterDefinition", "GD_TulipPackageDef.CharacterDef_Tulip", "GD_TulipPackageDef", "CharacterDef_MeinHeld")
registration.PackageDef = package_def
registration.ContentDisplayName = "MeinHeld"
package_def.PackageDisplayName = "MeinHeld"
package_def.DLCName = "MeinHeld"
package_def.PackageId = 27          # eindeutig! 25 = Nisha, 26 = Chronomaster

manager = <erste Instanz von WillowDownloadableContentManager ohne "Default__">
manager.ContentPackages.append(package_def)
manager.AllContent.append(registration)
manager.Characters.append(registration)      # <- ohne das bleibt die Klassentabelle bei sechs
```

`GD_TulipPackageDef` existiert beim Modulstart noch nicht (`load_package` holt es nicht). Deshalb: beim Start versuchen, im Auswahlmenü (Hook aus Schritt 4) nachholen. Alles idempotent halten — `copy()` gibt vorhandene Objekte zurück, Listen nur ergänzen, wenn das Objekt fehlt.

### 4. Kachel — PRE-Hook auf `WillowGame.CharacterSelectionGFxObject:CommitSelectableCharacters`

```python
movie = obj.Outer                              # CharacterSelectionReduxGFxMovie
if name_id not in movie.SelectableCharacters:
    movie.SelectableCharacters.append(name_id)
    obj.AddSelectableCharacter("/ package/UI_CharacterPortraits/Assassin")   # Portrait der Vorlage
```

Der Portrait-Pfad ist eine Scaleform-URL auf ein `SwfMovie`-Objekt (`StatusMenuGFxPortrait` der Vorlage: `UI_CharacterPortraits.Assassin` → `/ package/UI_CharacterPortraits/Assassin`, mit Leerzeichen nach dem Schrägstrich). Ein eigenes Portrait braucht ein eigenes SWF in einem `.upk` (Teil B).

### 5. Mehrere Charaktere

Alles oben pro Charakter wiederholen mit eigenen Namen, `UISortOrder` (6, 7, 8 …) und `PackageId` (26, 27, 28 …). Der Hook aus Schritt 4 hängt alle in `UISortOrder`-Reihenfolge an. Für einen 8. Charakter (z. B. FL4K) heißt das: eigenes Modul oder eine Charakterliste in einem gemeinsamen Modul — im Chronomaster-Modul ist `SEVENTH` ein einzelnes Dict; für mehrere Charaktere wird daraus eine Liste von Dicts, und `ensure_seventh_character` / `_on_commit_characters` iterieren darüber. Zwei getrennte Module (`zeitbombe`, `fl4k`) gehen auch — beide registrieren ihren Hook auf `CommitSelectableCharacters`, die Reihenfolge der Kacheln folgt dann der Hook-Reihenfolge.

### 6. Stufe 1b — eigener Skillbaum (im Spiel bestätigt 2026-09-20)

Die Kopie spielt sich sonst exakt wie die Vorlage. Der eigene Baum entsteht als weitere Laufzeit-Kette in **Stufe 1**, denn er muss stehen, bevor ein Spielstand lädt (Vorbild: `ensure_skilltree()` im Chronomaster-Modul):

1. **Vorlagen laden.** `load_package("<Vorlage>_Streaming_SF")` — für Zer0 also `GD_Assassin_Streaming_SF`. **Das ist die wichtigste Zeile des ganzen Schritts** (siehe Falle unten).
2. **Wurzelobjekt** `SkillTreeDefinition` **ohne Vorlage** bauen (`construct_object` ohne `template_obj`) — `SkillTree_<Vorlage>` liegt nie im Speicher. Es trägt nur das Feld `Root`.
3. **Wurzelast** als Kopie von `<Skills>.SkillTree.Branch_ActionSkill_*` (trägt in `Tiers(0)` den Action Skill).
4. **Drei Äste** als Kopien der drei Vorlagen-Äste, `BranchName` setzen — der Text erscheint so im Skillmenü und kommt deutsch aus dem Objekt (`Branch_Sniping` = `HINTERHALT`).
5. **Verknüpfen:** `wurzel.Root = wurzelast`, `wurzelast.Children = [ast1, ast2, ast3]`, dann `class_def.SkillTreePath = wurzel._path_name()` — ein **String**, kein Objektverweis.

Alle Array-Zugriffe (`Tiers`, `Children`, `SkillEffectDefinitions`) sind per SDK elementweise schreibbar; die Hotfix-Regel „immer das ganze Array setzen" gilt hier nicht. Danach die Skills in den Tiers durch eigene Kopien ersetzen (Rezept: `docs/skills.md`, 6.2).

Eigener Action Skill: Hooks auf die vier Skill-Funktionen (`TRACE_FUNCS` im Modul). Eigenes Modell/Portrait/Stimme: `.upk`-Pakete wie bei Nisha (`unrealsdk.load_package(<Dateipfad>)`), Teil B.

## Fallen (alle selbst erlebt)

| Falle | Symptom | Lösung |
|---|---|---|
| Objekte nicht gerootet | Objekte sind im Menü wieder weg, werden neu erzeugt, Verknüpfungen fehlen | `ObjectFlags \|= 0x4000` sofort nach `construct_object` |
| Zu später Hook (`BuildCharacterList` POST) | Eintrag in der Liste, aber keine Kachel; beim Bestätigen Klasse der zuletzt gewählten Kachel | PRE auf `CommitSelectableCharacters` + `AddSelectableCharacter` |
| Keine DLC-Registrierung | Kachel und Infokarte da, aber Klasse bleibt die vorherige | `manager.Characters.append(registration)` |
| Kette bricht beim Start an Tulip ab, **bevor** verknüpft wird | Lade-Menü zeigt den Klassennamen der Vorlage | Stufe 1 (Basisspiel) zuerst und vollständig, Stufe 2 danach mit eigenem try |
| `pc.GetCachedSaveGame()` beschreiben | Schreiben ohne Wirkung — es ist eine Kopie | Klasse über die Objektkette, nicht über den Spielstand |
| Referenz auf das Menü-Objekt cachen | Absturz, sobald das Menü zu ist | bei jedem Aufruf per `find_all` frisch suchen |
| `WillowDownloadableContentManager.bDeleteMe` | AttributeError, Registrierung übersprungen | kein Actor, Flag existiert nicht |
| `rlm` nach Hook-Änderungen | alte Hooks feuern weiter, Log widerspricht dem Code | Spiel neu starten |
| PowerShell `Set-Content -Encoding UTF8` | Python-Datei beginnt mit BOM, Modul lädt nicht | `UTF8Encoding($false)` |
| Doppelte `PackageId` | unbekannt, vermutlich Konflikt mit Nisha/anderen DLC-Mods | eindeutige IDs vergeben |
| **Skill-/Baumpaket über den Pfadnamen laden** | `Outer-Paket fehlt: <Skills>.SkillTree`, obwohl `load_package` ohne Fehler durchlief. Das Paket `GD_Assassin_Skills` **existiert** von Anfang an — nur ohne die Gruppe `.SkillTree` darin, und ein `load_package` darauf bringt nichts dazu | `load_package("<Vorlage>_Streaming_SF")` nehmen, nicht den Namen aus dem Objektpfad. `zb pakete` findet den richtigen Namen, wenn er bei einer anderen Vorlage anders heißt |
| Mehrere Kandidaten in **einer** Messung durchprobieren | Man weiß hinterher, *dass* es geht, aber nicht *wodurch* — hier führte das zu der falschen Erklärung „beim Modulstart zu früh" | nach jedem Kandidaten einzeln prüfen und den Treffer ins Log schreiben |

## Was noch nicht geklärt ist

- Koop (Nisha: „Solo play only") — vermutlich fehlt die Klasse beim Mitspieler.
- Klassenmods und Customizations (Skins/Heads) für die neue ClassId — die Kopie zeigt auf die Pools der Vorlage; Nisha registriert eigene `CustomizationSet`/ItemPools.
- Ob `unrealsdk.load_package` DLC-Pakete beim Start laden kann, wenn man den Dateipfad statt des Paketnamens angibt (Nisha macht das mit absoluten Pfaden auf ihre `.upk`).
- Level-30-Startcharaktere (`GD_Level30Character.*`) und das Lade-Menü-Portrait — nicht untersucht.
