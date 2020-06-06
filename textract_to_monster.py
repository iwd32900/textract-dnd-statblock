#!/usr/bin/env python3
import json
import re
import sys

class locstr(str):
    # See https://stackoverflow.com/a/30045261
    def __new__(cls, block):
        # explicitly only pass value to the str constructor
        return super().__new__(cls, block['Text'])
    def __init__(self, block):
        # super().__init__(block['Text'])
        self.confidence = block['Confidence']
        b = block['Geometry']['BoundingBox']
        self.width = b['Width']
        self.height = b['Height']
        self.left = b['Left']
        self.top = b['Top']

def midline_gap(b0, b1):
    return (b1.top + 0.5*b1.height) - (b0.top + 0.5*b0.height)
def baseline_gap(b0, b1):
    return (b1.top+b1.height) - (b0.top+b0.height)
def topline_gap(b0, b1):
    return b1.top - b0.top
# On balance, baseline is detected most reliably:
line_gap = baseline_gap

def empty_monster():
    return {
    "Name": "", # this is a non-standard field!
    "Source": "Textract-DnD-StatBlock",
    "Type": "",
    "HP": {
        "Value": 1,
        "Notes": "(1d1+0)"
    },
    "AC": {
        "Value": 10,
        "Notes": ""
    },
    "InitiativeModifier": 0,
    "InitiativeAdvantage": False,
    "Speed": [],
    "Abilities": {
        "Str": 10,
        "Dex": 10,
        "Con": 10,
        "Int": 10,
        "Wis": 10,
        "Cha": 10
    },
    "DamageVulnerabilities": [],
    "DamageResistances": [],
    "DamageImmunities": [],
    "ConditionImmunities": [],
    "Saves": [],
    "Skills": [],
    "Senses": [],
    "Languages": [],
    "Challenge": "",
    "Traits": [],
    "Actions": [],
    "Reactions": [],
    "LegendaryActions": [],
    "Description": "",
    "Player": "",
    "Version": "2.15.4",
    "ImageURL": ""
    }

def parse_armor_class(block):
    m = re.search(r'Armor Class ([1-9][0-9]?)\s*(.+)?', block)
    return {
        'Value': int(m.group(1)),
        'Notes': m.group(2) or "",
    }

def parse_hit_points(block):
    m = re.search(r'Hit Points ([1-9][0-9]*)\s*(.+)?', block)
    return {
        'Value': int(m.group(1)),
        'Notes': m.group(2) or "",
    }

rx_comma = re.compile(r'[,;]')
def parse_comma_list(blocks, nwords=1):
    b0 = blocks.pop(0)
    lines = [b0]
    # Multi-line lists (later lines are indented)
    # I've only seen 2 lines, but theoretically could stretch to 3+ ...
    while True:
        if len(blocks) == 0:
            break # We reached the end of the page!
        b1 = blocks[0]
        indent = b1.left - b0.left
        # print(f"COMMA LIST {indent:.4f}    {b1}    {b0}")
        if indent < 0.008 or b1 == 'STR':
            # We get a weird problem parsing Speed:  it's followed by stats, which looks like an indent!
            break
        lines.append(blocks.pop(0))
    block = " ".join(lines)
    block = block.split(None, nwords)[-1] # remove leading N words
    return [b.strip() for b in rx_comma.split(block) if b.strip()]

def parse_ability_score(block):
    # like "7 (-2)" or "16 (+3)"
    return int(block.split()[0])

def parse_challenge(block):
    m = re.search(r'Challenge ((1/)?[1-9][0-9]*)\s*(.+)?', block)
    return m.group(1)

def parse_saving_throws(blocks, nwords=1):
    saves = parse_comma_list(blocks, nwords)
    out = []
    for save in saves:
        try:
            name, mod = save.split()
            out.append({'Name': name, 'Modifier': int(mod)})
        except:
            # raise
            pass
    return out

rx_spell_line = re.compile(r'^(Cantrips?|([1I]st|2nd|3rd|[4-9]th) level) \(')
def is_spell_line(block):
    m = rx_spell_line.search(block)
    return bool(m)

# Attack.
# Big Attack.
# Attack of Bigness.
# Joe's Attack of Bigness (Recharge 5-6).
rx_trait_name = re.compile(r"^([A-Z][a-z']+)( [a-z]{1,4}| [A-Z][a-z']+)*?( [A-Z][a-z']+)?( [(][^)]+[)])?\.")
def parse_paragraph(blocks):
    '''
    Identify a sequence of lines that are ended by vertical whitespace,
    or dedent.
    '''
    trait = []
    while True:
        b0 = blocks.pop(0)
        # if rx_trait_name.search(b0): print("TRAIT: ", b0)
        trait.append(b0)
        if len(blocks) == 0:
            # We reached the end of the page!
            break
        b1 = blocks[0]
        if is_spell_line(b1):
            # Sometimes spells are separated by vertical whitespace (e.g. Mummy Lord).
            # They should get hard line breaks, but not be new paragraphs
            trait.append('\n')
            continue
        vert_gap = line_gap(b0, b1)
        # Dedent can be used to separate Legendary Actions (e.g. Mummy Lord)
        dedent = b0.left - b1.left
        print(f'{vert_gap/MED_GAP:.4f}    {dedent:.4f}    {b0}')
        if vert_gap > 1.3*MED_GAP or dedent > 0.008:
            break
        if vert_gap < -0.3 and rx_trait_name.search(b1):
            # Tricky case -- after column wrap, is it a continuation or a new trait?
            # Try to decide based on whether the text looks like a new trait/action/etc.
            # L-shaped stat block is possible:  Kobold Inventor, in Volo's
            break
    trait = " ".join(trait)
    if '.' in trait:
        name, content = trait.split('.', 1)
    else:
        name, content = "", trait
    return {'Name': name.strip(), 'Content': content.strip(), 'Usage': ''}

def main(infile):
    textract = json.load(infile)
    blocks = []
    for block in textract['Blocks']:
        if block['BlockType'] != 'LINE':
            continue
        blocks.append(locstr(block))
    # print(json.dumps(blocks, indent=4))
    # import pdb; pdb.set_trace()

    # If it appears there are 2 columns of text,
    # put all lines from the second column after the first!
    first_col = []
    second_col = []
    for block in blocks:
        if block.left >= 0.47:
            second_col.append(block)
        else:
            first_col.append(block)
    # L-shaped stat block is possible:  Kobold Inventor, in Volo's
    if len(second_col) >= 0.3*len(first_col):
        blocks = first_col + second_col

    # This code determined that baseline can be measured most accurately:
    # import numpy as np
    # for line_gap in (topline_gap, baseline_gap, midline_gap):
    #     diffs = np.array([line_gap(blocks[i], blocks[i+1]) for i in range(len(blocks)-1)])
    #     med_diff = np.median(diffs)
    #     mad_diff = np.median(np.abs(diffs - med_diff))
    #     print(f"Median: {med_diff}   MAD: {mad_diff}")
    # return 0

    # Infer the typical spacing between lines of text, so we can identify vertical gaps:
    gaps = [line_gap(blocks[ii], blocks[ii+1]) for ii in range(len(blocks)-1)]
    gaps = gaps[17:] # discard name, stats
    global MED_GAP
    # Median is good for long entries, but short entries have more variability!
    MED_GAP = gaps[int(0.25 * len(gaps))]

    print(json.dumps(blocks, indent=4))

    monster = empty_monster()
    monster['Name'] = blocks.pop(0).title()
    monster['Type'] = blocks.pop(0)

    mode = 'PRE_STATS'
    while blocks:
        block = blocks[0]
        if mode == 'PRE_STATS':
            if block.startswith("Armor Class"):
                monster['AC'] = parse_armor_class(blocks.pop(0))
            elif block.startswith("Hit Points"):
                monster['HP'] = parse_hit_points(blocks.pop(0))
            elif block.startswith("Speed"):
                monster['Speed'] = parse_comma_list(blocks)
            elif block == 'STR' and len(blocks) >= 12:
                assert blocks[0:6] == "STR DEX CON INT WIS CHA".split()
                monster['Abilities']['Str'] = parse_ability_score(blocks[6])
                monster['Abilities']['Dex'] = parse_ability_score(blocks[7])
                monster['Abilities']['Con'] = parse_ability_score(blocks[8])
                monster['Abilities']['Int'] = parse_ability_score(blocks[9])
                monster['Abilities']['Wis'] = parse_ability_score(blocks[10])
                monster['Abilities']['Cha'] = parse_ability_score(blocks[11])
                blocks = blocks[12:]
                mode = 'POST_STATS'
            else:
                blocks.pop(0)
        elif mode == 'POST_STATS':
            if block.startswith('Saving Throws'):
                monster['Saves'] = parse_saving_throws(blocks, 2)
            if block.startswith('Skills'):
                monster['Skills'] = parse_saving_throws(blocks)
            elif block.startswith('Damage Vulnerabilities'):
                monster['DamageVulnerabilities'] = parse_comma_list(blocks, 2)
            elif block.startswith('DamageResistances'):
                monster['DamageResistances'] = parse_comma_list(blocks)
            elif block.startswith('Damage Immunities'):
                monster['DamageImmunities'] = parse_comma_list(blocks, 2)
            elif block.startswith('Condition Immunities'):
                monster['ConditionImmunities'] = parse_comma_list(blocks, 2)
            elif block.startswith('Senses'):
                monster['Senses'] = parse_comma_list(blocks)
            elif block.startswith('Languages'):
                monster['Languages'] = parse_comma_list(blocks)
            elif block.startswith('Challenge'):
                monster['Challenge'] = parse_challenge(blocks.pop(0))
                mode = 'TRAITS'
            else:
                blocks.pop(0)
        else: # TRAITS, ACTIONS, REACTIONS, LEGENDARY_ACTIONS
            if block == 'ACTIONS':
                mode = 'ACTIONS'
                blocks.pop(0)
            elif block == 'REACTIONS':
                mode = 'REACTIONS'
                blocks.pop(0)
            elif block == 'LEGENDARY ACTIONS':
                mode = 'LEGENDARY_ACTIONS'
                blocks.pop(0)
            elif mode == 'TRAITS':
                monster['Traits'].append(parse_paragraph(blocks))
            elif mode == 'ACTIONS':
                monster['Actions'].append(parse_paragraph(blocks))
            elif mode == 'REACTIONS':
                monster['Reactions'].append(parse_paragraph(blocks))
            elif mode == 'LEGENDARY_ACTIONS':
                monster['LegendaryActions'].append(parse_paragraph(blocks))
            else:
                break

    print(json.dumps(monster, indent=4))

if __name__ == '__main__':
    sys.exit(main(open(sys.argv[1])))
    # sys.exit(main(sys.stdin))