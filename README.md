# SauceBot
[![Discord](https://img.shields.io/discord/722787678546034769?label=discord&logo=discord&logoColor=ffffff&color=7389D8&labelColor=6A7EC2)](https://discord.gg/p7fstG4) [![GitHub](https://img.shields.io/github/license/FujiMakoto/saucebot)](https://github.com/FujiMakoto/saucebot/blob/master/LICENSE) [![GitHub release (latest by date)](https://img.shields.io/github/v/release/fujimakoto/saucebot)](https://github.com/FujiMakoto/saucebot/releases)

SauceBot is an open-source Discord bot that utilizes the [SauceNao API](https://saucenao.com/) to find the source of images or anime screencaps.

## Documentation
### Inviting the bot
You can invite SauceBot to your server using the following invite link. Keep in mind, it's still in beta!

https://discord.com/api/oauth2/authorize?client_id=718642000898818048&permissions=604892224&scope=bot

### Using the bot
SauceBot can operate in multiple ways. All of which center around using the `?sauce` command.

The first way is to provide a direct URL to the image you want to look up as a command argument, like so,
```
?sauce https://i.redd.it/rqtzjynwx7351.jpg
```

![Bot demonstration](https://i.imgur.com/4zbCKbc.png)

The second way is to upload an image to the channel and supply `?sauce` as the images comment.

Lastly, if someone just uploaded an image to a channel and you want to look up the sauce, just use the `?sauce` command without any arguments, and it'll automatically do a search on the last attachment uploaded to that channel!

### Increasing your API limits
Each Discord server is currently allotted 50 free API queries/day from a shared pool. This value may change depending on how much Patreon/Github funding the project receives, and how popular the bot becomes.

If you run a larger server and need more API queries, you can upgrade to a limit of 5,000 queries/day by obtaining an [enhanced license key](https://saucenao.com/user.php?page=account-upgrades) directly from SauceNao for $6/month.

To register an API key to your server, run `?apikey YOUR_API_KEY_HERE` from a channel that only administrators have access to. (You'll need to grant the bot access to this channel as well, at least temporarily).

You should receive a confirmation message afterwards verifying your API key was successfully linked.

Keep in mind, this will only work for **enhanced** license keys. Freely registered API keys will not work, as these are still IP restricted (meaning, multiple free accounts cannot be used on the same network). If you want to use a freely registered API key, you'll need to run your own instance of the bot.

### Give it a test run!
Want to give SauceBot a try? Join the support discord and use the `#sfw-lookups` and `#nsfw-lookups` channels respectively to experiment!

https://discord.gg/p7fstG4

### Supporters
We unfortuantely don't have any supporters yet. Perhaps you'd like to be the first?

If you sponsor this project on Patreon, your name will be added here!

https://www.patreon.com/saucebot
