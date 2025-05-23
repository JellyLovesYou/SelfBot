## How to Find Your Discord Cookies

**Note: Cookie extraction is only required if you want to use 2 authenticated users. For single user scenarios, the script will automatically handle authentication setup.**

If you need to run with 2 authenticated users, you'll need to extract specific cookies from your Discord session. Follow the steps below for your browser:

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
