import configparser

# configparser.ConfigParser config
config = None

# return boolean
def setup_config():
	config = configparser.ConfigParser()
	config.read("settings.cfg")
	if config.sections == []:
		print("settings.cfg is missing!")
		return False
	else:
		return True

# params: String section, String key
# return String
def get_config(section, key):
	return config[section][key]

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
	config[section][key] = value

# return boolean
def save_config():
	# File config_file
	config_file = open("settings.cfg", "w")
	if config_file is not None:
		config.write(config_file)
		return True
	else:
		return False