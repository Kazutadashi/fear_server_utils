# UNIX FEAR Server Utilities
This is a program designed to give hosters more information about their FEAR Server, as well as additional tracking for players over time. Currently there is very little that comes with the built in UNIX based FEAR Server. There are few logging options and no designated display to determine the current status of the server. Using the generated log files, we can build up to the current status of the server to display a nice, easy to see at a glace display about the state of the server. This code has been tested successfully using python 3.7.3.
## Instructions
To begin, start your FEAR server and redirect stdout to a log file of your choosing
```
$ cd /path/to/server
$ ./start.sh > server_log_file.log
```
This will begin your server and start tracking events that happen in the game, such as connections, map changes, and chat messages. 

After this, enable the display and specify your data files with the following
```
$ python3 fear_server_utils.py <path to log file> <path to server stats data file> <path to player data file>
```
In our example this might look something like this
```
$ python3 fear_server_utils.py ~/FEARServer/server_log_file.log ~/Documents/DataFiles/server_stats.csv ~/DataFiles/players.csv
```
If everything was successful, you should now see your server

![ServerDisplay](https://github.com/Kazutadashi/fear_server_utils/assets/40162378/60f1696e-a4e2-46c2-8f25-f2add06afc17)
## Data Files
The server saves data to two user specified files which track the following:

- Server Information (Records data every 30 seconds)
  - Time and date of when the data was saved
  - How many players are in the server
  - Minimum ping
  - Maximum ping
  - Average ping

- Player Information (Records when a player connects):
  - In-game name
  - Date and time player connected to the server
  - IP:Port of the connection
  - Ping
  - Name used to register for the SEC2 CD Key
  - Whether or not the player passed the SEC2 check
  - The player's GUID


This information can then be used to plot player counts overtime to see what times are popular for a specific server, as well as track hackers
and other malicious players even when smurfing. In our example, the contents of the files would look like this:
```
$ cat example_server.csv

XxFioraMaster18xX,2023-12-02 19:26:18,12.34.56.78:48421,96.25ms,Example_Player1,True,22a373ba18ec39b6d93222a373ba18ec
G2A2Lover,2023-12-02 19:26:18,12.34.56.78:48421,50ms,Example_Player2,True,22a373ba18ec39b6d93222a373ba18ec
boblol,2023-12-02 19:26:18,11.11.11.11:48421,24.1ms,Example_Player3,True,6d93222a373ba18ec93222a373ba18ec
whybad?,2023-12-02 19:26:18,98.76.5.4:48421,183.37ms,Example_Player4,True,32a373ba18ecba18ec93222373ba18e6
TekkenGodOmega,2023-12-02 19:26:18,99.99.99.99:48421,150.11ms,Example_Player5,True,24a373baecba18ec932222a373ba18ef
Player,2023-12-02 19:26:18,101.102.103.104:48421,201.98ms,Example_Player6,True,92a373ba18ec39b6d93222a932222a37
Jugador,2023-12-02 19:26:18,255.255.255.255:48421,47ms,Example_Player7,True,20a373ba18ec39b6d93222a932221239
```

```
$ cat example_player.csv

12-02-2023,21:08:30,7,24.1,201.98,107.54428571428572
12-02-2023,21:09:00,7,24.1,201.98,107.54428571428572
12-02-2023,21:09:30,7,24.1,201.98,107.54428571428572
12-02-2023,21:10:00,7,24.1,201.98,107.54428571428572
12-02-2023,21:10:30,7,24.1,201.98,107.54428571428572
12-02-2023,21:11:00,7,24.1,201.98,107.54428571428572
12-02-2023,21:11:30,7,24.1,201.98,107.54428571428572
12-02-2023,21:12:00,7,24.1,201.98,107.54428571428572
12-02-2023,21:12:30,7,24.1,201.98,107.54428571428572
12-02-2023,21:13:00,7,24.1,201.98,107.54428571428572
```

## Additional Information
### tmux
It is highly recommended setup a script that manages these applications using tmux, especially if doing things over ssh as it can make it much
easier to interact with and view. More information on tmux can be [found on their github](https://pages.github.com/](https://github.com/tmux/tmux/wiki)https://github.com/tmux/tmux/wiki).
### Player Data File
The player data file will only record unique rows. That is, if the in-game name, IP, website name, or GUID is different than any other row in the file, it will
record this as a new player and add an additional row. This is to help track malicious players if they switch IP addresses, or in-game names.
### Ping Updates
Because there is no real time information given to the hoster, the closest we can get is by tracking CHAT or INFO messages. Anytime a player generates one
of these types of lines in the log files, we use all the information we can to update the current status of the player, which for now is just the ping. 

## Bugs
If a player changes their name during the match, and then leaves the server with that different name, the terminal display window will never show them as having left. 
Unfortunately the server does not log or show anything regarding name changes, so there is no way for the hoster to know who changed their name or is really still connected.
As a temporary workaround, if a player remains "connected" for 12 hours or more, they are "disconnected" from the server and removed from the output and tracking.

