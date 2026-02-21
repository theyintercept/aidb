#!/usr/bin/env python3
"""
Assign intrinsic load to elements based on CLT heuristics.
- Low (1): Few interacting elements, concrete, foundational
- Medium (2): Several interacting elements, some abstraction  
- High (3): Many interacting elements, abstract reasoning
- NULL: Left blank - ambiguous or total guess
"""

import sqlite3
import re

DATABASE = "learning_sequence_v2.db"

# Keywords/patterns that suggest load level (from title + learning objective)
# Low: few elements, concrete, foundational
LOW_PATTERNS = [
    r'stable order', r'one.to.one', r'correspodence', r'cardinality', r'perceptual subitising',
    r'build dismantle', r'add remove', r'forward back', r'rearrange', r'hide reveal',
    r'fives frame introduction', r'tens frame introduction', r'counting forwards',
    r'backwards 5 to 0', r'backwards 10 to 0', r'counting back from',
    r'fair share', r'sharing construct', r'grouping construct',
    r'counting collections', r'counting with digits', r'tally marks to',
    r'number track to 5', r'number track to 10', r'number track to 20',
    r'tenth place', r'ordinal', r'familiar shapes', r'position', r'location',
    r'measurement attributes', r'days', r'data with two outcomes', r'instructions',
    r'addition notation', r'subtraction notation', r'notation intuitive',
    r'number track add', r'number track subtract', r'forwards', r'before & between',
    r'locating values', r'first build', r'movement', r'number line add', r'number line subtract',
    r'filling the grid', r'using patterns', r'bundles', r'mab ones', r'mab the tens rod',
    r'counting objects to 100', r'counting objects to 120', r'mab 120',
    r'fluency', r'double', r'half', r'friends of 10', r'number bonds to 10',
    r'odd even', r'8 & 9', r'15 20 25', r'number bonds to 100', r'facts for twos',
    r'halving', r'hands', r'hour', r'half hour', r'quarter', r'informal measurement',
    r'measures of turn', r'shape terminology', r'objects', r'shapes', r'numbers',
    r'locate & move', r'working with data', r'graphing data', r'record data', r'disply data',
]

# Medium: several interacting elements, some abstraction
MEDIUM_PATTERNS = [
    r'one more one less', r'recording after counting', r'counting structured',
    r'digits & words', r'comparing objects', r'deciding then comparing',
    r'matching then comparing', r'storytelling combining', r'dots combining',
    r'tens frames combining', r'bar model combining', r'storytelling partitioning',
    r'dots partitioning', r'tens frames partitioning', r'bar model partitioning',
    r'storytelling missing part', r'dots missing part', r'tens frames missing part',
    r'bar model missing part', r'tens frames to 20', r'number line to 20',
    r'patterns', r'estimating', r'representing', r'relationship between',
    r'add subtract', r'calculating with', r'commutative property', r'count on order',
    r'count back', r'see subtract think add', r'bar model$', r'combining tens & ones',
    r'separating into tens & ones', r'place value names', r'values of digits',
    r'tens & ones number line', r'renaming tens & ones', r'unitising tens & ones',
    r'choosing the sign', r'adding & subtracting tens', r'rounding tens & ones',
    r'drawing the sign', r'equals sign', r'not equal to', r'common language errors',
    r'number sentence formation', r'quotative grouping', r'partitive sharing',
    r'remainders', r'arrays', r'silver coins', r'gold coins', r'notation',
    r'tens', r'fives', r'twos', r'number line skip', r'number line intervals',
    r'repetition', r'length attributes', r'mass attributes', r'capacity attributes',
    r'measuring length', r'units & benchmarks', r'describe', r'sequences', r'make',
    r'compare', r'classify', r'language', r'give & follow directions',
    r'partitioning hundreds', r'renaming hundreds', r'unitising hundreds',
    r'comparing hundreds', r'rounding hundreds', r'calculating with hundreds',
    r'introducing halves', r'halves two equal', r'halves partitioning',
    r'halves collections', r'one half two halves', r'halfway', r'halves in wholes',
    r'half as a number', r'introducing quarters', r'quarters & eighths',
    r'bridging through 10', r'number bonds to 20', r'split strategy',
    r'rounding estimate', r'bar model addition', r'bar model subtraction',
    r'bar model combination', r'worded representations', r'creating from worded',
    r'addition to grouping', r'grouping notation', r'rows & columns',
    r'similar facts', r'sharing notation', r'movement', r'intervals & increments',
    r'magnitude to 1000', r'combining with coins', r'equal or not equal',
    r'balancing', r'comparing', r'vertical solving', r'application',
    r'connection to fours', r'grid patterns', r'counting concurrently',
    r'one thousand is ten', r'thousands separator', r'making thousands',
    r'naming thousands', r'partitioning thousands', r'renaming thousands',
    r'unitising thousands', r'number line with thousands', r'comparing thousands',
    r'rounding thousands', r'calculating with thousands',
]

# High: many interacting elements, abstract reasoning
HIGH_PATTERNS = [
    r'place value', r'partitioning to 100', r'combining to 100',
    r'120 to 199', r'199 to 300', r'300 to 999', r'grid problems',
    r'counting collections to 1000', r'one hundred is ten tens',
    r'counting mab tens', r'using mab hundreds', r'hundreds number line',
    r'naming hundreds', r'locating values within', r'rounding hundreds to nearest',
    r'teen ty misconception', r'digits & words 100', r'counting sequence 100',
    r'counting concrete collections to 100', r'counting pictorial collections',
    r'ordinal problems', r'making a number line to 120', r'number line magnitude 120',
    r'one thousand is ten hundreds', r'relationship between days weeks months years',
]

# Specific element overrides (element_number -> load_id) for ambiguous cases
# 1=Low, 2=Medium, 3=High, None = leave blank
OVERRIDES = {
    11204: 1,   # Tally marks to 20 - simple recording (obj mentions place value but that's "not yet")
    11804: 2,   # Money play - medium (value, exchange)
    20303: 2,   # Words to 30 - vocabulary
    20904: 1,   # Property of 0 - simple property
    20906: 2,   # Bar model - representation
    29015: 2,   # Counting sequence 120
    39005: 2,   # Counting sequence (generic)
    39037: 3,   # One eighth eighth eighths - fractions
    39042: 2,   # Bar model
    39068: 2,   # Number lines
    39075: 2,   # Number lines
}

# Elements to explicitly leave blank (ambiguous / total guess)
LEAVE_BLANK = {
    11805,   # Situations - too vague
    29027, 29033, 29043, 39085,  # Problems - generic, level depends on problem type
    39040,   # Common uses - vague
    39081,   # The notes - money context unclear
    39103,   # Counting sequence - could be 100s or 1000s
}

def get_load(text):
    """Determine load from text (title + objective). Returns 1, 2, 3, or None."""
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
            left_blank.append((el['element_number'], el['title'], 'In LEAVE_BLANK list'))
            continue
        
        if el['element_number'] in OVERRIDES:
            load_id = OVERRIDES[el['element_number']]
            if load_id is None:
                left_blank.append((el['element_number'], el['title'], 'Override: leave blank'))
                continue
            db.execute('UPDATE elements SET intrinsic_load_id = ? WHERE id = ?', (load_id, el['id']))
            load_name = ['', 'Low', 'Medium', 'High'][load_id]
            assigned.append((el['element_number'], el['title'], load_name))
            continue
            
        text = f"{el['title']} {el['learning_objective'] or ''}"
        load_id = get_load(text)
        
        if load_id:
            db.execute('UPDATE elements SET intrinsic_load_id = ? WHERE id = ?', (load_id, el['id']))
            load_name = ['', 'Low', 'Medium', 'High'][load_id]
            assigned.append((el['element_number'], el['title'], load_name))
        else:
            left_blank.append((el['element_number'], el['title'], 'No pattern match'))
    
    db.commit()
    
    print("=" * 80)
    print("INTRINSIC LOAD ASSIGNMENT COMPLETE")
    print("=" * 80)
    print(f"\n✅ Assigned: {len(assigned)} elements")
    print(f"⏭️  Left blank (ambiguous): {len(left_blank)} elements")
    print()
    
    print("ASSIGNED (by load level):")
    print("-" * 80)
    for load_name in ['Low', 'Medium', 'High']:
        subset = [a for a in assigned if a[2] == load_name]
        print(f"\n{load_name} ({len(subset)}):")
        for en, title, _ in subset[:15]:
            print(f"  {en}: {title[:60]}...")
        if len(subset) > 15:
            print(f"  ... and {len(subset)-15} more")
    
    print("\n" + "=" * 80)
    print("LEFT BLANK (review these - ambiguous or no clear pattern):")
    print("-" * 80)
    for en, title, reason in left_blank[:40]:
        print(f"  {en}: {title[:55]}...")
    if len(left_blank) > 40:
        print(f"  ... and {len(left_blank)-40} more")
    
    db.close()

if __name__ == '__main__':
    main()
