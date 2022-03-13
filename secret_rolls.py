import json
import logging
import sys
import config
import random
import string
from enum import IntEnum
from dataclasses import dataclass
from dataclasses import field
from os.path import exists

class Proficiency(IntEnum):
	Unknown = 0
	Untrained = 1
	Trained = 2
	Expert = 3
	Master = 4
	Legendary = 5

class BonusType(IntEnum):
	Unknown = 0
	Item = 1
	Status = 2
	Circumstance = 3
	Untyped = 4

class DegOfSuccess(IntEnum):
	Unknown = 0
	CritFail = 1
	Fail = 2
	Success = 3
	CritSuccess = 4

# this is a dict of dicts, serving as a representation of JSON data
# any time this is changed, before returning from the changing function, you must call save_json()
party: dict = dict()

def setup():
	global party

	if exists("party.json"):
		party_json: File = open("party.json", "r")
		party = json.load(party_json)
		party_json.close()
		print("Party JSON loaded.")
	else:
		party_json: File = open("party.json", "x")
		party_json.close()
		print("Party JSON created.")

	needed_init: bool = False
	if "level" not in party:
		party["level"] = 1
		needed_init = True
	if "members" not in party:
		party["members"] = dict()
		needed_init = True

	if needed_init:
		save_json()

def save_json():
	global party

	party_json: File = open("party.json", "w")
	json.dump(party, party_json, indent="\t")
	party_json.close()
	print("Party JSON updated.")

def convert_proficiency(proficiency: str) -> Proficiency:
	# no case sensitivity
	proficiency = proficiency.lower()

	if proficiency in config.get_config_list("Rolls", "untrained_aliases"):
		return Proficiency.Untrained
	elif proficiency in config.get_config_list("Rolls", "trained_aliases"):
		return Proficiency.Trained
	elif proficiency in config.get_config_list("Rolls", "expert_aliases"):
		return Proficiency.Expert
	elif proficiency in config.get_config_list("Rolls", "master_aliases"):
		return Proficiency.Master
	elif proficiency in config.get_config_list("Rolls", "legendary_aliases"):
		return Proficiency.Legendary

	return Proficiency.Unknown

def convert_bonus_type(bonus_type: str) -> BonusType:
	for bonus_enum in BonusType:
		if bonus_type.lower() == bonus_enum.name.lower():
			return bonus_enum

	return BonusType.Unknown

def make_default_ability_mods() -> dict:
	default_mods = dict()
	for ability in config.get_config_list("Rolls", "valid_abilities"):
		default_mods[ability] = 0

	return default_mods

# Creates a default dict for a check to be plugged into a party member
def make_initial_check_info() -> dict:
	initial_check = dict()
	initial_check["proficiency"] = Proficiency.Untrained
	initial_check["bonuses"] = dict()

	for bonus in BonusType:
		if bonus is BonusType.Unknown:
			continue
		initial_check["bonuses"][bonus.name] = 0

	return initial_check

def get_ability_for_check(check_name: str) -> str:
	check_name = check_name.lower()
	if check_name not in config.get_config_list("Rolls", "valid_checks"):
		return ""

	return config.get_config("Rolls-CheckAbilities", check_name)

# -------------
# Party management
# -------------

def check_party_member(name: str) -> bool:
	global party

	return name in party["members"]

def format_modifier(modifier: int) -> str:
	modifier_sign: str = "+"
	if modifier < 0:
		modifier_sign = "-"
	return "{}{}".format(modifier_sign, abs(modifier))

# returns an abridged stat block for the PC
def inspect_pc(name: str) -> str:
	global party

	name = name.lower()
	if not check_party_member(name):
		return ""

	# pc_json_str: str = json.dumps(party["members"][name], indent="\t")

	pc_stat_blk: str = "**{}**\t\t\t\t\t\t\t\t\t\t\t**LEVEL {}**\n".format(party["members"][name]["name"].upper(), party["level"])
	pc_stat_blk = pc_stat_blk + "**Perception** {}\n".format(format_modifier(get_modifier(name, "perception")))

	# Add all skills
	pc_stat_blk = pc_stat_blk + "**Skills** "
	skill_list: list[str] = list()
	for check_name in config.get_config_list("Rolls", "valid_checks"):
		if is_skill(check_name):
			skill_list.append("{} {}".format(check_name.capitalize(), format_modifier(get_modifier(name, check_name))))
	pc_stat_blk = pc_stat_blk + ", ".join(skill_list) + "\n"

	# Add abilities
	ability_list: list[str] = list()
	for ability_name in config.get_config_list("Rolls", "valid_abilities"):
		ability_list.append("**{}** {}".format(ability_name.capitalize(), format_modifier(party["members"][name]["ability_mods"][ability_name])))
	pc_stat_blk = pc_stat_blk + ", ".join(ability_list) + "\n"

	# Add defenses
	pc_stat_blk = pc_stat_blk + "**AC** {}; **Fort** {}, **Ref** {}, **Will** {}".format(get_dc(name, "ac"), format_modifier(get_modifier(name, "fort")), format_modifier(get_modifier(name, "ref")), format_modifier(get_modifier(name, "will")))

	feat_list: list[str] = [string.capwords(feat) for feat in party["members"][name]["feats"]]
	if feat_list:
		pc_stat_blk = pc_stat_blk + "\n**Feats** " + ", ".join(feat_list)

	return pc_stat_blk

def set_level(level: int) -> bool:
	global party

	if level < 1 or level > 20:
		return False

	party["level"] = level
	save_json()
	return True

def add_pc(name: str) -> bool:
	global party

	name = name.lower()
	if check_party_member(name):
		return False

	# add dict representing that party member to the party
	party["members"][name] = dict()
	party["members"][name]["name"] = name.capitalize()

	# fill in default info
	party["members"][name]["ability_mods"] = make_default_ability_mods()
	for check in config.get_config_list("Rolls", "valid_checks"):
		party["members"][name][check] = make_initial_check_info()
	party["members"][name]["feats"] = list()

	save_json()
	return True

def remove_pc(name: str) -> bool:
	global party

	name = name.lower()
	if not check_party_member(name):
		return False

	del party["members"][name]
	save_json()
	return True

def set_ability_mod(name: str, ability_name: str, modifier: int) -> bool:
	global party

	name = name.lower()
	if not check_party_member(name):
		return False

	if not ability_name in config.get_config_list("Rolls", "valid_abilities"):
		return False

	party["members"][name]["ability_mods"][ability_name] = modifier
	save_json()
	return True

def set_proficiency(name: str, check_name: str, proficiency: str) -> bool:
	global party

	name = name.lower()
	if not check_party_member(name):
		return False

	check_name = check_name.lower()
	if check_name not in config.get_config_list("Rolls", "valid_checks"):
		return False

	prof_enum: Proficiency = convert_proficiency(proficiency)

	if prof_enum is Proficiency.Unknown:
		return False

	party["members"][name][check_name]["proficiency"] = prof_enum
	save_json()
	return True

def set_bonus(name: str, check_name: str, bonus_type: str, bonus: int) -> bool:
	global party

	name = name.lower()
	if not check_party_member(name):
		return False

	check_name = check_name.lower()
	if check_name not in config.get_config_list("Rolls", "valid_checks"):
		return False

	bonus_enum: BonusType = convert_bonus_type(bonus_type)
	if bonus_enum is BonusType.Unknown:
		return False

	party["members"][name][check_name]["bonuses"][bonus_enum.name] = bonus
	save_json()
	return True

def set_feat(name: str, feat_name: str, enable: bool) -> bool:
	global party

	name = name.lower()

	if not check_party_member(name):
		return False

	if enable:
		party["members"][name]["feats"].append(feat_name)
	elif feat_name in party["members"][name]["feats"]:
		party["members"][name]["feats"].remove(feat_name)
	else:
		save_json()
		return False

	save_json()
	return True

# -----------
# Check Fundamentals
# -----------

# contains info on the numerical result and the degree of success the result got for each member of the party
# for example, if Viola is in the crit_success_vs list, then the check was a critical success against her
@dataclass
class CheckResults:
	num_on_die: int = 0
	total: int = 0
	dc_name: str = ""
	crit_success_vs: list[str] = field(default_factory=list)
	success_vs: list[str] = field(default_factory=list)
	fail_vs: list[str] = field(default_factory=list)
	crit_fail_vs: list[str] = field(default_factory=list)
	valid: bool = False

def roll_d20() -> int:
	return random.randint(1, 20)

def get_proficiency_mod(level: int, proficiency: Proficiency, untrained_improv: bool) -> int:
	if proficiency == Proficiency.Untrained:
		if untrained_improv:
			if level < 7:
				return level // 2
			else:
				return level
		else:
			return 0
	elif proficiency == Proficiency.Trained:
		return level + 2
	elif proficiency == Proficiency.Expert:
		return level + 4
	elif proficiency == Proficiency.Master:
		return level + 6
	elif proficiency == Proficiency.Legendary:
		return level + 8

	return 0

def get_degree_of_success(raw_result: int, result: int, dc: int) -> DegOfSuccess:
	retval: DegOfSuccess = DegOfSuccess.Unknown

	if result >= dc + 10:
		retval = DegOfSuccess.CritSuccess
	elif result >= dc:
		retval = DegOfSuccess.Success
	elif result > dc - 10:
		retval = DegOfSuccess.Fail
	else:
		retval = DegOfSuccess.CritFail

	if raw_result == 1 and retval > DegOfSuccess.CritFail:
		retval = retval - 1
	elif raw_result == 20 and retval < DegOfSuccess.CritSuccess:
		retval = retval + 1

	return retval

def is_skill(check_name: str) -> bool:
	return check_name not in ["ac", "perception", "will", "fort", "ref"]

def get_modifier(name: str, check_name: str) -> int:
	global party

	has_untrained_improv: bool = "untrained improvisation" in party["members"][name]["feats"]
	if not is_skill(check_name):
		has_untrained_improv = False

	prof_mod: int = get_proficiency_mod(party["level"], party["members"][name][check_name]["proficiency"], has_untrained_improv)

	check_ability: str = get_ability_for_check(check_name)
	ability_mod = party["members"][name]["ability_mods"][check_ability]

	total_bonus: int = 0
	for bonus_type in BonusType:
		if bonus_type == BonusType.Unknown:
			continue
		total_bonus = total_bonus + party["members"][name][check_name]["bonuses"][bonus_type.name]

	return prof_mod + ability_mod + total_bonus

def get_dc(name: str, check_name: str) -> int:
	return 10 + get_modifier(name, check_name)

def add_name_to_result(name: str, deg_of_success: DegOfSuccess, out_result: CheckResults):
	if deg_of_success is DegOfSuccess.CritSuccess:
		out_result.crit_success_vs.append(name)
	elif deg_of_success is DegOfSuccess.Success:
		out_result.success_vs.append(name)
	elif deg_of_success is DegOfSuccess.Fail:
		out_result.fail_vs.append(name)
	elif deg_of_success is DegOfSuccess.CritFail:
		out_result.crit_fail_vs.append(name)

def roll_check(modifier: int, dc_name: str) -> CheckResults:
	global party

	result = CheckResults()

	if dc_name not in config.get_config_list("Rolls", "valid_checks"):
		return result

	result.valid = True
	result.dc_name = dc_name
	result.num_on_die = roll_d20()
	result.total = result.num_on_die + modifier
	for member_name in party["members"].keys():
		dc: int = get_dc(member_name, dc_name)
		deg_of_success: DegOfSuccess = get_degree_of_success(result.num_on_die, result.total, dc)
		add_name_to_result(member_name, deg_of_success, result)

	return result

def get_member_name_list(name_indices: list[str], dc_name: str) -> str:
	global party

	return ", ".join([party["members"][name]["name"] + " ({})".format(get_dc(name, dc_name)) for name in name_indices])

def format_party_success(result: CheckResults, omit_header: bool = False) -> str:
	result_str: str = ""
	if not omit_header:
		result_str = "**RESULTS**\n**Roll** {}, **Total** {}".format(result.num_on_die, result.total)

	if result.crit_success_vs:	# stupid python and its implicit bool-ing
		result_str = result_str + "\n" + "**Critical Success vs** " + get_member_name_list(result.crit_success_vs, result.dc_name)
	if result.success_vs:
		result_str = result_str + "\n" + "**Success vs** " + get_member_name_list(result.success_vs, result.dc_name)
	if result.fail_vs:
		result_str = result_str + "\n" + "**Failure vs** " + get_member_name_list(result.fail_vs, result.dc_name)
	if result.crit_fail_vs:
		result_str = result_str + "\n" + "**Critical Failure vs** " + get_member_name_list(result.crit_fail_vs, result.dc_name)

	return result_str

# -----------
# Specific Activities
# -----------

# NOTE: When adding the URLs in the action descriptions, please wrap the URL in angle brackets ('<' and '>')

def activity_lie(modifier: int) -> str:
	global party

	result: CheckResults = roll_check(modifier, "perception")

	description: str = "**LIE** <https://2e.aonprd.com/Actions.aspx?ID=47>\n**Success** The target believes your lie.\n**Failure** The target doesn't believe your lie and gains a +4 circumstance bonus against your attempts to Lie for the duration of your conversation."

	party_result_str: str = format_party_success(result)

	pcs_with_lie_to_me: list[str] = list()
	for member_name in party["members"].keys():
		if "lie to me" in party["members"][member_name]["feats"]:
			pcs_with_lie_to_me.append(member_name)

	lie_to_me_section: str = ""
	if pcs_with_lie_to_me:
		lie_to_me_section = "**Lie to Me** The following PC(s) have the feat Lie to Me.  This allows them to use their Deception DC instead of their Perception DC in conversations in which they've had a back in forth with the lying creature.  If Lie to Me applies in this context, then use the following results:"

		lie_to_me_result = CheckResults()
		lie_to_me_result.num_on_die = result.num_on_die
		lie_to_me_result.total = result.total
		lie_to_me_result.dc_name = "deception"

		for pc in pcs_with_lie_to_me:
			dc: int = get_dc(pc, lie_to_me_result.dc_name)
			deg_of_success: DegOfSuccess = get_degree_of_success(result.num_on_die, result.total, dc)
			add_name_to_result(pc, deg_of_success, lie_to_me_result)

		# These results will only include PCs who have Lie to Me
		lie_to_me_section = lie_to_me_section + format_party_success(lie_to_me_result, True)

	return_str: str = description + "\n\n" + party_result_str
	if lie_to_me_section != "":
		return_str = return_str + "\n\n" + lie_to_me_section

	return return_str

def activity_sneak(modifier: int) -> str:
	result: CheckResults = roll_check(modifier, "perception")

	description: str = "**SNEAK** <https://2e.aonprd.com/Actions.aspx?ID=63>\n**Success** You're undetected by the creature during your movement and remain undetected by the creature at the end of it.\n**Failure** A telltale sound or other sign gives your position away, though you still remain unseen.  You're hidden from the creature throughout your movement and remain so.\n**Critical Failure** You're spotted!  You're observec by the creature throughout your movement and remain so.  If you're invisible and were hidden from the creature, instead of being observed you're hidden throughout your movement and remain so."

	party_result_str: str = format_party_success(result)

	return description + "\n\n" + party_result_str

def activity_hide(modifier: int) -> str:
	result: CheckResults = roll_check(modifier, "perception")

	description: str = "**HIDE** <https://2e.aonprd.com/Actions.aspx?ID=62>\n**Success** If the creature could see you, you're now hidden from it instead of observed.  If you were hidden from or undetected by the creature, you retain that condition."

	party_result_str: str = format_party_success(result)

	return description + "\n\n" + party_result_str

def activity_impersonate(modifier: int) -> str:
	result: CheckResults = roll_check(modifier, "perception")

	description: str = "**IMPERSONATE** <https://2e.aonprd.com/Actions.aspx?ID=46>\n**Success** You trick the creature into thinking you're the person you're disguised as.  You might have to attempt a new check if your behavior changes.\n**Failure** The creature can tell you're not who you claim to be.\n**Critical Failure** As failure, and the creature recognizes you if it would know you without a disguise."

	party_result_str: str = format_party_success(result)

	return description + "\n\n" + party_result_str

def activity_conceal(modifier: int) -> str:
	result: CheckResults = roll_check(modifier, "perception")

	description: str = "**CONCEAL AN OBJECT** <https://2e.aonprd.com/Actions.aspx?ID=61>\n**Success** The object remains undetected.\n**Failure** The searcher finds the object."

	party_result_str: str = format_party_success(result)

	return description + "\n\n" + party_result_str