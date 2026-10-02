# Chronomaster — a 7th Vault Hunter for Borderlands 2

**Class: Timekeeper · Action Skill: Time Bomb**

A new playable character with his own tile in character select, his own save, a new Action Skill and three skill trees (36 skills). The other six Vault Hunters are not changed.

> **Test version** — balance is not tuned yet. Feedback welcome!

## The Time Bomb

*What you did stays done, what happened to you gets undone.* (Inspired by Black Ops 2 Zombies.)

1. **Throw** the bomb with your Action Skill key. Where it lands, it saves your health, shield and magazine.
2. **Fight** for up to 20 seconds.
3. **Press again** to return to the bomb with the saved health, shield and magazine. Kills, damage and loot stay. Cooldown: 35 s (half if the bomb expires unused).

## Skill trees

- **Hindsight** — rewards what happens while the bomb is out.
- **Rewind** — makes the return stronger (healing, explosions, ally support).
- **Detour** — rewards going far from the bomb before you return.

**All 36 skills with their numbers: [SKILLS.md](SKILLS.md)**, readable without installing anything.

## Requirements

- **Borderlands 2** on PC.
- **Python SDK / Willow2 Mod Manager 3.x** from Nexus Mods. Once installed, the main menu shows a *Mods* entry.
- **Mechromancer Pack (Gaige) DLC**, as far as we know — the 7th character slot is built from its data. Included in the Game of the Year Edition.

## Installation

1. Download **`Chronomaster-v1.54.zip`** from the [GitHub Releases](https://github.com/zombierrr-boss/chronomaster/releases) page and unzip it. You get two folders: `chronomaster` and `CookedPCConsole`.
   *Downloaded the whole project instead (Code → Download ZIP)? Then the `chronomaster` folder is inside its `sdk` folder — ignore the long outer folder name. That download has no model files; get them from the release.*
2. Copy **the `chronomaster` folder** into `…\Borderlands 2\sdk_mods\`. It must end up like this:
   ```
   …\Borderlands 2\sdk_mods\chronomaster\__init__.py
   ```
3. **Model and portrait (optional):** with the game closed, copy the four `Chronomaster*.upk` files from the `CookedPCConsole` folder into `…\Borderlands 2\WillowGame\CookedPCConsole\`. Without them, the Chronomaster looks like Zer0.
4. Start the game, enable **Chronomaster** in the *Mods* menu and **restart the game once**.
5. Create a new character on the 7th tile.

To uninstall, disable the mod and restart, then delete the four `Chronomaster*.upk` files from `CookedPCConsole`. Don't load a Chronomaster save while the mod is disabled.

## Known limitations

- The model is a placeholder.
- In co-op, other players only see the model if they installed the model files too.
- Co-op, a full playthrough from level 1 and other character mods are untested.
- Grenade skills scale with your grenade's card damage — grenades without a damage number make them weak.

## Feedback

Balance, ideas, bugs — everything is welcome: open an issue on [GitHub](https://github.com/zombierrr-boss/chronomaster/issues) or comment in the Reddit thread. (Not on Nexus Mods yet — that comes after this test phase.) For crashes, please attach `…\Borderlands 2\Binaries\Win32\Plugins\unrealsdk.log` — copy it before restarting the game.

## Credits & License

Made by **zombierrr**. Thanks to **LJBreeze** — the Nisha mod (Nexus #654) showed that a 7th character slot is possible. The model packages were built with **[bl2-part-pipeline](https://github.com/corporateweapon/bl2-part-pipeline)** by **44M0N**.

MIT License for the code — use, change and reupload freely, as long as you credit zombierrr. See [LICENSE](LICENSE).
The model files (`Chronomaster*.upk`) are **not** covered by the MIT License: they are built on Zer0's model and skeleton from Borderlands 2.
*Borderlands 2 and Zer0 are property of Gearbox Software / 2K. This is an unofficial fan mod.*
