
# Manual Data provided by User (Detailed)
ARC_DATA = {
  "snitch": {
    "names": {
      "en": "Snitch",
      "de": "Spitzel / Petze"
    },
    "tier": 1,
    "type": "Aufklärungsdrohne",
    "threat_level": "Strategisch Hoch (Verstärkungsruf)",
    "description": "Schwebende Drohne mit 'Scheibenwischer'-Flügeln. Fungiert als sensorischer Knotenpunkt. Bei Entdeckung (Laser-Kontakt) wird sofort Verstärkung gerufen.",
    "drops": ["Snitch Scanner", "Sensors", "ARC Synthetic Resin"],
    "weak_points": ["Antennen ('Wischerblätter')", "Zentrale Linse"],
    "tactic": "Alpha-Strike: Sofort mit maximalem Schaden zerstören, bevor der Ruf vollendet ist. Alternativ: 'Snitch Scanner' Gadget zur Ablenkung nutzen."
  },
  "tick": {
    "names": {
      "en": "Tick",
      "de": "Zecke"
    },
    "tier": 1,
    "type": "Boden-Schwarmeinheit",
    "threat_level": "Niedrig (Hoch in Schwärmen)",
    "description": "Kleine, spinnenartige Maschinen. Operieren in Rudeln, springen Spieler an und klammern sich fest (Damage over Time).",
    "drops": ["Tick Pod", "ARC Alloy"],
    "weak_points": ["Gesamter Körper (geringe HP)"],
    "tactic": "Nahkampf (One-Hit), Ausweichrolle beim Sprunggeräusch, Schrotflinten für Gruppen. Wenn festgeklammert: Teambeschuss oder Interaktionstaste hämmern."
  },
  "pop": {
    "names": {
      "en": "Pop",
      "de": "Platzer"
    },
    "tier": 1,
    "type": "Boden-Kamikaze",
    "threat_level": "Mittel",
    "description": "Kugelförmige Einheit, die auf Spieler zurollt und explodiert. Kündigt sich durch schnelles Ticken an.",
    "drops": ["Pop Trigger", "Crude Explosives"],
    "weak_points": ["Zentraler Sprengstoffkern"],
    "tactic": "Auf Distanz halten. In der Nähe von anderen ARCs zur Explosion bringen (Kettenreaktion). Niemals im Nahbereich bekämpfen."
  },
  "spotter": {
    "names": {
      "en": "Spotter",
      "de": "Späher"
    },
    "tier": 1,
    "type": "Support-Drohne",
    "threat_level": "Indirekt Hoch",
    "description": "Winzige Flugdrohne. Greift nicht direkt an, sondern markiert Spieler per Laser ('Line-of-Sight') für den Bombardier. Ermöglicht Artilleriefeuer über Hindernisse und extreme Distanzen hinweg.",
    "drops": ["Spotter Relay", "Electrical Components"],
    "weak_points": ["Gesamter Körper (sehr fragil)"],
    "tactic": "Höchste Priorität! Zerstören ('blendet' den Bombardier). Sichtlinie brechen (Wände/Gebäude). Quick-Use Items zum Blenden/Stunnen nutzen."
  },
  "wasp": {
    "names": {
      "en": "Wasp",
      "de": "Wespe"
    },
    "tier": 2,
    "type": "Leichte Flugdrohne",
    "threat_level": "Niedrig-Mittel",
    "description": "Schnellfeuernde Drohne, fliegt in Gruppen (3-5). Nutzt Schwarmtaktiken und Flankenmanöver.",
    "drops": ["Wasp Driver", "Light Ammo", "ARC Alloy"],
    "weak_points": ["Rotoren (Propeller)"],
    "tactic": "Ziele auf die Rotoren für sofortigen Absturz. Automatische Waffen nutzen."
  },
  "hornet": {
    "names": {
      "en": "Hornet",
      "de": "Hornisse"
    },
    "tier": 2,
    "type": "Schwere Flugdrohne",
    "threat_level": "Mittel",
    "description": "Stärker gepanzert als die Wasp. Feuert aufgeladene Einzelschuss-Laser, die betäuben (Stagger).",
    "drops": ["Hornet Driver", "Medium Ammo"],
    "weak_points": ["Hecktriebwerke (ungepanzert)"],
    "tactic": "'Matador'-Taktik: Warten bis zum Angriff, ausweichen, dann auf die ungeschützten Triebwerke am Heck feuern."
  },
  "surveyor": {
    "names": {
      "en": "Surveyor",
      "de": "Vermesser"
    },
    "tier": 2,
    "type": "Loot-Einheit",
    "threat_level": "Niedrig (Fluchtgefahr)",
    "description": "Stark gepanzerte 'Loot-Goblin'-Einheit. Greift nicht an, flieht aber bei Beschuss und ruft Verstärkung.",
    "drops": ["Surveyor Vault (Baupläne)", "ARC Circuitry"],
    "weak_points": ["Rumpf (anfällig für Wolfpack-Granaten)"],
    "tactic": "Einkreisen oder betäuben (Goo/Stun), dann massiver Fokus-Schaden (Alpha Strike). Nicht anschießen, bevor das Team bereit ist."
  },
  "fireball": {
    "names": {
      "en": "Fireball",
      "de": "Feuerball"
    },
    "tier": 2,
    "type": "Gepanzerte Nahkampfeinheit",
    "threat_level": "Mittel-Hoch",
    "description": "Dunkel gepanzerte Kugel mit Flammenwerfern. Rollt nah heran, öffnet sich und verursacht Flächenbrand.",
    "drops": ["Fireball Burner", "ARC Powercell"],
    "weak_points": ["Innerer Kern (nur sichtbar wenn geöffnet/angreift)"],
    "tactic": "Warten bis er sich öffnet ('aufblüht'), dann auf den leuchtenden Kern schießen. Rückwärts bewegen (Kiting)."
  },
  "sentinel": {
    "names": {
      "en": "Sentinel",
      "de": "Wächter"
    },
    "tier": 2,
    "type": "Stationärer Scharfschütze",
    "threat_level": "Hoch (Long Range)",
    "description": "Stationärer Turm mit Railgun. Hoher Schaden auf Distanz, langsame Rotation.",
    "drops": ["Sentinel Firing Core"],
    "weak_points": ["Leuchtender Energiekern auf der Rückseite"],
    "tactic": "Sichtlinie brechen während des Aufladens. Flankieren, um den Kern am Rücken zu treffen. Der Bereich direkt unter dem Turm ist ein toter Winkel."
  },
  "turret": {
    "names": {
      "en": "Turret",
      "de": "Geschützturm"
    },
    "tier": 2,
    "type": "Stationäre Innenverteidigung",
    "threat_level": "Niedrig",
    "description": "Kleinerer Turm in Innenräumen. Dauerfeuer bei Sichtkontakt.",
    "drops": ["Munition"],
    "weak_points": ["Optik / Gehäuse"],
    "tactic": "Leicht zerstörbar durch Beschuss oder einen einzelnen Nahkampfhieb."
  },
  "leaper": {
    "names": {
      "en": "Leaper",
      "de": "Springer"
    },
    "tier": 3,
    "type": "Elite Walker",
    "threat_level": "Hoch",
    "description": "Vierbeiniger Mech (ehemals Bison). Springt große Distanzen, nutzt Schallimpulse und Frontalschilde.",
    "drops": ["Leaper Pulse Unit"],
    "weak_points": ["Beingelenke (Knie)", "Energiekern am Heck/Unterleib"],
    "tactic": "Beine beschießen für Stagger. Goo-Granaten zur Verlangsamung. Wenn Schild aktiv: Flankieren."
  },
  "bastion": {
    "names": {
      "en": "Bastion",
      "de": "Bastion"
    },
    "tier": 3,
    "type": "Elite Tank",
    "threat_level": "Sehr Hoch",
    "description": "Schwer gepanzerter Zweibeiner mit Minigun. Langsam, aber extrem widerstandsfähig frontal.",
    "drops": ["Bastion Cell", "Advanced ARC Powercell"],
    "weak_points": ["Gelber Kanister am Rücken", "Darunterliegendes 'Barrel'"],
    "tactic": "Aggro ziehen und flankieren. Rauch oder Köder (Lure) nutzen, um ihn umzudrehen. Schwachstelle ist nur hinten."
  },
  "bombardier": {
    "names": {
      "en": "Bombardier",
      "de": "Bombardier"
    },
    "tier": 3,
    "type": "Elite Artillerie",
    "threat_level": "Hoch",
    "description": "Walker mit Mörserkanone. Feuert indirekt über Hindernisse, geleitet von Spotter-Drohnen.",
    "drops": ["Bombardier Cell"],
    "weak_points": ["Mörserrohre", "Hinterer Zylinder", "Beingelenke"],
    "tactic": "Zuerst alle Spotter eliminieren (macht ihn blind). Nahdistanz suchen (Deadzone des Mörsers)."
  },
  "rocketeer": {
    "names": {
      "en": "Rocketeer",
      "de": "Raketenschütze"
    },
    "tier": 3,
    "type": "Elite Flugeinheit",
    "threat_level": "Sehr Hoch",
    "description": "Fliegende Infanterie mit Jetpack. Feuert Raketensalven und zielsuchende Projektile.",
    "drops": ["Rocketeer Driver"],
    "weak_points": ["Jetpack-Düsen (führt zum Absturz)"],
    "tactic": "Fokusfeuer auf die Düsen für 'Crash & Explosion'. Deckung ist gegen den Flächenschaden oft nutzlos."
  },
  "shredder": {
    "names": {
      "en": "Shredder",
      "de": "Schredder"
    },
    "tier": 3,
    "type": "Elite Nahkampf-Schweber",
    "threat_level": "Hoch",
    "description": "Schwebender Panzer, feuert Schrapnell-Salven. Bewegt sich aggressiv auf Spieler zu.",
    "drops": ["Shredder Gyro"],
    "weak_points": ["Antriebsdüsen (Thruster)"],
    "tactic": "Explosivwaffen nutzen, um ihn zu kippen (Flip). Abstand halten, Schwachstellen an den blauen Düsen treffen."
  },
  "queen": {
    "names": {
      "en": "The Queen",
      "de": "Königin"
    },
    "tier": 4,
    "type": "Boss (Harvester Event)",
    "threat_level": "Extrem",
    "description": "Gigantische mechanische Spinne.",
    "drops": ["Queen Reactor"],
    "weak_points": ["Beinpanzerung (absprengen)", "Beingelenke", "Kopfkern (Phase 2)"],
    "tactic": "Sprengstoff auf Beine. Wenn sie brüllt, Feuer auf den entblößten Kopfkern konzentrieren."
  },
  "matriarch": {
    "names": {
      "en": "Matriarch",
      "de": "Matriarchin"
    },
    "tier": 4,
    "type": "Boss",
    "threat_level": "Extrem",
    "description": "Massive Variante der Königin mit Energieschilden.",
    "drops": ["Matriarch Reactor"],
    "weak_points": ["Gesicht ('Nasenlöcher')", "Kopfkern (von oben angreifen)"],
    "tactic": "High Ground suchen. Schildphasen abwarten oder überladen. Präzisionsschüsse ins Gesicht."
  },
  "probe": {
    "names": {
      "en": "Probe",
      "de": "ARC Sonde"
    },
    "tier": 1,
    "type": "Loot-Einheit",
    "threat_level": "Keine (Lockt Gegner an)",
    "description": "Steht fest auf dem Boden oder ist abgestürzt. Greift nicht an. Erzeugt beim Aufbrechen laute Geräusche, die ARCs anlocken.",
    "drops": ["Materials", "Power Cells"],
    "weak_points": ["Interaktions-Panel"],
    "tactic": "Snitches erst klären. Schnell looten und Gebiet wechseln."
  }
}
