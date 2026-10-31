import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from mpq import GameData, Archive
game = sys.argv[1]; out = sys.argv[2]
gd = GameData(game)
names = ["Scripts\\common.j", "Scripts\\Blizzard.j", "Scripts\\common.ai",
         "Units\\UnitData.slk", "Units\\UnitBalance.slk", "Units\\UnitWeapons.slk", "Units\\UnitAbilities.slk",
         "Units\\UnitUI.slk", "Units\\UnitMetaData.slk", "Units\\AbilityData.slk", "Units\\AbilityMetaData.slk",
         "Units\\ItemData.slk", "Units\\DestructableData.slk", "Units\\UpgradeData.slk",
         "Units\\NeutralUnitStrings.txt", "Units\\CampaignUnitStrings.txt", "Units\\HumanUnitStrings.txt",
         "Units\\OrcUnitStrings.txt", "Units\\UndeadUnitStrings.txt", "Units\\NightElfUnitStrings.txt",
         "Units\\NeutralUnitFunc.txt", "Units\\CampaignUnitFunc.txt", "Units\\NeutralAbilityStrings.txt",
         "Units\\CommonAbilityStrings.txt", "Units\\NeutralAbilityFunc.txt", "Units\\ItemStrings.txt",
         "Units\\HumanUnitFunc.txt", "Units\\OrcUnitFunc.txt", "Units\\UndeadUnitFunc.txt", "Units\\NightElfUnitFunc.txt",
         "TerrainArt\\Terrain.slk", "TerrainArt\\CliffTypes.slk", "Doodads\\Doodads.slk",
         "UI\\MiscData.txt", "UI\\WorldEditStrings.txt", "UI\\TriggerData.txt"]
os.makedirs(out, exist_ok=True)
for n in names:
    d = gd.read(n)
    if d is None:
        print("MISSING", n); continue
    open(os.path.join(out, n.replace("\\", "_")), "wb").write(d)
    print("ok", n, len(d))
