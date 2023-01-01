# Generic Cogs

This project is a collection of generic extensions/cogs that can be used with discord.py.

**All files were developed with Python 3.11.1 and tested with discord.py version 2.1.0.**

**All licenses are contained within the individual files. If no license is present, you may assume it's MIT licensed.**

In general, these files follow the same basic template. If they require a database, they are configured to use `asqlite`, and may use differently named files for each specific function. This behavior could be changed by you.

Converting the commands contained within to slash commands should be a trivial task, though some of the commands (namely the ones reserved for bot owner usage) should not be converted, as they are better served as prefix commands.

All extensions assume that you have the following intents enabled:
- message_content
- guilds
- members
- messages
- emojis
- reactions

Any intents required specifically by an extensions *should* be noted in that extension, however this is not a guarantee. If an extension fails to work properly for you, please check the intents that your bot has and that are required by the extension(s) before filing an issue.

# Contributions and Issues

If you'd like to contribute, feel free to submit a pull request. If you find an error with any of the code, please file an issue.