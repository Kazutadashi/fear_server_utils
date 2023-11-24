import re
import time
import datetime


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
    server_status['world_start_time_ms'] = time.time()
    server_status['world_start_time'] = datetime.datetime.now()


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


def get_world_time_elapsed():
    world_elapsed_seconds = time.time() - server_status['world_start_time_ms']
    world_time_minutes_passed = int(world_elapsed_seconds // 60)
    world_time_seconds_passed = int(world_elapsed_seconds % 60)
    formatted_time = '{:02}:{:02}'.format(world_time_minutes_passed, world_time_seconds_passed)
    return formatted_time


def print_output():
    name = server_status['players_connected'][0]['game_name']
    world_time_elapsed = get_world_time_elapsed()
    world_start_time = str(server_status['world_start_time'])
    current_map = server_status['current_world']
    player_count = str(len(server_status['players_connected'])) + '/16'
    connect_time = server_status['players_connected'][0]['connect_time']
    ip_port = server_status['players_connected'][0]['ip_port']
    ping = server_status['players_connected'][0]['ping']
    site_name = server_status['players_connected'][0]['site_name']
    sec2_cd_verified = server_status['players_connected'][0]['sec2_cd_verified']
    guid = server_status['players_connected'][0]['guid']

    display_width = 110

    print(f"""
    ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │{'Server Status: ' + 'Running':<{display_width}}│
    ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │{'Current Map: ' + current_map:<{display_width}}│
    │{'Map Start Time: ' + world_start_time:<{display_width}}│
    │{'Map Time Elapsed: ' + world_time_elapsed:<{display_width}}│ 
    │{'Players: ' + player_count:<{display_width}}│
    │                                                                                                              │
    │Player Info                                                                                                   │
    ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │Name                Connect Time         IP:Port                Ping  SEC2   GUID                             │
    ├──────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │{name:<20}{connect_time:<21}{ip_port:<23}{ping:<6}{sec2_cd_verified:<7}{guid:<33}│
    │KazutadashiKazuman [2023-11-05 21:26:18] 777.777.777.777:12345 1000                                           │
    │                                                                                                              │
    │Kazutadashikazuman 2023-11-05521:26:188777.777.777.777:12345 1000 False 1225b5d2ecc8ce81a3f5bcfde5a72bc9      │
    │Kazutadashikazuman  2023-11-05 21:26:18  777.777.777.777:12345  1000  False  1225b5d2ecc8ce81a3f5bcfde5a72bc9 │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    │                                                                                                              │
    └──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
    \n""")


server_log = open('/home/kazutadashi-lt/Desktop/11052023.log', 'r', errors='replace')


server_status = {
    'loading_world_flag': 0,
    'world_being_loaded': 'none',
    'world_start_time_ms': 0.00,
    'world_start_time': datetime.datetime.now(),
    'current_world': 'none',
    'players_connected': []
}


for line in server_log:

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
        pass


server_log.close()

print_output()
