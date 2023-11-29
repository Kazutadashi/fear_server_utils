import re
import time
import datetime
import os
import sys
import csv
from typing import List
from typing import Optional


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
IP_PATTERN = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
WORLD_NAME_PATTERN = r'\\(\w+)\n'


class Server:
    def __init__(self):
        self.loading_world_flag: bool = False
        self.world_being_loaded: Optional[str] = None
        self.world_start_time_ms: float = 0.00
        self.world_start_time: datetime = datetime.datetime.now()
        self.current_world: Optional[str] = None
        self.players_connected: List[dict] = []
        self.server_status_state: str = '[GOOD]'
        self.de_synced_players: set = set()
        self.last_write_time: datetime = datetime.datetime.now()
        self.player_data_save_path: Optional[str] = None
        self.log_file_path: Optional[str] = None
        self.server_stats_save_path: Optional[str] = None

    def load_world(self, log_file_line: str) -> str:
        """
        Takes in a line from a server log file that starts with 'Loading world' and then scans that line
        for the world name. After finding it, it sets the world name to the match.

        Args:
            log_file_line (str): Log file line generated from the UNIX FEAR server to determine the world

        Returns:
            str: The name of the world that was loaded by the server

        Raises:
            ValueError: The world failed to load or the wrong line was read somehow
        """
        self.loading_world_flag = True

        # Find the name of the world at the end of the loading worlds line
        world_name_match = re.search(WORLD_NAME_PATTERN, log_file_line)

        # if there was a match, set this to the name of the world being loaded.
        if world_name_match:
            world_name = world_name_match.group(1)
            self.world_being_loaded = world_name
            return world_name
        else:
            error_message = (f"The load_world function attempted to load a world and failed." +
                             f"\nLog file line:{log_file_line}")
            self.world_being_loaded = 'FAIL_LOAD'
            raise ValueError(error_message)

    def set_current_world(self) -> None:
        """
        Sets the current world of the server to the world that was loaded

        Returns:
            None: This function does not return anything
        """
        if self.loading_world_flag:
            self.loading_world_flag = False
            self.current_world = self.world_being_loaded
            self.world_being_loaded = None
            self.world_start_time_ms = time.time()
            self.world_start_time = datetime.datetime.now()

        # In cases where players vote for the same map, the "Loading world" prefix never shows up in the log
        # which results in the method load_world never being called.

        # This will create a situation where this method is called, but there is no loading flag set. To handle this
        # We just assume that if this method is called while the loading flag is not set, it must be because
        # players voted for the same map, which means we just need to reset the time.

        elif not self.loading_world_flag:
            # if this is the case we just want to reset the time.
            self.world_start_time_ms = time.time()
            self.world_start_time = datetime.datetime.now()

    def connect_player(self, log_file_line: str) -> int:
        """
        Creates a dictionary object in player_connected that shows the players identity information.
        This information is later used to produce output to stdout in the terminal window

        Args:
            log_file_line (str): Log file line generated from the UNIX FEAR server to determine which player to connect

        Returns:
            int: 1 if a player was added, and 0 if they were not.

        """
        # The log file contains columns separated by spaces. This line lets us split up the information
        # from those columns into something usable for assignment.
        player_details: List[str] = log_file_line.split(']')
        game_name: str = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)

        # If there is no one in the server, add this new player.
        if len(self.players_connected) == 0:
            self.players_connected.append({
                'game_name': game_name,
                'connect_time': player_details[0][1:],
                'ip_port': player_details[1][2:],
                'ping': player_details[2][2:],
                'site_name': None,
                'sec2_cd_verified': None,
                'guid': None
            })
        # If there are other people in the server, and the CLIENT_SUFFIX is found in the log, make sure
        # the player connecting is not somehow someone already in the server. This prevents weird renaming bugs
        else:
            for player in self.players_connected:
                if player['game_name'] == game_name:  # This means the player is already in the server.
                    return 0

            # If we did not hit a match, then this is a new player and we should add them
            self.players_connected.append({
                'game_name': game_name,
                'connect_time': player_details[0][1:],
                'ip_port': player_details[1][2:],
                'ping': player_details[2][2:],
                'site_name': None,
                'sec2_cd_verified': None,
                'guid': None
            })
        return 1

    def disconnect_player(self, log_file_line: str) -> None:
        """
        Disconnects a player from the server.

        This function takes a log file line as input and extracts the game name using `get_game_name`.
        It then rebuilds the `players_connected` list, excluding the player who is to be disconnected.
        This effectively removes the player from the server's list of connected players. If the player
        cannot be found (due to server software bugs), a warning is printed.

        Args:
            log_file_line (str):  Log file line generated from the UNIX FEAR server to
            determine which player to disconnect

        Returns:
            None: This function does not return anything
        """
        game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)
        try:
            # We basically just rebuild the list of dicts here with this comprehension not including
            # the one that needs to be removed, effectively removing it from the list.
            self.players_connected =\
                [player_dict for player_dict in self.players_connected if player_dict['game_name'] != game_name]
        except ValueError as emsg:
            # There seems to be a bug in the linux server software that allows a player to connect without
            # showing up in the logs. Not sure why this happens.
            print(f'[WARNING] Player {game_name} somehow disconnected without ever connecting.\n{emsg})')

    def set_display_name(self, log_file_line: str) -> None:
        """
        After a player connects, a new line in the log file is generated that shows their display name. This method
        captures that display name, and saves it to the player's dict object in players_connected. This allows
        us to then show this on the terminal. Note that the log file calls it a display name, but it is actually
        the name the player created their account with on the fear-community.org website. Because of this, we
        refer to it as the site_name.

        Args:
            log_file_line: Log file line generated from the UNIX FEAR server to determine display name for the
            connecting player.

        Returns:
            None: This function does not return anything

        Raises:
            ValueError: The display name line was found, but there was no game name associated with it.
        """
        game_name = get_game_name(log_file_line, GAME_NAME_INFO_PATTERN)

        if game_name:
            # Search for that player in the list of player_dict objects
            for player in self.players_connected:
                if player['game_name'] == game_name:
                    display_name = re.search(DISPLAY_NAME_PATTERN, log_file_line)
                    if display_name:
                        player['site_name'] = display_name.group(1)
                        break
                    else:
                        player['site_name'] = None
        else:
            error_message = 'There is no game name associated with this player. Something went wrong' +\
                f'Log file line: {log_file_line}'
            raise ValueError(error_message)


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
                    update_player_stats(log_file_line)
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
    # the server does not log when people change their nicks in game
    # This means that if they change their nick, then leave the server
    # the original name for that player will remain connected in the player list
    # even though they are not in the server. I dont know a way around this for now, but
    # this at least tells us when its happening

    list_of_apparent_connected_players = []
    for players in server_status['players_connected']:
        list_of_apparent_connected_players.append(players['game_name'])

    game_name = get_game_name(log_file_line, GAME_NAME_PATTERN)

    # something is wrong if we have a name thats not connected
    # if the name is None we dont care, so we check if the game_name is a truthy value
    if game_name not in list_of_apparent_connected_players and game_name:
        server_status['server_status_state'] = '[WARNING] Unlisted Player(s) In Server!'
        server_status['desynced_players'].add(game_name)


def calculate_world_time_elapsed():
    world_start_time = server_status['world_start_time']
    time_elapsed = datetime.datetime.now() - world_start_time
    seconds_elapsed = time_elapsed.days*24*60*60 + time_elapsed.seconds
    world_time_minutes_passed = int(seconds_elapsed // 60)
    world_time_seconds_passed = int(seconds_elapsed % 60)
    formatted_time = '{:02}:{:02}'.format(world_time_minutes_passed, world_time_seconds_passed)
    return formatted_time


def save_player(log_file_line, player_data_file_path):

    player_name = get_game_name(log_file_line, GAME_NAME_PATTERN)
    player_details = [player for player in server_status['players_connected'] if player['game_name'] == player_name]
    player_dict = player_details[0]

    if not os.path.exists(player_data_file_path):
        f = open(player_data_file_path, "w")
        f.close()

    file_size = os.stat(player_data_file_path).st_size

    with open(player_data_file_path, newline='') as read_file:
        reader = csv.reader(read_file)

        # just add the next value because nothing is in this file
        if file_size == 0:
            pass
        else:
            for row in reader:

                row_ip = re.search(IP_PATTERN, row[2]).group(1)
                player_ip = re.search(IP_PATTERN, player_dict['ip_port']).group(1)

                # Player already exists in file
                if row[0] == player_dict['game_name'] and row_ip == player_ip and \
                   row[4] == player_dict['site_name'] and row[6] == player_dict['guid']:
                    return True  # player already in list, stop the function
                # otherwise add player

    with open(player_data_file_path, 'a') as save_file:
        w = csv.DictWriter(save_file, player_dict.keys())
        w.writerow(player_dict)
    return False


def update_player_stats(log_file_line):
    game_name = get_game_name(log_file_line, GAME_NAME_PATTERN)

    for players in server_status['players_connected']:
        if players['game_name'] == game_name:
            player_details = log_file_line.split(']')
            players['ping'] = player_details[2][2:]


def parse_logs(log_file_lines):
    for line in log_file_lines:

        if line.startswith(LOADING_WORLD_PREFIX):
            load_world(line)
            continue

        if line.startswith(WORLD_LOADED_PREFIX):
            set_current_world(server_status['loading_world_flag'])
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
            if sys.argv[1] != '-n':
                save_player(line, server_status['player_data_save_path'])
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
        with open(filepath, 'r', errors='replace') as file:
            file.seek(last_read_position)
            new_lines = file.readlines()
            last_read_position = current_size

    return last_read_position, new_lines


def save_server_stats(save_file_path):
    # takes a snapshot of some player statistics every 30 seconds so we can see when the server is popular

    current_time_stamp = datetime.datetime.now()

    if (current_time_stamp - server_status['last_write_time']).total_seconds() >= 30:
        current_date = current_time_stamp.date()
        current_time = current_time_stamp.time()
        num_players_in_server = len(server_status['players_connected'])
        current_pings = [float(players['ping'][:-2]) for players in server_status['players_connected']]
        if (len(current_pings) ==
                0):
            min_ping, max_ping, average_ping = 0, 0, 0
        else:
            min_ping = min(current_pings)
            max_ping = max(current_pings)
            average_ping = sum(current_pings) / len(current_pings)

        server_status['last_write_time'] = datetime.datetime.now()

        csv_line = current_date.strftime("%m-%d-%Y") + ',' + current_time.strftime("%H:%M:%S") + ',' +\
            str(num_players_in_server) + ',' + str(min_ping) + ',' + str(max_ping) + ',' + str(average_ping) + '\n'

        with open(save_file_path, "a") as csv_file:
            csv_file.write(csv_line)

        # print(save_file_path)
        # print(current_date, current_time, num_players_in_server, min_ping, max_ping, average_ping, sep=',')
        # print('\n')
        # time.sleep(5)
    else:
        pass


def main():

    if len(sys.argv) <= 2:
        print('No arguments were given.')
        return -1
    elif sys.argv[1] != '-n' and len(sys.argv) < 3:
        print('Required parameters missing. Did you mean to run with \'-n\'?')
    elif sys.argv[1] == '-n':
        if sys.argv[2]:
            try:
                server_status['log_file_path'] = sys.argv[2]
                log_file_path = server_status['log_file_path']
                server_log_lines = open(log_file_path, 'r', errors='replace')
                parse_logs(server_log_lines)
                last_read_position_by_size = os.path.getsize(log_file_path)
                server_log_lines.close()
                while True:
                    last_read_position_by_size, new_lines = read_new_lines(log_file_path, last_read_position_by_size)
                    parse_logs(new_lines)
                    print_output()
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
            except FileNotFoundError:
                print("One or more files were invalid or not found.")

    else:
        try:
            server_status['log_file_path'] = sys.argv[1]
            server_status['server_stats_save_path'] = sys.argv[2]
            server_status['player_data_save_path'] = sys.argv[3]

            log_file_path = server_status['log_file_path'] = sys.argv[1]
            server_stats_save_path = server_status['server_stats_save_path'] = sys.argv[2]

            server_log_lines = open(log_file_path, 'r', errors='replace')
            parse_logs(server_log_lines)
            last_read_position_by_size = os.path.getsize(log_file_path)
            server_log_lines.close()
            while True:
                last_read_position_by_size, new_lines = read_new_lines(log_file_path, last_read_position_by_size)
                parse_logs(new_lines)
                print_output()
                save_server_stats(server_stats_save_path)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
        except FileNotFoundError:
            print("One or more files were invalid or not found.")


if __name__ == '__main__':
    main()
