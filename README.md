# SauceBot
![GitHub](https://img.shields.io/github/license/FujiMakoto/saucebot) ![GitHub release (latest by date)](https://img.shields.io/github/v/release/fujimakoto/saucebot)

SauceBot is an open-source Discord bot that utilizes the [SauceNao API](https://saucenao.com/) to find the source of images or anime screencaps.

## Documentation
### Registering a SauceNAO API key
This is required to get the bot up and running on your server. The Sauce commands will not work until you have an API key registered.

Freely registered accounts have a limit of 200 per day, and SauceNAO supporters have a limit of 5000 queries per day.

You can register for an API key here:

https://saucenao.com/user.php?page=search-api

### Inviting the bot
You can invite SauceBot to your server using the following invite link. Keep in mind, it's still in beta!

https://discord.com/api/oauth2/authorize?client_id=718642000898818048&permissions=604892224&scope=bot

### Using the bot
Before you can use the bots Sauce commands, you'll need to register the API key you obtained above.

To do this, run `?apikey YOUR_API_KEY_HERE` from a channel that only administrators have access to. (You'll need to grant the bot access to this channel as well, at least temporarily).

Once that's out of the way, you and your members will be able to look up the source of uploads using the bots `?sauce` command!

This command will either search for the sauce of the attached image, the specified image URL, or the last image uploaded to the channel.

![Bot demonstration](https://i.imgur.com/4zbCKbc.png)
