# os module is used for deleting generated config files when the program is closed
import os
import configparser
import math

# The numpy package is used for connectivity matrix manipulation and solving the linear resource requirement equations.
import numpy

# Pawn class for the land pawns, boats and home towns
from pawn import Pawn, Harbour, Boat, Home
# Cards class for managing drawpiles of land tiles and resource cards
from cards import DrawPile, Stack
# The randomize function for shuffling the player order
from random import shuffle


class Game:

    """Handle the game mechanics which are not related to location on the board.
    
    The game class handles all mechanics which are non-spatial; the latter are handled by the grid class. 
    Processes which are handled by the game class are:
    - the player assignments and the status thereof
    - player turns
    - player cores
    - ownership of objects
    - resource drawpiles
    - moving resources between player objects
    - burning resources for extra movement
    - determined whether the game is over
    
    Input:
    - config: a configparser object containing the keys of the Config.ini file
    - grid: reference to the grid object which manages the location-based game mechanics
    - visualiser: reference to visualiser object which handles all i/o
    
    Functions:
    - activate_player: activates a specified player
    - boat_select_fuel: selects fuel card to use for moving a boat and update move parameter and visualisation
    - check_assignment: checks whether selected resources fulfill the player's tier1 or tier2 assignments
    - deactivate_player: updates a player's point count and de-highlight his/her pawns in case not all were used     
    - end_player_turn: ends the active player's turn by activating the next player
    - fulfill_tier1: fulfills the requirement of the player's tier1 assignment by removing the appropriate resources 
    - fulfill_tier2: fulfills the requirement of the plyer's tier2 assignment by removing the appropriate resources
    - game_over: checks whether the game's end conditions have been reached.
    - get_current_player: returns a reference to the object of the current player
    - quit: Cleans up the generated card config files and kills the program
    - shift_resources: Moves selected resources from one stakck to another.
        !!! The checkboxes are interface specific, move (part of) function to visualiser
    - update_card_counts: Initiates updating the visualization of the card counts of the resource drawpiles.
    - update_points: Calculates all player scores, stores them and updates the visualisation.
    
    The following functions are run during __init__ to generate the resource draw decks:
    - get_required_resources: calculates resource requirement of the all player assignments
    - adjust_resources: adjusts resource requirement determined by get_required_resources as specified in config
    - get_resource_matrix: constructs a list of card names and the matrix with the number of each resource in it
    - calculate_resources: calculate the number of each resource card needed    
    - gen_res_conf: generates the resource config files of each landscape type as calculated using calculate_resources
    
    """

    def __init__(self, config, grid, visualiser):

        """Initiate player components, create resource draw piles, randomize player order and activate first player. 
        
        For each player, search the player board table for objects owned by the currently generated player. After
        generating each player piece, place it on the board through the grid object. Randomly draw a assignment for each
        player.
        
        Generate the five resource draw piles; there is a draw pile for each of the five landscape types. The draw piles
        are generated based on the total amount of resources required for all player assignments. These totals are
        modified using slope and intercept parameters in the config.ini file. 
        
        Randomize the player order and activate the first player in the sequence.
        
        """

        # Store references to the grid, visualiser and config objects in the object for easy access.
        self.grid = grid
        self.visualiser = visualiser
        self.config = config
        # Retrieve the number of players
        self.n_players = config.getint('Game', 'n_players')
        # Assign colors to players. May want to move this to config at some point.
        self.player_colors = ['red', 'blue', 'green', 'orange', 'pink', 'purple']
        # Inititalize the list which will store the player order
        self.player_order = ['']*self.n_players
        # Retrieve the player assignments and shuffle them.
        self.assignment_stack = DrawPile(str(config.get('Game', 'assignments')), 'Assignments')
        # Counter for managing the end-of-game phase. -1 means that the end-of-game phase was not triggered. When it
        # does get triggered (by the game_end function in this class), each player gets on more turn and the number
        # remaining turns is administrated with this counter.
        self.turns_till_end = -1

        # Loop over the players to create struct for each containing their playing pieces. The playing pieces which
        # need to be created are stored in the grid object.
        for i in range(1, self.n_players+1):
            # Make an empty struct.
            def new_player(): return 0
            # Assign the player name and label. The name is used for visualization, the label for game management.
            new_player.name = 'Player ' + str(i)
            new_player.label = 'player' + str(i)
            # Assign a color to the player.
            new_player.color = self.player_colors[i]
            # Initialize the player's score as 0.
            new_player.points = 0

            # Assign an assignment to the player by drawing one from the assignment stack.
            new_player.assignment = self.assignment_stack.lose_card()
            # Each assignment has two phases: tier 1 and tier 2. Tier 1 needs to be completed before tier 2 can be
            # worked on. We keep track of resources spent on each tier by maintinging resource stacks for the
            # tier 1 and tier 2 assignments.
            new_player.assignment.tier1_stack = Stack(new_player.label + '_tier1')
            new_player.assignment.tier2_stack = Stack(new_player.label + '_tier2')

            # Find the player's objects in the grid.objects list and initialize them. First, extract indices of board
            # tiles which contain an object labeled as 'init' and have the player's label assigned to them.
            objects_index = [dummy for dummy, x in enumerate(grid.objects_init) if 'init_' + new_player.label in x]
            # Make counters for tracking the number of pawns and boats generated. This is needed for labelling them.
            pawn_counter = 0
            boat_counter = 0
            # Initiate lists with references to the player's pawns and boats.
            new_player.pawn_list = []
            new_player.boat_list = []

            # Loop over the indices of tiles containing the current player's pieces and create them.
            for index in objects_index:
                # The current piece is a harbour (these are the towns on the island where the resources are dug):
                if 'harbour' in grid.objects_init[index]:
                    # Create a harbour object.
                    new_harbour = Harbour(new_player.label, new_player.label + 'harbour', new_player.color, 'land')
                    # Add the harbour object to the player struct.
                    setattr(self, new_harbour.label, new_harbour)
                    # Place the harbour object on the playing board.
                    grid.place_object(new_harbour, index)

                # If the current piece is a pawn:
                elif 'pawn' in grid.objects_init[index]:
                    # Increase the pawn counter.
                    pawn_counter = pawn_counter + 1
                    # Create a new pawn. Specify the player label, the label of the pawn (player label + the word 'team'
                    # + the number of the pawn), give it the player's color and specify that it only moves on land.
                    new_pawn = Pawn(new_player.label, new_player.label + 'team' + str(pawn_counter),
                                    new_player.color, 'land')
                    # Set the pawn's allowed moves per turn as specified in the config and reset the moves which are
                    # available for the current turn.
                    new_pawn.set_moves_per_turn(self.config.getint('Game', 'pawn_moves'))
                    new_pawn.reset_moves()
                    # Add the pawn to the player stryct and add its label to the list of pawn labels.
                    setattr(self, new_pawn.label, new_pawn)
                    new_player.pawn_list.append(getattr(self, new_pawn.label))
                    # Place the pawn on the play board.
                    grid.place_object(new_pawn, index)

                # If the current piece is a boat:
                elif 'boat' in grid.objects_init[index]:
                    # Increase the boat counter.
                    boat_counter = boat_counter + 1
                    # Create a new boat object. Specify player label, boat label, player color, the fact that it only
                    # moves on water and that it has 6 resource slots. NB: This number needs to be moved to config.
                    new_boat = Boat(new_player.label, new_player.label + 'boat' + str(boat_counter), new_player.color,
                                    'water', 6)
                    # Set the boat's allowed moves per turn as specified in the config.
                    new_boat.set_moves_per_turn(self.config.getint('Game', 'boat_moves'))
                    # Contrary to pawns, boats cannot reach all tiles within range. They have a minimum move radius
                    # as well. This means that the reachable tiles form a ring structure. The widht of the ring
                    # is specified in the config file.
                    new_boat.set_ring(self.config.getint('Game', 'boat_ring'))
                    # Reset the moves which are available for the current turn.
                    new_boat.reset_moves()
                    # Add the boat the player structure.
                    setattr(self, new_boat.label, new_boat)
                    # Add the boat's label to the list of boats.
                    new_player.pawn_list.append(getattr(self, new_boat.label))
                    # Place the boat on the play boatrd.
                    grid.place_object(new_boat, index)

                # If the current object is a home base (the towns on the destination island):
                elif 'home' in grid.objects_init[index]:
                    # Create a new home object.
                    new_home = Home(new_player.label, new_player.label + 'home', new_player.color, 'home')
                    # Add the home to the player struct.
                    setattr(self, new_home.label, new_home)
                    # Place the home base on the play board.
                    grid.place_object(new_home, index)

                # If none of the above play pieces are found, something went wrong and the produce and error.
                else:
                    self.visualiser.log('Unknown object ' + grid.objects[index] + ' during init of player '
                                        + new_player.name)

            # Add the new player struct to self.
            setattr(self, new_player.label, new_player)
            # Add the player's label to the list for managing turn order.
            self.player_order[i-1] = new_player.label
            # Report on the creation of the new player.
            self.visualiser.log('Created player ' + self.player_order[i-1])

        # In the next block, derive the number of each resource card type to be added to the game and distribute them
        # over the landscapes.
        # Get the total resource requirement for all assignments
        req = self.get_required_resources()
        # Apply multipliers and offsets to requirements to get the number of resources needed in the game.
        req_corr = self.adjust_resources(req)
        # Retrieve resource count of each resource type except the collectibles.
        [cards, value_matrix] = self.get_resource_matrix()
        # Calculate the number of each resource card to be added to the game (excluding specials).
        res_count = self.calculate_resources(req_corr, value_matrix)
        # Creaate an ini temp file for each landscape type
        self.gen_res_conf(res_count, cards)
        # Create the resource draw stacks for each terrain type using the generated ini files.
        self.swamp_drawpile = DrawPile(config.get('Game', 'swamp_resources'), 'swamp_drawpile')
        self.rock_drawpile = DrawPile(config.get('Game', 'rock_resources'), 'rock_drawpile')
        self.forest_drawpile = DrawPile(config.get('Game', 'forest_resources'), 'forest_drawpile')
        self.meadow_drawpile = DrawPile(config.get('Game', 'meadow_resources'), 'meadow_drawpile')
        self.sand_drawpile = DrawPile(config.get('Game', 'sand_resources'), 'sand_drawpile')

        # Randomize the player order.
        shuffle(self.player_order)
        # Keep track of the turns, initialize at turn 1.
        self.turn = 1
        # Initialize a counter to keep track of the current active player.
        self.player_index = -1
        # Initialize a label indicating the current player.
        self.current_player = 'init'
        # Activate the first player in the sequence.
        self.activate_player(0)

    def activate_player(self, index):
        """ Perform all actions required to activate a player. This means that the object belonging to one player become
        clickable. Index specifies the position in the player list.
        
        """
        # Report on the activation of the player.
        self.visualiser.message('Activating player ' + self.player_order[index])
        # Set the active player in index to the input index.
        self.player_index = index
        # Set the label of the current player to the player in the sequence indicated by index.
        self.current_player = self.player_order[self.player_index]
        # Update the scoreso of all players.
        self.update_points()

        # Set the number of moves allowed for the player's pawns and boats.
        for p in getattr(self, self.current_player).pawn_list:
            p.reset_moves()
        for b in getattr(self, self.current_player).boat_list:
            b.reset_moves()

        # Instruct the visualiser object to highlight the objects of the players which have moves for this turn.
        # NB: This does not include homes, harbours and boats without pawns in them.
        # Loop over all tiles...
        for i in range(self.grid.n_hexes):
            # ... and if an object is found ....
            if self.grid.objects[i]:
                # ... which belongs to the activated player...
                if self.grid.objects[i].owner == self.player_order[index]:
                    # ... remove the visualisation of the objects...
                    self.visualiser.remove_object(i)
                    # ... snd redraw them.
                    # If the object has moves for this turn, the visualiser draws them highlighted.
                    if self.grid.objects[i].moves > 0:
                        self.visualiser.draw_object(i, self.grid.objects[i], 'highlight')
                    # If there are no moves for this turn, the object is drawn non-highlighted.
                    else:
                        self.visualiser.draw_object(i, self.grid.objects[i])

    def adjust_resources(self, req):
        """" Apply the intercepts and slopes specified in the config files to the resource requirements. Resource order 
        is as always ewsmf 
        
        """
        # Retrieve the modification parameters from config and put them in arrays.
        slope = numpy.array([
            int(self.config.get('Game', 'earth_multiplyer')),
            int(self.config.get('Game', 'wood_multiplyer')),
            int(self.config.get('Game', 'stone_multiplyer')),
            int(self.config.get('Game', 'metal_multiplyer')),
            int(self.config.get('Game', 'fuel_multiplyer'))
        ])
        offset = numpy.multiply(self.n_players, numpy.array([
            int(self.config.get('Game', 'earth_offset')),
            int(self.config.get('Game', 'wood_offset')),
            int(self.config.get('Game', 'stone_offset')),
            int(self.config.get('Game', 'metal_offset')),
            int(self.config.get('Game', 'fuel_offset'))
        ]))
        # Specify the shape of the slope and offset vectors.
        slope.shape = (5, 1)
        offset.shape = (5, 1)
        # Calculate the adjusted resource requirements by multiply the input with the slope vector and adding the
        # offset.
        req_adj = numpy.add(numpy.multiply(req, slope), offset)
        # Report on the adjustments
        self.visualiser.log('Adjusting resource requirements as follows '
                            '(result = requirement x multiplyier + n_player x offset')
        self.visualiser.log('Earth: ' + str(req[0]) + ' x ' + str(slope[0]) + ' + '
                            + str(offset[0]) + ' = ' + str(req_adj[0]))
        self.visualiser.log('Wood: ' + str(req[1]) + ' x ' + str(slope[1]) + ' + '
                            + str(offset[1]) + ' = ' + str(req_adj[1]))
        self.visualiser.log('Stone: ' + str(req[2]) + ' x ' + str(slope[2]) + ' + '
                            + str(offset[2]) + ' = ' + str(req_adj[2]))
        self.visualiser.log('Metal: ' + str(req[3]) + ' x ' + str(slope[3]) + ' + '
                            + str(offset[3]) + ' = ' + str(req_adj[3]))
        self.visualiser.log('Fuel: ' + str(req[4]) + ' x ' + str(slope[4]) + ' + '
                            + str(offset[4]) + ' = ' + str(req_adj[4]))
        # Return the result.
        return req_adj

    def boat_select_fuel(self, index, resource_index):
        """Selects a fuel card to use for moving a boat, updates the move parameter accordingly and updates the 
        visualisation.
        Arguments:
        - index: the location of the boat on play board
        - resource_index: the index of the selected fual in the list of fuel cards. Value -1 indicates to fuel selected.
        
        """
        # Close the boat's resource popup. NB: This is a tkinter operation, should move this to the visualiser.
        self.visualiser.popup.destroy()
        # If resource_index = -1, no fuel is selected and just use the basic move capability of the boat.
        if resource_index == -1:
            # Deselect the fuel card if the index is -1 ("row" in the boat dialog)
            self.grid.objects[index].deselect_fuel()
            # Remove the board indicators for the boat
            self.grid.deselect_object()
            # Update the visualisation to the new moves
            self.grid.select_object(index)
        # If resource_index is 0 or higher, select the indicated fuel resource and update the movess.
        elif resource_index > -1:
            # Select the fuel resource
            self.grid.objects[index].select_fuel(resource_index)
            # Remove the board indicators for the boat
            self.grid.deselect_object()
            # Update the visualisation to the new moves
            self.grid.select_object(index)
        # Any other value for fuel_index is invalid.
        else:
            self.visualiser.log('Invalid fuel selection!')

    def calculate_resources(self, req, value_matrix):
        """Calculate the number of each resource card needed tot satisfy the required number of each resource type.
        The requirement is fulfilled by solving the underdermined equation in the value_matrix.
        
        Arguments:
            - req: the required amount of each of the five resources,
            - value_matrix: matrix containing the resource value of each resource card type.
        
        """
        # Solve the liniear equation. The solution is not unique since the problem is underdefined.
        result = numpy.linalg.lstsq(value_matrix, req)
        # Round the card numbers upwards to integers.
        rounded = numpy.ceil(result[0])

        # Count the resource totals per type (excluding the specials) and report on them.
        res_total = numpy.inner(value_matrix, numpy.transpose(rounded))
        self.visualiser.log('Generated resources (excluding specials): ')
        self.visualiser.log('Earth required: ' + str(req[0]) + ', achieved: ' + str(res_total[0]))
        self.visualiser.log('Wood required: ' + str(req[1]) + ', achieved: ' + str(res_total[1]))
        self.visualiser.log('Stone required: ' + str(req[2]) + ', achieved: ' + str(res_total[2]))
        self.visualiser.log('Metal required: ' + str(req[3]) + ', achieved: ' + str(res_total[3]))
        self.visualiser.log('Fuel required: ' + str(req[4]) + ', achieved: ' + str(res_total[4]))
        # Return the result.
        return rounded

    def check_assignment(self, index, res_select, assignment):
        """Checks whether selected resources fulfill the tier1 or tier2 assignments.
        
        Arguments:
            - index: identifies the currently selected tile of the player board
            - res_select: tkinter variables indicating which property of each resource card is selected
            - assignment: the assignment card object which needs to be checked.
        
        """
        # Using the grid and index, retrieve the resources in the stack of the object located on the selected tile.
        # Get direct reference to the resource stack
        res = self.grid.objects[index].resources.stack

        # Create an empty struct for sturing the resource counts.
        def temp(): return 0
        # Initialize the resource counters for keeping track of the total of the selected resource cards.
        temp.earth = 0
        temp.wood = 0
        temp.stone = 0
        temp.metal = 0
        temp.fuel = 0
        temp.collect = 0

        # Loop over the selected resources and add up the resource counts
        for i in range(0, len(res_select)):
            # Count collectibles if they match the assigment's tier2 objective.
            if res_select[i].get() == 'collect' and assignment.tier2.find(res[i].collect) != 'none':
                temp.collect += 1
            # Count the non-collectibles.
            elif res_select[i].get() != 'none':
                this_res = getattr(temp, res_select[i].get())
                this_res += int(getattr(res[i], res_select[i].get()))
                setattr(temp, res_select[i].get(), this_res)

        # If tier1 of the assignment is unfulfilled and the resource count of the selection fulfills the tier1
        # requirements, then activate the tier1 fulfill button.
        if (assignment.tier1_fulfilled == '0' and
                temp.earth >= int(assignment.tier1_req_earth) and
                temp.wood >= int(assignment.tier1_req_wood) and
                temp.stone >= int(assignment.tier1_req_stone) and
                temp.metal >= int(assignment.tier1_req_metal) and
                temp.fuel >= int(assignment.tier1_req_fuel)):
            self.visualiser.ass_enable_1(True)
        # If the requirements of the tier1 assignment are not met, the tier1 fulfull button is disabled.
        else:
            self.visualiser.ass_enable_1(False)

        # If tier1 is fulfilled and any of the selected resources fulfills the tier2 requirement (ie it is a collectible
        # of the correct type), then enable the tier2 fulfill button.
        if assignment.tier1_fulfilled == '1' and temp.collect > 0:
            self.visualiser.ass_enable_2(True)
        # In any other case the tier2 fulfill button is disabled.
        else:
            self.visualiser.ass_enable_2(False)

    def deactivate_player(self, index):
        """ Update the player's point count and de-highlight the player's pawns in case not all were used.
        Arguments:
            - index: the player's number in the player sequence.
        
        """

        # Log message indicating that the player is being deactivated.
        self.visualiser.log('Deactivating player ' + self.player_order[index])
        # Message to UI to indicate that the player ended her/his turn.
        self.visualiser.message(self.player_order[index] + ' ended her/his turn.')
        # Update the scores.
        self.update_points()
        # Deselected any object which may still be selected.
        self.grid.deselect_object()
        # Loop over all board tiles to find objects of the current player.
        for i in range(self.grid.n_hexes):
            if self.grid.objects[i]:
                # If an object is found which belongs to the player being deactivated, remove it and redraw it as
                # unselected.
                if self.grid.objects[i].owner == self.player_order[index]:
                    self.visualiser.remove_object(i)
                    self.visualiser.draw_object(i, self.grid.objects[i])
    
    def end_player_turn(self):
        """Ends the current player's turn by activating the next player. If the last player in the sequence ends his
        turn, activate the first.
        
        """
        # Deactivate the current player.
        self.deactivate_player(self.player_index)
        # Check whether the game is over.
        if self.game_over():
            self.visualiser.log('Game over!')
        # Ativate the next player in sequence if player is not the last player.
        elif self.player_index < self.n_players-1:
            self.activate_player(self.player_index+1)
        # If current player is last player in sequence, activate player 1. For this we need to 'manually' do some
        # operations which are normally handled by the activate_player function.
        else:
            # Player index is 0.
            self.player_index = 0
            # Current player is the first of the sequence.
            self.current_player = self.player_order[0]
            # Increase the turn count.
            self.turn = self.turn+1
            # Activate the player.
            self.activate_player(0)
            # Throw a log message that a new turn has started.
            self.visualiser.log('New turn (' + str(self.turn) + '), activating ' + self.current_player)

    def fulfill_tier1(self, index, res_select, assignment, window):
        """Fulfills the requirement of the tier1 assignment by removing the appropriate resources. 
        
        The selected resources as passed in the res_select argumment fulfill the requirements as this was already 
        checked before enabling the fulfill button. The selected resources are passed to the resource stack of 
        of the assignment object until all conditions for the assignment are met. If any of the selected resource cards
        is unnecessary, it is not passed. If it somehow occurs that the assignment is not fulfilled after passing the
        cards, all resource cards are passed back to the home town stack.
        
        Arguments:
            - index: the index of the tile on which the player's home town is located
            - res_select: variables indicating which resource property of each card is selected
            - assignment: the assignment to be fulfilled
            - window: handle to the popup window with the resource selections.
        """
        # Show a message.
        self.visualiser.log('Attempting to fulfull tier 1 assigment...')
        # Get a shorter reference to the resource stack
        res = self.grid.objects[index].resources

        # Create a dummy object for containing the resource counts. Initialize the values to the requirements of the
        # assignment and subtract the selected attributes of the passed resource cards. By putting the counters in a
        # struct, each can be accessed using a getattr with the string of the resource properties in the resource cards.
        def counter(): return 0
        counter.earth = int(assignment.tier1_req_earth)
        counter.wood = int(assignment.tier1_req_wood)
        counter.stone = int(assignment.tier1_req_stone)
        counter.metal = int(assignment.tier1_req_metal)
        counter.fuel = int(assignment.tier1_req_fuel)

        # fulfilling the assignment. Stop the loop when the assignment is fulfilled. The resources which help in
        # fulfulling the assignment are transferred to the assignment tier1 stack. If the loop ends but the assignment
        # is not fulfilled (this should not happen as the fulfill button is only enabled when the selected resources
        # are enough), all resources are pushed back to the home stack.
        # Loop over the selected resources
        # Loop over the selected resources backwards until the assignment is met. By looping backwar we don't get
        # indexing problems when we pop a resource.
        i = res.get_size() - 1
        while assignment.tier1_fulfilled == '0' and i >= 0:
            # We only work on the selected resources
            if res_select[i].get() != 'none':
                # Check whether the selected resource attribute contributes to fulfulling the assignment
                if getattr(counter, res_select[i].get()) > 0:
                    # Deduct the resource value from the appropriate counter. We do this by retrieving the current
                    # resource count of the selected property from the counter struct, deducting the value of the
                    # selected resource and then setting the counter in the struct to the new result.
                    setattr(counter, res_select[i].get(),
                            getattr(counter, res_select[i].get())-int(getattr(res.stack[i], res_select[i].get())))
                    # Push the resource to the assignment stack.
                    res.give_selected_card(assignment.tier1_stack, i)

                    # Check whether the the assignment requirements are fulfulled. If so, we're done.
                    if (counter.earth <= 0 and counter.wood <= 0 and
                            counter.stone <= 0 and counter.metal <= 0 and counter.fuel <= 0):
                        assignment.tier1_fulfilled = '1'
                        self.visualiser.log('Tier 1 assignment fulfulled')
                        break

            # Decrease the counter for the next iteration.
            i -= 1

        # Safety measure: if we looped over all selected resources and the assigmnent is not fulfulled, push all
        # resources back to the home stack. This should never happen since the fulfull button is only enabled after
        # checking whether the selection fulfulls the assignment.
        if assignment.tier1_fulfilled == '0':
            self.visualiser.log('Tier 1 assignment not fulfilled, returning resources to home stack.')
            # Loop over all resource cards in the assignment stack and give them to the home town stack.
            while len(assignment.tier1_stack.stack) > 0:
                assignment.tier1_stack.give_card(res)
        # Close the resource window, it is not up-to-date anymore and pressing the fulfill button again would
        # cause problems.
        window.destroy()

    def fulfill_tier2(self, index, res_select, assignment, window):
        """Fulfill the requirement of the tier2 assignment by moving the appropriate resources. 
        
        The selected resources
        as passed in the res_select argumment fulfill the requirements as this was already checked before enabling the 
        fulfill button.
           Arguments:
            - index: the index of the tile on which the player's home town is located
            - res_select: variables indicating which resource property of each card is selected
            - assignment: the assignment to be fulfilled
            - window: handle to the popup window with the resource selections.
    
        """
        # Log message to announcing what we're about to do.
        self.visualiser.log('Attempting to fulfull tier 2 assigment...')
        # Get a short reference to the resource stack
        res = self.grid.objects[index].resources
        # Loop over the selected resources and remove them from the stack if it is the right type of special resource.
        # These resources are transferred to the assignment tier2 stack.
        # We will loop backwards, that way we don't get indexing problems when we pop a resource.
        i = res.get_size() - 1
        while i >= 0:
            # Check whether the resource is selected and whether the selection is the special for the assignment.
            if res_select[i].get() != 'none' and assignment.tier2.find(res_select[i].get()):
                # If so, transfer the resource to the assignment stack and remove the corresponding variable from
                # the res_select list.
                res.give_selected_card(assignment.tier2_stack, i)
                res_select.pop(i)

            # Decrease the counter for the next iteration
            i -= 1
        # Update the player scores
        self.update_points()
        # Close the resource window, it is not up-to-date anymore.
        window.destroy()

    def game_over(self):
        """Checks whether the game's end conditions have been reached. 
        The game ends one full round after two resource stacks have been depleted.
        
        """
        # Counter for the number of empty resource draw piles
        n_empty_stacks = 0
        # Check whether the end-of-game cycle was already triggered. -1 means no, this is the preset.
        if self.turns_till_end == -1:
            # If the end-of-game phase was not triggered, check whether it should be by counting the number of empty
            # card stacks.
            for pile in ['sand', 'forest', 'meadow', 'rock', 'swamp']:
                if getattr(self, pile+'_drawpile').get_size() == 0:
                    n_empty_stacks += 1
            # If the the number of empty stacks is 2 or more, initiate the end-of-game phase.
            if n_empty_stacks >= 2:
                self.visualiser.log('Two or more resource stacks are empty. Each player gets one more turn.')
                # self.end_cycle = True
                # Each player gets one more turn till game end
                self.turns_till_end = self.n_players
                # Send a message to the UI that the end-of-game phase has been started.
                self.visualiser.message(str(n_empty_stacks) + ' landscapes are empty. Each player gets one more turn.')
        # end_cycle is > -1, so we are in the end phase.
        else:
            # Every turn the counter gets lowered. When it hits 0 the game is over.
            self.turns_till_end -= 1

        # When the end-of-game counter reaches 0, the game is over.
        if self.turns_till_end == 0:
            self.visualiser.message('Game over')
            return True
        else:
            return False

    def gen_res_conf(self, res_count, cards):
        """Generates the resource config files of each landscape type. 
        
        Each landscape has it's own associated resource as follows: 
        Sand: earth, forest: wood, meadow: stone, rock: metal, swamp: fuel.
        Each terrain type stack contains 6/10 specials of it's own resource type and 1 of each of the other four.
        Each terrain type stack contains the 3-valued cards of its own resource type, the rest is distributed evenly.
        
        Arguments:
            - res_count: number of cards of each type to generate
            - cards: name of the cards corresponding to res_count.
        
        """
        self.visualiser.log('Creating landscape drawpiles...')
        # Put all terrain-specific variables in a struct so we can use getattr to loop over terrain types.
        # Create empty object to do store the terrain-specific variables.

        def terr(): return 0

        # Lists of terrain types and associated resources. The specials are not in this list and are handled separately.
        terrains = ['sand', 'forest', 'meadow', 'rock', 'swamp']
        resources = ['earth', 'wood', 'stone', 'metal', 'fuel']

        # Loop over terrain types.
        for i in terrains:
            # Initialize a new config structure
            this_config = configparser.ConfigParser()
            # Load all resource tiles except the specials.
            this_config.read([self.config.get('Game', 'resources'), self.config.get('Game', 'specials')])
            # Add the config for this terrain to the terr object. NB: all five configs are the same for now
            setattr(terr, i+'_conf', this_config)

        # Loop over the resource cards and distribute the number in res_count over the resource piles.
        for i in range(0, len(cards)):
            # Retrieve the values for the next card in the stack:
            # Name of the card (equal to key in the config object).
            this_card = cards[i]
            # Number of copies of the card to distribute.
            this_number = int(res_count[i][0])

            self.visualiser.log('Distributing ' + str(this_number) + ' copies of resource card ' + this_card)

            # Flag to indicate whether we ran into a 3-valued card. If not, it needs to be distributed later.
            isthree = False
            # Loop over terrains and distribute the current resource card count.
            for j, k in zip(resources, terrains):
                # Extract the resource values of the current card. I use the sand config here, but could be any of
                # the five, since they're all identical before processing.
                setattr(terr, 'this_' + j, terr.sand_conf.get(this_card, j))
                # In case of a 3-valued resource, set the card copies to 0 as default if the landscape type is not the
                # default, else set it to 3.
                if getattr(terr, 'this_' + j) == '3':
                    getattr(terr, k + '_conf').set(this_card, 'copies', str(this_number))
                    self.visualiser.log('    ...adding ' + str(this_number) + ' copies to ' + k)
                    isthree = True
                # If the resource card does not have a resource value of three for the preferred resource, set the card
                # count to 0. Part of these are overwritten in the next code block.
                else:
                    getattr(terr, k + '_conf').set(this_card, 'copies', str(0))

            # We divide the other cards by five and distribute evenly. The round-off error is handled by giving
            # sand, forest, meadow and swamp rounded 1/5 of the cards, and substracting the rounded from the total to
            # get the number for rock. This corrects for the fact that rock is a bit underpopulated since metal is
            # relatively rare in the game.
            # Do this for any card that is not a three for the current landscape.
            if not isthree:
                # Calculate the card count for all stacks except rock.
                fraction = math.floor(this_number/5)
                # Calculate the number for the rock stack.
                rest = this_number - 4*fraction
                # Put numbers for all five terrain types in one list.
                distribute = [fraction, fraction, fraction, rest, fraction]
                # Loop over the five terrain types and set the card counts as in distribute.
                for j, k in zip(terrains, distribute):
                    getattr(terr, j+'_conf').set(this_card, 'copies', str(k))
                    self.visualiser.log('    ...adding ' + str(k) + ' copies to ' + j)

        # Next, we handle the special cards. Retrieve specials only and shuffle.
        temp_cards = DrawPile(self.config.get('Game', 'specials'), 'temp')
        # Create counters for the number of each special type already assigned.
        for i in resources:
            setattr(terr, i+'_counter', 0)
            # Make a distribution list for each special type. The randimization is handled by the shuffling of the
            # DrawPile above.
            # Retrieve the dominant terrain for the current special resource type.
            dominant_terrain = terrains[resources.index(i)]
            # The dominant terrain for the special type is repeated 5x, the sixth is already in terrains.
            setattr(terr, i+'_dist', [dominant_terrain]*5 + terrains)

        # Loop over the specials and the set the card counts for each landscape, ie to 1 or 0 depending on how many of
        # the same collectible were already encountered. This is managed by counting how many of the same type of
        # collectible were already encountered and using this counter to index the terr.i+dist list declared above.
        for i in range(0, temp_cards.get_size()):
            # Pop the topmost card from the collectibles stack.
            this_card = temp_cards.lose_card()
            # Retrieve the corresponding landscape by finding the index of the collectible type in the resource list.
            this_res = [j for j in resources if this_card.collect[0:4] in j]
            # Assign the card to the landscape pile indicated by the counter for the special type. (Yes, this is a bit
            # convoluted, alternative is 10 km of spaghetti).
            # Retrieve the terrain type
            this_terrain = getattr(terr, this_res[0] + '_dist')[getattr(terr, this_res[0] + '_counter')]

            # Set the card counts for all terrain types to 0 except for this_terrain which is 1.
            for k in terrains:
                if k == this_terrain:
                    getattr(terr, k+'_conf').set(this_card.name, 'copies', '1')
                    self.visualiser.log('Assigning 1 copy of ' + this_card.name + ' to ' + k)
                else:
                    getattr(terr, k + '_conf').set(this_card.name, 'copies', '0')
            # Increase the counter for the current collectible type.
            setattr(terr, this_res[0] + '_counter', getattr(terr, this_res[0] + '_counter') + 1)

        # Write the five config files.
        with open(self.config.get('Game', 'sand_resources'), 'w') as configfile:
            terr.sand_conf.write(configfile)
        with open(self.config.get('Game', 'forest_resources'), 'w') as configfile:
            terr.forest_conf.write(configfile)
        with open(self.config.get('Game', 'meadow_resources'), 'w') as configfile:
            terr.meadow_conf.write(configfile)
        with open(self.config.get('Game', 'rock_resources'), 'w') as configfile:
            terr.rock_conf.write(configfile)
        with open(self.config.get('Game', 'swamp_resources'), 'w') as configfile:
            terr.swamp_conf.write(configfile)

    def get_current_player(self):
        """ Returns the label of the currently active player. """

        return getattr(self, self.current_player)

    def get_required_resources(self):
        """ Adds up the resource requirement of the all player assignments and applies the multiplier specified in the 
        game confige file.
        
        """
        self.visualiser.log('Calculating resource requirement...')
        # Initialize vectors to store the results (in the order ewsmf).
        req = numpy.array([0, 0, 0, 0, 0])
        req.shape = (5, 1)

        # Loop over the players and add up the resource requirements. We put the results in a vector in the order ewsmf.
        for player in range(0, self.n_players):
            # Retrieve an easy reference to the player assignment.
            ass = getattr(self, 'player' + str(player + 1)).assignment
            # Write a log message about the assignment.
            self.visualiser.log('player' + str(player + 1) + ' assignment requires (ewsmf) = ' + ass.tier1_req_earth
                                + ' ' + ass.tier1_req_wood + ' ' + ass.tier1_req_stone + ' ' + ass.tier1_req_metal
                                + ' ' + ass.tier1_req_fuel)
            # Add the resource requirement of the assignment to the total.
            req[0] += int(ass.tier1_req_earth)
            req[1] += int(ass.tier1_req_wood)
            req[2] += int(ass.tier1_req_stone)
            req[3] += int(ass.tier1_req_metal)
            req[4] += int(ass.tier1_req_fuel)
        # Log the total requirement.
        self.visualiser.log('Total resource requirement (ewsmf) =  ' + str(req[0]) + ' ' + str(req[1]) + ' '
                            + str(req[2]) + ' ' + str(req[3]) + ' ' + str(req[4]))
        return req

    def get_resource_matrix(self):
        """Constructs a list of card names and a matrix with the number of each resource in each card type. 
        Resource order: ewsmf. Collectibles are not handled here.
        
        """

        # To obtain info about all cards, create temp card stack from the config file containing 1 copy of each card
        # type.
        temp_cards = Stack('temp')
        temp_cards.create_cards_from_file(self.config.get('Game', 'resources'))

        # Retrieve the number of unique cards.
        n_cards = temp_cards.get_size()
        # Declare a list for storing the card names.
        card_names = []
        # Matrix (numpy array) for storing the resource counts of each resource card type.
        res_mat = numpy.zeros((n_cards, 5))

        # Loop over all cards in the card stack, pop them and store the resource counts and card name for
        # non-collectible resource cards.
        # Keep an index for inserting the resource counts in the right row of the res_mat matrix.
        index = 0
        # Keep going while there are still cards on the temp stack.
        while temp_cards.get_size() > 0:
            # Get a card from the stack.
            this_card = temp_cards.lose_card()
            # When the card is not a collectible, we process it.
            if this_card.collect == 'none':
                # Add the card's name to the card_names list.
                card_names.append(this_card.name)
                # Add the card's resource counts tot the res_mat matrix.
                res_mat[index, :] = [int(this_card.earth),
                                     int(this_card.wood),
                                     int(this_card.stone),
                                     int(this_card.metal),
                                     int(this_card.fuel)]
            index += 1

        return [card_names, numpy.transpose(res_mat)]

    def quit(self):
        """Cleans up the generated config files and kills the program."""

        # Tell people that there are no winners since the game ends prematurely.
        self.visualiser.log('Game is unfinished so no one wins and no one loses.')
        # Remove the temp config files.
        os.remove(self.config.get('Game', 'sand_resources'))
        os.remove(self.config.get('Game', 'swamp_resources'))
        os.remove(self.config.get('Game', 'rock_resources'))
        os.remove(self.config.get('Game', 'forest_resources'))
        os.remove(self.config.get('Game', 'meadow_resources'))
        os.remove(self.config.get('Grid', 'tile_temp'))
        # Tell the visualiser object to terminate.
        self.visualiser.kill(self.update_points())

    def shift_resources(self, source_index, destination_index, checks):
        """Move selected resources from source to destination.
        Arguments:
            - source_index: tile index of the source of the resource cards,
            - destination_index: tile index of the destination of the resource cards,
            - checks: selection of which resources need to be passed.
        """

        # Retrieve an easy reference to the source and destination stacks.
        source = self.grid.objects[source_index].resources
        destination = self.grid.objects[destination_index]

        # Loop from back to front over the resources in the source.
        for i in reversed(range(0, len(checks))):
            # If a check is yes, then pass the resource from source to destinatioon.
            if checks[i].get():
                source.give_selected_card(destination.resources, i)
        # Destroy the resource popup since it is not up to date anymore.
        self.visualiser.popup.destroy()

    def update_card_counts(self):
        """Updates the visualization of the card counts. 
        Counts are supplied in the order sand, forest, meadow, rock, swamp.
                
        """
        self.visualiser.update_card_counts(self.sand_drawpile.get_size(),
                                           self.forest_drawpile.get_size(),
                                           self.meadow_drawpile.get_size(),
                                           self.rock_drawpile.get_size(),
                                           self.swamp_drawpile.get_size())

    def update_points(self):
        """Calculates all player scores, stores them and updates the visualisation."""
        # Initialize a message string.
        score_string = ''
        # Loop over all players.
        for i in self.player_order:
            # Retrieve a reference to the player structure
            player = getattr(self, i)
            # Calculate the points (one point per special collected in tier2).
            player.points = player.assignment.tier2_stack.get_size()
            # Add the score of the player to the report string.
            if player.points == 1:
                score_string += i + ': 1 point.\n'
            else:
                score_string += i + ': ' + str(player.points) + ' points.\n'
        # Show the score string in the log.
        self.visualiser.log(score_string)
        # Send the string with socres to the visualiser.
        self.visualiser.update_scores()

        return score_string
