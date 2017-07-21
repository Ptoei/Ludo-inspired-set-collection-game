import tkinter
from Grid import *
import numpy
from Game import *
import configparser

class MainTK:
    def __init__(self,config_file):

        ''' Load game config file '''
        self.log('Retrieving config from  ' + config_file)
        config = configparser.ConfigParser()
        config.read(config_file)

        self.hex_size = config.getint('Visualiser','hex_size') #Horizontal hex size in pixels

        '''Inititalize the functional part of the board grid '''
        self.grid =  Grid(config.getint('Grid','hexes_x'),config.getint('Grid','hexes_y'),self,lambda: 0)

        ''' Convert the coordinates of the hex centers to coordinates in pixels'''
        self.x_pix = (self.grid.x_coords+1)*self.hex_size/2
        self.y_pix = (self.grid.y_coords*0.75+1)*self.hex_size/2 # Hex centers in y dir are actually 0.75 apart

        ''' TKinter reference to the visualisations of currently selected hexes '''
        self.sel_items = []

        ''' List of links to movable items shapes and texts drawn on the board. There can be one object per hex. '''
        self.objects_shape = [None] * self.grid.n_hexes
        self.objects_text = [None] * self.grid.n_hexes

        ''' Create the main screen'''
        self.master = tkinter.Tk()           # The Tkinter master process
        self.board = tkinter.Canvas(self.master, width=(self.grid.size_x+0.5)*self.hex_size, height=(self.grid.size_y+0.35)*self.hex_size*0.75, bd=0,highlightthickness=0) # Canvas for the play board
        self.board.configure(bg="white")    # Set the background color for the playing board
        self.board.grid(column=0,rowspan=8) # Make the height of the board extend over all rows if the rest of the interface as initialized below

        #self.grid.grow_land(config.getint('Grid','n_land'),config.get('Grid', 'tile_file'))    # Create a random map
        self.grid.load_map(config)          # Load map from file

        self.tile_color = self.assign_tile_colors(config)   # Assign colors depending on the terrain type.
        self.visualise_grid(config.get('Debug','show_index'))                               # Draw the map.

        ''' Add end-of-turn button'''
        self.end_turn = tkinter.Button(self.master, text='End turn', command = lambda: self.game.end_player_turn(), anchor='e', justify='left', padx=2) # End of turn
        self.end_turn.grid(column=1,row=0)

        ''' Add a quit botton all the way at the bottom far away from the end turn button.'''
        self.quit_button = tkinter.Button(self.master, text='Quit game', command = lambda: self.kill_choice(), anchor = 'e', justify = 'left',padx=2)
        self.quit_button.grid(column=1,row=7)

        ''' Add indicators for keeping track of the resource drawpile sizes. '''
        tkinter.Label(self.master,text='Resource cards remaining:', font=('bold')).grid(column=1, row=3, sticky='ws')
        self.card_field = tkinter.Text(self.master, width=30, height=5, state='disabled')
        self.card_field.grid(columnspan=2, column=1, row=4, sticky = 'nw')

        tkinter.Label(self.master,text='Messages:', font=('bold')).grid(column=1, row=5, sticky='ws')
        self.message_field = tkinter.Text(self.master, width=30, height=10, state='disabled')
        self.message_field.grid(columnspan=2, column=1, row=6, sticky='nw')

        self.game = Game(config,self.grid,self)             # Initialize the game manager
        self.grid.game = self.game                          # Update the grid's link to the game class, it was set as void before.

        ''' Add score indicators for the players. '''
        tkinter.Label(self.master,text='Player points:', font=('bold')).grid(column=1, row=1, sticky='sw')
        self.score_field = tkinter.Text(self.master, width=30, height=self.game.n_players, state='disabled')
        self.score_field.grid(columnspan=2, column=1, row=2, sticky='nw')
        self.game.update_points()       # Put info in the points field
        self.game.update_card_counts()  # Put info in the resource count field

        self.board.bind("<Button 1>", lambda event: self.click(event))  # Mouse click event for the game map
        self.popup = []         # Iniitialize reference variable to popup windows so we can destroy them from everywhere.
        tkinter.mainloop()      # Start the tkinter loop

    def add_player_tag(self, textbox, message):
        ''' Adds formatting to a text field which highlights the player's name in his color. '''
        if hasattr(self, 'game'): # Prevent the next from running on messages during game init.
            for player in self.game.player_order:
                start = message.find(player)
                if start >-1:
                    textbox.tag_config(player, foreground = getattr(self.game,player).color)
                    textbox.tag_add(player, '1.' + str(start), '1.' + str(start + len(player)))
        else:
            start = -1
        return start

    def assign_tile_colors(self,config):
        ''' Assigns colors to each hex based on the terrain type. Replace with graphics later.'''

        tile_color = ['black']*self.grid.n_hexes # Initialize with default color
        swampcolor = config.get('Visualiser', 'swamp')
        forestcolor = config.get('Visualiser', 'forest')
        meadowcolor = config.get('Visualiser', 'meadow')
        rockcolor = config.get('Visualiser','rock')
        sandcolor = config.get('Visualiser', 'sand')
        homecolor = config.get('Visualiser','home')

        for i in range(0,self.grid.n_hexes):
            if self.grid.tiles[i] == 'swamp':
                tile_color[i] = swampcolor
            if self.grid.tiles[i] == 'forest':
                tile_color[i] = forestcolor
            if self.grid.tiles[i] == 'meadow':
                tile_color[i] = meadowcolor
            if self.grid.tiles[i] == 'rock':
                tile_color[i] = rockcolor
            if self.grid.tiles[i] == 'sand':
                tile_color[i] = sandcolor
            if self.grid.tiles[i] == 'home':
                tile_color[i] = homecolor
            if self.grid.tiles[i] == 'water':
                tile_color[i] = 'blue'

        return tile_color


    def click(self,event):
        ''' Function to be called when the player clicks anywhere on the map. Retrieve the index of the clicked hex 
        based on the x,y coordinates by choosing the hex with shortest distance to center. '''

        if self.popup:          # If a popup window is open, destroy it first.
            self.popup.destroy()
            self.popup = []

        ''' Find the index of the clicked hex '''
        ''' I'll use the squared distances rather than actual distances. This safes a number of square root calculations and the ordering will not be affected.'''
        dist = (self.x_pix - event.x)**2 + (self.y_pix - event.y)**2
        index = numpy.argmin(dist)
        ''' Check whether the clicked pixel is inside the possible location of the "dig" option box '''
        if self.x_pix[index] - 0.3 * self.hex_size < event.x < self.x_pix[index] + 0.3 * self.hex_size and self.y_pix[
            index] - 0.3 * self.hex_size < event.y < self.y_pix[index]:
            self.grid.dig = True
        else:
            self.grid.dig = False

        self.grid.activate_hex(index)    # Activate the grid in the grid manager.

    def draw_hex(self,index,line_color,line_width,fill_color):
        ''' Draws a hex at the specified location. The location and size of the hex is determined by configurable parameters in de grid class '''
        ''' A list of pointers to the drawn objects is returned which can be used to later remove them if necessary. '''

        x_pix = self.x_pix[index]
        y_pix = self.y_pix[index]

        return self.board.create_polygon(x_pix-0.5*self.hex_size+0.5*line_width/2, y_pix-0.25*self.hex_size+0.87*line_width/2,
                                         x_pix-0.5*self.hex_size+0.5*line_width/2, y_pix+0.25*self.hex_size-0.866*line_width/2,
                                         x_pix, y_pix+0.5*self.hex_size-line_width/2,
                                         x_pix+0.5*self.hex_size-0.5*line_width/2, y_pix+0.25*self.hex_size-0.87*line_width/2,
                                         x_pix+0.5*self.hex_size-0.5*line_width/2, y_pix-0.25*self.hex_size+0.87*line_width/2,
                                         x_pix, y_pix-0.5*self.hex_size+line_width/2,
                                         outline=line_color,width=line_width, fill=fill_color)
        self.board.update()

    def draw_object(self, index, object, option='normal'):
        '''Draws an object on the canvas at hex index, either normal or highlighted'''
        obj_x = self.x_pix[index] - 0.2 * self.hex_size
        obj_y = self.y_pix[index] + 0.2 * self.hex_size
        obj_x1 = obj_x
        obj_y1 = obj_y
        obj_x2 = obj_x + self.hex_size * 0.2
        obj_y2 = obj_y + self.hex_size * 0.2

        if option == 'highlight' and 'boat' in object.label:
            self.objects_shape[index] = self.board.create_rectangle(obj_x1, obj_y1, obj_x2, obj_y2, fill=object.color, outline='pink', width=5)
        elif 'boat' in object.label:
            self.objects_shape[index] = self.board.create_rectangle(obj_x1, obj_y1, obj_x2, obj_y2, fill=object.color)
        elif option == 'highlight' and 'team' in object.label:
            self.objects_shape[index] = self.board.create_oval(obj_x1, obj_y1, obj_x2, obj_y2, fill=object.color, outline='pink', width=5)
        elif 'team' in object.label:
            self.objects_shape[index] = self.board.create_oval(obj_x1, obj_y1, obj_x2, obj_y2, fill=object.color)
        elif 'harbour' in object.label or 'home' in object.label:
            ''' Draws the player's harbour at index'''
            x_pix = self.x_pix[index]
            y_pix = self.y_pix[index]
            if option == 'highlight':
                self.objects_shape[index] = self.board.create_polygon(x_pix - 0.4 * self.hex_size, y_pix - 0.3 * self.hex_size,
                                          x_pix + 0.4 * self.hex_size, y_pix - 0.3 * self.hex_size,
                                          x_pix, y_pix + 0.3 * self.hex_size,
                                          fill=object.color, outline='pink', width=5)
            else:
                self.objects_shape[index] = self.board.create_polygon(x_pix - 0.4 * self.hex_size, y_pix - 0.3 * self.hex_size,
                                          x_pix + 0.4 * self.hex_size, y_pix - 0.3 * self.hex_size,
                                          x_pix, y_pix + 0.3 * self.hex_size,
                                          outline='black', fill=object.color)

        else:
            self.log('Error, cannot draw ' + object.label)

    def enemy_resources_popup(self, index):
        '''Prints an overview of the resources in the stack belonging to an object on the board.'''
        this_object = getattr(self.game,self.grid.objects[index]) # Retrieve the object located on hex index
        self.popup = tkinter.Toplevel(self.master)      # Create a popup window and wait for it to close)

        self.popup.title(this_object.label )

        tkinter.Label(self.popup, text = 'opponent resources').grid(row=0, sticky='W')

        isoccupied = ''
        if hasattr(this_object,'occupying_pawn_label'): # Only boats have this attribute
            if len(this_object.occupying_pawn_label) > 1:
                isoccupied = '(pawn)'

        t = tkinter.Text(self.popup, width=30, height=1)
        t.config(wrap=tkinter.WORD)
        t.grid(columnspan=2, row=1)
        t.insert('end',this_object.label + isoccupied + '\n')


        ''' Create radio buttons for stealing one resource.'''
        rows = 2 # Count the number of rows in the popup window
        keep_i = 0 # Dummy for counting the number of resources and updating the total nr of rows in the widget later.
        self.steal_resource_var = tkinter.IntVar()
        for i in range(rows,this_object.resources.get_size()+rows):
            tkinter.Radiobutton(self.popup, text=this_object.resources.stack[i - rows].name, variable=self.steal_resource_var, value=i - rows).grid(row=rows + keep_i, column=1, stick='W')
            keep_i = i
        rows = keep_i

        '''  If a current player ship with moves = 0 and stealing ability is adjacent show a button. '''
        conn_1 = self.grid.get_connections([index], 'all_conn', 1)                                               # Get all hexes one removed
        dest_boat = [x for i, x in enumerate(conn_1) if (self.game.current_player + 'boat') in self.grid.objects[x]]  # Find current players ships one removed
        pirates = [x for i,x in enumerate(dest_boat) if getattr(self.game, self.grid.objects[x]).moves == 0 and getattr(self.game, self.grid.objects[x]).can_steal == True]# Only keep enemy ships that have moves = 0 and can steal = 1

        for i in pirates:
            tkinter.Button(self.popup, text=self.grid.objects[i], command=lambda i=i: self.steal_resource(index, i, self.steal_resource_var)).grid(row = rows+i+1, column=0, sticky='W', pady=4)
            rows = rows + 1

        self.master.wait_window(self.popup)  # Create a popup window and wait for it to close


    def highlight_hex(self,index,type):
        '''Runs draw_hex and adds the reference to the objects to the sel_hex list'''

        if type == 'pawn':
            refs = self.draw_hex(index,'red',4, self.tile_color[index])
        else:
            refs = self.draw_hex(index,'green',4, self.tile_color[index])

        self.sel_items = self.sel_items + [refs]

    def kill(self,message):
        ''' Displays a popup with who won the game. When this is closed, the programm is killed. '''

        self.popup = tkinter.Toplevel(self.master)
        t = tkinter.Text(self.popup,width = 30, height = 10)
        t.insert('end',message)
        t.grid(row=0, column= 0, sticky='W')
        self.master.wait_window(self.popup)  # Create a popup window and wait for it to close
        self.master.quit()

    def kill_choice(self):
        ''' Displays a yes/no option when the quit button is pressed and then acts accourdingly.'''
        if self.popup:
            self.popup.destroy()

        self.popup = tkinter.Toplevel(self.master)
        msg = tkinter.Label(self.popup, text='Are you sure you want to quit?')
        yes = tkinter.Button(self.popup,text = 'Yes',command=lambda: self.game.quit())
        no = tkinter.Button(self.popup,text = 'No',command=lambda: self.popup.destroy())

        msg.grid(row=0,columnspan=2)
        yes.grid(row=1,column=0)
        no.grid(row=1,column=1)

    def log(self, message):
        ''' Logging function. For now it just prints to the command line, but a logfile might be handy at some point.'''
        print(message)

    def message(self, message):
        ''' Prints a message to the message screen on the user interface. '''
        self.log(message)                                   # All messages are sent to the log too
        #self.message_field.tag_config('player', foreground = 'blue')
        self.message_field.config(state = 'normal')         # Enable editing of text
        self.message_field.insert(1.0, message + '\n')      # Add the message at the top of the box
        self.add_player_tag(self.message_field, message)
        self.message_field.config(state = 'disabled')       # Disable editing

    def player_resources_popup(self, index):
        '''Prints an overview of the resources in the stack belonging to an object on the board.'''
        this_object = getattr(self.game,self.grid.objects[index]) # Retrieve the object located on hex index
        self.popup = tkinter.Toplevel(self.master)      # Create a popup window and wait for it to close)

        tkinter.Label(self.popup, text = 'Move resources').grid(columnspan=2, row=0, sticky='W')

        ''' Show object info'''
        ''' First prepare a string to indicate whether the clicked object belongs to the active player.'''
        t = tkinter.Text(self.popup,width=30,height=1)
        t.config(wrap=tkinter.WORD)
        t.grid(columnspan=2,row=1)

        isoccupied = ''
        if hasattr(this_object,'occupying_pawn_label'): # Only boats have this attribute
            if len(this_object.occupying_pawn_label) > 1:
                isoccupied = '(pawn)'

        t.insert('end',this_object.label + '(active)' + isoccupied + '\n')

        ''' TODO Position the popup in the corner furthest away from the clicked hex in order to prevent overlap with reachable hexes. '''
        ''' For now I just position the window right of the board.'''
        y_main = self.master.winfo_y()
        w_main = self.master.winfo_width()
        self.popup.geometry('+' + str(w_main) + '+' + str(y_main))

        ''' Create buttons for shifting resources to neigboring objects if any are present. '''
        ''' Get the indices of hexes one step removed from the active hex and find harboars, homebases and boats.'''
        conn_1 = self.grid.get_connections([index], 'all_conn', 1)
        dest_harbour = [x for i, x in enumerate(conn_1) if (self.game.current_player + 'harbour') in self.grid.objects[x]]
        dest_home = [x for i, x in enumerate(conn_1) if (self.game.current_player + 'home') in self.grid.objects[x]]
        dest_boat = [x for i, x in enumerate(conn_1) if (self.game.current_player + 'boat') in self.grid.objects[x]]

        rows = 2
        ''' For each harbour, home base and boat 1 step removed, add a button for shifting resources.'''
        for i in dest_harbour:
            tkinter.Button(self.popup, text=self.grid.objects[i], command=lambda i=i: self.game.shift_resources(index, i, vars)).grid(row=rows, column=0, sticky='W', pady=4)
            rows = rows + 1

        for i in dest_home:
            tkinter.Button(self.popup, text=self.grid.objects[i], command=lambda i=i: self.game.shift_resources(index, i, vars)).grid(row=rowss, column=0, sticky='W', pady=4)
            rows = rows + 1

        for i in dest_boat:
            # tkinter.Button(popup, text=grid.objects[i], command=print('boat'+str(i))).grid(row=rows+i+1, sticky='W', pady=4)
            tkinter.Button(self.popup, text=self.grid.objects[i], command=lambda i=i: self.game.shift_resources(index, i, vars)).grid(row=rows,
                                                                                               column=0, sticky='W', pady=4)
            rows = rows + 1


        t = tkinter.Text(self.popup,width=30,height=1)
        t.config(wrap=tkinter.WORD)
        t.grid(columnspan=2,row=rows)

        ''' Create a list of checkboxes for all resources'''
        rows = 1 # Count the number of rows in the popup window
        keep_i = 0 # Dummy for counting the number of resources and updating the total nr of rows in the widget later.
        checks = [] # Declare the list of checkboxes
        vars = [] # Declare the list of variables belonging to the checkboxes
        for i in range(rows,this_object.resources.get_size()+rows):
            vars.append(tkinter.IntVar())   # Add a variable to the list
            desc = this_object.resources.stack[i-rows].name + ' (ewsmf: ' + this_object.resources.stack[i-rows].earth + ' ' + \
                this_object.resources.stack[i - rows].wood + ' ' + this_object.resources.stack[i - rows].stone + ' ' + \
                this_object.resources.stack[i - rows].metal + ' ' + this_object.resources.stack[i-rows].fuel + ' ' + \
                this_object.resources.stack[i - rows].collect + ')'

            checks.append([tkinter.Checkbutton(t, text = desc,variable = vars[i-rows]).grid(row = i, column=0,sticky='w')])
            keep_i = i
        rows = keep_i



        ''' For boats belonging to the active player we add a radiobutton with the fuel resources. Changing the dial will change the moveable hexes.'''
        if 'boat' in this_object.label and self.game.current_player in this_object.label and this_object.occupying_pawn_label != '':
            tkinter.Label(self.popup, text='Move options').grid(row=0, column= 1, sticky='W')
            t = tkinter.Text(self.popup, width=30)
            t.config(wrap=tkinter.WORD)
            t.grid(row=1, column=2, sticky='W')

            ''' Create a list of radiobuttons for all resources'''
            self.burn_resource_var = tkinter.IntVar()
            self.burn_resource_var.set(this_object.selected_fuel)  # Set the radiobutton variable to the selected fuel indicator of the boat object
            tkinter.Radiobutton(t, text='Row', variable = self.burn_resource_var, value = -1, command = lambda: self.game.boat_select_fuel(index, self.burn_resource_var.get())).grid(row=1, column=1, stick = 'W')# 0: only use basic moves, don't use fuel
            rows = 2  # Count the number of rows in the popup window
            keep_i = 0
            for i in range(rows, this_object.resources.get_size() + rows):
                if int(this_object.resources.stack[i - rows].fuel) > 0:
                    #tkinter.Radiobutton(self.popup, text=this_object.resources.stack[i - rows].name, variable=burn_resource_var, value = i-rows).grid(row=i, stick='W')
                    tkinter.Radiobutton(t, text=this_object.resources.stack[i - rows].name, variable=self.burn_resource_var, value = i - rows, command = lambda: self.game.boat_select_fuel(index, self.burn_resource_var.get())).grid(row=rows+keep_i, column=1, stick='W')
                    keep_i = keep_i+1  # Count the number of rows in the popup window

        ''' For home bases belonging to the active player we add an overview of the assignment.'''
        if 'home' in this_object.label and self.game.current_player in this_object.label:
            # Retrieve the active player assignment
            assignment = self.game.get_current_player().assignment               # Also used for call by checkbuttons!
            button1, button2 = self.show_assignment(index, self.popup, assignment, vars)
            self.show_resource_choices(index,self.popup,assignment,button1,button2)

        self.master.wait_window(self.popup)  # Create a popup window and wait for it to close

    def remove_object(self,index):
        ''' Removes the object marker at hex index '''
        self.board.delete(self.objects_shape[index])
        self.board.delete(self.objects_text[index])
        self.objects_shape[index] = [None]
        self.objects_text[index] = [None]

    def remove_selected_items(self):
        ''' Removes all highlighted hexes '''
        for i in self.sel_items:
            self.board.delete(i)
        self.sel_items = []

    def show_assignment(self, index, target_canvas, assignment, vars):
        '''Creates a description of the assignment card object in the target_canvas'''
        tkinter.Label(target_canvas, text = 'Assignment').grid(row=0, column=1, sticky='W')
        t = tkinter.Text(target_canvas,width = 30)
        t.config(wrap=tkinter.WORD)
        t.grid(row=1, column= 2, sticky='W')
        t.insert('end', assignment.name + ': ')
        t.insert('end', assignment.description + '\n')
        t.insert('end', 'Stage one description: ' + assignment.tier1_desc + ' After you finish stage one you can gain points from stage 2.' + '\n')
        if assignment.tier1_fulfilled == '0':
            t.insert('end', 'Required resources for stage one: ' "\n")
            for resource in iter(['tier1_req_metal', 'tier1_req_fuel', 'tier1_req_earth','tier1_req_stone', 'tier1_req_wood']):
                if getattr(assignment,str(resource)) != '0':
                    t.insert('end', resource[10:] + ': ' + getattr(assignment,resource) + '\n') # Print the required amount of the resource
            t.insert('end',' Select resources and press fulfill \n')
        else:
            t.insert('end', 'Stage 1 fulfilled: ' "\n")

        b1 = tkinter.Button(t, text='Fulfill',state='disabled', command=lambda: self.game.fulfill_tier1(index, self.res_vars, assignment, target_canvas))
        t.window_create('end', window=b1)

        ''' Assignment stage 2 '''
        t.insert('end', '\n Stage two description: ' + assignment.tier2_desc + "\n")
        if assignment.tier1_fulfilled == '0':
            t.insert('end', 'First complete stage 1')

        b2 = tkinter.Button(t, text='Fulfill',state='disabled', command=lambda: self.game.fulfill_tier2(index, self.res_vars, assignment, target_canvas))
        t.window_create('end', window=b2)
        t.insert('end', "\n" 'Collected:' "\n") # Show the specials which are already added to the assignment
        for i in range(0,assignment.tier2_stack.get_size()):
            t.insert('end', assignment.tier2_stack.stack[i].name + '\n')

        return b1, b2 # The handle to the button can be used to activate/deactive it based on the selected resources.

    def show_resource_choices(self,index,target_canvas,assignment,button1,button2):
        ''' Displays a row of buttons for each resource in a home town. To be used for fulfilling assigments.'''

        ''' Give a title and make a new panel in the popup.'''
        tkinter.Label(target_canvas, text = 'Choose resources for assignment').grid(row=0, column=2, sticky='W')
        t = tkinter.Text(target_canvas,width = 30)
        t.config(wrap=tkinter.WORD)
        t.grid(row=1, column= 3, sticky='W')

        this_object = getattr(self.game,self.grid.objects[index]) # Retrieve the object located on hex index

        ''' Loop over all resources in the home town and all resource types to create the appropriate buttons.'''
        res_labels = ['earth','wood','stone','metal','fuel']
        self.res_vars = []  # Variable for the button presses (has to be persistent).
        for i in range(0,this_object.resources.get_size()):
            self.res_vars.append(tkinter.StringVar())   # Create a new variable for the resource.
            self.res_vars[i].set('none')                # Set the default value to don't use resource.

            ''' Create the button for not using the resource. This is the default value.'''
            tkinter.Radiobutton(t, text="Don't use " + this_object.resources.stack[i].name, indicatoron = 0, variable = self.res_vars[i], command=lambda i=i: self.game.check_assignment(index, self.res_vars,assignment,button1,button2), value = 'none' ).grid(row=i, column=0, stick = 'W')# 0: only use basic moves, don't use fuel

            ''' Loop over the five resource types and create a button if it has a value larger than 0 for this resource. '''
            for j,k in zip(res_labels,range(0,5)):
                if int(getattr(this_object.resources.stack[i],j)) > 0:
                    tkinter.Radiobutton(t, text= getattr(this_object.resources.stack[i], j) + ' ' + j, indicatoron = 0, variable = self.res_vars[i], command=lambda i=i: self.game.check_assignment(index, self.res_vars,assignment,button1,button2), value = j ).grid(row=i, column=k+1, stick = 'W')# 0: only use basic moves, don't use fuel

            ''' Add a final button for the collectible.'''
            if getattr(this_object.resources.stack[i],'collect') != 'none':
                tkinter.Radiobutton(t, text=this_object.resources.stack[i].collect, indicatoron=0, variable=self.res_vars[i],command=lambda i=i: self.game.check_assignment(index, self.res_vars, assignment, button1, button2), value='collect').grid(row=i, column=6,stick='W')  # 0: only use basic moves, don't use fuel


    def steal_resource(self, source_index, destination_index, resource_index):
        ''' Translates the list checkboxes into an index list relating to the resource stack in the source object.
        The list and objects are then passed to game.shift_resources to move the selected resources from source to destination.'''
        select = []
        pirate = getattr(self.game,self.grid.objects[destination_index])
        victim = getattr(self.game,self.grid.objects[source_index])
        pirate.steal_resource_from_boat(victim, resource_index.get())
        self.popup.destroy()

    def show_inactive_hex(self,index):
        '''Draws an an unactivated hex on the board '''
        self.draw_hex(index, 'grey', 2, self.tile_color[index])

    def show_boat_options(self, index):
        ''' Shows the options for a selected boat'''
        boat = getattr(self.game, self.grid.objects[index])
        ''' Show the tiles on a which an occupying pawn, if present, can disembark.'''
        if boat.occupying_pawn_label != '' and boat.moves > 0:
            ''' Find all unoccupied land tiles within moveable distance of the pawn on the boat.'''
            reachable_land = self.grid.get_reachable_land(index)
            ''' Draw a down arrow on all reachable hexes for the pawn'''
            for i in reachable_land:
                x_pix = self.x_pix[i]
                y_pix = self.y_pix[i]
                self.sel_items.append(self.board.create_polygon(x_pix + 0.15*self.hex_size, y_pix+0.3*self.hex_size,
                                x_pix - 0.15*self.hex_size, y_pix+0.3*self.hex_size,
                                x_pix - 0.15*self.hex_size, y_pix,
                                x_pix - 0.25 * self.hex_size, y_pix,
                                x_pix, y_pix - 0.2 * self.hex_size,
                                x_pix + 0.25 * self.hex_size, y_pix,
                                x_pix + 0.15*self.hex_size, y_pix,
                                outline = 'black', fill='white'))

        ''' Show enemy ships which can be boarded and which have something to loot'''
        if boat.moves == 0 and boat.can_steal: # Boat already moved and hasn't stolen in this turn
            reachable_sea = self.grid.get_connections([index],'water_conn',1) # Get all sea hexes one removed. Boat can only steal from neighbouring hexes
            for i in reachable_sea:
                if 'boat' in self.grid.objects[i] and self.game.current_player not in self.grid.objects[i]: # Identify enemy ships
                    if getattr(self.game,self.grid.objects[i]).resources.get_size() > 0:         # Check if there's anything to steal
                        x_pix = self.x_pix[i]
                        y_pix = self.y_pix[i]
                        self.sel_items.append(
                            self.board.create_polygon(x_pix + 0.15 * self.hex_size, y_pix + 0.3 * self.hex_size,
                                                  x_pix - 0.15 * self.hex_size, y_pix + 0.3 * self.hex_size,
                                                  x_pix - 0.15 * self.hex_size, y_pix,
                                                  x_pix - 0.25 * self.hex_size, y_pix,
                                                  x_pix, y_pix - 0.2 * self.hex_size,
                                                  x_pix + 0.25 * self.hex_size, y_pix,
                                                  x_pix + 0.15 * self.hex_size, y_pix,
                                                  outline='black', fill='red'))

    def show_pawn_options(self,index):
        '''Display the dig and move options in the hex'''
        # Only show options if pawn has at least 1 move left and if the resource stack for the occupied landscape type still has cards
        if getattr(self.game,self.grid.objects[index]).moves > 0 and self.grid.get_landscape_stack_size_by_index(index) > 0:
            x_pix = self.x_pix[index]
            y_pix = self.y_pix[index]

            '''Draw the dig option. Add the reference to the dig object to the sel_items list.'''
            self.sel_items.append(self.board.create_polygon(x_pix - 0.3*self.hex_size, y_pix,
                                 x_pix + 0.3*self.hex_size, y_pix,
                                 x_pix + 0.3*self.hex_size, y_pix-0.3*self.hex_size,
                                 x_pix - 0.3*self.hex_size, y_pix-0.3*self.hex_size,
                                 outline = 'black', fill='white'))
            self.sel_items.append(self.board.create_text(x_pix-0.1*self.hex_size,y_pix-0.12*self.hex_size,text='Dig'))

            ''' Draw the boarding option '''
            ''' First, we need to determine if a ship owned by the player is located 1. next to land, 2. within walkable reach and 3. unoccupied.'''
            boats = self.grid.get_reachable_boats(index)
            '''Draw an arrow on the reachable boats'''
            for i in boats:
                x_pix = self.x_pix[i]
                y_pix = self.y_pix[i]
                self.sel_items.append(self.board.create_polygon(x_pix + 0.15*self.hex_size, y_pix-0.3*self.hex_size,
                                x_pix - 0.15*self.hex_size, y_pix-0.3*self.hex_size,
                                x_pix - 0.15*self.hex_size, y_pix,
                                x_pix - 0.25 * self.hex_size, y_pix,
                                x_pix, y_pix + 0.2 * self.hex_size,
                                x_pix + 0.25 * self.hex_size, y_pix,
                                x_pix + 0.15*self.hex_size, y_pix,
                                outline = 'black', fill='white'))

    def update_card_counts(self, sand, forest, meadow, rock, swamp):
        ''' Updates the visualisations of the card counts for the five landscape types.'''
        self.card_field.config(state='normal')              # Enable editing of text
        self.card_field.delete(1.0,tkinter.END)             # Clear the text box, v- insert new text
        self.card_field.insert('end','Sand: ' + str(sand) + '\nForest: ' + str(forest) + '\nMeadow: ' + str(meadow) + '\nRock: ' + str(rock) + '\nSwamp: ' + str(swamp))

        self.card_field.tag_config('sa', foreground = self.game.config.get('Visualiser','sand'))
        self.card_field.tag_add('sa', 1.0, 1.4)
        self.card_field.tag_config('f', foreground = self.game.config.get('Visualiser','forest'))
        self.card_field.tag_add('f', 2.0, 2.6)
        self.card_field.tag_config('m', foreground = self.game.config.get('Visualiser','meadow'))
        self.card_field.tag_add('m', 3.0, 3.6)
        self.card_field.tag_config('r', foreground = self.game.config.get('Visualiser','rock'))
        self.card_field.tag_add('r', 4.0, 4.4)
        self.card_field.tag_config('sw', foreground = self.game.config.get('Visualiser','swamp'))
        self.card_field.tag_add('sw', 5.0, 5.5)

        self.card_field.config(state = 'disabled')          # Disable editing of text

    def update_scores(self):
        if hasattr(self,'score_field'):
            self.score_field.config(state='normal')             # Enable editing of text
            self.score_field.delete(1.0,tkinter.END)            # Clear the text box
            for player in reversed(self.game.player_order):
                new_line = player + ': ' + str(getattr(self.game,player).points) + ' points'
                if player == self.game.current_player:
                    new_line += ' (active)'
                self.score_field.insert(1.0, new_line + '\n')   # Insert the new scores
                start = self.add_player_tag(self.score_field,new_line)  # Color code the player name
                if player == self.game.current_player:          # Highlight the current player
                    self.score_field.tag_config('current', font = 'courier 10 bold italic')
                    self.score_field.tag_add('current', '1.' + str(start), '1.' + str(start + len(player) + 1))
            self.score_field.config(state = 'disabled')         # Disable editing of text

    def visualise_grid(self,show_index):
        ''' Draws the playing board. If show_index is set to "yes", the hex numbers are printed.'''
        if show_index == 'yes':
            print_index = True
        else:
            print_index = False

        for i in range(0,self.grid.n_hexes):
            self.show_inactive_hex(i)
            if print_index:
                self.board.create_text(self.x_pix[i],self.y_pix[i],text=str(i))

