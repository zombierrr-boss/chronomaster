"""
Chronomaster in Borderlands 2 - SDK-Modul "chronomaster" (bis v1.34 "zeitbombe"). Version: siehe __version__ unten.

Stand 2026-10-02 (v1.55): spielfertig und veroeffentlicht (GitHub, Nexus). Alle 36 Skills wirken,
der Action Skill ist komplett, dazu eigenes Modell und Portrait (Pakete im Release, nicht im Repo).
Wo es weitergeht: plan.md, "Wiedereinstieg" und "Fahrplan". Status je Skill: docs/skills.md, 8.

Seit D4 (2026-09-19) traegt dieses Modul BEIDES - Daten und Logik. Skills, Baeume, Texte und Zahlen
entstehen als Laufzeit-Kopien; an Zer0s Objekten wird nichts geaendert (D6). src/hotfixes.txt und
exec zeitbombe.txt sind Altlast.

Aufbau - im Modul nach diesen Ueberschriften suchen:
  "Legen / Zuenden"                 Zustand, Anker, Teleport und Werte (legen, zuenden, verpuffen)
  "die Bombe am Anker (D9)"         Caesium-Ladung als DynamicSMActor, ohne Kollision
  "Die Bombe werfen"                unsichtbare Granate per Behavior_SpawnProjectile, Bombe folgt (WURF_*)
  "Phase 3, Schritt 1"              Verdrahtung: Skilltaste -> legen/zuenden, Ablauf -> verpuffen
  "Schattenanker"                   Capstone Baum 2: Ringpuffer, Taste halten (WillowUIInteraction:InputKey)
  "Spike C: Charakterliste"         der 7. Charakterslot (ensure_seventh_character), Kachel, Portrait (img://)
  "Die eigene Baumkette"            Wurzel + drei Aeste als Kopien (ensure_skilltree)
  "Phase 4-6"                       die 36 Skills: Tabellen BAUM_*, Bauarten H / KILL / HS / S / KS,
                                    SKILL_ICONS, HUD_SLOT; _baeume_fuellen
  "Schadensimmunitaet"              Reinigung / Zeitsprung ueber versteckte Effekt-Skills
  "Handgriff 2"                     Ticker (PlayerTick, 1/s mit liegender Bombe): Gespannte Zeit
  "Handgriff 3" / "Kill-Stacks"     Kill-Zaehler (NotifyKilledEnemy), Haste Stacks mit HUD-Zahl,
                                    Dauerfeuer, Echo Bullet / Dimensional Loop (Zusatzschuss), Time Loop
  "Handgriff 4, Paket A"            am Zuenden: Umkreis-Treffer (_treffer), Volle Rueckerstattung,
                                    Reinigung, Nachhall, Zeitsprung; Refill, Infinite, Borrowed Health
  "Handgriff 4, Paket B"            Schadens-Hooks: Paradoxon (WillowAIPawn:TakeDamage), Return to
                                    Sender (WillowPlayerPawn:TakeDamage); Zeitspur ist der Zeitwirbel
  "Handgriff 4, Paket C"            Fight for your Life: Es war nie passiert; Kurs halten
  "Handgriff 4, Paket D"            Hologramme: Zeitkapsel, Nachbild; "Sprengsatz, neu"
  "Handgriff 4, Paket E"            Verbuendete: Zeitkapsel-Heilung
  "Phase 8, Teil 1"                 sichtbare Effekte (Behavior_Explode ueber ruhende Projektile)
  "Phase 3, Schritt 4" / "5b"       Zer0s Unsichtbarkeit, Schadensstack und Klang abhaengen (Hooks)
  "Skills schalten"                 skill_an / skill_aus / skill_grad (Spike E)
  "Aussehen"                        eigenes Modell NUR am Chronomaster: Schnellscan ueber PawnList,
                                    gemerkte Pfade, Vollscan selten (v1.54, find_all kostet ~9 ms)
  zb fps / zb icons                 Messwerkzeuge (Frame-Zeiten, Icon-Katalog)

Konsole: "zb" ohne Argument listet alle Befehle (alles landet in Binaries/Win32/Plugins/unrealsdk.log,
Praefix [ZB]). Die Werkzeuge mit Zweck stehen in plan.md, "Werkzeuge". Am haeufigsten gebraucht:
  zb status | zb spur | zb funcs KLASSE [FILTER] | zb enum [FILTER] | zb attr [NAME] [pawn|weapon|pc]
  zb skin [an|aus|mat ...] | zb fps [SEKUNDEN] | zb effekte test | zb baum
Testhilfen - aendern den Spielstand DAUERHAFT, laufen nur auf dem Chronomaster (testchar_only):
  zb xp [N] | zb respec | zb cash [N] | zb fasttot

Die Regeln aus Abstuerzen und Fehlmessungen stehen in CLAUDE.md ("Technische Regeln"), die bewiesene
Technik mit Belegen in docs/spikes.md. Die wichtigsten fuer dieses Modul:
  - Laufzeit-Objekte (construct_object) sofort rooten (_root), sonst holt sie die GC.
  - Nie UObject-Huellen ueber Frames merken (Menue-Objekte, Materialien) - Pfade merken, frisch suchen.
  - An fremden Objekten erst Pfad pruefen, dann Eigenschaften, Funktionen zuletzt (_ist_welt_actor).
  - Struct-Arrays nur elementweise beschreiben; nie per Zuweisung kuerzen oder verlaengern.
  - Funktionsnamen nie raten ('zb funcs'), Hook-Pakete im Dump nachlesen ("Class="-Zeile).
  - Nach Hook-Aenderungen das Spiel neu starten - "rlm" laesst alte Hooks weiterlaufen.
  - find_all nie in haeufigen Ticks (geht immer die ganze Objektliste durch).
"""

import math
import random
import time
from dataclasses import dataclass
from typing import Any

import unrealsdk
from mods_base import ENGINE, Game, build_mod, command
from unrealsdk import logging
from unrealsdk.unreal import UObject, WeakPointer

__version__ = "1.73"
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
        try:
            mechanik_zeitstillstand(loc.X, loc.Y, loc.Z)   # v1.71 Time Freeze: ohne Flug am Wurfpunkt
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Time Freeze: {ex}")


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
    # Zeitsprung und Nachbild brauchen ihn.
    global _absprung
    _absprung = _vec(pawn.Location.X, pawn.Location.Y, pawn.Location.Z)
    try:
        endspurt_messen(pc)   # v1.69 Crunch Time: Restzeit VOR ResetActionSkill, der Faktor gilt fuer Sprengsatz und Nachhall
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Crunch Time: {ex}")
    # Sprengsatz (v0.94) explodiert am Spieler - das geht nur hier, solange er noch am Absprungpunkt steht.
    try:
        mechanik_sprengsatz(pawn)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Sprengsatz: {ex}")
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
    try:
        frieren_aus(f"Bombe weg: {grund}")   # v1.71 Time Freeze: gefroren bis die Bombe weg ist
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Time Freeze: auftauen: {ex}")
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
        mechanik_zeitstillstand(x, y, z)   # v1.71 Time Freeze: am Landepunkt
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Time Freeze: {ex}")
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
    passiert), Schaden/Stagger an Gegnern (Nachhall, Zeitsprung, Paradoxon),
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
        ("Actor", "HurtRadius", "Sprengsatz"),
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
# v1.46: eigenes Portrait als Texture2D (Paket ChronomasterPortrait, gebaut mit bl2_upk.texture).
# VERMUTUNG, ungetestet: Scaleform in UE3 laedt per "img://Paket.Textur" eine Textur als Bild.
PORTRAIT_PAKET = "ChronomasterPortrait"
PORTRAIT_TEXTUR = "ChronomasterPortrait.Chronomaster_Portrait"


def portrait_url() -> str:
    """img://-URL auf das eigene Portrait, sonst Zer0s SwfMovie (Paket fehlt oder laedt nicht)."""
    import os  # noqa: PLC0415
    cooked = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "WillowGame", "CookedPCConsole")
    if not os.path.isfile(os.path.join(cooked, PORTRAIT_PAKET + ".upk")):
        return PORTRAIT_PATH
    try:
        tex = _find("Texture2D", PORTRAIT_TEXTUR)
        if tex is None:
            paket = unrealsdk.load_package(PORTRAIT_PAKET)
            if paket is not None:
                _root(paket)
            tex = _find("Texture2D", PORTRAIT_TEXTUR)
        if tex is None:
            logging.error(f"[ZB] Portrait: {PORTRAIT_TEXTUR} nicht gefunden - Zer0s Portrait")
            return PORTRAIT_PATH
        _root(tex)
        return f"img://{PORTRAIT_TEXTUR}"
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Portrait: {ex} - Zer0s Portrait")
        return PORTRAIT_PATH


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
    ("Ausflug", "Branch_Bloodshed", "OVERCLOCK"),   # v1.56, bis v1.55 DETOUR
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
# Precisi0n 4 Effekte.
# ---------------------------------------------------------------------------

# Attribute (alle in docs/skills.md, Abschnitt 2, am Datenpaket verifiziert)
A_KRIT = "D_Attributes.GameplayAttributes.PlayerCriticalHitBonus"
A_MAGAZIN = "D_Attributes.Weapon.WeaponClipSize"
A_SCHADEN = "D_Attributes.Weapon.WeaponDamage"
A_FEUERRATE = "D_Attributes.Weapon.WeaponFireInterval"          # negativ = schneller
A_NACHLADEN = "D_Attributes.Weapon.WeaponReloadSpeed"           # negativ = schneller
A_TEMPO = "D_Attributes.GameplayAttributes.FootSpeed"
A_ZOOM = "D_Attributes.Weapon.WeaponZoomEndFOV"                  # negativ = schneller
A_HINTERHALT = "D_Attributes.DamageEnhancementModifiers.PlayerAttackUnsuspectingTargetModifier"
A_COOLDOWN = "D_Attributes.ActiveSkillCooldownResource.ActiveSkillCooldownConsumptionRate"
# v1.61b: "Shield Recharge Rate" im Sinne des Spiels (Badass-Rang, GD_Challenges.BadassSkill, MT_Scale).
# NICHT ShieldPassiveRegenerationRate - das ist die Dauerregeneration, ohne passendes Schild 0, ein Scale
# darauf bleibt 0 (gemessen v1.61: 0.0 bei 16 Stacks; Standby nutzte es bis v1.62).
A_SCHILDLADEN = "D_Attributes.ShieldResourcePool.ShieldOnIdleRegenerationRate"
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


# v1.67: orange Werte unter dem Kartentext (Feedback I11/F2) auch fuer Skills ohne eigenen Attribut-Effekt
# (S, HS, KS). Rezept aus dem Original, Dump: Zer0s Decepti0n traegt Effekte mit EffectTarget=TARGET_None -
# sie wirken auf niemanden, liefern aber die Zahl fuer die Praesentation ("Melee Damage: up to +150%").
# Der Baum-Skill bekommt je Zeile so einen Anzeige-Effekt auf ein Traeger-Attribut plus eine Praesentation;
# das Spiel zeigt Wert und Vorschau auf den naechsten Rang. Wert bei Grad g = basis + je_grad x (g - 1).
@dataclass(frozen=True)
class Zeile:
    text: str             # Praesentation; $NUMBER$ ist die Zahl
    basis: float          # Wert bei Rang 1
    je_grad: float        # Zuwachs je weiterem Rang
    prozent: bool = True
    dezimal: bool = False
    plus: bool = True     # Vorzeichen zeigen


def _Z(text: str, je_rang: float, **k) -> Zeile:  # noqa: N802 - linear je Rang (der Normalfall)
    return Zeile(text, je_rang, je_rang, **k)


ANZEIGE: dict[str, tuple] = {
    # Hindsight
    "Nachwirkung": (_Z("Weapon Damage: $NUMBER$", 0.04),),
    "GespannteZeit": (_Z("Weapon Damage per stack: $NUMBER$", 0.01),),
    "Eile": (_Z("Fire Rate, Reload Speed and Shield Recharge per stack: $NUMBER$", 0.003, dezimal=True),),
    "Paradoxon": (_Z("Damage dealt again: $NUMBER$", 0.10),),
    "Zuruecksenden": (_Z("Damage sent back: $NUMBER$", 0.25),),
    "Wiederkehr": (_Z("Weapon Damage per kill: $NUMBER$", 0.02),),
    "Langzeitgedaechtnis": (_Z("Bomb Window: $NUMBER$ seconds", 2.0, prozent=False),
                            _Z("Critical Hit Damage: $NUMBER$", 0.04)),
    # Rewind
    "Auffrischung": (_Z("Health and Shield restored: $NUMBER$", 0.04),),
    "VolleRueckerstattung": (_Z("Ammo refunded: $NUMBER$", 0.20, plus=False),),
    "GeliehenesLeben": (_Z("Health restored: $NUMBER$", 0.12),),
    "SichereKrits": (_Z("Duration: $NUMBER$ seconds", 1.0, prozent=False, plus=False),),
    "Zeitkapsel": (_Z("Ally Health Regeneration: $NUMBER$ per second", 0.008, dezimal=True),),
    "Nachbild": (Zeile("Duration: $NUMBER$ seconds", 3.0, 1.0, prozent=False, plus=False),),
    # Overclock
    "Nachfuellen": (_Z("Magazine refilled per kill: $NUMBER$", 0.05, plus=False),),
    "Dimensionsschleife": (_Z("Double shots after reload: $NUMBER$", 1.0, prozent=False, plus=False),),
    "GranatenRueckruf": (_Z("Chance: $NUMBER$", 0.06, plus=False),),
    "Echokugel": (Zeile("Echo every $NUMBER$ shots", 10.0, -1.25, prozent=False, plus=False),),
    "KursHalten": (_Z("Window per kill: $NUMBER$ seconds", 1.0, prozent=False),),
}


# v1.14/v1.18: HUD-Plaetze der Stack-Skills unter der XP-Leiste (Zer0 nutzt 2 und 3 - er ist hier nicht
# Wirt; Axton nutzt Plaetze bis 9, also gibt es mindestens so viele)
HUD_SLOT = {"Eile": 1, "Echokugel": 2, "Dimensionsschleife": 3, "GespannteZeit": 4, "Wiederkehr": 5, "Zeitschleife": 6}   # v1.61 Haste 1, v1.63b Echo 2, v1.64 Loop 3, v1.65 Time Loop 6
KS_TRACK_VORBILD = "GD_Assassin_Skills.Sniping.KillConfirmed_Stack"   # TRACKEDSKILL_Respond (Dump)

# Die Tabellen. Reihenfolge = Tier 1..6, innen links nach rechts. Werte aus docs/skills.md, 5.
BAUM_VERGANGENHEIT = [
    [_S("Gedaechtnis", "Memory", "Increases [skill]Critical Hit Damage[-skill] and [skill]Magazine Size[-skill].", 5, "H",
        (Effekt(A_KRIT, 0.04, "Critical Hit Damage: $NUMBER$"), Effekt(A_MAGAZIN, 0.05, "Magazine Size: $NUMBER$"))),
     _S("Nachwirkung", "Aftermath", "After you [skill]detonate[-skill], gain [skill]Weapon Damage[-skill] for 8 seconds.", 5, "HS",
        (Effekt(A_SCHADEN, 0.04, "Weapon Damage: $NUMBER$"),), dauer=8.0)],
    [_S("GespannteZeit", "Tension", "While the bomb is out, gain a stack of [skill]Weapon Damage[-skill] every second, up to 10.", 5, "HS",
        (Effekt(A_SCHADEN, 0.01, "Weapon Damage: $NUMBER$"),)),
     # v1.56: ersetzt Deja Vu, Encore und Push Forward (docs/skills.md 9.2). v1.61: gebaut - Kill-Stack-
     # Code (KILL_SKILLS) wieder angeschlossen, Dauerfeuer ueber den Feuer-Hook (_on_fire_ammunition).
     _S("Eile", "Haste Stacks", "[skill]Kill Skill[-skill]. Each kill grants a stack of Haste, and every 2 seconds of sustained fire grants one too. Up to 20 stacks, at most 10 from sustained fire. Starting 3 seconds after your last stack, one stack decays every second.", 5, "KS",
        (Effekt(A_FEUERRATE, -0.003, "Fire Rate: $NUMBER$", dezimal=True), Effekt(A_NACHLADEN, -0.003, "Reload Speed: $NUMBER$", dezimal=True),
         Effekt(A_SCHILDLADEN, 0.003, "Shield Recharge Rate: $NUMBER$", dezimal=True)))],
    [_S("Paradoxon", "Paradox", "When you detonate, the damage you dealt while the bomb was out hits the same enemies again.", 5, "S"),
     _S("Zuruecksenden", "Return to Sender", "Damage you take while the bomb is out is stored. When you detonate, it strikes back at the enemies who dealt it.", 5, "S"),
     _S("Nachhall", "Reverberation", "Detonating releases a shockwave where you arrive: enemies within 6 meters take [skill]Shock Damage[-skill] equal to twice your grenade damage and are staggered.", 1, "S")],
    [_S("Erinnerung", "Recollection", "The anchor saves your Haste Stacks. If you have fewer when you detonate, they come back.", 1, "S"),
     _S("Wiederkehr", "Recurrence", "After you [skill]detonate[-skill], gain [skill]Weapon Damage[-skill] for 10 seconds for each kill you made while the bomb was out (up to 10).", 5, "HS",
        (Effekt(A_SCHADEN, 0.02, "Weapon Damage: $NUMBER$"),), dauer=10.0)],
    [_S("Langzeitgedaechtnis", "Long-Term Memory", "The Time Bomb window lasts longer, and while the bomb is out you gain [skill]Critical Hit Damage[-skill].", 5, "HS",
        (Effekt(A_KRIT, 0.04, "Critical Hit Damage: $NUMBER$"),)),
     _S("Zeitspur", "Time Vortex", "While the bomb is out, a time vortex erupts at the anchor every 2 seconds if enemies are within 8 meters: [skill]Shock Damage[-skill] equal to your grenade damage.", 1, "S")],
    [_S("Zeitstillstand", "Time Freeze", "Throwing the bomb freezes all enemies within 25 meters of where it lands, bosses included. A frozen enemy thaws when hit, and that first hit deals double damage. The rest stay frozen until the bomb is gone.", 1, "S")],
]

BAUM_RUECKKEHR = [
    [_S("Auffrischung", "Refresh", "[skill]Detonating[-skill] also restores [skill]Health[-skill] and [skill]Shield[-skill], beyond the anchor values.", 5, "HS"),
     _S("Bereitschaft", "Standby", "Increases [skill]Cooldown Rate[-skill] and [skill]Shield Recharge Rate[-skill].", 5, "H",
        (Effekt(A_COOLDOWN, 0.02, "Cooldown Rate: $NUMBER$"), Effekt(A_SCHILDLADEN, 0.015, "Shield Recharge Rate: $NUMBER$", dezimal=True)))],
    [_S("VolleRueckerstattung", "Full Refund", "[skill]Detonating[-skill] refunds the ammo reserve you have used since throwing the bomb.", 5, "S"),
     _S("GeliehenesLeben", "Borrowed Health", "[skill]Detonating[-skill] instantly restores [skill]Health[-skill]. Over the next 15 seconds you pay back 125% of it, but never below 1 health. Each kill in that time clears 25% of the debt.", 5, "S")],
    [_S("Reinigung", "Cleanse", "Detonating removes all status effects. 2 seconds of damage immunity after you arrive.", 1, "S"),
     _S("SichereKrits", "Guaranteed Crits", "After you [skill]detonate[-skill], every hit is a [skill]Critical Hit[-skill] for a short time.", 5, "S"),
     _S("Zeitkapsel", "Time Capsule", "A hologram of you also appears at the anchor. It draws enemy fire and regenerates [skill]Health[-skill] for allies within 8 meters.", 5, "S")],
    [_S("EsWarNiePassiert", "It Never Happened", "If you fall into Fight for Your Life while a bomb is out, it detonates on its own.", 1, "S"),
     _S("Nachbild", "Afterimage", "When you [skill]detonate[-skill], an afterimage stays behind where you left and draws enemy fire.", 5, "S")],
    [_S("Sprengsatz", "Parting Gift", "When you detonate, you leave a massive explosion behind - in your grenade's element, 5x your grenade damage.", 1, "S"),
     _S("Endspurt", "Crunch Time", "The earlier you detonate, the stronger it gets: Reverberation and Parting Gift deal up to double damage, and the bomb itself explodes at the anchor.", 1, "S")],
    [_S("Schattenanker", "Shadow Anchor", "Even without a bomb out, the skill keeps remembering an anchor from 5 seconds ago. Hold the key for a shadow detonation (1.5x cooldown).", 1, "S")],
]

BAUM_AUSFLUG = [
    [_S("Weite", "Open Road", "Increases [skill]Movement Speed[-skill] and [skill]Aim Speed[-skill].", 5, "H",
        (Effekt(A_TEMPO, 0.03, "Movement Speed: $NUMBER$"), Effekt(A_ZOOM, -0.02, "Aim Speed: $NUMBER$"))),
     _S("Nachfuellen", "Refill", "Each kill refills part of your magazine, without using reserve ammo.", 5, "S")],
    # v1.64: HS nur fuer die HUD-Zahl (verbleibende Doppelschuesse); der Effekt ist 0 und wirkt nicht.
    [_S("Dimensionsschleife", "Dimensional Loop", "After every reload, your first shots fire twice. The counter next to your XP bar shows the double shots left.", 5, "HS",
        (Effekt(A_SCHADEN, 0.0, ""),)),
     _S("GranatenRueckruf", "Grenade Recall", "Each grenade you throw has a chance to come back to you.", 5, "S")],
    [_S("Ausbruch", "Breakout", "Throwing the bomb gives you +50% [skill]Movement Speed[-skill] for 3 seconds.", 1, "HS",
        (Effekt(A_TEMPO, 0.50, "Movement Speed: $NUMBER$"),), dauer=3.0),
     _S("Hinterhalt", "Ambush", "Increases damage against enemies that are not targeting you.", 5, "H",
        (Effekt(A_HINTERHALT, 0.04, "Damage vs. Unaware Enemies: $NUMBER$"),)),
     # v1.63b: HS nur fuer die HUD-Zahl (Schusszaehler); der Effekt ist 0 und wirkt nicht.
     _S("Echokugel", "Echo Bullet", "Every few shots, your shot fires twice. The counter next to your XP bar shows the shots until the next echo.", 5, "HS",
        (Effekt(A_SCHADEN, 0.0, ""),))],
    [_S("KursHalten", "Stay the Course", "Each kill while the bomb is out extends the Time Bomb window.", 5, "S"),
     # v1.65: HS nur fuer die HUD-Zahl (Kills bis zur Ladung, 5 = geladen); der Effekt ist 0 und wirkt nicht.
     _S("Zeitschleife", "Time Loop", "Every 5 kills charge a Time Loop. Your next grenade is thrown a second time, half a second later, at no cost. The counter next to your XP bar shows your progress.", 1, "HS",
        (Effekt(A_SCHADEN, 0.0, ""),))],
    [_S("Unendlich", "Infinite", "For the first 5 seconds after you throw the bomb, you have infinite ammo.", 1, "S"),
     _S("KeinZurueck", "Point of No Return", "If the bomb expires unused: +25% [skill]Weapon Damage[-skill] for 10 seconds, and no cooldown at all.", 1, "HS",
        (Effekt(A_SCHADEN, 0.25, "Weapon Damage: $NUMBER$"),), dauer=10.0)],
    [_S("Zeitsprung", "Unspent Time", "Every enemy you kill releases the time it had left in a burst of energy, damaging nearby enemies in your weapon's element. Kills from the burst release theirs too.", 1, "S")],
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
    "Zeitsprung": "",                                        # v1.73 Unspent Time (ersetzt Time Skip)
    "Reinigung": "",                                         # v1.12 Immunitaet ueber ZB_Immun_A/B
    "Nachhall": "",                                          # v1.13 Schockwelle statt Rueckstoss
    "Zeitspur": "",                                          # v1.05 Zeitwirbel statt Verlangsamung (Spike A)
    "EsWarNiePassiert": "",                                  # v0.90, gemessen
    "KursHalten": "",                                        # v0.90, gemessen
    "Nachbild": "",                                          # v0.93, bestaetigt (Screenshot, 7 s), Leiche wird versteckt
    "Sprengsatz": "",                                        # v0.94 neu: Behavior_Explode beim Zuenden, ungetestet
    "Zeitkapsel": "",                                        # v0.95 Heilung gebaut, nur mit 'zb koop selbst' pruefbar
    "Schattenanker": "",                                     # v0.95, Ringpuffer + Halten ueber InputKey, ungetestet
    "Nachfuellen": "",                                       # v1.57 Refill, gemessen
    "Unendlich": "",                                         # v1.58 Infinite, im Spiel bestaetigt
    "GeliehenesLeben": "",                                   # v1.59 Borrowed Health, im Spiel bestaetigt
    "Zuruecksenden": "",                                     # v1.60 Return to Sender, im Spiel bestaetigt
}


# v1.37: Icons je Baum-Skill (Nutzerwahl 2026-09-27, Platzhalter bis eigene Icons gehen). Klasse ->
# ICON_KLASSEN (Paket + Gruppe), Bilder: docs/icon-katalog.md. Der Skillbaum liest SkillIcon live (v1.36).
SKILL_ICONS: dict[str, tuple[str, str]] = {
    # HINDSIGHT
    "Gedaechtnis": ("gaige", "SkillIcon-Mechro05"),            # Gehirn
    "Nachwirkung": ("axton", "SkillIcon-Impact"),              # gesplittertes Glas
    "GespannteZeit": ("salvador", "SkillIcon-ImReadyAlready"),  # Wecker
    "Eile": ("maya", "SkillIcon-ThoughtLock"),                 # v1.56 Platzhalter (von Deja Vu)
    "Zeitstillstand": ("zer0", "SkillIcon-KillConfirmed"),     # v1.56 Platzhalter (von Prior Record)
    "Zuruecksenden": ("maya", "SkillIcon-Recompense"),         # v1.56 Platzhalter (von Encore)
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
    "GeliehenesLeben": ("salvador", "SkillIcon-SteadyAsSheGoes"),  # v1.56 Platzhalter (von Stabilizer)
    "Reinigung": ("axton", "SkillIcon-Forbearance"),           # Feuerloescher
    "SichereKrits": ("gaige", "SkillIcon-Mechro25"),           # v1.56 Platzhalter (von Second Opinion)
    "Zeitkapsel": ("maya", "SkillIcon-Sphere"),                # Blasen
    "EsWarNiePassiert": ("maya", "SkillIcon-Res"),             # Feder
    "Nachbild": ("zer0", "SkillIcon-Unforseen"),               # Hologramm-Explosion
    "Sprengsatz": ("krieg", "SkillIcon-Psycho18"),             # Dynamit mit Uhr
    "Endspurt": ("maya", "SkillIcon-Restoration"),             # v1.56 Platzhalter (von Homecoming)
    "Schattenanker": ("zer0", "SkillIcon-LikeTheWind"),        # Pixel-Wirbelsturm
    # OVERCLOCK (bis v1.55 DETOUR)
    "Weite": ("salvador", "SkillIcon-Incite"),                 # Stiefel mit Fluegel
    "Nachfuellen": ("zer0", "SkillIcon-Squint"),               # v1.56 Platzhalter (von Distance)
    "Dimensionsschleife": ("axton", "SkillIcon-Steady"),       # v1.56 Platzhalter (von Push Forward)
    "GranatenRueckruf": ("axton", "SkillIcon-Preparation"),    # v1.56 Platzhalter (von Safe Distance)
    "Ausbruch": ("maya", "SkillIcon-Fleet"),                   # Hase
    "Hinterhalt": ("zer0", "SkillIcon-Backstab"),              # Ninja mit Dolch
    "Echokugel": ("maya", "SkillIcon-Accelerate"),             # v1.56 Platzhalter (von Long Shot)
    "KursHalten": ("salvador", "SkillIcon-Yippekiyay"),        # Cowboy-Totenkopf
    "Zeitschleife": ("zer0", "Skillicon-velocity"),            # v1.56 Platzhalter (von Tailwind)
    "Unendlich": ("axton", "SkillIcon-Ranger"),                # v1.56 Platzhalter (von Borderlander)
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
    Encore (bis v1.55; Vorlage Killer: 2 Effekte, gebraucht 1)."""
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


ANZEIGE_TRAEGER = (A_SCHADEN, A_KRIT, A_MAGAZIN, A_TEMPO)   # je Zeile ein anderes, damit die Zuordnung eindeutig ist
ANZEIGE_VORBILD = "GD_Assassin_Skills.ActionSkill.Skill_Deception"
# Dump: SkillEffectDefinitions(6) = InstigatedMeleeDamageModifier, MT_Scale, EffectTarget=TARGET_None;
#       SkillEffectDefinitions(10) = AttributeToModify None, MT_PostAdd (Cooldown-Zeile).
ANZEIGE_VORBILD_SCALE, ANZEIGE_VORBILD_ADD = 6, 10


def _anzeige_setzen(obj: UObject, zeilen: tuple, outer: str, name: str) -> None:
    """Anzeige-Effekte (TARGET_None) und Praesentationen an den Baum-Skill. SICHERHEIT: ohne belegtes
    TARGET_None waere ein Anzeige-Effekt ein echter Dauer-Buff - dann lieber gar keine Zeile."""
    vorbild = _find("SkillDefinition", ANZEIGE_VORBILD)
    try:
        v_scale = vorbild.SkillEffectDefinitions[ANZEIGE_VORBILD_SCALE]
        v_add = vorbild.SkillEffectDefinitions[ANZEIGE_VORBILD_ADD]
        ziel_none, mt_scale, mt_add = v_scale.EffectTarget, v_scale.ModifierType, v_add.ModifierType
        ok = (v_scale.AttributeToModify is not None
              and v_scale.AttributeToModify.Name == "InstigatedMeleeDamageModifier"
              and ziel_none != obj.SkillEffectDefinitions[0].EffectTarget)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] {name}: Anzeige - Vorbild {ANZEIGE_VORBILD} nicht lesbar ({ex}), keine orangen Zeilen")
        return
    if not ok:
        logging.error(f"[ZB] {name}: Anzeige - TARGET_None nicht belegt (Vorbild {ziel_none}, Vorlage "
                      f"{obj.SkillEffectDefinitions[0].EffectTarget}), keine orangen Zeilen")
        return
    liste = obj.SkillEffectDefinitions
    praes = []
    for i, z in enumerate(zeilen[:min(len(liste), len(ANZEIGE_TRAEGER))]):
        attr = _attr(ANZEIGE_TRAEGER[i])
        if attr is None:
            continue
        try:
            sed = liste[i]
            sed.EffectTarget = ziel_none   # ZUERST - erst danach bekommt der Effekt ein Attribut
            sed.ModifierType = mt_scale if z.prozent else mt_add
            sed.AttributeToModify = attr
            sed.BaseModifierValue.BaseValueConstant = z.basis
            sed.BaseModifierValue.BaseValueAttribute = None
            sed.PerGradeUpgrade.BaseValueConstant = z.je_grad
            sed.PerGradeUpgrade.BaseValueAttribute = None
            sed.GradeToStartApplyingEffect = 1
            sed.PerGradeUpgradeInterval = 1
            p = _copy("AttributePresentationDefinition", PRAES_POSITIV, outer, f"{name}_A{i}")
            p.Attribute = attr
            p.Description = z.text
            p.bDisplayAsPercentage = z.prozent
            p.bDisplayPercentAsFloat = z.dezimal
            p.bDontDisplayPlusSign = not z.plus
            praes.append(p)
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] {name}: Anzeige-Zeile {i}: {ex}")
    try:
        obj.SkillEffectPresentations = praes
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] {name}: Anzeige-Praesentationen setzen: {ex}")
    if name == "Paradoxon":   # eine Stichprobe je Start, damit das Log TARGET_None belegt
        logging.info(f"[ZB] Anzeige {name}: {len(praes)} Zeile(n), EffectTarget {liste[0].EffectTarget} "
                     f"(Vorlage sonst {ziel_none} = TARGET_None aus {ANZEIGE_VORBILD})")


def _skill_bauen(sk: Skill, outer: str) -> UObject | None:
    """Einen Baum-Skill (und bei HS seinen Effekt-Skill) als Laufzeit-Kopie anlegen. Idempotent."""
    sichtbar = sk.effekte if sk.art in ("H", "KILL") else ()
    zeilen = ANZEIGE.get(sk.name, ()) if not sichtbar else ()   # v1.67: nur Anzeige, wirkt nicht
    text = sk.text
    if sk.art == "S" and sk.name in S_GEBAUT:
        if S_GEBAUT[sk.name]:
            text += f" [Not functional yet: {S_GEBAUT[sk.name]}.]"
    elif sk.art == "S":
        text += PLATZHALTER_HINWEIS
    elif sk.offen:
        text += f" [Not functional yet: {sk.offen}.]"
    try:
        obj = _copy("SkillDefinition", _vorlage(sk.art, max(len(sichtbar), len(zeilen)), 0.0), outer, sk.name)
        obj.SkillName = sk.titel
        obj.SkillDescription = text
        obj.MaxGrade = sk.rang
        icon = _skill_icon(sk.name)   # v1.37 - vor der HUD-Kopie unten (wirk.SkillIcon = obj.SkillIcon)
        if icon is not None:
            obj.SkillIcon = icon
        _effekte_setzen(obj, sichtbar, outer, sk.name, mit_praesentation=True)
        if zeilen:
            _anzeige_setzen(obj, zeilen, outer, sk.name)
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
    wirkung_an("Langzeitgedaechtnis")  # Kritschaden, bis zum Zuenden/Verpuffen
    ticker_start()
    kills_start()
    mechanik_erinnerung_gelegt()       # merkt sich die Haste Stacks
    pc = local_pc()
    if pc is not None:
        mechanik_ammo_gelegt(pc)       # Volle Rueckerstattung: Reserve merken
    mechanik_unendlich_gelegt()        # v1.58: Infinite, 5 s volles Magazin
    mechanik_paket_b_gelegt()          # Paradoxon, Zeitspur: Raenge lesen, Buch leeren
    mechanik_ruecksenden_gelegt()      # v1.60: Return to Sender, Buch leeren
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
    wirkung_aus("Langzeitgedaechtnis")
    wirkung_an("Nachwirkung")          # 8 s
    mechanik_kills_gezuendet()         # Wiederkehr, 10 s
    mechanik_erinnerung_gezuendet()    # Haste Stacks vom Legen wiederherstellen
    # Handgriff 4, Paket A. Reihenfolge mit Absicht: erst was am Spieler haengt, dann die Wirkung
    # nach aussen - so steht im Log erst der eigene Zustand, dann die Trefferliste.
    pc = local_pc()
    if pc is not None:
        mechanik_rueckerstattung(pc, pawn)
    mechanik_reinigung(pawn)
    mechanik_nachhall(pawn)
    try:
        mechanik_sichere_krits()   # v1.72 Guaranteed Crits
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Guaranteed Crits: {ex}")
    try:
        mechanik_endspurt_bombe(pawn)   # v1.69 Crunch Time
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Crunch Time: Bombe: {ex}")
    mechanik_paradoxon()               # Paket B
    try:
        mechanik_ruecksenden_gezuendet()   # v1.60: Return to Sender
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Return to Sender: {ex}")
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
    try:
        mechanik_geliehen_gezuendet(pawn)   # v1.59: Borrowed Health, nach Auffrischung
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Borrowed Health: {ex}")


def mechanik_verpufft() -> bool:
    """Gibt True zurueck, wenn 'Kein Zurueck' greift - dann entfaellt der Cooldown ganz."""
    pc = local_pc()
    if pc is not None:
        # Messgroesse fuer Kurs halten (v0.90): wie lange lag die Bombe wirklich?
        logging.info(f"[ZB] Fenster tatsaechlich: {_game_time(pc) - _legen_time:.1f} s seit dem Legen, {_kills} Kill(s)")
    ticker_stop()
    mechanik_paket_b_verpufft()
    holo_entfernen("Zeitkapsel", "verpufft")
    wirkung_aus("Langzeitgedaechtnis")
    return wirkung_an("KeinZurueck")   # 10 s


# --- Handgriff 2: der Ticker (v0.59) --------------------------------------------------------------
#
# Gespannte Zeit braucht etwas, das waehrend der liegenden Bombe jede Sekunde laeuft (ein Stack je
# Sekunde), Zeitspur und Zeitkapsel ebenso. Muster aus dem FL4K-Projekt (fl4k_pet on_tick, bewiesen): POST-Hook auf
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

_tick_akku = 0.0
_tick_sekunden = 0        # Sekunden seit dem Legen (nur Anzeige)
_gespannt_stacks = 0


def ticker_start() -> None:
    global _tick_akku, _tick_sekunden, _gespannt_stacks
    _tick_akku = 0.0
    _tick_sekunden = 0
    _gespannt_stacks = 0


def ticker_stop() -> None:
    """Alles abraeumen, was der Ticker eingeschaltet hat. Die Zaehler setzt ticker_start zurueck."""
    if _gespannt_stacks > 0:
        stapel_setzen("GespannteZeit", 0)   # v1.18: Instanzen statt Grad
    ticker_start()


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
    global _tick_sekunden, _gespannt_stacks
    _tick_sekunden += 1
    pawn = pc.Pawn
    if pawn is None:
        return

    # Gespannte Zeit: ein Stack je Sekunde, Grad = Rang x Stacks
    rang_gz = skill_rang("GespannteZeit")
    if rang_gz > 0 and _gespannt_stacks < GESPANNT_STACKS_MAX:
        _gespannt_stacks += 1
        stapel_setzen("GespannteZeit", _gespannt_stacks)   # v1.18: ein Stack = eine Instanz (HUD)

    uu = anker_abstand(pawn)
    logging.info(
        f"[ZB] Ticker {_tick_sekunden}s | Anker {(uu or 0.0) / UU_JE_METER:.1f} m"
        f" | Gespannte Zeit {_gespannt_stacks}/{GESPANNT_STACKS_MAX}"
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
        try:
            mechanik_nachfuellen(pc)   # v1.57: Refill, jeder Kill
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Refill: {ex}")
        try:
            mechanik_geliehen_kill()   # v1.59: Borrowed Health, Kill tilgt Schuld
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Borrowed Health Kill: {ex}")
        try:
            mechanik_zeitschleife_kill()   # v1.65: Time Loop laden
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Time Loop Kill: {ex}")
    if _state != ZUSTAND_GELEGT or not ist_chronomaster(pc):
        return
    _kills += 1
    logging.info(f"[ZB] Kill {_kills} mit liegender Bombe: {name}")
    mechanik_kurs_halten()  # v0.90


# --- Kill-Stacks (v1.13, Nutzerwunsch 2026-09-26) -------------------------------------------------
#
# Seit v1.61 traegt nur Haste Stacks (Eile) diesen Zaehler (bis v1.55: Deja-vu, Encore, Push Forward).
# Jeder Kill +1, dazu Feuer-Stacks aus Dauerfeuer. Verfall (Nutzerentscheidung "einzeln abbauen"):
# 3 s nach dem letzten Stack faellt jede Sekunde einer. Wirkung = Instanzen des Effekt-Skills
# Eile_Wirkung (stapel_setzen). Erinnerung stellt beim Zuenden den Stapel vom Legen wieder her.

KILL_STACK_FRIST_S = 3.0
KILL_STACK_TAKT_S = 1.0

_kill_stacks = 0
_kill_frist = 0.0
_kill_takt = 0.0

# v1.61 Haste Stacks (docs/skills.md 9.2): hoechstens 20 Stacks, davon hoechstens 10 aus Dauerfeuer
# (Grund: Waffen wie die Infinity). Dauerfeuer = Schuesse mit hoechstens FEUER_PAUSE_MAX_S Abstand;
# je FEUER_STACK_S am Stueck ein Stack. Erkannt am Feuer-Hook, NICHT am Magazin (Nutzer: Infinity).
# Abbau: erst die Feuer-Stacks, dann die Kill-Stacks. Jeder neue Stack startet die Frist neu.
EILE_MAX = 20
EILE_FEUER_MAX = 10
FEUER_STACK_S = 2.0
FEUER_PAUSE_MAX_S = 1.0
FIRE_FUNC = "WillowGame.WillowWeapon:FireAmmunition"   # Dump: Function WillowGame.WillowWeapon:FireAmmunition; BO2 Test 53
_feuer_stacks = 0
_feuer_seit_schuss = 99.0   # Sekunden seit dem letzten eigenen Schuss
_feuer_am_stueck = 0.0      # Sekunden ununterbrochenes Feuer
_feuer_spur_gemeldet = False
_rang_eile_cache = 0
_rang_eile_uhr = 0.0


_ks_rang_gesetzt: dict[str, int] = {}   # v1.14: fuer welchen Rang die Effektwerte zuletzt gesetzt wurden


def _ks_werte_setzen(name: str, wirk: UObject, rang: int) -> None:
    """Jede Instanz (= ein Stack, Grad 1) traegt Wert x Rang. Elementweise geschrieben (Spike D).
    Nur bei Rangwechsel; danach werden die Instanzen neu aufgebaut."""
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


# v1.17: EIN STACK = EINE INSTANZ. Probe v1.16 im Spiel (Werkzeug inzwischen ausgebaut): jede ActivateSkill legt eine
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
    """Die Instanzen der Kill-Stack-Skills auf Kill- + Feuer-Stacks bringen. Still."""
    for name in KILL_SKILLS:
        stapel_setzen(name, _kill_stacks + _feuer_stacks)


def kill_stack_plus(name: str = "") -> None:
    global _kill_stacks, _kill_frist, _kill_takt
    if not any(skill_rang(n) > 0 for n in KILL_SKILLS):
        return
    if _kill_stacks + _feuer_stacks < EILE_MAX:
        _kill_stacks += 1
    _kill_frist, _kill_takt = KILL_STACK_FRIST_S, 0.0
    _kill_stacks_anwenden("Kill")
    logging.info(f"[ZB] Kill-Stacks: {_kill_stacks} + Feuer {_feuer_stacks} ({name}) - {_eile_werte()}")


def _eile_werte() -> str:
    """Messgroessen fuer Haste Stacks: Feuerintervall und Nachladezeit der Waffe in der Hand (Ist /
    Basis; negative Scale-Summen teilen, CLAUDE.md) und die Schildaufladung am Pawn."""
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        return "kein Pawn"
    teile = []
    w = pawn.Weapon
    if w is not None:
        try:
            teile.append(f"Intervall {float(w.FireInterval):.4f}/{float(w.FireIntervalBaseValue):.4f}")
        except Exception:  # noqa: BLE001
            pass
        try:
            teile.append(f"Nachladen {float(w.ReloadTime):.3f}/{float(w.ReloadTimeBaseValue):.3f}")
        except Exception:  # noqa: BLE001
            pass
    teile.append(f"Schildladen {attr_value('ResourcePoolAttributeDefinition', A_SCHILDLADEN, pawn)}")
    return ", ".join(teile)


def _on_fire_ammunition(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """PRE auf WillowWeapon:FireAmmunition - jeder Schuss jeder Waffe. Nur die Waffe in der eigenen
    Hand zaehlt; der Hook merkt sich nur den Zeitpunkt, gerechnet wird im Tick."""
    global _feuer_seit_schuss, _feuer_spur_gemeldet
    if _rang_eile_cache <= 0:
        return
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    w = pawn.Weapon if pawn is not None else None
    if w is None:
        return
    try:
        if obj._path_name() != w._path_name():
            return
    except Exception:  # noqa: BLE001
        return
    _feuer_seit_schuss = 0.0
    if not _feuer_spur_gemeldet:
        _feuer_spur_gemeldet = True
        logging.info(f"[ZB] Haste Stacks: Feuer-Hook feuert ({obj.Name})")


# v1.63: Echo Bullet (Overclock T3, docs/skills.md 9.2). Jeder N-te Schuss der Waffe in der Hand feuert
# doppelt (N je Rang: ECHO_JEDER).
# v1.63 erster Weg, IM SPIEL OHNE WIRKUNG: WillowWeapon.ProjectilesPerShot im PRE verdoppelt (1 -> 2, im POST
# zurueck). Das Feld stand nachweislich auf 2, der Schuss blieb einfach (Nutzer, Log 11:23). Das Spiel liest
# die Projektilzahl beim Schuss also nicht aus diesem Feld.
# v1.63b: Im POST ruft das Modul FireAmmunition der eigenen Waffe ein zweites Mal (Sperre gegen Rekursion)
# und erstattet die verbrauchte Munition (Pool und ReloadCnt gemeinsam, Rezept Refill). Messung: Gegner-
# Treffer (WillowAIPawn:TakeDamage) im Fenster ECHO_MESS_S nach dem Echo- und nach dem Schuss davor.
# HUD: Zaehler = Instanzen des Effekt-Skills Echokugel_Wirkung (stapel_setzen), Platz 2.
ECHO_JEDER = (10, 9, 8, 6, 5)   # Rang 1..5: jeder N-te Schuss
ECHO_MESS_S = 0.25
_rang_echo_cache = 0
_echo_zaehler = 0
_echo_jetzt = False        # dieser Schuss wird gedoppelt (PRE -> POST)
_echo_im_zweiten = False   # Rekursionssperre waehrend des zweiten Aufrufs
_echo_mess: list = []      # [Art, Restzeit, Treffer] des laufenden Messfensters
_echo_vorher_treffer = -1  # Treffer des letzten normalen Schusses (Gegenfall)
_echo_grund = ""           # wer den Zusatzschuss ausloest (Echo Bullet / Dimensional Loop)

# v1.64: Dimensional Loop (Overclock T2). Nach jedem Nachladen feuern die naechsten <Rang> Schuesse doppelt -
# ueber denselben Zusatzschuss wie Echo Bullet. Nachladen: PRE auf WillowWeapon:PlayReloadAnim (Dump; im
# BO2-Projekt bewiesen) merkt sich Waffe und Magazin. Erst wenn das Magazin beim naechsten eigenen Schuss
# VOLLER ist, war das Nachladen fertig (abgebrochenes Nachladen = gleiches Magazin = nichts).
RELOAD_FUNC = "WillowGame.WillowWeapon:PlayReloadAnim"
_rang_loop_cache = 0
_loop_rest = 0
_nachladen: tuple | None = None   # (Pfad der Waffe, Magazin beim Start des Nachladens)
_nachladen_gemeldet = False


def _on_reload_anim(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _nachladen, _nachladen_gemeldet
    if _rang_loop_cache <= 0:
        return
    w = _echo_waffe(obj)
    if w is None:
        return
    try:
        _nachladen = (w._path_name(), int(w.ReloadCnt))
    except Exception:  # noqa: BLE001
        return
    if not _nachladen_gemeldet:
        _nachladen_gemeldet = True
        logging.info(f"[ZB] Dimensional Loop: Nachlade-Hook feuert ({obj.Name}, Magazin {_nachladen[1]})")


def _echo_treffer_zaehlen() -> None:
    """Aus dem Gegner-Schadens-Hook: nur ein Zaehler, kein Engine-Zugriff."""
    if _echo_mess:
        _echo_mess[2] += 1


def _echo_mess_tick(dt: float) -> None:
    global _echo_vorher_treffer
    if not _echo_mess:
        return
    _echo_mess[1] -= dt
    if _echo_mess[1] > 0:
        return
    art, _, n = _echo_mess
    _echo_mess.clear()
    if art == "echo":
        logging.info(f"[ZB] Zusatzschuss: Treffer im Fenster {ECHO_MESS_S:.2f} s - Doppelschuss {n}, normaler Schuss davor {_echo_vorher_treffer}")
    else:
        _echo_vorher_treffer = n


def _echo_waffe(obj: UObject) -> UObject | None:
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    w = pawn.Weapon if pawn is not None else None
    if w is None:
        return None
    try:
        return w if obj._path_name() == w._path_name() else None
    except Exception:  # noqa: BLE001
        return None


def _on_echo_pre(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _echo_zaehler, _echo_jetzt, _echo_grund, _nachladen, _loop_rest
    if (_rang_echo_cache <= 0 and _rang_loop_cache <= 0) or _echo_im_zweiten:
        return
    w = _echo_waffe(obj)
    if w is None:
        return
    grund = []
    if _rang_loop_cache > 0:
        if _nachladen is not None:
            pfad, mag_start = _nachladen
            _nachladen = None
            try:
                mag = int(w.ReloadCnt)
                if pfad == w._path_name() and mag > mag_start:
                    _loop_rest = _rang_loop_cache
                    logging.info(f"[ZB] Dimensional Loop: nachgeladen ({mag_start} -> {mag}), {_loop_rest} Doppelschuesse")
            except Exception:  # noqa: BLE001
                pass
        if _loop_rest > 0:
            _loop_rest -= 1
            grund.append("Dimensional Loop")
            stapel_setzen("Dimensionsschleife", _loop_rest)   # HUD: verbleibende Doppelschuesse
    if _rang_echo_cache > 0:
        _echo_zaehler += 1
        jeder = ECHO_JEDER[min(_rang_echo_cache, len(ECHO_JEDER)) - 1]
        if _echo_zaehler >= jeder:
            _echo_zaehler = 0
            grund.append("Echo Bullet")
        stapel_setzen("Echokugel", _echo_zaehler)   # HUD: 1..N-1, beim Echo 0
    if grund:
        _echo_jetzt = True
        _echo_grund = " + ".join(grund)


def _on_echo_post(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _echo_jetzt, _echo_im_zweiten
    if _echo_im_zweiten or (_rang_echo_cache <= 0 and _rang_loop_cache <= 0):
        return
    w = _echo_waffe(obj)
    if w is None:
        return
    if not _echo_jetzt:
        _echo_mess[:] = ["normal", ECHO_MESS_S, 0]
        return
    _echo_jetzt = False
    try:
        mag, kosten = int(w.ReloadCnt), max(1, int(w.ShotCost))
        pool = w.AmmoPool.Data
        if mag < kosten and pool is not None:
            # Magazin leer geschossen: die Patrone fuer das Echo leihen (wird unten verrechnet)
            pool.CurrentValue = float(pool.CurrentValue) + kosten
            w.ReloadCnt = mag + kosten
        vor_mag = int(w.ReloadCnt)
        vor_pool = float(pool.CurrentValue) if pool is not None else -1.0
        _echo_im_zweiten = True
        try:
            w.FireAmmunition()
        finally:
            _echo_im_zweiten = False
        verbraucht = vor_mag - int(w.ReloadCnt)
        if verbraucht > 0:
            w.ReloadCnt = int(w.ReloadCnt) + verbraucht
            if pool is not None:
                pool.CurrentValue = float(pool.CurrentValue) + verbraucht
        if mag < kosten and pool is not None:
            pool.CurrentValue = float(pool.CurrentValue) - kosten
            w.ReloadCnt = int(w.ReloadCnt) - kosten
        _echo_mess[:] = ["echo", ECHO_MESS_S, 0]
        logging.info(f"[ZB] {_echo_grund}: zweiter Schuss ausgeloest - verbraucht {verbraucht}, erstattet;"
                     f" Magazin {mag} -> {int(w.ReloadCnt)}, Pool {vor_pool:.0f} -> {float(pool.CurrentValue) if pool is not None else -1:.0f}")
    except Exception as ex:  # noqa: BLE001
        _echo_im_zweiten = False
        logging.error(f"[ZB] Echo Bullet: zweiter Schuss: {ex}")


# v1.65: Time Loop (Overclock T4, docs/skills.md 9.2). Alle 5 Kills laedt er sich auf; die naechste Granate
# wird 0,5 s spaeter ein zweites Mal geworfen. SPIKE in zwei Teilen:
#  1. Wurf erkennen: welche Funktion beim Wurf feuert, steht nicht im Dump. Vier Kandidaten (Dump, alle
#     WillowGame): WillowPlayerController ThrowGrenade / ServerThrowGrenade / GrenadeThrowComplete und
#     WillowGrenadeMod:OnGrenadeSpawned. Jeder loggt beim ersten Feuern; der erste je Wurf (Sperre 0,3 s) zaehlt.
#  2. Zweiter Wurf: pc.ThrowGrenade() - dieselbe Idee wie der Zusatzschuss (v1.63b). Vorher +1 Granate in den
#     Pool (der zweite Wurf kostet nichts, und auch mit der letzten Granate geht er); hat der Wurf nichts
#     verbraucht, wird sie wieder abgezogen. Ob ein Wurf entstand, zeigt der Pool.
# HUD: Zeitschleife_Wirkung-Instanzen = Kills bis zur Ladung (5 = geladen).
ZEITSCHLEIFE_KILLS = 5
# v1.65 gemessen (Log 11:40): ThrowGrenade feuert sofort beim Wurf, GrenadeThrowComplete ~1 s spaeter
# (zaehlte so als zweiter Wurf); ServerThrowGrenade und OnGrenadeSpawned meldeten sich nicht. v1.65b: nur noch
# ThrowGrenade.
WURF_FUNCS = ("WillowGame.WillowPlayerController:ThrowGrenade",)
# v1.65d: pc.ThrowGrenade(def) 0,5 s nach dem Wurf lief fehlerfrei und tat NICHTS (Log 11:47: Vorrat sank nur
# um die erste Granate). Vermutung: der eigene Wurf laeuft noch (GrenadeThrowComplete kommt erst ~1 s spaeter),
# und das Spiel verwirft einen neuen. Darum startet der zweite Wurf erst NACH GrenadeThrowComplete.
WURF_FERTIG_FUNC = "WillowGame.WillowPlayerController:GrenadeThrowComplete"
_zs_warten = False   # geladen geworfen, zweiter Wurf wartet auf GrenadeThrowComplete


def _on_wurf_fertig(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _zs_warten, _zs_geplant
    if not _zs_warten or _zs_im_zweiten:
        return
    _zs_warten = False
    _zs_geplant = 0.05   # naechster Tick
    logging.info("[ZB] Time Loop: GrenadeThrowComplete - zweiter Wurf jetzt")
_zs_kills = 0
_zs_geplant = -1.0       # Sekunden bis zum zweiten Wurf (-1 = nichts geplant)
_zs_sperre = 0.0         # nach einem erkannten Wurf: weitere Hooks desselben Wurfs ignorieren
_zs_im_zweiten = False
_zs_gemeldet: set[str] = set()
_zs_probe: tuple | None = None   # (Pool-Name, Soll-Stand, Restzeit) - Abrechnung nach dem zweiten Wurf
# v1.65c: ThrowGrenade verlangt ProjectileDefinition (gemessen: "missing 1 required positional argument") -
# sie kommt aus den Argumenten des ECHTEN Wurfs. Und die Granate wird erst ~1 s NACH ThrowGrenade abgezogen
# (gemessen: die Leihgabe von v1.65b bezahlte den ersten Wurf). Darum Abrechnung am Ende: Vorrat beim echten
# Wurf merken, 1,5 s nach dem zweiten Wurf auf genau eins weniger setzen.
_zs_def = None
_zs_vorrat = -1.0


def _granaten_pool() -> tuple[str, UObject] | tuple[None, None]:
    """v1.65b: _ammo_pools (AmmoResourcePool) fand ihn nicht - im Spiel gemessen, "kein Granaten-Pool".
    Die Ressource heisst laut Dump D_Resources.AmmoResources.Ammo_Grenade_Protean. Darum alle ResourcePools der
    Welt, und verglichen werden der Name der Pool-Definition UND der Ressource. Findet sich nichts, kommen
    alle Namen ins Log."""
    gesehen = []
    for pool in unrealsdk.find_all("ResourcePool", exact=False):
        try:
            pfad = pool._path_name()
            if "Default__" in pfad or pool.Definition is None:
                continue
            namen = [str(pool.Definition.Name)]
            res = getattr(pool.Definition, "Resource", None)
            if res is not None:
                namen.append(str(res.Name))
            gesehen.append(f"{pool.Class.Name}:{'/'.join(namen)}")
            if any("grenade" in n.lower() for n in namen):
                return "/".join(namen), pool
        except Exception:  # noqa: BLE001
            continue
    logging.info(f"[ZB] Time Loop: Pools gesehen ({len(gesehen)}): {', '.join(gesehen)}")
    return None, None


def mechanik_zeitschleife_kill() -> None:
    global _zs_kills
    if skill_rang("Zeitschleife") <= 0 or _zs_kills >= ZEITSCHLEIFE_KILLS:
        return
    _zs_kills += 1
    stapel_setzen("Zeitschleife", _zs_kills)
    if _zs_kills >= ZEITSCHLEIFE_KILLS:
        logging.info("[ZB] Time Loop: geladen - die naechste Granate kommt doppelt")


def _make_wurf_hook(fname: str):
    kurz = fname.rsplit(".", 1)[-1]

    def hook(obj: UObject, args: Any, ret: Any, func: Any) -> None:
        global _zs_sperre, _zs_geplant, _zs_warten
        if _zs_im_zweiten:
            return
        if kurz not in _zs_gemeldet:
            _zs_gemeldet.add(kurz)
            logging.info(f"[ZB] Time Loop: Wurf-Hook feuert - {kurz} ({obj.Name})")
        global _zs_def, _zs_vorrat
        if _zs_sperre > 0:
            return
        _zs_sperre = 0.3
        _rueckruf_wurf()   # v1.68 Grenade Recall
        if skill_rang("Zeitschleife") <= 0:
            return
        logging.info(f"[ZB] Time Loop: Wurf erkannt ueber {kurz}, Kills {_zs_kills}/{ZEITSCHLEIFE_KILLS}")
        if _zs_kills >= ZEITSCHLEIFE_KILLS and _zs_geplant < 0 and not _zs_warten:
            try:
                _zs_def = args.ProjectileDefinition
            except Exception as ex:  # noqa: BLE001
                _zs_def = None
                logging.error(f"[ZB] Time Loop: ProjectileDefinition aus dem Wurf: {ex}")
            _, pool = _granaten_pool()
            _zs_vorrat = float(pool.CurrentValue) if pool is not None else -1.0
            logging.info(f"[ZB] Time Loop: Definition {_zs_def.Name if _zs_def is not None else None}, Vorrat beim Wurf {_zs_vorrat:.0f}")
            _zs_warten = True   # v1.65d: der zweite Wurf startet bei GrenadeThrowComplete
    return hook


# v1.68: Grenade Recall (Overclock T2, docs/skills.md 9.2). Jeder echte Wurf (nicht der zweite von Time Loop)
# kommt mit 6 % je Rang zurueck. Das Spiel zieht die Granate erst ~1 s nach ThrowGrenade ab (v1.65c), und die
# Abrechnung von Time Loop setzt den Vorrat ~1,9 s nach dem Wurf absolut. Darum die Rueckgabe erst nach 2,5 s:
# +1, aber hoechstens bis zum Vorrat beim Wurf (kein Ueberlaufen ueber das Maximum).
RUECKRUF_JE_RANG = 0.06
RUECKRUF_NACH_S = 2.5
_rueckruf_offen: list[list[float]] = []   # je zurueckkehrende Granate [Restzeit, Vorrat beim Wurf]


def _rueckruf_wurf() -> None:
    rang = skill_rang("GranatenRueckruf")
    if rang <= 0:
        return
    chance = RUECKRUF_JE_RANG * rang
    wurf = random.random()
    if wurf >= chance:
        logging.info(f"[ZB] Grenade Recall: kein Rueckruf ({wurf:.2f} >= {chance:.2f})")
        return
    _, pool = _granaten_pool()
    if pool is None:
        logging.error("[ZB] Grenade Recall: kein Granaten-Pool gefunden")
        return
    vorrat = float(pool.CurrentValue)
    _rueckruf_offen.append([RUECKRUF_NACH_S, vorrat])
    logging.info(f"[ZB] Grenade Recall: Rueckruf! ({wurf:.2f} < {chance:.2f}), Vorrat beim Wurf {vorrat:.0f}")


def _rueckruf_tick(dt: float) -> None:
    if not _rueckruf_offen:
        return
    for eintrag in _rueckruf_offen:
        eintrag[0] -= dt
    faellig = [e for e in _rueckruf_offen if e[0] <= 0]
    if not faellig:
        return
    _rueckruf_offen[:] = [e for e in _rueckruf_offen if e[0] > 0]
    _, pool = _granaten_pool()
    if pool is None:
        logging.error("[ZB] Grenade Recall: kein Granaten-Pool bei der Rueckgabe")
        return
    for _, vorrat in faellig:
        jetzt = float(pool.CurrentValue)
        neu = min(jetzt + 1.0, max(jetzt, vorrat))
        pool.CurrentValue = neu
        logging.info(f"[ZB] Grenade Recall: Granate zurueck - Vorrat {jetzt:.0f} -> {neu:.0f} (beim Wurf {vorrat:.0f})")


def _zeitschleife_tick(pc: UObject, dt: float) -> None:
    global _zs_sperre, _zs_geplant, _zs_im_zweiten, _zs_kills, _zs_probe
    _rueckruf_tick(dt)
    if _zs_sperre > 0:
        _zs_sperre -= dt
    if _zs_probe is not None:
        name, soll, rest = _zs_probe
        rest -= dt
        if rest > 0:
            _zs_probe = (name, soll, rest)
        else:
            _zs_probe = None
            _, pool = _granaten_pool()
            if pool is not None:
                jetzt = float(pool.CurrentValue)
                pool.CurrentValue = soll
                logging.info(f"[ZB] Time Loop: Abrechnung {name}: vor der Abrechnung {jetzt:.0f}, gesetzt auf {soll:.0f}"
                             f" (Vorrat beim Wurf {soll + 1:.0f}, beide Wuerfe zusammen kosten 1)")
    if _zs_geplant < 0:
        return
    _zs_geplant -= dt
    if _zs_geplant > 0:
        return
    _zs_geplant = -1.0
    _zs_kills = 0
    stapel_setzen("Zeitschleife", 0)
    name, pool = _granaten_pool()
    if pool is None:
        logging.error("[ZB] Time Loop: kein Granaten-Pool gefunden")
        return
    if _zs_def is None:
        logging.error("[ZB] Time Loop: keine ProjectileDefinition vom Wurf - kein zweiter Wurf")
        return
    vorher = float(pool.CurrentValue)
    if vorher < 1:
        pool.CurrentValue = 1.0   # die letzte Granate ist schon weg - fuer den Wurf leihen, die Abrechnung gleicht aus
    _zs_im_zweiten = True
    try:
        r = pc.ThrowGrenade(_zs_def)
        logging.info(f"[ZB] Time Loop: ThrowGrenade({_zs_def.Name}) -> {r}; {name} vor dem zweiten Wurf {vorher:.0f}")
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Time Loop: ThrowGrenade(): {ex}")
    finally:
        _zs_im_zweiten = False
    if _zs_vorrat >= 1:
        _zs_probe = (name, _zs_vorrat - 1, 1.5)


def _feuer_stack_tick(dt: float) -> None:
    """Dauerfeuer messen. Den Rang liest der Tick hoechstens einmal je Sekunde (der Hook laeuft je
    Schuss und soll nichts nachschlagen)."""
    global _feuer_seit_schuss, _feuer_am_stueck, _feuer_stacks, _kill_frist, _kill_takt
    global _rang_eile_cache, _rang_eile_uhr, _rang_echo_cache, _rang_loop_cache
    _echo_mess_tick(dt)
    pc_zs = local_pc()
    if pc_zs is not None:
        _zeitschleife_tick(pc_zs, dt)   # v1.65 Time Loop
    _rang_eile_uhr -= dt
    if _rang_eile_uhr <= 0:
        _rang_eile_uhr = 1.0
        _rang_eile_cache = skill_rang("Eile")
        _rang_echo_cache = skill_rang("Echokugel")   # v1.63, gleicher Takt
        _rang_loop_cache = skill_rang("Dimensionsschleife")   # v1.64
    if _rang_eile_cache <= 0:
        return
    _feuer_seit_schuss += dt
    if _feuer_seit_schuss > FEUER_PAUSE_MAX_S:
        _feuer_am_stueck = 0.0
        return
    _feuer_am_stueck += dt
    if _feuer_am_stueck < FEUER_STACK_S:
        return
    _feuer_am_stueck -= FEUER_STACK_S
    _kill_frist, _kill_takt = KILL_STACK_FRIST_S, 0.0   # Dauerfeuer haelt den Stapel
    if _feuer_stacks >= EILE_FEUER_MAX or _kill_stacks + _feuer_stacks >= EILE_MAX:
        return
    _feuer_stacks += 1
    _kill_stacks_anwenden("Dauerfeuer")
    logging.info(f"[ZB] Haste Stacks: Dauerfeuer +1 -> Kill {_kill_stacks} + Feuer {_feuer_stacks} - {_eile_werte()}")


def kill_stacks_festhalten(grund: str) -> None:
    """Erinnerung beim Zuenden: die Verfallsfrist beginnt von vorn."""
    global _kill_frist, _kill_takt
    if _kill_stacks > 0:
        _kill_frist, _kill_takt = KILL_STACK_FRIST_S, 0.0
        logging.info(f"[ZB] Kill-Stacks festgehalten ({grund}): {_kill_stacks}, Frist {KILL_STACK_FRIST_S:.0f} s")


def _kill_stack_tick(dt: float) -> None:
    global _kill_stacks, _kill_frist, _kill_takt, _feuer_stacks
    _feuer_stack_tick(dt)
    if _kill_stacks + _feuer_stacks <= 0:
        return
    if _kill_frist > 0:
        _kill_frist -= dt
        return
    _kill_takt += dt
    if _kill_takt < KILL_STACK_TAKT_S:
        return
    _kill_takt = 0.0
    if _feuer_stacks > 0:
        _feuer_stacks -= 1
    else:
        _kill_stacks -= 1
    _kill_stacks_anwenden("Verfall")
    if _kill_stacks + _feuer_stacks in (0, 10):
        logging.info(f"[ZB] Kill-Stacks verfallen: noch Kill {_kill_stacks} + Feuer {_feuer_stacks} - {_eile_werte()}")


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


# Kill Skills des Moduls sind Stack-Skills (stapel_setzen). Den harten Kill-Skill-Weg des Spiels
# (UpdateKillSkills, v0.70) und NotifySkillEvent (v0.69, wirkungslos) beschreibt docs/spikes.md, Spike E.

KILL_SKILLS = ("Eile",)  # v1.61: Haste Stacks; bis v1.55 DejaVu, Wiederholung, Vorstoss


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


# --- Time Freeze (Hindsight T6, Capstone) - Spike v1.70/v1.70b, Skill v1.71 ---------------------------
# Spike (Testbefehl `zb frieren ki|tick|pop|halten|aus [RADIUS_M]`, gemessen 2026-10-11):
#   bIsCriticalActor aus dem FL4K-Projekt sass an der Spawn-FACTORY, fuer lebende Gegner taugt es nicht.
#   ki   (WillowMind.bTickIsDisabled + WillowAIComponent.bTickInGame=False): greifen nicht mehr an, laufen
#        aber ihren Weg weiter (bis 24 m in 5 s).
#   tick (dazu WillowAIPawn.bTickIsDisabled): genauso, die Eigenschaft allein haelt nichts an.
#   pop  (WillowMind.bDisabledDueToPopulationIrrelevance): keine Wirkung.
#   halten = ki + jeden Frame Location zurueck, Velocity/Acceleration 0, Mesh.bPauseAnims: alle stehen wie
#        Statuen (0,00 m in 5 s, Gegenfall lief), nach `aus` kaempfen sie normal weiter.
# Nur Eigenschaften an fremden Objekten, keine Funktionsaufrufe (CLAUDE.md). Keine UObject-Huellen merken,
# nur Pfade.
ZEITSTILLSTAND_RADIUS_M = 25.0
_frieren: dict[str, dict] = {}            # Pawn-Pfad -> {"mind","komp","ort",alte Werte,"variante","skill"}
_frieren_messung: list[list] = []         # [Restzeit, Etikett] - nur fuer den Testbefehl
_frieren_gegenfall: tuple | None = None   # (Pfad, (x,y,z))
_auftau_offen: list[tuple[str, float]] = []   # (Pawn-Pfad, Bonus-Schaden) - im naechsten Tick austeilen


def _frieren_teile(p: UObject) -> tuple[UObject | None, UObject | None]:
    mind = getattr(p, "Controller", None)
    komp = getattr(mind, "AIComponent", None) if mind is not None else None
    return mind, komp


def _frieren_finden(cls: str, pfad: str | None) -> UObject | None:
    if not pfad:
        return None
    try:
        return unrealsdk.find_object(cls, pfad)
    except Exception:  # noqa: BLE001
        return None


def _frieren_einer(p: UObject, variante: str, skill: bool) -> dict:
    mind, komp = _frieren_teile(p)
    l = p.Location
    e = {"ort": (l.X, l.Y, l.Z), "mind": mind._path_name() if mind is not None else None,
         "komp": komp._path_name() if komp is not None else None, "variante": variante,
         "leben": _leben(p), "skill": skill}
    if variante in ("ki", "tick", "halten"):
        if mind is not None:
            e["mind_tick"] = bool(mind.bTickIsDisabled)
            mind.bTickIsDisabled = True
        if komp is not None:
            e["komp_tick"] = bool(komp.bTickInGame)
            komp.bTickInGame = False
    if variante == "tick":
        e["pawn_tick"] = bool(p.bTickIsDisabled)
        p.bTickIsDisabled = True
    if variante == "halten":
        mesh = getattr(p, "Mesh", None)
        if mesh is not None:
            e["anim"] = bool(mesh.bPauseAnims)
            mesh.bPauseAnims = True
    if variante == "pop" and mind is not None:
        e["pop"] = bool(mind.bDisabledDueToPopulationIrrelevance)
        mind.bDisabledDueToPopulationIrrelevance = True
    _frieren[p._path_name()] = e
    return e


def _auftauen(pfad: str) -> bool:
    e = _frieren.pop(pfad, None)
    if e is None:
        return False
    p = _frieren_finden("WillowAIPawn", pfad)
    mind = _frieren_finden("WillowMind", e["mind"]) or (getattr(p, "Controller", None) if p is not None else None)
    komp = _frieren_finden("WillowAIComponent", e["komp"])
    if "pawn_tick" in e and p is not None:
        p.bTickIsDisabled = e["pawn_tick"]
    if "mind_tick" in e and mind is not None:
        mind.bTickIsDisabled = e["mind_tick"]
    if "komp_tick" in e and komp is not None:
        komp.bTickInGame = e["komp_tick"]
    if "pop" in e and mind is not None:
        mind.bDisabledDueToPopulationIrrelevance = e["pop"]
    if "anim" in e and p is not None and getattr(p, "Mesh", None) is not None:
        p.Mesh.bPauseAnims = e["anim"]
    return True


def frieren(variante: str, radius_m: float) -> None:
    """zb frieren - der Testbefehl aus dem Spike (um den Spieler)."""
    global _frieren_gegenfall
    pc = local_pc()
    if pc is None or pc.Pawn is None:
        return
    if variante == "aus":
        frieren_aus("Befehl")
        return
    if _frieren:
        frieren_aus("neuer Versuch")
    o = pc.Pawn.Location
    _frieren_gegenfall = None
    for p in _gegner_lebend():
        try:
            d = _abstand_uu(p.Location, o)
            if d > radius_m * UU_JE_METER_A:
                if _frieren_gegenfall is None:
                    l = p.Location
                    _frieren_gegenfall = (p._path_name(), (l.X, l.Y, l.Z))
                continue
            e = _frieren_einer(p, variante, False)
            logging.info(f"[ZB] frieren ({variante}): {p.Name} auf {d / UU_JE_METER_A:.1f} m, Leben {e['leben']:.0f}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] frieren: {ex}")
    logging.info(f"[ZB] frieren ({variante}): {len(_frieren)} Gegner im Umkreis von {radius_m:.0f} m,"
                 f" Gegenfall {_frieren_gegenfall[0].rsplit('.', 1)[-1] if _frieren_gegenfall else 'keiner'}")
    _frieren_messung[:] = [[2.0, "2 s"], [5.0, "5 s"]]


def frieren_aus(grund: str) -> None:
    n = 0
    for pfad in list(_frieren):
        try:
            n += _auftauen(pfad)
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] frieren aus: {ex}")
    _frieren.clear()
    _frieren_messung.clear()
    # _auftau_offen bleibt: Sprengsatz trifft beim Zuenden noch Gefrorene, der Bonus kommt einen Tick spaeter
    if n:
        logging.info(f"[ZB] frieren aus ({grund}): {n} Gegner aufgetaut")


def mechanik_zeitstillstand(x: float, y: float, z: float) -> None:
    """v1.71: bei der Landung der Bombe alle Gegner im Umkreis einfrieren, Bosse eingeschlossen. Wer
    spaeter in den Kreis laeuft, bleibt frei - es wird nur einmal eingefroren."""
    if skill_rang("Zeitstillstand") <= 0:
        return
    if _frieren:
        frieren_aus("neue Bombe")
    mitte = _vec(x, y, z)
    for p in _gegner_lebend():
        try:
            if _abstand_uu(p.Location, mitte) <= ZEITSTILLSTAND_RADIUS_M * UU_JE_METER_A:
                _frieren_einer(p, "halten", True)
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Time Freeze: {ex}")
    logging.info(f"[ZB] Time Freeze: {len(_frieren)} Gegner im Umkreis von {ZEITSTILLSTAND_RADIUS_M:.0f} m eingefroren")


# --- Guaranteed Crits (Rewind T3, 5 Raenge) - v1.72 -------------------------------------------------
# Ob ein Treffer kritisch ist, entscheidet die Trefferzone: BodyHitRegionDefinition.bCriticalHit (Dump:
# 288 von 1105 Zonen True, z. B. GD_GoliathShared...HitRegion_Head). Das sind Datenobjekte, keine Welt-Actors -
# Eigenschaften schreiben ist unkritisch. Nach dem Zuenden fuer 1 s je Rang alle geladenen Zonen kritisch,
# danach genau die geaenderten zurueck. GD_PlayerShared bleibt aussen vor (Treffer auf Spieler).
# NEBENWIRKUNG (bewusst): auch Koop-Partner treffen in dieser Zeit kritisch. Zonen, die erst waehrend des
# Fensters geladen werden, bleiben normal.
KRIT_JE_RANG_S = 1.0
_krit_alt: list[str] = []   # Pfade der Zonen, die wir auf True gesetzt haben
_krit_rest = 0.0


def krit_an(sekunden: float, grund: str) -> None:
    global _krit_rest
    if not _krit_alt:
        for r in unrealsdk.find_all("BodyHitRegionDefinition", exact=False):
            try:
                pfad = r._path_name()
                if "Default__" in pfad or pfad.startswith("GD_PlayerShared."):
                    continue
                if not bool(r.bCriticalHit):
                    r.bCriticalHit = True
                    _krit_alt.append(pfad)
            except Exception:  # noqa: BLE001
                continue
    _krit_rest = max(_krit_rest, sekunden)
    logging.info(f"[ZB] Guaranteed Crits ({grund}): {len(_krit_alt)} Trefferzonen kritisch fuer {_krit_rest:.1f} s")


def krit_aus(grund: str) -> None:
    global _krit_rest
    _krit_rest = 0.0
    n = 0
    for pfad in _krit_alt:
        r = _frieren_finden("BodyHitRegionDefinition", pfad)
        if r is not None:
            try:
                r.bCriticalHit = False
                n += 1
            except Exception:  # noqa: BLE001
                pass
    if _krit_alt:
        logging.info(f"[ZB] Guaranteed Crits aus ({grund}): {n} von {len(_krit_alt)} Trefferzonen zurueck")
    _krit_alt.clear()


def _krit_tick(dt: float) -> None:
    global _krit_rest
    if _krit_rest <= 0:
        return
    _krit_rest -= dt
    if _krit_rest <= 0:
        krit_aus("Zeit um")


def mechanik_sichere_krits() -> None:
    rang = skill_rang("SichereKrits")
    if rang > 0:
        krit_an(KRIT_JE_RANG_S * rang, f"gezuendet, Rang {rang}")


def zeitstillstand_treffer(obj: UObject, args: Any, verlust: float) -> None:
    """Aus dem TakeDamage-POST: der erste Treffer taut auf. Kam er vom Spieler, gibt es denselben Schaden
    noch einmal - aber erst im naechsten Tick (kein TakeDamage mitten in TakeDamage, s. Paket B)."""
    pfad = obj._path_name()
    e = _frieren.get(pfad)
    if e is None or not e.get("skill"):
        return
    if verlust <= 0:   # Schild hat geschluckt - dann zaehlt der Parameter (wie bei Paradoxon)
        try:
            verlust = float(_arg(args, "Damage", "DamageAmount") or 0.0)
        except Exception:  # noqa: BLE001
            verlust = 0.0
    if verlust <= 0:
        # v1.71b: Treffer ohne Schaden tauen NICHT auf. Im Test 2026-10-11 tauten zwei Gegner 0,6 s nach der
        # Landung mit 0 Schaden auf - vermutlich ein eigener Effekt (Behavior_Explode mit Schaden 0).
        if not e.get("null_gemeldet"):
            e["null_gemeldet"] = True
            logging.info(f"[ZB] Time Freeze: {obj.Name} mit 0 Schaden getroffen - bleibt gefroren")
        return
    _auftauen(pfad)
    pc = local_pc()
    urheber = _arg(args, "InstigatedBy", "EventInstigator")
    vom_spieler = False
    try:
        if pc is not None and urheber is not None:
            upfad = urheber._path_name()
            vom_spieler = upfad == pc._path_name() or (pc.Pawn is not None and upfad == pc.Pawn._path_name())
    except Exception:  # noqa: BLE001
        pass
    if vom_spieler and _leben(obj) > 0:
        _auftau_offen.append((pfad, verlust))
    logging.info(f"[ZB] Time Freeze: {obj.Name} getroffen ({verlust:.0f}, {'Spieler' if vom_spieler else 'fremd'}) - aufgetaut,"
                 f" {len(_frieren)} bleiben gefroren")


def _frieren_tick(dt: float) -> None:
    global _eigen
    if _auftau_offen:
        offen = list(_auftau_offen)
        _auftau_offen.clear()
        pc = local_pc()
        for pfad, bonus in offen:
            p = _frieren_finden("WillowAIPawn", pfad)
            if p is None or pc is None or _leben(p) <= 0:
                continue
            _eigen = True
            try:
                logging.info(f"[ZB] Time Freeze: doppelter Schaden an {p.Name}: {_treffer(p, pc, bonus, 0.0, p.Location, False)}")
            finally:
                _eigen = False
    for pfad, e in list(_frieren.items()):
        if e.get("variante") != "halten":
            continue
        p = _frieren_finden("WillowAIPawn", pfad)
        if p is None:
            continue
        if e.get("skill") and _leben(p) <= 0:
            _auftauen(pfad)   # tot (z. B. Brand) - die Leiche nicht festhalten
            continue
        try:
            x, y, z = e["ort"]
            p.Velocity = _vec(0.0, 0.0, 0.0)
            p.Acceleration = _vec(0.0, 0.0, 0.0)
            p.Location = _vec(x, y, z)
        except Exception as ex:  # noqa: BLE001
            if not e.get("fehler"):
                e["fehler"] = True
                logging.error(f"[ZB] frieren halten: {ex}")
    if not _frieren_messung:
        return
    for m in _frieren_messung:
        m[0] -= dt
    faellig = [m for m in _frieren_messung if m[0] <= 0]
    _frieren_messung[:] = [m for m in _frieren_messung if m[0] > 0]
    for _, etikett in faellig:
        for pfad, e in _frieren.items():
            p = _frieren_finden("WillowAIPawn", pfad)
            if p is None:
                logging.info(f"[ZB] frieren nach {etikett}: {pfad.rsplit('.', 1)[-1]} nicht mehr da")
                continue
            l, (x, y, z) = p.Location, e["ort"]
            weg = math.sqrt((l.X - x) ** 2 + (l.Y - y) ** 2 + (l.Z - z) ** 2) / UU_JE_METER_A
            logging.info(f"[ZB] frieren nach {etikett}: {p.Name} bewegt {weg:.2f} m, Leben {e['leben']:.0f} -> {_leben(p):.0f}")
        if _frieren_gegenfall is not None:
            p = _frieren_finden("WillowAIPawn", _frieren_gegenfall[0])
            if p is not None:
                l, (x, y, z) = p.Location, _frieren_gegenfall[1]
                weg = math.sqrt((l.X - x) ** 2 + (l.Y - y) ** 2 + (l.Z - z) ** 2) / UU_JE_METER_A
                logging.info(f"[ZB] frieren nach {etikett}: Gegenfall {p.Name} (nicht gefroren) bewegt {weg:.2f} m")


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
    | (BL2s Singularity-Granaten ueber Behavior_SetPhysics). zb stoss ist seit v1.55 ausgebaut.|
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
# "Der Anker speichert deine Stacks; beim Zuenden sind sie wieder da." Seit v1.13 die Kill-Stacks
# (seit v1.61: Haste Stacks, nur die aus Kills): ist der Stapel beim Zuenden kleiner als beim Legen,
# kommt der alte zurueck, und die Verfallsfrist beginnt neu. Gespannte Zeit endet mit dem Zuenden
# per Design.

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
        _kill_stacks = min(_erinnerung_stacks, EILE_MAX - _feuer_stacks)
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
NACHHALL_FAKTOR = 2.0            # v1.13: x Granatenschaden der Schockwelle
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


# v1.57: Refill (Overclock T1, docs/skills.md 9.2). Jeder Kill fuellt 5 % je Rang des Magazins auf,
# ohne die Reserve anzutasten. ReloadCnt = Patronen IM Magazin (Spike B, docs/spikes.md). Der Pool der
# Waffe enthaelt das Magazin mit (BO2-Projekt, Test 7 bestaetigt: Reserve = Pool - ReloadCnt) - deshalb
# waechst der Pool um dieselbe Zahl, sonst ginge das Auffuellen doch von der Reserve ab. Pool schreiben
# ist belegt (Volle Rueckerstattung). VERMUTUNG: das Spiel kappt den Pool an seinem Maximum - dann
# kommt die Differenz aus der (vollen) Reserve; das Log zeigt es (Pool Soll/Ist).
NACHFUELLEN_JE_RANG = 0.05


def mechanik_nachfuellen(pc: UObject) -> bool:
    rang = skill_rang("Nachfuellen")
    if rang <= 0:
        return False
    pawn = pc.Pawn
    weapon = pawn.Weapon if pawn is not None else None
    if weapon is None:
        logging.info("[ZB] Refill: keine Waffe in der Hand")
        return False
    mag, groesse = int(weapon.ReloadCnt), int(weapon.ClipSize)
    soll = max(1, round(groesse * NACHFUELLEN_JE_RANG * rang))
    n = min(soll, groesse - mag)
    if n <= 0:
        logging.info(f"[ZB] Refill: Magazin voll ({mag}/{groesse})")
        return False
    pool = weapon.AmmoPool.Data
    pool_vorher = float(pool.CurrentValue) if pool is not None else -1.0
    if pool is not None:
        pool.CurrentValue = pool_vorher + n
    weapon.ReloadCnt = mag + n
    pool_nachher = float(pool.CurrentValue) if pool is not None else -1.0
    logging.info(f"[ZB] Refill: Rang {rang}, +{n} (Soll {soll}) | Magazin {mag} -> {int(weapon.ReloadCnt)}/{groesse}"
                 f" | Pool {pool_vorher:.0f} -> {pool_nachher:.0f} (Soll {pool_vorher + n:.0f})"
                 f" | Reserve {pool_vorher - mag:.0f} -> {pool_nachher - int(weapon.ReloadCnt):.0f}")
    return True


# v1.58: Infinite (Overclock T5, docs/skills.md 9.2). Die ersten 5 s nach dem Wurf haelt der Tick das
# Magazin der Waffe in der Hand voll - Rezept wie Refill (Pool und ReloadCnt um dieselbe Zahl), also
# ohne Griff in die Reserve. Gilt fuer jede Waffe, auch nach einem Wechsel. Geschrieben wird nur, wenn
# etwas fehlt; die Summe kommt beim Ende ins Log.
UNENDLICH_SEKUNDEN = 5.0
_unendlich_rest = 0.0
_unendlich_summe = 0


def mechanik_unendlich_gelegt() -> None:
    global _unendlich_rest, _unendlich_summe
    if skill_rang("Unendlich") <= 0:
        return
    _unendlich_rest, _unendlich_summe = UNENDLICH_SEKUNDEN, 0
    logging.info(f"[ZB] Infinite: an fuer {UNENDLICH_SEKUNDEN:.0f} s")


def _unendlich_tick(pc: UObject, dt: float) -> None:
    global _unendlich_rest, _unendlich_summe
    if _unendlich_rest <= 0:
        return
    _unendlich_rest -= dt
    pawn = pc.Pawn
    weapon = pawn.Weapon if pawn is not None else None
    if weapon is not None:
        mag, groesse = int(weapon.ReloadCnt), int(weapon.ClipSize)
        n = groesse - mag
        if n > 0:
            pool = weapon.AmmoPool.Data
            if pool is not None:
                pool.CurrentValue = float(pool.CurrentValue) + n
            weapon.ReloadCnt = groesse
            _unendlich_summe += n
    if _unendlich_rest <= 0:
        reserve = "?"
        if weapon is not None and weapon.AmmoPool.Data is not None:
            reserve = f"{float(weapon.AmmoPool.Data.CurrentValue) - int(weapon.ReloadCnt):.0f}"
        logging.info(f"[ZB] Infinite: aus, {_unendlich_summe} Schuss nachgefuellt | Reserve jetzt {reserve}")


# v1.59: Borrowed Health (Rewind T2, docs/skills.md 9.2). Zuenden heilt 12 % (v1.59d, vorher 10) des Maximums je Rang;
# die Schuld ist 125 % (bis v1.59b: das Doppelte) der tatsaechlich geheilten Menge (bei vollem Leben also keine). Der Tick
# zahlt den Rest gleichmaessig bis zum Ende der 15 s ab (Rest / Restzeit je Frame), nie unter 1 Leben.
# Jeder Kill tilgt 25 % der Anfangsschuld - vier Kills, und es bleibt nichts.
GELIEHEN_JE_RANG = 0.12  # v1.59d: Nutzer, Buff von 10 %
GELIEHEN_FAKTOR = 1.25  # v1.59c: Nutzer, das Doppelte war zu hart
GELIEHEN_SEKUNDEN = 15.0  # v1.59b: Nutzer, 6 s zog viel zu schnell ab
GELIEHEN_KILL_ANTEIL = 0.25
_geliehen_rest_s = 0.0
_geliehen_schuld = 0.0
_geliehen_start = 0.0
_geliehen_bezahlt = 0.0


def mechanik_geliehen_gezuendet(pawn: UObject) -> bool:
    global _geliehen_rest_s, _geliehen_schuld, _geliehen_start, _geliehen_bezahlt
    rang = skill_rang("GeliehenesLeben")
    if rang <= 0:
        return False
    maxi, alt = float(pawn.GetMaxHealth()), float(pawn.GetHealth())
    pawn.SetHealth(min(maxi, alt + GELIEHEN_JE_RANG * rang * maxi))
    neu = float(pawn.GetHealth())
    geheilt = max(0.0, neu - alt)
    _geliehen_schuld = _geliehen_start = GELIEHEN_FAKTOR * geheilt
    _geliehen_rest_s = GELIEHEN_SEKUNDEN if _geliehen_schuld > 0 else 0.0
    _geliehen_bezahlt = 0.0
    logging.info(f"[ZB] Borrowed Health: Rang {rang}, Leben {alt:.0f} -> {neu:.0f}/{maxi:.0f} (+{geheilt:.0f}), "
                 f"Schuld {_geliehen_schuld:.0f} ueber {GELIEHEN_SEKUNDEN:.0f} s")
    return True


def mechanik_geliehen_kill() -> None:
    global _geliehen_schuld
    if _geliehen_rest_s <= 0 or _geliehen_schuld <= 0:
        return
    vorher = _geliehen_schuld
    _geliehen_schuld = max(0.0, _geliehen_schuld - GELIEHEN_KILL_ANTEIL * _geliehen_start)
    logging.info(f"[ZB] Borrowed Health: Kill tilgt {vorher - _geliehen_schuld:.0f}, Schuld {vorher:.0f} -> {_geliehen_schuld:.0f}")


def _geliehen_tick(pc: UObject, dt: float) -> None:
    global _geliehen_rest_s, _geliehen_schuld, _geliehen_bezahlt
    if _geliehen_rest_s <= 0:
        return
    pawn = pc.Pawn
    anteil = min(1.0, dt / _geliehen_rest_s)
    abzug = _geliehen_schuld * anteil
    _geliehen_schuld -= abzug
    _geliehen_rest_s -= dt
    if pawn is not None and abzug > 0:
        h = float(pawn.GetHealth())
        ziel = max(1.0, h - abzug)
        if ziel < h:
            pawn.SetHealth(ziel)
            _geliehen_bezahlt += h - ziel
    if _geliehen_rest_s <= 0:
        _geliehen_schuld = 0.0
        leben = f"{float(pawn.GetHealth()):.0f}" if pawn is not None else "?"
        logging.info(f"[ZB] Borrowed Health: Ende, {_geliehen_bezahlt:.0f} von {_geliehen_start:.0f} bezahlt, Leben jetzt {leben}")


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
    explodieren(pawn, "Nachhall", FX_NACHHALL, basis * NACHHALL_FAKTOR * _endspurt_faktor, NACHHALL_RADIUS_M * UU_JE_METER_A,
                f"{NACHHALL_FAKTOR:.0f} x {basis:.0f} ({quelle}) x Crunch {_endspurt_faktor:.2f}")
    return _umkreis_treffen("Nachhall", pawn.Location, NACHHALL_RADIUS_M, 0.0, 0.0, True) >= 0


# --- Unspent Time (Overclock T6, Capstone) - v1.73, ersetzt Time Skip -------------------------------
# Nutzer 2026-10-11: Time Skip musste man "setuppen" (Gegner auf der Linie). Neu: Jeder Gegner, den der
# Spieler toetet, entlaedt die Zeit, die er noch gehabt haette - eine Explosion im Element der Waffe,
# die weitere Gegner toeten kann (Kette). Interner Schluessel bleibt "Zeitsprung", damit Punkte aus
# alten Spielstaenden uebergehen.
# Kill-Erkennung im WillowAIPawn:TakeDamage-Hook: Leben im PRE > 0, im POST <= 0, Urheber = Spieler
# (Controller oder Pawn - auch eigene Explosionen, so entsteht die Kette). Der Ort wird sofort gelesen,
# explodiert wird erst im Tick (kein Schaden aus dem Hook heraus), hoechstens UNSPENT_JE_S je Sekunde.
# Element: WillowWeapon.DefinitionData.ElementalPartDefinition (Dump: *_Elemental_Fire/_Shock/
# _Corrosive/_Slag/_None). Ohne Element eine normale Explosion.
UNSPENT_FAKTOR = 1.5          # x Waffenschaden (v1.73b, Nutzer; v1.73: 1.0)
UNSPENT_RADIUS_UU = 500.0     # 5 m
UNSPENT_JE_S = 8              # Explosionen je Sekunde hoechstens
UNSPENT_STAU_MAX = 16         # mehr wartende verfallen (aelteste zuerst)
UNSPENT_ELEMENT = {           # Teilname -> Schluessel in SPRENGSATZ_EXPLOSION
    "_Fire": "Incendiary", "_Shock": "Shock", "_Corrosive": "Corrosive", "_Slag": "Slag",
}
UNSPENT_OHNE_ELEMENT = "GD_Explosions.explosive.Explosion_ExplosiveMaster"   # = SPRENGSATZ_ERSATZ (steht weiter unten), nicht der Nukem-Pilz
_rang_unspent = 0
_rang_unspent_uhr = 0.0
_unspent_vor: dict[str, float] = {}
_unspent_stau: list[tuple[float, float, float, str]] = []   # (x, y, z, Name des Gegners)
_unspent_budget = float(UNSPENT_JE_S)
_unspent_element_gemeldet = ""


def _waffen_element(pawn: UObject) -> tuple[str, str]:
    """(ExplosionDefinition-Pfad, Beschreibung) nach dem Element der Waffe in der Hand."""
    global _unspent_element_gemeldet
    teil = ""
    try:
        t = pawn.Weapon.DefinitionData.ElementalPartDefinition
        teil = str(t.Name) if t is not None else ""
    except Exception:  # noqa: BLE001
        teil = ""
    for endung, element in UNSPENT_ELEMENT.items():
        if endung in teil:
            pfad, name = SPRENGSATZ_EXPLOSION[element], element
            break
    else:
        pfad, name = UNSPENT_OHNE_ELEMENT, "ohne Element"
    if teil != _unspent_element_gemeldet:
        _unspent_element_gemeldet = teil
        logging.info(f"[ZB] Unspent Time: Waffen-Element '{teil or 'kein Teil'}' -> {name}")
    return pfad, name


def _unspent_vorher(obj: UObject) -> None:
    """Aus dem TakeDamage-PRE: Leben merken (nur mit Skill)."""
    if _rang_unspent <= 0:
        return
    try:
        leben = _leben(obj)
        if leben > 0:
            _unspent_vor[obj._path_name()] = leben
    except Exception:  # noqa: BLE001
        pass


def _unspent_nachher(obj: UObject, args: Any) -> None:
    """Aus dem TakeDamage-POST: war das ein Kill durch den Spieler? Dann den Ort vormerken."""
    if _rang_unspent <= 0:
        return
    try:
        vorher = _unspent_vor.pop(obj._path_name(), None)
        if vorher is None or _leben(obj) > 0:
            return
        pc = local_pc()
        urheber = _arg(args, "InstigatedBy", "EventInstigator")
        if pc is None or urheber is None:
            return
        upfad = urheber._path_name()
        if upfad != pc._path_name() and (pc.Pawn is None or upfad != pc.Pawn._path_name()):
            return
        o = obj.Location
        _unspent_stau.append((o.X, o.Y, o.Z, str(obj.Name)))
        if len(_unspent_stau) > UNSPENT_STAU_MAX:
            del _unspent_stau[0]
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Unspent Time: Kill: {ex}")


def _unspent_tick(dt: float) -> None:
    global _rang_unspent, _rang_unspent_uhr, _unspent_budget
    _rang_unspent_uhr -= dt
    if _rang_unspent_uhr <= 0:
        _rang_unspent_uhr = 1.0
        _rang_unspent = skill_rang("Zeitsprung")
        if len(_unspent_vor) > 200:   # Treffer ohne POST (z. B. Kartenwechsel) nicht ewig sammeln
            _unspent_vor.clear()
    _unspent_budget = min(float(UNSPENT_JE_S), _unspent_budget + UNSPENT_JE_S * dt)
    if not _unspent_stau or _unspent_budget < 1.0:
        return
    pc = local_pc()
    pawn = pc.Pawn if pc else None
    if pawn is None:
        _unspent_stau.clear()
        return
    pfad, element = _waffen_element(pawn)
    schaden = _schaden_basis(pawn) * UNSPENT_FAKTOR
    while _unspent_stau and _unspent_budget >= 1.0:
        x, y, z, name = _unspent_stau.pop(0)
        _unspent_budget -= 1.0
        ort = _vec(x, y, z)
        proj = _projektil_traeger(ort)
        if proj is None:
            continue
        explodieren(proj, "Unspent Time", pfad, schaden, UNSPENT_RADIUS_UU,
                    f"{name} getoetet, {element}, {UNSPENT_FAKTOR:.1f} x Waffe", traeger=proj, mitte=ort)
        effekt("Unspent-Nova", FX_ABSPRUNG, ort, 300.0)   # blauer Zeit-Hauch zur Element-Explosion


# =================================================================================================
# Handgriff 4, Paket B (v0.84): Paradoxon, Zeitspur
#
# Paradoxon muss wissen, wen der Spieler mit liegender Bombe getroffen hat und
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
#   - Kein Schaden aus dem Hook heraus - ein TakeDamage mitten in TakeDamage waere Reentrancy ins
#     Ungewisse.
#   - _eigen: waehrend WIR Schaden austeilen, bucht der Hook nicht. Sonst wuerde Paradoxon sich
#     selbst ins Buch schreiben.

TAKE_DAMAGE_FUNC = "WillowGame.WillowAIPawn:TakeDamage"
PARADOXON_ANTEIL = 0.1   # je Rang (v1.56: 5 Raenge, bis v1.55 fest 0,5)
ZEITSPUR_RADIUS_M = 8.0

_eigen = False
_rang_para = 0
_rang_zeitspur = 0
_leben_vor: dict[str, float] = {}
_buch: dict[str, float] = {}               # Paradoxon: Pfad -> Schaden mit liegender Bombe
_schaden_spur_gemeldet = False             # der erste gezaehlte Treffer wird einmal geloggt


def _schaden_zaehlt() -> bool:
    """Die billige Vorpruefung - nur Python-Variablen, kein Engine-Zugriff."""
    if _eigen:
        return False
    return _state == ZUSTAND_GELEGT and _rang_para > 0


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
    _echo_treffer_zaehlen()   # v1.63b: Messung Echo Bullet
    _unspent_vorher(obj)      # v1.73 Unspent Time
    if _frieren and not _eigen:   # v1.71 Time Freeze: Leben vor dem Treffer
        try:
            pfad = obj._path_name()
            if pfad in _frieren:
                _frieren[pfad]["vor"] = _leben(obj)
        except Exception:  # noqa: BLE001
            pass
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
    _unspent_nachher(obj, args)   # v1.73 Unspent Time
    if _frieren and not _eigen:   # v1.71 Time Freeze: der erste Treffer taut auf
        try:
            e = _frieren.get(obj._path_name())
            if e is not None and "vor" in e:
                zeitstillstand_treffer(obj, args, max(0.0, e["vor"] - max(0.0, _leben(obj))))
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Time Freeze: Treffer: {ex}")
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
    _buch[pfad] = _buch.get(pfad, 0.0) + wert


# --- Diagnose fuer Paket B (v0.85) --------------------------------------------------------------
#
# Der Hook zaehlt, wie oft PRE/POST kamen und warum verworfen wurde; 'zb schaden' gibt es aus.
# Die Zaehl-Hooks auf sieben TakeDamage-Kandidaten (v0.85: welcher Weg traegt?) sind seit dem
# Aufraeumen 2026-10-10 raus - beantwortet: WillowAIPawn:TakeDamage. Am Spieler: WillowPlayerPawn (v1.60).

_schaden_filter: dict[str, int] = {}
_schaden_filter_beispiel: dict[str, str] = {}


def _filter_zaehlen(grund: str, beispiel: str = "") -> None:
    _schaden_filter[grund] = _schaden_filter.get(grund, 0) + 1
    if beispiel and grund not in _schaden_filter_beispiel:
        _schaden_filter_beispiel[grund] = beispiel


def schaden_zeigen() -> None:
    """zb schaden - was der Schadens-Hook gezaehlt und warum er verworfen hat."""
    pc = local_pc()
    logging.info(f"[ZB] schaden: eigener Controller = {pc._path_name() if pc else None}, "
                 f"Pawn = {pc.Pawn._path_name() if pc and pc.Pawn else None}")
    for grund, n in sorted(_schaden_filter.items()):
        logging.info(f"[ZB] schaden: Hook {grund}: {n}x" +
                     (f"  | Beispiel: {_schaden_filter_beispiel[grund]}" if grund in _schaden_filter_beispiel else ""))


def schaden_zuruecksetzen() -> None:
    _schaden_filter.clear()
    _schaden_filter_beispiel.clear()
    logging.info("[ZB] schaden: Zaehler auf null")


def mechanik_paket_b_gelegt() -> None:
    """Beim Legen: Raenge einmal lesen, Buch leeren."""
    global _rang_para, _rang_zeitspur
    _rang_para = skill_rang("Paradoxon")
    _rang_zeitspur = skill_rang("Zeitspur")
    _buch.clear()
    if _rang_para or _rang_zeitspur:
        logging.info(f"[ZB] Paket B: Paradoxon R{_rang_para}, Zeitspur R{_rang_zeitspur}")


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
            wert = gebucht * PARADOXON_ANTEIL * _rang_para
            logging.info(f"[ZB] Paradoxon: {ziel.Name} gebucht {gebucht:.0f} -> {_treffer(ziel, pc, wert, 0.0, ziel.Location, False)}")
            n += 1
            summe += wert
        finally:
            _eigen = False
    logging.info(f"[ZB] Paradoxon: {len(_buch)} Ziele im Buch, {n} noch am Leben, {summe:.0f} Schaden nachgereicht")
    _buch.clear()
    return True


# v1.60: Return to Sender (Hindsight T3, docs/skills.md 9.2). Solange die Bombe liegt, bucht ein Hook
# am SPIELER, wer ihn wie stark verletzt hat; beim Zuenden bekommt jeder noch lebende Urheber 20 % je
# Rang (v1.60b, vorher 20) davon zurueck, an seiner Position (_treffer, wie Paradoxon).
# Hook aus dem BO2-Projekt (Test 76, dort bewiesen, bei uns NEU): WillowGame.WillowPlayerPawn:TakeDamage.
# WillowPawn:TakeDamage feuert fuer Spieler fast nie. Gebucht wird der TATSAECHLICHE Verlust an Leben +
# Schild (PRE/POST am eigenen Pawn, Spike B), nicht args.Damage - so zaehlen Resistenzen schon mit.
# Urheber: InstigatedBy.Pawn, sonst Pipeline.DamageInstigator (ggf. dessen Instigator, falls Projektil).
# An fremden Objekten nur Eigenschaften lesen (v0.74).
SPIELER_SCHADEN_FUNC = "WillowGame.WillowPlayerPawn:TakeDamage"
RUECKSENDEN_JE_RANG = 0.25  # v1.60b: Nutzer, 20 % wirkte schwach
_rs_rang = 0
_rs_vor = -1.0
_rs_buch: dict[str, float] = {}   # Pfad des Urhebers -> erlittener Schaden
_rs_ohne_urheber = 0.0
_rs_spur_gemeldet = False


def _rs_eigener_pawn(obj: UObject) -> UObject | None:
    pc = local_pc()
    if pc is None or pc.Pawn is None:
        return None
    try:
        return pc.Pawn if obj._path_name() == pc.Pawn._path_name() else None
    except Exception:  # noqa: BLE001
        return None


def _rs_urheber(args: Any) -> UObject | None:
    kandidaten = []
    try:
        ib = _arg(args, "InstigatedBy", "EventInstigator")
        if ib is not None:
            kandidaten.append(ib.Pawn)
    except Exception:  # noqa: BLE001
        pass
    try:
        di = args.Pipeline.DamageInstigator
        if di is not None:
            kandidaten.append(di)
            kandidaten.append(getattr(di, "Instigator", None))
    except Exception:  # noqa: BLE001
        pass
    for k in kandidaten:
        if k is None or not _ist_welt_actor(k):
            continue
        try:
            if k.Class.Name.startswith("WillowAIPawn") or k.Class.Name.endswith("AIPawn"):
                return k
        except Exception:  # noqa: BLE001
            continue
    return None


def _on_spieler_schaden_pre(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _rs_vor
    if _rs_rang <= 0 or _state != ZUSTAND_GELEGT:
        return
    pawn = _rs_eigener_pawn(obj)
    if pawn is None:
        return
    try:
        _rs_vor = float(pawn.GetHealth()) + float(pawn.GetShieldStrength())
    except Exception as ex:  # noqa: BLE001
        _rs_vor = -1.0
        logging.error(f"[ZB] Return to Sender PRE: {ex}")


def _on_spieler_schaden_post(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _rs_vor, _rs_ohne_urheber, _rs_spur_gemeldet
    if _rs_rang <= 0 or _state != ZUSTAND_GELEGT or _rs_vor < 0:
        return
    pawn = _rs_eigener_pawn(obj)
    if pawn is None:
        return
    try:
        verlust = _rs_vor - (float(pawn.GetHealth()) + float(pawn.GetShieldStrength()))
    finally:
        _rs_vor = -1.0
    if verlust <= 0:
        return
    urheber = _rs_urheber(args)
    if urheber is None:
        _rs_ohne_urheber += verlust
        return
    pfad = urheber._path_name()
    _rs_buch[pfad] = _rs_buch.get(pfad, 0.0) + verlust
    if not _rs_spur_gemeldet:
        _rs_spur_gemeldet = True
        logging.info(f"[ZB] Return to Sender: erster Treffer gebucht - {urheber.Name} {verlust:.0f} (Hook feuert)")


def mechanik_ruecksenden_gelegt() -> None:
    global _rs_rang, _rs_ohne_urheber, _rs_vor
    _rs_rang = skill_rang("Zuruecksenden")
    _rs_buch.clear()
    _rs_ohne_urheber, _rs_vor = 0.0, -1.0


def mechanik_ruecksenden_gezuendet() -> bool:
    global _eigen
    if _rs_rang <= 0:
        return False
    pc = local_pc()
    if pc is None:
        return False
    if not _rs_buch:
        logging.info(f"[ZB] Return to Sender: nichts gebucht (ohne Urheber: {_rs_ohne_urheber:.0f})")
        return False
    ziele = {}
    for g in _gegner_lebend():
        try:
            ziele[g._path_name()] = g
        except Exception:  # noqa: BLE001
            continue
    n, summe = 0, 0.0
    for pfad, erlitten in _rs_buch.items():
        ziel = ziele.get(pfad)
        if ziel is None:
            continue  # tot oder weg - verfaellt
        wert = erlitten * RUECKSENDEN_JE_RANG * _rs_rang
        _eigen = True   # eigene Treffer nicht von Paradoxon buchen lassen
        try:
            logging.info(f"[ZB] Return to Sender: {ziel.Name} erlitten {erlitten:.0f} -> {_treffer(ziel, pc, wert, 0.0, ziel.Location, False)}")
        finally:
            _eigen = False
        n += 1
        summe += wert
    logging.info(f"[ZB] Return to Sender: Rang {_rs_rang}, {len(_rs_buch)} Urheber, {n} noch am Leben, "
                 f"{summe:.0f} zurueckgeschickt | ohne Urheber: {_rs_ohne_urheber:.0f}")
    _rs_buch.clear()
    return True


def mechanik_paket_b_verpufft() -> None:
    """Verpufft die Bombe, verfaellt das Buch."""
    if _buch:
        logging.info(f"[ZB] Paket B: verpufft - {len(_buch)} Buchungen verfallen")
    _buch.clear()


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
# (dasselbe Muster wie der zweite Wurf von Time Loop).
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
# Handgriff 4, Paket E (v0.95): Verbuendete - Zeitkapsel-Heilung
#
# Verbuendete = die anderen WillowPlayerPawns der Karte (Welt-Actors, Pfad geprueft). Pools setzen
# wie beim Zuenden und bei Auffrischung (SetHealth/SetShieldStrength, Get*/GetMax* - alle am eigenen
# Pawn belegt, Spike B / v0.55). VERMUTUNG: im Koop wirkt das nur beim Gastgeber; ein Client setzt
# die Pools eines Mitspielers nur lokal, der Server ueberschreibt sie.
#
# Solo nicht pruefbar - darum 'zb koop selbst': der eigene Pawn zaehlt dann als Verbuendeter. Mit
# 'zb fasttot' VOR dem Legen (Anker speichert Schild 0 / Leben 1) sieht man die Aufschlaege im Log.

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
    explodieren(pawn, "Sprengsatz", SPRENGSATZ_EXPLOSION[element], basis * SPRENGSATZ_FAKTOR * _endspurt_faktor,
                SPRENGSATZ_RADIUS_UU, f"{element}, {SPRENGSATZ_FAKTOR:.0f} x {basis:.0f} ({quelle}) x Crunch {_endspurt_faktor:.2f}")


# v1.69: Crunch Time (Rewind T5, 1 Rang, docs/skills.md 9.2). Je mehr Fenster beim Zuenden uebrig ist, desto
# staerker: Faktor 1 + min(1, Rest / 15 s) auf Sprengsatz und Nachhall (also bis doppelt), und die Bombe
# explodiert selbst am Anker (= Ankunftsort, nach dem Teleport) mit Faktor x Granatenschaden im Element der
# Granate. Die Restzeit kommt aus der laufenden Skill-Instanz (StartTime + Duration, s. Kurs halten) - so
# zaehlen Langzeitgedaechtnis und Kurs halten mit. Gemessen wird in zuenden(), VOR ResetActionSkill.
ENDSPURT_VOLL_S = 15.0
ENDSPURT_RADIUS_UU = 800.0   # 8 m
_endspurt_faktor = 1.0       # gilt fuer das laufende Zuenden; 1.0 ohne Skill


def endspurt_messen(pc: UObject) -> None:
    global _endspurt_faktor
    _endspurt_faktor = 1.0
    if skill_rang("Endspurt") <= 0:
        return
    rest, quelle = None, "Skill-Instanz"
    sm = skill_manager()
    d = _find("SkillDefinition", f"{ACTION_OUTER}.Skill_{SKILL_OBJ}")
    if sm is not None and d is not None:
        try:
            inst = sm.GetActiveSkillForInstigatorByDefinition(pc, d)
            if inst is not None:
                rest = float(inst.StartTime) + float(inst.Duration) - _game_time(pc)
        except Exception as ex:  # noqa: BLE001
            logging.info(f"[ZB] Crunch Time: Skill-Instanz nicht lesbar ({ex})")
    if rest is None:
        quelle = "Ersatz (Legezeit + Grundfenster)"
        rest = _legen_time + FENSTER_SEKUNDEN - _game_time(pc)
    _endspurt_faktor = 1.0 + max(0.0, min(1.0, rest / ENDSPURT_VOLL_S))
    logging.info(f"[ZB] Crunch Time: Rest {rest:.1f} s ({quelle}) -> Faktor {_endspurt_faktor:.2f}")


def mechanik_endspurt_bombe(pawn: UObject) -> None:
    """Nach dem Teleport: die Bombe explodiert am Anker (der Spieler steht dort)."""
    if skill_rang("Endspurt") <= 0:
        return
    granate = _granate(pawn)
    element = _granaten_element(granate)
    basis, quelle = _granaten_schaden(pawn, granate)
    explodieren(pawn, "Crunch Time", SPRENGSATZ_EXPLOSION[element], basis * _endspurt_faktor, ENDSPURT_RADIUS_UU,
                f"{element}, {_endspurt_faktor:.2f} x {basis:.0f} ({quelle})")


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
_effekt_queue: list[list] = []           # [Restzeit, Label, Pfad, Ort, Radius]
_fx_fehlt: set[str] = set()


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


def _on_player_tick(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    """POST auf WillowPlayerController:PlayerTick - jeden Frame. Nur im Zustand 'gelegt' und nur
    fuer den eigenen Controller wird gerechnet."""
    global _tick_akku, _wurf, _unendlich_rest, _geliehen_rest_s
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
        _frieren_tick(dt)  # Spike Time Freeze (v1.70)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] frieren messen: {ex}")
    try:
        _unspent_tick(dt)  # Unspent Time (v1.73)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Unspent Time: {ex}")
    try:
        _krit_tick(dt)  # Guaranteed Crits (v1.72)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Guaranteed Crits: {ex}")
    try:
        _schatten_tick(pc, dt)  # Schattenanker: Ringpuffer und Haltepruefung (v0.95)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Schattenanker-Tick: {ex}")
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
    try:
        _unendlich_tick(pc, dt)  # Infinite: Magazin voll halten (v1.58)
    except Exception as ex:  # noqa: BLE001
        _unendlich_rest = 0.0
        logging.error(f"[ZB] Infinite-Tick: {ex}")
    try:
        _geliehen_tick(pc, dt)  # Borrowed Health: Schuld abtragen (v1.59)
    except Exception as ex:  # noqa: BLE001
        _geliehen_rest_s = 0.0
        logging.error(f"[ZB] Borrowed-Health-Tick: {ex}")
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


_kachel_zaehler = 0
_kachel_index = -1
_kachel_selbst = False
ADD_SELECTABLE_FUNC = "WillowGame.CharacterSelectionGFxObject:AddSelectableCharacter"


def _on_add_selectable(obj: UObject, args: Any, ret: Any, func: Any) -> Any:
    """PRE: jede Kachel-Anlage des Spiels. Die Kachel des Chronomasters bekommt das eigene Portrait."""
    global _kachel_zaehler, _kachel_selbst
    if _kachel_selbst:
        return None
    # v1.47b: die Aufrufe kommen VOR dem Commit-Hook (Log) - Position deshalb hier aus der Liste
    # bestimmen. Aufruf i legt die Kachel fuer SelectableCharacters[i] an (Reihenfolge im Log gleich).
    try:
        chars = [c._path_name() if c else "" for c in obj.Outer.SelectableCharacters]
    except Exception:  # noqa: BLE001
        chars = []
    if chars and _kachel_zaehler >= len(chars):
        _kachel_zaehler = 0
    i = _kachel_zaehler
    _kachel_zaehler += 1
    try:
        alt = str(args.IconMoviePath)
    except Exception:  # noqa: BLE001
        alt = "?"
    if not (i < len(chars) and chars[i] == NAMEID_NEW):
        logging.info(f"[ZB] Kachel {i}: {alt}")
        return None
    url = portrait_url()
    logging.info(f"[ZB] Kachel {i} (Chronomaster): {alt} -> {url}")
    if url == PORTRAIT_PATH:
        return None
    _kachel_selbst = True
    try:
        obj.AddSelectableCharacter(url)
    finally:
        _kachel_selbst = False
    from unrealsdk.hooks import Block  # noqa: PLC0415
    return Block


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
            # v1.46b: seit der DLC-Registrierung legt das Spiel die Kachel selbst an (ruft
            # AddSelectableCharacter je Eintrag) - das Portrait tauscht _on_add_selectable
            global _kachel_zaehler, _kachel_index
            _kachel_zaehler = 0
            _kachel_index = names.index(NAMEID_NEW)
            logging.info(f"[ZB] SPIKE C: Chronomaster ist bereits in der Liste (Index {_kachel_index})")
            return
        chars.append(mine)
        url = portrait_url()
        obj.AddSelectableCharacter(url)
        logging.info(f"[ZB] SPIKE C: Chronomaster angehaengt + Kachel ({url}) -> jetzt {len(movie.SelectableCharacters)} Eintraege")
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
    add_hook(ADD_SELECTABLE_FUNC, Type.PRE, "zb_kachel", _on_add_selectable)  # eigenes Portrait, v1.46b
    # Phase 3: die Skilltaste wird zu Legen und Zuenden. Greift nur beim Chronomaster (ist_chronomaster).
    add_hook(SKILL_STARTED, Type.POST, "zb_legen", _on_skill_started)
    add_hook(SKILL_PRESSED, Type.PRE, "zb_zuenden", _on_start_pressed)
    add_hook(SKILL_ENDED, Type.POST, "zb_verpuffen", _on_skill_ended)
    add_hook(ACTIVATE_SKILL_FUNC, Type.PRE, "zb_stealth", _on_activate_skill)
    add_hook(POST_AK_EVENT_FUNC, Type.PRE, "zb_klang", _on_post_ak_event)
    add_hook(TICK_FUNC, Type.POST, "zb_ticker", _on_player_tick)  # Handgriff 2, v0.59
    add_hook(SKIN_TICK_FUNC, Type.PRE, "zb_aussehen", _on_viewport_tick)  # eigenes Modell, v1.41
    add_hook(INPUT_KEY_FUNC, Type.PRE, "zb_taste", _on_input_key)  # Schattenanker, v0.95
    add_hook(KILLED_ENEMY_FUNC, Type.POST, "zb_kill", _on_notify_killed_enemy)  # Handgriff 3, v0.66
    add_hook(UPDATE_KILL_SKILLS_FUNC, Type.PRE, "zb_killskills", _on_update_kill_skills)  # v1.16
    add_hook(TAKE_DAMAGE_FUNC, Type.PRE, "zb_schaden_vor", _on_take_damage_pre)     # Paket B, v0.84
    add_hook(TAKE_DAMAGE_FUNC, Type.POST, "zb_schaden_nach", _on_take_damage_post)  # Paket B, v0.84
    add_hook(SPIELER_SCHADEN_FUNC, Type.PRE, "zb_rs_vor", _on_spieler_schaden_pre)     # Return to Sender, v1.60
    add_hook(FIRE_FUNC, Type.PRE, "zb_feuer", _on_fire_ammunition)                     # Haste Stacks, v1.61
    add_hook(FIRE_FUNC, Type.PRE, "zb_echo_vor", _on_echo_pre)                         # Echo Bullet, v1.63
    add_hook(FIRE_FUNC, Type.POST, "zb_echo_nach", _on_echo_post)                      # Echo Bullet, v1.63
    add_hook(RELOAD_FUNC, Type.PRE, "zb_nachladen", _on_reload_anim)                   # Dimensional Loop, v1.64
    for i, fname in enumerate(WURF_FUNCS):                                             # Time Loop, v1.65
        add_hook(fname, Type.POST, f"zb_wurf_{i}", _make_wurf_hook(fname))
    add_hook(WURF_FERTIG_FUNC, Type.POST, "zb_wurf_fertig", _on_wurf_fertig)           # Time Loop, v1.65d
    add_hook(SPIELER_SCHADEN_FUNC, Type.POST, "zb_rs_nach", _on_spieler_schaden_post)  # Return to Sender, v1.60
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
    remove_hook(ADD_SELECTABLE_FUNC, Type.PRE, "zb_kachel")
    remove_hook(SKILL_STARTED, Type.POST, "zb_legen")
    remove_hook(SKILL_PRESSED, Type.PRE, "zb_zuenden")
    remove_hook(SKILL_ENDED, Type.POST, "zb_verpuffen")
    remove_hook(ACTIVATE_SKILL_FUNC, Type.PRE, "zb_stealth")
    remove_hook(POST_AK_EVENT_FUNC, Type.PRE, "zb_klang")
    remove_hook(TICK_FUNC, Type.POST, "zb_ticker")
    remove_hook(SKIN_TICK_FUNC, Type.PRE, "zb_aussehen")
    remove_hook(INPUT_KEY_FUNC, Type.PRE, "zb_taste")
    remove_hook(KILLED_ENEMY_FUNC, Type.POST, "zb_kill")
    remove_hook(UPDATE_KILL_SKILLS_FUNC, Type.PRE, "zb_killskills")
    remove_hook(TAKE_DAMAGE_FUNC, Type.PRE, "zb_schaden_vor")
    remove_hook(TAKE_DAMAGE_FUNC, Type.POST, "zb_schaden_nach")
    remove_hook(SPIELER_SCHADEN_FUNC, Type.PRE, "zb_rs_vor")
    remove_hook(FIRE_FUNC, Type.PRE, "zb_feuer")
    remove_hook(FIRE_FUNC, Type.PRE, "zb_echo_vor")
    remove_hook(FIRE_FUNC, Type.POST, "zb_echo_nach")
    remove_hook(RELOAD_FUNC, Type.PRE, "zb_nachladen")
    for i, fname in enumerate(WURF_FUNCS):
        remove_hook(fname, Type.POST, f"zb_wurf_{i}")
    remove_hook(WURF_FERTIG_FUNC, Type.POST, "zb_wurf_fertig")
    remove_hook(SPIELER_SCHADEN_FUNC, Type.POST, "zb_rs_nach")
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


# --- Aussehen: eigenes Modell NUR am Chronomaster (v1.41, Phase 9) -----------------------------------
# Die Pipeline (bl2_charswap) baut Meshes auf Zer0s Skelett; ihr Test-Host PipelineCharacters tauscht
# aber nach Mesh - Zer0 trug das Modell mit (2026-09-28). Hier dieselbe Technik (runtime.py der
# Pipeline, MIT: SetSkeletalMesh + eigenes MaterialInstanceConstant, Kopf ausblenden), aber je
# Komponente wird gefragt, WEM sie gehoert:
#   - dem eigenen Pawn, einer Vorschau (Statusmenue) oder dem Menue-Charakter (kein Pawn) ->
#     ist der lokale Spieler Chronomaster?
#   - einem fremden Pawn (Koop) -> dessen Controller.PlayerClass; unbekannt = nicht tauschen.
# Wechselt die Antwort (Hauptmenue: anderer Charakter gewaehlt), wird zurueckgetauscht.
# Fehlen die Pakete in CookedPCConsole (normale Spieler), passiert nichts.
# v1.42: Timekeeper-Modell (TRELLIS aus dem Konzeptbild, tools/modell_riggen.py, Spec skins/timekeeper/)
SKIN_PAKETE = ["ChronomasterTextures", "ChronomasterMeshes", "ChronomasterMeshesArms"]
SKIN_TAUSCH = {  # Quell-Mesh -> (neues Mesh, Name des Materials)
    "Char_Assassin.Mesh.Skel_AssassinBody": ("ChronomasterMeshes.Chronomaster_Body", "Mati_Chrono_Body"),
    "Char_Assassin.Mesh.Hands_Assassin": ("ChronomasterMeshesArms.Chronomaster_Arms", "Mati_Chrono_Arms"),
}
SKIN_TEXTUREN = {"p_Diffuse": "ChronomasterTextures.Chronomaster_Body_Albedo",
                 "p_Normal": "ChronomasterTextures.Chronomaster_Body_Normal"}
# Elternmaterial je Quell-Mesh plus zusaetzliche Texturen. v1.42 lief auf dem Class-Mod-Material (Platzhalter
# der Pipeline): gelb-golden, glaenzend. v1.43: Zer0s eigene Spieler-MICs (Parent Common_Materials.Player.
# Master_Player, Dump) - erben dessen kompilierte Shader. p_Masks legt fest, wo die Anpassungsfarben
# einfaerben; schwarz = nirgends, unsere Textur bleibt wie sie ist.
SKIN_MATERIALIEN = {
    "zer0": ({"Char_Assassin.Mesh.Skel_AssassinBody": "Char_Assassin.Materials.Mati_Assassin_Body",
              "Char_Assassin.Mesh.Hands_Assassin": "Char_Assassin.Materials.Mati_Assassin_Hands"},
             {"p_Masks": "EngineResources.Black"}),
    "klassenmod": ({"*": "Item_ClassMods.Mat.Master_ClassMod"}, {}),
    # v1.49: Zer0s eigene Texturen (aus seinem MIC kopiert) - fuer Modelle auf Zer0s UV-Layout
    # (Nullprobe, Zer0-Umbau aus docs/modell-pipeline.md 2b)
    "original": ({"Char_Assassin.Mesh.Skel_AssassinBody": "Char_Assassin.Materials.Mati_Assassin_Body",
                  "Char_Assassin.Mesh.Hands_Assassin": "Char_Assassin.Materials.Mati_Assassin_Hands"},
                 None),
}
_skin_mat_art = "zer0"
SKIN_MAT_OUTER = "Common_GunMaterials.Materials.Pistol"
SKIN_KOPF_PRAEFIX = "CD_Heads_Assassin"
SKIN_TICKS = 30          # v1.45: alle 30 Frames (vorher 10 wie die Pipeline; Ruckler gemessen v1.44)
SKIN_TICK_FUNC = "WillowGame.WillowGameViewportClient:Tick"  # laeuft auch im Menue/Pause (Pipeline, bewiesen)

_skin: dict[str, tuple[UObject, UObject]] = {}   # Quell-Mesh-Pfad -> (Mesh, MIC); leer = kein Skin
_skin_versucht = False
_skin_an = True          # zb skin aus|an
_skin_zaehler = 0
# Komponentenpfad -> (Quell-Mesh-Objekt, Materialliste, Besitzerpfad). Nur Pfade als Schluessel -
# Komponenten werden bei jedem Scan frisch per find_all geholt (keine Menue-Objekte cachen).
_skin_getauscht: dict[str, tuple[str, list, str]] = {}   # v1.53: (Mesh-Pfad, [(Klasse, Pfad)|None], Besitzer)
_skin_versteckt: dict[str, str] = {}   # Komponentenpfad -> Besitzerpfad
_skin_letzte_klasse: str | None = "?"


def _pfad(obj: UObject | None) -> str:
    try:
        return obj._path_name() if obj is not None else ""
    except Exception:  # noqa: BLE001
        return ""


def _skin_laden() -> None:
    """Einmal: Pakete laden (nur wenn die Dateien da sind), Meshes finden, Materialien bauen, rooten."""
    global _skin_versucht
    if _skin_versucht:
        return
    _skin_versucht = True
    import os  # noqa: PLC0415
    cooked = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                          "WillowGame", "CookedPCConsole")
    fehlt = [p for p in SKIN_PAKETE if not os.path.isfile(os.path.join(cooked, p + ".upk"))]
    if fehlt:
        logging.info(f"[ZB] Aussehen: kein eigenes Modell installiert (fehlt: {', '.join(fehlt)})")
        return
    try:
        for p in SKIN_PAKETE:
            paket = unrealsdk.load_package(p)
            if paket is not None:
                _root(paket)
        for quelle, (mesh_pfad, mat_name) in SKIN_TAUSCH.items():
            mesh = unrealsdk.find_object("SkeletalMesh", mesh_pfad)
            _root(mesh)
            for sock in mesh.Sockets:
                _root(sock)
            mic = _find("MaterialInstanceConstant", f"{SKIN_MAT_OUTER}.{mat_name}")
            if mic is None:
                outer = _find("Package", SKIN_MAT_OUTER) or _find("Package", "Char_Assassin.Materials")
                mic =unrealsdk.construct_object("MaterialInstanceConstant", outer, mat_name, 0, None)
            _root(mic)
            _skin[quelle] = (mesh, mic)
        skin_material(_skin_mat_art)
        logging.info(f"[ZB] Aussehen: Modell geladen ({len(_skin)} Meshes) - nur am {CHARACTER_NAME}")
    except Exception as ex:  # noqa: BLE001
        _skin.clear()
        logging.error(f"[ZB] Aussehen: Laden gescheitert: {ex}")


def skin_material(art: str) -> None:
    """Elternmaterial und Texturen unserer MICs setzen (zb skin mat zer0|klassenmod, v1.43)."""
    global _skin_mat_art
    if art not in SKIN_MATERIALIEN:
        logging.info(f"[ZB] Aussehen: Material {art}? Moeglich: {', '.join(SKIN_MATERIALIEN)}")
        return
    _skin_mat_art = art
    je_mesh, extra = SKIN_MATERIALIEN[art]
    for quelle, (_mesh, mic) in _skin.items():
        eltern_pfad = je_mesh.get(quelle) or next(iter(je_mesh.values()))
        eltern = _find("MaterialInstanceConstant", eltern_pfad) or _find("Material", eltern_pfad)
        if eltern is None:
            logging.error(f"[ZB] Aussehen: Elternmaterial {eltern_pfad} nicht gefunden")
            continue
        mic.SetParent(eltern)
        if extra is None:
            # "original": Zer0s Texturparameter uebernehmen (nur Properties lesen) - ueberschreibt,
            # was eine andere Art vorher an unserem MIC gesetzt hatte
            for tp in eltern.TextureParameterValues:
                if tp.ParameterValue is not None:
                    _root(tp.ParameterValue)
                    mic.SetTextureParameterValue(tp.ParameterName, tp.ParameterValue)
                    logging.info(f"[ZB] Aussehen:   {tp.ParameterName} = {_pfad(tp.ParameterValue)}")
        for k, t in (dict(SKIN_TEXTUREN, **extra) if extra is not None else {}).items():
            # v1.50: eigene Arm-Texturen (Zer0-Umbau: die Arme haben Zer0s Hand-UVs), sonst die des Koerpers
            eigene = t.replace("Chronomaster_Body_", "Chronomaster_Arms_") if "Hands_Assassin" in quelle else t
            tex = _find("Texture2D", eigene) or _find("Texture2D", t)
            if tex is None:
                logging.error(f"[ZB] Aussehen: Textur {t} nicht gefunden")
                continue
            _root(tex)
            mic.SetTextureParameterValue(k, tex)
            logging.info(f"[ZB] Aussehen:   {quelle.rsplit('.', 1)[-1]} {k} = {_pfad(tex)}")
        logging.info(f"[ZB] Aussehen: Material '{art}' fuer {quelle.rsplit('.', 1)[-1]}: {_pfad(eltern)}")
    # getauschte Komponenten sofort neu belegen (das Spiel haelt eigene Wrapper-Instanzen)
    for comp in unrealsdk.find_all("SkeletalMeshComponent", exact=False):
        try:
            if _pfad(comp) in _skin_getauscht:
                mic = next((m for n, m in _skin.values() if _pfad(n) == _pfad(comp.SkeletalMesh)), None)
                if mic is not None:
                    comp.SetMaterial(0, mic)
        except Exception:  # noqa: BLE001
            continue


def _skin_klasse_von(besitzer: UObject, pc: UObject, lokal: bool) -> bool:
    """Traegt der Besitzer dieser Komponente den Chronomaster?"""
    pawn = pc.Pawn if pc is not None else None
    if pawn is None or "Pawn" not in besitzer.Class.Name:
        return lokal                       # Menue-Charakter, Vorschau im Statusmenue
    if _pfad(besitzer) == _pfad(pawn):
        return lokal
    try:                                   # Koop: fremder Pawn - nur Eigenschaften lesen
        cls = besitzer.Controller.PlayerClass
        return bool(cls is not None and _pfad(cls).endswith(f"CharClass_{CHARACTER_NAME}"))
    except Exception:  # noqa: BLE001
        return False


# v1.52: Schnellscan. find_all("SkeletalMeshComponent") lieferte in Sanctuary jede NPC-/Gegner-Komponente
# samt Archetypen: 14,7 ms im Mittel, 29,9 ms hoechstens, alle 30 Frames (zb fps, 2026-10-02). Wir brauchen
# nur Komponenten an Spielerfiguren und an der Menuefigur. Felder laut Dump: Actor.Components,
# Pawn.Mesh/Arms/HeadMesh, PlayerStandIn.PlayerMeshComp. Der Vollscan bleibt als Gegenprobe (seltener).
SKIN_TRAEGER = ("WillowPlayerPawn", "PlayerStandIn")
SKIN_TRAEGER_FELDER = ("Mesh", "Arms", "HeadMesh", "PlayerMeshComp")
# v1.54: find_all geht IMMER die ganze Objektliste durch (~9 ms je Aufruf, egal wie wenige Treffer):
# v1.53 mit drei find_all je Schnellscan kostete 28 ms im Mittel, 101 ms hoechstens (gemessen). Der
# Schnellscan nimmt deshalb gar keinen mehr: Spieler ueber WorldInfo.PawnList/NextPawn (Dump), Menuefigur und
# Koepfe ueber Pfade, die der Vollscan merkt und die jedes Mal frisch per find_object (Hash) gesucht werden.
SKIN_VOLLSCAN_TICKS = 1800         # Sicherheitsnetz ~30 s; sonst nur bei Bedarf (_skin_voll_bald)
_skin_vollscan_zaehler = 0
_skin_voll_bald = True             # naechster Tick scannt voll: Start, neuer Tausch, Pfad verschwunden
_skin_merk: list[tuple[str, str]] = []   # (Klasse, Pfad): Menuefiguren und Koepfe, vom Vollscan
_skin_luecken: set[str] = set()    # Komponenten, die nur der Vollscan fand (einmal loggen)


def _skin_komponenten_von(actor: UObject, out: list, gesehen: set) -> None:
    """Mesh-Komponenten eines Traegers (nur Eigenschaften lesen)."""
    teile = [getattr(actor, f, None) for f in SKIN_TRAEGER_FELDER]
    teile += list(actor.Components)
    for c in teile:
        if c is None:
            continue
        try:
            c.SkeletalMesh            # kein SkeletalMeshComponent -> AttributeError
        except Exception:  # noqa: BLE001
            continue
        cp = _pfad(c)                 # Pfad statt id(): das SDK liefert je Zugriff neue Huellen
        if cp not in gesehen:
            gesehen.add(cp)
            out.append(c)


def _skin_kandidaten_schnell() -> tuple[list[UObject], bool]:
    """(Komponenten, ob ein gemerkter Pfad fehlt). Ohne find_all."""
    out, gesehen = [], set()
    pc = local_pc()
    try:
        p, n = pc.WorldInfo.PawnList, 0
        while p is not None and n < 512:
            if p.Class.Name in SKIN_TRAEGER:
                _skin_komponenten_von(p, out, gesehen)
            p, n = p.NextPawn, n + 1
    except Exception:  # noqa: BLE001
        pass
    fehlt = False
    for klasse, pfad in _skin_merk:
        o = _find(klasse, pfad)
        if o is None:
            fehlt = True
            continue
        try:
            if klasse in SKIN_TRAEGER:
                _skin_komponenten_von(o, out, gesehen)
            elif pfad not in gesehen:
                gesehen.add(pfad)
                out.append(o)
        except Exception:  # noqa: BLE001
            continue
    return out, fehlt


def skin_scan(grund: str, voll: bool = False) -> None:
    global _skin_letzte_klasse
    if not _skin:
        return
    pc = local_pc()
    klasse = player_class(pc) if pc is not None else None
    if klasse is None and pc is not None:
        # Hauptmenue: pc.PlayerClass ist None (v1.41, Log). Der angezeigte Charakter steht im
        # gecachten Spielstand - nur lesen (die Kopie ist ohnehin schreibgeschuetzt).
        try:
            sg = pc.GetCachedSaveGame()
            if sg is not None and sg.PlayerClassDefinition is not None:
                klasse = "Menue:" + _pfad(sg.PlayerClassDefinition)
        except Exception:  # noqa: BLE001
            pass
    if klasse != _skin_letzte_klasse:
        logging.info(f"[ZB] Aussehen: lokale Klasse {klasse} ({grund})")
        _skin_letzte_klasse = klasse
    lokal = _skin_an and bool(klasse and klasse.endswith(f"CharClass_{CHARACTER_NAME}"))
    aktion: list[str] = []
    # v1.45: erst nach Mesh filtern (ein Pfadaufruf je Komponente), alles andere nur fuer die wenigen
    # Treffer. v1.44 hat gemessen: 24-31 ms je Scan, weil jede der vielen Komponenten mehrere
    # _path_name-Aufrufe bekam - im Spiel ein Ruckler alle 10 Frames.
    unsere = {_pfad(n) for n, _ in _skin.values()}
    comps = []
    mesh_von: dict[int, str] = {}
    global _skin_voll_bald
    if voll:
        quelle = unrealsdk.find_all("SkeletalMeshComponent", exact=False)
    else:
        quelle, fehlt = _skin_kandidaten_schnell()
        if fehlt:
            _skin_voll_bald = True        # Menuefigur/Kopf weg (Levelwechsel, Respawn): neu suchen
    for comp in quelle:
        try:
            mesh = comp.SkeletalMesh
            if mesh is None:
                continue
            mp = _pfad(mesh)
            if mp not in _skin and mp not in unsere and not mp.startswith(SKIN_KOPF_PRAEFIX):
                continue
            if comp.Owner is None or "Default__" in _pfad(comp):
                continue
            mesh_von[id(comp)] = mp
            comps.append(comp)
        except Exception:  # noqa: BLE001 - halb abgebaute Komponenten
            continue
    if voll:
        # Gegenprobe: was haette der Schnellscan (mit den alten Merk-Pfaden) nicht gesehen?
        schnell = {_pfad(c) for c in _skin_kandidaten_schnell()[0]}
        merk: list[tuple[str, str]] = []
        for comp in comps:
            cp = _pfad(comp)
            try:
                besitzer = comp.Owner
                if besitzer.Class.Name not in SKIN_TRAEGER:
                    continue
                # Merken fuer den Schnellscan: Menuefiguren (nicht in der Pawn-Liste) und Koepfe
                if besitzer.Class.Name == "PlayerStandIn":
                    eintrag = ("PlayerStandIn", _pfad(besitzer))
                    if eintrag not in merk:
                        merk.append(eintrag)
                if mesh_von[id(comp)].startswith(SKIN_KOPF_PRAEFIX):
                    merk.append((comp.Class.Name, cp))
                    continue              # Koepfe kommen ab jetzt ueber merk - keine Luecke
            except Exception:  # noqa: BLE001
                continue
            if cp not in schnell and cp not in _skin_luecken:
                _skin_luecken.add(cp)
                logging.info(f"[ZB] Aussehen: LUECKE - nur der Vollscan fand {cp} "
                             f"(Mesh {mesh_von[id(comp)]}, Besitzer {_pfad(comp.Owner)})")
        _skin_merk[:] = merk
        _skin_voll_bald = False
    besitzer_mit_skin: set[str] = set()
    for comp in comps:
        try:
            cpfad, mesh_pfad, besitzer = _pfad(comp), mesh_von[id(comp)], comp.Owner
            if mesh_pfad.startswith(SKIN_KOPF_PRAEFIX):
                continue
            soll = _skin_an and _skin_klasse_von(besitzer, pc, lokal)
            if mesh_pfad in _skin and soll:
                neu, mic = _skin[mesh_pfad]
                # v1.53: nur PFADE merken. Die Materialien sind oft fluechtige Instanzen des Spiels; die
                # gemerkten Huellen zeigten beim Zuruecktauschen auf geloeschte Objekte -> Absturz (v1.52)
                mats = [(m.Class.Name, _pfad(m)) if m is not None else None for m in comp.Materials]
                _skin_getauscht[cpfad] = (mesh_pfad, mats, _pfad(besitzer))
                comp.SetSkeletalMesh(neu, False)
                comp.SetMaterial(0, mic)
                aktion.append(f"getauscht {cpfad}")
                if not voll:
                    _skin_voll_bald = True    # neuer Koerper (Statusmenue, Respawn) = neuer Kopf: suchen
            elif cpfad in _skin_getauscht and not soll:
                alt_pfad, mats, _ = _skin_getauscht.pop(cpfad)
                alt = _find("SkeletalMesh", alt_pfad)          # frisch suchen, nie gemerkte Huellen
                if alt is None:
                    logging.error(f"[ZB] Aussehen: Original-Mesh {alt_pfad} nicht mehr da - {cpfad} bleibt")
                    continue
                comp.SetSkeletalMesh(alt, False)
                weg = 0
                for i, eintrag in enumerate(mats):
                    m = _find(*eintrag) if eintrag else None
                    weg += eintrag is not None and m is None
                    comp.SetMaterial(i, m)                     # None = Standardmaterial des Meshes
                aktion.append(f"zurueck {cpfad}" + (f" ({weg} Material(ien) nicht mehr da)" if weg else ""))
            elif cpfad in _skin_getauscht:
                # das Spiel wickelt unser Material in eigene Instanzen (Schild, Status) - nur ersetzen,
                # wenn es nicht mehr von unserem abstammt
                mic = next((m for n, m in _skin.values() if _pfad(n) == mesh_pfad), None)
                erstes = comp.Materials[0] if len(comp.Materials) else None
                kette, ziel = erstes, _pfad(mic)
                for _ in range(8):
                    if kette is None or _pfad(kette) == ziel:
                        break
                    kette = getattr(kette, "Parent", None)
                if mic is not None and kette is None:
                    comp.SetMaterial(0, mic)
                    aktion.append(f"Material erneut {cpfad}")
            if cpfad in _skin_getauscht:
                besitzer_mit_skin.add(_pfad(besitzer))
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Aussehen: {ex}")
    for comp in comps:   # Koepfe: an getauschten Besitzern aus, sonst wieder an
        try:
            if not mesh_von[id(comp)].startswith(SKIN_KOPF_PRAEFIX):
                continue
            cpfad, besitzer = _pfad(comp), _pfad(comp.Owner)
            if besitzer in besitzer_mit_skin and not comp.HiddenGame:
                comp.SetHidden(True)
                _skin_versteckt[cpfad] = besitzer
                aktion.append(f"Kopf aus {cpfad}")
            elif cpfad in _skin_versteckt and besitzer not in besitzer_mit_skin:
                comp.SetHidden(False)
                del _skin_versteckt[cpfad]
                aktion.append(f"Kopf an {cpfad}")
        except Exception as ex:  # noqa: BLE001
            logging.error(f"[ZB] Aussehen (Kopf): {ex}")
    if aktion:
        logging.info(f"[ZB] Aussehen ({grund}): {len(aktion)} Aenderung(en): {'; '.join(aktion[:6])}")


_skin_zeit = [0.0, 0, 0.0]   # Summe s, Anzahl Scans, laengster Scan s (v1.44: "Spiel fuehlt sich langsamer an")


# zb fps [Sekunden] (v1.51): Frame-Zeiten zwischen zwei Viewport-Ticks. Vergleich eigenes Modell gegen
# Zer0 an derselben Stelle: "zb fps 15", dann "zb skin aus", "zb fps 15", "zb skin an".
_fps_zeiten: list[float] = []
_fps_letzt = 0.0
_fps_ende = 0.0
_fps_name = ""


def fps_start(sekunden: float) -> None:
    global _fps_letzt, _fps_ende, _fps_name
    _fps_zeiten.clear()
    _fps_letzt = 0.0
    _fps_ende = time.perf_counter() + sekunden
    _fps_name = f"Modell {'an' if _skin_an else 'aus (Zer0)'}"
    logging.info(f"[ZB] FPS: Messung {sekunden:.0f} s laeuft ({_fps_name}) - nicht bewegen")


def _fps_tick() -> None:
    global _fps_letzt, _fps_ende
    jetzt = time.perf_counter()
    if _fps_letzt:
        _fps_zeiten.append(jetzt - _fps_letzt)
    _fps_letzt = jetzt
    if jetzt < _fps_ende:
        return
    _fps_ende = 0.0
    z = sorted(_fps_zeiten)
    if len(z) < 10:
        logging.info("[ZB] FPS: zu wenige Frames")
        return
    mittel = sum(z) / len(z)
    eins = z[int(len(z) * 0.99):]                      # die langsamsten 1 %
    logging.info(f"[ZB] FPS ({_fps_name}): {len(z)} Frames, Mittel {1 / mittel:.1f} fps ({1000 * mittel:.2f} ms), "
                 f"Median {1000 * z[len(z) // 2]:.2f} ms, 1%-Low {1 / (sum(eins) / len(eins)):.1f} fps, "
                 f"schlechtester Frame {1000 * z[-1]:.1f} ms")


def _on_viewport_tick(obj: UObject, args: Any, ret: Any, func: Any) -> None:
    global _skin_zaehler, _skin_vollscan_zaehler
    if _fps_ende:
        _fps_tick()
    _skin_zaehler += 1
    if _skin_zaehler < SKIN_TICKS:
        return
    _skin_zaehler = 0
    _skin_vollscan_zaehler += SKIN_TICKS
    voll = _skin_voll_bald or _skin_vollscan_zaehler >= SKIN_VOLLSCAN_TICKS
    if voll:
        _skin_vollscan_zaehler = 0
    t0 = time.perf_counter()
    try:
        _skin_laden()
        skin_scan("tick voll" if voll else "tick", voll=voll)
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Aussehen: {ex}")
    dt = time.perf_counter() - t0
    z = _skin_zeit_voll if voll else _skin_zeit
    z[0] += dt
    z[1] += 1
    z[2] = max(z[2], dt)
    if _skin_zeit[1] and _skin_zeit[1] % 600 == 0 and not voll:
        _skin_zeit_loggen()


_skin_zeit_voll = [0.0, 0, 0.0]   # v1.52: Vollscan (Gegenprobe) getrennt gezaehlt


def _skin_zeit_loggen() -> None:
    for name, z, takt in (("Schnellscan", _skin_zeit, SKIN_TICKS), ("Vollscan", _skin_zeit_voll, SKIN_VOLLSCAN_TICKS)):
        n = max(1, z[1])
        logging.info(f"[ZB] Aussehen-{name}: {z[1]} Scans, im Mittel {1000 * z[0] / n:.2f} ms, "
                     f"laengster {1000 * z[2]:.2f} ms (alle {takt} Frames)")


def skin_befehl(arg: str) -> None:
    global _skin_an
    if arg.startswith("mat"):
        skin_material(arg.split(" ", 1)[1] if " " in arg else "")
        return
    if arg in ("an", "aus"):
        _skin_an = arg == "an"
        skin_scan(f"zb skin {arg}", voll=True)
    _skin_zeit_loggen()
    for cpfad, (alt_pfad, _, besitzer) in _skin_getauscht.items():
        logging.info(f"[ZB] Aussehen: {cpfad} (Besitzer {besitzer}, vorher {alt_pfad})")
    logging.info(f"[ZB] Aussehen: {'an' if _skin_an else 'aus'}, {len(_skin)} Meshes geladen, "
                 f"{len(_skin_getauscht)} getauscht, {len(_skin_versteckt)} Koepfe aus, Klasse {_skin_letzte_klasse}")


def on_enable() -> None:
    register_tracers()
    ensure_seventh_character()
    logging.info(f"[ZB] {CHARACTER_NAME}-Modul v{__version__} aktiviert ({len(TRACE_FUNCS)} Spur-Hooks)")


def on_disable() -> None:
    global _skin_an
    try:
        _skin_an = False
        skin_scan("Modul deaktiviert", voll=True)   # Zer0s Mesh und Kopf zurueck
    except Exception as ex:  # noqa: BLE001
        logging.error(f"[ZB] Aussehen zuruecksetzen: {ex}")
    _skin_an = True
    frieren_aus("Modul deaktiviert")
    krit_aus("Modul deaktiviert")
    unregister_tracers()
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
BAUM_TITEL = ("HINDSIGHT", "REWIND", "OVERCLOCK")
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
        case "skin":
            # zb skin [an|aus|mat zer0|klassenmod] - eigenes Modell am Chronomaster (v1.41, mat v1.43)
            skin_befehl(" ".join(args.args))
        case "fps":
            # zb fps [Sekunden] - Frame-Zeiten messen (v1.51)
            fps_start(float(args.args[0]) if args.args else 15.0)
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
                    "feuerrate": A_FEUERRATE, "schildladen": A_SCHILDLADEN}.get(name.lower(), name)
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
        case "krit":
            # zb krit an [SEKUNDEN] | aus - Guaranteed Crits von Hand (v1.72)
            if args.args and args.args[0] == "aus":
                krit_aus("Befehl")
            else:
                krit_an(float(args.args[1]) if len(args.args) > 1 else 10.0, "Befehl")
        case "frieren":
            # zb frieren ki|tick|pop|halten|aus [RADIUS_M] - Spike Time Freeze (v1.70)
            frieren(args.args[0] if args.args else "ki", float(args.args[1]) if len(args.args) > 1 else 25.0)
        case "fenster":
            # zb fenster - wo die Restzeit des Fensters steht (Diagnose Kurs halten, v0.89)
            fenster_zeigen()
        case "schaden":
            # zb schaden [reset] - was filtert der Schadens-Hook (v0.85)
            if args.args and args.args[0] == "reset":
                schaden_zuruecksetzen()
            else:
                schaden_zeigen()
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
                " | props pawn|pc|weapon FILTER | funcs KLASSE [FILTER] | enum [FILTER] | namen | gegner [RADIUS] | ziel [N] [ABSTAND] | schaden [reset] | ffyl | fenster | holo [SEKUNDEN] | koop selbst|aus | schatten [los] | effekte an|aus|log|test | immun [S] | ammo"
                " | xp N | respec | cash N | fasttot (die letzten vier: Testhilfen, nur Chronomaster)"
            )


zb.add_argument("action", choices=["status", "legen", "zuenden", "ende", "loeschen", "bombe", "meshes", "rang", "wirkung", "attr", "props", "funcs", "enum", "namen", "gegner", "ziel", "schaden", "ffyl", "fasttot", "fenster", "frieren", "krit", "holo", "koop", "schatten", "effekte", "immun", "ammo", "spur", "kopie", "baum", "pakete", "askill", "skill", "xp", "respec", "cash", "granate", "icons", "skin", "fps"])
zb.add_argument("args", nargs="*")

build_mod(
    name=CHARACTER_NAME,
    description="A new 7th Vault Hunter, the Timekeeper, with the Action Skill Time Bomb: throw it, fight, return - to where it landed, with the health, shield and ammo you had. Three new skill trees.",
    supported_games=Game.BL2,
    on_enable=on_enable,
    on_disable=on_disable,
)
