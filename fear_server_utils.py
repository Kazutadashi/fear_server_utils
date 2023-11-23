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


def add_player(log_file_line):
    player_details = log_file_line.split('] ')
    print(player_details)
    server_status['players_connected'].append(player_details[3][1:])  # using [1:] here to remove the first '[' char


server_log = open('/home/kazutadashi-lt/Desktop/11052023.log', 'r', errors='replace')


server_status = {
    'loading_world_flag': 0,
    'world_being_loaded': 'none',
    'current_world': 'none',
    'players_connected': [],
}


for line in server_log:
    print(line)

    # Check to see if the world load line was entered
    if line[0:13] == 'Loading world':
        load_world(line)

    if line[0:12] == 'World loaded' and server_status['loading_world_flag'] == 1:
        set_current_world()

    print(line[-17:-1])
    if line[-17:-1] == 'Client connected':  # remove the last two chars to avoid newline char
        add_player(line)

    print(server_status)



server_log.close()
