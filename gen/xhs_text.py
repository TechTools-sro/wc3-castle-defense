"""Names and test table of the 12 X Hero Siege champions' abilities: gen/xhs_data.py holds their numbers, gen/xhs_tips.py what a player reads.

SKILLS: ability id -> (name, kind, order, target, expected effect)
  kind    P passive or aura, A has a button to press
  order   the order string the self-test casts it with; "" = no cast (passive)
  target  none, enemy (a unit), point, ally, self, corpse
  effect  what the self-test must see after the cast: damage, heal, summon:<unit type>:<count>, buff:<buff id on him>, foebuff, allybuff, images:<count>, morph:<unit type>, split, toggle
"""

SKILLS = {
    # Dryad (Tyrande): every spear she throws is native
    "A028": ("Evasion", "P", "", "", ""),
    "A02A": ("Multiple Arrows", "P", "", "", ""),
    "A000": ("Critical Arrows", "P", "", "", ""),
    "A029": ("Trueshot Aura", "P", "", "", ""),
    "AOae": ("Endurance Aura", "P", "", "", ""),
    "ACvs": ("Envenomed Spears", "P", "", "", ""),
    "A027": ("Spell Immunity", "P", "", "", ""),
    # Mountain King
    "AHtb": ("Storm Bolt", "A", "thunderbolt", "enemy", "damage"),
    "AHtc": ("Thunder Clap", "A", "thunderclap", "none", "damage"),
    "AHbh": ("Bash", "P", "", "", ""),
    "AHav": ("Avatar", "A", "avatar", "none", "buff:BHav"),
    "A005": ("Muradin's Hammer", "P", "", "", ""),
    "A01K": ("Thunder Spirit", "P", "", "", ""),
    "A017": ("Lightning Shield", "A", "immolation", "none", "damage"),
    # Tauren Chieftain
    "AOsh": ("Shockwave", "A", "shockwave", "point", "damage"),
    "AOws": ("War Stomp", "A", "stomp", "none", "damage"),
    "A00W": ("Pulverize", "P", "", "", ""),
    "A00E": ("Lightning Stroke", "A", "fanofknives", "none", "damage"),
    "ACro": ("Battle Roar", "A", "roar", "none", "buff:B00N"),
    "AOre": ("Reincarnation", "P", "", "", ""),
    "A03Q": ("Battle Roar", "A", "roar", "none", "buff:B00N"),
    # Pit Lord
    "ANrf": ("Rain of Fire", "A", "rainoffire", "point", "damage"),
    "AOw2": ("War Stomp", "A", "stomp", "none", "damage"),
    "ANca": ("Cleaving Attack", "P", "", "", ""),
    "ANdo": ("Doom", "A", "doom", "enemy", "damage"),
    "AUau": ("Unholy Aura", "P", "", "", ""),
    "A02E": ("Howl of Terror", "A", "howlofterror", "none", "foebuff:BNht"),
    "A019": ("Finger of Death", "A", "fingerofdeath", "enemy", "damage"),
    # Archmage
    "AHbz": ("Blizzard", "A", "blizzard", "point", "damage"),
    "AHwe": ("Water Elemental", "A", "waterelemental", "none", "summon:hwt3:2"),
    "A003": ("Frost Bolt", "A", "thunderbolt", "enemy", "damage"),
    "AEsf": ("Starfall", "A", "starfall", "none", "damage"),
    "A00P": ("Debilitation Aura", "P", "", "", ""),
    "ACam": ("Anti-magic Shield", "A", "antimagicshell", "self", "buff:B00G"),
    "A02Y": ("Water Shield", "A", "frostarmor", "ally", "allybuff:B009"),
    # Lich
    "AUfn": ("Frost Nova", "A", "frostnova", "enemy", "damage"),
    "A04C": ("Breath of Frost", "A", "breathoffrost", "point", "damage"),
    "ANfa": ("Frost Arrows", "A", "", "", ""),
    "A035": ("Frost Beast", "A", "summongrizzly", "none", "summon:n00X:2"),
    "AUfu": ("Frost Armor", "A", "frostarmor", "ally", "allybuff:BUfa"),
    "A01L": ("Frost Frenzy", "A", "unholyfrenzy", "ally", "allybuff:B006"),
    "A006": ("Frost Chaos", "A", "deathanddecay", "point", "damage"),
    # Paladin (Uther)
    "A00M": ("Healing Wave", "A", "healingwave", "ally", "heal"),
    "A00H": ("Howl of Weakness", "A", "howlofterror", "none", "foebuff:Bcri"),
    "A00A": ("Fan of Light", "A", "fanofknives", "none", "damage"),
    "A00Y": ("Pure Light", "A", "spiritwolf", "none", "summon:e006:1"),
    "AHad": ("Devotion Aura", "P", "", "", ""),
    "ANta": ("Taunt", "A", "taunt", "none", "toggle"),
    "A010": ("Light Frenzy", "A", "cripple", "ally", "allybuff:B002"),
    # Blademaster
    "AOwk": ("Wind Walk", "A", "windwalk", "none", "buff:BOwk"),
    "AOcr": ("Critical Strike", "P", "", "", ""),
    "AOmi": ("Mirror Image", "A", "mirrorimage", "none", "images:6"),
    "AOww": ("Bladestorm", "A", "whirlwind", "none", "damage"),
    "A045": ("War Drums", "P", "", "", ""),
    "A04N": ("Berserk", "A", "berserk", "none", "buff:Bbsk"),
    "A01F": ("Partition", "A", "elementalfury", "none", "split"),
    # Beastmaster
    "ANsg": ("Summon Bear", "A", "summongrizzly", "none", "summon:n002:2"),
    "ACs7": ("Feral Spirit", "A", "spiritwolf", "none", "summon:n005:4"),
    "ANsw": ("Summon Hawk", "A", "summonwareagle", "none", "summon:n008:2"),
    "Arsp": ("Stampede", "A", "stampede", "point", "damage"),
    "AEah": ("Thorns Aura", "P", "", "", ""),
    "A009": ("Spirit Pig", "A", "wateryminion", "none", "summon:nspp:1"),
    "A02W": ("Terror Wolf", "A", "elementalfury", "none", "split"),
    # Crypt Lord
    "AUim": ("Impale", "A", "impale", "point", "damage"),
    "AUts": ("Spiked Carapace", "P", "", "", ""),
    "AUcb": ("Carrion Beetles", "A", "carrionscarabs", "corpse", "summon:u001:1"),
    "AUls": ("Locust Swarm", "A", "Locustswarm", "none", "damage"),
    "A020": ("Poison Sting", "P", "", "", ""),
    "A024": ("Anub'arak's Claw", "A", "berserk", "none", "buff:B005"),
    "A00Q": ("Burrow Impale", "A", "starfall", "none", "damage"),
    # Demon Hunter
    "AEim": ("Immolation", "A", "immolation", "none", "damage"),
    "A00K": ("Negative Energy", "A", "fingerofdeath", "enemy", "damage"),
    "AEev": ("Evasion", "P", "", "", ""),
    "AEme": ("Metamorphosis", "A", "metamorphosis", "none", "morph:Edmm"),
    "AUav": ("Vampiric Aura", "P", "", "", ""),
    "ACr1": ("Roar", "A", "roar", "none", "toggle"),
    "A02K": ("Resistant Skin", "P", "", "", ""),
    # Priestess of the Moon
    "AOcl": ("Chain Lightning", "A", "chainlightning", "enemy", "damage"),
    "ANwm": ("Watery Minion", "A", "wateryminion", "none", "summon:nsns:2"),
    "ANfl": ("Forked Lightning", "A", "forkedlightning", "enemy", "damage"),
    "A01M": ("Monsoon", "A", "monsoon", "point", "damage"),
    "AEar": ("Trueshot Aura", "P", "", "", ""),
    "ACrj": ("Rejuvenation", "A", "rejuvination", "ally", "heal"),
    "A02U": ("Lightning Chaos", "A", "deathanddecay", "point", "damage"),
}

HERO_TIPS = {
    "H007": "Throws spears at many enemies at once.",
    "Hmkg": "Melee tank. Stuns and clears around him.",
    "Otch": "Melee. Stomps and shockwaves, rises again.",
    "Nplh": "Melee fire. Cleaves, doom and fire rain.",
    "Hamg": "Mage. Blizzard, starfall, water elementals.",
    "Ulic": "Frost mage. Nova, frost beast, slows.",
    "Hpal": "Support. Heals and strengthens his team.",
    "Obla": "Melee. Crits, images, splits into three.",
    "Nbst": "Summoner. Bears, wolves, hawks.",
    "Ucrl": "Melee swarm. Impale, beetles, locusts.",
    "Edem": "Melee, then a ranged demon. Burns around him.",
    "Emoo": "Ranged lightning. Chains and storms.",
}
