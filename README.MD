# Selfbot README

## Disclaimer

**Use of selfbots is against Discord's Terms of Service (ToS)**, and using this selfbot may result in your account being banned or terminated. Proceed at your own risk.

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
git clone <repository_url>
Alternatively, download the ZIP file and extract it.

## 3. Install Required Packages

Navigate to the directory where you cloned or extracted the repository and run:

bash

```py
pip install -r requirements.txt
```

## Configuration

Open the `config.json` file in a text editor.
Replace the placeholders with your actual values

```json
{
    "main":{
        "prefix": "?",
        "user id": "",
        "version": "1.0.0",
        "catching?": true, // do you want to catch pokemon
        "p2assistant?": false // mostly useless now
    },
    "text": {
        "pokemon": true // do you want to get texts about p2 verification?
    },
    "paths":{
        "env": "C:\\Users\\Lego\\.env", // use an env 
        "venv": "C:\\Users\\Lego\\projects\\SelfBot\\v2\\venv\\Scripts\\python.exe", // use a venv
        "activity": "data/runtime/activity.json",
        "code logs": "data/logs/code.log",
        "discord logs": "data/logs/discord.log",
        "pokemon logs": "data/logs/pokemon.log",
        "helpers": "helpers.py",
        "restart": "data/runtime/restart.signal",
        "pokemon": "data/text/pokemon.json"
    },
    "ids":{
        "watch id": "854233015475109888",
        "mention id": "716390085896962058",
        "tree": "1177314426299363409" // change channel id for 'Grow a Tree#5130'
    }
}
```

## Running the Selfbot

Once you've configured everything, you can run the selfbot with:
python `main.py`
