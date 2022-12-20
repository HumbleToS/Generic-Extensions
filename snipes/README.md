# Snipes

The files in this folder deal with "snipes" on Discord. The files require guild_messages, message_content, and reactions intents to properly function. The Members intent is recommended.

`messagesnipe.py` deals with deleted messages, `editsnipe.py` deals with edited messages, and `reactionsnipe.py` deals with removed reactions.

The contents of `snipescommon.py` and `optout.py` are used in the the other snipe modules for consistency and to abide by the requirement that users can opt out of message recording.

**It is highly recommended that you do not remove the optout module as you may be violating Discord's rules if you do.**

## Dependencies

All snipe files rely on `asqlite` (https://github.com/Rapptz/asqlite) and `typing_extensions` being installed through pip via `pip install git+https://github.com/Rapptz/asqlite`.


## Customization

- The database filename can be changed in `snipescommon.py`.
- A decorator is provided in `optout.py` for use on any snipe related commands you'd like. Simply import it and add it as a check.
- The amount of time snipes are kept in the database can be changed by altering the `TTL_MINUTES` variable in each file. Note that the maximum age of a snipe will be `TTL_MINUTES * 2` minutes.
- Embed formatting can be changed by editing the `embed` coroutine for each snipe type.

## License

All files in this folder are licensed under the MIT License. You may use them in accordance with the terms of the license.
