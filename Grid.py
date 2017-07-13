from numpy.lib.function_base import select
import numpy
import configparser
from Cards import *

class Grid:
    '''Hexagonal grid for board management'''
    def __init__(self,size_x,size_y):

        '''Creates centre coordinates of the hexagonal grids. Center of bottom left hex is 0,0. All hexes have a diameter of 2. size_y
        is rounded up to an even number.'''
        
        ''' The hex coordinates are generated by staggering the x-coordinates of the even y-coordinates. The staggers are generated by
        repeating a [0,1] vector and reshaping. To make this work correctly, we need to add an even number of y-coordinates during the
        coordinate calculations.   '''
        
        # Make sure we get to all coordinates without problems by rounding to even numbers for the y-coordinate. Afterwards we truncate.
        size_y = int(2*numpy.ceil(size_y/2))
        
        print('Initializing board of ' + str(size_x) + ' by ' +  str(size_y)  + ' hexes.')
        
        self.size_y = size_y
        self.size_x = size_x
        self.n_hexes = size_y*size_x

        self.dig = False # Variable to indicate whether the location of the "dig" option in a selected hex is clicked.

        # Generate the y-coordinates by repeating the y_coordinates 'size_x' times and transposing to x-first matrix orientation. 
        # NB, the hex centers in y direction are in reality 0.75 apart. To mame things easier, I account for this in the visualizer.
        self.y_coords = numpy.array(list(range(0,2*size_y,2))*size_x).reshape(size_x,size_y).transpose().ravel()
        # The x-coordinates for the even y-coordinates need to be staggered by half a hex. We generate this by repeating [0,1]
        # x*y_rounded times, turning it into a mateix, transposing it and turning it into an array.
        x_stagger = numpy.array(list(range(0,2))*int(self.n_hexes/2))
        x_stagger = x_stagger.reshape(size_x,size_y).transpose().ravel() #reshape(size_x*size_y,1) #2= numpy.reshape(x_stagger)
        # The stagger values (0 or 1) are added to an array containing x coordinates (0-size_x repeated size_y times). 
        self.x_coords = numpy.add(numpy.array(list(range(0,2*size_x,2))*size_y), + x_stagger)
                
        
        self.tiles = list(['']*self.n_hexes)        # List with labels containing the tile type for each hex.
        self.objects = list(['']*self.n_hexes)      # List of objects (guys, boats) on the grid
        '''self.object_owner = list(['']*self.n_hexes) # List of owners (players) of the objects in self.objects'''
        
        ''' Index of the hex containing the currently selected pawn '''
        self.selected = []
        ''' Index list of the hexes reachable for the currently selected pawn'''
        self.select_reachable  = numpy.array([])

        # The hexes at the edges and corners of the board have less than 6 connections and need to handled separately/
        north = numpy.array(range(1,size_x-1,1))
        west = numpy.array(range(size_x,size_x*(size_y-1),size_x))
        south = numpy.array(range(size_x*(size_y-1)+1,self.n_hexes-1,1))
        east = numpy.array(range(2*size_x-1,size_x*(size_y-1),size_x))
    
        north_west = 0
        north_east = size_x-1
        south_west = size_x*(size_y-1)
        south_east = self.n_hexes-1

        # List of all hexes
        self.all_hexes = numpy.array(range(0,self.n_hexes))
        
        # For assigning the oblique connections we need to distinguish between even and uneven rows.
        odd_rows = self.all_hexes[numpy.in1d(self.y_coords,numpy.array(range(0,size_y*2,4)))]
        even_rows = self.all_hexes[numpy.in1d(self.y_coords,numpy.array(range(2,size_y*2,4)))]
       
        # Now we the determine which hexes are not at the edges by concatenating all edges...        
        edge = numpy.concatenate([south,east,west,north,[south_east,south_west,north_east,north_west]])
        # ...and removing them from a list of all hexes on the grid.
        inside = numpy.setdiff1d(self.all_hexes,edge)
       
        # Now we need to process each of the six connectivity directions separately by listing the hex indices for which the direction applies.
        # The connections are stored in a matrix, where the rows identify the hex of origin and the rows the destination.
        
        # Initialize the connectivity matrix with zeros. It kind of makes sense to use booleans for this, but that seems
        # to make the matrix multiplications in we do to get n-step connections a lot slower. Maybe they're cast to numericals?
        # Anyway, I'm not using booleans because it's slow.
        self.all_conn_1 = numpy.zeros((self.n_hexes,self.n_hexes))
        # Connections to the east
        select = numpy.concatenate([inside,west,south,north,[south_west,north_west]])
        self.all_conn_1[(select),(select)+1] = 1
        # Connections to the west
        select = numpy.concatenate([inside,east,south,north,[south_east,north_east]])
        self.all_conn_1[(select),(select)-1] = 1
          
        # north-west connections
        # Odd.
        select = numpy.intersect1d(numpy.concatenate([inside,east,south]),odd_rows)
        self.all_conn_1[(select),(select)-size_x-1] = 1
        # Even
        select = numpy.intersect1d(numpy.concatenate([inside,east,south,west,[south_west, south_east]]),even_rows)
        self.all_conn_1[(select),(select)-size_x] = 1
                       
        # Connections to the south-east
        # Odd
        select = numpy.intersect1d(numpy.concatenate([inside,west,north,east,[north_west, north_east]]),odd_rows)
        self.all_conn_1[(select),(select)+size_x] = 1
        #Even
        select = numpy.intersect1d(numpy.concatenate([inside,west,north]),even_rows)
        self.all_conn_1[(select),(select)+size_x+1] = 1
        
        # Connections to the north-east
        # Odd
        select = numpy.intersect1d(numpy.concatenate([inside,west,east,south]),odd_rows)
        self.all_conn_1[(select),(select)-size_x] = 1
        # Even
        select = numpy.intersect1d(numpy.concatenate([inside,west,south,[south_west]]),even_rows)
        self.all_conn_1[(select),(select)-size_x+1] = 1
        
        # Connections to the south-west
        # Odd
        select = numpy.intersect1d(numpy.concatenate([inside,north,east,[north_east]]),odd_rows)
        self.all_conn_1[(select),(select)+size_x-1] = 1
        # Even
        select = numpy.intersect1d(numpy.concatenate([inside,north,east,west]),even_rows)
        self.all_conn_1[(select),(select)+size_x] = 1
        
    def activate_hex(self,visualiser,game,index):
        ''' Spaghetti which handles the events when a player clicks a hex '''

        visualiser.remove_selected_items()
        if self.selected == [] and self.objects[index] == '':
            ''' Do nothing'''
            print('Nothing here to do on hex ' + str(index))

        elif self.selected == index and self.dig and 'team' in self.objects[index] and self.get_landscape_stack_size_by_index(game,index) > 0:
            ''' If a pawn is selected and the clicked index is the selected index and the drawpile for the landscape is not empty, check whether the "dig" option was clicked.'''
            print('Digging...')
            '''The drawpile of the tile type gives a resource to the stash of the activeplayer'''
            getattr(game,self.tiles[index]+'_drawpile').give_card(getattr(game,game.player_order[game.player_index] + 'harbour').resources) # Get a card from the appropriate stack and move it to the player's harbour
            getattr(game,self.objects[self.selected]).use_moves(1)          # Deduct one move for the pawn
            self.deselect_object(visualiser, game)                          # Deselect the hex
            game.update_card_counts(visualiser)                             # Update the card counts

        elif self.selected and 'boat' in self.objects[index] and game.current_player in self.objects[index]:
            ''' If a pawn is selected and the clicked index contains a boat, check whether the boat is 1. reachable and
            2. belongs the the active player. If so, move the selected pawn into the boat. '''
            if 'team' in self.objects[self.selected]:
                if index in self.get_reachable_boats(game, self.selected):
                    ''' Move the pawn into the boat'''
                    print('Moving pawn ' + getattr(game,self.objects[self.selected]).label + ' into boat' + getattr(game,self.objects[index]).label)
                    not_removed =  getattr(game,self.objects[index]).occupy(getattr(game,self.objects[self.selected]))
                    if not_removed == '':
                        moved_pawn = self.selected
                        self.deselect_object(visualiser, game)
                        self.remove_object(visualiser, game, moved_pawn)
                    else:
                        self.select_object(visualiser, game, self.selected)
                else:
                    print('Boat ' + getattr(game,self.objects[index]).label + ' too far removed from pawn ' + getattr(game,self.objects[self.selected]).label)
                    self.select_object(visualiser, game, self.selected)
            else: # The previously selected object wasn't a pawn, so just activate the boat
                self.deselect_object(visualiser, game)
                self.select_object(visualiser, game, index)

        elif 'harbour' in self.objects[index] or 'home' in self.objects[index]:
            '''Display the resources stored by the owner of the harbour'''
            #visualiser.show_resources(index,getattr(game,self.objects[index]).resources)
            if self.selected:
                self.deselect_object(visualiser,game)
            self.select_object(visualiser, game, index)

        elif self.selected and not self.objects[index]:
            ''' If a boat is selected which has a pawn, we see if the pawn can disembark. If the index hex contains an enemy ship, we try to steal from it.'''
            if 'boat' in self.objects[self.selected]:
                if getattr(game,self.objects[self.selected]).occupying_pawn_label != '':
                    if index in(self.get_reachable_land(game, self.selected)):  # Disembark the occupying pawn to the index hex
                        self.place_object(visualiser,getattr(game,getattr(game,self.objects[self.selected]).unboard()),index) # The boat object is retrieved, the pawn is unboarded which returns the pawn label, which is in turn used to get the pawn object

            if 'team' in self.objects[self.selected] or 'boat' in self.objects[self.selected]:
                ''' If a pawn/boat is selected and no object is in the clicked hex, we attempt to move the selected pawn. '''
                try:
                    print('Attempt to move pawn to ' + str(index))
                    found = self.select_reachable.tolist().index(index) #This is just a trick to generate an exception if index is empty
                    self.move_object(visualiser,game, index)
                    visualiser.remove_selected_items()
                    self.selected = []

                except ValueError:
                    '''deselect pawn'''
                    self.deselect_object(visualiser,game)
                    print('Cannot move object to hex ' + str(index))

            '''If an object is found on the hex AND it belongs to the active player, select it. '''
        else:
            print('Activating ' + self.objects[index] + ' found on hex ' + str(index))
            ''' If an object is already selected, then deselect that before selecting the new one '''
            if self.selected:
                self.deselect_object(visualiser,game)
            if getattr(game,self.objects[index]).owner == game.current_player:
                self.select_object(visualiser, game, index)
            else:
                self.select_enemy_object(visualiser,game,index)

    def deselect_object(self,visualiser,game):
        if self.selected == []: # Escape the method if nothing is selected
            return
        this_pawn = getattr(game,self.objects[self.selected])
        visualiser.remove_object(self.selected)
        visualiser.remove_selected_items()
        '''If the pawn belongs to the active player and has moves left, it needs to be highliighted, '''
        if this_pawn.owner == game.current_player and this_pawn.moves > 0:
            visualiser.draw_object(self.selected,this_pawn,'highlight')
        else:
            visualiser.draw_object(self.selected,this_pawn)
        ''' Clear the index of the currently selected hex '''
        self.selected = []
        self.selected_reachable = []
                  
    def get_connections(self,index_list,conn_list_name,dist):
        ''' Returns all hex indices of tiles which are dist away from all hexes in index_list according to connectivity matrix conn_list_name'''
        # Check if the list of connections has been extended far enough to fulfill the request. If not then add it.
        try:
            print('Retrieving connections ' + conn_list_name + '_' + str(dist))
            connections = getattr(self, conn_list_name + '_' + str(dist))

        except AttributeError:
            print('Generating ' + str(dist) + '-step connectivity matrix for ' + conn_list_name)
            ''' Retrieve the dist-min-1-step connectivity for conn_list_name. 
            If this isn't found, it is created by running this function recursively.'''
            try:
                connection_dist_min_one = getattr(self, conn_list_name + '_' + str(dist-1))
            except AttributeError:
                self.get_connections(index_list,conn_list_name,dist-1)
                connection_dist_min_one = getattr(self, conn_list_name + '_' + str(dist - 1))

            ''' Somehow, if we just exponate the connectivities which have narrow bridges, there are steps missing. 
            We fix this by multipling dist-min-one connectivity with the full connectivity and then removing the 
            rows and columns of the unreachable hexes according to the original connectivity matrix of dist-min-one.'''
            all_conn_1 = getattr(self,'all_conn_1')       # Get the connectivity for all hexes
            connections = numpy.add(numpy.dot(connection_dist_min_one,all_conn_1),connection_dist_min_one)  # Calculate the dist-steps connectivity
            remove = numpy.where(sum(connection_dist_min_one) == 0)
            connections[remove,:] = 0
            connections[:,remove] = 0
            setattr(self,conn_list_name + '_' + str(dist), connections)       # Store the new connectivity matrix because we will probably need it again

        # Return indices to the columns which contain a number for any of the rows in Index_list, excluding the hexes in index_list themselves
        return numpy.setdiff1d(numpy.where(connections[index_list,:].sum(0)>0), index_list)

    def get_landscape_stack_size_by_index(self,game,index):
        ''' Returns the number of resources still available in the stack of the landscape of hex index.'''
        return getattr(game,self.tiles[index]+'_drawpile').get_size()

    def get_reachable_boats(self,game,index):
        ''' Returns a list of indices for hexes containing a boardable boar for a pawn located at index.'''
        pawn_moves = getattr(game,self.objects[index]).moves
        # 1. Retrieve reachable land hexes. There needs to be one move left to hop to the ship, so I need to get the
        # reachables for moves-1.
        if pawn_moves == 0:
            return numpy.array([])      # If the pawn has no moves, then nothing is returned
        else:
            if pawn_moves == 1:
                reachable_land = numpy.array(index) # In case move is already 1, I only select the Index of the pawn otherwise I get a crash.
            else:
                reachable_land = numpy.append(self.get_connections([index], 'land_conn', pawn_moves-1),index)
            # 2. Retrieve all tiles which are 1 step removed from the reachable hexes
            water_1 = self.get_connections(numpy.append(reachable_land,index), 'all_conn',1)
            # 3. Retrieve all tiles which are within moveable distance for the pawn, regardless of terrain type
            reachable_all = self.get_connections([index], 'all_conn', pawn_moves)
            # 4. Select indexes which are the overlap of 2 and 3. The result includes some land tiles, but since these won't have any boats it's not a problem.
            next_to_land = numpy.intersect1d(water_1, reachable_all)
            # Now iterate over the resulting tiles to find boats belonging to the player and which are unoccupied
            reachable_boats = []
            for i in next_to_land:
                if self.objects[i]: # Check if there is an object on the tile
                    obj_ref = getattr(game,self.objects[i]) # Retrieve the object on the tile
                    if obj_ref.owner == game.current_player and 'boat' in obj_ref.label: # check if the object is a boat and if it belongs to the active player
                        if obj_ref.occupying_pawn_label == '': # Need to put this condition separate since non-boat objects don't have this field
                            reachable_boats.append(i)
            return reachable_boats

    def get_reachable_hexes(self,index,pawn):
        '''Returns a list of all hexes that are reachable for the pawn.'''
        
        ''' Retrieve the hexes which are within reach. The connectivity matrix depends on the tile type (i.e. land for
        pawns, water for boats). If the ring parameter of the object is set to 0, the whole surface within reach of 
        pawn.moves can be reached. If ring is any positive integer value, a ring of reachable hexes is generated. This 
        is the case for boats. '''
        if pawn.moves > 0 and pawn.ring < 1:    # The all hexis within pawn.moves distance can be reached.
            conn = self.get_connections([index],pawn.terrain + '_conn', pawn.moves)
        elif pawn.moves > 0 and pawn.ring > 0:  # Only a ring of hexes can be reached
            outer = self.get_connections([index],pawn.terrain + '_conn', pawn.moves)
            inner = self.get_connections([index],pawn.terrain + '_conn', pawn.moves-pawn.ring)
            conn = numpy.setdiff1d(outer, inner)    # The reachable ring is in the outer list but not in the inner list.
        else:
            conn = [-1]

        ''' Identify unoccupied hexes. Occupied hexes cannot be reached. '''
        empty = [i for i, x in enumerate(self.objects) if x == ""]

        ''' The reachable hexes are the union of the previous two'''
        return numpy.intersect1d(conn,empty)

    def get_reachable_land(self, game, index):
        ''' Returns all reachable hexes for a pawn located on a boat. '''
        pawn_moves = getattr(game,getattr(game,self.objects[index]).occupying_pawn_label).moves

        if pawn_moves == 0: # If the pawn has no moves, it can't go anywhere.
            return []

        # Get all hexes in a 1-hex diameter
        all_1 = self.get_connections([index], 'all_conn', 1)

        # Select all land hexes within the 1-hex diameter
        land_1 = [x for i, x in enumerate(all_1) if self.tiles[x] not in ['water','home']]
        # Select all hexes which are reachable from the nearby land hexes with moves-1 steps for the pawn on the boat
        pawn_land = self.get_connections(land_1, 'land_conn', pawn_moves - 1)
        all_reachable_pawn = numpy.append(pawn_land,land_1)
        # Remove the occupied hexes
        return [x for i, x in enumerate(all_reachable_pawn) if self.objects[x] == '']


    def grow_land(self,number,tile_file):
        ''' Put the land tiles in a stack and shuffle'''
        self.tile_draw = DrawPile(tile_file,'tile_drawpile')
        
        '''Generates an island of "number" land tiles starting from a random hex.'''
        # Randomly pick starting hex and set the tile
        this_index = numpy.random.randint(0,self.n_hexes-1)
        drawn_tile = self.tile_draw.lose_card()
        print('Land tile ' + drawn_tile.name + ' added to hex ' + str(this_index))
        self.tiles[this_index] = drawn_tile.name
        index_list = [this_index]
        # Add the remaining tiles to the start hex
        for i in range(1,number):
            # Retrieve the neighboring hexes of the already placed land tiles
            neighbours = self.get_connections(index_list,'all_conn',1)
            # Select a random hex from the neighbours
            this_index = neighbours[numpy.random.randint(0,len(neighbours))]
            drawn_tile = self.tile_draw.lose_card()
            print('Land tile ' + drawn_tile.name + ' added to hex ' + str(this_index))

            # Add a land tile label to the tiles list
            self.tiles[this_index] = drawn_tile.name
            # Add the new index to the index_list for use in the next iterations
            index_list.append(this_index)

        self.set_land_connectivity()

    def load_map(self,file,tile_file):
        ''' Creates a game board with player start setup from csv file'''

        self.tile_draw = DrawPile(tile_file, 'tile_drawpile') # Create the draw pile for the randomized tiles

        '''Open de board file. If the tile type is random or land, a random land tile needs to be drawn.
        Otherwise the tile type specified in the board file is copied.'''
        import csv
        with open(file) as f:
            reader = csv.reader(f,delimiter=';')
            next(reader,'none') # skip the header
            for row, index in zip(reader,range(0,self.n_hexes)):
                if row[1] == 'random': # fully randomized tiles, including water
                    drawn_tile = self.tile_draw.lose_card()
                    self.tiles[index] = drawn_tile.name
                elif row[1] == 'land':  # randomized land only
                    drawn_tile = self.tile_draw.lose_card()
                    while drawn_tile.name == 'water':   # Keep drawing until a non-water tile is drawn
                         drawn_tile = self.tile_draw.lose_card()
                    self.tiles[index] = drawn_tile.name
                else: # In all other cases the tile type is specified in the input file
                    self.tiles[index] = row[1]
                ''' Set the initial object positions of the players. This will be processed and modified during the
                initialization of the Game class.'''
                if row[2]:
                    self.objects[index] = 'init_' + row[3] + '_' + row[2]

        self.set_land_connectivity()
        self.set_water_connectivity()

    def move_object(self,visualiser, game, new_index):
        ''' Attempts to move a pawn from the current location to new_index'''
        ''' If everything is going as it should, self.selected and self.select_reachable should already be filled '''
        ''' check if the new_index is reachable, if so do the move'''
        #if numpy.where(self.select_reachable == new_index):
        if new_index in self.select_reachable:
            object = self.remove_object(visualiser, game, self.selected)
            self.place_object(visualiser,object,new_index)
            object.moves = 0
            ''' If the moved object is a boat then burn the selected fuel'''
            if 'boat' in object.label:
                object.burn_fuel()                                  # Burn selected fuel
            print('Pawn ' + object.label + ' moved from hex ' + str(self.selected) + ' to ' + str(new_index))
            
        else:
            object = getattr(game,self.objects[self.selected])
            print('Illegal move for pawn ' + object.label + ' moved from hex ' + str(self.selected) + ' to ' + str(new_index))

    def place_object(self, visualizer, object, index):
        '''Attempts to place a moveable Game piece on the playing board on hex index '''
        print('Placing ' + object.label + ' on hex ' + str(index) + '...')
        # Check whether position x,y is occupied, if so return false.
        if not self.objects[index]:
            self.objects[index] = object.label
            visualizer.draw_object(index, object)
            print('    ...success')
            return True
        else:
            print('    ...failed: hex already occupied by ' + self.objects[index])
            return False

    def remove_object(self,visualiser,game,index):
        if not self.objects:
            print('No pawn found on hex ' + str(index))
        else:
            object = getattr(game,self.objects[index]) # Retrieve the pawn so we can return it as function output
            visualiser.remove_object(index)
            self.objects[index] = ''
            return object
            print('Object removed from hex ' + str(index))

    def select_enemy_object(self,visualiser,game,index):
        ''' shows objects belonging to enemy objects of the board.'''
        '''Retrieve the object on hex index '''
        this_obj = getattr(game,self.objects[index])

        ''' The rest of the procedure depends on the object type'''
        if 'team' in this_obj.label:
            print('No options for enemy pawns')
        elif 'boat' in this_obj.label:
            '''Draw the highlighted pawn, draw the icons for the boat options (unboarding), display the resource popup and display the fuel burn popup. '''
            visualiser.enemy_resources_popup(index, game, self)
        elif 'harbour' in this_obj.label or 'home' in this_obj.label:
            ''' Draw the harbour and show the resource popup.'''
            visualiser.enemy_resources_popup(index, game, self)
        else:
            print('Unknown object')

    def select_object(self,visualiser,game,index):
        '''Assigns the input index to self.selected and determines all reachable hexes for the selected object. 
        Then tells the visualiser to highlight the hex in which it is located and all reachable hexes'''

        '''Retrieve the object on hex index '''
        this_obj = getattr(game,self.objects[index])

        print('Selecting pawn at hex ' + str(index))
        ''' Store  the index of the currently selected hex '''
        self.selected = index

        print('Selecting pawn at hex ' + str(index))
        ''' Store  the index of the currently selected hex '''
        self.selected = index
        ''' Determine hexes reachable by the pawn in hex index '''
        self.select_reachable = numpy.array(self.get_reachable_hexes(index, getattr(game,self.objects[index])))

        for i in self.select_reachable:
            visualiser.highlight_hex(i, 'pawn')

        '''Remove existing pawn visualisation'''
        visualiser.remove_object(index)
        ''' Highlight the hex '''
        visualiser.highlight_hex(index,'reachable')

        ''' The rest of the procedure depends on the object type'''
        if 'team' in this_obj.label:
            ''' Draw the highlighted pawn and show the pawn options (digging, boarding a boat) '''
            visualiser.draw_object(index,this_obj)
            visualiser.show_pawn_options(self,game,index)
        elif 'boat' in this_obj.label:
            '''Draw the highlighted pawn, draw the icons for the boat options (unboarding), display the resource popup and display the fuel burn popup. '''
            visualiser.draw_object(index, this_obj)
            visualiser.show_boat_options(self,game,index)
            visualiser.player_resources_popup(index, game, self)
        elif 'harbour' in this_obj.label or 'home' in this_obj.label:
            ''' Draw the harbour and show the resource popup.'''
            visualiser.draw_object(index, this_obj)
            visualiser.player_resources_popup(index, game, self)
        else:
            print('Unknown object')

    def set_land_connectivity(self):
        # To get the connectivity matrix for the landmass, we copy the full board connectivity and set the not-land rows and columns to 0
        self.land_conn_1 = numpy.array(self.all_conn_1)                     # Copy the full connectivity, using '=' creates a link instead of a copy!
        not_land = [i for i, x in enumerate(self.tiles) if x in ['water','home']]
        self.land_conn_1[not_land, :] = 0
        self.land_conn_1[:, not_land] = 0

    def set_water_connectivity(self):
        # Set the connectivity matrix for water
        self.water_conn_1 = numpy.array(self.all_conn_1)
        not_water = [i for i, x in enumerate(self.tiles) if x not in ['water']]
        self.water_conn_1[not_water, :] = 0
        self.water_conn_1[:, not_water] = 0