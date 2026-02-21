#!/usr/bin/env python3
"""
Assign concept stability to elements based on research.
Concept stability = how much reiteration/retrieval practice needed for consolidation.
- High (3): Concept is fragile; requires lots of revisiting
- Medium (2): Moderate reiteration needed
- Low (1): Consolidates relatively readily
- NULL: Left blank - insufficient research or too unclear

Research sources:
- Cardinality, one-to-one: protracted acquisition, knower-levels (Wynn, Spaepen et al.)
- Teen/ty, place value: persistent misconceptions (Vic Ed, NCBI)
- Fractions: notoriously difficult, persistent misconceptions (Siegler, NNB)
- Equals sign: operational vs relational misconception, barrier to algebra
- Part-part-whole, missing part: "most difficult" for number bonds (Math Coach)
- Fair share/grouping: foundational division, needs both concepts
- Measurement: conservation, unit iteration challenging (NCETM)
- Addition/subtraction: concept-procedure interactions, developmental stages
"""

import sqlite3
import re

DATABASE = "learning_sequence_v2.db"

# HIGH: Research explicitly shows protracted acquisition, fragile, or persistent misconceptions
HIGH_PATTERNS = [
    # Foundational counting - protracted acquisition (Wynn, knower-levels)
    r'stable order', r'one.to.one', r'correspodence', r'cardinality',
    r'perceptual subitising',
    # Teen/ty - persistent misconception (Vic Ed)
    r'teen ty misconception', r'teen.*ty',
    # Place value structure - persistent (NCBI, Vic Ed)
    r'place value names for digits', r'values of digits',
    r'one hundred is ten tens', r'renaming tens & ones', r'unitising tens & ones',
    r'one thousand is ten hundreds', r'renaming hundreds', r'unitising hundreds',
    r'tenth place', r'above tenth place',
    # Fractions - notoriously difficult, persistent (Siegler, NNB)
    r'introducing halves', r'halves two equal', r'halves partitioning',
    r'halves collections', r'one half two halves', r'halfway', r'halves in wholes',
    r'half as a number', r'introducing quarters', r'quarters & eighths',
    r'one quarter four quarters', r'one eighth eighth eighths',
    r'quarter as a number',
    # Equals sign - operational misconception, barrier to algebra (Alibali et al.)
    r'equals sign with concrete', r'equals sign with abstract',
    r'not equal to', r'equal or not equal', r'balancing',
    # Missing part - "most difficult" for number bonds (Math Coach)
    r'missing part',
]

# MEDIUM: Research suggests moderate reiteration
MEDIUM_PATTERNS = [
    # Symbolic number knowledge - develops gradually (Purpura et al.)
    r'number bonds to 10', r'friends of 10', r'number bonds to 20',
    r'number bonds to 100', r'bridging through 10',
    r'counting sequence', r'counting forwards', r'counting back',
    r'digits & words', r'counting with digits',
    # Part-part-whole relationships - need reinforcement
    r'combining to 10', r'partitioning to 10', r'combining to 20',
    r'partitioning to 20', r'bar model combining', r'bar model partitioning',
    r'storytelling combining', r'dots combining', r'tens frames combining',
    r'storytelling partitioning', r'dots partitioning', r'tens frames partitioning',
    # Fair share/grouping - foundational division concepts
    r'fair share', r'sharing construct', r'grouping construct',
    # Addition/subtraction concepts - developmental stages
    r'commutative property', r'count on order', r'count back',
    r'see subtract think add', r'bar model addition', r'bar model subtraction',
    r'bar model combination', r'worded representations', r'creating from worded',
    r'addition to grouping', r'grouping notation', r'sharing notation',
    # Multiplication/division - equal groups, quotative/partitive
    r'quotative grouping', r'partitive sharing', r'remainders', r'arrays',
    r'rows & columns',
    # Measurement - conservation, unit iteration challenging (NCETM)
    r'measurement attributes', r'length attributes', r'mass attributes',
    r'capacity attributes', r'measuring length', r'units & benchmarks',
    r'informal measurement', r'measures of turn',
    # Place value operations
    r'combining tens & ones', r'separating into tens & ones',
    r'adding & subtracting tens', r'rounding tens & ones',
    r'partitioning hundreds', r'comparing hundreds', r'calculating with hundreds',
    r'partitioning thousands', r'renaming thousands', r'unitising thousands',
    r'comparing thousands', r'calculating with thousands',
    # MAB / base-10 structure
    r'mab ones', r'mab the tens rod', r'mab 120', r'counting mab tens',
    r'using mab hundreds', r'bundles', r'counting objects to 100',
    r'counting objects to 120', r'counting collections to 1000',
    # Number line magnitude
    r'number line to 20', r'number line magnitude', r'making a number line',
    r'locating values', r'magnitude to 1000',
    # Estimating
    r'estimating', r'estimating to 30',
    # Recording/counting
    r'recording after counting', r'recording as counting',
    r'counting structured', r'counting collections', r'tally marks',
    r'number track', r'number line add', r'number line subtract',
    r'fives frame introduction', r'tens frame introduction',
    r'one more one less', r'backwards 5 to 0', r'counting back from',
    r'build dismantle', r'add remove', r'forward back', r'rearrange', r'hide reveal',
    r'comparing objects', r'deciding then comparing', r'matching then comparing',
    r'comparing', r'comparing hundreds', r'comparing thousands',
    r'similar facts', r'double', r'half', r'halving', r'facts for twos',
    r'split strategy', r'rounding estimate', r'vertical solving',
    r'odd even', r'8 & 9', r'15 20 25', r'connection to fours',
    r'grid patterns', r'counting concurrently',
    # Time
    r'days & time', r'relationship between days weeks months years',
    r'hour', r'half hour', r'quarter', r'hands',
    # Data
    r'data with two outcomes', r'record data', r'disply data',
    r'working with data', r'graphing data',
    # Position/location
    r'position', r'location', r'give & follow directions', r'locate & move',
    # Patterns
    r'patterns', r'using patterns', r'sequences', r'describe', r'make',
    r'compare', r'classify',
    # Shapes
    r'familiar shapes', r'shape terminology', r'objects', r'shapes', r'numbers',
    # Money
    r'money play', r'silver coins', r'gold coins', r'combining with coins',
]

# LOW: Procedural/fluency - consolidates with practice once learned
LOW_PATTERNS = [
    r'fluency', r'addition notation', r'subtraction notation',
    r'notation intuitive', r'instructions', r'notation$',
    r'number line skip', r'number line intervals', r'repetition',
    r'movement', r'intervals & increments',
]

# Elements to explicitly leave blank (too vague, generic, or unclear)
LEAVE_BLANK = {
    11805,   # Situations - too vague
    29027, 29033, 29043, 39085,  # Problems - generic, depends on problem type
    29028, 29054, 29056, 29069, 39076,  # Language - too generic
    39040,   # Common uses - vague
    39081,   # The notes - unclear context
    39103,   # Counting sequence - could be 100s or 1000s
    39030, 39098,  # Application - depends on context
    29049, 29050, 29051, 29052, 29053,  # Describe, Sequences, Make, Compare, Classify - could be many things
    39124, 39125, 39126,  # Objects, Shapes, Numbers (391xx) - generic
    39083, 39084,  # Common language errors, Number sentence formation - unclear
}

# Overrides: element_number -> stability_id (1=Low, 2=Medium, 3=High, None=blank)
OVERRIDES = {
    # Explicit overrides for edge cases
    10701: 1,   # Numbers in other cultures - cultural exposure, low consolidation need
    11901: 1,   # Instructions - procedural
    12001: 2,   # Patterns - pattern recognition needs practice
    12101: 2,   # Measurement attributes - foundational for measurement
    12201: 2,   # Days & time - time concepts need reiteration
    12301: 1,   # Familiar shapes - recognition
    12401: 2,   # Position & location - spatial
    12501: 2,   # Data with two outcomes - early data
    20101: 1, 20102: 1, 20103: 1,  # Notation - procedural
    20201: 2, 20202: 2,  # Number track add/subtract
    20301: 2, 20302: 2, 20303: 2, 20304: 2, 20305: 2,  # Forwards, before & between, etc.
    20401: 2, 20402: 2, 20403: 1,  # Locating, first build, movement
    20501: 2, 20502: 2,  # Number line add/subtract
    20601: 2, 20602: 2,  # Filling grid, using patterns
    20704: 2, 20705: 2, 20706: 2,  # Counting to 100, ordinal
    20801: 2,  # Estimating
    20901: 2, 20902: 2, 20903: 2, 20904: 1, 20905: 2, 20906: 2,  # Properties, bar model
    29000: 2, 29001: 2, 29002: 2, 29003: 2,  # Bundles, counting, MAB
    29008: 2, 29009: 2, 29010: 2,  # Tens & ones
    29011: 2, 29012: 2, 29013: 2, 29014: 2,  # Comparing, adding/subtracting tens
    29015: 2, 29016: 2, 29017: 2, 29018: 2, 29019: 2, 29020: 2,  # 120 range
    29034: 2, 29035: 2, 29036: 1,  # Coins, notation
    29037: 2, 29038: 2, 29039: 2,  # Tens, fives, twos
    29040: 2, 29041: 2, 29042: 1,  # Number line skip, intervals, repetition
    29044: 2, 29045: 2, 29046: 2, 29047: 2, 29048: 2,  # Measurement
    29057: 2, 29058: 2,  # Record data, display data
    39000: 3, 39001: 3, 39002: 3, 39003: 3,  # 120-999, grid - high place value
    39004: 2, 39005: 2, 39006: 2, 39007: 2,  # Digits, counting, estimating
    39009: 2, 39010: 2, 39011: 2, 39012: 2, 39013: 2,  # MAB hundreds
    39014: 2, 39015: 2, 39016: 2, 39017: 2, 39018: 2, 39019: 2, 39020: 2, 39021: 2,
    39042: 2, 39044: 1, 39045: 1, 39046: 2, 39047: 2, 39048: 2, 39049: 2, 39050: 1,
    39051: 1, 39052: 1, 39053: 1, 39054: 1, 39055: 1, 39056: 2, 39057: 2, 39058: 1,
    39059: 2, 39060: 2, 39061: 2, 39062: 2, 39063: 2, 39064: 2, 39065: 2,
    39066: 2, 39067: 2, 39068: 2, 39070: 2, 39071: 1, 39072: 2, 39073: 2,
    39074: 2, 39075: 2, 39077: 1, 39078: 1, 39079: 2, 39080: 2,
    39082: 2, 39086: 2, 39087: 2, 39088: 2, 39089: 2,
    39090: 2, 39091: 2, 39092: 2, 39093: 2, 39094: 1, 39095: 1, 39096: 2,
    39099: 2, 39100: 2, 39101: 2, 39102: 2, 39104: 2,
    39105: 3, 39106: 2, 39107: 2, 39108: 2, 39109: 2, 39110: 2, 39111: 2,
    39112: 2, 39113: 2, 39114: 2, 39115: 2,
    39116: 1, 39117: 2, 39118: 2, 39119: 2, 39120: 3,  # Time - relationship high
    39121: 2, 39122: 2, 39123: 1, 39127: 2, 39128: 2, 39129: 2,
}


def get_stability(text):
    """Determine stability from text. Returns 1, 2, 3, or None."""
    if not text:
        return None
    t = text.lower()
    
    for p in HIGH_PATTERNS:
        if re.search(p, t, re.I):
            return 3
    
    for p in MEDIUM_PATTERNS:
        if re.search(p, t, re.I):
            return 2
    
    for p in LOW_PATTERNS:
        if re.search(p, t, re.I):
            return 1
    
    return None


def main():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    
    elements = db.execute('''
        SELECT e.id, e.element_number, e.title, e.learning_objective
        FROM elements e
        ORDER BY e.element_number
    ''').fetchall()
    
    assigned = []
    left_blank = []
    
    for el in elements:
        if el['element_number'] in LEAVE_BLANK:
            left_blank.append((el['element_number'], el['title'], 'In LEAVE_BLANK'))
            continue
        
        if el['element_number'] in OVERRIDES:
            sid = OVERRIDES[el['element_number']]
            if sid is None:
                left_blank.append((el['element_number'], el['title'], 'Override: blank'))
                continue
            db.execute('UPDATE elements SET concept_stability_id = ? WHERE id = ?', (sid, el['id']))
            name = ['', 'Low', 'Medium', 'High'][sid]
            assigned.append((el['element_number'], el['title'], name))
            continue
            
        text = f"{el['title']} {el['learning_objective'] or ''}"
        sid = get_stability(text)
        
        if sid:
            db.execute('UPDATE elements SET concept_stability_id = ? WHERE id = ?', (sid, el['id']))
            name = ['', 'Low', 'Medium', 'High'][sid]
            assigned.append((el['element_number'], el['title'], name))
        else:
            left_blank.append((el['element_number'], el['title'], 'No research match'))
    
    db.commit()
    
    print("=" * 80)
    print("CONCEPT STABILITY ASSIGNMENT COMPLETE")
    print("=" * 80)
    print(f"\nAssigned (research-based): {len(assigned)} elements")
    print(f"Left blank (insufficient research / unclear): {len(left_blank)} elements")
    print()
    
    for level in ['High', 'Medium', 'Low']:
        subset = [a for a in assigned if a[2] == level]
        print(f"{level} ({len(subset)}):")
        for en, title, _ in subset[:15]:
            print(f"  {en}: {title[:55]}...")
        if len(subset) > 15:
            print(f"  ... and {len(subset)-15} more")
        print()
    
    print("LEFT BLANK (review - insufficient research or unclear):")
    print("-" * 80)
    for en, title, reason in left_blank[:25]:
        print(f"  {en}: {title[:50]}...")
    if len(left_blank) > 25:
        print(f"  ... and {len(left_blank)-25} more")
    
    db.close()


if __name__ == '__main__':
    main()
