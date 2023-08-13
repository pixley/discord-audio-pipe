import configparser
import asyncio
from os.path import exists
import zoneinfo
import datetime

# configparser.ConfigParser config
config = None
# asyncio.Task save_task
save_task = None
# str file_name
file_name = ""
# set[str] valid_time_zones
valid_time_zones = None

# params: str cfg_file_name
# return boolean
def setup_config(cfg_file_name):
	global valid_time_zones
	valid_time_zones = zoneinfo.available_timezones()

	global file_name
	file_name = cfg_file_name
	# str use_file_name
	use_file_name = file_name
	# declare config for use within the function (Python, scope is a thing, bruh)
	global config
	config = configparser.ConfigParser()
	# if our config file doesn't already exist, load the default
	# bool use_default
	use_default = not exists(cfg_file_name)
	if use_default:
		use_file_name = cfg_file_name + ".default"

	config.read(use_file_name)
	if config.sections == []:
		print("{} is empty!  Cannot load!".format(use_file_name))
		return False
	else:
		print("{} successfully loaded".format(use_file_name))
		return True

	if use_default:
		# write the defaults out to the regular cfg file
		try_save()

# params: str section, str key
# return str
def get_config(section, key):
	if config is not None:
		return config[section][key]
	else:
		raise Exception()

# alias for readability's sake
get_config_string = get_config

# params: str section, str key
# return float
def get_config_float(section, key):
	return float(get_config(section, key))

# params: str section, str key
# return int
def get_config_int(section, key):
	return int(get_config(section, key))

# params: str section, str key
# return boolean
def get_config_bool(section, key):
	return config.getboolean(section, key)

# params: str section, str key
# return List[str]
def get_config_list(section, key):
	# str raw_str
	raw_str = get_config(section, key)
	return raw_str.split(',')

# alias for readability's sake
get_config_str_list = get_config_list

# params: str section, str key
# return List[int]
def get_config_int_list(section, key):
	return list(map(int, get_config_list(section, key)))

# params: str section, str key
# return List[float]
def get_config_float_list(section, key):
	return list(map(float, get_config_list(section, key)))

# params: str section, str key
# return List[boolean]
def get_config_bool_list(section, key):
	return list(map(convert_to_bool, get_config_list(section, key)))

# params: str section, str key, ??? value
# return boolean
def config_list_add(section, key, value):
	# str value_str
	value_str = str(value)

	# str list_str
	list_str = get_config(section, key)

	if len(list_str) == 0:
		# nothing's in there, so we can just set the list to be the one new element
		set_config(section, key, value_str)
		return True
	else:
		if list_str.find(value_str) == -1:
			list_str = list_str + ',' + value_str
			set_config(section, key, value_str)
			return True
		else:
			print("Attention: Value \"{}\" is already in [{}] {}.".format(value_str, section, key))
			return False

# params: str section, str key, ??? value
# return boolean
def config_list_remove(section, key, value):
	# str value_str
	value_str = str(value)

	# str list_str
	list_str = get_config(section, key)

	if len(list_str) == 0:
		print("Attention: Cannot remove value \"{}\" from empty list [{}] {}.".format(value_str, section, key))
		return False
	elif list_str == value_str:
		list_str = ""
		set_config(section, key, list_str)
		return True
	else:
		# int substr_idx
		substr_idx = list_str.find(value_str)
		if substr_idx != -1:
			if substr_idx + len(value_str) == len(list_str) - 1:
				list_str = list_str.replace(value_str, "")
			else:
				list_str = list_str.replace(value_str + ',', "")
			set_config(section, key, list_str)
			return True
		else:
			print("Attention: Cannot remove value \"{}\" from [{}] {} because the list doesn't contain it.".format(value_str, section, key))
			return False

# params: str value
# return boolean
# copy of ConfigParser._convert_to_boolean()
def convert_to_bool(value):
	if value.lower() not in config.BOOLEAN_STATES:
		raise ValueError('Not a boolean: %s' % value)
	return config.BOOLEAN_STATES[value.lower()]

# params: str section, str key, ??? value
def set_config(section, key, value):
	# stupid Python global nonsense...
	global config
	config[section][key] = str(value)

	try_save()

def try_save():
	# allow multiple config sets to be bundled into one save
	global save_task
	if save_task is None:
		save_task = asyncio.ensure_future(save_config())

async def save_config():
	# clear task
	global save_task
	save_task = None

	global file_name
	# File config_file
	config_file = open(file_name, "w")
	if config_file is not None:
		config.write(config_file)
		print("{} successfully saved".format(file_name))
	else:
		print("{} is missing!  Cannot save!".format(file_name))

# params: str date, str time
# return datetime.DateTime
def parse_datetime(date: str, time: str):
	concat_dt = date + " " + time
	valid_formats = get_config_str_list("Time", "datetime_formats")
	for dt_format in valid_formats:
		try:
			test_dt = datetime.strftime(concat_dt, dt_format)
			return test_dt
		except ValueError:
			# strftime() throws this if the input string doesn't fit the format
			# we're okay with this because we're testing multiple formats
			continue

	raise ValueError("Invalid date format!")