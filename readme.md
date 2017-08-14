## Synopsis

This project is a Python implementation of a board game concept, which is very much a work in progress. At the moment the game is set up for three players which need to play hotseat on a single PC. A multiplayer clienter/server capability is in the works.

## Motivation

The project fulfills three purposes, it allows me to: 
1. showcase my Python programming skills as I am currently looking for a job as Python developer,
2. learn new programming skills by applying them to a project,
3. develop a board game concept I came up with. 

## Installation

The game is programmed in Python 3. It can be started from main.py. 

## Technical highlights 

The program consists of three major chunks: 
1. the game class, which manages the turns, the points, the ownership of player pieces and the assignments,
2. the grid class, which manages which object is located where,
3. the visualizer which handles input and output.
The visualizer is separated from the rest of the program in order to allow fancier visualization later on without having to redevelop the whole game. The split also will make it easier to split up the program in a client and a server application for multiplayer. Because of the way TKinter works, the visualizer is currently controlling the game and grid classes.

The amount of resources in the game is determined dynamically during initialization based on the requirements of the assignments which are drawn. Each resource card has two resource properties. Possible properties are wood, metal, stone, fuel and collectible. Not all combination of these five are possible. Wood, metal, stone and fuel occur in values in 1, 2 or 3. In order to come up with a card count which satisfied the required total number of resources, a underdetermined linear system of equations needs to be solved since there are more card types than resource types. This is done in Game.calculated_resources() using the numpy.linalg.lstsq function. The result is not unique, but the function pushes the numbers of each card type towards being as equal as possible.

The board game is a hexagonal grid. Movement on the grid is managed in the Hexgrid class. At initialization, a matrix is set up which specifies which hex connects to which other hex. When the actual play board gets loaded, two matrices are derived from this: one which identifies neighbouring water hexes and one for land. These one-step matrices can be used to derived >1 step connections. To get the 2-step connection, the 1-step matrix is squared and then added to itself. So n2 = n1*n1 + n1. The resulting numbers are bogus, but any number larger than 0 is reachable in at most two steps. The addition of n1 is necessary in cases where "corridors" occur: strings of single hexes, each of which is only connected to two neighbours. To get to n3: n3 = n2*n1 + n2




## Game manual

The objective of the game is to fulfill your individual assignment by collecting resources on the island with the colored tiles and shipping them to the island with the white tiles.
Resources can be collected by clicking a pawn (circle in the player color; the active player’s pawns are highlighted in pink) and then pressing the DIG sign which is presented. Alternatively, a pawn can be moved to an empty tile by clicking on any of the tiles which are highlighted in red. Each pawn can perform two actions per round. All collected resources are stored in your harbor (the triangle on the colored island). To see which resources you collected, you can click the harbor. 
Resources can be moved from your harbor to any of your ships adjacent to it. To do this, click on the harbor, select the resources which need to be moved and press the button corresponding to the ship you want to move them too. Each ship can hold six resource units. 
Ships need a pawn to man them in order to be able to move. In order to occupy a boat, select a pawn which is in moveable range of a ship and click on the ship. A white downward arrow will appear on any reachable ship if a pawn is selected. You will be able to move the ship during your next turn.
When a ship with an occupying pawn is selected and the ship has moves left, a ring of red highlighted tiles appears indicating all hexes the ship can move to. This is always a ring shape. The move range can be influenced by burning fuel, which is one of the resource types which can be collected. If a ship is selected, two panels appear. One contains the all resources on the ship (left), the other contains all fuel resources and the “row” option. Selecting row means that you do not burn fuel but it also means your ship moves slowly. If you select any fuel resource, the ring of reachable tiles gets wider. When you click any of the highlighted tiles, the selected fuel is burned and the ship moves.
You can steal resources from enemy ships. To do this, you need to move your ship to a position adjacent to an enemy ship. You can now click the enemy ship and select the resource you want to steal. Note that you ship needs room to carry the resource. Each ship can only steal one resource per turn.
When you move your ship to your home town (triangle on the white land) you can move your resources from the ship to the town by clicking the boat, selecting the resources in the popup and pressing the button of the home town below the resource list.
When you click your home town, a list of stored resources is shown as well as an assignment description. Each assignment consists of two stages. The first one consists of building something and requires a lot of resources. The second stage consists of adding special collectible resources. Each of these will gain you 1 point. If sufficient resources get selected in the leftmost panel to satisfy the current assignment, the fulfill button in the assignment pane is activated and can be pressed to fulfill the assignment. The third panel all the way to the right is an unfinished beta feature.
The resource types in the game are earth, wood, metal, stone, fuel and collectible. Each resource item has two properties which add up to a value of 4. Existing combinations are earth/stone, earth/fuel, fuel/stone, fuel/wood and stone/metal. Each in a 1/3,2/2 and 3/1 version. In addition, for every resource type 10 collectibles are present in the game. These have a resource value of 2 and the label collectible. 
To end your turn, press the “end turn” button.

## Contributors

At the moment, this game is a one-man project by Peter Steenbergen