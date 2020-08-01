#!/usr/bin/env python3
import argparse
import json
import re
import sys

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

def split_list(lst):
    return [x.strip() for x in lst.split(',') if x]

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='count')
    parser.add_argument('json_files', nargs='+', type=argparse.FileType('rb'))
    return parser.parse_args()

def parse_monster(old):
    monster = empty_monster()
    monster['Name'] = old['name']
    monster['Type'] = f"{old['size']} {old['type']}, {old['alignment']}"
    monster['AC'] = {'Value': old['armor_class'], 'Notes': old['armor_desc']}
    monster['HP'] = {'Value': old['hit_points'], 'Notes': old['hit_dice']}
    for move_type, move_dist in old['speed'].items():
        monster['Speed'].append(f'{move_type} {move_dist} ft.')
    monster['Abilities']['Str'] = old['strength']
    monster['Abilities']['Dex'] = old['dexterity']
    monster['Abilities']['Con'] = old['constitution']
    monster['Abilities']['Int'] = old['intelligence']
    monster['Abilities']['Wis'] = old['wisdom']
    monster['Abilities']['Cha'] = old['charisma']
    for stat in ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']:
        if old[stat+'_save'] is not None:
            monster['Saves'].append({'Name': stat[:3].title(), 'Modifier': old[stat+'_save']})
    #monster['Senses'].append(f"passive Perception {old['perception']}")
    for name, mod in old['skills'].items():
        monster['Skills'].append({'Name': name, 'Modifier': mod})
    monster["DamageVulnerabilities"].extend(split_list(old['damage_vulnerabilities']))
    monster["DamageResistances"].extend(split_list(old['damage_resistances']))
    monster["DamageImmunities"].extend(split_list(old['damage_immunities']))
    monster["ConditionImmunities"].extend(split_list(old['condition_immunities']))
    monster["Senses"].extend(split_list(old['senses']))
    monster["Languages"].extend(split_list(old['languages']))
    monster['Challenge'] = old['challenge_rating']
    for action in old['actions']:
        monster['Actions'].append({'Name': action['name'], 'Content': action['desc'], 'Usage': ''})
    for action in old['reactions']:
        monster['Reactions'].append({'Name': action['name'], 'Content': action['desc'], 'Usage': ''})
    for action in old['legendary_actions']:
        monster['LegendaryActions'].append({'Name': action['name'], 'Content': action['desc'], 'Usage': ''})
    for action in old['special_abilities']:
        monster['Traits'].append({'Name': action['name'], 'Content': action['desc'], 'Usage': ''})
    if old['document__title']:
        monster['Source'] = old['document__title']

    return monster

def main(args):
    for infile in args.json_files:
        # curl https://api.open5e.com/monsters/boloti/ > boloti.json
        old = json.load(infile)
        monster = parse_monster(old)
        if args.verbose:
            print(json.dumps(monster, indent=4))
        outname = re.sub(r'[^A-Za-z]', r'', monster['Name']) + '.monster.json'
        with open(outname, 'w') as outfile:
            json.dump(monster, outfile, indent=4)

if __name__ == '__main__':
    sys.exit(main(parse_args()))
