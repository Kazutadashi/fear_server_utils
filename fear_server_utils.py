import re


# prefix constants
LOADING_WORLD_PREFIX = 'Loading world'
WORLD_LOADED_PREFIX = 'World loaded'
CLIENT_CONNECTED_SUFFIX = 'Client connected\n'
CLIENT_DISCONNECTED_SUFFIX = 'Client disconnected\n'
PASSED_SEC2_CD_KEY_CHECK_SUFFIX = 'Client passed cd-key check [SEC2]\n'
DISPLAY_NAME_INDICATOR_PATTERN = r'\[INFO\].*-- Display Name:'
GUID_INDICATOR_PATTERN = r'\[INFO\]: guid:'
DISPLAY_NAME_PATTERN = r'-- Display Name:\s*(\S+)'
GAME_NAME_PATTERN = r'\[((?:\[.*?\]|[^\[\]])*)\]\s*\[INFO\]:'
GUID_PATTERN = r'guid:\s*(\S+)'


def load_world(log_file_line):
    server_status['loading_world_flag'] = 1

    # Find the name of the world at the end of the loading worlds line
    world_name_match = re.search(r"\\(\w+)\n", log_file_line)

    # if there was a match, set this to the name of the world being loaded.
    if world_name_match:
        server_status['world_being_loaded'] = world_name_match.group(1)
    else:
        server_status['world_being_loaded'] = 'World loading seemed to fail.'


def set_current_world():
    server_status['loading_world_flag'] = 0
    server_status['current_world'] = server_status['world_being_loaded']
    server_status['world_being_loaded'] = 'None'


def connect_player(log_file_line):
    player_details = log_file_line.split(']')  # splits the server output into columns

    # We use [2:] to remove the first ' [' chars
    server_status['players_connected'].append({
        'game_name': player_details[3][2:],
        'connect_time': player_details[0][2:],
        'ip_port': player_details[1][2:],
        'ping': player_details[2][2:],
        'site_name': '',
        'sec2_cd_verified': '',
        'guid': ''
    })  # using [1:] here to remove the first '[' char


def disconnect_player(log_file_line):
    player_details = log_file_line.split(']')  # splits the server output into columns
    player = player_details[3][2:]  # using [2:] here to remove the first ' [' chars (gets the username)
    try:
        # we basically just rebuild the list of dicts here with this comprehension, not including
        # the one that needs to be removed.
        server_status['players_connected'] =\
            [player_dict for player_dict in server_status['players_connected'] if player_dict['game_name'] != player]
    except ValueError as emsg:
        # There seems to be a bug in the linux server software that allows a player to connect without
        # showing up in the logs. Not sure why this happens.
        print(f'[WARNING] Player {player} somehow disconnected without ever connecting.\n{emsg})')


def set_display_name(log_file_line):

    game_name = get_game_name(log_file_line)
    # if they have a valid game name
    if game_name:
        # search for that player in the list of player_dict objects
        for player in server_status['players_connected']:
            # when you find the match
            if player['game_name'] == game_name:
                # see what the display name is in the log file
                site_name_match = re.search(DISPLAY_NAME_PATTERN, log_file_line)
                # if there is a valid display name, set it, otherwise set it to None
                if site_name_match:
                    player['site_name'] = site_name_match.group(1)
                    break
                else:
                    player['site_name'] = None
    else:
        print('No valid game name for this player. Something went wrong?')


def set_guid(log_file_line):
    game_name = get_game_name(log_file_line)

    # if they have a valid game name
    if game_name:
        # search for that player in the list of player_dict objects
        for player in server_status['players_connected']:
            # when you find the match
            if player['game_name'] == game_name:
                # see what the guid is in the log file
                guid_search = re.search(GUID_PATTERN, log_file_line)
                # if there is a valid guid, set it, otherwise set it to None
                if guid_search:
                    player['guid'] = guid_search.group(1)
                    break
                else:
                    player['guid'] = None
    else:
        print(f'[WARNING] Unable to set guid for player: {game_name}')


def set_sec2_success_flag(log_file_line):
    game_name = get_game_name(log_file_line)

    if game_name:
        for player in server_status['players_connected']:
            if player['game_name'] == game_name:
                player['sec2_cd_verified'] = 'True'
                break
    else:
        print(f'[WARNING] Unable to set sec2 pass flag for player: {game_name}')


def get_game_name(log_file_line):
    game_name = re.search(GAME_NAME_PATTERN, log_file_line)
    if game_name:
        return game_name.group(1)
    else:
        return None


server_log = open('/home/kazutadashi-lt/Desktop/11052023.log', 'r', errors='replace')


server_status = {
    'loading_world_flag': 0,
    'world_being_loaded': 'none',
    'current_world': 'none',
    'players_connected': [],
}


for line in server_log:
    # We hard code the locations of these keywords to prevent accidental
    # collision with usernames
    print(server_status)
    print(line)

    if line.startswith(LOADING_WORLD_PREFIX):
        load_world(line)
        continue

    if line.startswith(WORLD_LOADED_PREFIX) and server_status['loading_world_flag'] == 1:
        set_current_world()
        continue

    if line.endswith(CLIENT_CONNECTED_SUFFIX):
        connect_player(line)
        continue

    if line.endswith(CLIENT_DISCONNECTED_SUFFIX):
        disconnect_player(line)
        continue

    if re.search(DISPLAY_NAME_INDICATOR_PATTERN, line):
        set_display_name(line)
        continue

    if line.endswith(PASSED_SEC2_CD_KEY_CHECK_SUFFIX):
        set_sec2_success_flag(line)
        continue

    if re.search(GUID_INDICATOR_PATTERN, line):
        set_guid(line)
        continue

    # Harder to hardcode this one because the position of [CHAT] is variable
    if '[CHAT]' in line:  # TODO: this is dangerous because a player can name themselves chat and mess up stats
        print("this is chat")


server_log.close()
