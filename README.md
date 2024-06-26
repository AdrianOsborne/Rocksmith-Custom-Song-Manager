# Rocksmith Custom Song Manager

## Description
Rocksmith Custom Song Manager is a tool for managing custom downloadable content for the Rocksmith game. The tool allows you to easily enable, disable, and search for custom songs within your Rocksmith DLC directory.

## Author
Created by Adrian Osborne.

## Installation

### Prerequisites
- Python 3.x
- Pip (Python package installer)

### Install Dependencies
Ensure you have Python and Pip installed on your system.

### How to Run
Simply just double-click the `run.bat` file to start the program.

## Usage

### Selecting the DLC Directory
1. Click the "Select DLC Directory" button.
2. Choose your Rocksmith DLC directory. (Make sure all CDLC is in this folder even if you don't currently want to load it into the game)
3. The program will automatically load all custom songs from the selected directory and any disabled songs from the `disabled` folder located in the same directory as the script.

### Enabling and Disabling Songs
- To enable or disable individual songs, check or uncheck the box next to the song in the table.
- To enable all songs, click the "Enable All" button.
- To disable all songs, click the "Disable All" button.

### Filtering and Searching Songs
- Use the "Show Enabled Files" and "Show Disabled Files" checkboxes to filter the songs displayed in the table.
- Use the search bar to find specific songs by name. The table will dynamically update to show only matching results.
- Use the "Enable Search Results" and "Disable Search Results" buttons to enable or disable all songs that match the search term.

### Enabling Random Songs
1. Click the "Enable Random Songs" button.
2. Enter the number of random songs you want to enable.
3. The program will disable all songs first and then enable the specified number of random songs.

### Notes
- The `disabled` folder will be created automatically in the same directory as the script if it doesn't already exist.
- The program will move files between the DLC directory and the `disabled` folder based on your actions.

Enjoy managing your Rocksmith custom songs!
