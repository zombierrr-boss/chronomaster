# Chronomaster — a 7th Vault Hunter for Borderlands 2

**Class: Timekeeper · Action Skill: Time Bomb**

A new playable character with his own tile in character select, his own save, a new Action Skill and three skill trees (36 skills). The other six Vault Hunters are not changed.

> **Test version.** All 36 skills and his own class mods work, but the balance is not tuned yet. Feedback welcome!

## The Time Bomb

*What you did stays done, what happened to you gets undone.* (Inspired by Black Ops 2 Zombies.)

1. **Throw** the bomb with your Action Skill key. Where it lands, it saves your health, shield and magazine.
2. **Fight** for up to 20 seconds.
3. **Press again** to return to the bomb with the saved health, shield and magazine. Kills, damage and loot stay. Cooldown: 35 s (half if the bomb expires unused).

## Skill trees

- **Hindsight** rewards what happens while the bomb is out: Haste Stacks, Paradox, Return to Sender. Capstone *Time Freeze* freezes every enemy where the bomb lands.
- **Rewind** makes the return stronger: healing, Borrowed Health, Guaranteed Crits, explosions. Capstone *Shadow Anchor* lets you jump back even without a bomb.
- **Overclock** is about more shots, more ammo and more grenades: Echo Bullet, Dimensional Loop, Time Loop, Infinite. Capstone *Unspent Time* makes every kill explode in your weapon's element.

## Class mods

Seven class mods of his own, each boosting **three skills that work together** (for example *Gunslinger*: Echo Bullet, Dimensional Loop and Haste Stacks). They drop from enemies and chests, are sold at Zed's vending machines and come as mission rewards, just like other class mods. **Legendary** versions boost five skills and add a unique effect, such as triple shots or exploding holograms.

**All 36 skills, all class mods and their numbers: [SKILLS.md](SKILLS.md)**, readable without installing anything.

## Requirements

- **Borderlands 2** on PC.
- **Python SDK / Willow2 Mod Manager 3.x** from Nexus Mods, **kept up to date**. Once installed, the main menu shows a *Mods* entry. Tested with unrealsdk 3.2 / pyunrealsdk 1.10. With an older SDK, the Action Skill may not work.
- **Mechromancer Pack (Gaige) DLC**, as far as we know. The 7th character slot is built from its data. It's included in the Game of the Year Edition.

## Installation

1. Download the latest **`Chronomaster-v….zip`** from [Nexus Mods](https://www.nexusmods.com/borderlands2/mods/680) or the [GitHub Releases](https://github.com/zombierrr-boss/chronomaster/releases) page and unzip it. You get two folders: `chronomaster` and `CookedPCConsole`.
   *Downloaded the whole project instead (Code → Download ZIP)? Then the `chronomaster` folder is inside its `sdk` folder. Ignore the long outer folder name. That download has no model files, so get them from the release.*
2. Copy **the `chronomaster` folder** into `…\Borderlands 2\sdk_mods\`. It must end up like this:
   ```
   …\Borderlands 2\sdk_mods\chronomaster\__init__.py
   ```
3. **Model and portrait (optional):** with the game closed, copy the four `Chronomaster*.upk` files from the `CookedPCConsole` folder into `…\Borderlands 2\WillowGame\CookedPCConsole\`. Without them, the Chronomaster looks like Zer0.
4. Start the game, enable **Chronomaster** in the *Mods* menu and **restart the game once**.
5. Create a new character on the 7th tile.

**Updating from v1.54?** The skill trees changed a lot: thirteen skills were replaced, and the third tree is now called Overclock. Reset your skill points at a Quick-Change station after updating.

To uninstall, disable the mod and restart, then delete the four `Chronomaster*.upk` files from `CookedPCConsole`. Don't load a Chronomaster save while the mod is disabled.

**Class mods are saved with the help of a small file** in `…\Borderlands 2\sdk_mods\_chronomaster_saves\`. Don't delete that folder, or your Chronomaster class mods are lost the next time you load.

## Known limitations

- The model is a placeholder. The blue parts (hourglass, buttons) are on purpose, not a missing texture.
- In co-op, other players only see the model if they installed the model files too.
- Co-op, a full playthrough from level 1 and other character mods are untested.
- There is no option to create the Chronomaster at level 30 yet.
- **Don't put Chronomaster class mods in the bank or Claptrap's stash.** They are only kept while you carry them (equipped or in your backpack).
- Class mods from DLC sources (e.g. Tiny Tina) are still Zer0's. In co-op with a real Zer0, he may find Chronomaster class mods instead of his own.
- The holograms (Time Capsule, Afterimage) still look like Zer0.
- Grenade skills scale with your grenade's card damage. Grenades without a damage number make them weak.

## Feedback

Balance, ideas, bugs: everything is welcome. Comment on [Nexus Mods](https://www.nexusmods.com/borderlands2/mods/680), open an issue on [GitHub](https://github.com/zombierrr-boss/chronomaster/issues) or comment in the Reddit thread. For crashes or skills that do nothing, please attach `…\Borderlands 2\Binaries\Win32\Plugins\unrealsdk.log`. Copy it before restarting the game, because it is overwritten at every start.

## Credits & License

Made by **zombierrr**. Thanks to **LJBreeze**: the Nisha mod (Nexus #654) showed that a 7th character slot is possible. Thanks to **inlecebra** for many of the new skill ideas. The model packages were built with **[bl2-part-pipeline](https://github.com/corporateweapon/bl2-part-pipeline)** by **44M0N**.

MIT License for the code: use, change and reupload freely, as long as you credit zombierrr. See [LICENSE](LICENSE).
The model files (`Chronomaster*.upk`) are **not** covered by the MIT License: they are built on Zer0's model and skeleton from Borderlands 2.
*Borderlands 2 and Zer0 are property of Gearbox Software / 2K. This is an unofficial fan mod.*
