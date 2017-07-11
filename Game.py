import Pawn as pawn             # My pawn class for the land pawns, boats and home towns
from Cards import *             # My cards class for managing drawpiles of land tiles and resource cards
import numpy                    # The numpy package for connectivity matrix manipulation and solving the linear resource requirement equations.
from random import shuffle      # The randomize function for shuffling the player order

class Game:
    def __init__(self,config,grid,visualiser):
        self.n_players = config.getint('Game', 'n_players')                             # Retrieve the number of players
        self.player_colors = ['red','blue','green','yellow','orange','pink','purple']   # Assign colors to players
        self.player_order = ['']*self.n_players                                         # Inititalize the list which will store the player order

        '''Retrieve the player assignments and shuffle them.'''
        self.assignment_stack = DrawPile(str(config.get('Game', 'assignments')),'Assignments')
        print(config.get('Game', 'assignments'))

        self.turns_till_end = -1 # Counter for managing the end-of-game phase.

        ''' Initialise the player variables '''
        for i in range(1,self.n_players+1):
            new_player = lambda: 0 # Make empty struct
            new_player.name = 'Player ' + str(i)
            new_player.label = 'player' + str(i)
            new_player.pawns = [None]*5
            new_player.color = self.player_colors[i]
            new_player.points = 0

            ''' Create the assignment by selecting one from the assignment stack and then adding resource
            stacks for the tier 1 and tier 2 assignments. '''
            new_player.assignment = self.assignment_stack.lose_card()
            new_player.assignment.tier1_stack = Stack(new_player.label + '_tier1')
            new_player.assignment.tier2_stack = Stack(new_player.label + '_tier2')

            ''' Find the player's objects in the grid.objects list and initialize them.'''
            objects_index = [dummy for dummy, x in enumerate(grid.objects) if 'init_' + new_player.label in x]
            pawn_counter = 0 # Used to number the pawns (not the other items)
            boat_counter = 0
            for index in objects_index:
                if 'harbour' in grid.objects[index]:
                    new_harbour = pawn.Harbour(new_player.label, new_player.label + 'harbour', new_player.color,'land')
                    setattr(self, new_harbour.label, new_harbour)
                    grid.objects[index] = ''
                    grid.place_object(visualiser, new_harbour, index)

                elif 'pawn' in grid.objects[index]:
                    ''' Increase pawn number, create pawn, add it to the player, free up the grid position (it is 
                    occupied by the init item, which will cause an error when placing the pawn) and place the pawn.'''
                    pawn_counter = pawn_counter + 1
                    new_pawn = pawn.Pawn(new_player.label, new_player.label + 'team' + str(pawn_counter), new_player.color,'land')
                    setattr(self, new_pawn.label, new_pawn)
                    grid.objects[index] = ''
                    grid.place_object(visualiser, new_pawn, index)

                elif 'boat' in grid.objects[index]:
                    ''' Increase boat number, create boat, add it to the player, free up the grid position (it is 
                    occupied by the init item, which will cause an error when placing the pawn) and place the pawn.'''
                    boat_counter = boat_counter + 1
                    new_boat = pawn.Boat(new_player.label, new_player.label + 'boat' + str(boat_counter), new_player.color, 'water', 6)
                    setattr(self,new_boat.label, new_boat)
                    grid.objects[index] = ''
                    grid.place_object(visualiser, new_boat, index)

                elif 'home' in grid.objects[index]:
                    new_home = pawn.Home(new_player.label, new_player.label + 'home', new_player.color,'home')
                    setattr(self, new_home.label, new_home)
                    grid.objects[index] = ''
                    grid.place_object(visualiser, new_home, index)

                else:
                    print('Unknown object ' + grid.objects[index] + ' during init of player ' + new_player.name)
            '''Add the new player struct to the exsiting ones. '''
            setattr(self, new_player.label, new_player)
            '''Add the player's identifyer to the list for managing turn order'''
            self.player_order[i-1] = new_player.label
            print('Created player ' + self.player_order[i-1])

        ''' Randomize the player order '''
        shuffle(self.player_order)
        self.turn = 1           # Keep track of the turn
        self.activate_player(0,visualiser,grid)

        ''' Determine the resource requirement for the assignments'''
        req = self.get_required_resources()                         # Get the total resource requirement for all assignments
        req_corr = self.adjust_resources(req,config)                # Apply multipliers and offsets to requirements to get the number of resources needed in the game.
        [cards,value_matrix] = self.get_resource_matrix(config)     # Retrieve resource count of each resource card type except the collectibles.
        res_count = self.calculate_resources(req_corr,value_matrix) # Calculate the number of each resource card to be added to the game (excluding specials)
        self.gen_res_conf(res_count,cards,config)                   # Creaate an ini temp file for each landscape type

        ''' Create the resource draw stacks for each terrain type'''
        self.swamp_drawpile = DrawPile(config.get('Game','swamp_resources'),'swamp_drawpile')
        self.rock_drawpile = DrawPile(config.get('Game','rock_resources'),'rock_drawpile')
        self.forest_drawpile = DrawPile(config.get('Game','forest_resources'),'forest_drawpile')
        self.meadow_drawpile = DrawPile(config.get('Game','meadow_resources'),'meadow_drawpile')
        self.sand_drawpile = DrawPile(config.get('Game','sand_resources'),'sand_drawpile')

    def activate_player(self,index,visualiser,grid):
        print('Activating player ' + self.player_order[index])
        self.player_index = index
        self.current_player = self.player_order[self.player_index]

        '''Highlight the player's objects'''
        for i in range(grid.n_hexes):
            if grid.objects[i]:
                if getattr(self,grid.objects[i]).owner == self.player_order[index]:
                    visualiser.remove_object(i)                                   # Remove the pawn
                    this_object = getattr(self,grid.objects[i])                   # Retrieve a copy of the pawn
                    this_object.reset_moves()                                     # Reset the moves
                    if this_object.moves > 0:
                        visualiser.draw_object(i,this_object,'highlight')             # Re-draw the pawn highlighted
                    else:
                        visualiser.draw_object(i,this_object)             # Re-draw the pawn unhighlighted

    def adjust_resources(self,req,config):
        ''' Applies the intercepts and slopes specified in the config files the resource requirements. Resource order is as always ewsmf'''
        ''' Retrieve the modification parameters from config and put them in arrays.'''
        slope = numpy.array([int(config.get('Game','earth_multiplyer')), int(config.get('Game','wood_multiplyer')), int(config.get('Game','stone_multiplyer')), int(config.get('Game','metal_multiplyer')), int(config.get('Game','fuel_multiplyer'))])
        offset = numpy.multiply(self.n_players,numpy.array([int(config.get('Game','earth_offset')), int(config.get('Game','wood_offset')), int(config.get('Game','stone_offset')), int(config.get('Game','metal_offset')), int(config.get('Game','fuel_offset'))]))
        slope.shape = (5, 1)
        offset.shape = (5, 1)

        ''' Calculate the adjusted resource requirements. '''
        req_adj = numpy.add(numpy.multiply(req,slope),offset)

        ''' Report on the adjustments'''
        print('Adjusting resource requirements as follows (result = requirement x multiplyier + n_player x offset')
        print('Earth: '  + str(req[0]) + ' x ' + str(slope[0]) + ' + ' + str(offset[0]) + ' = ' + str(req_adj[0]))
        print('Wood: ' + str(req[1]) + ' x ' + str(slope[1]) + ' + ' + str(offset[1]) + ' = ' + str(req_adj[1]))
        print('Stone: ' + str(req[2]) + ' x ' + str(slope[2]) + ' + ' + str(offset[2]) + ' = ' + str(req_adj[2]))
        print('Metal: ' + str(req[3]) + ' x ' + str(slope[3]) + ' + ' + str(offset[3]) + ' = ' + str(req_adj[3]))
        print('Fuel: ' + str(req[4]) + ' x ' + str(slope[4]) + ' + ' + str(offset[4]) + ' = ' + str(req_adj[4]))

        return req_adj


    def boat_select_fuel(self, grid, visualiser, index, resource_index):
        '''Selects a fuel card to use for moving, updates the move parameter and updates the visualisation'''
        visualiser.popup.destroy()                              # Close the boat's resource popup
        this_object = getattr(self, grid.objects[index])        # Retrieve a copy of the boat
        if resource_index == -1:
            this_object.deselect_fuel()                         # Deselect the fuel card if the index is -1 ("row" in the boat dialog)
            grid.deselect_object(visualiser, self)              # Remove the board indicators for the boat
            grid.select_object(visualiser,self,index)           # Update the visualisation to the new moves
        else:
            this_object.select_fuel(resource_index)             # Select the fuel resource
            grid.deselect_object(visualiser, self)              # Remove the board indicators for the boat
            grid.select_object(visualiser,self,index)           # Update the visualisation to the new moves

    def calculate_resources(self,req,value_matrix):
        ''' Calculate the number of each resource card needed tot satisfy the required number of each resource type.'''
        result = numpy.linalg.lstsq(value_matrix, req)              # Solve the liniear equation. The solution is not unique since the problem is underdefined
        rounded = numpy.ceil(result[0])                             # Round the card numbers upwards to integers

        ''' Report on the resulting resource counts'''
        res_total = numpy.inner(value_matrix,numpy.transpose(rounded))    # Count the resource totals per type. NB this does not include the specials yet
        print('Generated resources (excluding specials): ')
        print('Earth required: ' + str(req[0]) + ', achieved: ' + str(res_total[0]))
        print('Wood required: ' + str(req[1]) + ', achieved: ' + str(res_total[1]))
        print('Stone required: ' + str(req[2]) + ', achieved: ' + str(res_total[2]))
        print('Metal required: ' + str(req[3]) + ', achieved: ' + str(res_total[3]))
        print('Fuel required: ' + str(req[4]) + ', achieved: ' + str(res_total[4]))

        return rounded

    def check_assignment(self, grid, index, vars, assignment, button1, button2):
        ''' Checks whether selected resources fulfill the tier1 or tier2 assignments. '''
        ''' Because this function is bound to the checkbutton array which is used for all objects which contain resources,'''
        ''' often there will be no assignment or buttons. Check whether assignment, button1 and 2 are a value. If not, break. '''
        if assignment == [] or button1 == [] or button2 == []:
            return

        ''' Using the grid and hex index, retrieve the resources in the stack of the object located on the selected tile. Add up the selected resources.'''
        res = getattr(self, grid.objects[index]).resources.stack # Get direct reference to the resource stack
        temp = lambda: 0
        temp.earth = 0   # Set the resource counters
        temp.wood = 0
        temp.stone = 0
        temp.metal = 0
        temp.fuel = 0
        temp.collect = 0

        for i in range(0,len(vars)):  # Loop over the selected resources and add up the resource counts
            if vars[i].get() == 'collect' and assignment.tier2.find(res[i].collect) != 'none':   # Only count the collectibles if they match the assigment's tier2 objective
                temp.collect += 1
            elif vars[i].get() != 'none':
                this_res = getattr(temp, vars[i].get())
                this_res += int(getattr(res[i], vars[i].get()))
                setattr(temp, vars[i].get(), this_res)

        ''' If tier1 of the assignment is unfulfilled and the resource count of the selection fulfills the tier1 requirements, then activate button1.'''
        if assignment.tier1_fulfilled == '0' and temp.earth >= int(assignment.tier1_req_earth) and \
                        temp.wood >= int(assignment.tier1_req_wood) and temp.stone >= int(assignment.tier1_req_stone) and \
                        temp.metal >= int(assignment.tier1_req_metal) and temp.fuel >= int(assignment.tier1_req_fuel):
            button1.config(state='normal')
        else:
            button1.config(state='disabled')

        ''' If tier1 is fulfilled and any of the selected resources fulfills the tier2 requirement, then enable button2.'''
        if assignment.tier1_fulfilled == '1' and temp.collect > 0:
            button2.config(state='normal')
        else:
            button2.config(state='disabled')

    def deactivate_player(self,index,visualiser,grid):
        ''' Update the player's point count and de-highlight the player's pawns in case not all were used. '''
        print('Deactivating player ' + self.player_order[index])
        self.update_points(visualiser)
        grid.deselect_object(visualiser, self)
        for i in range(grid.n_hexes):
            if grid.objects[i]:
                if getattr(self,grid.objects[i]).owner == self.player_order[index]:
                    visualiser.remove_object(i)                                 # Remove the object
                    visualiser.draw_object(i,getattr(self,grid.objects[i]))     # Re-draw the object as unselected
    
    def end_player_turn(self,visualiser,grid):
        '''Ends the player's turn by activating the next player. If the last player in the sequence ends his turn, we check if the game is over. '''
        self.deactivate_player(self.player_index,visualiser,grid)
        if self.game_over():                                            # Check whether the game is over
            print('Game over!')
        elif self.player_index < self.n_players-1:                      # Go to next player in sequence if player is not the last player
            '''Activate next player'''
            self.activate_player(self.player_index+1,visualiser,grid)
        else:                                                           # If current player is last player in sequence, start from player 1
            '''Activate player 1'''
            self.current_player = self.player_order[0]
            self.turn = self.turn+1
            self.player_index = 0
            self.activate_player(0,visualiser,grid)
            print('New turn (' + str(self.turn) + '), activating ' + self.current_player)

    def fulfill_tier1(self, grid, index, vars, assignment, window):
        ''' Fulfills the requirement of the tier1 assignment by removing the appropriate resources. The selected resources
        as passed in the vars argumment fulfill the requirements as this was already checked before enabling the fulfill button. '''

        print('Attempting to fulfull tier 1 assigment...')

        res = getattr(self, grid.objects[index]).resources # Get direct reference to the resource stack
        counter = lambda: 0
        counter.earth = int(assignment.tier1_req_earth)   # Set the resource counters
        counter.wood = int(assignment.tier1_req_wood)
        counter.stone = int(assignment.tier1_req_stone)
        counter.metal = int(assignment.tier1_req_metal)
        counter.fuel = int(assignment.tier1_req_fuel)

        ''' Loop over the selected resources and remove them from the stack if any of its properties contribute to fulfilling the assignment.
        Stop the loop when the assignment is fulfilled. The resources which help in fulfulling the assignment are 
        transferred to the assignment tier1 stack. If the loop ends but the assignment is not fulfilled (this should
        not happen as the fulfill button is only enabled when the selected resources are enough), all resources are
        pushed back to the home stack. '''
        i = res.get_size() -1 # We will loop backwards, that way we don't get indexing problems when we pop a resource.
        while assignment.tier1_fulfilled == '0' and i >= 0:
            if vars[i].get() != 'none': # We only work on the selected resources
                # Check whether the resource contributes to fulfulling the assignment
                if getattr(counter,vars[i].get()) > 0:  # Check whether the current resource contributes to fulfilling the assignment.
                    setattr(counter,vars[i].get(),getattr(counter,vars[i].get())-int(getattr(res.stack[i],vars[i].get())))    # Deduct the resource value from the appropriate counter
                    res.give_selected_card(assignment.tier1_stack,i)                                                        # Push the resource to the assignment stack

                    ''' Check if the the assignment requirements are fulfulled. If so, we're done here.'''
                    if counter.earth <=0 and counter.wood <= 0 and counter.stone <= 0 and counter.metal <= 0 and counter.fuel <= 0:
                        assignment.tier1_fulfilled = '1'
                        print('Tier 1 assignment fulfulled')
                        break

            i -=1 # Decrease the counter for the next iteration

        ''' Safety measure: if we looped over all selected resources and the assigmnent is not fulfulled, push all 
        resources back to the home stack. This should never happen since the fulfull button is only enabled after 
        checking whether the selection fulfulls the assignment. '''
        if assignment.tier1_fulfilled == '0':
            print('Tier 1 assignment not fulfilled, returning resources to home stack.')
            while len(assignment.tier1_stack.stack) > 0:
                assignment.tier1_stack.give_card(res)

        window.destroy() # Close the resource window, it is not up-to-date anymore and pressing the fulfill button again would cause problems.

    def fulfill_tier2(self, grid, index, vars, assignment, window, visualiser):
        ''' Fulfills the requirement of the tier2 assignment by removing the appropriate resources. The selected resources
        as passed in the vars argumment fulfill the requirements as this was already checked before enabling the fulfill button. '''

        print('Attempting to fulfull tier 2 assigment...')

        res = getattr(self, grid.objects[index]).resources # Get direct reference to the resource stack
        ''' Loop over the selected resources and remove them from the stack if it is the right type of special resource.
        These resources are transferred to the assignment tier2 stack. '''
        i = res.get_size() -1 # We will loop backwards, that way we don't get indexing problems when we pop a resource.
        while i >= 0:
            if vars[i].get() != 'none' and assignment.tier2.find(vars[i].get()): # Check whether the resource is selected and whether the selection is the special for the assignment.

            #if vars[i].get() == '': # We only work on the selected resources
                # Check whether the resource contributes to fulfulling the assignment
            #    if assignment.tier2.find(res.stack[i].collect):
                    # Push the resource to the assignment stack
                res.give_selected_card(assignment.tier2_stack,i)    # Transfer the resource
                vars.pop(i)                                         # Remove the variable from the vars list

            i -=1 # Decrease the counter for the next iteration

        self.update_points(visualiser)   # Update the player scorers
        window.destroy()                                # Close the resource window, it is not up-to-date anymore. Pressing the button again causes problems.

    def game_over(self):
        ''' Checks whether the game's end conditions have been reached. 
        The game ends one full round after two resource stacks have been depleted. '''

        n_empty_stacks = 0              # Counter for the number of empty resource draw piles
        if self.turns_till_end == -1:   # Check whether the end-of-game cycle was already triggered. -1 means no, this is the preset.
            for pile in ['sand','forest','meadow','rock','swamp']:        # Count the number of empty card stacks
                if getattr(self, pile+'_drawpile').get_size() == 0:
                    n_empty_stacks += 1
            if n_empty_stacks >= 2:
                print('Two or more resource stacks are empty. Each player gets one more turn.')
                self.end_cycle = True                   # If two or more drawpiles are empty, the end of game cycle starts.
                self.turns_till_end = self.n_players    # Each player gets one more turn till game end
        else:                                           # end_cycle is true, so we're in the final stage.
            self.turns_till_end -= 1                    # The the end-of-game phase was triggered before, turns_till_end will be a number >0. Every turn the counter gets lowered.

        if self.turns_till_end == 0:                    # The the end-of-game counter reaches 0, the game is over.
            print('Game over')
            return True
        else:
            return False

    def gen_res_conf(self,res_count,cards,config):
        ''' Generates the resource config files of each landscape type. 
        Each landscape has it's own associated resource as follows: 
        Sand: earth, forest: wood, meadow: stone, rock: metal, swamp: fuel.
        Each terrain type stack contains 6/10 specials of it's own resource type and 1 of each of the other four.
        Each terrain type stack contains the 3-valued cards of its own resource type, the rest is distributed evenly.'''

        ''' Initialize each landscape config by making a copy of the 1-card default config.'''
        import configparser
        import math

        ''' We will put all terrain specific variables in a struct so we can use getattr to loop over terrain types.'''
        terr = lambda: 0 # Create empty object

        terrains = ['sand','forest','meadow','rock','swamp']
        resources = ['earth','wood','stone','metal','fuel']

        for i in terrains:                                                                          # Loop over terrain types
            this_config = configparser.ConfigParser()                                               # Initialize a new config structure
            this_config.read([config.get('Game', 'resources'), config.get('Game', 'specials')])     # Load all resource tiles
            setattr(terr,i+'_conf',this_config)                                                     # Add the config for this terrain to the terr object. NB: all five configs are the same for now

        print('Creating landscape drawpiles...')
        ''' Loop over the resource cards and distribute the number in res_count over the resource piles. '''
        for i in range(0,len(cards)):
            ''' Retrieve the values for the next card in the stack '''
            this_card = cards[i]                # Name of the card (equal to key in the config object)
            this_number = int(res_count[i][0])  # Number of copies of the card to distribute

            print('Distributing ' + str(this_number) + ' copies of resource card ' + this_card)

            ''' 1. Extract the resource values of the current card. I use the sand config here, but could be any of
            the five, since they're all identical before processing. 
            2. In case of a 3-valued resource, set the card copies to 0 as default if the landscape type is not the 
            default, else set it to 3.'''
            isthree = False # Flag to indicate whether we ran into a 3-valued card. If not, it needs to be distributed later.
            for j,k in zip(resources,terrains):
                setattr(terr,'this_' + j, terr.sand_conf.get(this_card,j))
                if getattr(terr,'this_' + j) == '3':
                    getattr(terr, k + '_conf').set(this_card, 'copies', str(this_number))
                    print('    ...adding ' + str(this_number) + ' copies to ' + k)
                    isthree = True
                else:
                    getattr(terr, k + '_conf').set(this_card, 'copies', str(0))

            ''' We divide the other cards by five and distribute evenly. The round-off error is handled by giving 
            sand, forest, meadow and swamp rounded 1/5 of the cards, and substructing the rounded from the total to 
            get the number for rock. This rock is a bit underpopulated since metal is relatively rare in the game. '''
            if not isthree:
                fraction = math.floor(this_number/5)
                rest = this_number - 4*fraction
                distribute = [fraction, fraction, fraction, rest, fraction]

                for j,k in zip(terrains, distribute):
                    getattr(terr,j+'_conf').set(this_card, 'copies', str(k))
                    print('    ...adding ' + str(k) + ' copies to ' + j)

        ''' Distribute the collectibles/specials'''

        ''' Retrieve specials only and shuffle'''
        temp_cards = DrawPile(config.get('Game', 'specials'),'temp')

        ''' Counters for the number of each special type already assigned'''
        for i in resources:
            setattr(terr,i+'_counter',0)
            ''' Make a distribution list for each special type. The randimization is hadled by the shuffling of the DrawPile.'''
            dominant_terrain = terrains[resources.index(i)]
            setattr(terr,i+'_dist',[dominant_terrain]*5 + terrains) # The dominant terrain for the special type is tepeated 5x, the sixth is already in terrains

        ''' Loop over the specials and the set the card counts for each landscape. '''
        for i in range(0, temp_cards.get_size()):
            this_card = temp_cards.lose_card()
            ''' Retrieve the corresponding landscape by finding the index of the collectible type in the resource list.'''
            this_res = [j for j in resources if this_card.collect[0:4] in j]
            ''' Assign the card to the landscape pile indicated by the counter for the special type. (Yes, this is a bit convoluted, alternative is 10 km of spaghetti).'''
            this_terrain = getattr(terr,this_res[0]+'_dist')[getattr(terr,this_res[0]+'_counter')] # Retrieve the terrain type

            # Set the card counts for all terrain types to 0 except for this_terrain which is 1
            for k in terrains:
                if k == this_terrain:
                    getattr(terr,k+'_conf').set(this_card.name,'copies','1')
                    print('Assigning 1 copy of ' + this_card.name + ' to ' + k)
                else:
                    getattr(terr,k+'_conf').set(this_card.name,'copies','0')

            setattr(terr,this_res[0] + '_counter',getattr(terr,this_res[0] + '_counter')+1) # Increase the counter of the special type

        ''' Write the five config files'''
        with open(config.get('Game', 'sand_resources'), 'w') as configfile:
            terr.sand_conf.write(configfile)
        with open(config.get('Game', 'forest_resources'), 'w') as configfile:
            terr.forest_conf.write(configfile)
        with open(config.get('Game', 'meadow_resources'), 'w') as configfile:
            terr.meadow_conf.write(configfile)
        with open(config.get('Game', 'rock_resources'), 'w') as configfile:
            terr.rock_conf.write(configfile)
        with open(config.get('Game', 'swamp_resources'), 'w') as configfile:
            terr.swamp_conf.write(configfile)

    def get_current_player(self):
        return getattr(self,self.current_player)

    def get_required_resources(self):
        ''' Adds up the resource requirement of the all player assignments and applies the multiplier specified in the game confige file. '''

        print('Calculating resource requirement...')
        '''We put the results in a vector in the order ewsmf.'''
        req = numpy.array([0, 0, 0, 0, 0])
        req.shape = (5, 1)

        ''' Loop over the players and add up the resource requirements. We put the results in a vector in the order ewsmf.'''
        for player in range(0,self.n_players):
            ass =  getattr(self,'player' + str(player+1)).assignment
            print('player' + str(player+1) + ' assignment requires (ewsmf) = ' + ass.tier1_req_earth + ' ' + ass.tier1_req_wood + ' ' + ass.tier1_req_stone + ' ' + ass.tier1_req_metal + ' ' + ass.tier1_req_fuel)
            req[0] +=  int(ass.tier1_req_earth)
            req[1] +=  int(ass.tier1_req_wood)
            req[2] +=  int(ass.tier1_req_stone)
            req[3] +=  int(ass.tier1_req_metal)
            req[4] +=  int(ass.tier1_req_fuel)

        print('Total resource requirement (ewsmf) =  ' + str(req[0]) + ' ' + str(req[1]) + ' ' + str(req[2]) + ' ' + str(req[3]) + ' ' + str(req[4]))
        return req

    def get_resource_matrix(self,config):
        ''' Constructs a list of card names and the matrix with the number of each resource in it. Resource order: ewsmf'''
        temp_cards = Stack('temp')
        temp_cards.create_cards_from_file(config.get('Game', 'resources'))

        n_cards = temp_cards.get_size() # Retrieve the number of cards in the equation
        card_names = []                 # List for storing the card names
        res_mat = numpy.zeros((n_cards,5)) # Numpy array for storing the resource counts of each resource card

        ''' Loop over all cards in the card stack, pop them and store the resource counts and card name for non-collectible resource cards. '''
        index = 0
        while temp_cards.get_size() > 0:
            this_card = temp_cards.lose_card()
            if this_card.collect=='none':
                card_names.append(this_card.name)
                res_mat[index,:] = [int(this_card.earth),int(this_card.wood),int(this_card.stone),int(this_card.metal),int(this_card.fuel)]
            index += 1

        return [card_names, numpy.transpose(res_mat)]


    def shift_resources(self, grid, visualiser, source_index, destination_index, checks):
        ''' Translates the list checkboxes into an index list relating to the resource stack in the source object.
        The list and objects are then passed to game.shift_resources to move the selected resources from source to destination.'''
        select = []
        for i in reversed(range(0,len(checks))):
            if checks[i].get():
                this_card = getattr(self, grid.objects[source_index]).resources.give_selected_card(getattr(self,grid.objects[destination_index]).resources,i)
                visualiser.popup.destroy()

    def update_card_counts(self,visualiser):
        ''' Updates the visualization of the card counts. Counts are supplied in the order sand, forest, meadow, rock, swamp'''
        visualiser.update_card_counts(self.sand_drawpile.get_size(),self.forest_drawpile.get_size(),self.meadow_drawpile.get_size(),self.rock_drawpile.get_size(),self.swamp_drawpile.get_size(),)

    def update_points(self,visualiser):
        ''' Calculates the all players point counts, stores them and updates the visualisation. '''

        score_string = ''
        for i in self.player_order:
            player = getattr(self,i)                                    # Retrieve a reference to the player structure
            player.points = player.assignment.tier2_stack.get_size()    # Calculate the points
            if player.points == 1:                                      # Create report strings
                score_string += player.name + ': 1 point.\n'
            else:
                score_string += player.name + ': ' + str(player.points) + ' points.\n'
        print(score_string)
        visualiser.update_scores(score_string)  # Send the string with socres to the visualiser