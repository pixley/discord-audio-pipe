import configparser
import asyncio

# configparser.ConfigParser config
config = None
# asyncio.Task save_task
save_task = None
# str file_name
file_name = ""

# params: str cfg_file_name
# return boolean
def setup_config(cfg_file_name):
	global file_name
	file_name = cfg_file_name
	# declare config for use within the function (Python, scope is a thing, bruh)
	global config
	config = configparser.ConfigParser()
	config.read(file_name)
	if config.sections == []:
		print("{} is missing!  Cannot load!".format(file_name))
		return False
	else:
		print("{} successfully loaded".format(file_name))
		return True

# params: String section, String key
# return String
def get_config(section, key):
	if config is not None:
		return config[section][key]
	else:
		raise Exception()

# alias for readability's sake
get_config_string = get_config

# params: String section, String key
# return float
def get_config_float(section, key):
	return float(get_config(section, key))

# params: String section, String key
# return int
def get_config_int(section, key):
	return int(get_config(section, key))

# params: String section, String key
# return boolean
def get_config_bool(section, key):
	return config.getboolean(section, key)

# params: String section, String key, ??? value
def set_config(section, key, value):
	# stupid Python global nonsense...
	global config
	config[section][key] = str(value)

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