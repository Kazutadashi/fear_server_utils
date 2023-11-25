import re
import time
import datetime
import os
import sys

# prefix constants
LOADING_WORLD_PREFIX = 'Loading world'
WORLD_LOADED_PREFIX = 'World loaded'
CLIENT_CONNECTED_SUFFIX = 'Client connected\n'
CLIENT_DISCONNECTED_SUFFIX = 'Client disconnected\n'
PASSED_SEC2_CD_KEY_CHECK_SUFFIX = 'Client passed cd-key check [SEC2]\n'
DISPLAY_NAME_INDICATOR_PATTERN = r'\[INFO\].*-- Display Name:'
GUID_INDICATOR_PATTERN = r'\[INFO\]: guid:'
DISPLAY_NAME_PATTERN = r'-- Display Name:\s*(\S+)'
GAME_NAME_INFO_PATTERN = r'\[((?:\[.*?\]|[^\[\]])*)\]\s*\[INFO\]:'
GAME_NAME_CHAT_PATTERN = r'\[((?:\[.*?\]|[^\[\]])*)\]\s*\[CHAT\]:'
GAME_NAME_PATTERN = r'\[((?:\[.*?\]|[^\[\]])*)\]\s*\[(?:CHAT|INFO)\]:'
GUID_PATTERN = r'guid:\s*(\S+)'
CHAT_INDICATOR_PATTERN = r'\[CHAT\]:'

server_status = {
    'loading_world_flag': 0,
    'world_being_loaded': 'none',
    'world_start_time_ms': 0.00,
    'world_start_time': datetime.datetime.now(),
    'current_world': 'none',
    'players_connected': [],
    'server_status_state': 'Healthy',
    'desynced_players': set()
}




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
    game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)

    if len(server_status['players_connected']) == 0:
        server_status['players_connected'].append({
            'game_name': game_name,
            'connect_time': player_details[0][1:],
            'ip_port': player_details[1][2:],
            'ping': player_details[2][2:],
            'site_name': '',
            'sec2_cd_verified': '',
            'guid': ''
        })
    else:
        for player in server_status['players_connected']:
            if player['game_name'] == game_name: #  already in players list
                return 0 # we hit a match can stop this function

        # if we did not hit a match, then this is a new player and we should add them
        server_status['players_connected'].append({
            'game_name': game_name,
            'connect_time': player_details[0][1:],
            'ip_port': player_details[1][2:],
            'ping': player_details[2][2:],
            'site_name': '',
            'sec2_cd_verified': '',
            'guid': ''
        })  # using [1:] here to remove the first '[' char


def disconnect_player(log_file_line):
    player = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)
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

    game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)
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
                    player['site_name'] = 'NA'
    else:
        print('No valid game name for this player. Something went wrong?')


def set_guid(log_file_line):
    game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)

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
                    player['guid'] = 'NA'
    else:
        print(f'[WARNING] Unable to set guid for player: {game_name}')


def set_sec2_success_flag(log_file_line):
    game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)

    if game_name:
        for player in server_status['players_connected']:
            if player['game_name'] == game_name:
                player['sec2_cd_verified'] = 'True'
                break
    else:
        print(f'[WARNING] Unable to set sec2 pass flag for player: {game_name}')


def get_game_name(log_file_line, regex_pattern):
    game_name = re.search(regex_pattern, log_file_line)
    if game_name:
        return game_name.group(1)
    else:
        return None


def print_output():

    players = server_status['players_connected']
    total_players = len(players)
    player_lines = ""  # preparing a variable to add the print text later
    max_players = 16
    display_width = 149

    if total_players == 0:
        player_lines = f'│{"":<{display_width}}│'
    else:
        for i, player in enumerate(players):
            name = player['game_name']
            connect_time = player['connect_time']
            ip_port = player['ip_port']
            ping = player['ping']
            site_name = player['site_name']
            sec2_cd_verified = player['sec2_cd_verified']
            guid = player['guid']

            # Format the line for the current player
            # :<8 and other numbers are used to keep things aligned with the f string formatting
            player_line = f"│{name:<22}{site_name:<33}{connect_time:<21}{ip_port:<23}{ping:<10}{sec2_cd_verified:<7}{guid:<33}│"

            # Add newline character only if it's not the last player
            if i < total_players - 1:
                player_line += "\n"

            player_lines += player_line

    world_time_elapsed = calculate_world_time_elapsed()
    world_start_time = str(server_status['world_start_time'])
    current_map = server_status['current_world']
    server_status_state = server_status['server_status_state']
    player_count = str(len(server_status['players_connected'])) + '/' + str(max_players)

    os.system('clear')

    print(f"""
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│{'Server Status: ' + server_status_state:<{display_width}}│
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│{'Current Map: ' + current_map:<{display_width}}│
│{'Map Start Time: ' + world_start_time:<{display_width}}│
│{'Map Time Elapsed: ' + world_time_elapsed:<{display_width}}│ 
│{'Players: ' + player_count:<{display_width}}│
│                                                                                                                                                     │ 
│Player Details                                                                                                                                       │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│Name                  Site Name                        Connect Time         IP:Port                Ping      SEC2   GUID                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
{player_lines}
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
    \n""")


def check_bugged_players(log_file_line):
    # there is a bug with the linux server application where it will sometimes not log
    # the client disconnect message. Possibly if the player crashes or alt f4. The exact reason isn't know
    # but this causes there to be a player who is ALWAYS on the server even when they aren't
    # we need to delete this player so they dont keep messing up stats for historical data
    # for now the only solution I can think is to delete them from the players list after 10 hours or something

    for players in server_status['players_connected']:
        player_connect_time = players['connect_time']
        formatted_player_connect_time = datetime.datetime.strptime(player_connect_time, '%Y-%m-%d %H:%M:%S')
        current_time = datetime.datetime.now()

        time_difference = current_time - formatted_player_connect_time
        difference_in_seconds = time_difference.days*24*60*60 + time_difference.seconds
        if difference_in_seconds >= 43200:  # if the player has been in the server for 12 hours, assume theyre bugged
            disconnect_player(log_file_line)


def check_for_renamed_player(log_file_line):

    list_of_apparent_connected_players = []
    for players in server_status['players_connected']:
        list_of_apparent_connected_players.append(players['game_name'])

    game_name = get_game_name(log_file_line, GAME_NAME_PATTERN)

    # something is wrong if we have a name thats not connected
    # if the name is None we dont care, so we check if the game_name is a truthy value
    if game_name not in list_of_apparent_connected_players and game_name:
        print(f'{game_name} IS NOT IN LIST OF CONNECTED PLAYERS!')
        server_status['server_status_state'] = '[WARNING]: Players De-Synced!'
        server_status['desynced_players'].add(game_name)
        print(server_status['desynced_players'])


def calculate_world_time_elapsed():
    world_start_time = server_status['world_start_time']
    time_elapsed = datetime.datetime.now() - world_start_time
    seconds_elapsed = time_elapsed.days*24*60*60 + time_elapsed.seconds
    world_time_minutes_passed = int(seconds_elapsed // 60)
    world_time_seconds_passed = int(seconds_elapsed % 60)
    formatted_time = '{:02}:{:02}'.format(world_time_minutes_passed, world_time_seconds_passed)
    return formatted_time


def update_player_stats(log_file_line):
    game_name = get_game_name(log_file_line, GAME_NAME_CHAT_PATTERN)

    for players in server_status['players_connected']:
        if players['game_name'] == game_name:
            player_details = log_file_line.split(']')
            players['ping'] = player_details[2][2:]


def parse_logs(log_file_lines):
    for line in log_file_lines:

        if line.startswith(LOADING_WORLD_PREFIX):
            load_world(line)
            continue

        if line.startswith(WORLD_LOADED_PREFIX) and server_status['loading_world_flag'] == 1:
            set_current_world()
            continue

        if line.endswith(CLIENT_CONNECTED_SUFFIX):
            connect_player(line)
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

        if line.endswith(CLIENT_DISCONNECTED_SUFFIX):
            check_for_renamed_player(line)
            check_bugged_players(line)
            disconnect_player(line)
            continue

        if re.search(CHAT_INDICATOR_PATTERN, line):
            check_for_renamed_player(line)
            check_bugged_players(line)
            update_player_stats(line)
            continue



        # TODO: save results over time for statistics


def read_new_lines(filepath, last_read_position):
    """
    Reads new lines from the file that were added after the last_read_position.

    Args:
    filepath (str): Path to the file.
    last_read_position (int): The position in the file from where to start reading.

    Returns:
    tuple: A tuple containing the updated last_read_position and a list of new lines.
    """
    new_lines = []
    current_size = os.path.getsize(filepath)

    if current_size > last_read_position:
        with open(filepath, 'r') as file:
            file.seek(last_read_position)
            new_lines = file.readlines()
            last_read_position = current_size

    return last_read_position, new_lines


def main():

    try:
        log_file_path = sys.argv[1]
        server_log_lines = open(log_file_path, 'r', errors='replace')
        parse_logs(server_log_lines)
        last_read_position_by_size = os.path.getsize(log_file_path)
        server_log_lines.close()
        while True:
            print(server_status)
            last_read_position_by_size, new_lines = read_new_lines(log_file_path, last_read_position_by_size)
            parse_logs(new_lines)
            print_output()
            time.sleep(1)
    except IndexError:
        print("No file path was given. Quitting...")
    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == '__main__':
    main()
