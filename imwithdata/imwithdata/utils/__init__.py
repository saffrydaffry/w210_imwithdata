from configparser import ConfigParser

# --- Helpers --- #
def get_ini_vals(ini_file, section):
    """Get a configurations for particular service
    :param ini_file: Location of ini_file
    :param section: Name of service (as .ini section header) to get config s for
    :return: ConfigParser Section
    """
    config = ConfigParser()
    config.read(ini_file)
    return config[section]