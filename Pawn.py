import cards

class Pawn:
    '''Class for moving board pieces. Each piece maintains its' own position on the board and checks with
    the grid what the movement options are. After each move the pawn arranges for the grid to update its'
    position in the grid's own board items list.'''
    def __init__(self,owner,label,color,terrain):
        ''' owner: label indicating the owner (generally a player) of the piece
            label: name of the piece
            color: color of the piece
        '''
        print('Creating new pawn ' + label + ' for player ' + owner)
        
        self.owner = owner
        self.label = label
        self.color = color
        self.terrain = terrain
        
        ''' Determine on which hex type the pawn is allowed to be. '''
        self.hex_type = 'all'
        
        ''' Default for the movement parameters of the pawn '''
        self.moves = 1  #
        self.ring = 0
        self.moves_per_turn = 1

    def reset_moves(self):
        self.moves = self.moves_per_turn

    def use_moves(self,moves_used):
        if self.moves > moves_used:
            self.moves = self.moves - moves_used
        else:
            self.moves = 0

    def set_moves_per_turn(self,n):
        self.moves_per_turn = n

    def set_ring(self,n):
        self.ring = n

class Boat(Pawn):
    def __init__(self,owner,label,color,terrain,slots):
        print('Creating new boat ' + label + ' for player ' + owner)
        super().__init__(owner,label,color,terrain)
        self.resource_slots = slots
        self.resources = cards.SizedStack('resources',6)
        #self.moves = 0
        #self.moves_per_turn = 3
        #self.ring = 2
        self.occupying_pawn = None
        self.selected_fuel = -1                         # Default value indicating that the team will be rowing, no fuel will be burned
        self.can_steal = True                           # Flag to administrer whether a boat has stolen someting from another boat in this turn.

    def burn_fuel(self):
        ''' Destroys the selected  fuel resource and sets the moves to 0.'''
        if self.selected_fuel != -1:
            burned = self.resources.stack.pop(self.selected_fuel)
            print('Boat ' + self.label + ' burned resource ' + burned.name)
            self.selected_fuel = -1
        else:
            print('Boat ' + self.label + ' has no selected resource to burn')


    def deselect_fuel(self):
        ''' Deselects the selected fuel resource and updates the moves accordingly.'''
        if self.selected_fuel != -1: # Check whether fuel is selected
            print('Boat ' + self.label + ' returning selected resource ' + self.resources.stack[self.selected_fuel].name + ' to resource stack')
            self.moves = self.moves - int(self.resources.stack[self.selected_fuel].fuel)
            self.selected_fuel = -1

    def occupy(self,pawn_object):
        ''' Moves a pawn into a boat.'''
        if not self.occupying_pawn:                     # Check whether the boat already has an occupying pawn
            self.occupying_pawn = pawn_object           # Set the name of the ooccupying pawn
            pawn_object.moves = 0                       # Set the pawn's moves to 0 so it can't move out again this turn
            print(pawn_object.label + ' is now manning ' + self.label)
            return None
        else:
            print(self.label + ' is already occupied!')
            return pawn_object

    def reset_moves(self):
        if self.occupying_pawn: # The boat can only move if there is a pawn on it
            self.moves = self.moves_per_turn
        else: # No pawn = no moves
            self.moves = 0
        self.selected_fuel = -1 # Deselect fuel if there was any selected
        self.can_steal = True   # Reset the flag which indicates whether a boat can steal in this turn

    def select_fuel(self,index):
        ''' Selects the resourche indicated in index from the resource stack for burning and changes the moves accordingly'''
        if self.moves > 0 and int(self.resources.stack[index].fuel) > 0: # If it is 0, the boat already used its moves; if the fuel value of the resource is 0 then it's not fuel
            self.selected_fuel = index
            self.moves = self.moves_per_turn + int(self.resources.stack[index].fuel)
            print('Boat ' + self.label + ' select resource ' + self.resources.stack[index].name + ' for burning. Number of moves is now ' + str(self.moves))
        else:
            print('Error selecting fuel for ' + self.label)

    def steal_resource_from_boat(self,target,resource_index):
        ''' Steals the indicated resource from the the indicated boat. '''
        if isinstance(target, Boat) and target.owner != self.owner and self.resources.get_size() < self.resources.stack_size:    # Check whether the target is an enemy ship and if the attacking ship has room to store a stolen resource
            stolen_resource = target.resources.lose_card(resource_index ) # Take the resource
            if stolen_resource.name != 'empty': # If no card was returned, we don't add the dummy resource to the stack
                returned = self.resources.receive_card(stolen_resource)      # Add the stolen resource to stack
                if returned.name == 'empty': # Transfer succesfull
                    self.can_steal = False  # Change the flag so the boat can't steal repeatedly in the same turn
                else:   # Transfer failed, give the card back to the target
                    target.receive_card(returned)
        else:
            print('Target object is not an enemy ship.')

    def unboard(self):
        unboarding_pawn = self.occupying_pawn
        self.occupying_pawn = None
        print(unboarding_pawn.label + ' is leaving ' + self.label)
        self.reset_moves()
        return unboarding_pawn # This is the label of the pawn, not the actual object!

class Harbour(Pawn):
    def __init__(self,owner,label,color,terrain):
        ''' a harbour is basically a non-moving pawn owning a stack of cards. '''
        super().__init__(owner,label,color,terrain)
        self.moves = 0
        self.moves_per_turn = 0
        self.resources = cards.Stack('harbour')


class Home(Pawn):
    def __init__(self,owner,label,color,terrain):
        ''' a home is basically a non-moving pawn owning a stack of cards and assignment achievements '''
        super().__init__(owner,label,color,terrain)
        self.moves = 0
        self.moves_per_turn = 0
        self.resources = cards.Stack('home')
