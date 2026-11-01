"""Our own short text and test table for the 12 X Hero Siege champions: gen/xhs_data.py holds their numbers, this file what a player reads.

SKILLS: ability id -> (name, kind, text per level, order, target, expected effect)
  kind    P passive or aura, A has a button to press
  text    {A}..{I} = the ability's Data field for that level, {A%} as a percent, {Dur} {Cool} {Area} {Rng} its other fields. The game fills
          them in from the real data, so a tooltip cannot disagree with the ability.
  order   the order string the self-test casts it with; "" = no cast (passive)
  target  none, enemy (a unit), point, ally, self, corpse
  effect  what the self-test must see after the cast: damage, heal, summon:<unit type>:<count>, buff:<buff id on him>, foebuff, allybuff, images:<count>, morph:<unit type>, split, toggle
"""

SKILLS = {
    # Dryad (Tyrande): every spear she throws is native
    "A028": ("Evasion", "P", "{A%}% chance to avoid an attack.", "", "", ""),
    "A02A": ("Multiple Arrows", "P", "Every attack also throws spears at other enemies nearby, all with her attack's damage. More every level.", "", "", ""),
    "A000": ("Critical Arrows", "P", "{A}% chance for {B} times damage.", "", "", ""),
    "A029": ("Trueshot Aura", "P", "+{A%}% ranged damage near you.", "", "", ""),
    "AOae": ("Endurance Aura", "P", "+{A%}% move speed, +{B%}% attack speed near you.", "", "", ""),
    "ACvs": ("Envenomed Spears", "P", "Her hits poison: {A} damage per second for {Dur} s, and slow.", "", "", ""),
    "A027": ("Spell Immunity", "P", "Hero level 20: immune to spells.", "", "", ""),
    # Mountain King
    "AHtb": ("Storm Bolt", "A", "{A} damage and a {Dur} s stun.", "thunderbolt", "enemy", "damage"),
    "AHtc": ("Thunder Clap", "A", "{A} damage around you, slows.", "thunderclap", "none", "damage"),
    "AHbh": ("Bash", "P", "{A}% chance: +{C} damage and a stun.", "", "", ""),
    "AHav": ("Avatar", "A", "{Dur} s: +{A} armor, +{B} HP, +{C} damage, spell immune.", "avatar", "none", "buff:BHav"),
    "A005": ("Muradin's Hammer", "P", "Melee allies near you heal {A%}% of their damage.", "", "", ""),
    "A01K": ("Thunder Spirit", "P", "Top speed. From hero level 20 Storm Bolt and Thunder Clap strike twice.", "", "", ""),
    "A017": ("Lightning Shield", "A", "Hero level 20: {A} damage per second around you.", "immolation", "none", "damage"),
    # Tauren Chieftain
    "AOsh": ("Shockwave", "A", "{A} damage in a line.", "shockwave", "point", "damage"),
    "AOws": ("War Stomp", "A", "{A} damage around you and a {Dur} s stun.", "stomp", "none", "damage"),
    "A00W": ("Pulverize", "P", "{A}% chance: {B} damage around the target.", "", "", ""),
    "A00E": ("Lightning Stroke", "A", "{A} damage to enemies around you.", "fanofknives", "none", "damage"),
    "ACro": ("Battle Roar", "A", "More damage and armor for a while.", "roar", "none", "buff:B00N"),
    "AOre": ("Reincarnation", "P", "Hero level 20: rises again after {A} s, every {Cool} s.", "", "", ""),
    "A03Q": ("Battle Roar", "A", "Hero level 20: +{A%}% damage, +{B} armor; Stomp and Shockwave strike twice while it lasts.", "roar", "none", "buff:B00N"),
    # Pit Lord
    "ANrf": ("Rain of Fire", "A", "{A} waves in an area, {B} damage each.", "rainoffire", "point", "damage"),
    "AOw2": ("War Stomp", "A", "{A} damage around you and a {Dur} s stun.", "stomp", "none", "damage"),
    "ANca": ("Cleaving Attack", "P", "{A%}% of your damage hits enemies near the target.", "", "", ""),
    "ANdo": ("Doom", "A", "{A} damage per second on a non-hero; a demon rises when it dies.", "doom", "enemy", "damage"),
    "AUau": ("Unholy Aura", "P", "+{A%}% move speed, +{B%}% life regeneration near you.", "", "", ""),
    "A02E": ("Howl of Terror", "A", "Enemies near you deal {A%}% less damage.", "howlofterror", "none", "foebuff:BNht"),
    "A019": ("Finger of Death", "A", "Hero level 20: {C} damage on one enemy.", "fingerofdeath", "enemy", "damage"),
    # Archmage
    "AHbz": ("Blizzard", "A", "{A} waves in an area, {B} damage each.", "blizzard", "point", "damage"),
    "AHwe": ("Water Elemental", "A", "Summons {A} water elementals.", "waterelemental", "none", "summon:hwt3:2"),
    "A003": ("Frost Bolt", "A", "{A} damage and a {Dur} s stun.", "thunderbolt", "enemy", "damage"),
    "AEsf": ("Starfall", "A", "Channel: {A} damage to enemies in a big area, again and again.", "starfall", "none", "damage"),
    "A00P": ("Debilitation Aura", "P", "Enemies near you have {A} armor.", "", "", ""),
    "ACam": ("Anti-magic Shield", "A", "Shields a unit from spells.", "antimagicshell", "self", "buff:B00G"),
    "A02Y": ("Water Shield", "A", "Hero level 20: +{B} armor on an ally for {A} s.", "frostarmor", "ally", "allybuff:B009"),
    # Lich
    "AUfn": ("Frost Nova", "A", "{B} damage to the target, {A} around it, slows.", "frostnova", "enemy", "damage"),
    "A04C": ("Breath of Frost", "A", "{A} damage in a cone, then {E} per second.", "breathoffrost", "point", "damage"),
    "ANfa": ("Frost Arrows", "A", "Your hits deal +{A} damage and slow. Autocast.", "", "", ""),
    "A035": ("Frost Beast", "A", "Summons a Frost Beast for {Dur} s.", "summongrizzly", "none", "summon:n00X:2"),
    "AUfu": ("Frost Armor", "A", "+{B} armor on an ally. Autocast.", "frostarmor", "ally", "allybuff:BUfa"),
    "A01L": ("Frost Frenzy", "A", "A unit attacks {A%}% faster, but loses {B} HP per second.", "unholyfrenzy", "ally", "allybuff:B006"),
    "A006": ("Frost Chaos", "A", "Hero level 20: {A%}% of max HP per second in an area.", "deathanddecay", "point", "damage"),
    # Paladin (Uther)
    "A00M": ("Healing Wave", "A", "Heals {A} and bounces {B} times.", "healingwave", "ally", "heal"),
    "A00H": ("Howl of Weakness", "A", "Enemies near you deal {A%}% less damage and lose {B} armor.", "howlofterror", "none", "foebuff:Bcri"),
    "A00A": ("Fan of Light", "A", "{A} damage to enemies around you.", "fanofknives", "none", "damage"),
    "A00Y": ("Pure Light", "A", "Summons an invulnerable sphere of light for {Dur} s.", "spiritwolf", "none", "summon:e006:1"),
    "AHad": ("Devotion Aura", "P", "+{A} armor near you.", "", "", ""),
    "ANta": ("Taunt", "A", "Enemies near you attack you.", "taunt", "none", "toggle"),
    "A010": ("Light Frenzy", "A", "Hero level 20: a unit attacks and moves far faster, hits harder and its cooldowns reset.", "cripple", "ally", "allybuff:B002"),
    # Blademaster
    "AOwk": ("Wind Walk", "A", "Invisible, +{B%}% speed, next hit +{C} damage.", "windwalk", "none", "buff:BOwk"),
    "AOcr": ("Critical Strike", "P", "{A}% chance for {B} times damage.", "", "", ""),
    "AOmi": ("Mirror Image", "A", "{A} images of you, they deal {B%}% damage.", "mirrorimage", "none", "images:6"),
    "AOww": ("Bladestorm", "A", "{Dur} s: {A} damage per second around you, spell immune.", "whirlwind", "none", "damage"),
    "A045": ("War Drums", "P", "Attack damage bonus near you, more with every level.", "", "", ""),
    "A04N": ("Berserk", "A", "You attack {B%}% faster and take {C%}% more damage.", "berserk", "none", "buff:Bbsk"),
    "A01F": ("Partition", "A", "Hero level 20: you split into 3 warriors. If one lives you come back.", "elementalfury", "none", "split"),
    # Beastmaster
    "ANsg": ("Summon Bear", "A", "Summons {A} bears.", "summongrizzly", "none", "summon:n002:2"),
    "ACs7": ("Feral Spirit", "A", "Summons {B} wolves for {Dur} s.", "spiritwolf", "none", "summon:n005:4"),
    "ANsw": ("Summon Hawk", "A", "Summons {A} hawks with true sight.", "summonwareagle", "none", "summon:n008:2"),
    "Arsp": ("Stampede", "A", "{A} beasts per second run through an area, {C} damage each.", "stampede", "point", "damage"),
    "AEah": ("Thorns Aura", "P", "Attackers near you take {A%}% of the damage back.", "", "", ""),
    "A009": ("Spirit Pig", "A", "Summons {A} spirit pig.", "wateryminion", "none", "summon:nspp:1"),
    "A02W": ("Terror Wolf", "A", "Hero level 20: you become a Terror Wolf for a while.", "elementalfury", "none", "split"),
    # Crypt Lord
    "AUim": ("Impale", "A", "{C} damage in a line, throws enemies up.", "impale", "point", "damage"),
    "AUts": ("Spiked Carapace", "P", "+{C} armor, attackers take {A%}% back.", "", "", ""),
    "AUcb": ("Carrion Beetles", "A", "Raises a beetle from a corpse. Autocast.", "carrionscarabs", "corpse", "summon:u001:1"),
    "AUls": ("Locust Swarm", "A", "{A} locusts attack enemies around you and bring you life.", "Locustswarm", "none", "damage"),
    "A020": ("Poison Sting", "P", "Your hits poison: {A} damage per second, and slow.", "", "", ""),
    "A024": ("Anub'arak's Claw", "A", "You move {A%}% and attack {B%}% faster.", "berserk", "none", "buff:B005"),
    "A00Q": ("Burrow Impale", "A", "Hero level 20: {A} damage again and again to ground enemies around you.", "starfall", "none", "damage"),
    # Demon Hunter
    "AEim": ("Immolation", "A", "{A} damage per second around you, costs mana.", "immolation", "none", "damage"),
    "A00K": ("Negative Energy", "A", "{C} damage and a {Dur} s stun.", "fingerofdeath", "enemy", "damage"),
    "AEev": ("Evasion", "P", "{A%}% chance to avoid an attack.", "", "", ""),
    "AEme": ("Metamorphosis", "A", "{Dur} s demon form: ranged, +{E} HP, top speed.", "metamorphosis", "none", "morph:Edmm"),
    "AUav": ("Vampiric Aura", "P", "Allies near you heal {A%}% of their damage.", "", "", ""),
    "ACr1": ("Roar", "A", "More damage for a while.", "roar", "none", "toggle"),
    "A02K": ("Resistant Skin", "P", "Hero level 20: spells hurt you less.", "", "", ""),
    # Priestess of the Moon
    "AOcl": ("Chain Lightning", "A", "{A} damage, jumps to {B} enemies.", "chainlightning", "enemy", "damage"),
    "ANwm": ("Watery Minion", "A", "Summons {A} water minions.", "wateryminion", "none", "summon:nsns:2"),
    "ANfl": ("Forked Lightning", "A", "{A} damage to {B} enemies in a cone.", "forkedlightning", "enemy", "damage"),
    "A01M": ("Monsoon", "A", "Lightning strikes an area for {Dur} s, {A} damage each.", "monsoon", "point", "damage"),
    "AEar": ("Trueshot Aura", "P", "+{A%}% ranged damage near you.", "", "", ""),
    "ACrj": ("Rejuvenation", "A", "Heals {A} over time.", "rejuvination", "ally", "heal"),
    "A02U": ("Lightning Chaos", "A", "Hero level 20: {A%}% of max HP per second in an area.", "deathanddecay", "point", "damage"),
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
