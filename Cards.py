import itertools  # itertools allows creating multpiple instances in one go.

class Stack:
    '''Class for a stack of cards'''
    def __init__(self,name):
        self.stack_name = name
        print('Card stash ' + self.stack_name + ' created')
        self.stack = []

    def create_cards_from_file(self,file_name):
        ''' Creates a stack of cards based on specifications in a config file.'''
        import configparser
        print('Retrieving cards from ' + file_name)
        config = configparser.ConfigParser()
        config.read(file_name)
        for this_card in config.sections():
            temp = lambda: 0
            temp.name = this_card
            copies = config.getint(this_card,'copies')
            if copies == 1:
                print('Creating 1 copy of card ' + this_card + ' in stash ' + self.stack_name)
            if copies > 1:
                print('Creating ' + str(copies) + ' copies of card ' + this_card + ' in stash ' + self.stack_name)
            for (key,value) in config.items(this_card):      # Loop over the properties of the card
                setattr(temp,key,value)                      # Add the property to the temp card
            self.stack.extend(itertools.repeat(temp, copies))# Add the specified number of copies of the card in temp to the stack

    def create_dummy(self):
        # Creates an empty dummy card
        dummy = lambda: 0
        dummy.name = 'empty'
        return dummy

    def give_card(self,target_stack):
        # Actively give the top card to the stack passed in target_Stack
        try:
            card_back = target_stack.receive_card(self.stack.pop())  # Give the last card in the stack to the target stack
            print('Stash ' + self.stack_name + ' gives a card to stash ' + target_stack.stack_name + '. Stash ' + self.stack_name + ' has ' + str(self.get_size()) + ' cards left.')
            if card_back.name != 'empty':  # If the target stack rejected the card, we put it back where it was.
                self.stack.append(card_back)
                print('Stash ' + target_stack.stack_name + ' rejected the card.')
        except IndexError:
            print('Stash ' + self.stack_name + ' is empty, failed to give card to ' + target_stack.stack_name)
            return self.create_dummy()

    def give_selected_card(self,target_stack,index):
        # Actively give the selected card to the target_stack.
        try:
            card_back = target_stack.receive_card(self.stack.pop(index)) # Give the last card in the stack to the target stack
            print('Stash ' + self.stack_name + ' gives a card to stash ' + target_stack.stack_name)
            if card_back.name != 'empty':   # If the target stack rejected the card, we put it back where it was.
                self.stack.insert(index,card_back)
                print('Stash ' + target_stack.stack_name + ' rejected the card.')
        except IndexError:
            print('Stash ' + self.stack_name + ' is empty, failed to give card to ' + target_stack.stack_name)
            return self.create_dummy()

    def get_size(self):
        return len(self.stack)

    def take_card(self,target_stack):
        # Actively take a card from the passed stack
        taken_card = target_stack.lose_card()
        if taken_card.name == 'empty':
            print('Stash ' + self.stack_name + ' failed to take  a card from stash ' + target_stack.stack_name + ' since it is empty')
        else:
            print('Stash ' + self.stack_name + ' takes  a card from stash ' + target_stack.stack_name)
            self.stack.append(taken_card)

    def receive_card(self,card_in):
        # Passively receive a card from another stack
        if card_in.name == 'dummy':
            print('Stash ' + self.stack_name + ' did NOT receive a card')
        else:
            self.stack.append(card_in)
            print('Stash ' + self.stack_name + ' gains a card')

        return self.create_dummy() # Return a dummy. Needed for consistency with the sized stack, which can return the passed card if the stack is full.

    def lose_card(self):
        # Passively lose a card to another stack
        try:
            cardOut = self.stack.pop()
            print('Stash ' + self.stack_name + ' loses a card')
            return cardOut
        except IndexError:  # Stack is empty
            print('Stash ' + self.stack_name + ' is empty!')
            return self.create_dummy()

    def print_stack(self):
        # Prints a list of all cards in the stack
        print('Stack ' + self.stack_name + ' contains the following cards')
        for card in self.stack:
            print('        ' + card.name)

class DrawPile(Stack):
    def __init__(self,file_name,label):
        super().__init__(label)
        # Read the card info from the file and create the cards
        self.create_cards_from_file(file_name)
        # Shuffle the cards
        self.shuffle_stack()

    def shuffle_stack(self):
        print('Shuffling ' + self.stack_name)
        #self.print_stack()
        from random import shuffle
        shuffle(self.stack)
        #self.print_stack()

class SizedStack(Stack):
    def __init__(self,name,size):
        self.stack_name = name
        self.stack = []
        self.stack_size = size

    def take_card(self, target_stack):
        '''Runs the Stack take_card function only if the stack is not full. '''
        if len(self.stack) < self.stack_size:
            print('Stack ' + self.stack_name + ' takes a card from ' + target_stack.name)
            super().take_card(target_stack)
        else:
            print('Stack ' + self.stack_name + ' is full. No card taken from ' + target_stack.name)

    def receive_card(self, card_in):
        '''Runs the Stack receive_card function only if the stack is not full. If it is full, the received card is returned.'''
        if len(self.stack) < self.stack_size:
            print('Stack ' + self.stack_name + ' receives a card')
            super().receive_card(card_in)
            return self.create_dummy()
        else:
            print('Stack ' + self.stack_name + ' is full, returning received card.')
            return card_in

    def lose_card(self, index):
        ''' Returns a card by index and pops it from the stack. '''
        try:
            cardOut = self.stack.pop(index)
            print('Stash ' + self.stack_name + ' loses a card')
            return cardOut
        except IndexError:  # Stack does not have a resource and index
            print('Card not found!')
            return self.create_dummy()