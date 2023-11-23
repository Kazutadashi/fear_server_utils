import re


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
    server_status['players_connected'].append({
        'game_name': player_details[3][1:],
        'connect_time': player_details[0][1:],
        'ip_port': player_details[1][1:],
        'ping': player_details[2][1:],
        'site_name': '',
        'sec2_cd_verified': '',
        'guid': ''
    })  # using [1:] here to remove the first '[' char


def disconnect_player(log_file_line):
    player_details = log_file_line.split(']')  # splits the server output into columns
    player = player_details[3][1:]  # using [1:] here to remove the first '[' char (gets the username)
    try:
        # we basically just rebuild the list of dicts here with this comprehension, not including
        # the one that needs to be removed.
        server_status['players_connected'] =\
            [player_dict for player_dict in server_status['players_connected'] if player_dict['game_name'] != player]
    except ValueError as emsg:
        # There seems to be a bug in the linux server software that allows a player to connect without
        # showing up in the logs. Not sure why this happens.
        print(f'[WARNING] Player {player} somehow disconnected without ever connecting.\n{emsg})')


server_log = open('/home/kazutadashi-lt/Desktop/11052023.log', 'r', errors='replace')


server_status = {
    'loading_world_flag': 0,
    'world_being_loaded': 'none',
    'current_world': 'none',
    'players_connected': [],
}



for line in server_log:
    # print(line)
    split_line = line.split(']')  # some things will need the position of the column of output instead
    # TODO: maybe change all of these things to be column based instead of position VV

    # We hard code the locations of these keywords to prevent accidental
    # collision with usernames
    if line[0:13] == 'Loading world':
        load_world(line)

    if line[0:12] == 'World loaded' and server_status['loading_world_flag'] == 1:
        set_current_world()

    if line[-17:-1] == 'Client connected':  # remove the last two chars to avoid newline char
        connect_player(line)

    if line[-20:-1] == 'Client disconnected':  # remove the last two chars to avoid newline char
        disconnect_player(line)

    # Harder to hardcode this one because the position of [CHAT] is variable
    if '[CHAT]' in line:  # TODO: this is dangerous because a player can name themselves chat and mess up stats
        print("this is chat")


    print(server_status)



server_log.close()
