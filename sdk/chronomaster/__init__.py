"""
Chronomaster in Borderlands 2 - SDK-Modul "chronomaster" (bis v1.34 "zeitbombe"). Version: siehe __version__ unten.

Stand 2026-09-23, Sitzungsende (v0.92):
  - Phase 1/2 durch. Spike A (Zeit-Dilation) an Gegnern WIDERLEGT (v0.88, docs/spikes.md).
  - Phase 3 KOMPLETT und im Spiel bestaetigt: Legen, Zuenden, Verpuffen, 20-s-Fenster, 35-s-Cooldown
    (17,5 s beim Verpuffen), Caesium-Ladung am Anker, Zer0s Hologramm/Unsichtbarkeit/Markierung/Klang
    abgehaengt - Zer0 selbst unveraendert (D6; 'zb ziel' und die Hologramme setzen seine Factory zurueck).
  - Phase 4-6: alle 36 Skills in den Baeumen. 16 gemessen, 17 gebaut, 3 Platzhalter (Zweite Meinung,
    Gemeinsame Rueckkehr, Schattenanker). Status je Skill: docs/skills.md, 8; im Modul: S_GEBAUT.
  - Die Mechaniken, nach Abschnitten (im Modul danach suchen):
      "Handgriff 2"          Ticker (PlayerTick, 1/s mit liegender Bombe): Stacks, Entfernung zum Anker
      "Handgriff 3"          Kill-Zaehler (NotifyKilledEnemy): Wiederkehr, Kurs halten
      "Handgriff 3b"         Deja-vu (pc.UpdateKillSkills)
      "Handgriff 4, Paket A" am Zuenden: Umkreis-Treffer (_treffer: Schaden/Stoss/Stagger), Volle
                             Rueckerstattung, Reinigung, Nachhall, Ruecksprung-Detonation, Zeitsprung
      "Handgriff 4, Paket B" Schadens-Hook (WillowAIPawn:TakeDamage): Paradoxon, Vorbelastung, Zeitspur
      "Handgriff 4, Paket C" Fight for your Life: Es war nie passiert; Kurs halten
      "Handgriff 4, Paket D" selbst gespawnte Hologramme: Zeitkapsel, Nachbild, Sprengsatz
  - Geparkt: Rueckstoss an Bodengegnern, Verlangsamung (beide: PHYS_NavMeshWalking, docs/spikes.md).
  - Naechster Handgriff: plan.md, Wiedereinstieg ("Wenn der Nutzer 'lass uns weitermachen' sagt").

Aufgabe: Seit D4 (2026-09-19) traegt dieses Modul BEIDES - Daten und Logik. Skills, Baeume, Texte
und Zahlen entstehen als Laufzeit-Kopien; Hotfixes werden nicht mehr gebraucht, an Zer0s Objekten
wird nichts geaendert. (src/hotfixes.txt und exec zeitbombe.txt sind damit Altlast.)

Was das Modul heute tut:
  1. Den 7. Vault Hunter anlegen (ensure_seventh_character, Spike C - funktioniert): beim Start
     Laufzeit-Kopien von Zer0s Klasse/ClassId/Profil/NameId (gerootet), im Auswahlmenue die
     DLC-Registrierung und die Kachel (_on_commit_characters). Anleitung: docs/kammerjaeger-hinzufuegen.md
  2. Die eigene Baumkette anlegen (ensure_skilltree - im Spiel bestaetigt 2026-09-20): Wurzelobjekt,
     Wurzelast und die drei Aeste VERGANGENHEIT / RUECKKEHR / AUSFLUG als Kopien, SkillTreePath der
     eigenen Klasse darauf. Entsteht beim Modulstart, vor jedem Spielstand. Voraussetzung ist der
     richtige Paketname: load_package("GD_Assassin_Streaming_SF") bringt Zer0s Vorlagen, das
     naheliegende "GD_Assassin_Skills" nicht.
  2b. Die 36 Skills in die Aeste haengen (_baeume_fuellen, Abschnitt "Phase 4-6"): je Skill eine
     Kopie eines Zer0-Skills mit eigenem Namen/Text/Effekten/Praesentationen, dazu bei HS-Skills
     ein versteckter Effekt-Skill <Name>_Wirkung, den das Modul mit dem Rang des Spielers schaltet
     (mechanik_gelegt / mechanik_gezuendet / mechanik_verpufft, fenster_anpassen). Eigenes Layout
     Layout_Chronomaster (12 Zellen; Zer0 hat 10).
  3. Den Action Skill tragen (Phase 3, alle Schritte im Spiel bestaetigt):
       - ensure_action_skill: eigene Kopien Skill_Zeitbombe / ActionSkill_Zeitbombe (Name, Text,
         Fenster 20 s, Nahkampf-Dash aus, Vision Mode leer) im Tiers(0) des Wurzelastes
       - ensure_cooldown_pool: eigene Pool-Kopie mit 35 s an der eigenen Klasse
       - drei Hooks: Skilltaste -> legen(), zweiter Druck -> zuenden() + ResetActionSkill +
         StartActiveSkillCooldown, Ablauf -> verpuffen() mit halbem Cooldown
       - ein vierter Hook blockiert Zer0s Skill_Stealth (Unsichtbarkeit) und seit v0.63 den
         Schadensstack Skill_ActionSkillDamageBuffStack, den Skill_Deceptions BPD im Loop anwirft
       - ein fuenfter Hook blockiert Zer0s Klang: Wwise-State "ActionSkill_On" (Daempfer - im Spiel
         bestaetigt v0.49) sowie "Start"/"Loop" (Ambiente, bestaetigt v0.50)
     Alles gegattert durch ist_chronomaster - Zer0s Decepti0n bleibt, was sie ist.
     Schritt 5 (bestaetigt v0.47): bombe_setzen spawnt am Anker ein DynamicSMActor_Spawnable per
     pc.Spawn + SetStaticMesh (Caesium-Ladung, gerootet), bombe_weg raeumt es beim Zuenden/Verpuffen ab.
  4. Skills schalten (Spike E - gemessen): skill_an / skill_aus / skill_grad / skill_aktiv /
     skills_aus_alle. Darauf stehen die HS-Skills (wirkung_an / wirkung_aus).
  5. kopie() ist der Prototyp aus Spike D (eigene Skill-Kopie, Wert aendern, messen) - durch
     _skill_bauen abgeloest, bleibt als kleinster Beweis stehen.

Konsole (alles landet in Binaries/Win32/Plugins/unrealsdk.log, Praefix [ZB]):
  zb status                 Zustand (Karte, Pawn, Klasse, bereit/gelegt, Anker)
  zb legen                  Anker von Hand setzen (der Skill tut das sonst selbst)
  zb zuenden                Anker wiederherstellen (Teleport + Werte); Anker bleibt fuer Wiederholung
  zb ende [2|1|3]           laufenden Skill beenden (Standard 2 = ResetActionSkill, wirkt)
  zb loeschen               Anker verwerfen, Zustand zurueck auf bereit
  zb bombe [MESH] [SCALE]   Bombenobjekt am eigenen Standort spawnen (Standard: BOMB_MESH, 1.0) -
                            zum Ausprobieren anderer Meshes. 'zb bombe weg [1|2|3]' entfernt es,
                            'zb bombe diag' zeigt Kollisionsflags und alle Bomben-Actors im Level,
                            'zb bombe koll 1|2|3' probiert Kollisions-Abschaltungen (1 ist belegt).
  zb attr [NAME|PFAD] [pawn|weapon|pc]  Attributwert ablesen (Standard WeaponDamage an der Waffe).
                            Kurznamen: WeaponDamage, FootSpeed, krit, magazin, feuerrate.
  zb rang [NAME]            Punkte des Spielers in einem Baum-Skill.
  zb wirkung an|aus NAME [GRAD]   Effekt-Skill eines HS-Skills von Hand schalten.
  zb meshes [FILTER]        geladene StaticMeshes ins Log (nur die kommen fuer die Bombe in Frage -
                            Prop_*/FX_*-Pakete gibt es nicht als .upk, load_package taete nichts)
  zb props pawn|pc|weapon FILTER   Eigenschaften eines Objekts ins Log (Diagnose, Namen finden)
  zb funcs KLASSE [FILTER]  Funktionen einer Klasse MIT Elternklassen ins Log. Immer zuerst, bevor
                            ein Funktionsname geraten wird (GetSkillGrade sass am Controller, v0.54).
                            Enum-Parameter zeigen seit v0.68 ihren Enum-Namen (ByteProperty:ENUM).
  zb enum [FILTER]          Enums samt Werten ins Log (Standard: alles mit "skill" im Namen). Die
                            Werte stehen in keinem Dump, nur im Speicher - so kam SEVT_KilledEnemy=11.
  zb dejavu                 Das Kill-Ereignis von Hand melden (Deja-vu), mit an/aus der Kill-Skills
                            vor und nach dem Melden - ohne den Skillzyklus zu durchlaufen.
  zb spur                 Skill-Ereignisse loggen an/aus (Standard aus) - auch jede Skill-
                            Aktivierung durch BPDs und jeden Kill (NotifyKilledEnemy).
  zb skill an|aus|grad N|stack N|status [PFAD]
                            Skill schalten und das Attribut seines ERSTEN Effekts messen (Weapon.*
                            an der Waffe, sonst am Pawn). Standard: Innervate (+7 % FootSpeed je Rang).
                            'stack N' = an + Raenge 2..N + aus, alles in einem Befehl.
  zb kopie                  Prototyp: eigene Skill-Kopie anlegen, Wert aendern, Wirkung messen
  zb baum                   Diagnose: die eigene Baumkette ins Log (alle Tiers mit Skill[Rang/Max]);
                            fehlt sie, wird ein Anlauf nachgeholt. Angelegt wird sie beim Modulstart.
  zb rang [NAME]            Punkte des Spielers in einem (oder allen) Baum-Skills - prueft GetSkillGrade
  zb wirkung an|aus NAME [GRAD]   Effekt-Skill eines HS-Skills von Hand schalten (z. B. Stabilisator)
  zb pakete                 Diagnose: welcher Paketname bringt Zer0s Skill-/Baumobjekte in den
                            Speicher? Im HAUPTMENUE ausfuehren - dort entscheidet sich die Frage.
  zb askill                 Diagnose: Objekte am Action Skill (Tiers(0), Skill_Deception,
                            ActionSkill_Deception) und der Cooldown-Pool. Hat in Schritt 2/3 die
                            Klassennamen und die Cooldown-API geliefert; bleibt als Nachschlagewerk.
                            Mit GELADENEM Chronomaster ausfuehren.

Testhilfen - aendern den Spielstand DAUERHAFT, laufen nur auf dem Chronomaster (testchar_only):
  zb xp [N]                 N Erfahrungspunkte gutschreiben (Standard 1000, hoechstens 2 Mio)
                            KEIN "bis Stufe N" - warum nicht, steht bei xp()
  zb respec                 Skillpunkte kostenlos zuruecksetzen
  zb cash [N]               Geld gutschreiben (Standard 1 Mio)

Regeln (aus Abstuerzen und Fehlversuchen, Details docs/spikes.md):
  - Laufzeit-Objekte (construct_object) immer rooten (_root), sonst holt sie die GC.
  - Nie Referenzen auf Menue-Objekte cachen - bei jedem Aufruf frisch suchen (Absturz 18:41).
  - pc.GetCachedSaveGame() ist eine Kopie; Schreiben darauf ist wirkungslos.
  - Nach Aenderungen an Hooks das Spiel neu starten, "rlm" laesst alte Hooks weiterlaufen.
  - Vor jedem Hook das Paket der Klasse im Dump nachlesen ("Class=" -Zeile): Behavior_PostAkEvent
    liegt in GearboxFramework, Behavior_ActivateSkill in WillowGame. add_hook prueft nichts -
    ein falscher Name heisst nur: der Hook feuert nie (v0.48).
  - Funktionsnamen nie aus der Erinnerung: 'zb funcs KLASSE' fragen (v0.53: PlayerSkillTree hat
    kein GetSkillGrade, der Controller schon).
  - Struct-Arrays (SkillEffectDefinitions) lassen sich per SDK elementweise beschreiben und
    kuerzen; Verlaengern ist unbelegt - Vorlage nach Effektzahl waehlen.
  - Prop_*/FX_*-Pakete gibt es nicht als .upk; nur geladene Meshes sind erreichbar ('zb meshes'),
    beim ersten Fund rooten, dann ueberleben sie den Kartenwechsel.
  - Im Fahrzeug ist pc.Pawn das Fahrzeug -> Legen/Zuenden blockiert.
  - Muster aus ../borderlands 2 mod/sdk/fl4k_pet: SetLocation lehnt ab -> Location direkt schreiben,
    dann PHYS_Falling (2). Actor.Destroy greift nicht -> Died(). bIsCriticalActor friert KI ein.
"""

import math
from dataclasses import dataclass
from typing import Any

import unrealsdk
from mods_base import ENGINE, Game, build_mod, command
from unrealsdk import logging
from unrealsdk.unreal import UObject, WeakPointer

__version__ = "1.40"
__author__ = "zombierrr"

# Der Charaktername ist ein Platzhalter (plan.md, Anhang A). Seit D4 ist DIESE Konstante die einzige
# Stelle, an der er steht - hotfixes.txt ist stillgelegt. Nirgends sonst fest verdrahten.
CHARACTER_NAME = "Chronomaster"

# Die Vorlage fuer Teil A ist Zer0 (plan.md, D2). Wo genau seine Objekte stehen, sagt SEVENTH
# weiter unten - eine eigene Konstante dafuer waere eine zweite Wahrheit.


@dataclass
class Anchor:
    """Alles, was beim Legen gespeichert und beim Zuenden wiederhergestellt wird (plan.md, Anhang A, Frage 4)."""

    map_name: str
    x: float
    y: float
    z: float
    pitch: int
    yaw: int
    roll: int
    health: float
    shield: float
    weapon: str  # Pfad der aktiven Waffe - Magazin wird nur zurueckgesetzt, wenn sie noch aktiv ist
    magazine: int


_anchor: Anchor | None = None


def local_pc() -> UObject | None:
    try:
        return ENGINE.GamePlayers[0].Actor
    except Exception:  # noqa: BLE001
        return None


def map_name(pc: UObject) -> str:
    try:
        return pc.WorldInfo.GetMapName(True)
    except Exception:  # noqa: BLE001
        return "?"


def player_class(pc: UObject) -> str | None:
    """Pfad der PlayerClassDefinition. Spike B klaert, welches Feld sie traegt - deshalb mehrere Kandidaten."""
    for getter in (
        lambda: pc.PlayerClass,
        lambda: pc.Pawn.PlayerClass,
        lambda: pc.PlayerReplicationInfo.PlayerClass,
    ):
        try:
            obj = getter()
            if obj is not None:
                return obj._path_name()
        except Exception:  # noqa: BLE001
            continue
    return None


def ist_chronomaster(pc: UObject | None) -> bool:
    """Nur unser Charakter bekommt die Zeitbombe. Ohne diese Pruefung wuerde die Verdrahtung aus
    Phase 3 auch Zer0s Decepti0n umbauen - ein Verstoss gegen D6 (der Wirt bleibt unberuehrt)."""
    cls = player_class(pc) if pc else None
    return bool(cls and cls.endswith(f"CharClass_{CHARACTER_NAME}"))


def in_vehicle(pc: UObject) -> bool:
    """Im Fahrzeug ist pc.Pawn das Fahrzeug selbst (Test 2026-09-19: Teleport des Autos -> schwerer Schaden,
    Schild-Setzen wirkungslos). Legen und Zuenden sind dort blockiert (plan.md, 2.3)."""
    try:
        return pc.Pawn.Class._inherits(unrealsdk.find_class("WillowVehicle"))
    except Exception:  # noqa: BLE001
        return "Vehicle" in pc.Pawn.Class.Name


def try_call(label: str, fn: Any) -> Any:
    """Aufruf mit Log statt Absturz: Spike-Befehle sollen zeigen, WAS scheitert."""
    try:
        v = fn()
        logging.info(f"[ZB]   {label}: {v}")
        return v
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB]   {label}: FEHLER {ex}")
        return None


# ---------------------------------------------------------------- Legen / Zuenden


def legen() -> None:
    global _anchor
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] legen: kein Spieler-Pawn (Hauptmenue?)")
        return
    if in_vehicle(pc):
        logging.info("[ZB] legen: im Fahrzeug nicht moeglich")
        return
    logging.info("[ZB] legen: lese Zustand")
    loc = pawn.Location
    rot = pc.Rotation  # Blickrichtung haengt am Controller, nicht am Pawn
    health = try_call("GetHealth", pawn.GetHealth)
    shield = try_call("GetShieldStrength", pawn.GetShieldStrength)
    weapon = pawn.Weapon
    magazine = try_call("Weapon.ReloadCnt", lambda: weapon.ReloadCnt) if weapon else None
    _anchor = Anchor(
        map_name=map_name(pc),
        x=loc.X, y=loc.Y, z=loc.Z,
        pitch=rot.Pitch, yaw=rot.Yaw, roll=rot.Roll,
        health=float(health or 0), shield=float(shield or 0),
        weapon=weapon._path_name() if weapon else "",
        magazine=int(magazine or 0),
    )
    logging.info(f"[ZB] Anker gesetzt: {_anchor}")
    # v1.19: geworfen statt abgelegt. Bis zur Landung gilt der Wurfpunkt als Anker; der Landepunkt
    # ersetzt nur die Koordinaten (Nutzerentscheidung 2026-09-26: man kehrt dorthin zurueck, wo die
    # Bombe liegt). Der Legen-Effekt kommt mit der Landung (_wurf_landen).
    bombe = bombe_setzen(pawn, wurf=True)
    if bombe is None or not wurf_starten(pc, pawn, bombe):
        effekt("Legen", FX_LEGEN, _vec(loc.X, loc.Y, loc.Z), 400.0)   # Phase 8 (v1.00)


def zuenden() -> None:
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] zuenden: kein Spieler-Pawn")
        return
    if _anchor is None:
        logging.error("[ZB] zuenden: kein Anker - erst 'zb legen'")
        return
    if _anchor.map_name != map_name(pc):
        logging.error(f"[ZB] zuenden: Anker liegt in {_anchor.map_name}, wir sind in {map_name(pc)} - verworfen")
        return
    if in_vehicle(pc):
        logging.info("[ZB] zuenden: im Fahrzeug nicht moeglich (erst aussteigen)")
        return
    a = _anchor
    # Wo wir JETZT stehen - der Absprungpunkt. Nach dem Teleport ist er nicht mehr zu haben, und
    # drei Skills aus Paket A brauchen ihn (Ruecksprung-Detonation, Zeitsprung, Nachbild).
    global _absprung
    _absprung = _vec(pawn.Location.X, pawn.Location.Y, pawn.Location.Z)
    # Sprengsatz (v0.94) explodiert am Spieler, Rueckenwind (v0.97) misst die Entfernung zum Anker -
    # beides geht nur hier, solange er noch am Absprungpunkt steht.
    try:
        mechanik_sprengsatz(pawn)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Sprengsatz: {ex}")
    try:
        mechanik_ruecksprung_detonation(pawn, _vec(a.x, a.y, a.z))
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Ruecksprung-Detonation: {ex}")
    # Phase 8 (v1.00): Nova am Absprungpunkt - blau beim Zuenden, violett bei der Schattenzuendung.
    try:
        effekt("Absprung", FX_SCHATTEN if _schatten_laeuft else FX_ABSPRUNG, _absprung, 1000.0)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Effekt Absprung: {ex}")
    logging.info("[ZB] zuenden: stelle Zustand her")

    # Position: Location direkt schreiben (SetLocation lehnt beim Pet immer ab, s. FL4K), Tempo auf null,
    # Physik 'fallend', damit die Schwerkraft den Spieler auf den Boden holt.
    def teleport() -> str:
        pawn.Velocity = unrealsdk.make_struct("Vector", X=0, Y=0, Z=0)
        pawn.Location = unrealsdk.make_struct("Vector", X=a.x, Y=a.y, Z=a.z)
        pawn.SetPhysics(2)  # PHYS_Falling
        nl = pawn.Location
        return f"jetzt ({nl.X:.0f},{nl.Y:.0f},{nl.Z:.0f}), Ziel ({a.x:.0f},{a.y:.0f},{a.z:.0f})"

    try_call("Teleport", teleport)

    # Blickrichtung: ClientSetRotation MIT bResetCamera=True setzt Controller und Pawn (Test 2026-09-19).
    # Ohne das Flag oder per direktem Schreiben von pc.Rotation dreht sich nur der Controller.
    rot = unrealsdk.make_struct("Rotator", Pitch=a.pitch, Yaw=a.yaw, Roll=a.roll)

    def set_rotation() -> str:
        pc.ClientSetRotation(rot, True)
        return f"pc.Yaw={pc.Rotation.Yaw} pawn.Yaw={pawn.Rotation.Yaw} (Ziel {a.yaw})"

    try_call("ClientSetRotation", set_rotation)

    # Leben und Schild: die Set-Funktionen des WillowPawn. Danach nachlesen, ob der Wert angenommen wurde.
    try_call("SetHealth", lambda: pawn.SetHealth(a.health))
    try_call("GetHealth danach", pawn.GetHealth)
    try_call("SetShieldStrength", lambda: pawn.SetShieldStrength(a.shield))
    try_call("GetShieldStrength danach", pawn.GetShieldStrength)

    # Magazin: nur wenn dieselbe Waffe noch aktiv ist (sonst wuerden wir das Magazin einer anderen Waffe setzen).
    weapon = pawn.Weapon
    if weapon is not None and weapon._path_name() == a.weapon:
        def set_mag() -> str:
            weapon.ReloadCnt = a.magazine
            return f"ReloadCnt {weapon.ReloadCnt} (Ziel {a.magazine})"
        try_call("Magazin", set_mag)
    else:
        logging.info(f"[ZB]   Magazin: andere Waffe aktiv ({weapon._path_name() if weapon else None}), uebersprungen")
    logging.info("[ZB] zuenden: fertig")


# ---------------------------------------------------------------- Phase 3, Schritt 5: die Bombe am Anker (D9)
#
# Am Anker liegt ein sichtbares Geraet, kein Doppelgaenger. Zer0s Decoy-Spawn feuert seit dem
# Skill_Stealth-Block (v0.35) ohnehin nicht mehr - Rauchtest v0.43 (2026-09-20): "zb spur" zeigte
# keine Zeile SPUR Behavior_SpawnFromPopulationSystem, der Nutzer sah kein Hologramm. Es bleibt
# also nur, das eigene Objekt zu setzen.
#
# Weg: Actor.Spawn(DynamicSMActor_Spawnable), dann StaticMeshComponent.SetStaticMesh(Mesh).
# DynamicSMActor_Spawnable ist die Mesh-Actor-Klasse, die UE3 fuers Spawnen zur Laufzeit vorsieht
# (Dump Engine.Default__DynamicSMActor_Spawnable: bStatic=False, bNoDelete=False, Physics=PHYS_None,
# eigener StaticMeshComponent0). StaticMeshActor geht nicht (bStatic), DynamicSMActor ist abstrakt.
# Spawn ist "native noexport" - ob das SDK es ueber ProcessEvent erreicht, entscheidet der Test.
#
# Der Verweis auf den Actor ist ein WeakPointer: Kartenwechsel und Engine koennen ihn jederzeit
# entsorgen, ein toter Zeiger waere ein Absturz (CLAUDE.md: keine Referenzen auf Welt-Objekte cachen).

# Mesh: Caesium-Ladung (flacher Kasten mit leuchtendem Auge), vom Nutzer aus fuenf Kandidaten
# gewaehlt (v0.45/46, Screenshots). Die Digistruct-"Cubes" aus 4.1 sind Wolken aus dutzenden
# Wuerfeln, kein Geraet. Die Uhren aus 4.1 sind kartengebunden und in Sanctuary gar nicht geladen.
BOMB_MESH = "Prop_CesiumCharge.Meshes.CesiumCharge"
BOMB_SCALE = 1.0  # Masse stehen nicht im Dump, und StaticMesh.Bounds reicht das SDK nicht durch (v0.44) - Augenmass
BOMB_ACTOR_CLASS = "DynamicSMActor_Spawnable"

_bombe: WeakPointer = WeakPointer()
_mesh_gerootet: set[str] = set()  # Pfade, deren Mesh schon RF_RootSet traegt


def _mesh_laden(pfad: str) -> UObject | None:
    """Mesh holen und beim ersten Fund rooten.

    Prop_Pickups & Co. gibt es nicht als .upk (v0.44) - load_package taete nichts. Das Mesh ist in
    Sanctuary geladen (v0.45), auf anderen Karten vielleicht nicht. Gerootet ueberlebt es den
    Kartenwechsel wie unsere Klassenkopien; ob das reicht, zeigt der Test auf einer zweiten Karte."""
    mesh = _find("StaticMesh", pfad)
    if mesh is not None and pfad not in _mesh_gerootet:
        _root(mesh)
        _mesh_gerootet.add(pfad)
        logging.info(f"[ZB] bombe: Mesh {pfad} gerootet")
    return mesh


def bombe_setzen(pawn: UObject, mesh_pfad: str = BOMB_MESH, scale: float = BOMB_SCALE,
                 wurf: bool = False) -> UObject | None:
    """Das Bombenobjekt am Fuss des Spielers spawnen. Jeder Schritt einzeln geloggt: was scheitert,
    muss im Log stehen (Falle 2 aus plan.md - eine Messung, die zwei Ursachen nicht trennt, ist keine).
    `wurf=True` (v1.19): in Augenhoehe spawnen, den Rest macht wurf_starten."""
    bombe_weg("neu gelegt")
    pc = local_pc()
    mesh = _mesh_laden(mesh_pfad)
    if mesh is None:
        logging.error(f"[ZB] bombe: Mesh {mesh_pfad} nicht im Speicher (Karte: {map_name(pc)})")
        return None
    try:
        cls = unrealsdk.find_class(BOMB_ACTOR_CLASS)
    except ValueError:
        logging.error(f"[ZB] bombe: Klasse {BOMB_ACTOR_CLASS} nicht gefunden")
        return None
    # mesh.Bounds gibt es fuer das SDK nicht ('no attribute Bounds', v0.44) - Groesse bleibt Augenmass.

    # pawn.Location ist die Koerpermitte; die Bombe soll am Boden liegen.
    loc = pawn.Location
    hoehe = try_call("CollisionHeight", lambda: float(pawn.CylinderComponent.CollisionHeight)) or 0.0
    spawn_loc = unrealsdk.make_struct("Vector", X=loc.X, Y=loc.Y, Z=loc.Z - hoehe)
    if wurf:
        spawn_loc = _augen(pawn)
    spawn_rot = unrealsdk.make_struct("Rotator", Pitch=0, Yaw=pawn.Rotation.Yaw, Roll=0)

    # bNoCollisionFail: der Spieler steht genau dort - ohne das Flag lehnt Spawn den Platz ab.
    actor = try_call(
        f"Spawn {BOMB_ACTOR_CLASS}",
        lambda: pc.Spawn(SpawnClass=cls, SpawnLocation=spawn_loc, SpawnRotation=spawn_rot, bNoCollisionFail=True),
    )
    if actor is None:
        return None
    _bombe.replace(actor)
    try_call("SetStaticMesh", lambda: actor.StaticMeshComponent.SetStaticMesh(mesh, True))
    # Keine Kollision: beim Zuenden landet der Spieler genau auf der Bombe. SetCollision(F,F,F) lief
    # fehlerfrei und wirkte nicht (v0.44-v0.56, Nutzer stiess an); SetCollisionType(NoCollision)
    # setzt Actor- UND Component-Flag (v0.57 gemessen: bCollideActors/CollideActors False, keine Wand).
    try_call("SetCollisionType(NoCollision)", lambda: actor.SetCollisionType(COLLIDE_NO_COLLISION))
    if scale != 1.0:
        try_call(f"SetDrawScale {scale}", lambda: actor.SetDrawScale(scale))
    try_call("Bombe steht", lambda: f"{actor._path_name()} bei ({actor.Location.X:.0f},{actor.Location.Y:.0f},{actor.Location.Z:.0f})"
             f" Mesh={actor.StaticMeshComponent.StaticMesh} bHidden={actor.bHidden}")
    return actor


def bombe_weg(grund: str, art: int = 1) -> None:
    global _wurf
    if _wurf is not None:
        # Gezuendet oder verpufft, bevor sie lag: der Anker bleibt der Wurfpunkt (v1.19).
        logging.info(f"[ZB] Wurf abgebrochen ({grund}) nach {_wurf.zeit:.2f} s - Anker bleibt am Wurfpunkt")
        _wurf = None
        _wurf_proj_weg()
    actor = _bombe()
    _bombe.replace(None)
    if actor is None:
        return
    # Destroy() greift NICHT - wie beim FL4K-Pet. Befund v0.57 (zb bombe diag): alle bisherigen Bomben
    # liegen versteckt im Level (bHidden=True, bDeleteMe=False), und weil SetCollision(F,F,F) nichts
    # bewirkt hatte, war jede davon eine unsichtbare Wand (0b). Darum jetzt immer: verstecken UND die
    # Kollision per SetCollisionType abschalten (gemessen). Die Leiche bleibt, stoert aber nicht mehr.
    # Kandidaten zum echten Entfernen (zb bombe weg N), ungetestet:
    #   2 = ShutDown() - Actor-Funktion, schaltet Sichtbarkeit, Kollision und Tick ab (Name per
    #       "zb funcs Actor ShutDown" belegt, v0.57)
    #   3 = zusaetzlich 10000 Einheiten unter die Karte schieben
    try:
        actor.SetHidden(True)
        try_call("SetCollisionType(NoCollision)", lambda: actor.SetCollisionType(COLLIDE_NO_COLLISION))
        if art == 2:
            try_call("ShutDown", actor.ShutDown)
        elif art == 3:
            loc = actor.Location
            actor.Location = unrealsdk.make_struct("Vector", X=loc.X, Y=loc.Y, Z=loc.Z - 10000)
            try_call("Location danach", lambda: f"({actor.Location.X:.0f},{actor.Location.Y:.0f},{actor.Location.Z:.0f})")
        else:
            actor.Destroy()
        logging.info(f"[ZB] bombe weg ({grund}, Art {art}): bDeleteMe={actor.bDeleteMe} bHidden={actor.bHidden}"
                     f" bCollideActors={actor.bCollideActors}")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] bombe weg ({grund}): FEHLER {ex}")


# ECollisionType (Engine.Actor): 0 CustomDefault, 1 NoCollision, 2 BlockAll, 3 BlockWeapons, 4 TouchAll ...
COLLIDE_NO_COLLISION = 1


def bombe_kollision_aus(actor: UObject, art: int) -> None:
    """Kollision der liegenden Bombe abschalten - drei Kandidaten (0b, plan.md), jeder Schritt geloggt.

    Befund v0.56: actor.SetCollision(False, False, False) laeuft ohne Fehler, der Spieler stoesst
    trotzdem an. Der Dump (Default__DynamicSMActor_Spawnable) sagt CollisionComponent=StaticMeshComponent0,
    CollisionType=COLLIDE_CustomDefault - die Flags, die zaehlen, sitzen am Component.
      1 = actor.SetCollisionType(COLLIDE_NoCollision) - **gemessen v0.57:** actor.bCollideActors und
          comp.CollideActors werden False (bBlockActors bleibt True), der Nutzer laeuft durch.
          Seitdem fest in bombe_setzen und bombe_weg. 2 und 3 blieben ungetestet.
      2 = Component-Funktionen: SetActorCollision(False, False), SetTraceBlocking(False, False),
          SetBlockRigidBody(False) - Namen per "zb funcs PrimitiveComponent" belegt (v0.57)
      3 = Flags direkt schreiben, am Actor und am Component (ohne Neuanmeldung im Octree -
          greift vielleicht erst nach einer Bewegung)"""
    comp = actor.StaticMeshComponent
    if art == 1:
        try_call("SetCollisionType(NoCollision)", lambda: actor.SetCollisionType(COLLIDE_NO_COLLISION))
    elif art == 2:
        try_call("SetActorCollision(F,F)", lambda: comp.SetActorCollision(False, False))
        try_call("SetTraceBlocking(F,F)", lambda: comp.SetTraceBlocking(False, False))
        try_call("SetBlockRigidBody(F)", lambda: comp.SetBlockRigidBody(False))
    else:
        for name in ("bCollideActors", "bBlockActors", "bCollideWorld"):
            try_call(f"actor.{name}=False", lambda n=name: setattr(actor, n, False))
        for name in ("CollideActors", "BlockActors", "BlockNonZeroExtent", "BlockZeroExtent", "BlockRigidBody"):
            try_call(f"comp.{name}=False", lambda n=name: setattr(comp, n, False))
    bombe_diag()


def bombe_diag() -> None:
    """zb bombe diag - Kollisionsflags der Bombe ins Log, dazu alle DynamicSMActor_Spawnable im Level:
    liegt nach 'weg' noch einer mit unserem Mesh herum, ist das die unsichtbare Wand."""
    actor = _bombe()
    if actor is None:
        logging.info("[ZB] diag: keine Bombe gemerkt")
    else:
        for name in ("bHidden", "bDeleteMe", "bCollideActors", "bBlockActors", "bCollideWorld", "CollisionType", "CollisionComponent"):
            try_call(f"actor.{name}", lambda n=name: getattr(actor, n))
        comp = actor.StaticMeshComponent
        for name in ("HiddenGame", "CollideActors", "BlockActors", "BlockNonZeroExtent", "BlockZeroExtent", "BlockRigidBody"):
            try_call(f"comp.{name}", lambda n=name: getattr(comp, n))
    reste = []
    for o in unrealsdk.find_all(BOMB_ACTOR_CLASS, exact=True):
        pfad = o._path_name()
        if "Default__" in pfad:
            continue
        try:
            mesh = str(o.StaticMeshComponent.StaticMesh)
            reste.append(f"{pfad} Mesh={mesh.rsplit('.', 1)[-1].rstrip(chr(39))} bHidden={o.bHidden} bDeleteMe={o.bDeleteMe}")
        except Exception as ex:  # noqa: BLE001
            reste.append(f"{pfad} <{ex}>")
    logging.info(f"[ZB] diag: {len(reste)} {BOMB_ACTOR_CLASS} im Level" + ("".join("\n    " + r for r in reste) if reste else ""))


# ---------------------------------------------------------------- Die Bombe werfen (v1.19, Granaten-Projektil seit v1.27)
#
# Nutzerwunsch (2026-09-21, plan.md), Anker entschieden 2026-09-26: man kehrt dorthin zurueck, wo
# die Bombe LANDET. Leben, Schild, Magazin und Blickrichtung bleiben die vom Moment des Wurfs.
#
# Sackgassen (gemessen, CHANGELOG v1.19-v1.26):
#   - Actor.Trace / Actor.FastTrace laufen ueber das SDK nicht: Trace gibt nur die mitgegebenen
#     Platzhalter zurueck, FastTrace immer False. Das Modul kann Weltgeometrie nicht selbst abtasten.
#   - SetPhysics(PHYS_Falling) am DynamicSMActor: Physics bleibt 0 (v1.24).
#   - Ein NACKTES WillowProjectile (pc.Spawn, ohne Definition): fliegt, Acceleration wirkt als
#     Schwerkraft, aber es beruehrt die Welt nie - weder mit noch ohne bCollideActors (v1.25/v1.26,
#     bis 27 m unter die Karte). Ihm fehlt die Kollisionsform (CylinderComponent=None im Dump).
#
# Weg seit v1.31 (Nutzeridee: wie Axtons Geschuetz, das ein WillowProjectile MIT ProjectileDefinition
# ist): die normale Granate GD_GrenadeMods.Projectiles.Grenade_DefaultFrag, gespawnt ueber einen
# eigenen Behavior_SpawnProjectile (v1.28). Gemessen v1.30: so bekommt das Projektil Mesh + Zylinder
# aus der BodyComposition und LANDET (1,73 s, 12,8 m). Eine Kopie der Definition verliert die
# BodyComposition (0 Attachments) und faellt durch; InitializeFromDefinition an einem pc.Spawn-
# Projektil haengt sie ebenfalls nicht an (v1.27). Zuender und Rauchspur nimmt _wurf_projektil der
# Original-Definition nur fuer den Spawn-Aufruf weg.
# Die Engine wirft, prallt ab und laesst sie liegen; das Granaten-Mesh wird versteckt, unsere Bombe
# folgt dem Projektil jeden Frame (Location + ForceUpdateComponents, v1.21).
# Landung (v1.32) = die POSITION steht WURF_STILL_S lang still. Das Tempo taugt nicht: ohne ihr BPD
# bleibt die Granate beim Aufprall stehen, ihr Velocity waechst aber mit der Schwerkraft weiter (v1.31
# gemessen, bis -7000) - daher auch das Dauer-Aufprallgeraeusch. Beim ERSTEN Stillstand wird sie
# 20 uu gegen die Flugrichtung zurueckgesetzt und faellt senkrecht (Wand -> zu Boden; Boden -> fast
# derselbe Punkt), erst der zweite zaehlt. Danach Physik und Kollision aus (Geraeusch weg).

WURF_VORLAGE = "GD_GrenadeMods.Projectiles.Grenade_DefaultFrag"
WURF_TEMPO_UU = 1100.0        # Abwurftempo in Blickrichtung (uu/s)
WURF_AUFTRIEB_UU = 250.0      # zusaetzlich nach oben, damit ein flacher Blick einen Bogen gibt
WURF_MAX_S = 6.0              # liegt sie dann noch nicht, Notlandung am Wurfpunkt
WURF_DREH_JE_S = 65536 * 2    # zwei Ueberschlaege je Sekunde
WURF_STILL_UU = 1.0           # weniger Bewegung je Frame = steht
WURF_STILL_S = 0.1            # so lange muss sie stehen
WURF_NACHFALL_UU = 20.0       # beim ersten Stillstand so weit gegen die Flugrichtung zurueck, dann fallen
WURF_NACHFALL_SCHONZEIT_S = 0.3  # so lange nach dem Zuruecksetzen zaehlt kein Stillstand (Start aus Tempo 0)
WURF_ANKER_LUFT_UU = 5.0      # Anker so hoch ueber dem Boden, dass der Spieler nicht einsinkt
WURF_ANKER_ZURUECK_UU = 40.0  # Anker so weit zum Werfer hin - weg von einer Wand, an der sie liegt
WURF_LOG_TAKT_S = 0.25
WURF_START_VOR_UU = 80.0      # Projektil so weit vor den Augen spawnen - ausserhalb des Spielerkoerpers
PHYS_NONE = 0


@dataclass
class Wurf:
    yaw: int
    wx: float                 # Wurfpunkt (Spieler), fuer den Rueckzug des Ankers
    wy: float
    x: float                  # Ort im letzten Frame
    y: float
    z: float
    zeit: float = 0.0
    log_akku: float = 0.0
    stand: float = 0.0        # Sekunden ohne Bewegung
    nachgefallen: bool = False
    nachfall_zeit: float = 0.0
    pitch: int = 0


_wurf: Wurf | None = None
_wurf_proj: WeakPointer = WeakPointer()
_wurf_bewegen_weg = ""      # "SetLocation" | "Location+ForceUpdate" - einmal ermittelt, dann geloggt


def _augen(pawn: UObject) -> Any:
    loc = pawn.Location
    try:
        eye = float(pawn.EyeHeight)
    except Exception:  # noqa: BLE001
        eye = 60.0
    return _vec(loc.X, loc.Y, loc.Z + eye)


def _bombe_bewegen(actor: UObject, x: float, y: float, z: float, pitch: int, yaw: int) -> None:
    global _wurf_bewegen_weg
    ziel = _vec(x, y, z)
    if _wurf_bewegen_weg != "Location+ForceUpdate":
        ok = actor.SetLocation(ziel)
        if not _wurf_bewegen_weg:
            _wurf_bewegen_weg = "SetLocation" if ok else "Location+ForceUpdate"
            logging.info(f"[ZB] Wurf: SetLocation -> {ok}, Weg ab jetzt: {_wurf_bewegen_weg}")
    if _wurf_bewegen_weg == "Location+ForceUpdate":
        actor.Location = ziel
        actor.ForceUpdateComponents()
    _bombe_drehen(actor, pitch, yaw)


def _bombe_drehen(actor: UObject, pitch: int, yaw: int) -> None:
    actor.SetRotation(unrealsdk.make_struct("Rotator", Pitch=pitch % 65536, Yaw=yaw % 65536, Roll=0))


def _wurf_definition() -> UObject | None:
    """Die ORIGINAL-Granate (v1.31). Eine Kopie taugt nicht: construct_object mit Vorlage verliert die
    BodyComposition (v1.30 gemessen: Original 2 Attachments - Mesh + Zylinder -, Kopie 0), und ohne
    Zylinder beruehrt das Projektil die Welt nie. Den Zuender nimmt _wurf_projektil ihr nur fuer den
    Spawn-Aufruf weg."""
    d = _find("ProjectileDefinition", WURF_VORLAGE)
    if d is None:
        logging.error(f"[ZB] Wurf: {WURF_VORLAGE} nicht im Speicher")
    return d


WURF_BEHAVIOR = "ZB_Wurf_Spawn"


def _wurf_behavior() -> UObject | None:
    """Eigener Behavior_SpawnProjectile (wie ZB_Sprengsatz_Explode: einmal gebaut, gerootet)."""
    paket = unrealsdk.find_object("Package", "Transient")
    b = _find("Behavior_SpawnProjectile", f"Transient.{WURF_BEHAVIOR}")
    if b is not None:
        return b
    try:
        b = unrealsdk.construct_object("Behavior_SpawnProjectile", paket, WURF_BEHAVIOR)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Wurf: Behavior_SpawnProjectile nicht gebaut: {ex}")
        return None
    _root(b)
    logging.info(f"[ZB] erzeugt Behavior_SpawnProjectile {b._path_name()}")
    return b


def _wurf_projektile_der_welt(def_pfad: str) -> list[UObject]:
    """Alle Welt-Projektile mit unserer Definition - nur Eigenschaften (CLAUDE.md, v0.74)."""
    treffer = []
    for p in unrealsdk.find_all("WillowProjectile", exact=True):
        pfad = p._path_name()
        if "TheWorld" not in pfad or "Default__" in pfad:
            continue
        try:
            if p.Definition is not None and p.Definition._path_name() == def_pfad and not bool(p.bDeleteMe):
                treffer.append(p)
        except Exception:  # noqa: BLE001
            continue
    return treffer


def _wurf_projektil(pc: UObject, pawn: UObject, x: float, y: float, z: float,
                    vx: float, vy: float, vz: float, rot: Any) -> UObject | None:
    """Projektil mit der Granaten-Kopie ueber den Spawn-Weg des Spiels (v1.28).

    v1.27: pc.Spawn + InitializeFromDefinition gab Physics 2 und die Definition, aber
    CollisionComponent None - die BodyComposition (Zylinder) haengt erst der volle Spawn-Weg an.
    Den geht Behavior_SpawnProjectile, derselbe Baustein, mit dem Granaten und Geschuetze fliegen."""
    definition = _wurf_definition()
    b = _wurf_behavior()
    if definition is None or b is None:
        return None
    def_pfad = definition._path_name()
    vorher = {p._path_name() for p in _wurf_projektile_der_welt(def_pfad)}
    b.ProjectileDefinition = definition
    b.bSpawnFromContextViewLocation = True   # aus den Augen, in Blickrichtung
    b.bSetOwnerFromOwnerContext = False
    b.NumProjectilesFormula.BaseValueConstant = 1.0
    b.NumProjectilesFormula.BaseValueAttribute = None
    # v1.31: Zuender (BPD) und Rauchspur nur fuer diesen einen Aufruf weg, danach sofort zurueck -
    # echte Granaten des Spielers behalten beides. Ob das Projektil den Zuender beim Spawn bindet (dann
    # explodiert es nicht) oder spaeter nachschlaegt, zeigt _wurf_landen (bDeleteMe nach der Landung).
    bpd, rauch = definition.BehaviorProviderDefinition, definition.InFlightEffects
    try:
        definition.BehaviorProviderDefinition = None
        definition.InFlightEffects = None
        b.ApplyBehaviorToContext(
            ContextObject=pawn, KernelInfo=unrealsdk.make_struct("BehaviorKernelInfo"),
            SelfObject=pawn, MyInstigatorObject=pawn, OtherEventParticipantObject=None,
            EventData=unrealsdk.make_struct("BehaviorParameters"),
        )
    finally:
        definition.BehaviorProviderDefinition = bpd
        definition.InFlightEffects = rauch
    neu = [p for p in _wurf_projektile_der_welt(def_pfad) if p._path_name() not in vorher]
    if not neu:
        logging.error(f"[ZB] Wurf: Behavior_SpawnProjectile lief, aber kein neues Projektil mit {definition.Name}")
        return None
    proj = neu[-1]
    logging.info(f"[ZB] Wurf: {proj.Name} vom Spiel gespawnt, eigenes Tempo war"
                 f" ({proj.Velocity.X:.0f},{proj.Velocity.Y:.0f},{proj.Velocity.Z:.0f}),"
                 f" CollisionComponent {proj.CollisionComponent}")
    proj.Velocity = _vec(vx, vy, vz)
    try_call("Granaten-Mesh verstecken", lambda: proj.SetHidden(True))
    _wurf_proj.replace(proj)
    return proj


def _proj_zustand(proj: UObject) -> str:
    v, o = proj.Velocity, proj.Location
    return (f"Ort ({o.X:.0f},{o.Y:.0f},{o.Z:.0f}), Tempo ({v.X:.0f},{v.Y:.0f},{v.Z:.0f}),"
            f" Physics {int(proj.Physics)}, bDeleteMe {proj.bDeleteMe}")


_wurf_rest: WeakPointer = WeakPointer()   # das ruhende Projektil, 4 s beobachtet (v1.31: explodiert es?)
_wurf_rest_s = 0.0
WURF_REST_BEOBACHTEN_S = 4.0


def _wurf_proj_weg() -> None:
    """Projektil ruhigstellen - Destroy greift nicht (spikes.md), LifeSpan raeumt es ab."""
    global _wurf_rest_s
    proj = _wurf_proj()
    _wurf_proj.replace(None)
    if proj is None:
        return
    # v1.32: sonst drueckt die Schwerkraft sie jeden Frame weiter in den Boden - Dauer-Aufprallgeraeusch.
    for label, fn in (("Tempo 0", lambda: setattr(proj, "Velocity", _vec(0.0, 0.0, 0.0))),
                      ("verstecken", lambda: proj.SetHidden(True)),
                      ("SetPhysics(None)", lambda: proj.SetPhysics(PHYS_NONE)),
                      ("Kollision aus", lambda: (setattr(proj, "bCollideWorld", False), setattr(proj, "bCollideActors", False)))):
        try:
            fn()
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] Wurf: Projektil {label}: {ex}")
    try:
        logging.info(f"[ZB] Wurf: Projektil abgeschaltet: Physics {int(proj.Physics)}, bCollideWorld {proj.bCollideWorld}")
    except Exception:  # noqa: BLE001
        pass
    _wurf_rest.replace(proj)
    _wurf_rest_s = 0.0


def _wurf_rest_tick(dt: float) -> None:
    """Nach der Landung: verschwindet das Projektil (Zuender doch gebunden -> Explosion)?"""
    global _wurf_rest_s
    proj = _wurf_rest()
    if proj is None:
        return
    _wurf_rest_s += dt
    try:
        weg = bool(proj.bDeleteMe)
    except Exception:  # noqa: BLE001
        weg = True
    if weg:
        logging.info(f"[ZB] Wurf: ruhendes Projektil nach {_wurf_rest_s:.2f} s VERSCHWUNDEN (explodiert?)")
        _wurf_rest.replace(None)
    elif _wurf_rest_s >= WURF_REST_BEOBACHTEN_S:
        logging.info(f"[ZB] Wurf: ruhendes Projektil nach {WURF_REST_BEOBACHTEN_S:.0f} s noch da - kein Zuender")
        _wurf_rest.replace(None)


def wurf_starten(pc: UObject, pawn: UObject, bombe: UObject) -> bool:
    """Projektil in Blickrichtung mit WURF_TEMPO_UU, dazu WURF_AUFTRIEB_UU nach oben."""
    global _wurf
    try:
        rot = pc.Rotation
        p = (rot.Pitch % 65536) / 65536.0 * 2 * math.pi
        if p > math.pi:
            p -= 2 * math.pi   # Blick nach unten = negativer Pitch
        y = (rot.Yaw % 65536) / 65536.0 * 2 * math.pi
        vx = WURF_TEMPO_UU * math.cos(p) * math.cos(y)
        vy = WURF_TEMPO_UU * math.cos(p) * math.sin(y)
        vz = WURF_TEMPO_UU * math.sin(p) + WURF_AUFTRIEB_UU
        # Start vor dem Koerper (v1.26): das Projektil soll den Werfer nicht beruehren.
        auge = _augen(pawn)
        start = _vec(auge.X + math.cos(y) * WURF_START_VOR_UU, auge.Y + math.sin(y) * WURF_START_VOR_UU, auge.Z)
        proj = _wurf_projektil(pc, pawn, start.X, start.Y, start.Z, vx, vy, vz,
                               unrealsdk.make_struct("Rotator", Pitch=rot.Pitch, Yaw=rot.Yaw, Roll=0))
        if proj is None:
            raise RuntimeError("kein Projektil")
        loc = pawn.Location
        _wurf = Wurf(yaw=int(rot.Yaw), wx=float(loc.X), wy=float(loc.Y),
                     x=float(start.X), y=float(start.Y), z=float(start.Z))
        logging.info(f"[ZB] Wurf: ab ({start.X:.0f},{start.Y:.0f},{start.Z:.0f}), Pitch {math.degrees(p):.0f} Grad,"
                     f" Tempo ({vx:.0f},{vy:.0f},{vz:.0f}); {proj.Name} gelesen: {_proj_zustand(proj)},"
                     f" Definition {proj.Definition}, CollisionComponent {proj.CollisionComponent},"
                     f" bCollideWorld {proj.bCollideWorld}")
        return True
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Wurf: Start gescheitert ({ex}) - Bombe bleibt beim Spieler")
        _wurf = None
        _wurf_notlandung(pc)
        return False


def _wurf_tick(pc: UObject, dt: float) -> None:
    """Laeuft im PlayerTick: die Bombe folgt dem Projektil, bis es liegt."""
    global _wurf
    w = _wurf
    if w is None:
        return
    actor = _bombe()
    pawn = pc.Pawn
    if actor is None or pawn is None:
        logging.info("[ZB] Wurf: Bombe oder Spieler weg - Flug beendet")
        _wurf = None
        _wurf_proj_weg()
        return
    w.zeit += dt
    w.log_akku += dt
    proj = _wurf_proj()
    if proj is None or bool(proj.bDeleteMe):
        # Weg (zerstoert/abgelaufen): dort liegen lassen, wo es zuletzt war.
        logging.info(f"[ZB] Wurf {w.zeit:.2f} s: Projektil weg - Bombe bleibt bei ({w.x:.0f},{w.y:.0f},{w.z:.0f})")
        _wurf_landen(pc, pawn, actor, w.x, w.y, w.z, "Projektil weg")
        return
    o, v = proj.Location, proj.Velocity
    x, y, z = float(o.X), float(o.Y), float(o.Z)
    phys = int(proj.Physics)
    if w.log_akku >= WURF_LOG_TAKT_S:
        w.log_akku = 0.0
        logging.info(f"[ZB] Wurf {w.zeit:.2f} s: {_proj_zustand(proj)}")
    bewegt = math.sqrt((x - w.x) ** 2 + (y - w.y) ** 2 + (z - w.z) ** 2)
    w.x, w.y, w.z = x, y, z
    # v1.33: nach dem Nachfallen startet sie mit Tempo 0 und faellt die ersten Frames < 1 uu weit - ohne
    # Schonzeit galt das als Stillstand (v1.32: 0,1 s nach dem Zuruecksetzen "gelandet", 1 uu tiefer).
    schonzeit = w.nachgefallen and w.zeit - w.nachfall_zeit < WURF_NACHFALL_SCHONZEIT_S
    w.stand = w.stand + dt if bewegt < WURF_STILL_UU and not schonzeit else 0.0
    if w.zeit > 0.1 and (phys == PHYS_NONE or w.stand >= WURF_STILL_S):
        if not w.nachgefallen:
            # Erster Stillstand: Wand oder Boden? Ein Stueck zurueck und senkrecht fallen lassen.
            hx, hy = float(v.X), float(v.Y)
            laenge = math.hypot(hx, hy) or 1.0
            nx, ny, nz = x - hx / laenge * WURF_NACHFALL_UU, y - hy / laenge * WURF_NACHFALL_UU, z + 5.0
            proj.Location = _vec(nx, ny, nz)
            proj.Velocity = _vec(0.0, 0.0, 0.0)
            w.nachgefallen, w.stand, w.nachfall_zeit = True, 0.0, w.zeit
            w.x, w.y, w.z = nx, ny, nz
            logging.info(f"[ZB] Wurf {w.zeit:.2f} s: erster Halt bei ({x:.0f},{y:.0f},{z:.0f}) - zurueck nach"
                         f" ({nx:.0f},{ny:.0f},{nz:.0f}), faellt senkrecht; gelesen {_proj_zustand(proj)}")
            return
        try:
            z -= float(proj.CylinderComponent.CollisionHeight)   # Mitte des Zylinders -> Boden
        except Exception:  # noqa: BLE001
            pass
        _wurf_landen(pc, pawn, actor, x, y, z, f"Physics {phys}, steht seit {w.stand:.2f} s")
        return
    w.pitch += int(WURF_DREH_JE_S * dt)
    _bombe_bewegen(actor, x, y, z, w.pitch, w.yaw)
    if w.zeit >= WURF_MAX_S:
        logging.info(f"[ZB] Wurf: nach {WURF_MAX_S:.0f} s kein Halt ({_proj_zustand(proj)})")
        _wurf = None
        _wurf_notlandung(pc)


# zb granate (v1.29): Was gibt ECHTEN Granaten Halt? v1.25-v1.28 fielen alle eigenen Projektile durch,
# auch das vom Spiel gespawnte (Behavior_SpawnProjectile) - CollisionComponent war jedes Mal None.
# Der Spaeher loggt jedes neue Welt-Projektil zweimal (beim ersten Sichten und 0,3 s spaeter), nur
# Eigenschaften, damit man eine geworfene Granate mit unserem ZB_Wurf vergleichen kann.
_spaeher_an = False
_spaeher_akku = 0.0
_spaeher_gesehen: dict[str, float] = {}   # Pfad -> Sekunden seit dem ersten Sichten (-1 = fertig)


def granate_spaeher(an: bool) -> None:
    global _spaeher_an
    _spaeher_an = an
    _spaeher_gesehen.clear()
    logging.info(f"[ZB] Granaten-Spaeher {'an - jetzt eine Granate werfen' if an else 'aus'}")


def _spaeher_felder(p: UObject) -> str:
    def lies(fn: Any) -> str:
        try:
            return str(fn())
        except Exception as ex:  # noqa: BLE001
            return f"<{ex}>"

    teile = [f"Definition {lies(lambda: p.Definition)}", f"Physics {lies(lambda: int(p.Physics))}",
             f"bCollideWorld {lies(lambda: p.bCollideWorld)}", f"bCollideActors {lies(lambda: p.bCollideActors)}",
             f"bBlockActors {lies(lambda: p.bBlockActors)}", f"CollisionType {lies(lambda: p.CollisionType)}",
             f"bHidden {lies(lambda: p.bHidden)}", f"bBounce {lies(lambda: p.bBounce)}",
             f"CollisionComponent {lies(lambda: p.CollisionComponent)}", f"CylinderComponent {lies(lambda: p.CylinderComponent)}"]
    try:
        cyl = p.CylinderComponent
        if cyl is not None:
            teile.append(f"Zylinder r={cyl.CollisionRadius:.1f} h={cyl.CollisionHeight:.1f} CollideActors {cyl.CollideActors}"
                         f" BlockActors {cyl.BlockActors} BlockZero {cyl.BlockZeroExtent} BlockNonZero {cyl.BlockNonZeroExtent}")
    except Exception as ex:  # noqa: BLE001
        teile.append(f"Zylinder <{ex}>")
    try:
        teile.append("Components [" + ", ".join(f"{c.Class.Name}:{c.Name}" for c in p.Components if c is not None) + "]")
    except Exception as ex:  # noqa: BLE001
        teile.append(f"Components <{ex}>")
    try:
        v, o = p.Velocity, p.Location
        teile.append(f"Ort ({o.X:.0f},{o.Y:.0f},{o.Z:.0f}) Tempo ({v.X:.0f},{v.Y:.0f},{v.Z:.0f})")
    except Exception as ex:  # noqa: BLE001
        teile.append(f"Ort <{ex}>")
    return " | ".join(teile)


def _spaeher_tick(dt: float) -> None:
    global _spaeher_akku
    if not _spaeher_an:
        return
    for pfad in list(_spaeher_gesehen):
        if _spaeher_gesehen[pfad] >= 0:
            _spaeher_gesehen[pfad] += dt
    _spaeher_akku += dt
    if _spaeher_akku < 0.05:
        return
    _spaeher_akku = 0.0
    for p in unrealsdk.find_all("WillowProjectile", exact=True):
        pfad = p._path_name()
        if "TheWorld" not in pfad or "Default__" in pfad:
            continue
        try:
            if bool(p.bDeleteMe):
                continue
        except Exception:  # noqa: BLE001
            continue
        alter = _spaeher_gesehen.get(pfad)
        if alter is None:
            _spaeher_gesehen[pfad] = 0.0
            logging.info(f"[ZB] Spaeher NEU {p.Name}: {_spaeher_felder(p)}")
        elif alter >= 0.3:
            _spaeher_gesehen[pfad] = -1.0
            logging.info(f"[ZB] Spaeher +0,3s {p.Name}: {_spaeher_felder(p)}")


def trace_diag() -> None:
    """zb trace - v1.22: senkrecht 50 m nach unten, fuenf Varianten, alles ins Log.

    Ergebnis (v1.22/v1.23, gemessen): KEINE Variante taugt. Trace liefert Actor None und die
    Platzhalter (0,0,0); FastTrace liefert immer False, auch fuer einen 2-cm-Schritt in freier Luft.
    Bleibt als Werkzeug stehen, falls ein anderer Aufrufweg auftaucht."""
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] trace: kein Spieler-Pawn")
        return
    start = _augen(pawn)
    ende = _vec(start.X, start.Y, start.Z - 5000.0)
    logging.info(f"[ZB] trace: von ({start.X:.0f},{start.Y:.0f},{start.Z:.0f}) nach unten; Fuesse bei Z"
                 f" {pawn.Location.Z - float(pawn.CylinderComponent.CollisionHeight):.0f}")

    def fmt(v: Any) -> str:
        try:
            return f"({v.X:.0f},{v.Y:.0f},{v.Z:.2f})"
        except Exception:  # noqa: BLE001
            return repr(v)

    def probe(label: str, fn: Any) -> None:
        try:
            r = fn()
            if isinstance(r, tuple):
                teile = [fmt(t) if hasattr(t, "X") else (t._path_name() if hasattr(t, "_path_name") else repr(t)) for t in r[:3]]
                logging.info(f"[ZB] trace {label}: Actor={teile[0]} HitLocation={teile[1]} HitNormal={teile[2]}")
            else:
                logging.info(f"[ZB] trace {label}: {r!r}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] trace {label}: FEHLER {ex}")

    null = lambda: _vec(0, 0, 0)  # noqa: E731
    probe("1 pawn, nur Welt", lambda: pawn.Trace(HitLocation=null(), HitNormal=null(), TraceEnd=ende, TraceStart=start, bTraceActors=False))
    probe("2 pawn, mit Actors", lambda: pawn.Trace(HitLocation=null(), HitNormal=null(), TraceEnd=ende, TraceStart=start, bTraceActors=True))
    probe("3 pc, mit Actors", lambda: pc.Trace(HitLocation=null(), HitNormal=null(), TraceEnd=ende, TraceStart=start, bTraceActors=True))
    probe("4 pawn, positionell", lambda: pawn.Trace(null(), null(), ende, start, True))
    probe("5 FastTrace (True = frei)", lambda: pawn.FastTrace(TraceEnd=ende, TraceStart=start))


def _wurf_notlandung(pc: UObject) -> None:
    """Flug gescheitert oder ohne Halt: Bombe an die Fuesse des Wurfpunkts, Anker bleibt dort
    (v1.19/v1.20 hing sie zweimal in Augenhoehe)."""
    _wurf_proj_weg()
    try:
        actor, a, pawn = _bombe(), _anchor, pc.Pawn
        if actor is None or a is None or pawn is None:
            return
        hoehe = float(pawn.CylinderComponent.CollisionHeight)
        actor.Location = _vec(a.x, a.y, a.z - hoehe)
        actor.ForceUpdateComponents()
        _bombe_drehen(actor, 0, a.yaw)
        logging.info(f"[ZB] Wurf: Notlandung am Wurfpunkt, Bombe jetzt bei ({actor.Location.X:.0f},{actor.Location.Y:.0f},{actor.Location.Z:.0f})")
        effekt("Legen", FX_LEGEN, _vec(a.x, a.y, a.z), 400.0)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Wurf: Notlandung gescheitert: {ex}")


def _wurf_landen(pc: UObject, pawn: UObject, actor: UObject, x: float, y: float, z: float, grund: str) -> None:
    """Die Bombe liegt: flach drehen und den Anker dorthin setzen, wo der Spieler Platz hat."""
    global _wurf
    w = _wurf
    _wurf = None
    _wurf_proj_weg()
    _bombe_bewegen(actor, x, y, z, 0, w.yaw if w else 0)
    a = _anchor
    if a is None:   # Zuenden/Verpuffen im Flug raeumt _wurf schon in bombe_weg ab
        logging.info(f"[ZB] Wurf: gelandet ({grund}), aber kein Anker mehr")
        return
    hoehe = float(pawn.CylinderComponent.CollisionHeight)
    # Ohne Trace laesst sich keine Wand ertasten. Liegt die Bombe an einer, dann meist auf der Seite
    # zum Werfer hin - also den Anker ein Stueck zum Wurfpunkt zurueckziehen.
    ax, ay = x, y
    if w is not None:
        dx, dy = w.wx - x, w.wy - y
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            zurueck = min(WURF_ANKER_ZURUECK_UU, dist)
            ax, ay = x + dx / dist * zurueck, y + dy / dist * zurueck
    az = z + hoehe + WURF_ANKER_LUFT_UU
    wx, wy = a.x, a.y
    a.x, a.y, a.z = ax, ay, az
    zeit = w.zeit if w else 0.0
    logging.info(f"[ZB] Wurf: gelandet ({grund}) nach {zeit:.2f} s bei ({x:.0f},{y:.0f},{z:.0f}),"
                 f" {math.hypot(ax - wx, ay - wy) / UU_JE_METER:.1f} m vom Wurfpunkt; Anker ({ax:.0f},{ay:.0f},{az:.0f})")
    effekt("Legen", FX_LEGEN, _vec(x, y, z), 400.0)
    try:
        mechanik_zeitkapsel_gelegt(_vec(ax, ay, az))   # Hologramm erst am Landepunkt
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Zeitkapsel nach Landung: {ex}")


def meshes(flt: str = "", limit: int = 400) -> None:
    """zb meshes [FILTER] - alle geladenen StaticMeshes ins Log, deren Pfad FILTER enthaelt.

    Warum: die Kandidaten aus docs/skills.md 4.1 liegen in Paketen (Prop_Pickups, Prop_PocketWatch, ...),
    die es nicht als .upk gibt - sie stecken in Levelpaketen. load_package taete still nichts (v0.44).
    Brauchbar fuer die Bombe ist nur, was ohnehin im Speicher ist; das zeigt diese Liste.
    Ohne FILTER wird es lang (Level-Geometrie) - besser 'zb meshes Grenade', 'zb meshes Prop_' usw."""
    flt_l = flt.lower()
    treffer: list[str] = []
    gesamt = 0
    for m in unrealsdk.find_all("StaticMesh", exact=True):
        gesamt += 1
        pfad = m._path_name()
        if flt_l in pfad.lower():
            treffer.append(pfad)
    treffer.sort()
    logging.info(f"[ZB] meshes '{flt}': {len(treffer)} von {gesamt} geladenen StaticMeshes")
    for pfad in treffer[:limit]:
        logging.info(f"[ZB]   {pfad}")
    if len(treffer) > limit:
        logging.info(f"[ZB]   ... und {len(treffer) - limit} weitere (Filter enger fassen)")


# ---------------------------------------------------------------- Diagnose


def dump_props(obj: UObject | None, flt: str) -> None:
    if obj is None:
        logging.info("[ZB] props: kein Objekt")
        return
    flt = flt.lower()
    n = 0
    for name in dir(obj):
        if flt not in name.lower():
            continue
        try:
            val = getattr(obj, name)
        except Exception as ex:  # noqa: BLE001
            val = f"<{ex}>"
        if callable(val):
            continue
        n += 1
        logging.info(f"[ZB] {obj.Class.Name}.{name} = {str(val)[:160]}")
    logging.info(f"[ZB] props: {n} Treffer fuer '{flt}' an {obj.Class.Name}")


def dump_funcs(cname: str, flt: str = "") -> None:
    from unrealsdk.unreal import UFunction  # noqa: PLC0415
    try:
        ucls = unrealsdk.find_class(cname)
    except ValueError:
        logging.error(f"[ZB] Klasse {cname} nicht gefunden")
        return
    # Auch die geerbten Funktionen (v0.54): PlayerSkillTree hatte kein GetSkillGrade - ob die
    # Elternklasse eins hat, sieht man nur, wenn man die Kette hochlaeuft.
    cls = ucls
    while cls is not None and cls.Name != "Object":  # Object selbst: 250 Zeilen Mathe, nie gesucht
        for fld in cls._fields():
            if not isinstance(fld, UFunction) or flt.lower() not in fld.Name.lower():
                continue
            params = []
            for p in fld._fields():
                try:
                    if p.Class.Name == "StructProperty":
                        extra = f":{p.Struct.Name}"
                    elif p.Class.Name == "ByteProperty":
                        # Ein ByteProperty mit Enum ist ein Enum-Parameter (v0.68: NotifySkillEvent
                        # EventType). Ohne diesen Namen weiss man nicht, welche Werte erlaubt sind.
                        extra = f":{p.Enum.Name}" if p.Enum is not None else ""
                    else:
                        extra = ""
                except Exception:  # noqa: BLE001
                    extra = ""
                params.append(f"{p.Class.Name}{extra} {p.Name}")
            logging.info(f"[ZB] {cls.Name}.{fld.Name}({', '.join(params)})")
        try:
            cls = cls.SuperField
        except Exception:  # noqa: BLE001
            cls = None


def namen_sammeln() -> None:
    """Alle Namen auf einmal fragen, die Handgriff 4 (die 17 Platzhalter) braucht (v0.71).

    Ein Testlauf statt siebzehn. Jede Zeile ist eine Frage aus docs/skills.md: Munition (Volle
    Rueckerstattung), Statuseffekte und Unverwundbarkeit (Reinigung, Zeitsprung), FFYL (Es war nie
    passiert), Schaden/Stagger an Gegnern (Nachhall, Ruecksprung-Detonation, Zeitsprung, Paradoxon),
    Tempo an Gegnern (Zeitspur) und die laufende Skilldauer (Kurs halten).

    Gegner finden ist schon belegt: unrealsdk.find_all("WillowAIPawn", exact=False) - das Muster
    steht im FL4K-Projekt (sdk/fl4k_pet/__init__.py) und laeuft dort seit Monaten.
    """
    fragen = (
        # (Klasse, Filter, wofuer)
        ("WillowPlayerController", "Ammo", "Volle Rueckerstattung"),
        ("WillowPlayerController", "Injured", "Es war nie passiert"),
        ("WillowPlayerController", "Invuln", "Reinigung, Zeitsprung"),
        ("WillowPlayerPawn", "Ammo", "Volle Rueckerstattung"),
        ("WillowPlayerPawn", "Status", "Reinigung"),
        ("WillowPlayerPawn", "Injured", "Es war nie passiert"),
        ("WillowPlayerPawn", "Invuln", "Reinigung, Zeitsprung"),
        ("WillowPlayerPawn", "God", "Reinigung (Notnagel)"),
        ("WillowWeapon", "Ammo", "Volle Rueckerstattung"),
        ("WillowAIPawn", "TakeDamage", "Nachhall, Zeitsprung, Paradoxon"),
        ("WillowAIPawn", "Stagger", "Nachhall, Zeitsprung"),
        ("WillowAIPawn", "Knock", "Nachhall (Rueckstoss)"),
        ("WillowAIPawn", "Status", "Zeitspur (Markierung)"),
        ("WillowAIPawn", "Velocity", "Nachhall (Rueckstoss)"),
        ("Actor", "HurtRadius", "Ruecksprung-Detonation, Sprengsatz"),
        ("ExecuteActionSkill", "Duration", "Kurs halten"),
        ("ExecuteActionSkill", "Time", "Kurs halten"),
        ("SkillEffectManager", "GetActive", "Kurs halten (laufende Instanz)"),
    )
    for cls, flt, wofuer in fragen:
        logging.info(f"[ZB] --- {cls} ~ '{flt}'  ({wofuer})")
        dump_funcs(cls, flt)
    # Munition und Statuseffekte haengen vermutlich an Eigenschaften, nicht an Funktionen - beides
    # fragen, damit der Lauf in jedem Fall etwas hergibt.
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    for obj, label, flt in ((pawn, "pawn", "ammo"), (pawn, "pawn", "pool"), (pawn, "pawn", "status"),
                            (pc, "pc", "ammo"), (pawn, "pawn", "invuln")):
        logging.info(f"[ZB] --- Eigenschaften {label} ~ '{flt}'")
        dump_props(obj, flt)
    logging.info("[ZB] namen: fertig")


def dump_enum(flt: str = "skill") -> None:
    """Enums samt Werten auflisten (v0.68/v0.69, fuer Deja-vu: der Enum-Wert von NotifySkillEvent).

    Der Objekt-Dump von OpenBLCMM kennt die Enum-Objekte, aber nicht ihre Werte - die stehen nur
    im Speicher. `unrealsdk.find_enum` liefert sie (v0.68 gemessen; `uenum.Names` gibt es nicht).

    FALLE (v0.68, gemessen): Was zurueckkommt, ist ein Python-IntFlag, und ueber ein IntFlag
    ITERIEREN zeigt nur die Einzelbit-Werte - 1, 2, 4, 8, 16, 32. Alles andere (der Wert 0 und
    jeder Wert, der aus mehreren Bits besteht: 3, 5, 6, 7, ...) gilt Python als Alias und faellt
    weg. UE3-Enums zaehlen aber schlicht hoch. Belegt am Gegenbeispiel: ESkillKillEvents zeigte
    beim Iterieren nur SKE_KilledByEnemy, obwohl SKE_KilledEnemy 70-mal im Dump steht - es hat
    Wert 0. Deshalb `__members__`: das Verzeichnis haelt ALLE Namen, Aliase eingeschlossen.
    """
    flt = flt.lower()
    treffer = 0
    for uenum in unrealsdk.find_all("Enum"):
        name = uenum.Name
        if flt not in str(name).lower():
            continue
        treffer += 1
        werte: list[str] = []
        weg = "-"
        try:
            py = unrealsdk.find_enum(str(name))  # type: ignore[attr-defined]
            mitglieder = getattr(py, "__members__", None)
            if mitglieder:
                weg = "__members__"
                werte = [f"{int(m)}={n}" for n, m in sorted(mitglieder.items(), key=lambda kv: int(kv[1]))]
            else:  # kein Python-Enum, sondern etwas anderes - dann eben iterieren
                weg = "iteriert (nur Einzelbits!)"
                werte = [f"{e.value}={e.name}" for e in py]
        except Exception as ex:  # noqa: BLE001
            weg = f"kein Weg ({ex})"
        logging.info(f"[ZB] Enum {uenum._path_name()} [{weg}]: {', '.join(werte) if werte else '?'}")
    logging.info(f"[ZB] enum: {treffer} Enum(s) mit '{flt}' im Namen")


# ---------------------------------------------------------------- Spur: die Skill-Ereignisse (Spike B, beantwortet)
#
# Ergebnis 2026-09-19 (docs/spikes.md): genau diese vier Funktionen tragen den Action Skill. Sie sind die
# Hook-Punkte fuer Phase 3 - Legen (OnActionSkillStarted), Zuenden (StartActionSkill PRE bei Zustand
# "gelegt", dann pc.ResetActionSkill()), Verpuffen (OnActionSkillEnded), Hologramm (Decoy-Spawn).
# "zb spur" schaltet das Logging ein; Standard aus.

_trace = False

SKILL_PRESSED = "WillowGame.WillowPlayerController:StartActionSkill"  # jeder Druck, auch bei laufendem Skill
SKILL_STARTED = "WillowGame.ActionSkill:OnActionSkillStarted"          # Skill gestartet (obj = ExecuteActionSkill)
SKILL_ENDED = "WillowGame.ActionSkill:OnActionSkillEnded"              # Ablauf oder Abbruch
DECOY_SPAWN = "WillowGame.Behavior_SpawnFromPopulationSystem:ApplyBehaviorToContext"  # Decoy, 0,6 s nach Start

TRACE_FUNCS = [SKILL_PRESSED, SKILL_STARTED, SKILL_ENDED, DECOY_SPAWN]


# Die ActionSkill-Instanz (ExecuteActionSkill) - kommt aus dem OnActionSkillStarted-Hook, wird fuer
# das programmatische Beenden (zb ende) gebraucht.
_skill: UObject | None = None


def _make_tracer(fname: str):
    short = fname.split(".")[-1]

    def tracer(obj: UObject, args: Any, ret: Any, func: Any) -> None:
        global _skill
        if short == "ActionSkill:OnActionSkillStarted":
            _skill = obj
        if not _trace:
            return
        try:
            cooldown = local_pc().IsActionSkillOnCooldown()
        except Exception:  # noqa: BLE001
            cooldown = "?"
        logging.info(f"[ZB] SPUR {short}  obj={obj.Class.Name}  cooldown={cooldown}")

    return tracer


# ---------------------------------------------------------------------------
# Phase 3, Schritt 1: die Verdrahtung - aus der Skilltaste wird Legen und Zuenden
# Im Spiel bestaetigt (v0.31, 2026-09-20): drei Zyklen Legen->Zuenden und ein Verpuffen.
#
# Zustandsautomat: docs/skills.md, Abschnitt 4. Hook-Punkte: docs/spikes.md, Spike B.
#
#   OnActionSkillStarted (POST)  -> legen()     Anker setzen
#   StartActionSkill     (PRE)   -> zuenden()   nur im Zustand "gelegt"; danach Skill beenden
#   OnActionSkillEnded   (POST)  -> verpuffen() falls noch "gelegt" (Fenster abgelaufen)
#
# ZUR REIHENFOLGE: Beim ersten Tastendruck kommt StartActionSkill ZUERST, OnActionSkillStarted
# danach - der PRE-Hook trifft den Zustand also noch auf "bereit" und laesst durch. Spike B hatte
# es zunaechst umgekehrt notiert; widerlegt im v0.31-Test durch Abwesenheit (die Totzeit-Logzeile
# "selber Druck, ignoriert" erschien in keinem der drei Zyklen). Die Totzeit GUARD_SECONDS bleibt
# trotzdem stehen: sie kostet nichts, und ob die Reihenfolge ueberall dieselbe ist, ist
# erklaertermassen unsicher. Der gemessene Abstand steht in jeder Zuenden-Logzeile.
#
# Schritt 5 (plan.md D9): Zer0s Hologramm erscheint seit dem Stealth-Block nicht mehr (v0.43);
# stattdessen legt legen() per bombe_setzen() ein eigenes Objekt am Anker ab (Abschnitt oben).
# ---------------------------------------------------------------------------

ZUSTAND_BEREIT = "bereit"
ZUSTAND_GELEGT = "gelegt"

GUARD_SECONDS = 0.3  # kuerzer als jeder menschliche Doppeldruck, laenger als "derselbe Frame"

_state = ZUSTAND_BEREIT
_legen_time = 0.0


def _game_time(pc: UObject) -> float:
    try:
        return float(pc.WorldInfo.TimeSeconds)
    except Exception:  # noqa: BLE001
        return 0.0


def cooldown_rest(pc: UObject) -> float:
    try:
        return float(pc.GetSkillCooldownTimeRemaining())
    except Exception:  # noqa: BLE001
        return 0.0


def cooldown_setzen(pc: UObject, sekunden: float) -> bool:
    """Den Cooldown-Pool auf einen Wert setzen. "Auf Cooldown" heisst Poolwert > 0, und der Wert
    ist zugleich die Restzeit in Sekunden (Verbrauchsrate 1.0/s).

    Der belegte Schreibweg ist pool.SetCurrentValue(x) (gemessen 2026-09-20: 17,5 s beim Verpuffen).
    Der zweite Weg bleibt als Rueckfallebene stehen, falls eine andere Pool-Art einmal anders
    reagiert. Gemessen wird am Ende ueber GetSkillCooldownTimeRemaining, nicht am geschriebenen
    Wert: nur das zaehlt als Beweis (CLAUDE.md, Regel 3).
    """
    try:
        pool = pc.SkillCooldownPool.Data
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Cooldown setzen: Pool nicht erreichbar: {ex}")
        return False
    if pool is None:
        logging.error("[ZB] Cooldown setzen: Pool ist None")
        return False
    for weg, fn in (
        ("SetCurrentValue", lambda: pool.SetCurrentValue(sekunden)),
        ("CurrentValue =", lambda: setattr(pool, "CurrentValue", sekunden)),
    ):
        try:
            fn()
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] Cooldown setzen: {weg} geht nicht ({ex})")
            continue
        rest = cooldown_rest(pc)
        if abs(rest - sekunden) < 0.6:
            logging.info(f"[ZB] Cooldown gesetzt ueber {weg}: {rest:.1f}s (Ziel {sekunden:.1f}s)")
            return True
        logging.info(f"[ZB] Cooldown setzen: {weg} lief, wirkte aber nicht (Rest {rest:.1f}s)")
    return False


def verpuffen(grund: str) -> None:
    """Fenster abgelaufen oder Skill abgebrochen, ohne dass gezuendet wurde. Anker weg, keine
    Rueckkehr - und nur der HALBE Cooldown (docs/skills.md, Abschnitt 4: nicht zuenden zu muessen
    wird belohnt)."""
    global _state, _anchor
    _state = ZUSTAND_BEREIT
    if _anchor is not None:
        effekt("Verpuffen", FX_VERPUFFEN, _vec(_anchor.x, _anchor.y, _anchor.z), 500.0)   # Phase 8 (v1.00)
    _anchor = None
    logging.info(f"[ZB] verpufft ({grund}) - Anker verworfen, keine Rueckkehr")
    bombe_weg("verpufft")

    pc = local_pc()
    if pc is None:
        return
    # Beim regulaeren Ablauf startet die Engine den Cooldown selbst - dann steht hier schon die volle
    # Zeit und wir halbieren sie. Steht nichts, starten wir ihn erst. Halbiert wird der GEMESSENE
    # Rest, nicht COOLDOWN_SEKUNDEN: so stimmt es auch, wenn Skills den Cooldown verkuerzen.
    rest = cooldown_rest(pc)
    if rest <= 0.1:
        try_call("StartActiveSkillCooldown (verpufft)", pc.StartActiveSkillCooldown)
        rest = cooldown_rest(pc)
    if mechanik_verpufft():
        # Kein Zurueck (Baum 3, Tier 5): voller Erlass statt Haelfte.
        logging.info(f"[ZB] verpufft: Cooldown {rest:.1f}s -> erlassen (Kein Zurueck)")
        cooldown_setzen(pc, 0.0)
        return
    logging.info(f"[ZB] verpufft: Cooldown {rest:.1f}s -> halbiert")
    cooldown_setzen(pc, rest / 2.0)


def _on_skill_started(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST auf ActionSkill:OnActionSkillStarted - der Skill laeuft, die Bombe wird gelegt."""
    global _state, _legen_time, _anchor
    pc = local_pc()
    if not ist_chronomaster(pc):
        return
    # Alten Anker erst wegwerfen: legen() steigt bei Fahrzeug/kein Pawn aus, OHNE _anchor zu setzen -
    # ein stehengebliebener Anker wuerde sonst als frisch gelegt gelten.
    _anchor = None
    legen()
    if _anchor is None:
        logging.info("[ZB] legen abgelehnt - Zustand bleibt bereit")
        return
    _state = ZUSTAND_GELEGT
    _legen_time = _game_time(pc)
    logging.info(f"[ZB] Zustand: {_state} (t={_legen_time:.2f}) - Skilltaste erneut = zuenden")
    mechanik_gelegt()


def _on_start_pressed(obj: UObject, args: Any, ret: Any, func: Any) -> Any:
    """PRE auf WillowPlayerController:StartActionSkill - jeder Tastendruck, auch waehrend der
    Skill laeuft (Spike B). Im Zustand 'gelegt' ist das der zweite Druck: zuenden."""
    global _state
    from unrealsdk.hooks import Block  # noqa: PLC0415
    pc = local_pc()
    if not ist_chronomaster(pc):
        return None
    if _state != ZUSTAND_GELEGT:
        # Erster Druck: der Skill startet gleich - vorher das Fenster nach Langzeitgedaechtnis setzen.
        fenster_anpassen()
        try:
            _schatten_taste_gedrueckt(pc)  # Schattenanker (v0.95): Halten beobachten
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Schattenanker: {ex}")
        return None
    abstand = _game_time(pc) - _legen_time
    if abstand < GUARD_SECONDS:
        # Derselbe Tastendruck, der eben den Skill gestartet hat - durchlassen.
        logging.info(f"[ZB] StartActionSkill {abstand:.3f}s nach dem Legen -> selber Druck, ignoriert")
        return None
    logging.info(f"[ZB] ZUENDEN ({abstand:.2f}s nach dem Legen)")
    if in_vehicle(pc):
        logging.info("[ZB] zuenden: im Fahrzeug nicht moeglich - Bombe bleibt liegen")
        return Block
    zuenden_komplett(pc)
    return Block


def zuenden_komplett(pc: UObject) -> None:
    """Alles, was zum Zuenden gehoert - vom Tastendruck (_on_start_pressed) und seit v0.89 auch
    automatisch aus 'Es war nie passiert'. Vorher stand das nur im Tastendruck-Hook."""
    global _state
    # Zustand VOR dem Beenden zuruecksetzen: ResetActionSkill loest OnActionSkillEnded noch im
    # selben Aufruf aus (Spike B), und das wuerde sonst faelschlich als "verpufft" gelten.
    zuenden()
    bombe_weg("gezuendet")
    _state = ZUSTAND_BEREIT
    if pc.Pawn is not None:
        mechanik_gezuendet(pc.Pawn)
    # ResetActionSkill beendet den Skill sofort - loescht aber auch den Cooldown (Spike B, zweimal
    # gemessen: TimeRemaining 15.0 -> 0.0). Deshalb starten wir ihn danach selbst; die eigene
    # Pool-Kopie (ensure_cooldown_pool) macht daraus 35 s statt Decepti0ns 15 s.
    try_call("ResetActionSkill", pc.ResetActionSkill)
    try_call("StartActiveSkillCooldown", pc.StartActiveSkillCooldown)
    logging.info(f"[ZB] Cooldown laeuft: {cooldown_rest(pc):.1f}s")


# ---------------------------------------------------------------- Schattenanker (Capstone Baum 2, v0.95)
#
# "Auch ohne gelegte Bombe merkt sich der Skill laufend einen Anker von vor 5 s. Taste halten =
# Schattenzuendung (1,5-facher Cooldown)."
#
# Ringpuffer: im PlayerTick alle 0,1 s ein stiller Schnappschuss (dieselben Felder wie legen()),
# 6 s lang. Nur mit gelerntem Skill - sonst kostet es nichts.
#
# "Halten": ein Loslassen-Ereignis der Skilltaste gibt es nicht (Spike B; die Taste ist als GBA_
# fest verdrahtet, in keiner INI). Aber WillowUIInteraction:InputKey sieht jede Taste mit
# IE_Pressed/IE_Released - darauf baut die offizielle Keybind-Erweiterung (sdk_mods/keybinds.sdkmod).
# Welche Taste die Skilltaste ist, lernen wir: die zuletzt gedrueckte Taste, wenn StartActionSkill
# feuert. Der Druck legt die Bombe ganz normal; wird die Taste danach SCHATTEN_HALTEN_S gehalten,
# wird daraus eine Schattenzuendung: Anker = Schnappschuss von vor 5 s, dann zuenden_komplett, dann
# Cooldown x 1,5. So braucht es keinen geblockten Tastendruck und keinen eigenen Skillstart.

# Paket per keybinds.sdkmod belegt ("WillowGame.WillowUIInteraction:InputKey", dort in Betrieb).
INPUT_KEY_FUNC = "WillowGame.WillowUIInteraction:InputKey"
SCHATTEN_ALTER_S = 5.0
SCHATTEN_PUFFER_S = 6.0
SCHATTEN_TAKT_S = 0.1
SCHATTEN_HALTEN_S = 0.5            # BL2s eigene Haltezeit ist 0,35 s (WillowPlayerInput.ButtonHoldEventTime)
SCHATTEN_COOLDOWN_FAKTOR = 1.5

_schatten_puffer: list[tuple[float, Anchor]] = []   # (Spielzeit, Schnappschuss), aelteste zuerst
_schatten_akku = 0.0
_taste_zuletzt: tuple[str, float] = ("", -1.0)      # (Taste, Spielzeit) des letzten IE_Pressed
_skill_taste = ""                                   # gelernt bei StartActionSkill
_skill_taste_unten = False
_halten_seit = -1.0                                  # >= 0: Haltepruefung laeuft seit dieser Spielzeit
_zeitkapsel_ausstehend: Any = None                   # Ort, falls die Zeitkapsel auf das Loslassen wartet
_schatten_laeuft = False                             # waehrend einer Schattenzuendung: keine Hologramme


def _schnappschuss(pc: UObject, pawn: UObject) -> Anchor | None:
    """Wie legen(), aber still (10 x je Sekunde) - keine try_call-Zeilen im Log."""
    try:
        loc, rot, weapon = pawn.Location, pc.Rotation, pawn.Weapon
        return Anchor(
            map_name=map_name(pc), x=loc.X, y=loc.Y, z=loc.Z,
            pitch=rot.Pitch, yaw=rot.Yaw, roll=rot.Roll,
            health=float(pawn.GetHealth()), shield=float(pawn.GetShieldStrength()),
            weapon=weapon._path_name() if weapon else "",
            magazine=int(weapon.ReloadCnt) if weapon else 0,
        )
    except Exception:  # noqa: BLE001
        return None


def _schatten_tick(pc: UObject, dt: float) -> None:
    """Jeden Frame: Puffer fuellen (alle 0,1 s) und die Haltepruefung."""
    global _schatten_akku, _halten_seit, _zeitkapsel_ausstehend
    jetzt = _game_time(pc)
    _schatten_akku += dt
    # Rang nur im 0,1-s-Takt fragen (skill_rang sucht jedes Mal das Skillobjekt).
    if _schatten_akku >= SCHATTEN_TAKT_S:
        _schatten_akku = 0.0
        if skill_rang("Schattenanker") <= 0:
            _schatten_puffer.clear()
            _halten_seit = -1.0
            return
        snap = _schnappschuss(pc, pc.Pawn) if pc.Pawn is not None and not in_vehicle(pc) else None
        if snap is not None:
            if _schatten_puffer and _schatten_puffer[-1][1].map_name != snap.map_name:
                _schatten_puffer.clear()   # Kartenwechsel: alte Orte gelten nicht mehr
            _schatten_puffer.append((jetzt, snap))
            while _schatten_puffer and jetzt - _schatten_puffer[0][0] > SCHATTEN_PUFFER_S:
                _schatten_puffer.pop(0)
    if _halten_seit < 0:
        return
    if not _skill_taste_unten:
        logging.info(f"[ZB] Schattenanker: Taste nach {jetzt - _halten_seit:.2f} s losgelassen - normales Legen")
        _halten_seit = -1.0
        if _zeitkapsel_ausstehend is not None and _state == ZUSTAND_GELEGT:
            holo_spawnen(_zeitkapsel_ausstehend, "Zeitkapsel", HOLO_OHNE_ENDE)  # nachgeholt (v0.96)
        _zeitkapsel_ausstehend = None
        return
    if jetzt - _halten_seit >= SCHATTEN_HALTEN_S:
        _halten_seit = -1.0
        _zeitkapsel_ausstehend = None
        if _state == ZUSTAND_GELEGT:
            schatten_zuenden(pc, f"Taste {_skill_taste} {SCHATTEN_HALTEN_S:.1f} s gehalten")
        else:
            logging.info(f"[ZB] Schattenanker: gehalten, aber Zustand {_state} - nichts zu tun")


def _schatten_anker(pc: UObject) -> tuple[Anchor, float] | None:
    """Der Schnappschuss, der am naechsten an 'vor 5 s' liegt (oder der aelteste, wenn es noch
    keine 5 s gibt). Gibt (Anker, Alter in s) zurueck."""
    if not _schatten_puffer:
        return None
    ziel = _game_time(pc) - SCHATTEN_ALTER_S
    zeit, snap = min(_schatten_puffer, key=lambda e: abs(e[0] - ziel))
    return snap, _game_time(pc) - zeit


def schatten_zuenden(pc: UObject, grund: str) -> None:
    """Schattenzuendung: zuenden mit dem Anker von vor 5 s, danach Cooldown x 1,5."""
    global _anchor
    treffer = _schatten_anker(pc)
    if treffer is None:
        logging.info(f"[ZB] Schattenanker ({grund}): Puffer leer - nichts zu tun")
        return
    snap, alter = treffer
    logging.info(f"[ZB] SCHATTENZUENDUNG ({grund}): Anker von vor {alter:.1f} s bei ({snap.x:.0f},{snap.y:.0f},{snap.z:.0f}),"
                 f" Leben {snap.health:.0f}, Schild {snap.shield:.0f} ({len(_schatten_puffer)} im Puffer)")
    global _schatten_laeuft
    _anchor = snap
    _schatten_laeuft = True   # Nachbild aus (v0.96)
    try:
        zuenden_komplett(pc)
    finally:
        _schatten_laeuft = False
    _anchor = None
    rest = cooldown_rest(pc)
    cooldown_setzen(pc, rest * SCHATTEN_COOLDOWN_FAKTOR)
    logging.info(f"[ZB] Schattenanker: Cooldown {rest:.1f} s x {SCHATTEN_COOLDOWN_FAKTOR} -> {cooldown_rest(pc):.1f} s")


def _schatten_taste_gedrueckt(pc: UObject) -> None:
    """Aus _on_start_pressed (Zustand bereit): Skilltaste lernen, Haltepruefung scharf machen."""
    global _skill_taste, _skill_taste_unten, _halten_seit
    if skill_rang("Schattenanker") <= 0:
        return
    taste, zeit = _taste_zuletzt
    jetzt = _game_time(pc)
    if taste and 0 <= jetzt - zeit < 0.3:
        if taste != _skill_taste:
            logging.info(f"[ZB] Schattenanker: Skilltaste gelernt = {taste}")
        _skill_taste, _skill_taste_unten = taste, True
        _halten_seit = jetzt
    else:
        logging.info(f"[ZB] Schattenanker: keine Taste kurz vor StartActionSkill gesehen ({taste!r} vor"
                     f" {jetzt - zeit:.2f} s) - Halten nicht erkennbar")


def schatten_zeigen() -> None:
    """zb schatten [los] - Pufferstand; mit 'los' eine Schattenzuendung von Hand (ohne Taste)."""
    pc = local_pc()
    if pc is None:
        return
    treffer = _schatten_anker(pc)
    logging.info(f"[ZB] schatten: {len(_schatten_puffer)} Schnappschuesse, Skilltaste {_skill_taste or '(noch nicht gelernt)'},"
                 f" Anker {'von vor %.1f s' % treffer[1] if treffer else 'keiner'}")


def _on_input_key(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """PRE auf WillowUIInteraction:InputKey - jede Taste. Nur mitschreiben, nie blockieren."""
    global _taste_zuletzt, _skill_taste_unten
    try:
        taste = str(args.Key)
        ereignis = getattr(args.Event, "name", str(args.Event))
    except Exception:  # noqa: BLE001
        return
    if ereignis == "IE_Pressed":
        pc = local_pc()
        _taste_zuletzt = (taste, _game_time(pc) if pc else 0.0)
    elif ereignis == "IE_Released" and taste == _skill_taste:
        _skill_taste_unten = False


# v0.90: Das Umfallen in Fight for your Life BRICHT DEN ACTION SKILL AB (v0.89 im Spiel: "verpufft
# (... Skill abgebrochen) - Anker verworfen", dann erst lief der Tick, der fuer 'Es war nie passiert'
# zuenden wollte - und fand keinen Anker mehr). Wer den Skill gelernt hat, verpufft deshalb nicht
# sofort: 0,5 s Aufschub, in denen ein FFYL-Hook den Vorrang bekommt. Ohne den Skill bleibt alles
# wie vorher - kein Aufschub, kein veraendertes Verhalten.
VERPUFFEN_AUFSCHUB_S = 0.5
_verpuffen_ausstehend = ""   # Grund; leer = nichts vorgemerkt
_verpuffen_frist = 0.0


def _on_skill_ended(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST auf ActionSkill:OnActionSkillEnded - Ablauf oder Abbruch. Stehen wir hier noch auf
    'gelegt', hat der Spieler nicht gezuendet."""
    global _verpuffen_ausstehend, _verpuffen_frist
    if _state != ZUSTAND_GELEGT or not ist_chronomaster(local_pc()):
        return
    grund = "Fenster abgelaufen oder Skill abgebrochen"
    if skill_rang("EsWarNiePassiert") > 0:
        _verpuffen_ausstehend, _verpuffen_frist = grund, VERPUFFEN_AUFSCHUB_S
        logging.info(f"[ZB] Skill-Ende im Zustand gelegt - Verpuffen in {VERPUFFEN_AUFSCHUB_S} s, "
                     f"falls kein Fight for your Life dazwischenkommt")
        return
    verpuffen(grund)


def _verpuffen_tick(dt: float) -> None:
    """Laeuft im PlayerTick NACH _ffyl_tick: war kein Umfallen, jetzt verpuffen."""
    global _verpuffen_ausstehend, _verpuffen_frist
    if not _verpuffen_ausstehend:
        return
    if _state != ZUSTAND_GELEGT:  # inzwischen gezuendet (Es war nie passiert) - nichts mehr zu tun
        _verpuffen_ausstehend = ""
        return
    _verpuffen_frist -= dt
    if _verpuffen_frist > 0:
        return
    grund, _verpuffen_ausstehend = _verpuffen_ausstehend, ""
    verpuffen(grund)


def askill() -> None:
    """'zb askill': Bestandsaufnahme am Action Skill. Reines Lesen, jederzeit gefahrlos.

    Hat in Schritt 2/3 zwei Fragen beantwortet und bleibt als Nachschlagewerk:
      1. Was haengt am Action Skill? -> In Tiers(0) steht eine SkillDefinition (Skill_Deception),
         die ueber ActionSkillArchetype auf ActionSkill_Deception zeigt - Klasse ExecuteActionSkill,
         nicht ActionSkillDefinition (so hatte ich es angenommen, die Klasse gibt es gar nicht).
      2. Wie ist pc.SkillCooldownPool aufgebaut? -> ResourcePool unter einem ResourcePoolManager,
         dessen Name mit der Welt wechselt (drei Tests, drei Namen - nie cachen).
    """
    pc = local_pc()
    if pc is None:
        logging.error("[ZB] askill: kein Spieler")
        return
    logging.info("[ZB] === askill: Bestandsaufnahme Action Skill ===")

    # 1. Was steht in Tiers(0) unseres Wurzelastes?
    ast = _find("SkillTreeBranchDefinition", f"{TREE_OUTER}.Branch_{CHARACTER_NAME}")
    if ast is None:
        logging.error("[ZB] askill: Wurzelast fehlt")
    else:
        for i, t in enumerate(ast.Tiers):
            namen = [f"{s.Class.Name} {s._path_name()}" for s in t.Skills]
            logging.info(f"[ZB] askill: Wurzelast Tier {i}: {namen}")

    # 2. Die beiden Objekte aus docs/skills.md - welche Felder tragen was?
    for cls, pfad in (("SkillDefinition", "GD_Assassin_Skills.ActionSkill.Skill_Deception"),
                      ("ActionSkillDefinition", "GD_Assassin_Skills.ActionSkill.ActionSkill_Deception")):
        obj = _find(cls, pfad)
        if obj is None:
            # Klasse koennte anders heissen - ueber find_all im Paket suchen
            logging.info(f"[ZB] askill: {cls} {pfad} nicht gefunden, suche per find_all")
            for o in unrealsdk.find_all("SkillDefinition", exact=False):
                if "ActionSkill" in o._path_name():
                    logging.info(f"[ZB] askill:   Kandidat {o.Class.Name} {o._path_name()}")
            continue
        logging.info(f"[ZB] askill: --- {obj.Class.Name} {obj._path_name()} ---")
        for flt in ("duration", "name", "descri", "type", "grade", "ability", "skill", "stealth"):
            dump_props(obj, flt)

    # 3. Der Cooldown-Pool, diesmal ungekuerzt.
    try:
        pool = pc.SkillCooldownPool
        logging.info(f"[ZB] askill: SkillCooldownPool = {pool}")
        for feld in ("PoolManager", "PoolIndexInManager", "PoolGUID", "Data"):
            try:
                logging.info(f"[ZB] askill:   .{feld} = {getattr(pool, feld)}")
            except Exception as ex:  # noqa: BLE001
                logging.info(f"[ZB] askill:   .{feld} FEHLER {ex}")
        mgr = pool.PoolManager
        if mgr is not None:
            dump_funcs(mgr.Class.Name, "pool")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] askill: SkillCooldownPool: {ex}")

    # 4. Womit setzt man einen Cooldown? Die Kandidaten am Controller.
    dump_funcs("WillowPlayerController", "cooldown")
    dump_funcs("WillowPlayerController", "actionskill")
    logging.info("[ZB] === askill Ende ===")


def ende(variant: str) -> None:
    """Laufenden Skill per SDK beenden (Spike B, beantwortet 2026-09-19):
    2 = WillowPlayerController.ResetActionSkill  -> WIRKT (Standard); setzt aber auch den Cooldown zurueck
    1 = ActionSkill.OnActionSkillWantsToDeactivate -> laeuft, wirkt bei Zer0s ExecuteActionSkill nicht
    3 = ActionSkill.OnActionSkillDeactivated mit leerem Handle -> ungetestet"""
    pc = local_pc()
    if _skill is None:
        logging.error("[ZB] ende: keine Skill-Instanz bekannt (Skill seit Modulstart noch nie gestartet)")
        return
    logging.info(f"[ZB] ende: Variante {variant}")
    match variant:
        case "1":
            try_call("IsDeactivateBlocked", _skill.IsDeactivateBlocked)
            try_call("OnActionSkillWantsToDeactivate", _skill.OnActionSkillWantsToDeactivate)
        case "2":
            try_call("CanResetActionSkill", pc.CanResetActionSkill)
            try_call("ResetActionSkill", pc.ResetActionSkill)
        case "3":
            handle = unrealsdk.make_struct("BehaviorConsumerHandle")
            try_call("OnActionSkillDeactivated", lambda: _skill.OnActionSkillDeactivated(handle, pc.Pawn))
        case _:
            logging.info("[ZB] zb ende 1|2|3")


# ---------------------------------------------------------------- Spike C: Charakterliste
#
# Gelernt aus der Nisha-Mod (LJBreeze, GPL v3, custom_dlc_loader) am 2026-09-19:
#   - Der richtige Moment ist PRE CharacterSelectionGFxObject:CommitSelectableCharacters - das ist die
#     Uebergabe der Liste an Flash. Unser bisheriger POST-Hook auf BuildCharacterList kam zu spaet: Flash
#     war schon befuellt, Index 6 existierte nur in der Script-Liste -> keine Kachel, Klasse fiel auf Axton.
#   - Die Kachel legt Flash selbst an: obj.AddSelectableCharacter("/ package/<SwfPaket>/<Portrait>").
#   - Die Klasse braucht keinen Hook: NameId.CharacterClassId + NameId.DefaultSaveGame (Profil mit
#     PlayerClassDefinition) - die Objektkette entscheidet.
# Eigene Befunde (18:17-18:40): SelectableCharacters ist PlayerNameIdentifierDefinition[], StandIn hat
# nur 2 Eintraege (Spieler 1/2), GetCachedSaveGame() liefert eine Kopie (Schreiben wirkungslos).

COMMIT_FUNC = "WillowGame.CharacterSelectionGFxObject:CommitSelectableCharacters"
# Das Charakter-Menue selbst. In v0.6-v0.8 schon als POST-Hook benutzt (Log 18:23: "BuildCharacterList
# -> 6 Eintraege"), damals fuer die Bestandsaufnahme. Seit v0.29 haengt die Baumkette als
# RUECKFALLEBENE daran - die letzte Station vor jedem Laden, falls der Modulstart einmal nicht reicht.
LIST_FUNC = "WillowGame.CharacterSelectionReduxGFxMovie:BuildCharacterList"

# Siebtes Namensobjekt: Kopie von Zer0s, UISortOrder 6, Klasse und Profil vorerst Zer0s (Wirt).
NAMEID_TEMPLATE = "GD_PlayerNameId.Assassin"
NAMEID_NEW = "GD_PlayerNameId.Chronomaster"
# Scaleform laedt Portraits per "/ package/"-URL aus SwfMovie-Paketen; Zer0s Portrait ist
# SwfMovie'UI_CharacterPortraits.Assassin' (StatusMenuGFxPortrait im Dump).
PORTRAIT_PATH = "/ package/UI_CharacterPortraits/Assassin"


def _find(cls: str, path: str) -> UObject | None:
    try:
        return unrealsdk.find_object(cls, path)
    except ValueError:
        return None


RF_ROOTSET = 0x00004000  # UE3-Objektflag: nie per Garbage Collection entsorgen


def _root(obj: UObject) -> None:
    """Laufzeit-Objekte ueberleben die GC nur mit RF_RootSet (Test 19:13: beim Start erzeugte Objekte waren
    im Menue wieder weg). Muster aus dem Nisha-Loader (_root_object)."""
    obj.ObjectFlags = obj.ObjectFlags | RF_ROOTSET


def _outer(outer_path: str) -> UObject:
    """Das Outer-Paket (bzw. die Gruppe) holen. Ist es nicht geladen - im Hauptmenue der Normalfall
    (Test 19:12: GD_TulipPackageDef fehlte) -, wird es nachgeladen. Fehlt es danach immer noch,
    fliegt ein Fehler: der Aufrufer entscheidet, ob er es spaeter erneut versucht."""
    outer = _find("Package", outer_path)
    if outer is None:
        try:
            unrealsdk.load_package(outer_path.split(".")[0])
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] load_package {outer_path}: {ex}")
        outer = _find("Package", outer_path)
    if outer is None:
        raise RuntimeError(f"Outer-Paket fehlt: {outer_path}")
    return outer


def _copy(cls: str, template_path: str, outer_path: str, name: str) -> UObject:
    """Laufzeit-Kopie eines Spielobjekts (construct_object mit Vorlage), gerootet. Existiert sie schon,
    wird sie wiederverwendet (rlm-Neuladen). Fehlt das Outer-Paket (DLC-Pakete sind beim Start noch
    nicht geladen, Test 19:12), wird es nachgeladen."""
    outer = _outer(outer_path)
    existing = _find(cls, f"{outer_path}.{name}")
    if existing is not None:
        return existing
    template = _find(cls, template_path)
    if template is None:
        raise RuntimeError(f"Vorlage fehlt: {cls} {template_path}")
    obj = unrealsdk.construct_object(cls, outer, name, template_obj=template)
    _root(obj)
    logging.info(f"[ZB] erzeugt {cls} {obj._path_name()} (Vorlage {template_path})")
    return obj


def _neu(cls: str, outer_path: str, name: str) -> UObject:
    """Laufzeit-Objekt OHNE Vorlage, gerootet. Fuer Objekte, deren Vorlage nicht im Speicher liegt -
    etwa die SkillTreeDefinition aus dem Streaming-Paket (Test 22:1x: auch mit geladenem Charakter
    nicht auffindbar). Sie traegt ohnehin nur das Feld Root."""
    existing = _find(cls, f"{outer_path}.{name}")
    if existing is not None:
        return existing
    obj = unrealsdk.construct_object(cls, _outer(outer_path), name)
    _root(obj)
    logging.info(f"[ZB] erzeugt {cls} {obj._path_name()} (ohne Vorlage)")
    return obj


# Spike C, Runde 5 (v0.12): die komplette Objektkette eines DLC-Charakters als Laufzeit-Kopien von Zer0
# bzw. Gaige (Tulip), verknuepft wie im Nisha-Loader, und beim DLC-Manager eingetragen. Log 19:06 zeigte:
# UpdatePlayerSaveGameFromSelectedCharacter setzt die Klasse aus einer nativen Tabelle (Index 4 ->
# Mechromancer, 2 -> Siren, 6 -> nichts). Die Tabelle wird vermutlich aus manager.Characters gefuellt.
SEVENTH = {
    "class_def": ("PlayerClassDefinition", "GD_Assassin.Character.CharClass_Assassin", "GD_Assassin.Character", "CharClass_Chronomaster"),
    "class_id": ("PlayerClassIdentifierDefinition", "GD_PlayerClassId.Assassin", "GD_PlayerClassId", "Chronomant"),
    "profile": ("PlayerSaveGame", "GD_DefaultProfiles.Assassin.Profile_Assassin", "GD_DefaultProfiles.Assassin", "Profile_Chronomaster"),
    "package_def": ("DownloadablePackageDefinition", "GD_TulipPackageDef.PackageDef_Tulip", "GD_TulipPackageDef", "PackageDef_Zeitbombe"),
    "registration": ("DownloadableCharacterDefinition", "GD_TulipPackageDef.CharacterDef_Tulip", "GD_TulipPackageDef", "CharacterDef_Zeitbombe"),
}
PACKAGE_ID = 26  # Nisha benutzt 25
CLASS_TITLE = "Timekeeper"   # sichtbar (v1.34, Nutzerwahl); das Objekt heisst weiter "Chronomant" (SEVENTH)

_seventh_ready = False

# ---------------------------------------------------------------------------
# Die eigene Baumkette (Spike D, im Spiel bestaetigt; seit v0.28 dauerhaft)
#
# Kette laut Datenmodell (../borderlands 2 mod/docs/datenmodell.md, 2.2/2.3):
#   PlayerClassDefinition.SkillTreePath  (ein String, kein Objektverweis)
#     -> SkillTreeDefinition.Root
#          -> SkillTreeBranchDefinition   (Wurzelast, Tiers(0) = Action Skill)
#               -> Children(0..2)         = die drei Baeume
#
# Sie muss stehen, BEVOR ein Spielstand geladen wird - deshalb Stufe 1, wie die Klasse selbst
# (docs/skills.md, 6.2: "Alle Objekte muessen existieren, bevor der Charakter geladen wird").
#
# Die Aeste sind vorerst Kopien von Zer0s Aesten und tragen noch dessen Skills in den Tiers.
# Eigen sind bis hierher nur die Astnamen. Phase 4-6 ersetzt die Skills einen nach dem anderen
# (docs/skills.md, Abschnitt 5), Phase 3 haengt die Zeitbombe in den Wurzelast.
# ---------------------------------------------------------------------------

TREE_OUTER = "GD_Assassin_Skills.SkillTree"
ROOT_BRANCH_TEMPLATE = f"{TREE_OUTER}.Branch_ActionSkill_Deception"

# Der Action Skill. Belegt durch 'zb askill' (2026-09-20): In Tiers(0) des Wurzelastes steht eine
# SkillDefinition (Skill_Deception), und die zeigt ueber das Feld ActionSkillArchetype auf
# ActionSkill_Deception - ein Objekt der Klasse ExecuteActionSkill (nicht ActionSkillDefinition,
# wie docs/skills.md vermuten liess).
ACTION_OUTER = "GD_Assassin_Skills.ActionSkill"
ACTION_SKILL_TEMPLATE = f"{ACTION_OUTER}.Skill_Deception"
ACTION_ARCHETYPE_TEMPLATE = f"{ACTION_OUTER}.ActionSkill_Deception"

# Fenster laut plan.md, Anhang A, Frage 2. Zer0s Decepti0n hat 6.5.
FENSTER_SEKUNDEN = 20.0

# Cooldown laut docs/skills.md, Abschnitt 4: 35 s nach dem Zuenden, die Haelfte nach dem Verpuffen
# (nicht zuenden zu muessen wird belohnt).
#
# Wie der Cooldown in BL2 funktioniert (Datenpaket, 2026-09-20):
#   CharClass.SkillCooldownPoolDefinition -> D_Resourcepools.PlayerPools.ActiveSkillCooldownPool_Assassin
#   Dessen BaseMaxValue kommt aus dem Attribut GD_Assassin_Skills.Misc.Cooldown_Deception -> daher die
#   15 s, die 'zb askill' gemessen hat. Beim Einsatz wird der Pool auf das Maximum gefuellt und laeuft
#   mit BaseConsumptionRate 1.0 leer; "auf Cooldown" heisst also schlicht "Poolwert > 0".
# Wir haengen deshalb eine eigene Pool-Kopie an unsere Klasse, mit 35 als Konstante statt des Attributs.
COOLDOWN_SEKUNDEN = 35.0
POOL_OUTER = "D_Resourcepools.PlayerPools"
POOL_TEMPLATE = f"{POOL_OUTER}.ActiveSkillCooldownPool_Assassin"
# v1.34: Objektname und Anzeigename getrennt. SKILL_OBJ steckt in den Objektpfaden (Skill_Zeitbombe,
# ActionSkill_Zeitbombe) und darf sich NIE aendern - Spielstaende verweisen darauf. Sichtbar ist nur
# SKILL_TITEL, seit v1.34 englisch (Nutzerentscheidung 2026-09-26: alles, was Spieler sehen, auf Englisch).
SKILL_OBJ = "Zeitbombe"
SKILL_TITEL = "Time Bomb"
# Im Stil des Originals: dieselben Auszeichnungen ([skill]...[-skill], StringAliasMap fuer die
# Tastenbelegung).
SKILL_TEXT = (
    "[skill]Action Skill.[-skill] Press <StringAliasMap:Action.ActionSkill> to throw a "
    "[skill]Time Bomb[-skill]. Where it lands is your return point, and it saves this moment - "
    "health, shield, magazine. Press again to return to it with everything you had. "
    "Wait too long and it expires - but then only half the cooldown applies. "
    # Zer0s Karte zieht ihre Zahlen aus vier geerbten Praesentationen, die auf unserer Karte nicht
    # erscheinen (Screenshot 2026-09-21) - also stehen Fenster und Cooldown als Text hier.
    f"Window: {FENSTER_SEKUNDEN:.0f} seconds. Cooldown: {COOLDOWN_SEKUNDEN:.0f} seconds."
)

# (Name der Kopie, Vorlage bei Zer0, BranchName im Skillmenue)
# BranchName ist der sichtbare Text (Branch_Sniping = "HINTERHALT", Spike D Runde 1). Seit v1.34
# englisch; der erste Eintrag ist der Objektname und bleibt deutsch (Spielstaende).
BRANCHES = [
    ("Vergangenheit", "Branch_Sniping", "HINDSIGHT"),
    ("Rueckkehr", "Branch_Cunning", "REWIND"),
    ("Ausflug", "Branch_Bloodshed", "DETOUR"),
]

# Das Paket, das Zer0s Baum-Vorlagen mitbringt. Gemessen (Test 2026-09-20, 11:03, Log):
# **GD_Assassin_Streaming_SF ist es** - die SeekFree-Variante, dieselbe Bauart, die Nisha als
# GD_Nisha_Streaming_SF.upk mitliefert. Die beiden anderen Namen bringen nichts: das Paket
# GD_Assassin_Skills existiert zwar von Anfang an, aber ohne die Gruppe .SkillTree darin, und
# load_package darauf laeuft folgenlos durch (kein Fehler, kein Objekt) - genau daran ist v0.28
# gescheitert. Der Zeitpunkt war NICHT das Problem: mit dem richtigen Namen steht die Kette schon
# beim Modulstart. Die Reihenfolge bleibt als Liste, falls ein anderer Charakter anders gepackt ist.
TREE_PACKAGES = ["GD_Assassin_Streaming_SF", "GD_Assassin_Streaming", "GD_Assassin_Skills"]

_skilltree_ready = False


def _load_tree_packages() -> bool:
    """Zer0s Vorlagen in den Speicher holen - Baumaeste UND Action Skill, beide liegen im selben
    Paket. Schreibt in den Log, welcher Paketname es war (beim Chronomaster GD_Assassin_Streaming_SF)."""

    def da() -> bool:
        return (_find("SkillTreeBranchDefinition", ROOT_BRANCH_TEMPLATE) is not None
                and _find("SkillDefinition", ACTION_SKILL_TEMPLATE) is not None)

    if da():
        return True
    for pkg in TREE_PACKAGES:
        try:
            unrealsdk.load_package(pkg)
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] load_package({pkg}): {ex}")
        if da():
            logging.info(f"[ZB] Vorlagen geladen ueber load_package({pkg})")
            return True
    return False


# Skill_Deception traegt elf SkillEffectDefinitions (Dump 2026-09-21), und die Kopie erbt sie alle.
# Gemessen v0.60: waehrend die Bombe liegt, steigt WeaponDamage fuenf Sekunden lang um +40 % der
# Basis je Sekunde (134 -> 178 bei Basis 22,17) - das ist Effekt 7, Decepti0ns Schadens-Ramp
# (Att_Deception_GunDamagePerStack x 5). Was bleibt und was geht:
#   0  Att_ActionSkillIsActive = 1        bleibt  (das Spiel fragt so "Action Skill laeuft?")
#   1  ActiveSkillCooldownConsumptionRate -1  bleibt  (Cooldown steht, solange der Skill laeuft)
#   2-5 Genauigkeit / Streuung             weg     (Zer0)
#   6  Nahkampf-Ramp  7  Waffenschaden-Ramp  8  Krit-Ramp   weg  (Decepti0n)
#   9  EnableWeaponFireSkillEvent          weg     (Zer0s "endet beim Schuss"-Verdrahtung)
#   10 AttributeToModify=None, Cooldown_Deception  bleibt  (modifiziert nichts; vermutlich Kartenanzeige)
# FALLE (v0.61, gemessen): "skill.SkillEffectDefinitions = [liste[0], liste[1], liste[10]]" setzt die
# Laenge auf 3, aber alle drei Eintraege sind danach LEER (AttributeToModify None) - und Effekt 1
# fehlte im Spiel (Cooldown lief waehrend des Skills mit: "verpufft: Cooldown 2.0s"). Eine Zuweisung
# an ein Struct-Array uebertraegt die Inhalte nicht. Deshalb elementweise neutralisieren (Attribut
# None, Werte 0 - so sieht Effekt 10 im Original ohnehin aus), die Laenge bleibt 11.
ACTION_EFFEKTE_WEG = (2, 3, 4, 5, 6, 7, 8, 9)


def _action_effekte_kuerzen(skill: UObject) -> None:
    try:
        liste = skill.SkillEffectDefinitions
        for i in ACTION_EFFEKTE_WEG:
            if i >= len(liste):
                continue
            e = liste[i]
            e.AttributeToModify = None
            e.BaseModifierValue.BaseValueConstant = 0.0
            e.BaseModifierValue.BaseValueAttribute = None
            e.PerGradeUpgrade.BaseValueConstant = 0.0
            e.PerGradeUpgrade.BaseValueAttribute = None
        namen = []
        for e in skill.SkillEffectDefinitions:
            a = e.AttributeToModify
            namen.append(a._path_name().rsplit(".", 1)[-1] if a is not None else "-")
        logging.info(f"[ZB] Action Skill: {len(namen)} Effekte, davon {len(ACTION_EFFEKTE_WEG)} neutralisiert: {namen}")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Action Skill: Effekte neutralisieren: {ex}")


def ensure_action_skill() -> UObject | None:
    """Phase 3, Schritt 2: die eigene Zeitbombe als Skillobjekt. Idempotent.
    Im Spiel bestaetigt (v0.33): Skillkarte zeigt "Zeitbombe", Fenster gemessen 19,99 / 20,00 s.

    Zwei Kopien, beide nach dem Rezept aus docs/skills.md, 6.2 (Spike D):
      Skill_Zeitbombe       (SkillDefinition)    - Name, Text, Fenster
      ActionSkill_Zeitbombe (ExecuteActionSkill) - der Kern; Nahkampf-Dash und Vision Mode aus

    Was hier bewusst NICHT sitzt, weil es ein anderer Mechanismus ist:
      - Unsichtbarkeit: haengt am Teil-Skill Skill_Stealth und kommt aus Zer0s BPDs - deshalb ein
        Hook mit Block (_on_activate_skill, Schritt 4), kein Feld an diesem Objekt.
      - Cooldown: eigene Pool-Kopie an der Klasse (ensure_cooldown_pool, Schritt 3).
      - "endet beim ersten Schuss" ist erledigt, ohne dass etwas zu tun war: im Test beendete ein
        Schuss das Fenster nicht (Zuenden nach 14,73 s belegt). Damit muss kein Array-Element
        geloescht werden - ein Fall, den Spike D nie abgedeckt hat.

    Schritt 5 (D9) ist seit v0.50 durch: am Anker liegt die Caesium-Ladung, Zer0s Hologramm, Klang
    und Daempfer sind abgehaengt. SKILL_TEXT beschreibt das seit v0.51 (Text ungetestet).
    """
    try:
        skill = _copy("SkillDefinition", ACTION_SKILL_TEMPLATE, ACTION_OUTER, f"Skill_{SKILL_OBJ}")
        kern = _copy("ExecuteActionSkill", ACTION_ARCHETYPE_TEMPLATE, ACTION_OUTER, f"ActionSkill_{SKILL_OBJ}")

        # Nahkampf-Dash aus (plan.md D2: "nativer Kern per bDisableExecuteAbility abschaltbar").
        # Das Feld wird gelesen zurueckgemeldet, damit der Log zeigt, ob es wirklich existiert.
        try:
            kern.bDisableExecuteAbility = True
            logging.info(f"[ZB] Action Skill: bDisableExecuteAbility = {kern.bDisableExecuteAbility}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Action Skill: bDisableExecuteAbility nicht setzbar: {ex}")

        # Zer0s Vision Mode abschalten: der blaue Schleier und die Gegner-Hervorhebung beim Einsatz.
        # Belegt im Datenpaket als vier Felder DIREKT am ExecuteActionSkill (nicht in der BPD) -
        # also an unserer eigenen Kopie aenderbar, ohne Zer0 anzufassen:
        #   VisionModeCoordinatedEffect = GD_CoordinatedEffects.CriticalEye  <- markiert die Gegner
        #   VisionModePostProcessChain  = FX_CHAR_Assassin.PostProcess.Ã¢â‚¬Â¦     <- der blaue Schleier
        #   VisionModeMaterial          = EngineMaterials.CubeMaterial
        # Jedes Feld wird zurueckgelesen, damit im Log steht, welches wirklich leer wurde.
        for feld in ("VisionModeCoordinatedEffect", "VisionModePostProcessChain", "VisionModeMaterial"):
            try:
                setattr(kern, feld, None)
                logging.info(f"[ZB] Action Skill: {feld} = {getattr(kern, feld)}")
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] Action Skill: {feld} nicht leerbar: {ex}")
        try:
            skill.SkillVisionModeCoordinatedEffect = None
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Action Skill: SkillVisionModeCoordinatedEffect: {ex}")

        skill.ActionSkillArchetype = kern
        skill.SkillName = SKILL_TITEL
        skill.SkillDescription = SKILL_TEXT
        skill.InitialDuration = FENSTER_SEKUNDEN
        _action_effekte_kuerzen(skill)

        logging.info(
            f"[ZB] Action Skill: {skill._path_name()} - Name '{skill.SkillName}', "
            f"Fenster {skill.InitialDuration}s, Kern {kern._path_name()}"
        )
        return skill
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Action Skill konnte nicht gebaut werden: {ex}")
        return None


def ensure_cooldown_pool(class_def: UObject) -> bool:
    """Eigene Cooldown-Pool-Definition mit 35 s, an unsere Klasse gehaengt. Idempotent.

    BaseValueAttribute wird auf None gesetzt, weil sonst das Attribut (15 s) die Konstante schlaegt.
    Cooldown-VERKUERZUNG durch Skills/Gear bleibt davon unberuehrt - die laeuft ueber die
    Verbrauchsrate (ActiveSkillCooldownConsumptionRate, siehe Bereitschaft in docs/skills.md),
    nicht ueber den Maximalwert.
    """
    try:
        pool = _copy("ResourcePoolDefinition", POOL_TEMPLATE, POOL_OUTER,
                     f"ActiveSkillCooldownPool_{CHARACTER_NAME}")
        pool.BaseMaxValue.BaseValueConstant = COOLDOWN_SEKUNDEN
        pool.BaseMaxValue.BaseValueAttribute = None
        class_def.SkillCooldownPoolDefinition = pool
        logging.info(
            f"[ZB] Cooldown-Pool: {pool._path_name()} - Max {pool.BaseMaxValue.BaseValueConstant}s"
            f" (Attribut {pool.BaseMaxValue.BaseValueAttribute})"
        )
        return True
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Cooldown-Pool konnte nicht gebaut werden: {ex}")
        return False


# ---------------------------------------------------------------------------
# Phase 4-6: die 36 Skills der drei Baeume (v0.52-v0.55, auf Nutzerwunsch alle auf einmal)
#
# Im Spiel bestaetigt (2026-09-20): alle 36 gebaut, Karten mit Text und Zahl, Weite gemessen
# (FootSpeed 440 -> 506), H+S-Kette mit Ausbruch/Stabilisator. Status je Skill: docs/skills.md, 8.
#
# Entwuerfe: docs/skills.md, Abschnitt 5. Rezept: 6.2 (Spike D). Jeder Skill ist eine Kopie eines
# Zer0-Skills - NUR Zer0s Objekte sind beim Chronomaster sicher geladen (GD_Assassin_Streaming_SF);
# die Praesentationen anderer Klassen (Axton hat eine fuer Magazingroesse) sind es nicht.
#
# Vier Bauarten (Spalte "Kl." in docs/skills.md):
#   H     Stat-Skill: die Effekte sitzen am Baum-Skill selbst, das Spiel wertet sie aus.
#   KILL  Kill Skill: wie H, aber Vorlage Killer (SKILL_TYPE_Kill) - das Spiel loest ihn beim Kill aus.
#   HS    Bedingter Skill nach Zer0s Muster CriticalAscention + CriticalAscention_Stack: der sichtbare
#         Baum-Skill traegt Name, Text und Rang, aber KEINEN Effekt. Daneben ein unsichtbarer
#         Effekt-Skill "<Name>_Wirkung", den das Modul mit dem Rang des Spielers schaltet
#         (skill_an/skill_aus, Spike E). Zeitlich begrenzte (Nachwirkung 8 s, Ausbruch 3 s, ...)
#         haben Skill_Speed als Vorlage (DURATION_Timed) und laufen von selbst ab.
#   S     Platzhalter: Baum-Skill ohne Effekt, der Text sagt ehrlich "noch ohne Wirkung".
#
# Praesentationen (die Zahl auf der Karte) sind eigene Kopien je Effekt, Attribut und Text gesetzt.
# Zwei Vorlagen: Headsh0t fuer positive Werte, Killer(Nachladen) fuer negative - die traegt
# SIGNSTYLE_Positive, damit -15 % Nachladezeit als "+15 %" erscheint (Dump 2026-09-20).
#
# Vorlagen nach Effektzahl, weil Struct-Arrays per SDK nur GEKUERZT werden (Spike D: Element
# beschreiben und ganzes Array setzen sind belegt, Anhaengen nicht): Headsh0t 1, FastHands 2,
# Precisi0n 4 Effekte. Deshalb deckt "Stabilisator" vier statt fuenf Schadensquellen ab.
# ---------------------------------------------------------------------------

# Attribute (alle in docs/skills.md, Abschnitt 2, am Datenpaket verifiziert)
A_KRIT = "D_Attributes.GameplayAttributes.PlayerCriticalHitBonus"
A_MAGAZIN = "D_Attributes.Weapon.WeaponClipSize"
A_SCHADEN = "D_Attributes.Weapon.WeaponDamage"
A_FEUERRATE = "D_Attributes.Weapon.WeaponFireInterval"          # negativ = schneller
A_NACHLADEN = "D_Attributes.Weapon.WeaponReloadSpeed"           # negativ = schneller
A_TEMPO = "D_Attributes.GameplayAttributes.FootSpeed"
A_ZOOM = "D_Attributes.Weapon.WeaponZoomEndFOV"                  # negativ = schneller
A_STREUUNG = "D_Attributes.Weapon.WeaponSpread"                  # negativ = genauer
A_PROJEKTIL = "D_Attributes.Weapon.WeaponProjectileSpeedMultiplier"
A_HINTERHALT = "D_Attributes.DamageEnhancementModifiers.PlayerAttackUnsuspectingTargetModifier"
A_COOLDOWN = "D_Attributes.ActiveSkillCooldownResource.ActiveSkillCooldownConsumptionRate"
A_SCHILDREGEN = "D_Attributes.ShieldResourcePool.ShieldPassiveRegenerationRate"
A_RESIST = (
    "D_Attributes.DamageSourceModifiers.ReceivedBulletDamageModifier",
    "D_Attributes.DamageSourceModifiers.ReceivedMeleeDamageModifier",
    "D_Attributes.DamageSourceModifiers.ReceivedGrenadeDamageModifier",
    "D_Attributes.DamageSourceModifiers.ReceivedRocketDamageModifier",
)

VORLAGE_PASSIV = {1: "GD_Assassin_Skills.Sniping.HeadShot", 2: "GD_Assassin_Skills.Cunning.FastHands",
                  4: "GD_Assassin_Skills.Sniping.Precision"}
VORLAGE_KILL = "GD_Assassin_Skills.Sniping.Killer"            # SKILL_TYPE_Kill, 2 Effekte
VORLAGE_TIMED = "GD_Assassin_Skills.ActionSkill.Skill_Speed"  # DURATION_Timed, 1 Effekt, keine Constraints
PRAES_POSITIV = "GD_Assassin_Skills.Sniping.HeadShot:AttributePresentationDefinition_2"
PRAES_NEGATIV = "GD_Assassin_Skills.Sniping.Killer:AttributePresentationDefinition_4"
WIRKUNG_MAXGRADE = 100000  # Effekt-Skills: Stacks ueber den Rang hinaus (v1.13: Kill-Stacks unbegrenzt, Grad = Rang x Stacks)


@dataclass(frozen=True)
class Effekt:
    attribut: str
    je_rang: float       # BaseValueConstant = PerGradeUpgrade (linear, wie bei Zer0)
    text: str            # Praesentation; $NUMBER$ ist die Zahl
    dezimal: bool = False  # Prozent mit Nachkommastelle zeigen (1,5 %)


@dataclass(frozen=True)
class Skill:
    name: str            # Objektname - eindeutig, ohne Sonderzeichen
    titel: str           # SkillName auf der Karte (ohne Umlaute)
    text: str            # SkillDescription
    rang: int            # MaxGrade
    art: str             # "H" | "KILL" | "HS" | "S" | "KS" (v1.14: Kill-Stack - Kill-Vorlage fuers Symbol + Stack-Wirkung mit HUD)
    effekte: tuple = ()  # Effekt-Tupel; bei HS die des versteckten Effekt-Skills
    dauer: float = 0.0   # HS: Sekunden, nach denen der Effekt-Skill von selbst ablaeuft (0 = Modul schaltet)
    offen: str = ""      # was das Modul noch nicht kann - landet als Hinweis im Text


def _S(*a, **k) -> Skill:  # noqa: N802 - kurz, damit die Tabelle lesbar bleibt
    return Skill(*a, **k)


# v1.14/v1.18: HUD-Plaetze der Stack-Skills unter der XP-Leiste (Zer0 nutzt 2 und 3 - er ist hier nicht
# Wirt; Axton nutzt Plaetze bis 9, also gibt es mindestens so viele)
HUD_SLOT = {"DejaVu": 1, "Wiederholung": 2, "Vorstoss": 3, "GespannteZeit": 4, "Wiederkehr": 5, "Abstand": 6}
KS_TRACK_VORBILD = "GD_Assassin_Skills.Sniping.KillConfirmed_Stack"   # TRACKEDSKILL_Respond (Dump)
# v1.13: gemeinsamer Satz der drei Kill Skills (ein Stack-Zaehler fuer alle, s. "Kill-Stacks")
KILLSTACK_TEXT = "Each kill grants a stack, with no limit (shared by all Kill Skills); starting 3 seconds after your last kill, one stack decays every second."

# Die Tabellen. Reihenfolge = Tier 1..6, innen links nach rechts. Werte aus docs/skills.md, 5.
BAUM_VERGANGENHEIT = [
    [_S("Gedaechtnis", "Memory", "Increases [skill]Critical Hit Damage[-skill] and [skill]Magazine Size[-skill].", 5, "H",
        (Effekt(A_KRIT, 0.04, "Critical Hit Damage: $NUMBER$"), Effekt(A_MAGAZIN, 0.05, "Magazine Size: $NUMBER$"))),
     _S("Nachwirkung", "Aftermath", "After you [skill]detonate[-skill], gain more [skill]Weapon Damage[-skill] for 8 seconds: +4% per rank.", 5, "HS",
        (Effekt(A_SCHADEN, 0.04, "Weapon Damage: $NUMBER$"),), dauer=8.0)],
    [_S("GespannteZeit", "Tension", "While the bomb is out, gain a stack every second (max 10). Each stack: +1% [skill]Weapon Damage[-skill] per rank.", 5, "HS",
        (Effekt(A_SCHADEN, 0.01, "Weapon Damage: $NUMBER$"),)),
     # v1.13 (Nutzerwunsch): die drei Kill Skills stapeln unbegrenzt - Bauart HS, das Modul setzt
     # Grad = Rang x Kill-Stacks (s. "Kill-Stacks"). Negative Scale-Summen teilen (v0.99), also waechst
     # das TEMPO linear: 100 Stacks x R5 x 0,002 = Summe -1,0 = doppeltes Tempo.
     _S("DejaVu", "Deja Vu", "[skill]Kill Skill[-skill]. " + KILLSTACK_TEXT + " +0.2% [skill]Fire Rate[-skill] and [skill]Reload Speed[-skill] per stack and rank. Detonating holds your stacks: the decay starts over.", 5, "KS",
        (Effekt(A_FEUERRATE, -0.002, "Fire Rate: $NUMBER$"), Effekt(A_NACHLADEN, -0.002, "Reload Speed: $NUMBER$")))],
    [_S("Vorbelastung", "Prior Record", "Enemies you hit while the bomb is out are marked: for 8 seconds after you detonate, they take +5% damage from you per rank.", 5, "S"),
     _S("Wiederholung", "Encore", "[skill]Kill Skill[-skill]. " + KILLSTACK_TEXT + " +0.4% [skill]Critical Hit Damage[-skill] per stack and rank.", 5, "KS",
        (Effekt(A_KRIT, 0.004, "Critical Hit Damage: $NUMBER$"),)),
     _S("Nachhall", "Reverberation", "Detonating releases a shockwave where you arrive: enemies within 6 meters take [skill]Shock Damage[-skill] equal to twice your grenade damage and are staggered.", 1, "S")],
    [_S("Erinnerung", "Recollection", "The anchor saves your active Kill Skills and their stacks. When you detonate, they come back.", 1, "S"),
     _S("Wiederkehr", "Recurrence", "After you detonate: for each kill you made while the bomb was out, +2% [skill]Weapon Damage[-skill] per rank for 10 seconds (max 10).", 5, "HS",
        (Effekt(A_SCHADEN, 0.02, "Weapon Damage: $NUMBER$"),), dauer=10.0)],
    [_S("Langzeitgedaechtnis", "Long-Term Memory", "The Time Bomb window lasts 2 seconds longer per rank, and while the bomb is out you gain +4% [skill]Critical Hit Damage[-skill] per rank.", 5, "HS",
        (Effekt(A_KRIT, 0.04, "Critical Hit Damage: $NUMBER$"),)),
     _S("Zeitspur", "Time Vortex", "While the bomb is out, a time vortex erupts at the anchor every 2 seconds if enemies are within 8 meters: [skill]Shock Damage[-skill] equal to your grenade damage.", 1, "S")],
    [_S("Paradoxon", "Paradox", "When you detonate, all damage you dealt while the bomb was out hits the same enemies again - at half strength.", 1, "S")],
]

BAUM_RUECKKEHR = [
    [_S("Auffrischung", "Refresh", "Detonating also restores [skill]Health[-skill] and [skill]Shield[-skill]: +4% of maximum per rank, beyond the anchor values.", 5, "HS"),
     _S("Bereitschaft", "Standby", "Increases [skill]Cooldown Rate[-skill] and [skill]Shield Recharge Rate[-skill].", 5, "H",
        (Effekt(A_COOLDOWN, 0.02, "Cooldown Rate: $NUMBER$"), Effekt(A_SCHILDREGEN, 0.015, "Shield Recharge Rate: $NUMBER$", dezimal=True)))],
    [_S("VolleRueckerstattung", "Full Refund", "Detonating refunds 20% per rank of the ammo reserve you have used since throwing the bomb.", 5, "S"),
     _S("Stabilisator", "Stabilizer", "While the bomb is out, you take 2% less damage per rank from bullets, melee, grenades and rockets.", 5, "HS",
        tuple(Effekt(a, -0.02, "Damage Resistance: $NUMBER$") for a in A_RESIST))],
    [_S("Reinigung", "Cleanse", "Detonating removes all status effects. 2 seconds of damage immunity after you arrive.", 1, "S"),
     _S("ZweiteMeinung", "Second Opinion", "Allies near the anchor gain shield when you detonate: +6% of their maximum per rank.", 5, "S"),
     _S("Zeitkapsel", "Time Capsule", "A hologram of you also appears at the anchor. It draws enemy fire and regenerates health for allies within 8 meters.", 5, "S")],
    [_S("EsWarNiePassiert", "It Never Happened", "If you fall into Fight for Your Life while a bomb is out, it detonates on its own.", 1, "S"),
     _S("Nachbild", "Afterimage", "When you detonate, an afterimage stays behind where you left and draws enemy fire: 2 seconds + 1 per rank.", 5, "S")],
    [_S("Sprengsatz", "Parting Gift", "When you detonate, you leave a massive explosion behind - in your grenade's element, 5x your grenade damage.", 1, "S"),
     _S("GemeinsameRueckkehr", "Homecoming", "Allies near where you arrive are healed: +5% of their maximum per rank.", 5, "S")],
    [_S("Schattenanker", "Shadow Anchor", "Even without a bomb out, the skill keeps remembering an anchor from 5 seconds ago. Hold the key for a shadow detonation (1.5x cooldown).", 1, "S")],
]

BAUM_AUSFLUG = [
    [_S("Weite", "Open Road", "Increases [skill]Movement Speed[-skill] and [skill]Aim Speed[-skill].", 5, "H",
        (Effekt(A_TEMPO, 0.03, "Movement Speed: $NUMBER$"), Effekt(A_ZOOM, -0.02, "Aim Speed: $NUMBER$"))),
     _S("Abstand", "Distance", "+2% [skill]Weapon Damage[-skill] per rank for every 10 meters between you and the anchor (max 5 stages).", 5, "HS",
        (Effekt(A_SCHADEN, 0.02, "Weapon Damage: $NUMBER$"),))],
    [_S("Vorstoss", "Push Forward", "[skill]Kill Skill[-skill]. " + KILLSTACK_TEXT + " +0.2% [skill]Movement Speed[-skill] and [skill]Reload Speed[-skill] per stack and rank.", 5, "KS",
        (Effekt(A_TEMPO, 0.002, "Movement Speed: $NUMBER$"), Effekt(A_NACHLADEN, -0.002, "Reload Speed: $NUMBER$"))),
     _S("SichererAbstand", "Safe Distance", "More than 15 meters from the anchor, you take 2% less damage per rank from bullets, melee, grenades and rockets.", 5, "HS",
        tuple(Effekt(a, -0.02, "Damage Resistance: $NUMBER$") for a in A_RESIST))],
    [_S("Ausbruch", "Breakout", "Throwing the bomb gives you +50% [skill]Movement Speed[-skill] for 3 seconds.", 1, "HS",
        (Effekt(A_TEMPO, 0.50, "Movement Speed: $NUMBER$"),), dauer=3.0),
     _S("Hinterhalt", "Ambush", "Increases damage against enemies that are not targeting you.", 5, "H",
        (Effekt(A_HINTERHALT, 0.04, "Damage vs. Unaware Enemies: $NUMBER$"),)),
     _S("Weitschuss", "Long Shot", "Increases [skill]Accuracy[-skill] and [skill]Projectile Speed[-skill].", 5, "H",
        (Effekt(A_STREUUNG, -0.04, "Spread: $NUMBER$"), Effekt(A_PROJEKTIL, 0.15, "Projectile Speed: $NUMBER$")))],
    [_S("KursHalten", "Stay the Course", "Each kill while the bomb is out extends the window by 1 second per rank.", 5, "S"),
     # v0.97 (Nutzerwunsch): statt Explosion (doppelte Sprengsatz) ein Buff nach Sprungweite. Wirkung:
     # Grad g -> Intervall x (1 - 0,01 g); mechanik_ruecksprung_detonation rechnet den Grad aus dem
     # gewuenschten Tempobonus um (+100 % Tempo = halbes Intervall = Grad 50).
     _S("RuecksprungDetonation", "Tailwind", "After you [skill]detonate[-skill], gain more [skill]Fire Rate[-skill] and [skill]Reload Speed[-skill] for 10 seconds - the farther you were from the anchor, the more: up to +20% per rank (full effect at 50 meters).", 5, "HS",
        # dauer=0: die Timed-Vorlage Skill_Speed hat nur 1 Effekt, verlaengern geht nicht (v0.52) -
        # also passive Vorlage mit 2 Effekten, und das Modul schaltet nach 10 s ab (_wirkung_uhren).
        (Effekt(A_FEUERRATE, -0.01, "Fire Rate: $NUMBER$"), Effekt(A_NACHLADEN, -0.01, "Reload Speed: $NUMBER$")))],
    [_S("Grenzgaenger", "Borderlander", "More than 30 meters from the anchor: +3% [skill]Fire Rate[-skill] and +4% [skill]Magazine Size[-skill] per rank.", 5, "HS",
        (Effekt(A_FEUERRATE, -0.03, "Fire Rate: $NUMBER$"), Effekt(A_MAGAZIN, 0.04, "Magazine Size: $NUMBER$"))),
     _S("KeinZurueck", "Point of No Return", "If the bomb expires unused: +25% [skill]Weapon Damage[-skill] for 10 seconds, and no cooldown at all.", 1, "HS",
        (Effekt(A_SCHADEN, 0.25, "Weapon Damage: $NUMBER$"),), dauer=10.0)],
    [_S("Zeitsprung", "Time Skip", "When you detonate, all enemies on the line between you and the anchor are damaged and staggered. 1 second of invulnerability after you arrive.", 1, "S")],
]

# (Tabelle, Outer-Paket fuer die Objekte - Zer0s Gruppen, weil sie sicher existieren)
BAEUME = [
    (BAUM_VERGANGENHEIT, "GD_Assassin_Skills.Sniping"),
    (BAUM_RUECKKEHR, "GD_Assassin_Skills.Cunning"),
    (BAUM_AUSFLUG, "GD_Assassin_Skills.Bloodshed"),
]
SKILL_OUTER: dict[str, str] = {sk.name: outer for tabelle, outer in BAEUME for tier in tabelle for sk in tier}
PLATZHALTER_HINWEIS = " [Not functional yet - mechanic coming.]"

# S-Skills, die seit Handgriff 4 eine Mechanik haben (v0.87). Ohne Eintrag hier traegt die Karte
# weiter den Platzhalter-Hinweis. Der Wert sagt, was noch fehlt - leer heisst vollstaendig, und
# dann steht auch nichts auf der Karte. Spieltext, also ohne Umlaute.
S_GEBAUT: dict[str, str] = {
    "Erinnerung": "",
    "VolleRueckerstattung": "",
    "Paradoxon": "",
    "Vorbelastung": "",
    "Zeitsprung": "",                                        # v1.12 Immunitaet ueber ZB_Immun_A/B
    "Reinigung": "",                                         # v1.12 Immunitaet ueber ZB_Immun_A/B
    "Nachhall": "",                                          # v1.13 Schockwelle statt Rueckstoss
    "Zeitspur": "",                                          # v1.05 Zeitwirbel statt Verlangsamung (Spike A)
    "EsWarNiePassiert": "",                                  # v0.90, gemessen
    "KursHalten": "",                                        # v0.90, gemessen
    "Nachbild": "",                                          # v0.93, bestaetigt (Screenshot, 7 s), Leiche wird versteckt
    "Sprengsatz": "",                                        # v0.94 neu: Behavior_Explode beim Zuenden, ungetestet
    "Zeitkapsel": "",                                        # v0.95 Heilung gebaut, nur mit 'zb koop selbst' pruefbar
    "ZweiteMeinung": "",                                     # v0.95, Koop - VERMUTUNG: wirkt nur als Gastgeber
    "GemeinsameRueckkehr": "",                               # v0.95, Koop - wie Zweite Meinung
    "Schattenanker": "",                                     # v0.95, Ringpuffer + Halten ueber InputKey, ungetestet
}


# v1.37: Icons je Baum-Skill (Nutzerwahl 2026-09-27, Platzhalter bis eigene Icons gehen). Klasse ->
# ICON_KLASSEN (Paket + Gruppe), Bilder: docs/icon-katalog.md. Der Skillbaum liest SkillIcon live (v1.36).
SKILL_ICONS: dict[str, tuple[str, str]] = {
    # HINDSIGHT
    "Gedaechtnis": ("gaige", "SkillIcon-Mechro05"),            # Gehirn
    "Nachwirkung": ("axton", "SkillIcon-Impact"),              # gesplittertes Glas
    "GespannteZeit": ("salvador", "SkillIcon-ImReadyAlready"),  # Wecker
    "DejaVu": ("maya", "SkillIcon-ThoughtLock"),               # Totenkoepfe in Spirale
    "Vorbelastung": ("zer0", "SkillIcon-KillConfirmed"),       # Fadenkreuz auf Figur
    "Wiederholung": ("maya", "SkillIcon-Recompense"),          # Rose
    "Nachhall": ("axton", "SkillIcon-LaserSight"),             # Lichtblitz
    "Erinnerung": ("axton", "SkillIcon-DutyCalls"),            # Hundemarken
    "Wiederkehr": ("maya", "SkillIcon-Stagnant"),              # Kreispfeile
    "Langzeitgedaechtnis": ("salvador", "SkillIcon-LastLonger"),
    "Zeitspur": ("maya", "SkillIcon-Scorn"),                   # Wirbel
    "Paradoxon": ("maya", "SkillIcon-MindsEye"),               # Auge in Pyramide
    # REWIND
    "Auffrischung": ("axton", "Skillicon-willing"),            # Schild mit Kreispfeil
    "Bereitschaft": ("axton", "SkillIcon-Ready"),              # Ampel
    "VolleRueckerstattung": ("salvador", "SkillIcon-MoneyShot"),  # Muenzen
    "Stabilisator": ("salvador", "SkillIcon-SteadyAsSheGoes"),  # Sextant
    "Reinigung": ("axton", "SkillIcon-Forbearance"),           # Feuerloescher
    "ZweiteMeinung": ("gaige", "SkillIcon-Mechro25"),          # zwei Schilde
    "Zeitkapsel": ("maya", "SkillIcon-Sphere"),                # Blasen
    "EsWarNiePassiert": ("maya", "SkillIcon-Res"),             # Feder
    "Nachbild": ("zer0", "SkillIcon-Unforseen"),               # Hologramm-Explosion
    "Sprengsatz": ("krieg", "SkillIcon-Psycho18"),             # Dynamit mit Uhr
    "GemeinsameRueckkehr": ("maya", "SkillIcon-Restoration"),  # Taube
    "Schattenanker": ("zer0", "SkillIcon-LikeTheWind"),        # Pixel-Wirbelsturm
    # DETOUR
    "Weite": ("salvador", "SkillIcon-Incite"),                 # Stiefel mit Fluegel
    "Abstand": ("zer0", "SkillIcon-Squint"),                   # Fernglas
    "Vorstoss": ("axton", "SkillIcon-Steady"),                 # Widder
    "SichererAbstand": ("axton", "SkillIcon-Preparation"),     # Schild
    "Ausbruch": ("maya", "SkillIcon-Fleet"),                   # Hase
    "Hinterhalt": ("zer0", "SkillIcon-Backstab"),              # Ninja mit Dolch
    "Weitschuss": ("maya", "SkillIcon-Accelerate"),            # Kugel mit Tempolinien
    "KursHalten": ("salvador", "SkillIcon-Yippekiyay"),        # Cowboy-Totenkopf
    "RuecksprungDetonation": ("zer0", "Skillicon-velocity"),   # Kugel mit Tempolinien
    "Grenzgaenger": ("axton", "SkillIcon-Ranger"),             # Gewehr mit Sternen
    "KeinZurueck": ("axton", "SkillIcon-DoOrDie"),             # Helm mit Totenkopf
    "Zeitsprung": ("maya", "SkillIcon-Subsequence"),           # Komet mit Einschlag
}
_icon_pakete_geladen: set[str] = set()
_icons_offen: set[str] = set()   # beim Bauen nicht gefunden -> icons_nachholen (v1.38)


def _skill_icon(name: str) -> UObject | None:
    """Das gewaehlte Icon eines Baum-Skills holen; das Klassenpaket wird einmal nachgeladen.
    Fehlt es, bleibt das Vorlagen-Icon (Aufrufer setzt nur bei Treffer)."""
    wahl = SKILL_ICONS.get(name)
    if wahl is None:
        return None
    paket, gruppe = ICON_KLASSEN[wahl[0]]
    icon = _find("SwfMovie", f"{gruppe}.{wahl[1]}")
    if icon is None and paket not in _icon_pakete_geladen:
        _icon_pakete_geladen.add(paket)
        try:
            unrealsdk.load_package(paket)
            logging.info(f"[ZB] Icons: load_package({paket})")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Icons: load_package({paket}): {ex}")
        icon = _find("SwfMovie", f"{gruppe}.{wahl[1]}")
    if icon is None:
        # v1.38: beim Modulstart sind die DLC-Pakete (Gaige, Krieg) noch nicht eingebunden - load_package
        # laeuft ohne Fehler, findet aber nichts (Log v1.37). Nachgeholt im Charakter-Menue.
        _icons_offen.add(name)
        logging.info(f"[ZB] Icon noch nicht da: {name} -> {gruppe}.{wahl[1]} (wird im Charakter-Menue nachgeholt)")
    return icon


def icons_nachholen(wo: str) -> None:
    """Icons, die beim Modulstart fehlten, erneut suchen - auch am HUD-Stack-Skill (_Wirkung)."""
    if not _icons_offen:
        return
    for name in sorted(_icons_offen):
        paket = ICON_KLASSEN[SKILL_ICONS[name][0]][0]
        _icon_pakete_geladen.discard(paket)   # erneut laden erlauben
        _icons_offen.discard(name)
        icon = _skill_icon(name)
        if icon is None:
            continue
        for pfad in (f"{SKILL_OUTER[name]}.{name}", f"{SKILL_OUTER[name]}.{name}_Wirkung"):
            obj = _find("SkillDefinition", pfad)
            if obj is not None:
                obj.SkillIcon = icon
        logging.info(f"[ZB] Icon nachgeholt ({wo}): {name} -> {icon._path_name()}")
    if _icons_offen:
        logging.error(f"[ZB] Icons fehlen weiter ({wo}): {sorted(_icons_offen)}")


# v1.39: Die Menue-Hooks (v1.38) feuern bei "Weiter" nicht (Log: keine Zeile). Im laufenden Spiel ging
# das Laden der DLC-Icons (v1.36) - also dort nachholen: 2 s nach dem ersten Tick, hoechstens 3 Versuche
# im Abstand von 5 s, damit kein load_package pro Frame laeuft.
_icons_takt = -2.0
_icons_versuche = 0


def _icons_tick(pc: UObject, dt: float) -> None:
    global _icons_takt, _icons_versuche
    if _icons_versuche >= 3:
        return
    # v1.40: PlayerTick laeuft schon im Hauptmenue/Ladebildschirm - dort scheiterten Versuch 1 und 2,
    # erst Versuch 3 traf (Log v1.39). Also erst zaehlen, wenn eine Spielfigur steht.
    if pc.Pawn is None:
        return
    _icons_takt += dt
    if _icons_takt < 0.0:
        return
    _icons_takt = -5.0
    _icons_versuche += 1
    icons_nachholen(f"im Spiel, Versuch {_icons_versuche}")


def _attr(pfad: str) -> UObject | None:
    """AttributeDefinition holen. Einige sind ResourcePoolAttributeDefinition (Accuracy*, Health*,
    Shield*) - find_object prueft die Klasse, deshalb beide Namen probieren."""
    for cls in ("AttributeDefinition", "ResourcePoolAttributeDefinition"):
        obj = _find(cls, pfad)
        if obj is not None:
            return obj
    logging.error(f"[ZB] Attribut nicht geladen: {pfad}")
    return None


def _vorlage(art: str, n: int, dauer: float) -> str:
    if art in ("KILL", "KS"):   # KS (v1.14): Kill-Symbol auf der Karte behalten
        return VORLAGE_KILL
    if dauer > 0:
        return VORLAGE_TIMED
    for k in sorted(VORLAGE_PASSIV):
        if k >= n:
            return VORLAGE_PASSIV[k]
    raise ValueError(f"keine Vorlage fuer {n} Effekte")


def _effekte_setzen(obj: UObject, effekte: tuple, outer: str, name: str, mit_praesentation: bool) -> None:
    """SkillEffectDefinitions auf genau diese Effekte bringen (Element fuer Element beschreiben -
    Spike D) und je Effekt eine eigene Praesentation anlegen.

    Ueberzaehlige Effekte der Vorlage werden NICHT mehr per Zuweisung abgeschnitten (bis v0.61:
    obj.SkillEffectDefinitions = liste[:n]) - eine Zuweisung an ein Struct-Array verliert die
    Inhalte (gemessen v0.61 am Action Skill: alle Eintraege danach ohne Attribut). Stattdessen
    werden sie neutralisiert (Attribut None, Werte 0); die Laenge bleibt. Betroffen war bisher nur
    Wiederholung (Vorlage Killer: 2 Effekte, gebraucht 1) - nachmessen."""
    liste = obj.SkillEffectDefinitions
    if len(liste) < len(effekte):
        logging.error(f"[ZB] {name}: Vorlage hat {len(liste)} Effekte, gebraucht {len(effekte)} - Rest entfaellt")
        effekte = effekte[:len(liste)]
    for i in range(len(effekte), len(liste)):
        try:
            e = liste[i]
            e.AttributeToModify = None
            e.BaseModifierValue.BaseValueConstant = 0.0
            e.BaseModifierValue.BaseValueAttribute = None
            e.PerGradeUpgrade.BaseValueConstant = 0.0
            e.PerGradeUpgrade.BaseValueAttribute = None
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] {name}: Effekt {i} neutralisieren: {ex}")
    praes = []
    for i, e in enumerate(effekte):
        attr = _attr(e.attribut)
        if attr is None:
            continue
        try:
            sed = obj.SkillEffectDefinitions[i]
            sed.AttributeToModify = attr
            sed.BaseModifierValue.BaseValueConstant = e.je_rang
            sed.BaseModifierValue.BaseValueAttribute = None
            sed.PerGradeUpgrade.BaseValueConstant = e.je_rang
            sed.PerGradeUpgrade.BaseValueAttribute = None
            # v0.67: Skill_Speed (Vorlage der Timed-Skills) hat GradeToStartApplyingEffect=0, die passiven
            # Vorlagen 1. Mit 0 rechnet das Spiel Base + jeGrad x Grad statt x (Grad-1) - Wiederkehr gab
            # +32 % statt +30 % (gemessen), Ausbruch +100 % statt +50 %. Darum fuer jede Kopie fest 1.
            sed.GradeToStartApplyingEffect = 1
            sed.PerGradeUpgradeInterval = 1
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] {name}: Effekt {i} ({e.attribut}): {ex}")
            continue
        if mit_praesentation:
            try:
                p = _copy("AttributePresentationDefinition", PRAES_NEGATIV if e.je_rang < 0 else PRAES_POSITIV,
                          outer, f"{name}_P{i}")
                p.Attribute = attr
                p.Description = e.text
                p.bDisplayPercentAsFloat = e.dezimal
                praes.append(p)
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] {name}: Praesentation {i}: {ex}")
    if mit_praesentation:
        try:
            obj.SkillEffectPresentations = praes
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] {name}: Praesentationen setzen: {ex}")


def _skill_bauen(sk: Skill, outer: str) -> UObject | None:
    """Einen Baum-Skill (und bei HS seinen Effekt-Skill) als Laufzeit-Kopie anlegen. Idempotent."""
    sichtbar = sk.effekte if sk.art in ("H", "KILL") else ()
    text = sk.text
    if sk.art == "S" and sk.name in S_GEBAUT:
        if S_GEBAUT[sk.name]:
            text += f" [Not functional yet: {S_GEBAUT[sk.name]}.]"
    elif sk.art == "S":
        text += PLATZHALTER_HINWEIS
    elif sk.offen:
        text += f" [Not functional yet: {sk.offen}.]"
    try:
        obj = _copy("SkillDefinition", _vorlage(sk.art, len(sichtbar), 0.0), outer, sk.name)
        obj.SkillName = sk.titel
        obj.SkillDescription = text
        obj.MaxGrade = sk.rang
        icon = _skill_icon(sk.name)   # v1.37 - vor der HUD-Kopie unten (wirk.SkillIcon = obj.SkillIcon)
        if icon is not None:
            obj.SkillIcon = icon
        _effekte_setzen(obj, sichtbar, outer, sk.name, mit_praesentation=True)
        if sk.art in ("HS", "KS") and sk.effekte:
            wirk = _copy("SkillDefinition", _vorlage("HS", len(sk.effekte), sk.dauer), outer, f"{sk.name}_Wirkung")
            wirk.SkillName = f"{sk.titel} (Effect)" if sk.art == "HS" else sk.titel
            wirk.SkillDescription = ""
            wirk.MaxGrade = WIRKUNG_MAXGRADE
            if sk.dauer > 0:
                wirk.InitialDuration = sk.dauer
            _effekte_setzen(wirk, sk.effekte, outer, f"{sk.name}_Wirkung", mit_praesentation=False)
            if sk.name in HUD_SLOT:
                # v1.14/v1.18: Stack-Anzeige unter der XP-Leiste - Muster Zer0s Kill Confirmed (Dump):
                # Baum-Skill.TrackedActiveSkills -> Stack-Skill mit TrackedSkillHUDSlot und SkillIcon;
                # das HUD zaehlt dessen INSTANZEN (v1.16 gemessen), s. stapel_setzen.
                try:
                    wirk.SkillIcon = obj.SkillIcon
                    wirk.TrackedSkillHUDSlot = HUD_SLOT[sk.name]
                    obj.TrackedActiveSkills = [wirk]
                    # v1.15: Symbol ohne Zahl (v1.14). Zer0s Stack-Skills MIT Zahl: Stack-Skill
                    # TRACKEDSKILL_Respond, Baum-Skill Untracked (Dump). Unsere Kill-Vorlage macht den
                    # Baum-Skill zu TRACKEDSKILL_Kill (nur Symbol). Enum-Werte von den Originalen kopiert.
                    respond = _find("SkillDefinition", KS_TRACK_VORBILD)
                    untracked = _find("SkillDefinition", VORLAGE_PASSIV[1])
                    if respond is not None and untracked is not None:
                        wirk.TrackedSkillType = respond.TrackedSkillType
                        obj.TrackedSkillType = untracked.TrackedSkillType
                        logging.info(f"[ZB] {sk.name}: HUD Slot {wirk.TrackedSkillHUDSlot}, Stack-Skill {wirk.TrackedSkillType},"
                                     f" Baum-Skill {obj.TrackedSkillType}")
                    else:
                        logging.error(f"[ZB] {sk.name}: Vorbild {KS_TRACK_VORBILD} nicht geladen - keine Stackzahl")
                except Exception as ex:  # noqa: BLE001
                    logging.error(f"[ZB] {sk.name}: HUD-Anzeige: {ex}")
        return obj
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Skill {sk.name}: {ex}")
        return None


# Zer0s Aeste haben 2-2-3-1-1-1 = 10 Skills, und welche Zelle des 3x6-Rasters ein Kaestchen bekommt,
# sagt ein eigenes Layout-Objekt (Dump: Layout_Sniping, Tiers(n).bCellIsOccupied = 3 Bools). Unser
# Layout 2-2-3-2-2-1 braucht in Tier 4 und 5 die Aussenzellen - Test v0.52: der zweite Skill dort
# war unsichtbar. Deshalb eine eigene Layout-Kopie fuer alle drei Aeste (v0.53).
LAYOUT_TEMPLATE = f"{TREE_OUTER}.Layout_Sniping"
LAYOUT_ZELLEN = {1: (False, True, False), 2: (True, False, True), 3: (True, True, True)}


def _layout_bauen(tabelle: list) -> UObject | None:
    """Ein Layout passend zur Tabelle: je Tier so viele Zellen belegt, wie Skills da sind."""
    try:
        layout = _copy("SkillTreeBranchLayoutDefinition", LAYOUT_TEMPLATE, TREE_OUTER, f"Layout_{CHARACTER_NAME}")
        for t, tier_skills in enumerate(tabelle):
            zellen = LAYOUT_ZELLEN[len(tier_skills)]
            tier = layout.Tiers[t]
            try:
                for i, b in enumerate(zellen):
                    tier.bCellIsOccupied[i] = b
            except Exception as ex:  # noqa: BLE001
                logging.info(f"[ZB] Layout Tier {t + 1}: elementweise nicht ({ex}), ganz setzen")
                tier.bCellIsOccupied = list(zellen)
        belegung = [tuple(bool(b) for b in tier.bCellIsOccupied) for tier in layout.Tiers]
        logging.info(f"[ZB] Layout: {belegung}")
        return layout
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Layout: {ex}")
        return None


def _baeume_fuellen(aeste: list) -> None:
    """Die drei Aeste mit unseren Skills belegen: je Tier das Skills-Array ganz setzen (Objekt-Arrays
    sind per SDK ganz setzbar, Spike D Runde 3). Zer0s Skills fallen dabei aus unseren Kopien heraus."""
    layout = _layout_bauen(BAUM_VERGANGENHEIT)  # alle drei Tabellen haben dasselbe Raster
    for ast, (tabelle, outer) in zip(aeste, BAEUME):
        if layout is not None:
            try:
                ast.Layout = layout
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] {ast.BranchName}: Layout setzen: {ex}")
        for t, tier_skills in enumerate(tabelle):
            objs = [o for o in (_skill_bauen(sk, outer) for sk in tier_skills) if o is not None]
            if len(objs) != len(tier_skills):
                logging.error(f"[ZB] {ast.BranchName} Tier {t + 1}: nur {len(objs)} von {len(tier_skills)} Skills gebaut")
            try:
                if t >= len(ast.Tiers):
                    logging.error(f"[ZB] {ast.BranchName}: Vorlage hat nur {len(ast.Tiers)} Tiers, Tier {t + 1} entfaellt")
                    break
                ast.Tiers[t].Skills = objs
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] {ast.BranchName} Tier {t + 1} setzen: {ex}")
        try:
            belegung = [[s.SkillName for s in tier.Skills] for tier in ast.Tiers]
            logging.info(f"[ZB] {ast.BranchName}: {belegung}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] {ast.BranchName}: Belegung lesen: {ex}")
    _immunitaet_bauen()


# --- Schadensimmunitaet (v1.12): Reinigung 2 s, Zeitsprung 1 s ------------------------------------
#
# Am Spieler-Pawn gibt es keine Invulnerability-Funktion (v0.71). Also Effekt-Skills auf die
# Received*DamageModifier - wie Stabilisator, aber mit -99: negative Scale-Summen TEILEN (v0.99),
# -99 heisst Schaden / 100, nicht 0. Sechs Quellen (alle Received*-Attribute ausser Amplify),
# verteilt auf zwei bewaehrte passive Vorlagen (4 + 2 Effekte) - DeathMark_Marked haette 7, bringt
# aber eine Bedingung und ein BPD mit. Das Modul schaltet beide an und nach Ablauf wieder ab.

IMMUN_WERT = -99.0
IMMUN_A = ("ZB_Immun_A", 4, A_RESIST)
IMMUN_B = ("ZB_Immun_B", 2, ("D_Attributes.DamageSourceModifiers.ReceivedSkillDamageModifier",
                             "D_Attributes.DamageSourceModifiers.ReceivedStatusEffectDamageModifier"))
IMMUN_OUTER = "GD_Assassin_Skills.Cunning"
_immun_rest = 0.0


def _immunitaet_bauen() -> None:
    for name, n, attribute in (IMMUN_A, IMMUN_B):
        try:
            obj = _copy("SkillDefinition", VORLAGE_PASSIV[n], IMMUN_OUTER, name)
            obj.SkillName = "Immunity"
            obj.SkillDescription = ""
            obj.MaxGrade = 1
            _effekte_setzen(obj, tuple(Effekt(a, IMMUN_WERT, "") for a in attribute), IMMUN_OUTER, name,
                            mit_praesentation=False)
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Immunitaet {name}: {ex}")


def immunitaet(sekunden: float, grund: str) -> None:
    """Schaden fuer `sekunden` auf 1 % senken. Laeuft schon eine, gilt die laengere Restzeit."""
    global _immun_rest
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        return
    def wert() -> str:
        return f"{attr_value('AttributeDefinition', A_RESIST[0], pawn)}"
    vorher = wert()
    ok = [skill_an(_find("SkillDefinition", f"{IMMUN_OUTER}.{name}"), 1) for name, _, _ in (IMMUN_A, IMMUN_B)]
    _immun_rest = max(_immun_rest, sekunden)
    logging.info(f"[ZB] Immunitaet ({grund}): {sekunden:.0f} s, an {ok}; ReceivedBulletDamageModifier {vorher} -> {wert()}")
    effekt("Immunitaet", FX_NACHHALL, None, 250.0, verzoegerung=0.1)   # sichtbar: kleine Nova am Spieler


def _immunitaet_tick(dt: float) -> None:
    global _immun_rest
    if _immun_rest <= 0:
        return
    _immun_rest -= dt
    if _immun_rest > 0:
        return
    for name, _, _ in (IMMUN_A, IMMUN_B):
        skill_aus(_find("SkillDefinition", f"{IMMUN_OUTER}.{name}"))
    pc = local_pc()
    wert = attr_value("AttributeDefinition", A_RESIST[0], pc.Pawn) if pc and pc.Pawn else "?"
    logging.info(f"[ZB] Immunitaet: aus, ReceivedBulletDamageModifier {wert}")


# --- Laufzeit: Rang lesen, Effekt-Skills schalten -----------------------------------------------

_SKILL_NAMEN = {n.lower(): n for n in SKILL_OUTER}  # Konsole tippt klein - der Objektname nicht


def skill_def(name: str, wirkung: bool = False) -> UObject | None:
    name = _SKILL_NAMEN.get(name.lower(), name)
    outer = SKILL_OUTER.get(name)
    if outer is None:
        logging.error(f"[ZB] unbekannter Skill: {name}")
        return None
    return _find("SkillDefinition", f"{outer}.{name}{'_Wirkung' if wirkung else ''}")


def skill_rang(name: str) -> int:
    """Wie viele Punkte hat der Spieler in diesem Baum-Skill?

    v0.53 scheiterte an PlayerSkillTree.GetSkillGrade - die Funktion gibt es dort nicht. 'zb funcs'
    (v0.54, mit Vererbung) zeigte sie am CONTROLLER: WillowPlayerController.GetSkillGrade(Definition)
    -> int, Zwilling GetSkillGradeByDef. Der Baum selbst hat nur GetSkillState(Def, OutState)."""
    pc = local_pc()
    d = skill_def(name)
    if pc is None or d is None:
        return 0
    for fn in ("GetSkillGrade", "GetSkillGradeByDef"):
        try:
            return int(getattr(pc, fn)(d))
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Rang {name} ueber {fn}: {ex}")
    return 0


def wirkung_an(name: str, grade: int | None = None) -> bool:
    """Effekt-Skill eines HS-Skills einschalten - mit dem Rang des Spielers, oder mit 'grade' (Stacks)."""
    rang = skill_rang(name)
    if rang <= 0:
        return False
    wirk = skill_def(name, wirkung=True)
    if wirk is None:
        return False
    g = rang if grade is None else grade
    ok = skill_an(wirk, g)
    logging.info(f"[ZB] Wirkung {name}: an, Rang {rang}, Grad {g} -> {ok}")
    return ok


def wirkung_aus(name: str) -> None:
    wirk = skill_def(name, wirkung=True)
    if wirk is not None and skill_aktiv(wirk):
        skill_aus(wirk)
        logging.info(f"[ZB] Wirkung {name}: aus")


def fenster_anpassen() -> None:
    """Langzeitgedaechtnis: +2 s Fenster je Rang. InitialDuration wird beim Start des Skills gelesen -
    also VOR StartActionSkill setzen (PRE-Hook), nicht danach."""
    skill = _find("SkillDefinition", f"{ACTION_OUTER}.Skill_{SKILL_OBJ}")
    if skill is None:
        return
    ziel = FENSTER_SEKUNDEN + 2.0 * skill_rang("Langzeitgedaechtnis")
    if abs(float(skill.InitialDuration) - ziel) > 0.01:
        skill.InitialDuration = ziel
        logging.info(f"[ZB] Fenster: {ziel:.0f}s (Langzeitgedaechtnis)")


def mechanik_gelegt() -> None:
    wirkung_an("Ausbruch")             # 3 s, laeuft von selbst ab
    wirkung_an("Stabilisator")         # bis zum Zuenden/Verpuffen
    wirkung_an("Langzeitgedaechtnis")  # Kritschaden, bis zum Zuenden/Verpuffen
    ticker_start()
    kills_start()
    mechanik_erinnerung_gelegt()       # merkt sich laufende Kill Skills
    pc = local_pc()
    if pc is not None:
        mechanik_ammo_gelegt(pc)       # Volle Rueckerstattung: Reserve merken
    mechanik_paket_b_gelegt()          # Paradoxon, Vorbelastung, Zeitspur: Raenge lesen, Buch leeren
    if pc is not None and pc.Pawn is not None and _wurf is None:
        # Paket D: Hologramm am Anker. Fliegt die Bombe (v1.19), setzt es erst _wurf_landen.
        o = pc.Pawn.Location
        mechanik_zeitkapsel_gelegt(_vec(o.X, o.Y, o.Z))


def mechanik_gezuendet(pawn: UObject) -> None:
    ticker_stop()
    # Phase 8 (v1.00): Einschlag am Ankunftsort, kurz danach das Beben.
    try:
        o = pawn.Location
        effekt("Ankunft", FX_ANKUNFT, _vec(o.X, o.Y, o.Z), 1000.0)
        # Das Beben (FX_BEBEN) ist raus - Nutzer, v1.03: "hat ein wenig uebertrieben gewirkt".
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Effekt Ankunft: {ex}")
    wirkung_aus("Stabilisator")
    wirkung_aus("Langzeitgedaechtnis")
    wirkung_an("Nachwirkung")          # 8 s
    mechanik_kills_gezuendet()         # Wiederkehr, 10 s
    # Erinnerung zuerst (stellt nur wieder her, was lief), dann Deja-vu (frischt immer auf) -
    # laeuft beides, ist die zweite Meldung wirkungslos, aber im Log sichtbar.
    mechanik_erinnerung_gezuendet()
    mechanik_dejavu()                  # Kill Skills auffrischen (Handgriff 3b)
    # Handgriff 4, Paket A. Reihenfolge mit Absicht: erst was am Spieler haengt, dann die Wirkung
    # nach aussen - so steht im Log erst der eigene Zustand, dann die Trefferliste.
    pc = local_pc()
    if pc is not None:
        mechanik_rueckerstattung(pc, pawn)
    mechanik_reinigung(pawn)
    mechanik_nachhall(pawn)
    # Ruecksprung-Detonation laeuft seit v0.95 in zuenden() vor dem Teleport (Explosion am Spieler).
    mechanik_zeitsprung(pawn)
    # Paket B. Paradoxon vor dem Vorbelastungsfenster: dessen Treffer sollen nicht nachgeschlagen
    # werden (_eigen schuetzt ohnehin, aber die Reihenfolge macht es auch ohne Flag richtig).
    mechanik_paradoxon()
    if pc is not None:
        mechanik_vorbelastung_gezuendet(pc)
    # Paket D: die Zeitkapsel hat ausgedient, am Absprungpunkt bleibt das Nachbild.
    holo_entfernen("Zeitkapsel", "gezuendet")
    mechanik_nachbild()
    # Auffrischung: +4 % des Maximums je Rang, ueber den Ankerwert hinaus (Pools setzen: Spike B).
    rang = skill_rang("Auffrischung")
    if rang > 0:
        anteil = 0.04 * rang
        max_h = try_call("GetMaxHealth", pawn.GetMaxHealth)
        max_s = try_call("GetMaxShieldStrength", pawn.GetMaxShieldStrength)
        if max_h:
            try_call("Auffrischung Leben", lambda: pawn.SetHealth(min(float(max_h), float(pawn.GetHealth()) + anteil * float(max_h))))
        if max_s:
            try_call("Auffrischung Schild", lambda: pawn.SetShieldStrength(min(float(max_s), float(pawn.GetShieldStrength()) + anteil * float(max_s))))
    # Paket E (v0.95): Verbuendete am Ankunftsort - nach Auffrischung, damit der Log-Wert fuer den
    # eigenen Pawn (Testschalter 'zb koop selbst') beide Aufschlaege getrennt zeigt.
    mechanik_verbuendete_gezuendet(pawn)


def mechanik_verpufft() -> bool:
    """Gibt True zurueck, wenn 'Kein Zurueck' greift - dann entfaellt der Cooldown ganz."""
    pc = local_pc()
    if pc is not None:
        # Messgroesse fuer Kurs halten (v0.90): wie lange lag die Bombe wirklich?
        logging.info(f"[ZB] Fenster tatsaechlich: {_game_time(pc) - _legen_time:.1f} s seit dem Legen, {_kills} Kill(s)")
    ticker_stop()
    mechanik_paket_b_verpufft()
    holo_entfernen("Zeitkapsel", "verpufft")
    wirkung_aus("Stabilisator")
    wirkung_aus("Langzeitgedaechtnis")
    return wirkung_an("KeinZurueck")   # 10 s


# --- Handgriff 2: der Ticker (v0.59) --------------------------------------------------------------
#
# Vier Skills brauchen etwas, das waehrend der liegenden Bombe jede Sekunde laeuft: Gespannte Zeit
# (ein Stack je Sekunde) und die drei Entfernungs-Skills Abstand, Sicherer Abstand, Grenzgaenger.
# Muster aus dem FL4K-Projekt (fl4k_pet on_tick, bewiesen): POST-Hook auf
# WillowPlayerController:PlayerTick, args.DeltaTime aufsummieren. Der Hook feuert jeden Frame -
# darum steht die Zustandsabfrage ganz vorn, im Zustand "bereit" kostet er nichts.
#
# Stacks laufen ueber den Rang des Effekt-Skills (skill_grad = UpdateSkillGrade + Refresh, gemessen):
# der Effekt-Skill hat je_rang als PerGradeUpgrade, also Grad = Rang x Stacks (MaxGrade 99).
#
# UU_JE_METER ist eine ANNAHME: die Skilltexte sprechen von Metern, das Spiel rechnet in Unreal-
# Einheiten. Pawn-CollisionHeight 86,6 (halbe Hoehe) passt zu ~100 Einheiten je Meter. Das Log
# zeigt beide Zahlen - wer nachmisst, korrigiert die Konstante.

TICK_FUNC = "WillowGame.WillowPlayerController:PlayerTick"  # Klasse in WillowGame (FL4K-Hook, bewiesen)
TICK_SEKUNDEN = 1.0
UU_JE_METER = 100.0
GESPANNT_STACKS_MAX = 10
ABSTAND_STUFE_METER = 10.0
ABSTAND_STUFEN_MAX = 5
SICHER_AB_METER = 15.0
GRENZ_AB_METER = 30.0

_tick_akku = 0.0
_tick_sekunden = 0        # Sekunden seit dem Legen (nur Anzeige)
_gespannt_stacks = 0
_abstand_stufe = 0
_sicher_an = False
_grenz_an = False


def ticker_start() -> None:
    global _tick_akku, _tick_sekunden, _gespannt_stacks, _abstand_stufe, _sicher_an, _grenz_an
    _tick_akku = 0.0
    _tick_sekunden = 0
    _gespannt_stacks = 0
    _abstand_stufe = 0
    _sicher_an = False
    _grenz_an = False


def ticker_stop() -> None:
    """Alles abraeumen, was der Ticker eingeschaltet hat. Die Zaehler setzt ticker_start zurueck."""
    if _gespannt_stacks > 0:
        stapel_setzen("GespannteZeit", 0)   # v1.18: Instanzen statt Grad
    if _abstand_stufe > 0:
        stapel_setzen("Abstand", 0)
    if _sicher_an:
        wirkung_aus("SichererAbstand")
    if _grenz_an:
        wirkung_aus("Grenzgaenger")
    ticker_start()


def wirkung_grad(name: str, grad: int) -> bool:
    """Effekt-Skill auf einen Grad setzen: einschalten, wenn er nicht laeuft, sonst umstufen."""
    wirk = skill_def(name, wirkung=True)
    if wirk is None:
        return False
    if not skill_aktiv(wirk):
        return wirkung_an(name, grad)
    ok = skill_grad(wirk, grad)
    logging.info(f"[ZB] Wirkung {name}: Grad {grad} -> {ok}")
    return ok


def wirkung_schalten(name: str, soll: bool, ist: bool) -> bool:
    """Zustandsskill nach Bedingung: nur beim Wechsel schalten, gibt den neuen Zustand zurueck."""
    if soll and not ist:
        return wirkung_an(name)
    if ist and not soll:
        wirkung_aus(name)
        return False
    return ist


def anker_abstand(pawn: UObject) -> float | None:
    """Entfernung Spieler -> Anker in Unreal-Einheiten, None ohne Anker oder auf anderer Karte."""
    a = _anchor
    if a is None:
        return None
    try:
        loc = pawn.Location
        return math.sqrt((loc.X - a.x) ** 2 + (loc.Y - a.y) ** 2 + (loc.Z - a.z) ** 2)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Ticker: Abstand: {ex}")
        return None


def ticker_sekunde(pc: UObject) -> None:
    try:
        zeitspur_sekunde()  # v1.05 - Zeitwirbel am Anker (bis v0.88: verlangsamen, Spike A)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Zeitspur: {ex}")
    _ticker_sekunde_rest(pc)


def _ticker_sekunde_rest(pc: UObject) -> None:
    """Einmal je Sekunde im Zustand 'gelegt'."""
    global _tick_sekunden, _gespannt_stacks, _abstand_stufe, _sicher_an, _grenz_an
    _tick_sekunden += 1
    pawn = pc.Pawn
    if pawn is None:
        return

    # Gespannte Zeit: ein Stack je Sekunde, Grad = Rang x Stacks
    rang_gz = skill_rang("GespannteZeit")
    if rang_gz > 0 and _gespannt_stacks < GESPANNT_STACKS_MAX:
        _gespannt_stacks += 1
        stapel_setzen("GespannteZeit", _gespannt_stacks)   # v1.18: ein Stack = eine Instanz (HUD)

    # Entfernung zum Anker
    uu = anker_abstand(pawn)
    meter = (uu or 0.0) / UU_JE_METER
    if uu is not None:
        stufe = min(ABSTAND_STUFEN_MAX, int(meter // ABSTAND_STUFE_METER))
        rang_ab = skill_rang("Abstand")
        if rang_ab > 0 and stufe != _abstand_stufe:
            stapel_setzen("Abstand", stufe)   # v1.18: Stufe = Instanzen (HUD)
            _abstand_stufe = stufe
        _sicher_an = wirkung_schalten("SichererAbstand", meter > SICHER_AB_METER, _sicher_an)
        _grenz_an = wirkung_schalten("Grenzgaenger", meter > GRENZ_AB_METER, _grenz_an)

    logging.info(
        f"[ZB] Ticker {_tick_sekunden}s | Anker {meter:.1f} m ({(uu or 0.0):.0f} uu)"
        f" | Gespannte Zeit {_gespannt_stacks}/{GESPANNT_STACKS_MAX} | Abstand Stufe {_abstand_stufe}"
        f" | Sicher {'an' if _sicher_an else 'aus'} | Grenz {'an' if _grenz_an else 'aus'}"
        f" | WeaponDamage(Waffe)={attr_value('AttributeDefinition', A_SCHADEN, pawn.Weapon) if pawn.Weapon else '-'}"
    )


# --- Handgriff 3: das Kill-Ereignis (v0.65-v0.67) ----------------------------------------------
#
# Kill-Weg: WillowPlayerController.NotifyKilledEnemy(EnemyName) - die Kill-Meldung. Name per
# "zb funcs WillowPlayerController Kill" belegt, im Spiel bestaetigt (v0.66: drei Bullymong-Kills,
# drei Zeilen). Der UE3-Standard Controller.NotifyKilled(Killer, Killed, KilledPawn, damageType)
# steht zwar in der Funktionsliste, ein POST-Hook darauf feuerte aber bei keinem einzigen Kill
# (v0.65/v0.66, Spur an) - vermutlich laeuft er nativ am Hook vorbei. Deshalb raus.
#
# Wiederkehr: Kills mit liegender Bombe zaehlen, beim Zuenden Effekt-Skill mit Grad = Rang x Kills
# (max 10) fuer 10 s (Vorlage Skill_Speed, DURATION_Timed - laeuft von selbst ab).

KILLED_ENEMY_FUNC = "WillowGame.WillowPlayerController:NotifyKilledEnemy"
# v1.16: die harten Kill Skills des Spiels. Unsere drei stapelt das Modul (v1.13); das Spiel schaltete
# ihre Baum-Skills (Kill-Vorlage, SKILL_TYPE_Kill) zusaetzlich an -> doppelte Symbole im HUD
# (Nutzer-Screenshot v1.15). Fuer den Chronomaster geblockt. Funktion belegt seit v0.70 (Deja-vu).
UPDATE_KILL_SKILLS_FUNC = "WillowGame.WillowPlayerController:UpdateKillSkills"


def _on_update_kill_skills(obj: UObject, args: Any, ret: Any, func: Any) -> Any:
    from unrealsdk.hooks import Block  # noqa: PLC0415
    pc = local_pc()
    if pc is None or obj._path_name() != pc._path_name() or not ist_chronomaster(pc):
        return None
    # VERMUTUNG: das Spiel ruft UpdateKillSkills beim Kill. Die Zeile belegt es (oder ihr Fehlen nicht).
    logging.info("[ZB] UpdateKillSkills geblockt (Kill Skills stapelt das Modul)")
    return Block
WIEDERKEHR_KILLS_MAX = 10

_kills = 0  # Kills seit dem Legen (nur im Zustand "gelegt" gezaehlt)


def _on_notify_killed_enemy(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST auf WillowPlayerController:NotifyKilledEnemy - jeder eigene Kill."""
    global _kills
    pc = local_pc()
    if pc is None or obj._path_name() != pc._path_name():
        return
    try:
        name = args.EnemyName
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] NotifyKilledEnemy: {ex}")
        return
    if _trace:
        logging.info(f"[ZB] SPUR NotifyKilledEnemy EnemyName={name!r}")
    if ist_chronomaster(pc):
        try:
            kill_stack_plus(name)   # v1.13: jeder Kill, auch ohne liegende Bombe
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Kill-Stacks: {ex}")
    if _state != ZUSTAND_GELEGT or not ist_chronomaster(pc):
        return
    _kills += 1
    logging.info(f"[ZB] Kill {_kills} mit liegender Bombe: {name}")
    mechanik_kurs_halten()  # v0.90


# --- Kill-Stacks (v1.13, Nutzerwunsch 2026-09-26) -------------------------------------------------
#
# Deja-vu, Wiederholung und Vorstoss stapeln unbegrenzt. EIN Zaehler fuer alle drei: jeder Kill +1.
# Verfall (Nutzerentscheidung "einzeln abbauen"): 3 s nach dem letzten Kill faellt jede Sekunde
# ein Stack. Wirkung ueber die Effekt-Skills <Name>_Wirkung, Grad = Rang x Stacks (skill_grad =
# UpdateSkillGrade + Refresh, fuer Gespannte Zeit gemessen). Deja-vu haelt beim Zuenden fest (Frist
# neu), Erinnerung stellt beim Zuenden den Stapel vom Legen wieder her.

KILL_STACK_FRIST_S = 3.0
KILL_STACK_TAKT_S = 1.0

_kill_stacks = 0
_kill_frist = 0.0
_kill_takt = 0.0


_ks_rang_gesetzt: dict[str, int] = {}   # v1.14: fuer welchen Rang die Effektwerte zuletzt gesetzt wurden


def _ks_werte_setzen(name: str, wirk: UObject, rang: int) -> None:
    """Jede Instanz (= ein Stack, Grad 1) traegt Wert x Rang. Elementweise geschrieben wie bei
    Rueckenwind (Spike D). Nur bei Rangwechsel; danach werden die Instanzen neu aufgebaut."""
    if _ks_rang_gesetzt.get(name) == rang:
        return
    sk = next((s for tabelle, _ in BAEUME for tier in tabelle for s in tier if s.name == name), None)
    if sk is None:
        return
    liste = wirk.SkillEffectDefinitions
    for i, e in enumerate(sk.effekte):
        liste[i].BaseModifierValue.BaseValueConstant = e.je_rang * rang
        liste[i].PerGradeUpgrade.BaseValueConstant = e.je_rang * rang
    _ks_rang_gesetzt[name] = rang
    # alle laufenden Instanzen weg - sie tragen die alten Werte; _kill_stacks_anwenden baut neu auf
    _ks_alle_weg(name, wirk)
    logging.info(f"[ZB] Kill-Stacks {name}: Werte fuer Rang {rang} gesetzt")


# v1.17: EIN STACK = EINE INSTANZ. zb stapeltest (v1.16) im Spiel: jede ActivateSkill legt eine
# weitere Instanz desselben Skills an (Krit 2,484 -> 2,524 -> 2,564 -> 2,604), jede DeactivateSkill
# nimmt genau eine weg (-> 2,564), und das HUD zeigt die Zahl der Instanzen ("3x" -> "2x"). So stapelt
# auch Zer0s Critical Ascension (MaxGrade 5, zaehlt bis 999). Jede Instanz laeuft mit Grad 1.
_ks_instanzen: dict[str, int] = {}
KS_ABBAU_MAX = 100000   # Sicherung gegen Endlosschleifen beim Abbauen


def _ks_alle_weg(name: str, wirk: UObject) -> None:
    n = 0
    while skill_aktiv(wirk) and n < KS_ABBAU_MAX:
        skill_aus(wirk)
        n += 1
    _ks_instanzen[name] = 0


def stapel_setzen(name: str, n: int, neu: bool = False) -> None:
    """v1.18: die Instanzen des Effekt-Skills <name>_Wirkung auf n bringen (0 = keine) - der Weg fuer
    JEDEN Stack-Skill mit HUD-Zahl (Kill Skills, Gespannte Zeit, Abstand, Wiederkehr). Jede Instanz
    laeuft mit Grad 1 und traegt Wert x Rang. `neu`: erst alle weg (frische Laufzeit bei Timed-Skills)."""
    rang = skill_rang(name)
    wirk = skill_def(name, wirkung=True)
    if wirk is None:
        return
    try:
        if neu:
            _ks_alle_weg(name, wirk)
        ziel = n if rang > 0 else 0
        if rang > 0:
            _ks_werte_setzen(name, wirk, rang)
        ist = _ks_instanzen.get(name, 0)
        if ist > 0 and not skill_aktiv(wirk):
            ist = 0   # Kartenwechsel, Tod oder Ablauf (Timed) hat die Instanzen geraeumt
        while ist < ziel:
            skill_an(wirk, 1)
            ist += 1
        while ist > ziel and skill_aktiv(wirk):
            skill_aus(wirk)
            ist -= 1
        _ks_instanzen[name] = 0 if ziel == 0 else ist
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Stapel {name}: {ex}")


def _kill_stacks_anwenden(grund: str) -> None:
    """Die Instanzen der drei Kill-Stack-Skills auf _kill_stacks bringen. Still."""
    for name in KILL_SKILLS:
        stapel_setzen(name, _kill_stacks)


def stapeltest(teil: str = "") -> None:
    """zb stapeltest (v1.16): stapelt das Spiel Instanzen desselben Skills? Die HUD-Zahl bei Zer0s
    Critical Ascension (MaxGrade 5, zaehlt bis 999, Dauer 300 s) ist nicht der Grad - Vermutung:
    die Zahl der gleichzeitig laufenden Instanzen. Probe am Wirkungs-Skill von Wiederholung (Krit)."""
    global _kill_stacks
    pc = local_pc()
    wirk = skill_def("Wiederholung", wirkung=True)
    if pc is None or pc.Pawn is None or wirk is None:
        logging.error("[ZB] stapeltest: kein Pawn oder kein Wirkungs-Skill")
        return
    krit = lambda: attr_value("AttributeDefinition", A_KRIT, pc.Pawn)  # noqa: E731
    if teil == "aus":
        logging.info(f"[ZB] stapeltest aus: DeactivateSkill einmal -> {skill_aus(wirk)}, aktiv {skill_aktiv(wirk)}, Krit {krit()}")
        return
    _kill_stacks = 0   # die normale Stack-Logik aus dem Weg
    _kill_stacks_anwenden("stapeltest")
    rang = max(1, skill_rang("Wiederholung"))
    _ks_werte_setzen("Wiederholung", wirk, rang)
    logging.info(f"[ZB] stapeltest: aus, Krit {krit()}")
    for i in range(1, 4):
        logging.info(f"[ZB] stapeltest: ActivateSkill #{i} (Grad 1) -> {skill_an(wirk, 1)}, aktiv {skill_aktiv(wirk)}, Krit {krit()}")
    logging.info("[ZB] stapeltest: jetzt HUD ansehen, dann 'zb stapeltest aus'")


def kill_stack_plus(name: str = "") -> None:
    global _kill_stacks, _kill_frist, _kill_takt
    if not any(skill_rang(n) > 0 for n in KILL_SKILLS):
        return
    _kill_stacks += 1
    _kill_frist, _kill_takt = KILL_STACK_FRIST_S, 0.0
    _kill_stacks_anwenden("Kill")
    pc = local_pc()
    krit = attr_value("AttributeDefinition", A_KRIT, pc.Pawn) if pc and pc.Pawn else "?"
    logging.info(f"[ZB] Kill-Stacks: {_kill_stacks} ({name}) - Krit-Attribut jetzt {krit}")


def kill_stacks_festhalten(grund: str) -> None:
    """Deja-vu beim Zuenden: die Verfallsfrist beginnt von vorn."""
    global _kill_frist, _kill_takt
    if _kill_stacks > 0:
        _kill_frist, _kill_takt = KILL_STACK_FRIST_S, 0.0
        logging.info(f"[ZB] Kill-Stacks festgehalten ({grund}): {_kill_stacks}, Frist {KILL_STACK_FRIST_S:.0f} s")


def _kill_stack_tick(dt: float) -> None:
    global _kill_stacks, _kill_frist, _kill_takt
    if _kill_stacks <= 0:
        return
    if _kill_frist > 0:
        _kill_frist -= dt
        return
    _kill_takt += dt
    if _kill_takt < KILL_STACK_TAKT_S:
        return
    _kill_takt = 0.0
    _kill_stacks -= 1
    _kill_stacks_anwenden("Verfall")
    if _kill_stacks % 10 == 0:
        logging.info(f"[ZB] Kill-Stacks verfallen: noch {_kill_stacks}")


def kills_start() -> None:
    global _kills
    _kills = 0


def mechanik_kills_gezuendet() -> None:
    """Wiederkehr: nach dem Zuenden je Kill +2 % Waffenschaden je Rang, 10 s."""
    if _kills <= 0:
        return
    rang = skill_rang("Wiederkehr")
    if rang > 0:
        # v1.18: Instanzen statt Grad; neu=True, damit alle ihre 10 s frisch beginnen
        stapel_setzen("Wiederkehr", min(_kills, WIEDERKEHR_KILLS_MAX), neu=True)
    logging.info(f"[ZB] Wiederkehr: {_kills} Kill(s) seit dem Legen, Rang {rang}")


# --- Handgriff 3b: Deja-vu - das Zuenden frischt alle Kill Skills auf (v0.69/v0.70) -------------
#
# ERSTER WEG, IM SPIEL WIDERLEGT (v0.69): SkillEffectManager.NotifySkillEvent(11 = SEVT_KilledEnemy,
# pc, None, None, None, None). Der Aufruf geht fehlerfrei durch und bewirkt NICHTS - sieben Versuche
# von Hand und einer beim Zuenden, jedes Mal blieben alle drei Kill-Skills aus.
#
# Warum, sagt der Dump: unsere Vorlage GD_Assassin_Skills.Sniping.Killer hat **kein KillEvents-Feld**,
# nur SkillType=SKILL_TYPE_Kill und DurationType=DURATION_Infinite. Die KillEvents(n).EventType=SKE_*
# aus dem Datenpaket gehoeren Schild- und Artefakt-Skills (Roid_Shield_Skill_*) - ein anderer
# Mechanismus, und nur der haengt an NotifySkillEvent. Charakter-Kill-Skills schaltet das Spiel hart.
#
# ZWEITER WEG (v0.70): WillowPlayerController.UpdateKillSkills(bEnable, ...) - stand seit Spike E in
# docs/spikes.md ("UpdateKillSkills und ForceKillSkillsOff fuer Kill Skills") und ist dort uebersehen
# worden. Die weiteren Parameter sind unbekannt, darum ruft mechanik_dejavu erst mit einem Argument
# und loggt bei Fehlschlag die Signatur gleich mit - ein Testlauf reicht so in jedem Fall.

SEVT_KILLED_ENEMY = 11  # ESkillEventType, im Spiel abgelesen (v0.69). Bleibt dokumentiert: der Wert
                        # stimmt, nur traegt dieser Weg unsere Kill-Skills nicht.
KILL_SKILLS = ("DejaVu", "Wiederholung", "Vorstoss")  # unsere drei Skills der Bauart KILL


def _kill_skills_zustand() -> str:
    """an/aus der drei Kill-Skills als Zeile - die Messgroesse fuer Deja-vu (Regel 3).

    Der Rang steht mit dabei (v0.70): ein Skill ohne Punkte kann gar nicht angehen. Ohne diese Zahl
    sind "bleibt aus, weil kaputt" und "bleibt aus, weil 0 Punkte" nicht zu unterscheiden - genau
    die Art Messung, vor der Falle 2 warnt.
    """
    teile = []
    for n in KILL_SKILLS:
        d = skill_def(n)
        teile.append(f"{n}={'an' if d is not None and skill_aktiv(d) else 'aus'}(R{skill_rang(n)})")
    return ", ".join(teile)


# =================================================================================================
# Handgriff 4, Paket A (v0.72): die fuenf Platzhalter, die am Zuenden haengen
#
# Alle Namen hier stammen aus dem Sammellauf "zb namen" (v0.71, Log 15:57 UTC) - keiner ist geraten:
#   WillowAIPawn.TakeDamage(DamageAmount, EventInstigator, HitLocation, Momentum, DamageType,
#                           HitInfo, DamageCauser, Pipeline)
#   WillowAIPawn.Stagger(StaggerInstigator) / CanBeStaggered() -> bool
#   Pawn.AddVelocity(NewVelocity, HitLocation, DamageType, DamageTypeDefinition, HitInfo)
#   WillowPawn.RemoveAllStatusEffects()
#   WillowWeapon.AddAmmo(Amount) -> int, GetAmmoCount() -> int
#   pc.LastKnownAmmoCount_<Typ> (Eigenschaften, Float - das HUD liest sie)
# Gegner finden: unrealsdk.find_all("WillowAIPawn", exact=False) - Muster aus dem FL4K-Projekt.
#
# Actor.HurtRadius(...) gaebe es auch, mit elf Parametern. Wir nehmen stattdessen ueberall dieselbe
# eigene Schleife: ein Mechanismus fuer alle vier Umkreis-Skills, jeder Treffer einzeln im Log, und
# keine Ueberraschung, wen die Engine sonst noch trifft (Verbuendete, Fahrzeuge, uns selbst).

UU_JE_METER_A = 100.0  # wie beim Ticker (v0.59, dort gegen Sprinttempo geprueft)


def _vec(x: float, y: float, z: float) -> Any:
    return unrealsdk.make_struct("Vector", X=x, Y=y, Z=z)


# ABSTURZ v0.74, teuer bezahlt: `zb gegner` rief _leben() -> p.GetHealth() auf ALLEN 51 Treffern von
# find_all("WillowAIPawn") - auch auf Archetypen, die in Paketen liegen und keine Welt-Actors sind.
# Das Spiel war sofort weg, das Log endet mitten im Befehl. Lehre, die es so noch nicht gab:
#
#   An FREMDEN Objekten nur EIGENSCHAFTEN lesen, nie Funktionen rufen, solange nicht feststeht,
#   dass es echte Welt-Actors sind. Ein Property-Zugriff daneben wirft eine Python-Exception; ein
#   ProcessEvent daneben nimmt das Spiel mit, und kein try/except faengt das ab.
#
# Seitdem: erst der Pfad (den liefert das SDK ohne die Engine zu fragen), dann Eigenschaften, und
# Funktionen nur an Objekten, die beides ueberstanden haben.

WELT_MARKE = "TheWorld"  # nur was hier drinsteht, ist eine Instanz in der Karte


def _ist_welt_actor(p: UObject) -> bool:
    """Reiner Pfadtest, ohne die Engine zu fragen - das ist die sichere Vorstufe zu allem anderen."""
    try:
        pfad = p._path_name()
    except Exception:  # noqa: BLE001
        return False
    return WELT_MARKE in pfad and "Default__" not in pfad and "Archetype" not in pfad


def _leben(p: UObject) -> float:
    """Leben eines Welt-Pawns, NUR ueber Eigenschaften gelesen. -1, wenn nicht zu ermitteln.

    GetHealth() waere der Weg des Spielers (Spike B), aber an fremden Pawns ist ein Funktionsaufruf
    das Risiko aus v0.74 nicht wert.

    KORREKTUR v0.86: **WillowAIPawn hat KEIN Feld Health** ('zb schaden' im Spiel: "'WillowAIPawn'
    object has no attribute 'Health'"). Alles, was seit v0.75 an Gegnerleben gemessen wurde, kam aus
    dem HealthPool - der war nur als Ersatzweg gedacht und hat still die ganze Arbeit getan. Darum
    steht er jetzt vorn; das Feld bleibt als Ersatz fuer Pawn-Arten, die es doch haben.
    """
    if not _ist_welt_actor(p):
        return -1.0
    try:
        return float(p.HealthPool.Data.CurrentValue)
    except Exception:  # noqa: BLE001
        pass
    try:
        return float(p.Health)
    except Exception:  # noqa: BLE001
        return -1.0


def _gegner_lebend() -> list[UObject]:
    """Alle lebenden KI-Pawns der Karte. Archetypen, Default-Objekte, Leichen und seit v0.92 unsere
    eigenen Hologramme fliegen raus - die sind selbst WillowAIPawns, und Nachhall oder Sprengsatz
    haetten sonst das eigene Nachbild getroffen."""
    raus = []
    eigene = _holo_pfade()
    for p in unrealsdk.find_all("WillowAIPawn", exact=False):
        if not _ist_welt_actor(p):
            continue
        try:
            if p._path_name() in eigene:
                continue
        except Exception:  # noqa: BLE001
            continue
        try:
            if bool(p.bDeleteMe):
                continue
        except Exception:  # noqa: BLE001
            continue
        if _leben(p) <= 0.0:
            continue
        raus.append(p)
    return raus


def _abstand_uu(a: Any, b: Any) -> float:
    return math.sqrt((a.X - b.X) ** 2 + (a.Y - b.Y) ** 2 + (a.Z - b.Z) ** 2)


def _schaden_basis(pawn: UObject) -> float:
    """Der Waffenschaden des Spielers - der eine Teil der Schadensformel (s. _schaden_gegen)."""
    try:
        wert = attr_value("AttributeDefinition", A_SCHADEN, pawn.Weapon) if pawn.Weapon else None
        return float(wert) if wert else 100.0
    except Exception:  # noqa: BLE001
        return 100.0


# Anteil am Leben des Ziels - der zweite Teil der Formel. Ohne ihn ist ein Umkreis-Skill auf Stufe
# 80 / OP 10 wirkungslos: v0.78 gemessen, 402 bis 739 Schaden gegen Ziele mit 925.976 Leben, also
# unter 0,1 %. Ein Waffen-Vielfaches waechst mit der eigenen Waffe, aber Gegnerleben waechst auf den
# OP-Stufen viel schneller - deshalb skaliert der zweite Teil am Ziel selbst und bleibt auf jeder
# Stufe gleich stark. Gerechnet wird der GROESSERE der beiden Werte, nie die Summe.
ANTEIL_JE_20M = 0.05   # 5 % des Ziel-Lebens je 20 m Sprungweite
ANTEIL_MAX = 0.35      # nie mehr als 35 % auf einen Schlag - gegen Bosse soll es kein Knopfdruck-Tod sein


def _schaden_gegen(ziel: UObject, waffen_anteil: float, weite_m: float) -> float:
    """Was ein Umkreis-Skill diesem Ziel zufuegt: das Groessere aus Waffen- und Lebensanteil."""
    anteil = min(ANTEIL_MAX, ANTEIL_JE_20M * weite_m / 20.0)
    leben = _leben(ziel)
    vom_leben = leben * anteil if leben > 0 else 0.0
    return max(waffen_anteil, vom_leben)


def _treffer(ziel: UObject, pc: UObject, schaden: float, stoss_uu: float, mitte: Any, stagger: bool) -> str:
    """Ein Gegner: Schaden, Rueckstoss, Stagger - alles einzeln gekapselt, damit ein Fehlschlag die
    anderen nicht mitnimmt. Gibt zurueck, was tatsaechlich ankam (fuer das Log).

    Hier WERDEN Funktionen an fremden Pawns gerufen - das geht nur, weil jedes Ziel vorher den
    Welt-Test bestanden hat. Der Test steht trotzdem noch einmal hier: nach v0.74 ist eine
    zusaetzliche Zeile billiger als ein Absturz."""
    if not _ist_welt_actor(ziel):
        return "kein Welt-Actor - uebersprungen"
    teile = []
    ort = ziel.Location
    richtung = _vec(ort.X - mitte.X, ort.Y - mitte.Y, ort.Z - mitte.Z)
    laenge = max(1.0, math.sqrt(richtung.X ** 2 + richtung.Y ** 2 + richtung.Z ** 2))
    if schaden > 0:
        vorher = _leben(ziel)
        try:
            hit = unrealsdk.make_struct("TraceHitInfo")
            wucht = _vec(richtung.X / laenge * stoss_uu, richtung.Y / laenge * stoss_uu, stoss_uu * 0.3)
            ziel.TakeDamage(schaden, pc, ort, wucht, None, hit, None, None)
            # Regel 3: "kein Fehler" ist keine Wirkung. Was zaehlt, ist das Leben davor und danach.
            nachher = _leben(ziel)
            teile.append(f"Schaden {schaden:.0f} (Leben {vorher:.0f} -> {nachher:.0f}, ab {vorher - nachher:.0f})")
        except Exception as ex:  # noqa: BLE001
            teile.append(f"TakeDamage: {ex}")
    # REIHENFOLGE: erst Stagger, dann Stoss. Der Stagger wirft das Ziel in die Ragdoll-Physik
    # (v0.78 nachgemessen: Physics 2 -> 10 = PHYS_RigidBody), und was vorher an Velocity gesetzt
    # wurde, ist damit hinfaellig. Also zuerst umwerfen, dann den umgeworfenen Koerper schieben.
    if stagger:
        # StaggerInstigator will einen PAWN, keinen Controller (v0.75 gemessen: "Object is not
        # instance of Pawn"). Bei ActivateSkill ist es genau andersherum (Spike E) - die beiden
        # Funktionen sehen gleich aus und meinen Verschiedenes.
        try:
            urheber = pc.Pawn
            if bool(ziel.CanBeStaggered()):
                ziel.Stagger(urheber)
                teile.append("Stagger")
            else:
                teile.append("stagger-fest")
        except Exception as ex:  # noqa: BLE001
            teile.append(f"Stagger: {ex}")
    if stoss_uu > 0:
        teile.append(_stoss_geben(ziel, richtung, laenge, stoss_uu, ort))
        _flug_merken(ziel)  # ob es gehalten hat, sagt erst die Nachmessung eine Sekunde spaeter
    return ", ".join(teile)


def stoss_versuch(kraft: float, art: int, radius_m: float = 8.0) -> None:
    """zb stoss [KRAFT] [ART] - Rueckstoss-Varianten an den Zielen ringsum ausprobieren (v0.80).

    v0.79 ist durchgefallen: AddImpulse laeuft ohne Fehler, die Ziele rutschen trotzdem nur rund
    einen Meter. Verdacht: die Parameterfolge ist GERATEN, und wenn bVelChange nicht als True
    ankommt, rechnet die Engine 542 als echten Impuls gegen die Masse des Koerpers - bei rund 100 kg
    sind das 5 Einheiten je Sekunde, was genau wie "faellt um" aussieht.

    Statt weiter zu raten und jedes Mal neu auszuliefern: durchprobieren. Die Nachmessung sagt nach
    einer Sekunde, welche Art wie weit getragen hat.
      1  Impuls aufs Mesh, bVelChange=True   (der Weg aus v0.79)
      2  Impuls aufs Mesh, bVelChange=False  (echter Impuls - braucht viel groessere Zahlen)
      3  nur Actor.Velocity + PHYS_Falling   (ohne Ragdoll-Umweg)
      4  Mesh aufwecken, dann Impuls         (Verdacht: der Koerper schlaeft)
      5  alles zusammen
      6  NavMesh loesen, dann Falling + Velocity   (fuer Bodengegner, v0.81)
      7  TakeDamage mit Momentum                   (BL2s eigener Weg, wie Nova-Schilde)
      8  Ragdoll erzwingen + Radial-Impuls         (SetDyingPhysics, v0.82)
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] stoss: kein Spieler-Pawn")
        return
    logging.info(f"[ZB] stoss: Art {art}, Kraft {kraft:.0f}, Radius {radius_m:.0f} m")
    mitte = pawn.Location
    n = 0
    for ziel in _gegner_lebend():
        try:
            d = _abstand_uu(ziel.Location, mitte)
        except Exception:  # noqa: BLE001
            continue
        if d > radius_m * UU_JE_METER_A:
            continue
        n += 1
        o = ziel.Location
        r = _vec(o.X - mitte.X, o.Y - mitte.Y, o.Z - mitte.Z)
        laenge = max(1.0, math.sqrt(r.X ** 2 + r.Y ** 2 + r.Z ** 2))
        waagerecht = kraft * 0.707
        schub = _vec(r.X / laenge * waagerecht, r.Y / laenge * waagerecht, kraft * 0.707)
        teile = []
        mesh = None
        try:
            mesh = ziel.Mesh
        except Exception as ex:  # noqa: BLE001
            teile.append(f"kein Mesh: {ex}")
        if art in (4, 5) and mesh is not None:
            try:
                mesh.WakeRigidBody("")  # Name GERATEN - die Signatur steht im Fehlerfall im Log
                teile.append("geweckt")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"WakeRigidBody: {ex}")
        if art in (1, 2, 4, 5) and mesh is not None:
            vel = art != 2
            try:
                mesh.AddImpulse(schub, o, "", vel)
                teile.append(f"Impuls(bVelChange={vel})")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"AddImpulse: {ex}")
        if art in (3, 5):
            try:
                ziel.SetPhysics(2)
                ziel.Velocity = schub
                teile.append("Velocity+Falling")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"Velocity: {ex}")
        if art == 6:
            # v0.80 gemessen: fliegende Ziele (Physics 4) fliegen mit Art 3 vier bis fuenf Meter,
            # Bodengegner keinen. Bei denen steht auch nach dem Stoss wieder Physics 12 =
            # PHYS_NavMeshWalking - das Navigationsnetz haelt sie fest und macht jede Geschwindigkeit
            # zunichte. Hier also erst das NavMesh loesen. Beide Namen sind GERATEN (UE3 kennt
            # SetNavMeshWalking; die Eigenschaft ist der zweite Versuch), darum einzeln geloggt.
            for name, tu in (("SetNavMeshWalking(False)", lambda o: o.SetNavMeshWalking(False)),
                             ("bUseNavMeshWalking=False", lambda o: setattr(o, "bUseNavMeshWalking", False)),
                             ("bCollideWorld=True", lambda o: setattr(o, "bCollideWorld", True))):
                try:
                    tu(ziel)
                    teile.append(name)
                except Exception as ex:  # noqa: BLE001
                    teile.append(f"{name}: {ex}")
            try:
                ziel.SetPhysics(2)
                ziel.Velocity = schub
                teile.append(f"Falling+Velocity (Physics jetzt {ziel.Physics})")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"Velocity: {ex}")
        if art == 8:
            # v0.81: die Signatur von AddImpulse war richtig (im Spiel abgelesen), nur simuliert die
            # Engine bei Physics 12 gar kein Skelett - ein Mesh-Impuls trifft dann nichts. Also den
            # Koerper erst in die Ragdoll-Physik werfen (SetDyingPhysics - Name aus 'zb funcs', was
            # er wirklich tut, ist eine Vermutung), aufwecken und mit dem Explosionsimpuls schieben.
            try:
                ziel.SetDyingPhysics()
                teile.append(f"SetDyingPhysics (Physics jetzt {ziel.Physics})")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"SetDyingPhysics: {ex}")
            if mesh is not None:
                try:
                    mesh.WakeRigidBody("")
                    # AddRadialImpulse(Origin, Radius, Strength, Falloff, bVelChange) - im Spiel
                    # abgelesen (v0.81). Falloff 0 = konstant ueber den ganzen Radius.
                    mesh.AddRadialImpulse(mitte, radius_m * UU_JE_METER_A, kraft, 0, True)
                    teile.append("RadialImpuls")
                except Exception as ex:  # noqa: BLE001
                    teile.append(f"AddRadialImpulse: {ex}")
        if art == 7:
            # BL2s eigener Weg: der Momentum-Parameter von TakeDamage. So schleudern Nova-Schilde
            # und Explosionen - mit DamageType, nicht mit None wie bisher.
            # v0.81: WillowDamageTypeDefinition wurde abgelehnt ("Class does not inherit from
            # DamageType") - der Parameter will eine echte DamageType-KLASSE. Welche es in BL2 gibt,
            # ist unbekannt, also der Reihe nach probieren und die erste nehmen, die es gibt.
            dmg_klasse = None
            for kandidat in ("WillowDamageTypeExplosive", "DmgType_Explosion", "DmgType_Crushed",
                             "DmgType_Fell", "WillowDamageType", "DamageType"):
                try:
                    dmg_klasse = unrealsdk.find_class(kandidat)
                    teile.append(f"DamageType={kandidat}")
                    break
                except Exception:  # noqa: BLE001
                    continue
            try:
                hit = unrealsdk.make_struct("TraceHitInfo")
                ziel.TakeDamage(1.0, pc, o, schub, dmg_klasse, hit, None, None)
                teile.append("TakeDamage mit Momentum")
            except Exception as ex:  # noqa: BLE001
                teile.append(f"TakeDamage: {ex}")
        _flug_merken(ziel)
        logging.info(f"[ZB] stoss: {ziel.Name} auf {d / UU_JE_METER_A:.1f} m, Physics {ziel.Physics} -> {', '.join(teile)}")
    logging.info(f"[ZB] stoss: {n} Ziel(e) - Weiten kommen in einer Sekunde")
    if n == 0:
        logging.info("[ZB] stoss: niemand in Reichweite ('zb ziel 3' spawnt welche)")


def _stoss_geben(ziel: UObject, richtung: Any, laenge: float, stoss_uu: float, ort: Any) -> str:
    """Ein Ziel wegschleudern.

    +---------------------------------------------------------------------------------------+
    | GEPARKT (2026-09-23, v0.77-v0.82). Das wirkt NUR an fliegenden Gegnern (Physics 4):    |
    | gemessen 4,3-5,4 m. Bodengegner stehen in PHYS_NavMeshWalking (12) und bewegen sich    |
    | 0,0-0,2 m, EGAL WAS MAN TUT.                                                           |
    |                                                                                        |
    | Acht Wege sind durchprobiert, sieben widerlegt - darunter Mesh-Impuls (mit und ohne    |
    | bVelChange, bis Kraft 50.000), WakeRigidBody, AddRadialImpulse, SetDyingPhysics,       |
    | TakeDamage-Momentum und das Loesen des NavMesh (die Funktionen dafuer gibt es nicht).  |
    |                                                                                        |
    | >>> VOR JEDEM NEUEN VERSUCH: docs/spikes.md, Abschnitt "Rueckstoss an Gegnern". <<<    |
    | Dort stehen alle Messwerte, alle Sackgassen und der einzige noch offene Weg            |
    | (BL2s Singularity-Granaten ueber Behavior_SetPhysics). Zum Ausprobieren: zb stoss.     |
    +---------------------------------------------------------------------------------------+

    Der Mesh-Impuls bleibt drin, weil er nichts kostet und bei ragdollenden Zielen der einzige Weg
    waere; die Signatur ist im Spiel abgelesen (v0.81), nicht geraten.
    """
    waagerecht = stoss_uu * 0.707
    schub = _vec(richtung.X / laenge * waagerecht, richtung.Y / laenge * waagerecht, stoss_uu * 0.707)
    teile = [f"Stoss {stoss_uu:.0f}"]
    try:
        phys_vorher = ziel.Physics
    except Exception:  # noqa: BLE001
        phys_vorher = "?"
    mesh = None
    try:
        mesh = ziel.Mesh
    except Exception as ex:  # noqa: BLE001
        teile.append(f"kein Mesh: {ex}")
    if mesh is not None:
        try:
            mesh.AddImpulse(schub, ort, "", True)
            teile.append("Impuls aufs Mesh")
        except Exception as ex:  # noqa: BLE001
            teile.append(f"AddImpulse: {ex}")
            dump_funcs("SkeletalMeshComponent", "Impulse")  # Signatur ins selbe Log (Falle 5)
    try:
        ziel.SetPhysics(2)  # PHYS_Falling - fuer alles, was nicht im Ragdoll haengt
        ziel.Velocity = schub
        v = ziel.Velocity
        teile.append(f"Tempo {math.sqrt(v.X ** 2 + v.Y ** 2 + v.Z ** 2):.0f}, Physics {phys_vorher}->{ziel.Physics}")
    except Exception as ex:  # noqa: BLE001
        teile.append(f"Velocity: {ex}")
    return " + ".join(teile)


# --- Nachmessung des Rueckstosses (v0.78) -------------------------------------------------------
#
# "Tempo danach 910" heisst nur, dass die Zahl im Augenblick des Setzens dort stand. Ob der Gegner
# damit auch geflogen ist, sagt allein die Strecke, die er zurueckgelegt hat. Darum merkt sich
# _flug_merken jeden Gestossenen mit seinem Startpunkt, und der PlayerTick misst eine Sekunde
# spaeter nach. Erst diese Zahl ist die Antwort auf "er soll drei Meter zurueckfliegen".

FLUG_MESSUNG_S = 1.0
_flug_proben: list[tuple[str, Any, float, str, float]] = []  # (Pfad, Start, Rest, Beschriftung, Dauer)


def _flug_merken(ziel: UObject, label: str = "Rueckstoss", dauer: float = FLUG_MESSUNG_S) -> None:
    try:
        o = ziel.Location
        _flug_proben.append((ziel._path_name(), _vec(o.X, o.Y, o.Z), dauer, label, dauer))
    except Exception:  # noqa: BLE001
        pass


def _flug_nachmessen(dt: float) -> None:
    """Laeuft im PlayerTick, unabhaengig vom Zustand der Bombe."""
    global _flug_proben
    if not _flug_proben:
        return
    offen = []
    for pfad, start, rest, label, dauer in _flug_proben:
        rest -= dt
        if rest > 0:
            offen.append((pfad, start, rest, label, dauer))
            continue
        ziel = None
        for p in unrealsdk.find_all("WillowAIPawn", exact=False):
            if _ist_welt_actor(p) and p._path_name() == pfad:
                ziel = p
                break
        if ziel is None:
            logging.info(f"[ZB] {label} nachgemessen: {pfad.rsplit('.', 1)[-1]} nicht mehr da")
            continue
        try:
            weite = _abstand_uu(ziel.Location, start) / UU_JE_METER_A
            # GroundSpeed zum Messzeitpunkt (v0.88): zeigt, ob jemand den gesetzten Wert zurueckgeschrieben hat
            logging.info(f"[ZB] {label} nachgemessen: {ziel.Name} {weite:.1f} m in {dauer:.0f} s"
                         f" = {weite / dauer:.1f} m/s (Physics {ziel.Physics}, GroundSpeed jetzt {ziel.GroundSpeed:.0f})")
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] {label} nachgemessen: {ex}")
    _flug_proben = offen


def _umkreis_treffen(label: str, mitte: Any, radius_m: float, schaden: float,
                     stoss_uu: float, stagger: bool, weite_m: float = 0.0) -> int:
    """Alle lebenden Gegner im Umkreis treffen. Gibt die Zahl der Getroffenen zurueck.

    Die Schlusszeile nennt seit v0.73 auch, wie viele Gegner es ueberhaupt gab und wer der naechste
    war. "0 im Umkreis" allein trennt nicht, ob keiner nah genug stand oder ob die Suche nichts
    findet - und genau davor warnt Falle 2 (v0.72 prompt hineingelaufen).
    """
    pc = local_pc()
    if pc is None:
        return 0
    radius_uu = radius_m * UU_JE_METER_A
    n = 0
    alle = _gegner_lebend()
    naechster = ""
    beste = None
    for ziel in alle:
        try:
            d = _abstand_uu(ziel.Location, mitte)
        except Exception:  # noqa: BLE001
            continue
        if beste is None or d < beste:
            beste, naechster = d, str(ziel.Name)
        if d > radius_uu:
            continue
        n += 1
        wirkt = _schaden_gegen(ziel, schaden, weite_m) if schaden > 0 else 0.0
        logging.info(f"[ZB] {label}: {ziel.Name} auf {d / UU_JE_METER_A:.1f} m -> {_treffer(ziel, pc, wirkt, stoss_uu, mitte, stagger)}")
    naechste_info = f"naechster {naechster} auf {beste / UU_JE_METER_A:.1f} m" if beste is not None else "keiner gefunden"
    logging.info(f"[ZB] {label}: {n} von {len(alle)} lebenden Gegnern im Umkreis von {radius_m:.0f} m ({naechste_info})")
    return n


# --- Testziele spawnen (v0.77) ------------------------------------------------------------------
#
# Nutzerwunsch: der Rueckstoss laesst sich an echten Gegnern nicht beurteilen, weil sie waehrend des
# Fensters auf den Spieler zulaufen und damit von der Bombe weg. Also ein Ziel, das stehen bleibt.
#
# Weg: die Spawn-Factory aus Zer0s Stealth-BPD - dasselbe Objekt, mit dem das FL4K-Projekt sein Pet
# beschwoert (sdk/fl4k_pet/__init__.py, dort seit Monaten in Betrieb). Uebernommen wird von dort
# auch die Budget-Umgehung (UseCostOverride/SpawnCostOverride=0), ohne die das Populationssystem
# den Spawn in ruhigen Karten stillschweigend ablehnt.
#
# Was WIR anders machen: Statt ein Paket nachzuladen nehmen wir die Balance eines Gegners, der auf
# dieser Karte schon lebt (Eigenschaft BalanceDefinitionState.BalanceDefinition). Damit laeuft der
# Befehl ueberall, wo es etwas zu testen gibt - und wo keine Gegner sind, braucht es auch kein Ziel.
#
# Passiv wird das Ziel ueber die Fraktion: Allegiance_Player. Der Archetyp wird nur fuer den
# Augenblick des Spawns umgeschaltet und sofort zurueckgesetzt (FL4K-Muster) - sonst kaemen spaeter
# wilde Gegner derselben Art als Verbuendete zur Welt.

SPAWN_FACTORY = ("GD_Assassin_Skills.ActionSkill.Skill_Stealth:BehaviorProviderDefinition_0"
                 ".Behavior_SpawnFromPopulationSystem_0.PopulationFactoryBalancedAIPawn_0")
ALLEGIANCE_PLAYER = "GD_AI_Allegiance.Allegiance_Player"


def _vor_spieler(pawn: UObject, dist_uu: float) -> Any:
    """Punkt `dist_uu` Einheiten VOR dem Spieler, auf seiner Hoehe."""
    loc = pawn.Location
    yaw = pawn.Rotation.Yaw / 65536.0 * 2.0 * math.pi
    return _vec(loc.X + dist_uu * math.cos(yaw), loc.Y + dist_uu * math.sin(yaw), loc.Z)


def _balance_von_gegner() -> tuple[Any, str]:
    """Die Balance eines lebenden Gegners der Karte (Eigenschaft, kein Funktionsaufruf - v0.74)."""
    for g in _gegner_lebend():
        try:
            bal = g.BalanceDefinitionState.BalanceDefinition
            if bal is not None:
                return bal, str(g.Name)
        except Exception:  # noqa: BLE001
            continue
    return None, ""


def ziel_spawnen(anzahl: int = 1, abstand_m: float = 5.0) -> None:
    """zb ziel [ANZAHL] [ABSTAND] - stehende Testziele vor dem Spieler."""
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pc is None or pawn is None:
        logging.error("[ZB] ziel: kein Spieler-Pawn")
        return
    factory = _find("PopulationFactoryBalancedAIPawn", SPAWN_FACTORY)
    if factory is None:
        logging.error(f"[ZB] ziel: Spawn-Factory nicht gefunden ({SPAWN_FACTORY}) - Zer0s Paket nicht geladen?")
        return
    master = None
    for m in unrealsdk.find_all("WillowPopulationMaster"):
        if "Default__" not in m._path_name():
            master = m
    if master is None:
        logging.error("[ZB] ziel: kein WillowPopulationMaster")
        return
    balance, quelle = _balance_von_gegner()
    if balance is None:
        logging.error("[ZB] ziel: kein lebender Gegner auf der Karte, von dem eine Balance zu holen waere")
        return

    allegiance = _find("PawnAllegiance", ALLEGIANCE_PLAYER)
    try:
        # Feldname aus der Balance-Definition. VERMUTUNG (nicht per 'zb funcs' belegt) - schlaegt
        # sie fehl, bleibt die Fraktion beim Spawn unveraendert, und die Nachbereitung unten setzt
        # sie an der Instanz. Der Befehl funktioniert dann trotzdem.
        archetyp = balance.AIPawnArchetype
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] ziel: Archetyp der Balance nicht lesbar ({ex}) - Fraktion erst nach dem Spawn")
        archetyp = None
    # D6 (v0.91): Diese Factory gehoert ZER0 - sie spawnt sein Hologramm. Bis v0.90 blieb sie nach
    # 'zb ziel' auf die fremde Balance verbogen, ein echter Zer0 im selben Spielstart haette dann
    # Rakks statt Hologrammen bekommen. Also merken und im finally unten zuruecksetzen.
    alt_factory = (factory.PawnBalanceDefinition, factory.UseCostOverride, factory.SpawnCostOverride)
    factory.PawnBalanceDefinition = balance
    factory.UseCostOverride = True   # ohne das lehnt das Populationssystem ruhige Karten ab (FL4K)
    factory.SpawnCostOverride = 0
    gesetzt = None
    if archetyp is not None and allegiance is not None:
        gesetzt, archetyp.Allegiance = archetyp.Allegiance, allegiance
    vorher = {p._path_name() for p in unrealsdk.find_all("WillowAIPawn", exact=False)}
    gespawnt = 0
    try:
        for i in range(max(1, anzahl)):
            ort = _vor_spieler(pawn, abstand_m * UU_JE_METER_A + i * 200.0)
            try:
                neu = factory.SpawnAIPawn(
                    Master=master, SpawnLocationContextObject=pawn, SpawnLocation=ort,
                    SpawnRotation=pawn.Rotation, GameStage=pc.PlayerReplicationInfo.ExpLevel,
                    AwesomeLevel=0, bUseMemento=False,
                )
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] ziel: SpawnAIPawn: {ex}")
                break
            gespawnt += 1 if neu is not None else 0
            logging.info(f"[ZB] ziel {i + 1}: {'gespawnt ' + str(neu.Name) if neu is not None else 'SpawnAIPawn lieferte nichts'}")
    finally:
        if gesetzt is not None and archetyp is not None:
            archetyp.Allegiance = gesetzt  # wilde Gegner bleiben feindlich
        factory.PawnBalanceDefinition, factory.UseCostOverride, factory.SpawnCostOverride = alt_factory
        logging.info(f"[ZB] ziel: Zer0s Factory zurueckgesetzt (Balance {alt_factory[0].Name if alt_factory[0] else None})")
    # Die Neuen auch an der Instanz auf die Spielerfraktion setzen - der Archetyp wirkt nur beim
    # Spawn, und was danach kommt, soll trotzdem stehen bleiben.
    for p in unrealsdk.find_all("WillowAIPawn", exact=False):
        try:
            if p._path_name() in vorher or not _ist_welt_actor(p):
                continue
            if allegiance is not None:
                p.Allegiance = allegiance
            logging.info(f"[ZB] ziel: {p.Name} auf Spielerfraktion gesetzt, Leben {_leben(p):.0f}")
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] ziel: Nachbereitung: {ex}")
    logging.info(f"[ZB] ziel: {gespawnt} Ziel(e) aus der Balance von {quelle} ({balance.Name}) - sie greifen nicht an")


def gegner_zeigen(radius_m: float = 50.0) -> None:
    """zb gegner [RADIUS] - was die Umkreissuche sieht, ohne einen Skill zu bemuehen (v0.73).

    Beantwortet in einer Zeile, was v0.72 offengelassen hat: findet find_all("WillowAIPawn") auf
    dieser Karte ueberhaupt etwas, leben die, und wie weit sind sie weg?
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] gegner: kein Spieler-Pawn")
        return
    roh = list(unrealsdk.find_all("WillowAIPawn", exact=False))
    welt = [p for p in roh if _ist_welt_actor(p)]
    lebend = _gegner_lebend()
    mitte = pawn.Location
    mit_abstand = []
    for g in lebend:
        try:
            mit_abstand.append((_abstand_uu(g.Location, mitte) / UU_JE_METER_A, g))
        except Exception:  # noqa: BLE001
            continue
    mit_abstand.sort(key=lambda t: t[0])
    logging.info(f"[ZB] gegner: {len(roh)} WillowAIPawn gefunden, davon {len(welt)} in der Welt, {len(lebend)} lebend")
    for d, g in mit_abstand[:10]:
        marke = "  <- in Reichweite" if d <= radius_m else ""
        logging.info(f"[ZB] gegner: {d:6.1f} m  {g.Name}  Leben {_leben(g):.0f}{marke}")
    # Was die Suche liefert - NUR Pfadnamen. Der Pfad kommt aus dem SDK, dafuer muss die Engine
    # nichts tun; genau deshalb ist diese Zeile nach dem Absturz von v0.74 die erste, die laeuft.
    logging.info("[ZB] gegner: die ersten 15 Pfade (ungefiltert)")
    for p in roh[:15]:
        try:
            logging.info(f"[ZB] gegner:   {p._path_name()}")
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] gegner:   <{ex}>")
    # Und fuer die Welt-Actors die Eigenschaften, die den Lebend-Filter entscheiden. Auch hier:
    # kein einziger Funktionsaufruf.
    logging.info("[ZB] gegner: Welt-Actors (Pfad | Feld Health | HealthPool | bDeleteMe | Ort)")
    for p in welt[:12]:
        werte = []
        for name, hol in (("Health", lambda o: o.Health),
                          ("HealthPool", lambda o: o.HealthPool.Data.CurrentValue),
                          ("bDeleteMe", lambda o: o.bDeleteMe),
                          ("Ort", lambda o: f"({o.Location.X:.0f},{o.Location.Y:.0f},{o.Location.Z:.0f})")):
            try:
                werte.append(f"{name}={hol(p)}")
            except Exception as ex:  # noqa: BLE001
                werte.append(f"{name}=<{ex}>")
        logging.info(f"[ZB] gegner:   {p._path_name()} | " + " | ".join(werte))


def ammo_zeigen() -> None:
    """zb ammo - wo die Munitionsreserve wirklich steht (v0.73).

    v0.72 hat auf pc.LastKnownAmmoCount_* gesetzt: die Summe blieb ueber einen ganzen Kampf bei
    1027, obwohl geschossen wurde - die Felder sind nicht live (vermutlich nur HUD-Zwischenstand).
    Also die Pools selbst suchen: AmmoResourcePool-Objekte, die Pool-Felder der Waffe und der
    ResourcePoolManager. Was davon mitzaehlt, zeigt der Vergleich vor/nach dem Schiessen.
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pc is None:
        logging.error("[ZB] ammo: kein Controller")
        return
    n = 0
    for pool in unrealsdk.find_all("AmmoResourcePool", exact=False):
        try:
            if "Default__" in pool._path_name():
                continue
            defi = pool.Definition
            logging.info(f"[ZB] ammo Pool: {getattr(defi, 'Name', '?')} = {float(pool.CurrentValue):.0f}"
                         f" (Def {defi._path_name() if defi else '-'})")
            n += 1
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] ammo Pool: <{ex}>")
    logging.info(f"[ZB] ammo: {n} AmmoResourcePool(s)")
    logging.info(f"[ZB] ammo: LastKnownAmmoCount-Summe = {_ammo_summe(pc):.0f} (v0.72: aendert sich nicht)")
    if pawn is not None and pawn.Weapon is not None:
        dump_props(pawn.Weapon, "ammo")
        dump_props(pawn.Weapon, "pool")
    dump_props(pc, "pool")


# --- Erinnerung (Baum 1, Tier 4, Rang 1) - v0.71 -----------------------------------------------
#
# "Der Anker speichert Kill-Skill-Zustaende; beim Zuenden sind sie wieder da." Abgrenzung zu
# Deja-vu: Deja-vu frischt IMMER auf, Erinnerung stellt nur her, was beim LEGEN lief. Wer beides
# hat, merkt keinen Unterschied - wer nur Erinnerung hat, rettet seine laufenden Kill Skills ueber
# den Sprung. Gleiche Technik (UpdateKillSkills, v0.70 gemessen), anderer Ausloeser.
#
# Die "Stacks" aus dem Entwurf (docs/skills.md) bleiben vorerst aussen vor: Gespannte Zeit und
# Abstand sind unsere eigenen und enden mit dem Zuenden per Design; fremde Stack-Skills muessten
# einzeln erfasst werden. Steht im Skilltext nicht, also kein Bruch - aber hier notiert.

_erinnerung_stacks = 0  # v1.13: Kill-Stacks beim Legen


def mechanik_erinnerung_gelegt() -> None:
    global _erinnerung_stacks
    _erinnerung_stacks = 0
    if skill_rang("Erinnerung") <= 0:
        return
    _erinnerung_stacks = _kill_stacks
    logging.info(f"[ZB] Erinnerung: {_erinnerung_stacks} Kill-Stacks beim Legen gespeichert")


def mechanik_erinnerung_gezuendet() -> bool:
    """v1.13: Der Stapel vom Legen kommt beim Zuenden zurueck, wenn er inzwischen geschrumpft ist
    (sind es jetzt mehr, bleibt es dabei). Die Frist beginnt neu."""
    global _kill_stacks
    if skill_rang("Erinnerung") <= 0 or _erinnerung_stacks <= 0:
        return False
    vorher = _kill_stacks
    if _erinnerung_stacks > _kill_stacks:
        _kill_stacks = _erinnerung_stacks
        _kill_stacks_anwenden("Erinnerung")
    kill_stacks_festhalten("Erinnerung")
    logging.info(f"[ZB] Erinnerung: Kill-Stacks {vorher} -> {_kill_stacks} (beim Legen {_erinnerung_stacks})")
    return True


# --- Die fuenf Skills von Paket A ---------------------------------------------------------------

NACHHALL_RADIUS_M = 6.0
# Wunsch des Nutzers (2026-09-23): etwa 3 m zurueckfliegen, nicht nur umfallen. Aus der Wurfweite
# gerechnet statt geschaetzt: bei 45 Grad ist R = v^2 / g, also v = sqrt(g * R). Mit g = 980 uu/s^2
# (UE3-Standard) und R = 300 uu sind das rund 542 uu/s, die _treffer in zwei gleiche Anteile
# waagerecht und senkrecht zerlegt. Stimmt die Schwerkraft in BL2 nicht, sagt es die Nachmessung.
NACHHALL_WEITE_M = 3.0
SCHWERKRAFT_UU = 980.0
NACHHALL_STOSS_UU = math.sqrt(SCHWERKRAFT_UU * NACHHALL_WEITE_M * 100.0)  # seit v1.13 ungenutzt (Rueckstoss geparkt)
NACHHALL_FAKTOR = 2.0            # v1.13: x Granatenschaden der Schockwelle
RUECKSPRUNG_JE_RANG = 0.20      # Rueckenwind (v0.97): +20 % Feuerrate/Nachladetempo je Rang
RUECKSPRUNG_VOLL_M = 50.0       # ab dieser Entfernung zum Anker volle Wirkung, darunter linear
RUECKSPRUNG_DAUER_S = 10.0      # fest, skaliert nicht mit dem Rang (Nutzerwunsch)
ZEITSPRUNG_BREITE_M = 4.0        # halber Korridor links/rechts der Linie
ZEITSPRUNG_UNVERWUNDBAR_S = 1.0  # seit v1.12 ueber immunitaet()
REINIGUNG_IMMUN_S = 2.0
RUECKERSTATTUNG_JE_RANG = 0.20

# Die Munitionsreserven, die das HUD liest (v0.71 an pc abgelesen). Granaten bleiben absichtlich
# drin: verbraucht ist verbraucht, und der Skilltext schliesst nichts aus.
AMMO_FELDER = ("LastKnownAmmoCount_CombatRifle", "LastKnownAmmoCount_Grenades",
               "LastKnownAmmoCount_RepeaterPistol", "LastKnownAmmoCount_RevolverPistol",
               "LastKnownAmmoCount_RocketLauncher", "LastKnownAmmoCount_SMG",
               "LastKnownAmmoCount_Shotgun", "LastKnownAmmoCount_SniperRifle")

_ammo_beim_legen: dict[str, float] = {}
_absprung: Any = None  # wo der Spieler beim Zuenden stand, VOR dem Teleport


def _ammo_summe(pc: UObject) -> float:
    """Nur noch fuer den Vergleich im Log: die HUD-Felder. v0.73 gemessen - sie bewegen sich nicht."""
    summe = 0.0
    for feld in AMMO_FELDER:
        try:
            summe += float(getattr(pc, feld))
        except Exception:  # noqa: BLE001
            continue  # den Typ gibt es nicht an dieser Klasse - kein Grund zu klagen
    return summe


def _ammo_pools() -> dict[str, UObject]:
    """Die echten Munitionspools, nach Definitionsnamen (v0.73 im Spiel abgelesen).

    Sechs Stueck, `CurrentValue` ist live: Ammo_Repeater_Pistol_Pool fiel beim Schiessen von 152 auf
    106, waehrend die LastKnownAmmoCount-Summe bei 1047 stehen blieb. Nie cachen - die Pools haengen
    an der Welt (CLAUDE.md).
    """
    pools: dict[str, UObject] = {}
    for pool in unrealsdk.find_all("AmmoResourcePool", exact=False):
        try:
            if "Default__" in pool._path_name() or pool.Definition is None:
                continue
            pools[str(pool.Definition.Name)] = pool
        except Exception:  # noqa: BLE001
            continue
    return pools


def mechanik_ammo_gelegt(pc: UObject) -> None:
    """Pro Pool den Stand beim Legen merken - der ist zugleich die Obergrenze der Erstattung."""
    global _ammo_beim_legen
    _ammo_beim_legen = {}
    for name, pool in _ammo_pools().items():
        try:
            _ammo_beim_legen[name] = float(pool.CurrentValue)
        except Exception:  # noqa: BLE001
            continue
    if skill_rang("VolleRueckerstattung") > 0:
        logging.info(f"[ZB] Volle Rueckerstattung: Reserve beim Legen {sum(_ammo_beim_legen.values()):.0f}"
                     f" in {len(_ammo_beim_legen)} Pools")


def mechanik_rueckerstattung(pc: UObject, pawn: UObject) -> bool:
    """Volle Rueckerstattung: 20 % je Rang der seit dem Legen verbrauchten Reserve zurueck.

    Gerechnet wird je Pool, direkt auf CurrentValue (Pools setzen ist seit Spike B belegt - so
    stellt auch das Zuenden Leben und Schild her). Der Stand beim Legen ist die Obergrenze: mehr
    als da war, kann nie herauskommen, und ein Maximalwert muss dafuer gar nicht bekannt sein.
    """
    rang = skill_rang("VolleRueckerstattung")
    if rang <= 0:
        return False
    anteil = min(1.0, RUECKERSTATTUNG_JE_RANG * rang)
    pools = _ammo_pools()
    zeilen, verbraucht_ges, zurueck_ges = [], 0.0, 0.0
    for name, vorher in _ammo_beim_legen.items():
        pool = pools.get(name)
        if pool is None:
            continue
        try:
            jetzt = float(pool.CurrentValue)
            verbraucht = vorher - jetzt
            if verbraucht <= 0:
                continue
            neu = min(vorher, jetzt + verbraucht * anteil)
            pool.CurrentValue = neu
            gelesen = float(pool.CurrentValue)
            verbraucht_ges += verbraucht
            zurueck_ges += gelesen - jetzt
            zeilen.append(f"{name}: {vorher:.0f} -> {jetzt:.0f} -> {gelesen:.0f}")
        except Exception as ex:  # noqa: BLE001
            zeilen.append(f"{name}: <{ex}>")
    if not zeilen:
        logging.info(f"[ZB] Volle Rueckerstattung: nichts verbraucht (Rang {rang})")
        return False
    logging.info(f"[ZB] Volle Rueckerstattung: Rang {rang} = {anteil * 100:.0f} %, verbraucht {verbraucht_ges:.0f}, "
                 f"zurueck {zurueck_ges:.0f} | " + " | ".join(zeilen))
    return True


def mechanik_reinigung(pawn: UObject) -> bool:
    """Reinigung: Zuenden entfernt alle Statuseffekte, danach 2 s Schadensimmunitaet (seit v1.12
    ueber die versteckten Effekt-Skills ZB_Immun_A/B, s. immunitaet())."""
    if skill_rang("Reinigung") <= 0:
        return False
    try:
        pawn.RemoveAllStatusEffects()
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Reinigung: RemoveAllStatusEffects: {ex}")
        return False
    logging.info("[ZB] Reinigung: alle Statuseffekte entfernt")
    immunitaet(REINIGUNG_IMMUN_S, "Reinigung")
    return True


def mechanik_nachhall(pawn: UObject) -> bool:
    """Nachhall, seit v1.13 eine SCHOCKWELLE (Nutzerentscheidung 2026-09-26): an der Ankunft eine
    Schock-Explosion in 6 m mit 2 x Granatenschaden, und alle darin werden aus dem Tritt gebracht.
    Der Rueckstoss bis v1.12 wirkte an Bodengegnern nie (PHYS_NavMeshWalking, docs/spikes.md) -
    Stagger ja (v0.77 gemessen). Laeuft nach dem Teleport, der Spieler ist Ursprung (wie Sprengsatz)."""
    if skill_rang("Nachhall") <= 0:
        return False
    basis, quelle = _granaten_schaden(pawn, _granate(pawn))
    explodieren(pawn, "Nachhall", FX_NACHHALL, basis * NACHHALL_FAKTOR, NACHHALL_RADIUS_M * UU_JE_METER_A,
                f"{NACHHALL_FAKTOR:.0f} x {basis:.0f} ({quelle})")
    return _umkreis_treffen("Nachhall", pawn.Location, NACHHALL_RADIUS_M, 0.0, 0.0, True) >= 0


def mechanik_ruecksprung_detonation(pawn: UObject, anker: Any) -> bool:
    """Rueckenwind (Objektname bleibt RuecksprungDetonation, v0.97): nach dem Zuenden 10 s mehr
    Feuerrate und Nachladetempo, je weiter vom Anker, desto mehr - bis +20 % je Rang (R5 = +100 %),
    voll ab RUECKSPRUNG_VOLL_M. Die Dauer ist fest (Effekt-Skill, dauer=10).

    Umrechnung: das Spiel skaliert das INTERVALL (Fast Hands -0,05, Metal Storm -0,12 je Rang, Dump).
    +b Tempo heisst Intervall / (1 + b), also Skalierung -b/(1+b); +100 % = -50 %, nicht -100 %
    (das waere Intervall 0). Der Effekt-Skill rechnet -0,01 je Grad -> Grad = round(100 b/(1+b)).
    Laeuft in zuenden() VOR dem Teleport, weil nur dort die Entfernung zum Anker messbar ist."""
    rang = skill_rang("RuecksprungDetonation")
    if rang <= 0:
        return False
    weite_m = _abstand_uu(anker, pawn.Location) / UU_JE_METER_A
    bonus = RUECKSPRUNG_JE_RANG * rang * min(1.0, weite_m / RUECKSPRUNG_VOLL_M)
    grad = round(100.0 * bonus / (1.0 + bonus))
    logging.info(f"[ZB] Rueckenwind: {weite_m:.1f} m vom Anker, Rang {rang} -> +{bonus * 100:.0f} % Tempo"
                 f" = Intervall x {1 - grad / 100:.2f} (Grad {grad}), 10 s")
    if grad <= 0:
        return False
    def intervalle() -> str:
        w = pawn.Weapon
        if w is None:
            return "keine Waffe"
        try:
            return (f"Attr FireInterval {attr_value('AttributeDefinition', A_FEUERRATE, w):.4f},"
                    f" ReloadSpeed {attr_value('AttributeDefinition', A_NACHLADEN, w):.4f};"
                    f" Waffe FireInterval {float(w.FireInterval):.4f} (Basis {float(w.FireIntervalBaseValue):.4f}),"
                    f" ReloadTime {float(w.ReloadTime):.4f} (Basis {float(w.ReloadTimeBaseValue):.4f})")
        except Exception as ex:  # noqa: BLE001
            return f"nicht lesbar ({ex})"
    vorher = intervalle()
    # v0.98: Scale-Boni addieren sich auf die BASIS (CLAUDE.md). v0.97 gemessen: Grad 50 (-50 %)
    # brachte nur x0,71, weil die Waffe schon +74 % aufs Intervall traegt. Darum je Waffe und je
    # Attribut den Wert ausrechnen, der den AKTUELLEN Wert durch (1 + b) teilt, und mit Grad 1
    # einschalten (Wert = BaseModifierValue). Geht das nicht, bleibt der Grad-Weg von v0.97.
    wirkung_aus("RuecksprungDetonation")   # erst aus, damit der Istwert ohne den alten Buff gelesen wird
    grad = _rueckenwind_werte(pawn, bonus) or grad
    ok = wirkung_an("RuecksprungDetonation", grad)
    logging.info(f"[ZB] Rueckenwind gemessen: vorher {vorher} | nachher {intervalle()}")
    global _rueckenwind_probe
    _rueckenwind_probe = (1.0, intervalle)   # eine Sekunde spaeter noch einmal (Waffenfeld traege?)
    if ok:
        _wirkung_uhren["RuecksprungDetonation"] = RUECKSPRUNG_DAUER_S
        # Phase 8 (v1.04): der Buff wird sichtbar - kleine Nova am Spieler, nach der Ankunft
        effekt("Rueckenwind", FX_NACHHALL, None, 300.0, verzoegerung=0.5)
    return ok


def _rueckenwind_werte(pawn: UObject, bonus: float) -> int:
    """Effektwerte des Rueckenwind-Wirkungsskills fuer die aktuelle Waffe setzen. Gibt 1 zurueck
    (einschalten mit Grad 1), oder 0, wenn etwas nicht lesbar war (dann gilt der alte Grad-Weg)."""
    w = pawn.Weapon
    wirk = skill_def("RuecksprungDetonation", wirkung=True)
    if w is None or wirk is None:
        return 0
    liste = wirk.SkillEffectDefinitions
    teile = []
    for i, (attr, basis_feld) in enumerate(((A_FEUERRATE, "FireIntervalBaseValue"), (A_NACHLADEN, "ReloadTimeBaseValue"))):
        jetzt = attr_value("AttributeDefinition", attr, w)
        try:
            basis = float(getattr(w, basis_feld))
            jetzt = float(jetzt)
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] Rueckenwind: {basis_feld}/{attr} nicht lesbar ({ex}) - Grad-Weg")
            return 0
        if basis <= 0 or jetzt <= 0:
            return 0
        # v0.99, gemessen an drei Punkten (v0.97/v0.98): BL2 TEILT bei negativer Summe -
        # Wert = Basis / (1 + |Summe|), sonst Basis * (1 + Summe). Also die Gesamtsumme vorher und
        # nachher aus Ist- und Zielwert zurueckrechnen; der Effektwert ist die Differenz.
        def summe(v: float) -> float:
            return v / basis - 1.0 if v >= basis else -(basis / v - 1.0)
        ziel = jetzt / (1.0 + bonus)
        wert = summe(ziel) - summe(jetzt)
        try:
            liste[i].BaseModifierValue.BaseValueConstant = wert
            liste[i].PerGradeUpgrade.BaseValueConstant = wert
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] Rueckenwind: Effekt {i} nicht setzbar ({ex}) - Grad-Weg")
            return 0
        teile.append(f"{basis_feld[:-9]} {jetzt:.4f} -> Ziel {ziel:.4f} (Skalierung {wert:+.3f} auf Basis {basis:.4f})")
    logging.info(f"[ZB] Rueckenwind: je Waffe gerechnet: {'; '.join(teile)}")
    return 1


_wirkung_uhren: dict[str, float] = {}   # HS-Wirkungen, die das Modul nach Ablauf selbst abschaltet


_rueckenwind_probe: Any = None   # (Restzeit, Messfunktion)


def _wirkung_uhren_tick(dt: float) -> None:
    global _rueckenwind_probe
    if _rueckenwind_probe is not None:
        rest, messen = _rueckenwind_probe
        if rest - dt <= 0:
            _rueckenwind_probe = None
            logging.info(f"[ZB] Rueckenwind nach 1 s: {messen()}")
        else:
            _rueckenwind_probe = (rest - dt, messen)
    for name in list(_wirkung_uhren):
        _wirkung_uhren[name] -= dt
        if _wirkung_uhren[name] <= 0:
            del _wirkung_uhren[name]
            wirkung_aus(name)


def mechanik_zeitsprung(pawn: UObject) -> bool:
    """Zeitsprung (Capstone): alle Gegner auf der Linie zwischen Absprung und Ankunft werden
    verletzt und gestaggert, Schaden nach Entfernung.

    Der Korridor ist ein Zylinder um die Strecke: fuer jeden Gegner der Lotabstand zur Linie, und
    nur wer naeher als ZEITSPRUNG_BREITE_M liegt und zwischen den Endpunkten steht, wird getroffen.
    Die 1 s Unverwundbarkeit aus dem Entwurf fehlt noch - gleicher Grund wie bei Reinigung.
    """
    if skill_rang("Zeitsprung") <= 0 or _absprung is None:
        return False
    immunitaet(ZEITSPRUNG_UNVERWUNDBAR_S, "Zeitsprung")   # v1.12
    pc = local_pc()
    ziel = pawn.Location
    ax, ay, az = _absprung.X, _absprung.Y, _absprung.Z
    dx, dy, dz = ziel.X - ax, ziel.Y - ay, ziel.Z - az
    laenge2 = dx * dx + dy * dy + dz * dz
    if laenge2 >= 1.0:
        # Phase 8 (v1.00): die Blitzspur vom Absprung zur Ankunft
        effekt_spur("Zeitsprung-Spur", _absprung, _vec(ziel.X, ziel.Y, ziel.Z))
    if pc is None or laenge2 < 1.0:
        logging.info("[ZB] Zeitsprung: Absprung und Ankunft liegen aufeinander")
        return False
    weite_m = math.sqrt(laenge2) / UU_JE_METER_A
    schaden = _schaden_basis(pawn) * (weite_m / 10.0)
    breite_uu = ZEITSPRUNG_BREITE_M * UU_JE_METER_A
    n = 0
    for g in _gegner_lebend():
        try:
            o = g.Location
            # Lotfusspunkt auf der Strecke, auf [0,1] begrenzt: t=0 Absprung, t=1 Ankunft
            t = ((o.X - ax) * dx + (o.Y - ay) * dy + (o.Z - az) * dz) / laenge2
            if t < 0.0 or t > 1.0:
                continue
            lot = _vec(ax + dx * t, ay + dy * t, az + dz * t)
            d = _abstand_uu(o, lot)
        except Exception:  # noqa: BLE001
            continue
        if d > breite_uu:
            continue
        n += 1
        wirkt = _schaden_gegen(g, schaden, weite_m)
        logging.info(f"[ZB] Zeitsprung: {g.Name} {d / UU_JE_METER_A:.1f} m neben der Linie -> {_treffer(g, pc, wirkt, 200.0, lot, True)}")
    logging.info(f"[ZB] Zeitsprung: {weite_m:.1f} m Strecke, {schaden:.0f} Schaden je Treffer, {n} Gegner auf der Linie (Unverwundbarkeit fehlt noch)")
    return True


# =================================================================================================
# Handgriff 4, Paket B (v0.84): Paradoxon, Vorbelastung, Zeitspur
#
# Paradoxon und Vorbelastung muessen wissen, wen der Spieler mit liegender Bombe getroffen hat und
# wie hart. Dafuer ein Hook auf WillowGame.WillowAIPawn:TakeDamage (Klasse im Dump geprueft:
# Class'WillowGame.WillowAIPawn'), PRE und POST:
#   PRE  merkt sich das Leben des Ziels (Eigenschaft Health - v0.75 an KI-Pawns belegt)
#   POST rechnet die Differenz: DAS ist der Schaden, der ankam - nicht der Parameter, der noch vor
#        Resistenzen und Krit steht. Hat ein Schild alles geschluckt (Differenz 0), zaehlt der
#        Parameter, damit Treffer auf Schildgegner nicht verloren gehen.
#
# Drei Vorsichtsmassnahmen, alle aus Fehlern dieser Sitzung abgeleitet:
#   - Der Hook feuert bei JEDEM Schaden im Spiel. Die erste Pruefung ist daher reines Python ohne
#     Engine-Zugriff (_schaden_zaehlt), und die Raenge werden beim Legen einmal gelesen statt pro
#     Kugel (skill_rang ist ein Funktionsaufruf).
#   - Kein Schaden aus dem Hook heraus. Vorbelastungs-Nachschlag kommt in eine Warteschlange und wird
#     im naechsten PlayerTick ausgeteilt - ein TakeDamage mitten in TakeDamage waere Reentrancy
#     ins Ungewisse.
#   - _eigen: waehrend WIR Schaden austeilen, bucht der Hook nicht und verstaerkt nicht. Sonst
#     wuerde Paradoxon sich selbst ins Buch schreiben und Vorbelastung sich endlos nachschlagen.
#
# NICHT GEPRUEFT: ob TakeDamage beim echten Waffentreffer ueber diesen Weg laeuft oder nativ daran
# vorbei (wie NotifyKilled, v0.65). Die Spur-Zeile im Hook beantwortet das beim ersten Schuss.

TAKE_DAMAGE_FUNC = "WillowGame.WillowAIPawn:TakeDamage"
PARADOXON_ANTEIL = 0.5
VORBELASTUNG_JE_RANG = 0.05
VORBELASTUNG_DAUER_S = 8.0
ZEITSPUR_RADIUS_M = 8.0
ZEITSPUR_DAUER_S = 3.0
ZEITSPUR_FAKTOR = 0.5   # CustomTimeDilation: 0,5 = halbes Tempo fuer alles, was der Pawn selbst tickt

_eigen = False
_rang_para = 0
_rang_vorb = 0
_rang_zeitspur = 0
_leben_vor: dict[str, float] = {}
_buch: dict[str, float] = {}               # Paradoxon: Pfad -> Schaden mit liegender Bombe
_markiert: set[str] = set()                # Vorbelastung: wer mit liegender Bombe getroffen wurde
_vorbelastung_bis = 0.0                    # Spielzeit, bis zu der der Bonus gilt
_nachschlag: dict[str, list] = {}          # Pfad -> [WeakPointer, Summe] fuer den naechsten Tick
_verlangsamt: dict[str, list] = {}         # Pfad -> [WeakPointer, Restzeit, CTD, GroundSpeed, AirSpeed] (Originale)
_schaden_spur_gemeldet = False             # der erste gezaehlte Treffer wird einmal geloggt


def _schaden_zaehlt() -> bool:
    """Die billige Vorpruefung - nur Python-Variablen, kein Engine-Zugriff."""
    if _eigen:
        return False
    if _state == ZUSTAND_GELEGT:
        return _rang_para > 0 or _rang_vorb > 0
    return bool(_markiert) and _vorbelastung_bis > 0.0


def _arg(args: Any, *namen: str) -> Any:
    """Ein Argument unter einem von mehreren Namen. TakeDamage heisst je nach Klasse Damage/
    DamageAmount und InstigatedBy/EventInstigator (beides in 'zb namen' gesehen)."""
    for n in namen:
        try:
            return getattr(args, n)
        except Exception:  # noqa: BLE001
            continue
    return None


def _on_take_damage_pre(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    if not _schaden_zaehlt():
        return None
    _filter_zaehlen("PRE erreicht")
    try:
        pfad = obj._path_name()
        leben = _leben(obj)  # v0.86: NICHT obj.Health - das Feld gibt es an WillowAIPawn nicht
        if leben >= 0:
            _leben_vor[pfad] = leben
    except Exception:  # noqa: BLE001
        pass
    return None


def _on_take_damage_post(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _schaden_spur_gemeldet
    if not _schaden_zaehlt():
        return
    try:
        pfad = obj._path_name()
    except Exception:  # noqa: BLE001
        return
    _filter_zaehlen("POST erreicht")
    vorher = _leben_vor.pop(pfad, None)
    if WELT_MARKE not in pfad:
        _filter_zaehlen("verworfen: kein Welt-Actor", pfad)
        return
    pc = local_pc()
    urheber = _arg(args, "InstigatedBy", "EventInstigator")
    try:
        if pc is None or urheber is None:
            _filter_zaehlen("verworfen: kein Urheber", pfad)
            return
        upfad = urheber._path_name()
        # Der Urheber kann der Controller ODER der Pawn sein - welcher, ist nicht belegt.
        if upfad != pc._path_name() and (pc.Pawn is None or upfad != pc.Pawn._path_name()):
            _filter_zaehlen("verworfen: fremder Urheber", upfad)
            return
    except Exception as ex:  # noqa: BLE001
        _filter_zaehlen("verworfen: Urheber nicht lesbar", str(ex))
        return
    try:
        param = float(_arg(args, "Damage", "DamageAmount") or 0.0)
    except Exception:  # noqa: BLE001
        param = 0.0
    nachher = _leben(obj)  # v0.86: an diesem Feldzugriff sind in v0.85 ALLE eigenen Treffer gescheitert
    if nachher < 0:
        _filter_zaehlen("verworfen: Leben nicht lesbar", pfad)
        return
    nachher = max(0.0, nachher)
    diff = (vorher - nachher) if vorher is not None else 0.0
    wert = diff if diff > 0 else param
    if wert <= 0:
        _filter_zaehlen("verworfen: Schaden 0", f"Parameter {param}, Leben {vorher} -> {nachher}")
        return
    _filter_zaehlen("gezaehlt")
    if not _schaden_spur_gemeldet:
        _schaden_spur_gemeldet = True
        logging.info(f"[ZB] Schadens-Hook traegt: {obj.Name} Parameter {param:.0f}, Leben {vorher} -> {nachher:.0f}")
    if _state == ZUSTAND_GELEGT:
        if _rang_para > 0:
            _buch[pfad] = _buch.get(pfad, 0.0) + wert
        if _rang_vorb > 0:
            _markiert.add(pfad)
        return
    # Nach dem Zuenden: Vorbelastung, solange das Fenster offen ist.
    if pfad in _markiert and _game_time(pc) < _vorbelastung_bis:
        eintrag = _nachschlag.setdefault(pfad, [WeakPointer(obj), 0.0])
        eintrag[1] += wert * VORBELASTUNG_JE_RANG * _rang_vorb


# --- Diagnose fuer Paket B (v0.85) --------------------------------------------------------------
#
# v0.84 im Spiel: kein einziger Treffer gebucht, die Zeile "Schadens-Hook traegt" kam nie. Ob
# TakeDamage gar nicht feuert (wie NotifyKilled in v0.65) oder ob der Urheber-Vergleich alles
# verwirft, war aus dem Log NICHT zu trennen - Falle 2, zum dritten Mal. Jetzt zaehlen wir beides:
#   - Zaehl-Hooks auf sieben Kandidaten, jeder nur ein Zaehler plus der erste Aufruf im Wortlaut
#   - im eigentlichen Hook: wie oft PRE/POST kamen und warum verworfen wurde
# 'zb schaden' gibt alles aus. Pakete geprueft (Class=-Zeile): WillowPawn in WillowGame,
# GearboxPawn in GearboxFramework, Pawn und Actor in Engine.

SCHADEN_KANDIDATEN = (
    "WillowGame.WillowAIPawn:TakeDamage",
    "WillowGame.WillowPawn:TakeDamage",
    "GearboxFramework.GearboxPawn:TakeDamage",
    "Engine.Pawn:TakeDamage",
    "Engine.Actor:TakeDamage",
    "WillowGame.WillowAIPawn:ActorTakeDamageInner",
    "WillowGame.WillowPawn:ActorTakeDamageInner",
)
_schaden_zaehler: dict[str, int] = {}
_schaden_erster: dict[str, str] = {}
_schaden_filter: dict[str, int] = {}
_schaden_filter_beispiel: dict[str, str] = {}


def _filter_zaehlen(grund: str, beispiel: str = "") -> None:
    _schaden_filter[grund] = _schaden_filter.get(grund, 0) + 1
    if beispiel and grund not in _schaden_filter_beispiel:
        _schaden_filter_beispiel[grund] = beispiel


def _make_schaden_zaehler(fname: str):
    def zaehler(obj: UObject, args: Any, ret: Any, func: Any) -> None:
        _schaden_zaehler[fname] = _schaden_zaehler.get(fname, 0) + 1
        if fname in _schaden_erster:
            return
        try:
            urheber = _arg(args, "InstigatedBy", "EventInstigator")
            wert = _arg(args, "Damage", "DamageAmount")
            _schaden_erster[fname] = (f"{obj.Name} ({obj.Class.Name}), Schaden {wert}, "
                                      f"Urheber {urheber._path_name() if urheber is not None else None}")
        except Exception as ex:  # noqa: BLE001
            _schaden_erster[fname] = f"<{ex}>"
    return zaehler


def schaden_zeigen() -> None:
    """zb schaden - welcher Kandidat feuert beim Schiessen, und was filtert der Hook weg."""
    pc = local_pc()
    logging.info(f"[ZB] schaden: eigener Controller = {pc._path_name() if pc else None}, "
                 f"Pawn = {pc.Pawn._path_name() if pc and pc.Pawn else None}")
    for fname in SCHADEN_KANDIDATEN:
        n = _schaden_zaehler.get(fname, 0)
        logging.info(f"[ZB] schaden: {n:6d}x  {fname}" + (f"  | erster: {_schaden_erster[fname]}" if n else ""))
    for grund, n in sorted(_schaden_filter.items()):
        logging.info(f"[ZB] schaden: Hook {grund}: {n}x" +
                     (f"  | Beispiel: {_schaden_filter_beispiel[grund]}" if grund in _schaden_filter_beispiel else ""))
    logging.info("[ZB] schaden: weitere Kandidaten am Controller:")
    dump_funcs("WillowPlayerController", "Damage")


def schaden_zuruecksetzen() -> None:
    _schaden_zaehler.clear()
    _schaden_erster.clear()
    _schaden_filter.clear()
    _schaden_filter_beispiel.clear()
    logging.info("[ZB] schaden: Zaehler auf null")


ZEITLUPE_MESSUNG_S = 3.0  # eine Sekunde war zu verrauscht (v0.85: stehende Gegner sahen aus wie eingefroren)
_erzwungen: dict[str, float] = {}  # Pfad -> Faktor, fuer Art 4 jeden Frame nachgeschrieben


def zeitlupe_versuch(art: int, faktor: float, radius_m: float = 15.0, dauer_s: float = 5.0) -> None:
    """zb zeitlupe [ART] [FAKTOR] [RADIUS] - Verlangsamen an Gegnern ringsum ausprobieren (v0.85).

    v0.84: CustomTimeDilation = 0.5 steht nachweislich am Pawn (nachgelesen), der Nutzer sah aber
    keine Zeitlupe. Also wie beim Rueckstoss: Varianten ausprobieren und messen, statt zu raten.
      0  nichts aendern, nur messen            (der Vergleichswert)
      1  CustomTimeDilation = FAKTOR           (der Weg aus v0.84)
      2  GroundSpeed und AirSpeed x FAKTOR     (Bewegungstempo - Felder am Pawn, im Dump 440)
      3  beides
      4  GroundSpeed/AirSpeed x FAKTOR, JEDEN FRAME erzwungen (v0.88)
    Gemessen wird die Strecke in 3 s (_flug_nachmessen) - am besten an Gegnern, die auf einen
    zulaufen: Art 0 gibt die normale Strecke, Art 1-4 zeigen, ob sie kuerzer wird.

    v0.85/v0.86 im Spiel: Art 1 (CustomTimeDilation 0,3) - Nutzer: "ist nichts passiert"; die
    gemessenen 0,0 m waren Zufall (Gegner standen beim Zuschlagen). Art 2 streute (1,4 / 3,4 m). Der
    Verdacht fuer Art 4: GroundSpeed wird laufend aus einem Attribut neu gesetzt (beim Spieler speist
    FootSpeed ihn, *Weite* 440 -> 506), einmal setzen haelt dann nur bis zum naechsten Frame.
    Die Nachmessung liest GroundSpeed mit - steht dort wieder der alte Wert, ist der Verdacht belegt.
    Nach dauer_s Sekunden wird alles auf die gemerkten Werte zurueckgesetzt.
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] zeitlupe: kein Spieler-Pawn")
        return
    mitte = pawn.Location
    n = 0
    for g in _gegner_lebend():
        try:
            if _abstand_uu(g.Location, mitte) > radius_m * UU_JE_METER_A:
                continue
            pfad = g._path_name()
            eintrag = _verlangsamt.get(pfad) or [WeakPointer(g), 0.0, float(g.CustomTimeDilation),
                                                 float(g.GroundSpeed), float(g.AirSpeed)]
            eintrag[1] = dauer_s
            if art in (1, 3):
                g.CustomTimeDilation = faktor
            if art in (2, 3, 4):
                g.GroundSpeed = eintrag[3] * faktor
                g.AirSpeed = eintrag[4] * faktor
            if art == 4:
                _erzwungen[pfad] = faktor  # _paket_b_tick schreibt es jeden Frame nach
            if art != 0:
                _verlangsamt[pfad] = eintrag
            _flug_merken(g, f"Zeitlupe Art {art}", ZEITLUPE_MESSUNG_S)
            n += 1
            logging.info(f"[ZB] zeitlupe: {g.Name} CustomTimeDilation {g.CustomTimeDilation}, "
                         f"GroundSpeed {g.GroundSpeed:.0f}, AirSpeed {g.AirSpeed:.0f}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] zeitlupe: {ex}")
    logging.info(f"[ZB] zeitlupe: Art {art}, Faktor {faktor}, {n} Gegner - Strecken kommen in {ZEITLUPE_MESSUNG_S:.0f} s")


def mechanik_paket_b_gelegt() -> None:
    """Beim Legen: Raenge einmal lesen, Buch und Markierungen leeren."""
    global _rang_para, _rang_vorb, _rang_zeitspur, _vorbelastung_bis
    _rang_para = skill_rang("Paradoxon")
    _rang_vorb = skill_rang("Vorbelastung")
    _rang_zeitspur = skill_rang("Zeitspur")
    _buch.clear()
    _markiert.clear()
    _nachschlag.clear()
    _vorbelastung_bis = 0.0
    if _rang_para or _rang_vorb or _rang_zeitspur:
        logging.info(f"[ZB] Paket B: Paradoxon R{_rang_para}, Vorbelastung R{_rang_vorb}, Zeitspur R{_rang_zeitspur}")


def mechanik_paradoxon() -> bool:
    """Paradoxon: jeder Gegner, dem du mit liegender Bombe Schaden gemacht hast, bekommt beim
    Zuenden die Haelfte davon noch einmal.

    Keine Kappe je Ziel, anders als im Entwurf angedacht: 50 % des Schadens, den man selbst schon
    angerichtet hat, sind nie mehr als das, was man ohnehin konnte - auch gegen Bosse nicht. Wer das
    anders will, setzt hier eine.
    """
    if _rang_para <= 0:
        _buch.clear()
        return False
    pc = local_pc()
    if not _buch or pc is None:
        logging.info("[ZB] Paradoxon: nichts im Buch (niemand mit liegender Bombe getroffen)")
        return False
    ziele = {}
    for g in _gegner_lebend():
        try:
            ziele[g._path_name()] = g
        except Exception:  # noqa: BLE001
            continue
    global _eigen
    n, summe = 0, 0.0
    for pfad, gebucht in _buch.items():
        ziel = ziele.get(pfad)
        if ziel is None:
            continue  # tot oder weg - der Schaden verfaellt
        _eigen = True
        try:
            wert = gebucht * PARADOXON_ANTEIL
            logging.info(f"[ZB] Paradoxon: {ziel.Name} gebucht {gebucht:.0f} -> {_treffer(ziel, pc, wert, 0.0, ziel.Location, False)}")
            n += 1
            summe += wert
        finally:
            _eigen = False
    logging.info(f"[ZB] Paradoxon: {len(_buch)} Ziele im Buch, {n} noch am Leben, {summe:.0f} Schaden nachgereicht")
    _buch.clear()
    return True


def mechanik_vorbelastung_gezuendet(pc: UObject) -> None:
    """Das 8-s-Fenster oeffnen. Erst NACH den Umkreis-Skills des Zuendens, damit deren Treffer
    nicht selbst schon nachgeschlagen werden."""
    global _vorbelastung_bis
    if _rang_vorb <= 0 or not _markiert:
        _markiert.clear()
        return
    _vorbelastung_bis = _game_time(pc) + VORBELASTUNG_DAUER_S
    logging.info(f"[ZB] Vorbelastung: {len(_markiert)} Ziel(e) markiert, +{VORBELASTUNG_JE_RANG * _rang_vorb * 100:.0f} % "
                 f"fuer {VORBELASTUNG_DAUER_S:.0f} s")


def mechanik_paket_b_verpufft() -> None:
    """Verpufft die Bombe, verfaellt das Buch, und markiert ist auch niemand mehr."""
    global _vorbelastung_bis
    if _buch or _markiert:
        logging.info(f"[ZB] Paket B: verpufft - {len(_buch)} Buchungen und {len(_markiert)} Markierungen verfallen")
    _buch.clear()
    _markiert.clear()
    _vorbelastung_bis = 0.0


def _paket_b_tick(pc: UObject, dt: float) -> None:
    """Laeuft in jedem PlayerTick, unabhaengig vom Zustand: Nachschlag austeilen, Fenster schliessen,
    Verlangsamung auslaufen lassen."""
    global _eigen, _vorbelastung_bis
    if _nachschlag:
        auftrag = dict(_nachschlag)
        _nachschlag.clear()
        for pfad, (zeiger, wert) in auftrag.items():
            ziel = zeiger()
            if ziel is None or wert <= 0 or not _ist_welt_actor(ziel):
                continue
            _eigen = True
            try:
                logging.info(f"[ZB] Vorbelastung: {ziel.Name} -> {_treffer(ziel, pc, wert, 0.0, ziel.Location, False)}")
            finally:
                _eigen = False
    if _vorbelastung_bis > 0.0 and _game_time(pc) >= _vorbelastung_bis:
        logging.info("[ZB] Vorbelastung: Fenster zu")
        _vorbelastung_bis = 0.0
        _markiert.clear()
    for pfad in list(_verlangsamt):
        eintrag = _verlangsamt[pfad]
        eintrag[1] -= dt
        if eintrag[1] > 0:
            if pfad in _erzwungen:  # Art 4: jeden Frame nachschreiben, falls das Spiel zurueckgesetzt hat
                ziel = eintrag[0]()
                if ziel is not None and _ist_welt_actor(ziel):
                    try:
                        ziel.GroundSpeed = eintrag[3] * _erzwungen[pfad]
                        ziel.AirSpeed = eintrag[4] * _erzwungen[pfad]
                    except Exception:  # noqa: BLE001
                        pass
            continue
        del _verlangsamt[pfad]
        _erzwungen.pop(pfad, None)
        ziel = eintrag[0]()
        if ziel is not None and _ist_welt_actor(ziel):
            try:
                _verlangsamung_zuruck(ziel, eintrag)
                logging.info(f"[ZB] Zeitspur: {ziel.Name} wieder normal (CustomTimeDilation {ziel.CustomTimeDilation},"
                             f" GroundSpeed {ziel.GroundSpeed:.0f})")
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] Zeitspur zuruecksetzen: {ex}")


ZEITWIRBEL_TAKT_S = 2
ZEITWIRBEL_FAKTOR = 1.0          # x Granatenschaden je Impuls
ZEITWIRBEL_EXPLOSION = "GD_Explosions.shock.Explosion_ShockMaster_MaliwanNova"
_zeitwirbel_sekunden = 0


def zeitspur_sekunde() -> None:
    """Zeitspur, seit v1.05 der ZEITWIRBEL (Nutzerentscheidung 2026-09-26): solange die Bombe
    liegt und Gegner naeher als 8 m am Anker sind, entlaedt sich dort alle 2 s ein Schock-Impuls
    mit echtem Schaden (1 x Granatenschaden). Aus dem Ticker, einmal je Sekunde.

    Bis v0.88 sollte Zeitspur verlangsamen - an Bodengegnern unmoeglich (Spike A, docs/spikes.md).
    Die Explosion geht vom Spieler aus und wird per LocationOffset an den Anker gesetzt (v1.03);
    ob der SCHADEN mit dem Versatz mitwandert, zeigt die Nachmessung am Anker (mitte=).
    """
    global _zeitwirbel_sekunden
    if _rang_zeitspur <= 0 or _anchor is None:
        return
    _zeitwirbel_sekunden += 1
    if _zeitwirbel_sekunden % ZEITWIRBEL_TAKT_S:
        return
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        return
    anker = _vec(_anchor.x, _anchor.y, _anchor.z)
    radius = ZEITSPUR_RADIUS_M * UU_JE_METER_A
    nah = 0
    for g in _gegner_lebend():
        try:
            if _abstand_uu(g.Location, anker) <= radius:
                nah += 1
        except Exception:  # noqa: BLE001
            continue
    if nah == 0:
        # v1.08: ohne Gegner ein kleiner, rein optischer Puls - markiert den Anker und macht den
        # Ort auch auf Entfernung pruefbar (v1.07: Gegner liefen dem Spieler nach, Test ohne Aussage)
        effekt("Zeitwirbel-Puls", ZEITWIRBEL_EXPLOSION, anker, 300.0)
        return
    basis, quelle = _granaten_schaden(pawn, _granate(pawn))
    proj = _projektil_traeger(anker)   # v1.11: Projektil am Anker statt Versatz
    if proj is None:
        return
    explodieren(proj, "Zeitwirbel", ZEITWIRBEL_EXPLOSION, basis * ZEITWIRBEL_FAKTOR, radius,
                f"{nah} Gegner am Anker, {ZEITWIRBEL_FAKTOR:.0f} x {basis:.0f} ({quelle}), ueber Projektil",
                traeger=proj, mitte=anker)


def zeitspur_alle_zuruecksetzen() -> None:
    """Beim Deaktivieren des Moduls - sonst bleibt ein Gegner fuer immer in Zeitlupe."""
    for eintrag in _verlangsamt.values():
        ziel = eintrag[0]()
        if ziel is not None and _ist_welt_actor(ziel):
            try:
                _verlangsamung_zuruck(ziel, eintrag)
            except Exception:  # noqa: BLE001
                pass
    _verlangsamt.clear()


def _verlangsamung_zuruck(ziel: UObject, eintrag: list) -> None:
    """Die gemerkten Originalwerte zurueckschreiben - nie pauschal 1.0/440, ein Gegner kann von
    Haus aus anders laufen."""
    ziel.CustomTimeDilation = eintrag[2]
    ziel.GroundSpeed = eintrag[3]
    ziel.AirSpeed = eintrag[4]


# =================================================================================================
# Handgriff 4, Paket C (v0.89): Es war nie passiert - und die Diagnose fuer Kurs halten
#
# "Faellst du in Fight for your Life, waehrend eine Bombe liegt, zuendet sie von selbst."
#
# Die Namen stehen im 'zb namen'-Lauf (v0.71): hinein GoFromHealthToInjuredClient,
# SetupPlayerInjuredState, SetInjuredState(EInjuredStage), PlayInjured(...) am WillowPlayerPawn,
# SetupInjuredState am Controller; heraus GoFromInjuredToHealthy, RejuvenateFromInjured. WELCHER
# davon beim Umfallen feuert, ist offen - NotifyKilled (v0.65) hat gezeigt, dass ein vorhandener
# Name noch lange kein feuernder Hook ist. Darum zaehlen alle mit (zb ffyl), und JEDER Kandidat
# fuer "hinein" darf ausloesen - der erste gewinnt, der Merker verhindert Doppelausloesung.
#
# Nicht im Hook selbst zuenden: mitten im Umfallen Zustand und Position umzuschreiben waere
# Reentrancy ins Ungewisse. Der Hook setzt nur einen Merker, der naechste PlayerTick handelt
# (dasselbe Muster wie der Vorbelastungs-Nachschlag).
#
# Aufstehen: GoFromInjuredToHealthy() - GEWAEHLT nach dem Namen, nicht belegt, dass es den Spieler
# wirklich aufrichtet. Die Injured-Eigenschaften des Pawns werden davor und danach geloggt.

FFYL_HINEIN = (
    "WillowGame.WillowPlayerPawn:GoFromHealthToInjuredClient",
    "WillowGame.WillowPlayerPawn:SetupPlayerInjuredState",
    "WillowGame.WillowPlayerPawn:SetInjuredState",
    "WillowGame.WillowPlayerPawn:PlayInjured",
    "WillowGame.WillowPlayerController:SetupInjuredState",
)
FFYL_HERAUS = (
    "WillowGame.WillowPlayerPawn:GoFromInjuredToHealthy",
    "WillowGame.WillowPlayerPawn:RejuvenateFromInjured",
)
_ffyl_zaehler: dict[str, int] = {}
_ffyl_merker = ""  # Name des Kandidaten, der ausgeloest hat - leer = nichts zu tun


def _make_ffyl_hook(fname: str, hinein: bool):
    def hook(obj: UObject, args: Any, ret: Any, func: Any) -> None:
        global _ffyl_merker
        _ffyl_zaehler[fname] = _ffyl_zaehler.get(fname, 0) + 1
        if _trace:
            logging.info(f"[ZB] SPUR FFYL {fname.split(':')[-1]} an {obj.Name}")
        if not hinein or _state != ZUSTAND_GELEGT or _ffyl_merker:
            return
        pc = local_pc()
        if pc is None or not ist_chronomaster(pc):
            return
        try:
            eigen = obj._path_name() in (pc._path_name(), pc.Pawn._path_name() if pc.Pawn else "")
        except Exception:  # noqa: BLE001
            eigen = False
        if eigen:
            _ffyl_merker = fname
    return hook


def _injured_eigenschaften(pawn: UObject) -> str:
    """Die Injured-Felder des Pawns in einer Zeile - die Messgroesse fuers Aufstehen."""
    teile = []
    for name in dir(pawn):
        if "injured" not in name.lower():
            continue
        try:
            wert = getattr(pawn, name)
        except Exception:  # noqa: BLE001
            continue
        if callable(wert):
            continue
        teile.append(f"{name}={str(wert)[:40]}")
    return ", ".join(teile[:12]) or "keine Felder"


def _ffyl_tick(pc: UObject) -> None:
    """Laeuft im PlayerTick: hat ein FFYL-Hook ausgeloest, jetzt aufstehen und zuenden."""
    global _ffyl_merker
    if not _ffyl_merker:
        return
    ausloeser, _ffyl_merker = _ffyl_merker, ""
    if _state != ZUSTAND_GELEGT:
        return
    rang = skill_rang("EsWarNiePassiert")
    if rang <= 0:
        logging.info(f"[ZB] Es war nie passiert: FFYL erkannt ({ausloeser.split(':')[-1]}), aber keine Punkte")
        return
    pawn = pc.Pawn
    if pawn is None:
        return
    logging.info(f"[ZB] Es war nie passiert: FFYL erkannt ueber {ausloeser.split(':')[-1]} - Bombe zuendet von selbst")
    logging.info(f"[ZB]   vor dem Aufstehen: {_injured_eigenschaften(pawn)}")
    try_call("GoFromInjuredToHealthy", pawn.GoFromInjuredToHealthy)
    logging.info(f"[ZB]   nach dem Aufstehen: {_injured_eigenschaften(pawn)}")
    zuenden_komplett(pc)


def ffyl_zeigen() -> None:
    """zb ffyl - welcher FFYL-Kandidat wie oft gefeuert hat."""
    for fname in FFYL_HINEIN + FFYL_HERAUS:
        richtung = "hinein" if fname in FFYL_HINEIN else "heraus"
        logging.info(f"[ZB] ffyl: {_ffyl_zaehler.get(fname, 0):4d}x  {richtung:6s}  {fname}")


def fast_tot() -> None:
    """zb fasttot - TESTHILFE, nur am Chronomaster: Schild 0, Leben 1.

    Der Stufe-80-Testcharakter faellt sonst nie um. Ein Kratzer eines Gegners genuegt danach fuer
    Fight for your Life. SetHealth ist seit Spike B nur "plausibel" - der Log sagt, ob es griff.
    """
    pc = local_pc()
    if not testchar_only(pc) or pc.Pawn is None:
        return
    pawn = pc.Pawn
    try_call("SetShieldStrength(0)", lambda: pawn.SetShieldStrength(0.0))
    try_call("SetHealth(1)", lambda: pawn.SetHealth(1.0))
    logging.info(f"[ZB] TESTHILFE fasttot: Leben jetzt {try_call('GetHealth', pawn.GetHealth)}, "
                 f"Schild {try_call('GetShieldStrength', pawn.GetShieldStrength)}")


def fenster_zeigen() -> None:
    """zb fenster - wo die Restzeit des laufenden Fensters steht (Diagnose fuer Kurs halten, v0.89).

    Kurs halten soll das Fenster je Kill verlaengern. Das Fenster ist InitialDuration an unserer
    Skill_Zeitbombe (DURATION_Timed) - also laeuft irgendwo eine Skill-INSTANZ mit einer Restzeit.
    SkillEffectManager.GetActiveSkillForInstigatorByDefinition liefert sie (Name aus 'zb namen').
    Alle ihre Felder ins Log, dazu die Zeit-Felder der ExecuteActionSkill-Instanz. Nur lesen.
    """
    pc, sm = local_pc(), skill_manager()
    d = _find("SkillDefinition", f"{ACTION_OUTER}.Skill_{SKILL_OBJ}")
    if pc is None or sm is None or d is None:
        logging.error(f"[ZB] fenster: pc={pc} sm={sm} def={d}")
        return
    logging.info(f"[ZB] fenster: Zustand {_state}, InitialDuration {d.InitialDuration}, "
                 f"seit dem Legen {_game_time(pc) - _legen_time:.1f} s")
    try:
        inst = sm.GetActiveSkillForInstigatorByDefinition(pc, d)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] fenster: GetActiveSkillForInstigatorByDefinition: {ex}")
        inst = None
    logging.info(f"[ZB] fenster: laufende Skill-Instanz = {inst._path_name() if inst is not None else None}")
    if inst is not None:
        dump_props(inst, "")
    if _skill is not None:
        for flt in ("time", "dur"):
            dump_props(_skill, flt)


# --- Kurs halten (Baum 3, Tier 4, Rang 5) - v0.90 -----------------------------------------------
#
# "Jeder Kill mit liegender Bombe verlaengert das Fenster um 1 Sekunde je Rang."
#
# 'zb fenster' (v0.89) hat gezeigt, wo das Fenster lebt: an der Skill-INSTANZ, die
# SkillEffectManager.GetActiveSkillForInstigatorByDefinition(pc, Skill_Zeitbombe) liefert -
# Felder StartTime (Spielzeit beim Legen), Duration und DurationBaseValue (beide 20.0) samt einem
# leeren DurationModifierStack. Ein eigenes Restzeit-Feld gibt es nicht, die ExecuteActionSkill-
# Timer sind leer. Das Ende ist also StartTime + Duration.
#
# Geschrieben werden Duration UND DurationBaseValue: Duration ist das Ergebnis aus Basis und
# Modifikatoren und koennte bei der naechsten Neuberechnung aus der Basis ueberschrieben werden.
# OFFEN und nur im Spiel zu klaeren: ob der Manager das Ende laufend aus Duration rechnet oder es
# beim Start einmal festgelegt hat. Messgroesse: der Zeitpunkt des Verpuffens.

KURS_JE_RANG_S = 1.0


def mechanik_kurs_halten() -> None:
    """Aus dem Kill-Zaehler: das laufende Fenster um Rang x 1 s verlaengern."""
    rang = skill_rang("KursHalten")
    if rang <= 0:
        return
    pc, sm = local_pc(), skill_manager()
    d = _find("SkillDefinition", f"{ACTION_OUTER}.Skill_{SKILL_OBJ}")
    if pc is None or sm is None or d is None:
        return
    try:
        inst = sm.GetActiveSkillForInstigatorByDefinition(pc, d)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Kurs halten: laufende Instanz: {ex}")
        return
    if inst is None:
        logging.info("[ZB] Kurs halten: keine laufende Skill-Instanz")
        return
    plus = KURS_JE_RANG_S * rang
    try:
        vorher = float(inst.Duration)
        inst.DurationBaseValue = float(inst.DurationBaseValue) + plus
        inst.Duration = vorher + plus
        ende = float(inst.StartTime) + float(inst.Duration)
        logging.info(f"[ZB] Kurs halten: Rang {rang}, Fenster {vorher:.1f} -> {float(inst.Duration):.1f} s "
                     f"(Basis {float(inst.DurationBaseValue):.1f}), Ende bei Spielzeit {ende:.1f} "
                     f"= noch {ende - _game_time(pc):.1f} s")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Kurs halten: {ex}")


# =================================================================================================
# Handgriff 4, Paket D (v0.92): Hologramme - Zeitkapsel, Nachbild, Sprengsatz
#
# Zer0s Hologramm kommt aus der Spawn-Factory in seinem Stealth-BPD (dieselbe, die 'zb ziel'
# benutzt). Ihre Balance ist laut Dump GD_Assassin_Hologram.Character.BD_Assassin_Hologram - also
# koennen wir das Hologramm SELBST spawnen, ohne den Skill_Stealth-Block aufzuheben (der traegt
# auch die Unsichtbarkeit, v0.43/v0.44). Spawn-Aufruf und Budget-Umgehung wie bei 'zb ziel'.
#
# Entfernen ueber Pawn.Died(Killer=None, DamageType=DmgType_Suicided, HitLocation=...) - der Weg,
# mit dem das FL4K-Projekt seine Pets seit Wochen sicher entfernt. DestroyPopulationActor hat dort
# das Spiel abgeschossen, Actor.Destroy() greift nicht.
#
# OFFEN, nur im Spiel zu klaeren: ob das selbst gespawnte Hologramm Feuer auf sich zieht wie Zer0s
# (Fraktion und Zielbarkeit kommen aus der Balance, das spricht dafuer), und ob es eine eigene
# Lebensdauer hat, die unserer zuvorkommt.

HOLO_BALANCE = "GD_Assassin_Hologram.Character.BD_Assassin_Hologram"
NACHBILD_BASIS_S = 2.0
NACHBILD_JE_RANG_S = 1.0
HOLO_OHNE_ENDE = 1.0e9          # Zeitkapsel: bis zum Zuenden/Verpuffen, nicht nach Uhr

_hologramme: list[list] = []    # [WeakPointer, Restzeit, Zweck, Pfad]


def _holo_pfade() -> set[str]:
    return {h[3] for h in _hologramme}


def holo_spawnen(ort: Any, zweck: str, dauer: float) -> UObject | None:
    """Ein Hologramm von Zer0s Art an `ort`, fuer `dauer` Sekunden (oder bis holo_entfernen)."""
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    factory = _find("PopulationFactoryBalancedAIPawn", SPAWN_FACTORY)
    balance = _find("AIPawnBalanceDefinition", HOLO_BALANCE)
    if pawn is None or factory is None or balance is None:
        logging.error(f"[ZB] Hologramm ({zweck}): pawn={pawn is not None} factory={factory is not None} balance={balance is not None}")
        return None
    master = None
    for m in unrealsdk.find_all("WillowPopulationMaster"):
        if "Default__" not in m._path_name():
            master = m
    if master is None:
        logging.error(f"[ZB] Hologramm ({zweck}): kein WillowPopulationMaster")
        return None
    # Zer0s Factory nur fuer diesen Aufruf anfassen und sofort zuruecksetzen (D6, vgl. v0.91).
    alt = (factory.PawnBalanceDefinition, factory.UseCostOverride, factory.SpawnCostOverride)
    factory.PawnBalanceDefinition = balance
    factory.UseCostOverride = True
    factory.SpawnCostOverride = 0
    try:
        neu = factory.SpawnAIPawn(
            Master=master, SpawnLocationContextObject=pawn, SpawnLocation=ort,
            SpawnRotation=pawn.Rotation, GameStage=pc.PlayerReplicationInfo.ExpLevel,
            AwesomeLevel=0, bUseMemento=False,
        )
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Hologramm ({zweck}): SpawnAIPawn: {ex}")
        neu = None
    finally:
        factory.PawnBalanceDefinition, factory.UseCostOverride, factory.SpawnCostOverride = alt
    if neu is None:
        logging.error(f"[ZB] Hologramm ({zweck}): SpawnAIPawn lieferte nichts")
        return None
    _hologramme.append([WeakPointer(neu), dauer, zweck, neu._path_name()])
    effekt(f"Hologramm {zweck} erscheint", FX_LEGEN, ort, 300.0, verzoegerung=0.2)   # Phase 8 (v1.04)
    dauertext = "bis zum Zuenden" if dauer >= HOLO_OHNE_ENDE else f"{dauer:.0f} s"
    logging.info(f"[ZB] Hologramm ({zweck}): {neu.Name} steht ({dauertext}), Leben {_leben(neu):.0f}")
    return neu


def _holo_weg(eintrag: list, grund: str) -> None:
    """Ein Hologramm entfernen - ueber Died(), den FL4K-belegten Weg."""
    holo = eintrag[0]()
    if holo is None or not _ist_welt_actor(holo):
        logging.info(f"[ZB] Hologramm ({eintrag[2]}): schon weg ({grund})")
        return
    try:
        dmg = unrealsdk.find_class("DmgType_Suicided")
    except Exception:  # noqa: BLE001
        dmg = unrealsdk.find_class("DamageType")
    if grund != "Modul deaktiviert":   # Phase 8 (v1.04): es zerfaellt violett
        o = holo.Location
        effekt(f"Hologramm {eintrag[2]} zerfaellt", FX_VERPUFFEN, _vec(o.X, o.Y, o.Z), 300.0)
    try:
        holo.Died(Killer=None, DamageType=dmg, HitLocation=holo.Location)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Hologramm ({eintrag[2]}): Died: {ex}")
    # v0.93: Died() allein laesst eine Leiche liegen - sichtbar, im Ragdoll, mit "[E] BENUTZEN"
    # (Nutzer-Screenshot 2026-09-26). Also danach verstecken und die Kollision abschalten, wie bei
    # der Bombe (v0.57/v0.58 gemessen). Nur an unserem eigenen, oben gepruften Welt-Actor.
    try_call(f"Hologramm {holo.Name} SetHidden", lambda: holo.SetHidden(True))
    try_call(f"Hologramm {holo.Name} SetCollisionType(NoCollision)", lambda: holo.SetCollisionType(COLLIDE_NO_COLLISION))
    try:
        logging.info(f"[ZB] Hologramm ({eintrag[2]}): {holo.Name} entfernt ({grund}) - bHidden={holo.bHidden}"
                     f" bCollideActors={holo.bCollideActors}")
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] Hologramm ({eintrag[2]}): {holo.Name} entfernt ({grund}), Nachlesen: {ex}")


def holo_entfernen(zweck: str, grund: str) -> None:
    """Alle Hologramme eines Zwecks entfernen (Zeitkapsel beim Zuenden/Verpuffen)."""
    global _hologramme
    bleiben = []
    for eintrag in _hologramme:
        if eintrag[2] == zweck:
            _holo_weg(eintrag, grund)
        else:
            bleiben.append(eintrag)
    _hologramme = bleiben


def _holo_tick(dt: float) -> None:
    """Laeuft im PlayerTick: Uhren der Hologramme, am Ende Sprengsatz und Entfernen."""
    global _hologramme
    if not _hologramme:
        return
    bleiben = []
    for eintrag in _hologramme:
        eintrag[1] -= dt
        if eintrag[1] > 0:
            bleiben.append(eintrag)
            continue
        _holo_weg(eintrag, "Zeit abgelaufen")
    _hologramme = bleiben


def mechanik_zeitkapsel_gelegt(o: Any) -> None:
    """Zeitkapsel: am Anker `o` (Vector) steht ein Hologramm, solange die Bombe liegt. Die Heilung fuer
    Verbuendete in 8 m fehlt noch (solo nicht pruefbar - kommt mit den Verbuendeten-Skills)."""
    global _zeitkapsel_ausstehend
    if skill_rang("Zeitkapsel") <= 0:
        return
    if _halten_seit >= 0:
        # v0.96: Schattenanker prueft gerade, ob die Taste gehalten wird. Wird sie, ist das keine
        # Bombe, sondern eine Schattenzuendung - dann soll kein Hologramm aufblitzen (Nutzer: nervig).
        _zeitkapsel_ausstehend = _vec(o.X, o.Y, o.Z)
        logging.info("[ZB] Zeitkapsel: wartet, bis klar ist, ob die Taste gehalten wird")
        return
    holo_spawnen(_vec(o.X, o.Y, o.Z), "Zeitkapsel", HOLO_OHNE_ENDE)


def mechanik_nachbild() -> None:
    """Nachbild: beim Zuenden bleibt am Absprungpunkt ein Hologramm, 2 s + 1 s je Rang."""
    rang = skill_rang("Nachbild")
    if rang <= 0 or _absprung is None:
        return
    if _schatten_laeuft:
        logging.info("[ZB] Nachbild: Schattenzuendung - kein Hologramm")
        return
    holo_spawnen(_absprung, "Nachbild", NACHBILD_BASIS_S + NACHBILD_JE_RANG_S * rang)


# =================================================================================================
# Handgriff 4, Paket E (v0.95): Verbuendete - Zweite Meinung, Gemeinsame Rueckkehr, Zeitkapsel-Heilung
#
# Verbuendete = die anderen WillowPlayerPawns der Karte (Welt-Actors, Pfad geprueft). Pools setzen
# wie beim Zuenden und bei Auffrischung (SetHealth/SetShieldStrength, Get*/GetMax* - alle am eigenen
# Pawn belegt, Spike B / v0.55). VERMUTUNG: im Koop wirkt das nur beim Gastgeber; ein Client setzt
# die Pools eines Mitspielers nur lokal, der Server ueberschreibt sie.
#
# Solo nicht pruefbar - darum 'zb koop selbst': der eigene Pawn zaehlt dann als Verbuendeter. Mit
# 'zb fasttot' VOR dem Legen (Anker speichert Schild 0 / Leben 1) sieht man die Aufschlaege im Log.

VERBUENDETE_RADIUS_M = 10.0          # Zweite Meinung (um den Anker), Gemeinsame Rueckkehr (Ankunftsort)
ZWEITE_MEINUNG_JE_RANG = 0.06        # Schild, Anteil am Maximum
GEMEINSAM_JE_RANG = 0.05             # Leben, Anteil am Maximum
ZEITKAPSEL_RADIUS_M = 8.0
ZEITKAPSEL_JE_RANG_S = 0.008         # Leben je Sekunde, Anteil am Maximum

_koop_selbst = False                 # Testschalter: eigener Pawn zaehlt als Verbuendeter


def _verbuendete(mitte: Any, radius_m: float) -> tuple[list[UObject], int]:
    """Andere Spieler-Pawns im Umkreis (mit 'zb koop selbst' auch der eigene). Nur Eigenschaften."""
    pc = local_pc()
    eigen = pc.Pawn._path_name() if pc is not None and pc.Pawn is not None else ""
    raus, gesamt = [], 0
    for p in unrealsdk.find_all("WillowPlayerPawn", exact=False):
        if not _ist_welt_actor(p):
            continue
        try:
            if bool(p.bDeleteMe):
                continue
            pfad = p._path_name()
        except Exception:  # noqa: BLE001
            continue
        gesamt += 1
        if pfad == eigen and not _koop_selbst:
            continue
        try:
            if _abstand_uu(p.Location, mitte) <= radius_m * UU_JE_METER_A:
                raus.append(p)
        except Exception:  # noqa: BLE001
            continue
    return raus, gesamt


def _pool_auffuellen(p: UObject, label: str, anteil: float, schild: bool) -> str:
    """Leben oder Schild von p um `anteil` des Maximums anheben (hoechstens aufs Maximum)."""
    try:
        if schild:
            maxi, alt = float(p.GetMaxShieldStrength()), float(p.GetShieldStrength())
            p.SetShieldStrength(min(maxi, alt + anteil * maxi))
            neu = float(p.GetShieldStrength())
        else:
            maxi, alt = float(p.GetMaxHealth()), float(p.GetHealth())
            p.SetHealth(min(maxi, alt + anteil * maxi))
            neu = float(p.GetHealth())
    except Exception as ex:  # noqa: BLE001
        return f"{p.Name}: FEHLER {ex}"
    return f"{p.Name} {'Schild' if schild else 'Leben'} {alt:.0f} -> {neu:.0f} (Max {maxi:.0f}, +{anteil * 100:.1f} %)"


def mechanik_verbuendete_gezuendet(pawn: UObject) -> None:
    """Nach dem Teleport: Zweite Meinung (Schild) und Gemeinsame Rueckkehr (Leben) fuer Verbuendete
    um den Anker = Ankunftsort. Beide drehen sich um denselben Ort, weil der Spieler dort landet."""
    for skill, label, je_rang, schild in (("ZweiteMeinung", "Zweite Meinung", ZWEITE_MEINUNG_JE_RANG, True),
                                          ("GemeinsameRueckkehr", "Gemeinsame Rueckkehr", GEMEINSAM_JE_RANG, False)):
        rang = skill_rang(skill)
        if rang <= 0:
            continue
        ziele, gesamt = _verbuendete(pawn.Location, VERBUENDETE_RADIUS_M)
        for p in ziele:
            logging.info(f"[ZB] {label}: {_pool_auffuellen(p, label, je_rang * rang, schild)}")
        logging.info(f"[ZB] {label}: Rang {rang}, {len(ziele)} Verbuendete in {VERBUENDETE_RADIUS_M:.0f} m"
                     f" ({gesamt} Spieler-Pawns auf der Karte{', eigener zaehlt mit' if _koop_selbst else ''})")


def mechanik_zeitkapsel_sekunde() -> None:
    """Jede Sekunde im Zustand 'gelegt': Verbuendete in 8 m ums Zeitkapsel-Hologramm regenerieren."""
    rang = skill_rang("Zeitkapsel")
    if rang <= 0:
        return
    for eintrag in _hologramme:
        if eintrag[2] != "Zeitkapsel":
            continue
        holo = eintrag[0]()
        if holo is None or not _ist_welt_actor(holo):
            continue
        ziele, _ = _verbuendete(holo.Location, ZEITKAPSEL_RADIUS_M)
        for p in ziele:
            logging.info(f"[ZB] Zeitkapsel: {_pool_auffuellen(p, 'Zeitkapsel', ZEITKAPSEL_JE_RANG_S * rang, False)}")


def koop_schalter(wert: str) -> None:
    """zb koop selbst|aus - Testhilfe: eigener Pawn zaehlt als Verbuendeter (nur Chronomaster-Test)."""
    global _koop_selbst
    _koop_selbst = wert == "selbst"
    logging.info(f"[ZB] koop: eigener Pawn zaehlt {'als Verbuendeter (TESTHILFE)' if _koop_selbst else 'nicht mit'}")


# --- Sprengsatz, neu (v0.94, Nutzerwunsch 2026-09-26) ----------------------------------------------
#
# Bis v0.93 explodierte das Nachbild nach 7 s ueber _umkreis_treffen (TakeDamage + Stagger): im Test
# unsichtbar, und an den Testzielen (Spielerfraktion) kam kein Schaden an. Neues Design stattdessen:
# eine riesige Explosion, wo man zuendet, im Element der ausgeruesteten Granate, kein Stoss, kein
# Stagger, grosser Schaden.
#
# Weg: ein eigener Behavior_Explode - derselbe Baustein, mit dem Granaten explodieren (Dump:
# GD_GrenadeMods.Projectiles.*:BehaviorProviderDefinition_1.Behavior_Explode_*). Aufruf ueber
# ApplyBehaviorToContext mit leeren BehaviorKernelInfo/BehaviorParameters - so ruft das FL4K-Projekt
# seit v0.18 einen Baustein aus Python (sdk/fl4k_pet, dort: "spawnt"). Er explodiert am SelfObject;
# darum laeuft er in zuenden() VOR dem Teleport, mit dem Spieler als SelfObject.
#
# Aussehen, Klang und Element kommen aus der ExplosionDefinition (Partikel je Radius-Stufe bis 1024,
# DamageTypeDef = Element). Die Wahl haengt am Zubehoerteil (Delta) der ausgeruesteten Granate:
# GD_GrenadeMods.Accessory.Accessory_<Element>[_GradeN].

SPRENGSATZ_RADIUS_UU = 1000.0    # 10 m - die groesste Stufe der ExplosionDefinitions reicht bis 1024
SPRENGSATZ_FAKTOR = 5.0          # x Granatenschaden
SPRENGSATZ_EXPLOSION = {         # Element (aus dem Teilnamen) -> ExplosionDefinition
    "Incendiary": "GD_Explosions.Incendiary.Explosion_IncendiaryMaster",
    "Corrosive": "GD_Explosions.corrosive.Explosion_CorrosiveMaster",
    "Shock": "GD_Explosions.shock.Explosion_ShockMaster",
    "Slag": "GD_Explosions.Slag.Explosion_SlagMaster",
    "Explosive": "GD_Explosions.explosive.Explosion_Nukem",   # Nukem-Pilz, Nutzerwunsch
}
SPRENGSATZ_ERSATZ = "GD_Explosions.explosive.Explosion_ExplosiveMaster"
SPRENGSATZ_BEHAVIOR = "ZB_Sprengsatz_Explode"


def _granate(pawn: UObject) -> UObject | None:
    """Die ausgeruestete Granate: die Kette InvManager.ItemChain -> .Inventory, nur Eigenschaften."""
    try:
        item = pawn.InvManager.ItemChain
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] Sprengsatz: InvManager.ItemChain nicht lesbar ({ex})")
        return None
    n = 0
    while item is not None and n < 32:
        if item.Class.Name == "WillowGrenadeMod":
            return item
        item = item.Inventory
        n += 1
    return None


def _granaten_element(granate: UObject | None) -> str:
    if granate is None:
        return "Explosive"
    try:
        teil = granate.DefinitionData.DeltaItemPartDefinition
        name = str(teil.Name) if teil is not None else ""
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] Sprengsatz: Zubehoerteil nicht lesbar ({ex})")
        return "Explosive"
    for element in SPRENGSATZ_EXPLOSION:
        if element in name:
            return element
    logging.info(f"[ZB] Sprengsatz: Zubehoerteil '{name}' ohne bekanntes Element - explosiv")
    return "Explosive"


def _sprengsatz_behavior() -> UObject | None:
    """Unser Behavior_Explode, einmal gebaut und gerootet (im Transient-Paket, ueberlebt Kartenwechsel)."""
    b = _find("Behavior_Explode", f"Transient.{SPRENGSATZ_BEHAVIOR}")
    if b is not None:
        return b
    try:
        paket = unrealsdk.find_object("Package", "Transient")
        b = unrealsdk.construct_object("Behavior_Explode", paket, SPRENGSATZ_BEHAVIOR)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Sprengsatz: Behavior_Explode nicht gebaut: {ex}")
        return None
    _root(b)
    logging.info(f"[ZB] erzeugt Behavior_Explode {b._path_name()}")
    return b


def mechanik_sprengsatz(pawn: UObject) -> None:
    """Sprengsatz: beim Zuenden eine grosse Explosion am Absprungpunkt, im Element der ausgeruesteten
    Granate, SPRENGSATZ_FAKTOR x Granatenschaden. Muss VOR dem Teleport laufen (explodiert am Spieler)."""
    if skill_rang("Sprengsatz") <= 0:
        return
    granate = _granate(pawn)
    element = _granaten_element(granate)
    basis, quelle = _granaten_schaden(pawn, granate)
    explodieren(pawn, "Sprengsatz", SPRENGSATZ_EXPLOSION[element], basis * SPRENGSATZ_FAKTOR, SPRENGSATZ_RADIUS_UU,
                f"{element}, {SPRENGSATZ_FAKTOR:.0f} x {basis:.0f} ({quelle})")


def _granaten_schaden(pawn: UObject, granate: UObject | None) -> tuple[float, str]:
    """GrenadeDamage der ausgeruesteten Granate; ohne Granate der Waffenschaden."""
    if granate is not None:
        try:
            wert = float(granate.GrenadeDamage)
            if wert > 0:
                return wert, "Granate"
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] GrenadeDamage nicht lesbar ({ex})")
    return _schaden_basis(pawn), "Waffe (keine Granate)"


EXPLOSION_NACHMESSEN_S = 1.0   # im selben Frame kommt der Schaden noch nicht an (v0.94: 0 von 11)
_explosions_proben: list[list] = []   # [Label, Restzeit, {Pfad: Leben vorher}]


def explodieren(pawn: UObject, label: str, pfad: str, schaden: float, radius_uu: float, herkunft: str = "",
                traeger: UObject | None = None, visuell: bool = False, versatz: Any = None,
                mitte: Any = None) -> bool:
    """Eine echte Spiel-Explosion am Spieler (docs/spikes.md, "Explosionen aus Python"). Laeuft sie
    beim Zuenden, muss sie VOR dem Teleport kommen. Kein Stoss, kein Eigenschaden.

    v1.00: `traeger` - ein anderer Actor als Explosionsort (SelfObject/ContextObject), der Spieler
    bleibt Verursacher. `visuell` - nur Aussehen und Klang: Schaden 0, keine Statuseffekte, eine
    kurze Logzeile, keine Nachmessung (Ketten wuerden sonst das Log fluten)."""
    ort_actor = traeger if traeger is not None else pawn
    definition = _find("ExplosionDefinition", pfad) or _find("ExplosionDefinition", SPRENGSATZ_ERSATZ)
    if definition is None:
        logging.error(f"[ZB] {label}: weder {pfad} noch {SPRENGSATZ_ERSATZ} geladen")
        return False
    b = _sprengsatz_behavior()
    if b is None:
        return False
    try:
        b.Definition = definition
        b.DamageSource = unrealsdk.find_class("WillowDmgSource_Grenade")
        b.DamageFormula.BaseValueConstant = schaden
        b.DamageFormula.BaseValueAttribute = None
        b.DamageRadiusFormula.BaseValueConstant = radius_uu
        b.DamageRadiusFormula.BaseValueAttribute = None
        b.MomentumFormula.BaseValueConstant = 0.0     # kein Rueckstoss (Nutzerwunsch)
        b.StatusEffectChance.BaseValueConstant = 0.0 if visuell else 1.0
        b.StatusEffectDamage.BaseValueConstant = 0.0 if visuell else 1.0
        b.bCanDamageFriendlies = False
        b.InstigatorSelfDamageScale = 0.0             # der Spieler steht mitten drin
        b.bNoSound = False
        # v1.02: Explosionen an anderen Orten ueber LocationOffset (der Traeger zeigte nichts, v1.01)
        b.LocationOffset = versatz if versatz is not None else _vec(0.0, 0.0, 0.0)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] {label}: Felder setzen: {ex}")
        return False
    o = ort_actor.Location
    if visuell:
        try:
            b.ApplyBehaviorToContext(
                ContextObject=ort_actor, KernelInfo=unrealsdk.make_struct("BehaviorKernelInfo"),
                SelfObject=ort_actor, MyInstigatorObject=pawn, OtherEventParticipantObject=None,
                EventData=unrealsdk.make_struct("BehaviorParameters"),
            )
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Effekt {label}: {ex}")
            return False
        if _effekte_log:
            v = f", Versatz ({versatz.X:.0f},{versatz.Y:.0f},{versatz.Z:.0f})" if versatz is not None else ""
            logging.info(f"[ZB] Effekt {label}: {definition.Name}, Radius {radius_uu:.0f} bei ({o.X:.0f},{o.Y:.0f},{o.Z:.0f}){v}")
        return True
    if mitte is not None:   # v1.05: mit Versatz liegt die Explosion nicht am Spieler - dort messen
        o = mitte
    logging.info(f"[ZB] {label}: Explosion {definition.Name}, Schaden {schaden:.0f} ({herkunft}), Radius"
                 f" {radius_uu / UU_JE_METER_A:.0f} m, bei ({o.X:.0f},{o.Y:.0f},{o.Z:.0f})"
                 f" - gesetzt: Schaden {b.DamageFormula.BaseValueConstant:.0f}, Radius {b.DamageRadiusFormula.BaseValueConstant:.0f}")
    # v0.96: nur Gegner im Radius beobachten - "0 von 9 verletzt" trennte sonst nicht zwischen
    # "keiner in Reichweite" und "Schaden kommt nicht an" (Falle 2).
    vorher = {}
    for p in _gegner_lebend():
        try:
            if _abstand_uu(p.Location, o) <= radius_uu:
                vorher[p._path_name()] = _leben(p)
        except Exception:  # noqa: BLE001
            continue
    logging.info(f"[ZB] {label}: {len(vorher)} lebende Gegner im Radius")
    try:
        b.ApplyBehaviorToContext(
            ContextObject=ort_actor,
            KernelInfo=unrealsdk.make_struct("BehaviorKernelInfo"),
            SelfObject=ort_actor,
            MyInstigatorObject=pawn,
            OtherEventParticipantObject=None,
            EventData=unrealsdk.make_struct("BehaviorParameters"),
        )
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] {label}: ApplyBehaviorToContext: {ex}")
        return False
    _explosions_proben.append([label, EXPLOSION_NACHMESSEN_S, vorher])
    return True


def _explosion_tick(dt: float) -> None:
    """Nachmessung eine Sekunde nach der Explosion: wer hat Leben verloren (oder ist tot)?"""
    global _explosions_proben
    if not _explosions_proben:
        return
    offen = []
    for probe in _explosions_proben:
        probe[1] -= dt
        if probe[1] > 0:
            offen.append(probe)
            continue
        label, _, vorher = probe
        jetzt = {p._path_name(): (p, _leben(p)) for p in _gegner_lebend()}
        getroffen = tot = 0
        for pfad, alt in vorher.items():
            if pfad not in jetzt:
                tot += 1   # nicht mehr unter den Lebenden
                continue
            p, neu = jetzt[pfad]
            if neu < alt:
                getroffen += 1
                logging.info(f"[ZB] {label} nachgemessen: {p.Name} Leben {alt:.0f} -> {neu:.0f} (-{alt - neu:.0f})")
        logging.info(f"[ZB] {label} nachgemessen nach {EXPLOSION_NACHMESSEN_S:.0f} s: {getroffen} verletzt,"
                     f" {tot} nicht mehr am Leben, von {len(vorher)} Gegnern im Radius")
    _explosions_proben = offen


# =================================================================================================
# Phase 8, Teil 1 (v1.00): SICHTBARE EFFEKTE - "ziemlich over the top" (Nutzerwunsch 2026-09-26)
#
# Alles ueber explodieren(..., visuell=True): echte Spiel-Explosionen mit Schaden 0, ohne
# Statuseffekte - Partikel, Klang und Kamerawackeln kommen aus der ExplosionDefinition. Groesse
# ueber den Radius (ExplosionScale-Stufen 0-192 / 193-384 / 385-1024 uu).
#
# Explosionen an einem anderen Ort als dem Spieler brauchen einen Traeger: ein unsichtbarer
# DynamicSMActor_Spawnable (wie die Bombe, ohne Mesh, ohne Kollision), der vor jeder Explosion an
# den Ort geschoben wird. OFFEN, nur im Spiel zu klaeren: ob die Partikel am Traeger HAENGEN
# (dann liefe die Blitzspur mit ihm mit) - dann braucht es einen Traeger je Explosion.
#
# Ketten (Blitzspur) laufen ueber eine Warteschlange im PlayerTick.

FX_LEGEN = "GD_Explosions.Special.Explosion_SingularityImplosion"
FX_ABSPRUNG = "GD_Explosions.shock.Explosion_ShockMaster_ShieldNova"
FX_SCHATTEN = "GD_Explosions.Slag.Explosion_SlagMaster_MaliwanNova"
FX_ANKUNFT = "GD_Explosions.shock.Explosion_ShockMaster"
FX_BEBEN = "GD_Explosions.Special.Explosion_WarriorEarthquake"
FX_NACHHALL = "GD_Explosions.shock.Explosion_ShockMaster_MaliwanNova"
FX_SPUR = "GD_Explosions.shock.Explosion_ShockMaster"
FX_VERPUFFEN = "GD_Explosions.Slag.Explosion_SlagMaster"
FX_SPUR_SCHRITT_UU = 250.0
FX_SPUR_TAKT_S = 0.03
FX_SPUR_MAX = 60

_effekte_an = True
_effekte_log = False                     # zb effekte log: jede Effekt-Explosion loggen
_effekt_traeger_ptr: WeakPointer = WeakPointer()
_effekt_queue: list[list] = []           # [Restzeit, Label, Pfad, Ort, Radius]
_fx_fehlt: set[str] = set()


def _effekt_traeger(ort: Any) -> UObject | None:
    t = _effekt_traeger_ptr()
    try:
        if t is not None and _ist_welt_actor(t) and not bool(t.bDeleteMe):
            t.Location = ort
            return t
    except Exception:  # noqa: BLE001
        pass
    pc = local_pc()
    if pc is None:
        return None
    try:
        t = pc.Spawn(SpawnClass=unrealsdk.find_class(BOMB_ACTOR_CLASS), SpawnLocation=ort,
                     SpawnRotation=unrealsdk.make_struct("Rotator", Pitch=0, Yaw=0, Roll=0), bNoCollisionFail=True)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Effekt-Traeger: Spawn: {ex}")
        return None
    if t is None:
        return None
    try:
        t.SetCollisionType(COLLIDE_NO_COLLISION)
    except Exception:  # noqa: BLE001
        pass
    _effekt_traeger_ptr.replace(t)
    logging.info(f"[ZB] Effekt-Traeger gespawnt: {t._path_name()}")
    return t


def effekt(label: str, pfad: str, ort: Any, radius_uu: float, verzoegerung: float = 0.0) -> None:
    """Eine rein optische Explosion an `ort` (Vector), sofort oder nach `verzoegerung` Sekunden.
    `ort=None` heisst: am Spieler, wo er beim Ausloesen steht (v1.04, fuer Effekte nach dem Teleport)."""
    if not _effekte_an:
        return
    if verzoegerung > 0:
        _effekt_queue.append([verzoegerung, label, pfad, _vec(ort.X, ort.Y, ort.Z) if ort is not None else None, radius_uu])
        return
    if _find("ExplosionDefinition", pfad) is None:
        if pfad not in _fx_fehlt:
            _fx_fehlt.add(pfad)
            logging.info(f"[ZB] Effekt {label}: {pfad} nicht geladen - Ersatz {SPRENGSATZ_ERSATZ}")
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        return
    if ort is None:
        explodieren(pawn, label, pfad, 0.0, radius_uu, visuell=True)
        return
    # v1.11: ueber ein ruhendes Projektil (Probe 4 im Spiel bestaetigt) statt LocationOffset
    proj = _projektil_traeger(ort)
    if proj is not None:
        explodieren(proj, label, pfad, 0.0, radius_uu, traeger=proj, visuell=True)


# v1.11: DER Weg fuer Explosionen an fremden Orten (Probe 4, Nutzer 2026-09-26: "genau vor mir").
# Ein ruhendes WillowProjectile ist SelfObject, ContextObject UND MyInstigatorObject - so laufen auch
# Granaten-Explosionen. proj.Instigator = Spieler, damit Schaden (und hoffentlich Kills) ihm zufallen.
# Der Versatz-Weg (LocationOffset) wirkt zwar (10 m hoch: bestaetigt), die seitliche Drehung war aber
# nie sicher zu treffen (v1.02-v1.08).
_projektil_ptr: WeakPointer = WeakPointer()


def _projektil_traeger(ort: Any) -> UObject | None:
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        return None
    proj = _projektil_ptr()
    try:
        if proj is not None and _ist_welt_actor(proj) and not bool(proj.bDeleteMe):
            proj.Location = _vec(ort.X, ort.Y, ort.Z)
            proj.Velocity = _vec(0.0, 0.0, 0.0)
            proj.Instigator = pawn
            return proj
    except Exception:  # noqa: BLE001
        pass
    try:
        proj = pc.Spawn(SpawnClass=unrealsdk.find_class("WillowProjectile"), SpawnLocation=_vec(ort.X, ort.Y, ort.Z),
                        SpawnRotation=unrealsdk.make_struct("Rotator", Pitch=0, Yaw=0, Roll=0), bNoCollisionFail=True)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Projektil-Traeger: Spawn: {ex}")
        return None
    if proj is None:
        logging.error("[ZB] Projektil-Traeger: Spawn lieferte nichts")
        return None
    try:
        proj.Velocity = _vec(0.0, 0.0, 0.0)
        proj.SetCollisionType(COLLIDE_NO_COLLISION)
        proj.Instigator = pawn
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] Projektil-Traeger ruhigstellen: {ex}")
    _projektil_ptr.replace(proj)
    logging.info(f"[ZB] Projektil-Traeger gespawnt: {proj.Name}")
    return proj


# v1.02: Der Traeger (DynamicSMActor) zeigte nichts, der Spieler als Ort schon (Probe v1.01: nur
# die Varianten "am Spieler" sichtbar, Schaden 0 oder 1 egal). Also bleibt der Spieler Ursprung und
# die Explosion wird per LocationOffset verschoben. Ob der Versatz in Welt- oder Spielerkoordinaten
# gilt, klaerte 'zb effekte probe' (v1.02, Yaw 6336 = 35 Grad): die Variante "relativ zur
# Blickrichtung" landete vor dem Spieler, die Weltvariante 35 Grad daneben. Also Spielerkoordinaten.
FX_VERSATZ_LOKAL = True


def _versatz(pawn: UObject, ort: Any, lokal: bool) -> Any:
    """Weltversatz Spieler -> ort, bei `lokal` in die Achsen des Spielers umgerechnet.

    v1.06: die VOLLE Drehung (Pitch, Yaw, Roll), nicht nur Yaw. Der Zeitwirbel (v1.05) zeigte nichts
    und traf nichts, waehrend 'zb effekte test' (Blick geradeaus) sichtbar war - Vermutung: das
    Spiel dreht den Versatz auch um die Neigung, und wer nach unten schaut, schickt ihn in den Boden.
    Mit Pitch 0 ist das Ergebnis dasselbe wie vorher. Achsen wie FRotationMatrix (UE3)."""
    o = pawn.Location
    dx, dy, dz = ort.X - o.X, ort.Y - o.Y, ort.Z - o.Z
    if not lokal:
        return _vec(dx, dy, dz)
    # v1.07: die KAMERA (Controller) statt des Koerpers. Zeitwirbel v1.06: Pawn-Pitch immer 0, Controller
    # 11 Grad nach unten; der erste Impuls (Anker nah) traf, danach wanderte er mit wachsender Entfernung
    # weg und verschwand (31 m x sin 11 Grad = 6 m in den Boden).
    pc = local_pc()
    r = pc.Rotation if pc is not None else pawn.Rotation
    k = 2.0 * math.pi / 65536.0
    p, y, w = float(r.Pitch) * k, float(r.Yaw) * k, float(r.Roll) * k
    sp, cp, sy, cy, sr, cr = math.sin(p), math.cos(p), math.sin(y), math.cos(y), math.sin(w), math.cos(w)
    ax = (cp * cy, cp * sy, sp)
    ay = (sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, -sr * cp)
    az = (-(cr * sp * cy + sr * sy), cy * sr - cr * sp * sy, cr * cp)
    punkt = lambda a: dx * a[0] + dy * a[1] + dz * a[2]  # noqa: E731
    return _vec(punkt(ax), punkt(ay), punkt(az))


_effekt_rufe: list[list] = []   # [Restzeit, Funktion] - verzoegerte Aufrufe (zb effekte probe)


def _effekt_tick(dt: float) -> None:
    global _effekt_queue, _effekt_rufe
    if _effekt_rufe:
        faellig = [r for r in _effekt_rufe if r[0] - dt <= 0]
        _effekt_rufe = [[r[0] - dt, r[1]] for r in _effekt_rufe if r[0] - dt > 0]
        for _, fn in faellig:
            fn()
    if not _effekt_queue:
        return
    faellig, offen = [], []
    for e in _effekt_queue:
        e[0] -= dt
        (faellig if e[0] <= 0 else offen).append(e)
    _effekt_queue = offen
    for _, label, pfad, ort, radius in faellig:
        effekt(label, pfad, ort, radius)


def effekt_spur(label: str, von: Any, bis: Any, pfad: str = FX_SPUR, radius_uu: float = 300.0,
                start: float = 0.0) -> None:
    """Eine Kette kleiner Explosionen von `von` nach `bis` - die Blitzspur."""
    if not _effekte_an:
        return
    laenge = _abstand_uu(von, bis)
    n = max(2, min(FX_SPUR_MAX, int(laenge / FX_SPUR_SCHRITT_UU) + 1))
    for i in range(n):
        f = i / (n - 1)
        ort = _vec(von.X + (bis.X - von.X) * f, von.Y + (bis.Y - von.Y) * f, von.Z + (bis.Z - von.Z) * f)
        effekt(f"{label} {i + 1}/{n}", pfad, ort, radius_uu, verzoegerung=start + 0.001 + i * FX_SPUR_TAKT_S)
    logging.info(f"[ZB] Effekt {label}: {n} Explosionen ueber {laenge / UU_JE_METER_A:.1f} m")


def effekte_schalter(wert: str) -> None:
    """zb effekte an|aus|log|test - Effekte schalten; 'test' zeigt alle einmal vor dir."""
    global _effekte_an, _effekte_log
    if wert in ("an", "aus"):
        _effekte_an = wert == "an"
    elif wert == "log":
        _effekte_log = not _effekte_log
    elif wert.startswith("probe"):
        # v1.01: 'zb effekte test' lief fehlerfrei und zeigte NICHTS. Zwei Verdaechtige: Schaden 0
        # (Behavior_Explode ueberspringt vielleicht alles) oder der Traeger (nacktes Mesh-Objekt statt
        # Pawn). Vier Varianten, alle 3 s nacheinander, trennen beides. Nutzer sagt, welche er sah.
        pc = local_pc()
        if pc is None or pc.Pawn is None:
            return
        pawn = pc.Pawn
        vor = _vor_spieler(pawn, 600.0)
        _effekte_log = True
        # v1.09: Probe 3 - der Versatz wandert auf Entfernung weg (v1.06-v1.08). Zwei Auswege, beide
        # mit Ziel 15 m vor dem Spieler, festgelegt beim Befehl (danach darf er sich umsehen):
        #   1 = ein ruhendes WillowProjectile als Ursprung - so explodieren Granaten (Nutzeridee)
        #   2 = Versatz wie bisher, aber bSkipTraceTest=True (falls eine Sichtlinienpruefung ihn kappt)
        ziel = _vor_spieler(pawn, 1500.0)
        ziel = _vec(ziel.X, ziel.Y, ziel.Z)

        def probe_projektil() -> None:
            p = local_pc().Pawn
            try:
                proj = local_pc().Spawn(SpawnClass=unrealsdk.find_class("WillowProjectile"), SpawnLocation=ziel,
                                        SpawnRotation=unrealsdk.make_struct("Rotator", Pitch=0, Yaw=0, Roll=0),
                                        bNoCollisionFail=True)
            except Exception as ex:  # noqa: BLE001
                logging.error(f"[ZB] effekte probe 1: Spawn WillowProjectile: {ex}")
                return
            if proj is None:
                logging.error("[ZB] effekte probe 1: Spawn WillowProjectile lieferte nichts")
                return
            try:
                proj.Velocity = _vec(0.0, 0.0, 0.0)
                proj.SetCollisionType(COLLIDE_NO_COLLISION)
            except Exception as ex:  # noqa: BLE001
                logging.info(f"[ZB] effekte probe 1: Projektil ruhigstellen: {ex}")
            try:
                proj.Instigator = p   # Schaden wuerde so dem Spieler zugerechnet
            except Exception as ex:  # noqa: BLE001
                logging.info(f"[ZB] effekte probe 1: Instigator setzen: {ex}")
            l = proj.Location
            logging.info(f"[ZB] effekte probe 1: Projektil {proj.Name} bei ({l.X:.0f},{l.Y:.0f},{l.Z:.0f}) ist Self, Context UND Verursacher")
            # v1.10: das Projektil auch als MyInstigatorObject (bisher immer der Spieler)
            explodieren(proj, "Probe 1", FX_ABSPRUNG, 0.0, 600.0, traeger=proj, visuell=True)

        def probe_hoch() -> None:
            p = local_pc().Pawn
            logging.info("[ZB] effekte probe 2: Versatz 10 m senkrecht nach oben")
            explodieren(p, "Probe 2", FX_ABSPRUNG, 0.0, 600.0, visuell=True, versatz=_vec(0.0, 0.0, 1000.0))

        _effekt_rufe.append([0.001, probe_projektil])
        _effekt_rufe.append([5.0, probe_hoch])
        logging.info("[ZB] effekte probe: 1 Projektil (auch Verursacher) 15 m voraus sofort, 2 Versatz 10 m hoch in 5 s")
    elif wert == "test":
        pc = local_pc()
        if pc is None or pc.Pawn is None:
            return
        vor = _vor_spieler(pc.Pawn, 800.0)
        for i, (name, pfad, r) in enumerate((("Legen", FX_LEGEN, 400.0), ("Absprung", FX_ABSPRUNG, 1000.0),
                                             ("Schatten", FX_SCHATTEN, 1000.0), ("Ankunft", FX_ANKUNFT, 1000.0),
                                             ("Nachhall", FX_NACHHALL, 600.0),
                                             ("Verpuffen", FX_VERPUFFEN, 500.0))):
            effekt(f"Test {name}", pfad, vor, r, verzoegerung=0.001 + 2.0 * i)
            logging.info(f"[ZB] effekte test: {name} in {2 * i} s ({pfad})")
        effekt_spur("Test Spur", _vec(pc.Pawn.Location.X, pc.Pawn.Location.Y, pc.Pawn.Location.Z), vor, start=12.0)
        logging.info("[ZB] effekte test: Spur in 12 s")
    logging.info(f"[ZB] effekte: {'an' if _effekte_an else 'aus'}, Log {'an' if _effekte_log else 'aus'}")


def holo_test(sekunden: float = 10.0) -> None:
    """zb holo [SEKUNDEN] - ein Hologramm 3 m vor dir, zum Anschauen (v0.92)."""
    pc = local_pc()
    if pc is None or pc.Pawn is None:
        logging.error("[ZB] holo: kein Spieler-Pawn")
        return
    holo_spawnen(_vor_spieler(pc.Pawn, 300.0), "Test", sekunden)


def mechanik_dejavu(grund: str = "gezuendet") -> bool:
    """Deja-vu: beim Zuenden alle Kill Skills anwerfen, als haette man gerade getoetet.

    Haengt am Rang von Deja-vu selbst (der Skill verspricht es auf seiner Karte), nicht am Kill-
    Zaehler: auch ohne einen einzigen Kill im Fenster soll das Zuenden auffrischen.

    Gemessen wird ueber IsSkillActive vor und nach dem Aufruf (Spike E). "aus -> an" ist der Beleg;
    steht schon vorher alles auf "an", sagt der Vergleich nichts ueber das Auffrischen der Dauer -
    dann zaehlt nur das HUD. Darum im Test mit kalten Kill-Skills anfangen.
    """
    # v1.13: die Kill Skills sind jetzt Stack-Skills des Moduls - UpdateKillSkills (v0.70) schaltete
    # die harten Kill Skills des Spiels und hat hier nichts mehr zu tun. Deja-vu haelt die Stacks fest.
    if skill_rang("DejaVu") <= 0:
        return False
    kill_stacks_festhalten(f"Deja-vu, {grund}")
    return True


def _on_player_tick(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST auf WillowPlayerController:PlayerTick - jeden Frame. Nur im Zustand 'gelegt' und nur
    fuer den eigenen Controller wird gerechnet."""
    global _tick_akku, _wurf
    pc = local_pc()
    if pc is None or obj._path_name() != pc._path_name():
        return
    try:
        dt = float(args.DeltaTime)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Ticker: DeltaTime: {ex}")
        return
    if _icons_offen:
        try:
            _icons_tick(pc, dt)  # v1.39: DLC-Icons im laufenden Spiel nachholen
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Icons nachholen: {ex}")
    # Die Rueckstoss-Nachmessung laeuft AUSSERHALB des Zustands: gestossen wird beim Zuenden, und
    # danach ist der Zustand schon wieder "bereit" (v0.78).
    try:
        _flug_nachmessen(dt)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Rueckstoss-Nachmessung: {ex}")
    try:
        _wurf_tick(pc, dt)  # die geworfene Bombe fliegt (v1.19)
    except Exception as ex:  # noqa: BLE001
        _wurf = None
        logging.error(f"[ZB] Wurf: {ex} - Flug abgebrochen, Anker bleibt am Wurfpunkt")
        _wurf_notlandung(pc)
    try:
        _wurf_rest_tick(dt)  # explodiert das ruhende Projektil? (v1.31)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Wurf-Rest: {ex}")
    try:
        _spaeher_tick(dt)  # zb granate (v1.29)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Granaten-Spaeher: {ex}")
    try:
        _paket_b_tick(pc, dt)  # Vorbelastung austeilen, Zeitspur auslaufen lassen (v0.84)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Paket-B-Tick: {ex}")
    try:
        _ffyl_tick(pc)  # Es war nie passiert (v0.89)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] FFYL-Tick: {ex}")
    try:
        _verpuffen_tick(dt)  # aufgeschobenes Verpuffen (v0.90) - NACH dem FFYL-Tick, der Vorrang hat
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Verpuffen-Tick: {ex}")
    try:
        _holo_tick(dt)  # Hologramme: Uhren und Entfernen (v0.92)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Hologramm-Tick: {ex}")
    try:
        _explosion_tick(dt)  # Nachmessung der Explosionen, 1 s danach (v0.95)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Explosions-Nachmessung: {ex}")
    try:
        _schatten_tick(pc, dt)  # Schattenanker: Ringpuffer und Haltepruefung (v0.95)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Schattenanker-Tick: {ex}")
    try:
        _wirkung_uhren_tick(dt)  # Rueckenwind nach 10 s abschalten (v0.97)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Wirkungs-Uhren: {ex}")
    try:
        _effekt_tick(dt)  # verzoegerte Effekte und Blitzspur (v1.00)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Effekt-Tick: {ex}")
    try:
        _immunitaet_tick(dt)  # Reinigung/Zeitsprung-Immunitaet abschalten (v1.12)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Immunitaet-Tick: {ex}")
    try:
        _kill_stack_tick(dt)  # Kill-Stacks verfallen lassen (v1.13)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Kill-Stack-Tick: {ex}")
    if _state != ZUSTAND_GELEGT:
        return
    _tick_akku += dt
    if _tick_akku < TICK_SEKUNDEN:
        return
    _tick_akku -= TICK_SEKUNDEN
    try:
        ticker_sekunde(pc)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Ticker: {ex}")
    try:
        mechanik_zeitkapsel_sekunde()  # Paket E (v0.95): Heilung ums Hologramm
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Zeitkapsel-Heilung: {ex}")


def ensure_skilltree(class_def: UObject) -> bool:
    """Baumkette anlegen und die Chronomaster-Klasse darauf zeigen lassen. Idempotent.

    Laeuft beim Modulstart durch (im Spiel bestaetigt 2026-09-20: drei eigene Aeste im Skillmenue,
    Zer0 unveraendert). Scheitert sie doch einmal, bleibt SkillTreePath auf Zer0s Baum - der
    Charakter ist dann spielbar, nur eben mit Zer0s Aesten - und die Menue-Hooks holen sie nach,
    bevor ein Spielstand laedt.
    """
    global _skilltree_ready
    if not _load_tree_packages():
        logging.info(f"[ZB] Baumkette: {ROOT_BRANCH_TEMPLATE} noch nicht ladbar - spaeter erneut")
        _skilltree_ready = False
        return False
    try:
        # 1. Wurzelobjekt OHNE Vorlage. GD_Assassin_Streaming.SkillTree.SkillTree_Assassin ist nie
        #    im Speicher (Spike D Runde 3), load_package holt es auch nicht - das Spiel loest den
        #    Pfad offenbar nur beim Laden des Charakters auf. Das Objekt traegt ohnehin nur "Root".
        wurzel = _neu("SkillTreeDefinition", TREE_OUTER, f"SkillTree_{CHARACTER_NAME}")

        # 2. Wurzelast als Kopie von Zer0s Deception-Ast. Sein Tiers(0) haelt den Action Skill;
        #    Phase 3 haengt dort die Zeitbombe ein, bis dahin steht Decepti0n darin.
        wurzelast = _copy("SkillTreeBranchDefinition", ROOT_BRANCH_TEMPLATE, TREE_OUTER,
                          f"Branch_{CHARACTER_NAME}")

        # 2b. Unsere Zeitbombe in Tiers(0) haengen, an die Stelle von Zer0s Skill_Deception
        #     (belegt durch 'zb askill': dort steht genau ein Eintrag, eine SkillDefinition).
        eigener_skill = ensure_action_skill()
        if eigener_skill is not None:
            tier = wurzelast.Tiers[0]
            skills = list(tier.Skills)
            if skills and skills[0] is not eigener_skill:
                skills[0] = eigener_skill
                tier.Skills = skills
            logging.info(f"[ZB] Wurzelast Tiers(0): {[s._path_name() for s in wurzelast.Tiers[0].Skills]}")

        # 3. Die drei Aeste. BranchName ist das einzige, was hier schon uns gehoert.
        aeste = []
        for name, vorlage, titel in BRANCHES:
            ast = _copy("SkillTreeBranchDefinition", f"{TREE_OUTER}.{vorlage}", TREE_OUTER,
                        f"Branch_{CHARACTER_NAME}_{name}")
            ast.BranchName = titel
            aeste.append(ast)

        # 3b. Die 36 Skills hinein (Phase 4-6, v0.52). Scheitert ein Skill, bleibt sein Platz leer -
        #     das Log nennt ihn; die Kette steht trotzdem.
        _baeume_fuellen(aeste)

        # 4. Verknuepfen. Children ist ein Objekt-Array und per SDK ganz setzbar (Spike D Runde 3).
        wurzel.Root = wurzelast
        wurzelast.Children = aeste

        # 5. Die Klasse auf den eigenen Baum zeigen lassen. Das trifft nur unsere Kopie der Klasse -
        #    Zer0s CharClass_Assassin bleibt unberuehrt (D6).
        pfad = wurzel._path_name()
        if str(class_def.SkillTreePath) != pfad:
            class_def.SkillTreePath = pfad

        logging.info(
            f"[ZB] Baumkette steht: {pfad} -> {wurzelast._path_name()}"
            f" -> {[str(a.BranchName) for a in wurzelast.Children]}"
        )
        _skilltree_ready = True
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] Baumkette noch nicht moeglich ({ex}) - wird im Menue nachgeholt")
        _skilltree_ready = False
    return _skilltree_ready


# Diagnose, die v0.28 rettete (2026-09-20): Die Baumkette fiel mit "Outer-Paket fehlt:
# GD_Assassin_Skills.SkillTree" durch, obwohl load_package("GD_Assassin_Skills") ohne Fehler lief.
# Dieser Befehl zeigte, dass das Paket zwar existiert, die Gruppe .SkillTree darin aber nicht - und
# dass erst GD_Assassin_Streaming_SF die Vorlagen bringt. Nuetzlich bleibt er fuer jeden weiteren
# Kammerjaeger: dessen Paketnamen kennt man vorher auch nicht.
# Reine Lesediagnose plus load_package - es wird nichts geschrieben und nichts verknuepft.
PROBE_PACKAGES = [
    "GD_Assassin_Skills",      # der Name aus den Objektpfaden - bringt die Objekte NICHT
    "GD_Assassin_Streaming",   # das Streaming-Paket, Vorbild aus dem FL4K-Projekt
    "GD_Assassin_Streaming_SF",  # die SeekFree-Variante - DAS ist es (Nisha: GD_Nisha_Streaming_SF.upk)
    "GD_Assassin",             # das Basispaket, in dem unsere Klasse schon lebt
]
PROBE_OBJECTS = [
    ("Package", "GD_Assassin_Skills"),
    ("Package", "GD_Assassin_Skills.SkillTree"),
    ("Package", "GD_Assassin.Character"),
    ("SkillTreeBranchDefinition", "GD_Assassin_Skills.SkillTree.Branch_ActionSkill_Deception"),
    ("SkillTreeBranchDefinition", "GD_Assassin_Skills.SkillTree.Branch_Sniping"),
    ("SkillTreeBranchDefinition", "GD_Assassin_Skills.SkillTree.Branch_Cunning"),
    ("SkillTreeBranchDefinition", "GD_Assassin_Skills.SkillTree.Branch_Bloodshed"),
    ("SkillDefinition", "GD_Assassin_Skills.Cunning.Innervate"),
]


def pakete() -> None:
    """'zb pakete': Bestandsaufnahme, welche Skill-/Baumobjekte erreichbar sind - vor und nach
    load_package. Im Hauptmenue auszufuehren, dort entscheidet sich die Frage."""

    def bericht(label: str) -> None:
        for cls, path in PROBE_OBJECTS:
            logging.info(f"[ZB] pakete {label:8s}: {'DA    ' if _find(cls, path) else 'fehlt '} {cls} {path}")
        try:
            aeste = [o._path_name() for o in unrealsdk.find_all("SkillTreeBranchDefinition", exact=False)]
        except Exception as ex:  # noqa: BLE001
            aeste = [f"<Fehler {ex}>"]
        logging.info(f"[ZB] pakete {label:8s}: geladene SkillTreeBranchDefinition = {aeste}")

    logging.info("[ZB] === pakete: welcher Paketname bringt Zer0s Skillobjekte? ===")
    bericht("vorher")
    for pkg in PROBE_PACKAGES:
        try:
            unrealsdk.load_package(pkg)
            logging.info(f"[ZB] pakete: load_package({pkg}) -> ohne Fehler")
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] pakete: load_package({pkg}) -> {ex}")
    bericht("nachher")
    logging.info("[ZB] === pakete Ende ===")


def skilltree_status() -> None:
    """'zb baum': die Kette ins Log schreiben und, falls sie fehlt, einen Anlauf nachholen.
    Nur Diagnose - das Anlegen geschieht beim Modulstart (ensure_seventh_character)."""
    klasse = _find("PlayerClassDefinition", f"GD_Assassin.Character.CharClass_{CHARACTER_NAME}")
    if klasse is None:
        logging.error("[ZB] baum: Chronomaster-Klasse nicht geladen")
        return
    if not _skilltree_ready:
        logging.info("[ZB] baum: Kette fehlt noch, neuer Anlauf")
        ensure_skilltree(klasse)
    logging.info(f"[ZB] baum: SkillTreePath = {klasse.SkillTreePath}")
    wurzel = _find("SkillTreeDefinition", str(klasse.SkillTreePath))
    if wurzel is None:
        logging.error("[ZB] baum: Wurzelobjekt nicht im Speicher - die Kette ist unterbrochen")
        return
    ast = wurzel.Root
    logging.info(f"[ZB] baum: Root = {ast._path_name() if ast else 'FEHLT'}")
    if ast is None:
        return
    for kind in ast.Children:
        logging.info(f"[ZB] baum:   {kind.BranchName} ({kind._path_name().rsplit('.', 1)[-1]}), {len(kind.Tiers)} Tiers")
        for t, tier in enumerate(kind.Tiers):
            try:
                zeile = [f"{s.SkillName}[{skill_rang(s._path_name().rsplit('.', 1)[-1])}/{s.MaxGrade}]" for s in tier.Skills]
            except Exception as ex:  # noqa: BLE001
                zeile = [f"<Fehler {ex}>"]
            logging.info(f"[ZB] baum:     Tier {t + 1} (naechster ab {tier.PointsToUnlockNextTier}): {zeile}")


def ensure_name_id() -> UObject | None:
    try:
        obj = _copy("PlayerNameIdentifierDefinition", NAMEID_TEMPLATE, "GD_PlayerNameId", "Chronomaster")
        obj.CharacterName = CHARACTER_NAME
        obj.LocalizedCharacterName = CHARACTER_NAME
        obj.UISortOrder = 6
        return obj
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] SPIKE C: Namensobjekt konnte nicht erzeugt werden: {ex}")
        return None


def dlc_manager() -> UObject | None:
    for m in unrealsdk.find_all("WillowDownloadableContentManager", exact=True):
        if "Default__" not in m._path_name():
            return m
    return None


def ensure_seventh_character() -> None:
    """Objektkette bauen und registrieren. Idempotent: bei rlm werden vorhandene Objekte wiederverwendet.

    Phase 4-6 (v0.52): die drei Aeste werden in ensure_skilltree (Stufe 1b) mit den 36 Skills aus
    den Tabellen BAUM_* belegt - siehe Abschnitt "Phase 4-6" oben. Ein geaenderter Baum entwertet
    gesetzte Skillpunkte des Testcharakters - vor dem ersten Test 'zb respec'.
    """
    global _seventh_ready
    try:
        name_id = ensure_name_id()
        if name_id is None:
            return

        # Stufe 1 - nur Basisspiel-Objekte, laeuft beim Start immer durch. Muss VOR dem Laden eines
        # Spielstands fertig sein, sonst zeigt das Lade-Menue "Assassin" (Test 19:22: Kette brach vorher
        # an Tulip ab, Klasse hing noch an Zer0s ClassId).
        class_def = _copy(*SEVENTH["class_def"])
        class_id = _copy(*SEVENTH["class_id"])
        profile = _copy(*SEVENTH["profile"])
        class_def.CharacterNameId = name_id
        class_id.ClassName = CLASS_TITLE
        class_id.LocalizedClassName = CLASS_TITLE.upper()
        class_id.LocalizedClassNameNonCaps = CLASS_TITLE
        class_id.DlcCharacterDef = None
        profile.PlayerClassDefinition = class_def
        name_id.CharacterClassId = class_id
        name_id.DefaultSaveGame = profile

        # Stufe 1b - die eigene Baumkette. Laeuft hier durch (Test 2026-09-20, 09:03 UTC: "Baumkette
        # steht" noch vor dem Hauptmenue), weil _load_tree_packages das richtige Paket kennt. Sie
        # MUSS vor dem Laden eines Spielstands stehen - deshalb hier und nicht spaeter.
        ensure_skilltree(class_def)
        ensure_cooldown_pool(class_def)

        # Stufe 2 - DLC-Registrierung; braucht GD_TulipPackageDef, das beim Start noch fehlt. Wird im
        # Auswahlmenue nachgeholt (Commit-Hook), dort hat es 19:2x funktioniert: Figur Zer0, Klasse
        # CharClass_Chronomaster.
        package_def = _copy(*SEVENTH["package_def"])
        registration = _copy(*SEVENTH["registration"])
        registration.PackageDef = package_def
        registration.ContentDisplayName = CHARACTER_NAME
        package_def.PackageDisplayName = CHARACTER_NAME
        package_def.DLCName = "Zeitbombe"
        package_def.PackageId = PACKAGE_ID

        manager = dlc_manager()
        if manager is None:
            logging.error("[ZB] SPIKE C: kein DLC-Manager gefunden")
            return
        for arr_name, item in (("ContentPackages", package_def), ("AllContent", registration), ("Characters", registration)):
            arr = getattr(manager, arr_name)
            if item not in arr:
                arr.append(item)
        logging.info(
            f"[ZB] SPIKE C: registriert - Klasse {class_def._path_name()}, Profil {profile._path_name()}, "
            f"Manager: {len(manager.ContentPackages)} Pakete, {len(manager.AllContent)} Inhalte, {len(manager.Characters)} Charaktere"
        )
        _seventh_ready = True
    except Exception as ex:  # noqa: BLE001
        logging.info(f"[ZB] SPIKE C: Objektkette unvollstaendig ({ex}) - wird im Auswahlmenue nachgeholt")


def _on_commit_characters(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """PRE-Hook: obj ist das CharacterSelectionGFxObject (CharacterSelectClip), obj.Outer das Menue."""
    try:
        movie = obj.Outer
        chars = movie.SelectableCharacters
        names = [c._path_name() if c else None for c in chars]
        logging.info(f"[ZB] SPIKE C: CommitSelectableCharacters -> {len(names)} Eintraege: {names}")
        if not _seventh_ready:
            ensure_seventh_character()
        else:
            # Letzte Gelegenheit vor dem Anlegen eines Charakters, falls BuildCharacterList
            # sie nicht schon gebaut hat.
            _retry_skilltree("CommitSelectableCharacters")
        icons_nachholen("CommitSelectableCharacters")   # v1.38: DLC-Icons
        mine = ensure_name_id()
        if mine is None:
            return
        if any(n == NAMEID_NEW for n in names):
            logging.info("[ZB] SPIKE C: Chronomaster ist bereits in der Liste")
            return
        chars.append(mine)
        obj.AddSelectableCharacter(PORTRAIT_PATH)
        logging.info(f"[ZB] SPIKE C: Chronomaster angehaengt + Kachel ({PORTRAIT_PATH}) -> jetzt {len(movie.SelectableCharacters)} Eintraege")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] SPIKE C: {ex}")


# Aufgeraeumt am Ende von Spike C (v0.15): die Diagnosebefehle "zb kachel" / "zb bestaetigen" und die
# SAVE-Spur-Hooks auf das Auswahlmenue sind entfernt - ihr Ergebnis steht in docs/spikes.md. Der Klassen-
# Hook aus v0.10 (Schreiben in pc.GetCachedSaveGame()) war wirkungslos: die Funktion liefert eine Kopie.


# ---------------------------------------------------------------------------
# Phase 3, Schritt 4: Zer0s Unsichtbarkeit abhaengen
#
# Befund aus dem Datenpaket (2026-09-20): Skill_Stealth ist ein SKILL_TYPE_Passive mit
# DURATION_Infinite und genau zwei Effekten - Att_AssassinIsStealthed=1 (die Unsichtbarkeit) und
# EnableWeaponFireSkillEvent=1. Gestartet wird er von Behavior_ActivateSkill-Knoten in DREI BPDs:
#   ActionSkill_Deception:BehaviorProviderDefinition_0.Behavior_ActivateSkill_12 und _14
#   Skill_Deception:BehaviorProviderDefinition_0.Behavior_ActivateSkill_207
# Er selbst startet weiter Skill_Speed und Skill_ActionSkillCooldownReduction.
#
# WARUM NICHT DIE BPD AENDERN: Diese BPDs gehoeren Zer0. Unsere Kopien (Skill_Zeitbombe,
# ActionSkill_Zeitbombe) haben keine eigenen - construct_object kopiert den Verweis, nicht das
# Unterobjekt. Ein Eingriff dort traefe den echten Zer0 und verstiesse gegen D6.
#
# Stattdessen: den Aufruf blockieren, wenn WIR es sind. Dasselbe Muster, mit dem das FL4K-Projekt
# einen Spawn unterdrueckt (Block auf ApplyBehaviorToContext). Zer0 laeuft durch den Hook hindurch
# und behaelt seine Taeuschung.
#
# Mitgenommen wird dabei auch Skill_Speed und die Cooldown-Reduktion - beides Zer0-Design. Der
# Tempo-Schub kommt als eigener Skill zurueck (Ausbruch, Baum 3, docs/skills.md).
# ---------------------------------------------------------------------------

ACTIVATE_SKILL_FUNC = "WillowGame.Behavior_ActivateSkill:ApplyBehaviorToContext"
STEALTH_SKILL = "GD_Assassin_Skills.ActionSkill.Skill_Stealth"
# v0.63: Decepti0ns Schadens-Ramp. Das BPD von Skill_Deception (unsere Kopie zeigt auf DASSELBE
# Objekt) aktiviert in einer Delay-Schleife bis zu fuenfmal Skill_ActionSkillDamageBuffStack -
# DURATION_Infinite, +Att_Deception_GunDamagePerStack Waffenschaden je Instanz (gemessen v0.59-v0.62:
# +40 % der Basis je Sekunde, 5 s; die Stacks blieben ueber die Sitzung liegen, bis +505 %). Nur Zer0s
# Ende-Knoten (Behavior_DeactivateSkill) bauen sie ab, und die laufen bei uns nie. Also blocken.
DAMAGE_STACK_SKILL = "GD_Assassin_Skills.ActionSkill.Skill_ActionSkillDamageBuffStack"
BLOCKED_SKILLS = {STEALTH_SKILL: "Unsichtbarkeit unterdrueckt (Skill_Stealth blockiert)",
                  DAMAGE_STACK_SKILL: "Decepti0n-Schadensstack blockiert"}


def _on_activate_skill(obj: UObject, args: Any, ret: Any, func: Any) -> Any:
    """PRE auf Behavior_ActivateSkill:ApplyBehaviorToContext. Feuert im ganzen Spiel staendig -
    deshalb zuerst die billigste Pruefung (welcher Skill), erst danach die teure (welche Klasse)."""
    from unrealsdk.hooks import Block  # noqa: PLC0415
    try:
        ziel = obj.SkillToActivate
        meldung = BLOCKED_SKILLS.get(ziel._path_name()) if ziel is not None else None
        if meldung is None:
            if _trace and ziel is not None and ist_chronomaster(local_pc()):
                logging.info(f"[ZB] SPUR ActivateSkill {ziel._path_name()}")
            return None
    except Exception:  # noqa: BLE001
        return None
    if not ist_chronomaster(local_pc()):
        return None
    logging.info(f"[ZB] {meldung}")
    return Block


# ---------------------------------------------------------------------------
# Phase 3, Schritt 5b: Zer0s Ton-Daempfer und Klang abhaengen (v0.48-v0.50, im Spiel bestaetigt)
#
# Nutzer (2026-09-20): waehrend der Zeitbombe ist der Ton gedaempft wie bei Decepti0n. Befund aus
# dem Datenpaket: das BPD ActionSkill_Deception:BehaviorProviderDefinition_0 feuert beim Start
# drei Behavior_PostAkEvent-Knoten -
#   Ak_Play_FX_Assassin_ActionSkill_Start      (Aktivierungsklang, wiederholt sich ~40x im 100-ms-Takt)
#   Ak_Play_FX_Assassin_ActionSkill_Loop       (Dauerbrummen)
#   Ak_Set_State_FX_Assassin_ActionSkill_On    (Wwise-STATE - so werden Mischpult-Zustaende wie ein
#                                               Tiefpass geschaltet; BESTAETIGT: das ist der Daempfer)
# und beim Ende Ak_Play_FX_Assassin_ActionSkill_Stop / Deception_Ending. Am ExecuteActionSkill selbst
# haengt kein Audio, RTPC-Regler gibt es fuer Zer0 keine. Gleiches Muster wie beim Stealth-Block:
# das BPD gehoert Zer0, also den Aufruf blockieren, wenn WIR es sind. Ein Block auf "Start" nimmt
# Loop und State gleich mit - sie haengen im Graph dahinter (v0.50: nur eine Block-Zeile im Log).
#
# FALLE (v0.48, Test 15:02): Der Hook stand auf "WillowGame.Behavior_PostAkEvent:..." - die Klasse
# liegt aber in GearboxFramework (Dump: Class=Class'GearboxFramework.Behavior_PostAkEvent').
# add_hook prueft den Namen nicht: kein Fehler, keine Zeile, nichts. Vor jedem Hook die "Class="-Zeile
# im Dump lesen, das Paket NICHT von einer Nachbarklasse ableiten.
# ---------------------------------------------------------------------------

POST_AK_EVENT_FUNC = "GearboxFramework.Behavior_PostAkEvent:ApplyBehaviorToContext"
AK_ASSASSIN_PREFIX = "Ake_FX_Player_Assassin."
# v0.49 (Test 15:10): State geblockt -> Daempfer weg. Uebrig blieb Decepti0ns Ambiente: "Loop" feuert
# zweimal, "Start" rund 40-mal im 100-ms-Takt ueber vier Sekunden (das Pulsieren). Beides weg (v0.50).
# "Stop" und "Deception_Ending" bleiben durch - sie raeumen nur auf. Eigener Klang: Phase 8.
AK_BLOCKED = {
    "Ake_FX_Player_Assassin.Ak_Set_State_FX_Assassin_ActionSkill_On",
    "Ake_FX_Player_Assassin.Ak_Play_FX_Assassin_ActionSkill_Loop",
    "Ake_FX_Player_Assassin.Ak_Play_FX_Assassin_ActionSkill_Start",
}


def _on_post_ak_event(obj: UObject, args: Any, ret: Any, func: Any) -> Any:
    """PRE auf Behavior_PostAkEvent:ApplyBehaviorToContext. Feuert im ganzen Spiel staendig -
    zuerst die billige Pruefung (Assassin-Ereignis?), erst dann die teure (Chronomaster?)."""
    from unrealsdk.hooks import Block  # noqa: PLC0415
    try:
        ev = obj.Event
        if ev is None:
            return None
        name = ev._path_name()
        if not name.startswith(AK_ASSASSIN_PREFIX):
            return None
    except Exception as ex:  # noqa: BLE001
        # Nicht still schlucken (Falle 2, plan.md): sonst ist "Hook feuert nicht" von
        # "Hook feuert, Zugriff scheitert" nicht zu unterscheiden.
        logging.error(f"[ZB] Klang-Hook: {ex}")
        return None
    if not ist_chronomaster(local_pc()):
        return None
    if name in AK_BLOCKED:
        logging.info(f"[ZB] Klang blockiert: {name}")
        return Block
    if _trace:  # die durchgelassenen (Stop, Deception_Ending) nur mit 'zb spur'
        logging.info(f"[ZB] Klang: {name}")
    return None


# ---------------------------------------------------------------------------
# SACKGASSE, dokumentiert damit sie niemand erneut geht (2026-09-20, v0.37-v0.41)
#
# Frage: Waehrend des Action Skills liegt ein roter Rahmen am Bildschirmrand. Er soll weg oder
# umgefaerbt werden. Er gehoert zu Decepti0n und erscheint auch beim unveraenderten Zer0 - also
# nichts, was dieses Projekt verursacht haette.
#
# VIER Hypothesen, alle im Spiel widerlegt:
#   1. Skill.ScaleformFrameName (die fuenf HUD-Frames des Spiels)  -> umgestellt, Rahmen unveraendert
#   2. VisionMode-Felder am ExecuteActionSkill                      -> genullt, Rahmen blieb
#      (sie waren trotzdem richtig: sie haben die blaue Gegner-Markierung entfernt)
#   3. Skill_Stealth                                                -> geblockt, Rahmen blieb
#   4. Ein Screen Particle (Part_Assassin_Screen_Dash)              -> pc.ScreenParticleRecords ist
#      waehrend des Skills LEER. Es ist gar keines. Ebenso feuerten weder
#      WillowPlayerController:ShowScreenParticle noch
#      WillowGame.Behavior_ScreenParticle:ApplyBehaviorToContext je - beide Hooks waren registriert
#      (Klassenpfad zur Laufzeit ermittelt, nicht geraten).
#
# Offen geblieben: eine PostProcessChain an anderer Stelle, ein CoordinatedEffectDefinition am
# Pawn, oder ein HUD-Element, das nur auf "Action Skill aktiv" reagiert und sich nicht pro Skill
# einstellen laesst. GEPARKT auf Nutzerwunsch - das Aussehen nimmt sich Phase 8 als Ganzes vor,
# dann mit eigenem Farbschema statt Herumoperieren an einem geerbten Effekt.
#
# Zwei Lehren, die teurer waren als der Rahmen:
#   - Ein stiller except verschleiert den Unterschied zwischen "Hook feuert nicht" und "Hook feuert,
#     Zugriff scheitert". Immer loggen.
#   - "Eintrag -1 -> -1" hiess nicht "zu frueh gerufen" (so hatte ich es gedeutet), sondern
#     "falsche Objektart". Erst die Liste ALLER aktiven Effekte hat die beiden Faelle getrennt.
# ---------------------------------------------------------------------------


def _retry_skilltree(quelle: str) -> None:
    """Rueckfallebene: die Baumkette nachholen, falls sie beim Modulstart nicht zustande kam.
    Im Normalfall steht sie da bereits und diese Funktion tut nichts (Test 2026-09-20). Sie bleibt,
    weil ein Fehlschlag sonst erst im Skillmenue auffiele - und dann waere es zu spaet."""
    if _skilltree_ready:
        return
    klasse = _find("PlayerClassDefinition", f"GD_Assassin.Character.CharClass_{CHARACTER_NAME}")
    if klasse is None:
        logging.info(f"[ZB] Baumkette ({quelle}): Chronomaster-Klasse fehlt noch")
        return
    logging.info(f"[ZB] Baumkette: neuer Anlauf aus {quelle}")
    ensure_skilltree(klasse)


def _on_build_character_list(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST-Hook auf das Charakter-Menue - die letzte Station vor jedem Laden. Anders als
    CommitSelectableCharacters kommt hier auch vorbei, wer einen VORHANDENEN Charakter laedt.
    Reine Rueckfallebene: im Normalfall steht die Kette schon seit dem Modulstart."""
    _retry_skilltree("BuildCharacterList")
    try:
        icons_nachholen("BuildCharacterList")   # v1.38: DLC-Icons
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Icons nachholen: {ex}")


def register_tracers() -> None:
    from unrealsdk.hooks import Type, add_hook  # noqa: PLC0415
    add_hook(COMMIT_FUNC, Type.PRE, "zb_spike_c", _on_commit_characters)
    add_hook(LIST_FUNC, Type.POST, "zb_baumkette", _on_build_character_list)
    # Phase 3: die Skilltaste wird zu Legen und Zuenden. Greift nur beim Chronomaster (ist_chronomaster).
    add_hook(SKILL_STARTED, Type.POST, "zb_legen", _on_skill_started)
    add_hook(SKILL_PRESSED, Type.PRE, "zb_zuenden", _on_start_pressed)
    add_hook(SKILL_ENDED, Type.POST, "zb_verpuffen", _on_skill_ended)
    add_hook(ACTIVATE_SKILL_FUNC, Type.PRE, "zb_stealth", _on_activate_skill)
    add_hook(POST_AK_EVENT_FUNC, Type.PRE, "zb_klang", _on_post_ak_event)
    add_hook(TICK_FUNC, Type.POST, "zb_ticker", _on_player_tick)  # Handgriff 2, v0.59
    add_hook(INPUT_KEY_FUNC, Type.PRE, "zb_taste", _on_input_key)  # Schattenanker, v0.95
    add_hook(KILLED_ENEMY_FUNC, Type.POST, "zb_kill", _on_notify_killed_enemy)  # Handgriff 3, v0.66
    add_hook(UPDATE_KILL_SKILLS_FUNC, Type.PRE, "zb_killskills", _on_update_kill_skills)  # v1.16
    add_hook(TAKE_DAMAGE_FUNC, Type.PRE, "zb_schaden_vor", _on_take_damage_pre)     # Paket B, v0.84
    add_hook(TAKE_DAMAGE_FUNC, Type.POST, "zb_schaden_nach", _on_take_damage_post)  # Paket B, v0.84
    for fname in SCHADEN_KANDIDATEN:  # v0.85: welcher Weg traegt Waffenschaden ueberhaupt?
        add_hook(fname, Type.POST, f"zb_zaehl_{fname}", _make_schaden_zaehler(fname))
    for fname in FFYL_HINEIN + FFYL_HERAUS:  # v0.89: Es war nie passiert
        add_hook(fname, Type.POST, f"zb_ffyl_{fname}", _make_ffyl_hook(fname, fname in FFYL_HINEIN))
    for fname in TRACE_FUNCS:
        try:
            add_hook(fname, Type.POST, f"zb_spur_{fname}", _make_tracer(fname))
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Spur-Hook {fname}: {ex}")


def unregister_tracers() -> None:
    from unrealsdk.hooks import Type, remove_hook  # noqa: PLC0415
    remove_hook(COMMIT_FUNC, Type.PRE, "zb_spike_c")
    remove_hook(LIST_FUNC, Type.POST, "zb_baumkette")
    remove_hook(SKILL_STARTED, Type.POST, "zb_legen")
    remove_hook(SKILL_PRESSED, Type.PRE, "zb_zuenden")
    remove_hook(SKILL_ENDED, Type.POST, "zb_verpuffen")
    remove_hook(ACTIVATE_SKILL_FUNC, Type.PRE, "zb_stealth")
    remove_hook(POST_AK_EVENT_FUNC, Type.PRE, "zb_klang")
    remove_hook(TICK_FUNC, Type.POST, "zb_ticker")
    remove_hook(INPUT_KEY_FUNC, Type.PRE, "zb_taste")
    remove_hook(KILLED_ENEMY_FUNC, Type.POST, "zb_kill")
    remove_hook(UPDATE_KILL_SKILLS_FUNC, Type.PRE, "zb_killskills")
    remove_hook(TAKE_DAMAGE_FUNC, Type.PRE, "zb_schaden_vor")
    remove_hook(TAKE_DAMAGE_FUNC, Type.POST, "zb_schaden_nach")
    for fname in SCHADEN_KANDIDATEN:
        try:
            remove_hook(fname, Type.POST, f"zb_zaehl_{fname}")
        except Exception:  # noqa: BLE001
            pass
    for fname in FFYL_HINEIN + FFYL_HERAUS:
        try:
            remove_hook(fname, Type.POST, f"zb_ffyl_{fname}")
        except Exception:  # noqa: BLE001
            pass
    for fname in TRACE_FUNCS:
        try:
            remove_hook(fname, Type.POST, f"zb_spur_{fname}")
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Spike E/D: Wie schaltet das SDK einen Skill, und traegt die Klasse einen eigenen Baum?
#
# Betrifft 23 der 36 Skills (docs/skills.md, Abschnitt 6). Dieser Befehl LIEST nur:
# Funktionslisten, Objekte, Attributwerte. Kein Aufruf, kein Schreiben - die Aufrufe
# kommen erst, wenn die Signaturen aus diesem Log bekannt sind (falsche Argumenttypen
# an Engine-Funktionen sind ein Absturzrisiko).
# ---------------------------------------------------------------------------

# Messgroesse fuer Spike E: FootSpeed, Basiswert 440. Ein Skill "wirkt" erst, wenn der Wert
# gemessen ist (Regel 3).
#
# Testskill ist Innervate: DURATION_Infinite und +7 % FootSpeed JE RANG - damit laesst sich auch
# UpdateSkillGrade (der Stack-Mechanismus) pruefen. Skill_Speed taugte dafuer nicht: er ist
# DURATION_Timed 0.75 und war zwischen zwei Konsolenbefehlen laengst wieder aus (Test 21:34),
# und sein PerGradeUpgrade ist 0 - der Rang haette ohnehin nichts geaendert.
PROBE_ATTR = ("AttributeDefinition", "D_Attributes.GameplayAttributes.FootSpeed")
PROBE_SKILL = "GD_Assassin_Skills.Cunning.Innervate"  # Infinite, +7 % FootSpeed je Rang, MaxGrade 5


def attr_value(cls: str, path: str, obj: UObject) -> Any:
    """Aktueller Wert eines Attributs an einem Objekt. GetValue liefert teils ein Tupel."""
    attr = _find(cls, path)
    if attr is None:
        return f"<Attribut {path} nicht geladen>"
    try:
        v = attr.GetValue(obj)
        return float(v[0] if isinstance(v, tuple) else v)
    except Exception as ex:  # noqa: BLE001
        return f"<Fehler {ex}>"


# ---------------------------------------------------------------------------
# Skills schalten (Spike E, beantwortet und gemessen 2026-09-19)
#
# pc.GetSkillManager() liefert einen SkillEffectManager. Gemessen: ActivateSkill(pc, Skill_Speed)
# hebt FootSpeed 440 -> 550 (+25 %). Damit stehen alle 12 H+S-Skills aus docs/skills.md.
#
# FALLE: Der "SkillInstigator" ist der CONTROLLER, nicht der Pawn - mit dem Pawn kommt
# "Object is not instance of Controller". Deshalb nimmt jede Funktion hier den pc.
# ---------------------------------------------------------------------------


def skill_manager() -> UObject | None:
    """Den SkillEffectManager holen. Nie cachen - er haengt an der Welt und wechselt mit der Karte."""
    pc = local_pc()
    if pc is None:
        return None
    try:
        return pc.GetSkillManager()
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] GetSkillManager: {ex}")
        return None


def skill_an(skill: UObject, grade: int = 1) -> bool:
    """Skill aktivieren. Laeuft, bis er deaktiviert wird - Aufraeumen ist Aufgabe des Aufrufers."""
    sm, pc = skill_manager(), local_pc()
    if sm is None or pc is None or skill is None:
        return False
    try:
        return bool(sm.ActivateSkill(pc, skill, None, grade))
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] ActivateSkill {skill._path_name()}: {ex}")
        return False


def skill_aus(skill: UObject) -> bool:
    sm, pc = skill_manager(), local_pc()
    if sm is None or pc is None or skill is None:
        return False
    try:
        sm.DeactivateSkill(pc, skill, False)
        return True
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] DeactivateSkill {skill._path_name()}: {ex}")
        return False


def skill_grad(skill: UObject, grade: int) -> bool:
    """Rang eines laufenden Skills aendern - der Stack-Mechanismus (Gespannte Zeit, Abstand,
    Wiederkehr): ein Stack = ein Rang.

    FALLE (gemessen 21:41 und 21:48): UpdateSkillGrade allein gibt True zurueck, laesst den
    Attributwert aber stehen. Erst RefreshSkillsForInstigator rechnet die Modifikatoren neu
    (470.8 -> 594.0). Deshalb gehoeren die beiden hier zusammen und werden nie getrennt.
    """
    sm, pc = skill_manager(), local_pc()
    if sm is None or pc is None or skill is None:
        return False
    try:
        ok = bool(sm.UpdateSkillGrade(pc, skill, grade))
        sm.RefreshSkillsForInstigator(pc)
        return ok
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] UpdateSkillGrade {skill._path_name()}: {ex}")
        return False


def skills_aus_alle() -> bool:
    """Alle vom Modul aktivierten Skills abraeumen (Kartenwechsel, Tod, Modul aus).
    Gemessen: setzt FootSpeed zuverlaessig auf den Basiswert zurueck."""
    sm, pc = skill_manager(), local_pc()
    if sm is None or pc is None:
        return False
    try:
        sm.DeactivateAllSkillsForInstigator(pc)
        return True
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] DeactivateAllSkillsForInstigator: {ex}")
        return False


def skill_aktiv(skill: UObject) -> bool:
    sm, pc = skill_manager(), local_pc()
    if sm is None or pc is None or skill is None:
        return False
    try:
        return bool(sm.IsSkillActive(pc, skill))
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] IsSkillActive {skill._path_name()}: {ex}")
        return False


def kopie() -> None:
    """Spike D: eine eigene Skill-Kopie anlegen, ihren Wert aendern und die Wirkung messen.

    Die Kernfrage ist nicht das Kopieren (das kennen wir von der Klasse, Spike C), sondern ob
    sich SkillEffectDefinitions beschreiben laesst - ein Array von Structs. Deshalb zwei Wege:
    (a) Element direkt anfassen, (b) das ganze Array neu setzen. Bei Hotfixes greifen
    Struct-Felder in Arrays nachweislich nicht einzeln (CLAUDE.md) - ob das fuers SDK auch gilt,
    ist genau diese Frage.

    Traegt das, dann koennen Skills als Laufzeit-Kopien entstehen: Zer0 bleibt unangetastet
    und die Hotfix-Datei wird ueberfluessig (D4/D6).
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] kopie: kein Spieler-Pawn")
        return
    logging.info("[ZB] === SPIKE D: eigene Skill-Kopie ===")

    original = _find("SkillDefinition", PROBE_SKILL)
    if original is None:
        logging.error(f"[ZB] kopie: Vorlage {PROBE_SKILL} nicht geladen")
        return

    # 1. Kopie anlegen (idempotent, gerootet - wie bei der Klasse in Spike C)
    try:
        neu = _copy("SkillDefinition", PROBE_SKILL, "GD_Assassin_Skills.Cunning", "ZB_Testskill")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] kopie: construct_object fehlgeschlagen: {ex}")
        return
    logging.info(f"[ZB] Kopie: {neu._path_name()}")

    def wert(obj: UObject, label: str) -> None:
        try:
            sed = obj.SkillEffectDefinitions[0]
            logging.info(
                f"[ZB]   {label}: Attribut={sed.AttributeToModify._path_name() if sed.AttributeToModify else None}"
                f" Basis={sed.BaseModifierValue.BaseValueConstant:.3f}"
                f" jeRang={sed.PerGradeUpgrade.BaseValueConstant:.3f}"
            )
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB]   {label}: Lesen fehlgeschlagen: {ex}")

    wert(original, "Original vorher")
    wert(neu, "Kopie vorher")

    # 2. Weg (a): das Struct im Array direkt anfassen. Innervates Eintrag 0 ist FootSpeed
    #    (+0.07 je Rang) - wir setzen 0.50, damit die Wirkung unuebersehbar ist (440 -> 660).
    ZIEL = 0.50
    try:
        sed = neu.SkillEffectDefinitions[0]
        sed.BaseModifierValue.BaseValueConstant = ZIEL
        sed.PerGradeUpgrade.BaseValueConstant = ZIEL
        logging.info("[ZB] Weg a: Element direkt beschrieben")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Weg a: {ex}")
    wert(neu, "Kopie nach Weg a")

    # 3. Weg (b): ganzes Array neu setzen - noetig, falls (a) nur auf einer Kopie gearbeitet hat.
    try:
        if abs(float(neu.SkillEffectDefinitions[0].BaseModifierValue.BaseValueConstant) - ZIEL) > 0.001:
            liste = list(neu.SkillEffectDefinitions)
            liste[0].BaseModifierValue.BaseValueConstant = ZIEL
            liste[0].PerGradeUpgrade.BaseValueConstant = ZIEL
            neu.SkillEffectDefinitions = liste
            logging.info("[ZB] Weg b: ganzes Array neu gesetzt")
            wert(neu, "Kopie nach Weg b")
        else:
            logging.info("[ZB] Weg b: nicht noetig, Weg a hat gehalten")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Weg b: {ex}")

    # 4. Bleibt das Original unberuehrt? Das ist der ganze Sinn der Uebung (Zer0 unangetastet).
    wert(original, "Original nachher")

    # 5. Wirkung messen: erst die Kopie, dann das Original.
    def messung(label: str) -> None:
        logging.info(f"[ZB]   >>> FootSpeed {label}: {attr_value(*PROBE_ATTR, pawn)}")

    messung("Ausgangswert")
    logging.info(f"[ZB] Kopie aktivieren -> {skill_an(neu, 1)}")
    messung("Kopie aktiv (erwartet ~660 statt 470.8)")
    skill_aus(neu)
    messung("Kopie aus")
    logging.info(f"[ZB] Original aktivieren -> {skill_an(original, 1)}")
    messung("Original aktiv (erwartet 470.8 - unveraendert)")
    skill_aus(original)
    skills_aus_alle()
    messung("Ende")
    logging.info("[ZB] === SPIKE D Ende ===")


def skill_befehl(aktion: str, rest: list[str]) -> None:
    """zb skill an|aus|grad N|status [PFAD] - die Skill-API von Hand ausloesen, mit Messung.

    Spike E Runde 3 hat ActivateSkill belegt (FootSpeed 440 -> 550). Runde 4 prueft mit diesem
    Befehl die uebrigen Funktionen: Deaktivieren, Rang aendern (Stacks), Zustand lesen.
    Standardskill ist Skill_Speed, weil seine Wirkung an FootSpeed direkt messbar ist.
    """
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        logging.error("[ZB] skill: kein Spieler-Pawn")
        return
    # Rang steht bei 'grad' vorn, der Pfad ist immer das letzte Argument (oder der Standardskill).
    grade = 1
    path = PROBE_SKILL
    for arg in rest:
        if arg.isdigit():
            grade = int(arg)
        elif "." in arg:
            path = arg
    skill = _find("SkillDefinition", path)
    if skill is None:
        logging.error(f"[ZB] skill: {path} nicht geladen")
        return

    logging.info(f"[ZB] === skill {aktion} {path} (Rang {grade}) ===")
    # Messgroesse: das Attribut des ERSTEN Effekts dieses Skills (v0.60 - bis dahin immer FootSpeed,
    # was fuer die WeaponDamage-Kopien nichts sagt). Weapon.*-Attribute werden an der Waffe gelesen.
    try:
        eff = skill.SkillEffectDefinitions[0]
        mess_attr = eff.AttributeToModify
        mess_pfad = mess_attr._path_name() if mess_attr is not None else PROBE_ATTR[1]
        logging.info(f"[ZB]   Effekt 0: {mess_pfad.rsplit('.', 1)[-1]} Base {float(eff.BaseModifierValue.BaseValueConstant):.4f}"
                     f" je Grad {float(eff.PerGradeUpgrade.BaseValueConstant):.4f} | MaxGrade {skill.MaxGrade} | SkillType {skill.SkillType}")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB]   Effekt 0 lesen: {ex}")
        mess_pfad = PROBE_ATTR[1]
    mess_obj = pawn.Weapon if ".Weapon." in mess_pfad and pawn.Weapon is not None else pawn
    mess_name = mess_pfad.rsplit(".", 1)[-1]

    def messung(label: str) -> None:
        logging.info(f"[ZB]   >>> {mess_name} {label}: {attr_value('AttributeDefinition', mess_pfad, mess_obj)} | aktiv={skill_aktiv(skill)}")

    messung("vorher")
    match aktion:
        case "an":
            logging.info(f"[ZB]   ActivateSkill -> {skill_an(skill, grade)}")
        case "aus":
            logging.info(f"[ZB]   DeactivateSkill -> {skill_aus(skill)}")
        case "grad":
            logging.info(f"[ZB]   UpdateSkillGrade({grade}) -> {skill_grad(skill, grade)}")
        case "status":
            pass
        case "stack":
            # Der Stack-Test muss in EINEM Befehl laufen: ein Skill kann zwischen zwei
            # Konsolenbefehlen ablaufen (Skill_Speed, Test 21:34), dann findet UpdateSkillGrade
            # keine Instanz und gibt False - das sah nach einem Fehler aus, war aber keiner.
            logging.info(f"[ZB]   ActivateSkill(Rang 1) -> {skill_an(skill, 1)}")
            messung("Rang 1")
            for g in range(2, grade + 1):
                logging.info(f"[ZB]   UpdateSkillGrade({g}) -> {skill_grad(skill, g)}")
                messung(f"Rang {g}")
            logging.info(f"[ZB]   DeactivateSkill -> {skill_aus(skill)}")
        case _:
            logging.info("[ZB] skill an | aus | grad N | stack N | status [PFAD]")
            return
    messung("nachher")


# ---------------------------------------------------------------------------
# Testhilfen (CLAUDE.md, Regel 5: nur auf dem Testcharakter, als solche gekennzeichnet)
#
# Alle drei aendern den Spielstand DAUERHAFT. Deshalb die Sperre unten: sie laufen nur,
# wenn der geladene Charakter der Chronomaster ist - der Spielstand des Nutzers (Zer0 &
# Co.) kann damit nicht versehentlich verlevelt werden.
# Muster uebernommen aus ../borderlands 2 mod/sdk/fl4k_pet (dort im Spiel bewiesen).
# ---------------------------------------------------------------------------


def testchar_only(pc: UObject | None) -> bool:
    """True, wenn der geladene Charakter der Chronomaster ist. Sonst Hinweis ins Log und False."""
    if pc is None:
        logging.error("[ZB] TESTHILFE: kein Spieler geladen")
        return False
    cls = player_class(pc)
    if not (cls and cls.endswith(f"CharClass_{CHARACTER_NAME}")):
        logging.error(f"[ZB] TESTHILFE abgelehnt: geladen ist {cls or 'nichts'}, nicht der {CHARACTER_NAME}")
        return False
    return True


def xp(amount: int) -> None:
    """Genau N Erfahrungspunkte gutschreiben - EINMAL, keine Schleife.

    Warum nicht "bis Stufe N" (v0.16, im Spiel widerlegt): ExpLevel aktualisiert sich nicht
    innerhalb des Aufrufs. Eine Schleife "solange ExpLevel < Ziel: ExpEarn(...)" bricht deshalb
    nie ab - sie lief 2000 mal durch, vergab 100 Mio XP und setzte den Testcharakter auf Stufe 80,
    waehrend das Log am Ende noch "Stufe 2 -> 2" meldete (Log 2026-09-19, 20:41:32).
    Ein Komfortbefehl "levels N" braucht die XP-Schwelle pro Stufe; die ist noch nicht gefunden
    (Diagnose: zb funcs WillowPlayerController exp).

    Anhaltswerte: Stufe 2 kostet ~360 XP, Stufe 10 ~26 000, Stufe 30 ~600 000 - lieber klein
    anfangen und nachlegen. Die neue Stufe steht erst im naechsten Frame im HUD.
    DeveloperFreeLevels ist im Verkaufsspiel wirkungslos (FL4K-Projekt, Test 2026-09-19).
    """
    pc = local_pc()
    if not testchar_only(pc):
        return
    if amount > 2_000_000:
        logging.error(f"[ZB] TESTHILFE xp: {amount} abgelehnt - hoechstens 2 000 000 pro Aufruf, sonst lieber nachlegen")
        return
    try:
        before = pc.PlayerReplicationInfo.ExpLevel
        pc.ExpEarn(amount, 0, 0)
        logging.info(f"[ZB] TESTHILFE xp: {amount} XP gutgeschrieben (Stufe vor dem Aufruf: {before};"
                     " die neue Stufe steht erst im naechsten Frame)")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] TESTHILFE xp: {ex}")


def respec() -> None:
    """Skillpunkte kostenlos zuruecksetzen."""
    pc = local_pc()
    if not testchar_only(pc):
        return
    try:
        n = pc.ResetSkillTree(False, False)
        logging.info(f"[ZB] TESTHILFE respec: Skillbaum zurueckgesetzt, {n} Punkte frei")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] TESTHILFE respec: {ex}")


def cash(amount: int) -> None:
    """Geld gutschreiben. DeveloperGiveCash allein ist womoeglich stillgelegt, deshalb zusaetzlich
    der Verkaufs-Weg (PlayerSoldItem) - so im FL4K-Projekt uebernommen."""
    pc = local_pc()
    if not testchar_only(pc):
        return
    try:
        pc.DeveloperGiveCash(amount)
        pc.PlayerSoldItem(0, amount)
        logging.info(f"[ZB] TESTHILFE cash: {amount} gutgeschrieben")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] TESTHILFE cash: {ex}")


def on_enable() -> None:
    register_tracers()
    ensure_seventh_character()
    logging.info(f"[ZB] {CHARACTER_NAME}-Modul v{__version__} aktiviert ({len(TRACE_FUNCS)} Spur-Hooks)")


def on_disable() -> None:
    unregister_tracers()
    zeitspur_alle_zuruecksetzen()
    for zweck in {h[2] for h in _hologramme}:
        holo_entfernen(zweck, "Modul deaktiviert")
    bombe_weg("Modul deaktiviert")
    logging.info("[ZB] Modul deaktiviert")


# --- Icon-Katalog (v1.36, Testbefehl) --------------------------------------------------------------
# Nutzerwunsch 2026-09-27: passende Icons statt der geerbten Vorlagen-Icons. SkillDefinition.SkillIcon
# ist ein SwfMovie (Dump). Die Icons jeder Klasse liegen in ihrem GD_<Klasse>_Streaming_SF (Suche in den
# .upk, 2026-09-27) - dasselbe Paket, aus dem wir Zer0s Vorlagen holen. `zb icons KLASSE [START]` legt die
# Icons einer Klasse der Reihe nach auf unsere 36 Baum-Skills, damit der Nutzer sie im Skillbaum sieht
# (ein Screenshot je Klasse); das Log sagt, welches Icon auf welchem Skill liegt. `zb icons zurueck`
# stellt die Vorlagen-Icons wieder her. OFFEN: ob der Skillbaum das Icon live liest oder zwischenspeichert.
ICON_KLASSEN = {
    "zer0": ("GD_Assassin_Streaming_SF", "SharedSkillIcons_Assassin"),
    "maya": ("GD_Siren_Streaming_SF", "SharedSkillIcons_Siren"),
    "axton": ("GD_Soldier_Streaming_SF", "SharedSkillIcons_Soldier"),
    "salvador": ("GD_Mercenary_Streaming_SF", "SharedSkillIcons_Mercenary"),
    "gaige": ("GD_Tulip_Mechro_Streaming_SF", "UI_Tulip_SharedSkillIcons_Mech"),
    "krieg": ("GD_Lilac_Psycho_Streaming_SF", "UI_Lilac_SharedSkillIcons_Psyc"),
}
BAUM_TITEL = ("HINDSIGHT", "REWIND", "DETOUR")
# Skillpfad -> Pfad des Vorlagen-Icons. Pfade statt Objekte: keine Referenzen cachen (CLAUDE.md).
_icon_original: dict[str, str] = {}


def _baum_skills() -> list[tuple[str, int, Skill, UObject]]:
    """Alle Baum-Skills in Baum-/Reihenfolge: (Baumtitel, Reihe ab 1, Skill, Objekt)."""
    aus = []
    for titel, (tabelle, outer) in zip(BAUM_TITEL, BAEUME):
        for reihe, tier in enumerate(tabelle, 1):
            for sk in tier:
                obj = _find("SkillDefinition", f"{outer}.{sk.name}")
                if obj is not None:
                    aus.append((titel, reihe, sk, obj))
    return aus


def icons_katalog(klasse: str, start: int = 0) -> None:
    skills = _baum_skills()
    if klasse == "zurueck":
        for _t, _r, sk, obj in skills:
            pfad = _icon_original.get(obj._path_name())
            if pfad is not None:
                obj.SkillIcon = _find("SwfMovie", pfad)
        logging.info(f"[ZB] icons: {len(_icon_original)} Vorlagen-Icons zurueckgesetzt")
        return
    if klasse not in ICON_KLASSEN:
        logging.error(f"[ZB] icons: Klasse unbekannt - {' | '.join(ICON_KLASSEN)} | zurueck")
        return
    paket, gruppe = ICON_KLASSEN[klasse]
    try:
        unrealsdk.load_package(paket)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] icons: load_package({paket}): {ex}")
    icons = sorted(
        (m for m in unrealsdk.find_all("SwfMovie", exact=True) if m._path_name().startswith(gruppe + ".")),
        key=lambda m: m._path_name().lower(),
    )
    logging.info(f"[ZB] icons {klasse}: {len(icons)} Icons in {gruppe} (nach load_package({paket})), ab Nr. {start}")
    if not icons:
        return
    for i, (titel, reihe, sk, obj) in enumerate(skills):
        pfad = obj._path_name()
        if pfad not in _icon_original and obj.SkillIcon is not None:
            _icon_original[pfad] = obj.SkillIcon._path_name()
        n = start + i
        if n >= len(icons):
            logging.info(f"[ZB] icons   {titel} R{reihe} {sk.titel:<20} <- (keins mehr)")
            continue
        obj.SkillIcon = icons[n]
        logging.info(f"[ZB] icons   {titel} R{reihe} {sk.titel:<20} <- {n:2d} {icons[n]._path_name().split('.', 1)[1]}")
    if start + len(skills) < len(icons):
        logging.info(f"[ZB] icons: {len(icons) - start - len(skills)} weitere - zb icons {klasse} {start + len(skills)}")


@command("zb", description="Zeitbombe: status | legen | zuenden | ende | loeschen | bombe | baum | pakete | askill | skill | spur | props | funcs | xp | respec | cash")
def zb(args: Any) -> None:
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    match args.action:
        case "status":
            cls = player_class(pc) if pc else None
            # Ohne geladenen Charakter gibt es keine Klasse zu lesen - dann ist die Antwort nicht
            # "nein", sondern "unbekannt". Das "nein" im Hauptmenue hat schon einmal verwirrt.
            wer = ("ja" if ist_chronomaster(pc) else "nein") if cls else "? (kein Charakter geladen)"
            logging.info(
                f"[ZB] v{__version__} | Karte: {map_name(pc) if pc else '-'} | Pawn: {pawn._path_name() if pawn else 'nein'}"
                f" | Klasse: {cls or '-'} | Chronomaster: {wer}"
                f" | Zustand: {_state} | Anker: {_anchor or 'keiner'}"
            )
        case "legen":
            legen()
        case "zuenden":
            zuenden()
        case "ende":
            ende(args.args[0] if args.args else "2")
        case "loeschen":
            verpuffen("von Hand verworfen")
        case "granate":
            # zb granate [aus] - jedes neue Projektil mit Kollisionsfeldern loggen (v1.29, Wurf)
            granate_spaeher(not (args.args and args.args[0] == "aus"))
        case "trace":
            # zb trace - Kollisionspruefung nach unten, fuenf Varianten (v1.22, Wurf)
            trace_diag()
        case "bombe":
            # zb bombe [weg [1|2|3] | diag | koll 1|2|3 | MESHPFAD [SCALE]] - Bombe ohne den Skill bemuehen
            if args.args and args.args[0] == "weg":
                bombe_weg("von Hand", int(args.args[1]) if len(args.args) > 1 else 1)
            elif args.args and args.args[0] == "diag":
                bombe_diag()
            elif args.args and args.args[0] == "koll":
                actor = _bombe()
                if actor is None:
                    logging.error("[ZB] koll: keine Bombe liegt")
                else:
                    bombe_kollision_aus(actor, int(args.args[1]) if len(args.args) > 1 else 1)
            elif pawn is None:
                logging.error("[ZB] bombe: kein Spieler-Pawn")
            else:
                mesh = args.args[0] if args.args else BOMB_MESH
                scale = float(args.args[1]) if len(args.args) > 1 else BOMB_SCALE
                bombe_setzen(pawn, mesh, scale)
        case "meshes":
            meshes(args.args[0] if args.args else "")
        case "icons":
            # zb icons KLASSE [START] | zurueck - Icon-Katalog im Skillbaum (v1.36)
            if not args.args:
                logging.info(f"[ZB] zb icons {' | '.join(ICON_KLASSEN)} [START] | zurueck")
            else:
                icons_katalog(args.args[0].lower(), int(args.args[1]) if len(args.args) > 1 else 0)
        case "rang":
            # zb rang NAME - Punkte des Spielers in einem Baum-Skill (prueft PlayerSkillTree.GetSkillGrade)
            for n in (args.args or list(SKILL_OUTER)):
                logging.info(f"[ZB] rang {n}: {skill_rang(n)}")
        case "wirkung":
            # zb wirkung an|aus NAME [GRAD] - Effekt-Skill eines HS-Skills von Hand schalten
            if len(args.args) < 2:
                logging.info("[ZB] zb wirkung an|aus NAME [GRAD]")
            elif args.args[0] == "an":
                wirkung_an(args.args[1], int(args.args[2]) if len(args.args) > 2 else None)
            else:
                wirkung_aus(args.args[1])
        case "attr":
            # zb attr [NAME|PFAD] [pawn|weapon|pc] - Attributwert ablesen (Messgroesse ohne Ticker)
            name = args.args[0] if args.args else "WeaponDamage"
            pfad = {"weapondamage": A_SCHADEN, "footspeed": A_TEMPO, "krit": A_KRIT, "magazin": A_MAGAZIN,
                    "feuerrate": A_FEUERRATE}.get(name.lower(), name)
            which = args.args[1] if len(args.args) > 1 else "weapon"
            obj = {"pawn": pawn, "pc": pc, "weapon": pawn.Weapon if pawn else None}.get(which)
            logging.info(f"[ZB] attr {pfad.rsplit('.', 1)[-1]} ({which}) = {attr_value('AttributeDefinition', pfad, obj) if obj else 'kein Objekt'}")
        case "props":
            which = args.args[0] if args.args else "pawn"
            flt = args.args[1] if len(args.args) > 1 else ""
            obj = {"pawn": pawn, "pc": pc, "weapon": pawn.Weapon if pawn else None}.get(which)
            dump_props(obj, flt)
        case "funcs":
            # zb funcs KLASSE [FILTER]
            dump_funcs(args.args[0], args.args[1] if len(args.args) > 1 else "") if args.args else None
        case "enum":
            # zb enum [FILTER] - Enums samt Werten (Standard: alles mit "skill" im Namen)
            dump_enum(args.args[0] if args.args else "skill")
        case "holo":
            # zb holo [SEKUNDEN] - ein Hologramm vor dir, zum Anschauen (v0.92)
            holo_test(float(args.args[0]) if args.args else 10.0)
        case "koop":
            # zb koop selbst|aus - Testhilfe: eigener Pawn zaehlt als Verbuendeter (v0.95)
            koop_schalter(args.args[0] if args.args else "aus")
        case "stapeltest":
            # zb stapeltest [aus] - stapelt das Spiel Instanzen eines Skills? (v1.16)
            stapeltest(args.args[0] if args.args else "")
        case "immun":
            # zb immun [SEKUNDEN] - Schadensimmunitaet von Hand, zum Messen (v1.12)
            immunitaet(float(args.args[0]) if args.args else 10.0, "von Hand")
        case "effekte":
            # zb effekte an|aus|log|test - sichtbare Effekte (v1.00)
            effekte_schalter(args.args[0] if args.args else "")
        case "schatten":
            # zb schatten [los] - Schattenanker: Pufferstand; 'los' zuendet von Hand (v0.95)
            if args.args and args.args[0] == "los" and local_pc() is not None:
                schatten_zuenden(local_pc(), "von Hand")
            else:
                schatten_zeigen()
        case "ffyl":
            # zb ffyl - welcher Fight-for-your-Life-Kandidat gefeuert hat (v0.89)
            ffyl_zeigen()
        case "fasttot":
            # zb fasttot - TESTHILFE, nur Chronomaster: Schild 0, Leben 1 (v0.89)
            fast_tot()
        case "fenster":
            # zb fenster - wo die Restzeit des Fensters steht (Diagnose Kurs halten, v0.89)
            fenster_zeigen()
        case "schaden":
            # zb schaden [reset] - welcher TakeDamage-Kandidat feuert, was filtert der Hook (v0.85)
            if args.args and args.args[0] == "reset":
                schaden_zuruecksetzen()
            else:
                schaden_zeigen()
        case "zeitlupe":
            # zb zeitlupe [ART 0-3] [FAKTOR] [RADIUS] - Verlangsamen ausprobieren (v0.85)
            zeitlupe_versuch(int(args.args[0]) if args.args else 1,
                             float(args.args[1]) if len(args.args) > 1 else 0.3,  # Art 0-4
                             float(args.args[2]) if len(args.args) > 2 else 15.0)
        case "stoss":
            # zb stoss [KRAFT] [ART] [RADIUS] - Rueckstoss-Varianten ausprobieren (1..5, s. Docstring)
            stoss_versuch(float(args.args[0]) if args.args else 542.0,
                          int(args.args[1]) if len(args.args) > 1 else 1,
                          float(args.args[2]) if len(args.args) > 2 else 8.0)
        case "ziel":
            # zb ziel [ANZAHL] [ABSTAND_M] - stehende Testziele spawnen (Rueckstoss messen)
            ziel_spawnen(int(args.args[0]) if args.args else 1,
                         float(args.args[1]) if len(args.args) > 1 else 5.0)
        case "gegner":
            # zb gegner [RADIUS] - was die Umkreissuche sieht (Diagnose fuer Paket A)
            gegner_zeigen(float(args.args[0]) if args.args else 50.0)
        case "ammo":
            # zb ammo - wo die Munitionsreserve wirklich steht
            ammo_zeigen()
        case "namen":
            # zb namen - alle offenen Funktionsnamen fuer Handgriff 4 auf einmal ins Log
            namen_sammeln()
        case "dejavu":
            # zb dejavu - das Kill-Ereignis von Hand melden (ohne den Skillzyklus zu durchlaufen)
            if not mechanik_dejavu("von Hand"):
                logging.info(f"[ZB] Deja-vu: nichts gemeldet (Rang {skill_rang('DejaVu')}) | {_kill_skills_zustand()}")
        case "kopie":
            kopie()
        case "baum":
            skilltree_status()
        case "pakete":
            pakete()
        case "askill":
            askill()
        case "skill":
            skill_befehl(args.args[0] if args.args else "status", args.args[1:])
        case "xp":
            xp(int(args.args[0]) if args.args else 1000)
        case "respec":
            respec()
        case "cash":
            cash(int(args.args[0]) if args.args else 1000000)
        case "spur":
            global _trace
            _trace = not _trace
            logging.info(f"[ZB] Spur {'an' if _trace else 'aus'}: Skill-Ereignisse werden {'geloggt' if _trace else 'nicht geloggt'}")
        case _:
            logging.info(
                "[ZB] zb status | legen | zuenden | ende [1|2|3] | loeschen | bombe [weg [1|2|3]|diag|koll 1|2|3|MESH [SCALE]] | meshes [FILTER]"
                " | rang [NAME] | wirkung an|aus NAME [GRAD] | attr [NAME|PFAD] [pawn|weapon|pc] | baum | pakete | askill | skill an|aus|grad N|stack N|status [PFAD] | kopie | spur"
                " | props pawn|pc|weapon FILTER | funcs KLASSE [FILTER] | enum [FILTER] | namen | gegner [RADIUS] | ziel [N] [ABSTAND] | stoss [KRAFT] [ART 1-8] | schaden [reset] | zeitlupe [ART 0-4] [FAKTOR] | ffyl | fenster | holo [SEKUNDEN] | koop selbst|aus | schatten [los] | effekte an|aus|log|test | immun [S] | ammo | dejavu"
                " | xp N | respec | cash N | fasttot (die letzten vier: Testhilfen, nur Chronomaster)"
            )


zb.add_argument("action", choices=["status", "legen", "zuenden", "ende", "loeschen", "bombe", "meshes", "rang", "wirkung", "attr", "props", "funcs", "enum", "namen", "gegner", "ziel", "stoss", "schaden", "zeitlupe", "ffyl", "fasttot", "fenster", "holo", "koop", "schatten", "effekte", "immun", "stapeltest", "ammo", "dejavu", "spur", "kopie", "baum", "pakete", "askill", "skill", "xp", "respec", "cash", "trace", "granate", "icons"])
zb.add_argument("args", nargs="*")

build_mod(
    name=CHARACTER_NAME,
    description="A new 7th Vault Hunter, the Timekeeper, with the Action Skill Time Bomb: throw it, fight, return - to where it landed, with the health, shield and ammo you had. Three new skill trees.",
    supported_games=Game.BL2,
    on_enable=on_enable,
    on_disable=on_disable,
)
