import csv
import configparser

import numpy

from cards import DrawPile
from hexgrid import Hexgrid

class Grid(Hexgrid):
    def __init__(self,size_x,size_y, visualiser):
        super().__init__(size_x,size_y)     # Run the hexgrid constructor
        self.visualiser = visualiser        # Set a link with the visualiser, safes a lot of parameter passing

    def activate_hex(self,index):
        ''' Spaghetti which handles the events when a player clicks a hex '''

        self.visualiser.remove_selected_items() # Remove all highlighted items and option icons from the board.

        if self.selected == [] and not self.objects[index]:
            ''' Do nothing'''
            self.visualiser.log('Nothing here to do on hex ' + str(index))

        elif self.selected == index and self.dig and 'team' in self.objects[index].label and self.get_landscape_stack_size_by_index(index) > 0:
            ''' If a pawn is selected and the clicked index is the selected index and the drawpile for the landscape is not empty, check whether the "dig" option was clicked.'''
            self.visualiser.log('Digging...')
            '''The drawpile of the tile type gives a resource to the stash of the activeplayer'''
            getattr(self.game,self.tiles[index]+'_drawpile').give_card(getattr(self.game,self.game.player_order[self.game.player_index] + 'harbour').resources) # Get a card from the appropriate stack and move it to the player's harbour
            self.objects[self.selected].use_moves(1)          # Deduct one move for the pawn
            self.deselect_object()                          # Deselect the hex
            self.game.update_card_counts()                  # Update the card counts
            self.visualiser.message(self.game.player_order[self.game.player_index] + ' gains ' + getattr(self.game,self.game.player_order[self.game.player_index] + 'harbour').resources.stack[-1].name)

        elif self.selected and not self.objects[index]:
            ''' If a boat is selected which has a pawn, we see if the pawn can disembark. If the index hex contains an enemy ship, we try to steal from it.'''
            if 'boat' in self.objects[self.selected].label:
                if self.objects[self.selected].occupying_pawn:
                    if index in(self.get_reachable_land(self.selected)):  # Disembark the occupying pawn to the index hex
                        self.place_object(self.objects[self.selected].unboard(),index) # The boat object is retrieved, the pawn is unboarded which returns the pawn label, which is in turn used to get the pawn object

            if 'team' in self.objects[self.selected].label or 'boat' in self.objects[self.selected].label:
                ''' If a pawn/boat is selected and no object is in the clicked hex, we attempt to move the selected pawn. '''
                try:
                    self.visualiser.log('Attempt to move pawn to ' + str(index))
                    found = self.select_reachable.tolist().index(index) #This is just a trick to generate an exception if index is empty
                    self.move_object(index)
                    self.visualiser.remove_selected_items()
                    self.selected = []

                except ValueError:
                    '''deselect pawn'''
                    self.deselect_object()
                    self.visualiser.log('Cannot move object to hex ' + str(index))


        elif self.selected and 'boat' in self.objects[index].label and self.game.current_player in self.objects[index].label:
            ''' If a pawn is selected and the clicked index contains a boat, check whether the boat is 1. reachable and
            2. belongs the the active player. If so, move the selected pawn into the boat. '''
            if 'team' in self.objects[self.selected].label:
                if index in self.get_reachable_boats(self.selected):
                    ''' Move the pawn into the boat'''
                    self.visualiser.message(self.game.current_player + ' moves pawn ' + self.objects[self.selected].label + ' into boat' + self.objects[index].label)
                    not_removed =  self.objects[index].occupy(self.objects[self.selected])
                    if not not_removed:
                        moved_pawn_index = self.selected
                        self.deselect_object()
                        self.remove_object(moved_pawn_index)
                    else:
                        self.select_object(self.selected)
                else:
                    self.visualiser.log('Boat ' + self.objects[index].label + ' too far removed from pawn ' + self.objects[self.selected].label)
                    self.select_object(self.selected)
            else: # The previously selected object wasn't a pawn, so just activate the boat
                self.deselect_object()
                self.select_object(index)

        elif 'harbour' in self.objects[index].label or 'home' in self.objects[index].label:
            '''Display the resources stored by the owner of the harbour'''
            if self.selected:
                self.deselect_object()
            self.select_object(index)

            '''If an object is found on the hex AND it belongs to the active player, select it. '''
        else:
            self.visualiser.log('Activating ' + self.objects[index].label + ' found on hex ' + str(index))
            ''' If an object is already selected, then deselect that before selecting the new one '''
            if self.selected:
                self.deselect_object()
            if self.objects[index].owner == self.game.current_player:
                self.select_object(index)
            else:
                self.select_enemy_object(index)

    def deselect_object(self):
        if self.selected == []: # Escape the method if nothing is selected
            return
        self.visualiser.remove_object(self.selected)
        self.visualiser.remove_selected_items()
        '''If the pawn belongs to the active player and has moves left, it needs to be highliighted, '''
        if self.objects[self.selected].owner == self.game.current_player and self.objects[self.selected].moves > 0:
            self.visualiser.draw_object(self.selected,self.objects[self.selected],'highlight')
        else:
            self.visualiser.draw_object(self.selected,self.objects[self.selected])
        ''' Clear the index of the currently selected hex '''
        self.selected = []
        self.selected_reachable = []

    def get_reachable_object_indices(self, terrain, index, radius):
        ''' Returns a list of objects which are within a certain distance, taking into account terrain type (all, land,
        water), from index. '''

        conn_1 = self.get_connections([index], terrain + '_conn', radius)
        return  [x for i, x in enumerate(conn_1) if self.objects[x]]

    def get_landscape_stack_size_by_index(self,index):
        ''' Returns the number of resources still available in the stack of the landscape of hex index.'''
        return getattr(self.game,self.tiles[index]+'_drawpile').get_size()

    def get_reachable_boats(self,index):
        ''' Returns a list of indices for hexes containing a boardable boat for a pawn located at index.'''
        pawn_moves = self.objects[index].moves
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
                    if self.objects[i].owner == self.game.current_player and 'boat' in self.objects[i].label: # check if the object is a boat and if it belongs to the active player
                        if not self.objects[i].occupying_pawn: # Need to put this condition separate since non-boat objects don't have this field
                            reachable_boats.append(i)
            return reachable_boats

    def get_reachable_hexes(self,index,pawn):
        '''Returns a list of all hexes that are reachable for the pawn.'''
        
        ''' Retrieve the hexes which are within reach. The connectivity matrix depends on the tile type (i.e. land for
        pawns, water for boats). If the ring parameter of the object is set to 0, the whole surface within reach of 
        pawn.moves can be reached. If ring is any positive integer value, a ring of reachable hexes is generated. This 
        is the case for boats. '''
        if pawn.moves > 0 and pawn.ring < 1:                                                    # All hexis within pawn.moves distance can be reached.
             conn = self.get_connections([index],pawn.terrain + '_conn', pawn.moves)
        elif pawn.moves > 0 and pawn.ring > 0:                                                  # Only a ring of hexes can be reached
            outer = self.get_connections([index],pawn.terrain + '_conn', pawn.moves)            # Get all water tiles in range
            inner = self.get_connections([index],pawn.terrain + '_conn', pawn.moves-pawn.ring)  # Get all water tiles in range minus 1
            conn = numpy.setdiff1d(outer, inner)                                                # The reachable ring is in the outer list but not in the inner list.

            ''' We want harbours and towns to be reachable always if they're inside movable range, even if the water/land next to it is
            not on the reachable ring. For this, we need to add all tiles bordering any harbour/town inside the moveable
            radius to the list. '''
            harbours = []                       # List of tiles indices containing a town or harbour
            ''' Find any player-owned harbour in range + 1. (Harbours bordering the outer ring are already taken care of intrinsically.) '''
            for i in self.get_connections([index], 'all_conn', pawn.moves+1):           # Loop over the tiles in range
                if self.objects[i]:             # Is there an object?
                    if (self.objects[i].label.find('harbour') != -1 or self.objects[i].label.find('home') != -1) and self.objects[i].owner.find(self.game.current_player) != -1:    # Identify player-owned harbours
                        harbours.append(i)           # Add the index to the list

            next_to_town = numpy.array(self.get_connections(harbours, 'all_conn', 1))   # Find tiles one step removed from each index in the list
            next_to_town = numpy.intersect1d(next_to_town, outer)                       # Retain indices adjacent to a town/harbour which are within moveable range with the correct landscape type.
            conn = numpy.append(conn, next_to_town)                                     # Add the resulting tiles to conn

        else:
            conn = [-1]

        ''' Identify unoccupied hexes. Occupied hexes cannot be reached. '''
        empty = [i for i, x in enumerate(self.objects) if not x]

        ''' The reachable hexes are the union of the previous two'''
        return numpy.intersect1d(conn,empty)

    def get_reachable_land(self, index):
        ''' Returns all reachable hexes for a pawn located on a boat. '''
        pawn_moves = self.objects[index].occupying_pawn.moves

        if pawn_moves == 0: # If the pawn has no moves, it can't go anywhere.
            return []

        # Get all hexes in a 1-hex diameter
        all_1 = self.get_connections([index], 'all_conn', 1)

        # Select all land hexes within the 1-hex diameter
        land_1 = [x for i, x in enumerate(all_1) if self.tiles[x] not in ['water','home']]
        # If the pawn has more than 1 move, select all hexes which are reachable from the nearby land hexes with moves-1 steps for the pawn on the boat
        if pawn_moves > 1:
            pawn_land = self.get_connections(land_1, 'land_conn', pawn_moves - 1)
            all_reachable_pawn = numpy.append(pawn_land,land_1)
        else:
            all_reachable_pawn = land_1

        # Remove the occupied hexes
        return [x for i, x in enumerate(all_reachable_pawn) if self.objects[x] == '']

    def load_map(self, config):
        ''' Creates a game board with player start setup from csv file'''

        '''Open de board file. If the tile type is random or land, a random land tile needs to be drawn.
        Otherwise the tile type specified in the board file is copied.'''
        with open(config.get('Game','board')) as f:
            reader = csv.reader(f, delimiter=',')
            next(reader, 'none')  # skip the header
            for row, index in zip(reader, range(0, self.n_hexes)):
                self.tiles[index] = row[1]  # The tile type is specified in row 1 the input file. Randomized tiles are handled below
                if row[2]:                  # Row 2 contains the locations of the player objects. These will later be processed during init of Game class
                    self.objects_init[index] = 'init_' + row[3] + '_' + row[2]

            ''' Determine how many of each landscape tile we need for the randomized tiles. There is two types of 
            random tiles: 1. random (all tile types, including water) and 2. land (random but has to be land). '''
            # Count the numbmer of random entries
            # Count the nuber of land entires
            n_random = self.tiles.count('random') + self.tiles.count('land')                  # Total number of ranomized tiles
            n_land = numpy.floor(self.tiles.count('random')/6 + self.tiles.count('land')/5)   # Number of land tiles required of each type is random/6 + land/5
            n_water = n_random - 5*n_land                                                       # Number of water is all that remains
            this_config = configparser.ConfigParser()                                           # Initialize a new config structure
            this_config.read(config.get('Grid', 'tile_file'))                                   # Load a template for all tiles (single copy each)

            for type in ['sand','forest','meadow','rock','swamp']:                          # Set the number of copies for each tile type
                this_config.set(type, 'copies', str(int(n_land)))
            this_config.set('water', 'copies', str(int(n_water)))

            with open(config.get('Grid', 'tile_temp'), 'w') as configfile:        # Write the result to a temporary ini file
                this_config.write(configfile)

            self.tile_draw = DrawPile(config.get('Grid', 'tile_temp'), 'tile_drawpile')                  # Create the draw pile for the randomized tiles from the temp file

        ''' Now we loop over the randomized tiles and assign a random tile from the draw pile.
        NB we need to process the land-only randoms first, otherwise we may run out of land tiles before we get to them.'''
        for tile, index in zip(self.tiles,self.all_hexes):
            if tile == 'land':  # randomized land only. If we draw water, we put it back, shuffle, and try again
                iswater = True
                iterations = 0
                while iswater:  # Keep drawing until a non-water tile is drawn
                    drawn_tile = self.tile_draw.lose_card()
                    if drawn_tile.name == 'water' and iterations < 2*self.tile_draw.get_size():    # At some point we may need to give up :)
                        self.tile_draw.receive_card(drawn_tile)
                        self.tile_draw.shuffle_stack()
                        iswater = True
                        iterations += 1
                    else:
                        self.tiles[index] = drawn_tile.name
                        iswater = False
            elif tile == 'random':  # fully randomized tiles, including water
                drawn_tile = self.tile_draw.lose_card()
                self.tiles[index] = drawn_tile.name

        self.set_land_connectivity()        # Set the land connectivity matrix
        self.set_water_connectivity()       # Set the water connectivity matrix

    def move_object(self, new_index):
        ''' Attempts to move a pawn from the current location to new_index'''
        ''' If everything is going as it should, self.selected and self.select_reachable should already be filled '''
        ''' check if the new_index is reachable, if so do the move'''
        #if numpy.where(self.select_reachable == new_index):
        if new_index in self.select_reachable:
            object = self.remove_object(self.selected)
            self.place_object(object,new_index)
            object.moves = 0
            ''' If the moved object is a boat then burn the selected fuel'''
            if 'boat' in object.label:
                object.burn_fuel()                                  # Burn selected fuel
            self.visualiser.log('Pawn ' + object.label + ' moved from hex ' + str(self.selected) + ' to ' + str(new_index))
            
        else:
            object = getattr(self.game,self.objects[self.selected])
            self.visualiser.log('Illegal move for pawn ' + object.label + ' moved from hex ' + str(self.selected) + ' to ' + str(new_index))

    def place_object(self, object, index):
        '''Attempts to place a moveable Game piece on the playing board on hex index '''
        self.visualiser.log('Placing ' + object.label + ' on hex ' + str(index) + '...')
        # Check whether position x,y is occupied, if so return false.
        if not self.objects[index]:
            self.objects[index] = object
            self.visualiser.draw_object(index, object)
            self.visualiser.log('    ...success')
            return True
        else:
            self.visualiser.log('    ...failed: hex already occupied by ' + self.objects[index])
            return False

    def remove_object(self,index):
        if not self.objects:
            self.visualiser.log('No pawn found on hex ' + str(index))
        else:
            self.visualiser.remove_object(index)
            removed  = self.objects[index]
            self.objects[index] = None
            self.visualiser.log('Object ' + removed.label + ' removed from hex ' + str(index))
            return removed


    def select_enemy_object(self,index):
        ''' shows objects belonging to enemy objects of the board.'''

        ''' The rest of the procedure depends on the object type'''
        if 'team' in self.objects[index].label:
            self.visualiser.log('No options for enemy pawns')
        elif 'boat' in self.objects[index].label:
            '''Draw the highlighted pawn, draw the icons for the boat options (unboarding), display the resource popup and display the fuel burn popup. '''
            self.visualiser.enemy_resources_popup(index)
        elif 'harbour' in self.objects[index].label or 'home' in self.objects[index].label:
            ''' Draw the harbour and show the resource popup.'''
            self.visualiser.enemy_resources_popup(index)
        else:
            self.visualiser.log('Unknown object')

    def select_object(self,index):
        '''Assigns the input index to self.selected and determines all reachable hexes for the selected object. 
        Then tells the visualiser to highlight the hex in which it is located and all reachable hexes'''

        self.visualiser.log('Selecting pawn at hex ' + str(index))
        ''' Store  the index of the currently selected hex '''
        self.selected = index

        self.visualiser.log('Selecting pawn at hex ' + str(index))
        ''' Store  the index of the currently selected hex '''
        self.selected = index
        ''' Determine hexes reachable by the pawn in hex index '''
        self.select_reachable = numpy.array(self.get_reachable_hexes(index, self.objects[index]))

        for i in self.select_reachable:
            self.visualiser.highlight_hex(i, 'pawn')

        '''Remove existing pawn visualisation'''
        self.visualiser.remove_object(index)
        ''' Highlight the hex '''
        self.visualiser.highlight_hex(index,'reachable')

        ''' The rest of the procedure depends on the object type'''
        if 'team' in self.objects[index].label:
            ''' Draw the highlighted pawn and show the pawn options (digging, boarding a boat) '''
            self.visualiser.draw_object(index,self.objects[index])
            self.visualiser.show_pawn_options(index)
        elif 'boat' in self.objects[index].label:
            '''Draw the highlighted pawn, draw the icons for the boat options (unboarding), display the resource popup and display the fuel burn popup. '''
            self.visualiser.draw_object(index, self.objects[index])
            self.visualiser.show_boat_options(index)
            self.visualiser.player_resources_popup(index)
        elif 'harbour' in self.objects[index].label or 'home' in self.objects[index].label:
            ''' Draw the harbour and show the resource popup.'''
            self.visualiser.draw_object(index, self.objects[index])
            self.visualiser.player_resources_popup(index)
        else:
            self.visualiser.log('Unknown object')