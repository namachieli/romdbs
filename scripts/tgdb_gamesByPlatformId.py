#!/usr/bin/python3.6
import json
import sys
import requests
import os
import time

# TheGamesDB API Key
api_key = 'YOUR API KEY'
# TheGamesDB api base URL
tgdb_apiurl = 'https://api.thegamesdb.net'
# Also include Box Art data?
boxart = False



# Platform requested
if len(sys.argv) == 1:
	print(f"You need to specify the Name or Alias of a Platform to retrieve. Ex: \"Sony Playstation\"")
	sys.exit(1)	
else:
	platform = sys.argv[1]
	print(f"Platform: {platform}")


# Check if we already have Platforms, Developers, Genres, and Publishers downloaded. 
# If not, pull them down and save them for later use. (Lets not hammer the API for no reason)
dependency_path = "./"
dependencies = ['Platforms', 'Developers', 'Genres', 'Publishers']

dependency_data = {}

for d in dependencies:
	file=f"{dependency_path}tgdb_{d}.json"
	if os.path.isfile(file):
		print(f"Opening {d}")
		with open(file, 'r') as f:
			data = json.load(f)
		dependency_data[d] = data['data'][d.lower()]
	else:
		print(f"Cound't find local copy of {d}, downloading from API")
		try:
			r = requests.get(f"{tgdb_apiurl}/{d}?apikey={api_key}")
		except requests.exceptions.RequestException as e:
			print(e)
			sys.exit(1)
		data = json.loads(r.text)
		dependency_data[d] = data['data'][d.lower()]
		print(f"Creating {dependency_path}tgdb_{d}.json")
		with open(file, 'w') as f:
			json.dump(data, f)

# Find platform ID
for k, p in dependency_data['Platforms'].items():
	if platform == p['name'] or platform == p['alias']:
		platform_id = p['id']
		platform = p['name']

# Check that we found the requested platform
try: 
	platform_id
except NameError as e:
	print(f"Could not find an ID for Platform: {platform}. Please check you have the correct name or alias")
	sys.exit(1)

print(f"Found Platform: {platform} with ID: {platform_id}")

# Go get the games!
if os.path.isfile(f"./{platform}_raw_games.json"):
	###
	# Load from file
	###
	print(f"Loading lists from file for {platform}")
	with open(f"./{platform}_raw_games.json", 'r') as f:
		games_list = json.load(f)
	if boxart:
		if os.path.isfile(f"./{platform}_raw_boxart.json"):
			print(f"Boxart data found")
			with open(f"./{platform}_raw_boxart.json", 'r') as f:
				boxart_dict = json.load(f)
		else:
			print(f"Couldn't find file for boxart data, skipping")

else:

	confirm = input(f"Local data for '{platform}' not found, Continue and download from API? (y/N)")
	if confirm in ('y', 'Y', 'yes', 'Yes', 'YES'):
		pass
	else:
		print(f"User chose to not continue (didn't answer 'yes', Exiting...")
		sys.exit(1)
	###
	# Load from API
	###
	print(f"Downloading games list for {platform}")
	games_list = []
	fields="players,publishers,genres,overview,last_updated,rating,platform,coop,youtube,os,processor,ram,hdd,video,sound,alternates"
	if boxart:
		boxart_dict = {}
		include="boxart"
		url=f"{tgdb_apiurl}/Games/ByPlatformID?apikey={api_key}&id={platform_id}&fields={fields}&include={include}&page=1"
	else:
		url=f"{tgdb_apiurl}/Games/ByPlatformID?apikey={api_key}&id={platform_id}&fields={fields}&page=1"

	i = 1
	while True:
		print(f"Downloading page {i}", end='\r')
		try:
			r = requests.get(url)
		except 	requests.exceptions.RequestException as e:
			print(e)
			sys.exit(1)

		result = json.loads(r.text)

		games_list.extend(result['data']['games']) # Add games to list
		if boxart:
			boxart_dict.update(result['include']['boxart']['data']) # Add box art to dictionary
		if result['pages']['next'] is not None:
			url = result['pages']['next'] # set next page
			time.sleep(0.25) #Lets slow down a little and not completely hammer the API
		else:
			print(f"Finished Downloading {i} Pages", end='\r\n')
			break # No more pages
		i += 1

	###
	# For Troubleshooting/Queueing
	###
	print(f"Saving raw data for later use")
	with open(f"./{platform}_raw_games.json", 'w') as f:
		json.dump(games_list, f)
	if boxart:
		with open(f"./{platform}_raw_boxart.json", 'w') as f:
			json.dump(boxart_dict, f)

print(f"Parsing Games list and expanding IDs into values")
# Parse games list, expand ids into values and add in box art
i=0
expanded_games_list = [] # Storage list for post-expansion
for game in games_list:
	i += 1
	expanded_game = {} # Holding Dict for expanding current game
	expanded_game['platform_name'] = dependency_data['Platforms'][str(game['platform'])]['name'] # Add Platform Name into Dict
	print(f"Expanding Developers, Genres, and Publishers for {game['game_title']} ({i} of {len(games_list)})", end='\r')
	for dependency in ['developers', 'genres', 'publishers']: # Check each of the three dependencies
		if game[dependency] is not None: # Check that it has values
			expanded_game[dependency] = [] # Create an entry on the current game for this dependency
			dependency_list = [] # Create a holding list for all the lookups
			for _id in game.pop(dependency, None): # pop off the dependency in the current itteration and loop each id 
				dependency_list.append(dependency_data[dependency.capitalize()][str(_id)]['name']) # Lookup in the dependency data the name for this id
			expanded_game[dependency].extend(dependency_list) # add all the entries to the current game under the right dependency
		else:
			expanded_game[dependency] = None
		# remove from keys we don't care about
		game.pop('os', None)
		game.pop('processor', None)
		game.pop('ram', None)
		game.pop('hdd', None)
		game.pop('video', None)
		game.pop('sound', None)
		expanded_game.update(game) # add back in all the other fields that were already fine for the current itteration (game)

	if boxart:
		# Check if we have boxart info, and add it in if we do
		try:
			boxart_dict
		except NameError:
			pass
		else:
			expanded_game['boxart'] = []
			try:
				expanded_game['boxart'].extend(boxart_dict[str(game['id'])]) # Check if this game has box art info
			except NameError:
				pass

	expanded_games_list.append(expanded_game) # add the current game into the expanded list of games

print(f"Expanding Developers, Genres, and Publishers complete! ({i} of {len(games_list)}) Writting to file './{platform}.json' ", end='\r\n')

with open(f"./{platform}.json", 'w') as f:
	json.dump(expanded_games_list, f)
