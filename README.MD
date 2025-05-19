# Selfbot README

## Disclaimer

**Use of selfbots is against Discord's Terms of Service (ToS)**, and using this selfbot may result in your account being banned or terminated. Proceed at your own risk.

## commands

### Games

- **dox**  
  Aliases: None  
  Help: Sends a random, fake, and funny dox message.  
  Usage: `?dox @user`

- **mimic**  
  Aliases: m  
  Help: Repeats messages from a user in quotes, optionally with an emoji.  
  Usage: `?m @user [:emoji:]`

- **mimicstop**  
  Aliases: ms  
  Help: Stops mimicking a user.  
  Usage: `?ms`

### Messages

- **send**  
  Aliases: None  
  Help: Sends random messages to the specified channel.  
  Usage: `?send <text>`

- **stop**  
  Aliases: None  
  Help: Stops sending random messages.  
  Usage: `?stop`

- **clear**  
  Aliases: None  
  Help: Clears a specified number of bot messages in the current channel.  
  Usage: `?clear <limit>`

- **h**  
  Aliases: None  
  Help: Shows available command categories or lists commands within a category.  
  Usage: `?h [category]`

- **ping**  
  Aliases: None  
  Help: Checks bot latency.  
  Usage: `?ping`

- **logs**  
  Aliases: None  
  Help: (No help specified)  
  Usage: (No usage specified)

### Operators

- **shutdown**  
  Aliases: sd  
  Help: Shuts the bot down completely.  
  Usage: `?sd`

- **restart**  
  Aliases: None  
  Help: Restarts the bot and reloads all cogs.  
  Usage: `?restart`

### Reactions

- **react**  
  Aliases: r  
  Help: Starts auto-reacting with multiple emojis, optionally filtered by users.  
  Usage: `?r :emoji1: :emoji2: ... [@user1] [@user2] ...`

- **reactstop**  
  Aliases: rs  
  Help: Stops auto-reacting for a specific reaction ID.  
  Usage: `?rs <id>`

- **reactold**  
  Aliases: ro  
  Help: Adds reactions to past messages using the specified emoji, optionally filtered by user.  
  Usage: `?ro :emoji: @optionaluser`

- **reactoldstop**  
  Aliases: ros  
  Help: Stops processing old messages for reactions.  
  Usage: `?ros`

- **reactremove**  
  Aliases: rr  
  Help: Removes the bot’s own reactions from past messages.  
  Usage: `?rr`

- **reactstopremove**  
  Aliases: rsr  
  Help: Stops removing the bot’s reactions from messages.  
  Usage: `?rsr`

- **reactlist**  
  Aliases: rl  
  Help: Lists all configured reactions.  
  Usage: `?rl`

## Info

- **pokemon**
automatically catches pokemon from `Pokétwo#8236` if enabled in config, stopping if verification is required and optionally sending you a text letting you know.
will pull cookies from your browser and attempt to fake your headers to verify through poketwo

- **logging**
logs user mentions, and pokemon catching activity

- **grow a tree**
automatically waters your tree when possible if you have `Grow a Tree#5130`

- **multiple accounts**
optional helper account config that send with the user, (up to 5, easy change though)

## Requirements

- **Python 3.9 or higher**: Ensure Python is installed on your system and in PATH.

## Installation

### 1. Download and Install Python

1. Go to the [official Python website](https://www.python.org/downloads/).
2. Download the latest version of Python (3.8 or higher).
3. During installation, ensure you check the box that says "Add Python to PATH".

### 2. Clone the Repository

Clone this repository to your local machine using:
bash
git clone <https://github.com/JellyLovesYou/SelfBot/tree/main>
Alternatively, download the ZIP file and extract it.

## 3. Install Required Packages

Navigate to the directory where you cloned or extracted the repository and run:

bash

```py
pip install -r requirements.txt
```

## Configuration

Open `data/config/config.show.jsonc` file in a text editor.
Replace the placeholders with your actual values, remove comments, change to config.json
You can also just copy the contents into `data/config/config.json` after creating it.
Same with `data/config/telecom.show.jsonc` -> `data/config/telecom.json`

## Running the Selfbot

Once you've configured everything, you can run the selfbot with:
python `main.py`
