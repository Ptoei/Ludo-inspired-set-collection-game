import tkinter                          # Package for usie io
import configparser                     # Package for handling the input/output from/to config ini files.
import Visualize_tkinter as visualiser  # Runs the main program using tkinter io
import re                               # Regular expression module for checking inputs
import socket                           # Socket package for client/server communication
import threading                        # Multithreading for the socket wait loops
from time import sleep                  # Wait function for the server and client while loops

class Start_menu:
    def __init__(self):
        ''' Shows a startup menu with options to start or join a game and to provide player information. '''

        self.game_config = configparser.ConfigParser()                                  # Config file which stores the player information
        self.game_config.read('Game.ini')

        self.master = tkinter.Tk()  # The Tkinter master process
        name_box_label = tkinter.Label(self.master,text='Your name:').grid(row=0, column=0, sticky='e')

        self.name_box = tkinter.Text(self.master, width=15, height=1)

        self.name_warning = tkinter.StringVar()
        self.name_warning.set('                          ')
        self.name_box_warning = tkinter.Label(self.master, textvariable = self.name_warning, foreground="red")
        self.name_box_warning.grid(row=2, column=0, columnspan=2)

        self.name_box.grid(row=0, column=1)
        self.name_box.insert('end', self.game_config.get('Self','name'))

        self.start_button = tkinter.Button(self.master, text='Start new game', command = lambda: self.start_screen())
        self.start_button.grid(row=3, column=0)

        self.join_button = tkinter.Button(self.master, text='Join game', command = lambda: self.join_screen())
        self.join_button.grid(row=3, column=1)


        tkinter.mainloop()      # Start the tkinter loop

    def join_screen(self):
        ''' Shows the dialogue for joining a game.'''

        self.start_button.destroy()
        self.join_button.destroy()
        self.name_warning.set('                          ')
        self.name_box.config(state='disabled', background="light grey")  # Disable editing

        tkinter.Label(self.master,text='Please fill in host IP and port:').grid(row=4, columnspan=2)
        tkinter.Label(self.master, text='Host IP').grid(row=5, column=0)
        self.host_IP_field = tkinter.Text(self.master, width=15, height=1)
        self.host_IP_field.grid(row=5, column=1)
        self.host_IP_warning = tkinter.StringVar()
        self.host_IP_warning.set('                          ')
        self.host_IP_box_warning = tkinter.Label(self.master, textvariable = self.host_IP_warning, foreground="red")
        self.host_IP_box_warning.grid(row=6, columnspan=2)

        tkinter.Label(self.master, text='Host port').grid(row=7, column=0)
        self.host_port_field = tkinter.Text(self.master, width=15, height=1)
        self.host_port_field.grid(row=7, column=1)
        self.host_port_warning = tkinter.StringVar()
        self.host_port_warning.set('                          ')
        self.host_port_box_warning = tkinter.Label(self.master, textvariable = self.host_port_warning, foreground="red")
        self.host_port_box_warning.grid(row=8, columnspan=2)

        self.join_button = tkinter.Button(self.master, text='Join game', command=lambda: self.join_game())
        self.join_button.grid(row=9, column=0)

    def join_game(self):
        ''' Joins a player to a game hosted on another computer. '''

        ''' Check the IP adress for validity'''
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",self.host_IP_field.get(1.0,'end')):
            self.host_IP_warning.set('Invalid IP adress')
            return
        else:
            self.host_IP_warning.set('')

        ''' Check the port for validity'''
        if not re.match(r"^\d{1,5}$",self.host_port_field.get(1.0,'end')):
            self.host_port_warning.set('Invalid port number')
            return
        else:
            self.host_port_warning.set('')

        self.make_server_socket(1)                                                                              # Create a server socket
        self.make_client_socket(self.host_IP_field.get(1.0,'end'),int(self.host_port_field.get(1.0,'end')))     # Bind to host




    def make_client_socket(self, host, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

    def make_server_socket(self, n):

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a socket
        self.server_socket.bind((socket.gethostname(), 0))                      # Bind socket to computer and generate a port number
        self.server_socket.listen(n)                                            # Open the port for n_players-1 connections

        hostname = socket.gethostname()                                         # Get the name of the computer
        self.IP = socket.gethostbyname(hostname)                                # Get IP adress
        self.port = self.server_socket.getsockname()[1]                         # Store the port number for later reference
        self.server_socket.listen(5)                                            # Allow number of players minus yourself to connect

    def start_screen(self):
        ''' Check the provided name'''
        if not re.match("^[a-z]*$", self.name_box.get(1.0,'end')):
            self.name_warning.set('Single word, letters only.')
            return
        else:
            self.start_button.destroy()
            self.join_button.destroy()
            self.name_warning.set('                          ')
            self.name_box.config(state='disabled', background="light grey")  # Disable editing

            tkinter.Label(self.master,text='Select number of players: ').grid(row=3, column=0, sticky='e')
            self.n_players = tkinter.IntVar()
            self.n_players.set(self.game_config.getint('Players','n_players'))  # default value
            self.n_players_pulldown = tkinter.OptionMenu(self.master, self.n_players, 2, 3, 4, 5)
            self.n_players_pulldown.grid(row=3, column=1)

            self.make_server_socket(self.n_players.get()-1)   # Create a server socket

            tkinter.Label(self.master,text='Setup for new game, provide these to your opponents: ').grid(row=4,column=0,columnspan=2)
            IP_box_label = tkinter.Label(self.master,text='Your IP adress:').grid(row=5, column=0, sticky='e')
            IP_box = tkinter.Text(self.master, width=15, height=1)
            IP_box.grid(row=5, column=1)
            IP_box.insert('end',self.IP)                                         # Put the IP adress in the text field
            IP_box.config(state='disabled', background="light grey")             # Disable editing

            port_box_label = tkinter.Label(self.master,text='Your port:').grid(row=6, column=0, sticky='e')
            port_box = tkinter.Text(self.master, width=15, height=1)
            port_box.grid(row=6, column=1)
            port_box.insert('end', self.port)
            port_box.config(state='disabled', background="light grey")  # Disable editing

            self.open_pressed = False
            #self.open_button = tkinter.Button(self.master, text='Open game', command=lambda: self.set_open_pressed())
            self.open_button = tkinter.Button(self.master, text='Open game', command=lambda: self.open_game())
            self.open_button.grid(row=8, column=0)

    def wait_for_connections(self):
        ''' Detect players connecting'''
        while not self.open_pressed:            # Open_pressed in is connected to the open button
            # accept connections from outside
            self.server_socket.settimeout(1)    # Set a timeout of 1 s. The loop will keep trying to pick up conditions until the open button is pressed.
            try:
                (clientsocket, address) = self.server_socket.accept()                               # Try to accept an incoming connection
                self.player_list[self.n_connected].config(state='normal', background="light grey")  # Enable the new player text field
                self.player_list[self.n_connected].delete('1.0', 'end')                             # Emtpy the old contents
                self.player_list[self.n_connected].insert('end',address)                            # Put the new player in the text field
                self.player_list[self.n_connected].config(state='disabled', background="light grey")# Disable the text field for further manipulation
                self.n_connected += 1                                                               # Increase the number of connected players

            except:
                pass

    def open_game(self):
        self.open_button.destroy()
        self.join_button.destroy()
        self.n_players_pulldown.config(state='disabled')

        self.n_connected = 1  # Number of players connected

        tkinter.Label(self.master, text = '').grid(row=8, column=0)
        tkinter.Label(self.master, text='Waiting for players to join: ').grid(row=9, column=0, columnspan=2)
        tkinter.Label(self.master, text='Player 1').grid(row=10, column=0)
        self.player_list = [None] * int(self.n_players.get())
        self.player_list[0] = tkinter.Text(self.master, width=15, height=1)
        self.player_list[0].grid(row=10, column=1)
        self.player_list[0].insert('end', 'You')
        self.player_list[0].config(state='disabled', background="light grey")  # Disable editing

        for i in range(1, int(self.n_players.get())):
            tkinter.Label(self.master, text='Player ' + str(i+1)).grid(row=10+i, column=0)
            self.player_list[i] = tkinter.Text(self.master, width=15, height=1)
            self.player_list[i].grid(row=10+i, column=1)
            self.player_list[i].insert('end', '...waiting...')
            self.player_list[i].config(state='disabled', background="light grey")  # Disable editing

        thread = threading.Thread(target=self.wait_for_connections)
        thread.start()

        self.start_button = tkinter.Button(self.master, text='Start game', command=lambda: self.start_game())
        self.start_button.grid(row=20, column=0)

    def start_game(self):
        self.open_pressed = True  # Make the server wait loop finish

        self.game_config.set('Players', 'n_players', str(self.n_players.get()))
        self.game_config.set('Self', 'name', self.name_box.get(1.0, 'end'))
        self.game_config.set('Self', 'IP', self.IP)
        self.game_config.set('Self', 'port', str(self.port))

        with open('Game.ini', 'w') as configfile:
            self.game_config.write(configfile)

        self.master.destroy()
        vis = visualiser.MainTK('Config.ini')
