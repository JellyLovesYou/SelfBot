# 🤖 Discord Selfbot

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Discord](https://img.shields.io/badge/Discord-Selfbot-7289da.svg)](https://discord.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## *A feature-rich Discord selfbot for automation and entertainment*

---

## ⚠️ **IMPORTANT DISCLAIMER**

> **Using selfbots violates Discord's Terms of Service and may result in account suspension or termination.**  
> **Use at your own risk. The developers are not responsible for any consequences.**

---

## ✨ **Features**

### 🎮 **Entertainment & Games**

- **Fake Dox Generator** - Send hilarious fake dox messages
- **Message Mimicker** - Copy and repeat user messages with custom emojis
- **Auto Pokemon Catcher** - Automatically catch Pokémon from Pokétwo bot
- **Tree Watering** - Auto-water your Grow a Tree bot trees

### 💬 **Message Management**

- **Bulk Message Sender** - Send random messages to channels
- **Smart Message Cleaner** - Clear bot messages efficiently
- **Comprehensive Logging** - Track mentions and bot activity

### 🎭 **Reaction Automation**

- **Multi-Emoji Auto-React** - React with multiple emojis automatically
- **Historical Reactions** - Add reactions to past messages
- **User-Filtered Reactions** - Target specific users
- **Reaction Management** - Full control over all reaction features

### 🔧 **System Controls**

- **Multi-Account Support** - Manage up to 5 helper accounts
- **Smart Restart System** - Reload without losing configuration
- **Advanced Logging** - Detailed activity tracking

---

## 🚀 **Quick Start**

### **Prerequisites**

- 🐍 **Python 3.9+** - [Download here](https://python.org/downloads/)
- 🔑 **Discord Token** - Your account token
- 💻 **Basic terminal knowledge**

### **Installation**

1. **Clone the repository**

   ```bash
   git clone https://github.com/JellyLovesYou/SelfBot.git
   cd SelfBot
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**

   ```bash
   # Copy the example config
   cp data/config/config.show.jsonc data/config/config.json
   cp data/config/telecom.show.jsonc data/config/telecom.json
   
   # Edit with your settings
   nano data/config/config.json
   ```

4. **Launch the bot**

   ```bash
   python main.py
   ```

---

## 📋 **Command Reference**

### 🎮 **Games & Fun**

| Command | Usage | Description |
|---------|-------|-------------|
| `?dox @user` | Mention a user | Sends a fake, humorous dox message |
| `?mimic @user [:emoji:]` | `?m @user 😂` | Mimics user messages with optional emoji |
| `?mimicstop` | `?ms` | Stops mimicking current user |

### 💬 **Message Commands**

| Command | Usage | Description |
|---------|-------|-------------|
| `?send <text>` | `?send Hello world!` | Sends random messages to channel |
| `?stop` | - | Stops sending random messages |
| `?clear <limit>` | `?clear 10` | Clears specified number of bot messages |
| `?ping` | - | Checks bot latency |
| `?h [category]` | `?h Games` | Shows help for commands |

### 🎭 **Reaction System**

| Command | Usage | Description |
|---------|-------|-------------|
| `?react :emoji: [@users]` | `?r 😀 😎 @user1` | Auto-react with emojis |
| `?reactstop <id>` | `?rs 1` | Stop specific auto-reaction |
| `?reactold :emoji: [@user]` | `?ro 👍 @user` | React to past messages |
| `?reactoldstop` | `?ros` | Stop processing old messages |
| `?reactremove` | `?rr` | Remove bot's reactions |
| `?reactlist` | `?rl` | List all active reactions |

### ⚙️ **System Controls**

| Command | Usage | Description |
|---------|-------|-------------|
| `?shutdown` | `?sd` | Completely shut down bot |
| `?restart` | - | Restart and reload all modules |
| `?logs` | - | Access system logs |

---

## 🤖 **Automated Features**

### **🎯 Pokémon Auto-Catcher**

- Automatically catches Pokémon from `Pokétwo#8236`
- Handles verification challenges intelligently
- Uses browser cookies for authentication
- Sends notifications when manual intervention needed

### **🌳 Tree Auto-Waterer**

- Automatically waters trees in `Grow a Tree#5130`
- Smart timing to maximize efficiency
- Prevents over-watering

### **📊 Advanced Logging**

- Tracks user mentions across servers
- Monitors Pokémon catching statistics
- Records all bot activities
- Exportable log data

### **👥 Multi-Account Support**

- Configure up to 5 helper accounts
- Synchronized operations
- Easy account switching
- Bulk command execution

---

## ⚙️ **Configuration**

The bot uses JSON configuration files located in `data/config/`:

- **`config.json`** - Main bot settings and tokens
- **`telecom.json`** - Communication and notification settings

**Example configuration structure:**

```json
{
    "main":{
        "prefix": "", // prefix
        "user id": "", // your user id
        "nickname": "",
        "version": "1.0.1",
        "catching?": true,
        "p2assistant?": false,
        "texts?": true,
        "helpers?": true,
        "solving?": true,
        "sniping?": true,
        "fishing?": true,
        "fishing paid?": false
    },
    "text": {
        "pokemon": true,
        "fishing": true
    },
    "paths":{
        "env": "", // absolute path to .env
        "venv": "" // absolute path to python.exe in venv 
    },
    "ids":{
        "watch id": "854233015475109888",
        "mention id": "716390085896962058",
        "tree id": "972637072991068220",
        "fish id": "574652751745777665",
        "tree channel": "", // channel id for Grow a Tree#5130
        "fish channel": "", // channel id for Virtual Fisher#7036
        "guild": "" // guild id
    }
}
```

---

```json
[
  {
    "name": "__dcfduid",
    "value": "",
    "domain": ".discord.com",
    "path": "/",
    "expires": -1,
    "httpOnly": false,
    "secure": true,
    "sameSite": "Lax"
  },
  {
    "name": "__sdcfduid",
    "value": "",
    "domain": ".discord.com",
    "path": "/",
    "expires": -1,
    "httpOnly": false,
    "secure": true,
    "sameSite": "Lax"
  },
  {
    "name": "__cfruid",
    "value": "",
    "domain": ".discord.com",
    "path": "/",
    "expires": -1,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  },
  {
    "name": "_cfuvid",
    "value": "",
    "domain": ".discord.com",
    "path": "/",
    "expires": -1,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  },
  {
    "name": "cf_clearance",
    "value": "",
    "domain": ".discord.com",
    "path": "/",
    "expires": 1779401172.281411,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  },
  {
    "name": "__cf_bm",
    "value": "",
    "domain": ".discord.gg",
    "path": "/",
    "expires": 1747867896.295188,
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
  }
]
```

## How to Find Your Discord Cookies

### **Note: Cookie extraction is only required if you use 2 factor authentication. For single user scenarios, the script will automatically handle authentication setup.**

### **Note: Cookie extraction is also only required for fishing and watering tasks**

If you need to run with 2 factor authentication, you'll need to extract specific cookies from your Discord session. Follow the steps below for your browser:

### Chrome / Edge / Brave

1. Open Discord in your browser and make sure you're logged in
2. Press `F12` or right-click anywhere and select "Inspect" to open Developer Tools
3. Go to the **Application** tab (or **Storage** tab in some browsers)
4. In the left sidebar, expand **Cookies** and click on `https://discord.com`
5. Look for the following cookie names and copy their values:
   - `__dcfduid`
   - `__sdcfduid`
   - `__cfruid`
   - `_cfuvid`
   - `cf_clearance`
6. Also check cookies for `https://discord.gg` and look for:
   - `__cf_bm`

### Firefox

1. Open Discord in Firefox and ensure you're logged in
2. Press `F12` to open Developer Tools
3. Go to the **Storage** tab
4. Expand **Cookies** in the left sidebar and click on `https://discord.com`
5. Find the required cookies listed above and copy their values
6. Check `https://discord.gg` for the `__cf_bm` cookie as well

### Safari

1. First enable the Develop menu: Go to Safari > Preferences > Advanced > Show Develop menu
2. Open Discord and make sure you're logged in
3. Go to Develop > Show Web Inspector
4. Click the **Storage** tab
5. Expand **Cookies** and select `discord.com`
6. Locate the required cookies and copy their values

### Filling the Configuration

Once you have the cookie values, replace the empty `"value": ""` fields in your configuration with the actual cookie values you copied. Make sure to keep the quotation marks around the values.

**Important Note:**
Keep your cookies secure and never share them publicly

### Troubleshooting

- **Cookie not found**: Try refreshing Discord and checking again, if a cookie is not found, delete it from the .json
- **Empty values**: Make sure you're logged into Discord when extracting cookies

---

## 🛡️ **Safety & Security**

- **Token Security**: Never share your Discord token
- **Rate Limiting**: Built-in protection against API limits
- **Stealth**: Designed to minimize detection risk

---

## 🤝 **Contributing**

We welcome contributions! Please feel free to:

- 🐛 Report bugs
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📖 Improve documentation

---

## 📞 **Support**

Having issues? Check out our troubleshooting guide or reach out:

- 📋 **Issues**: Use GitHub Issues for bug reports
- 💬 **Discord**: [Join our support server](https://discord.gg/Ps7e7zR7tQ)

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⭐ Star this repository if you found it helpful!**

## *Made with ❤️ -legolovesyou*
