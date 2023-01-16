"""
Copyright 2022-present fretgfr

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is **not** meant to be run on it's own, rather it's meant to serve as a guide
of sorts for extending the `reminders` extension to handle other scenarios besides just reminders.
You should read and understand the general idea and format of what this is doing before attempting to use it.
"""

from discord.ext import commands, tasks


# You'll want to change the names that are used.
class YourCogName(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self) -> None:
        self.future_tasks_loop.start()

    async def cog_unload(self) -> None:
        self.future_tasks_loop.cancel()

    @tasks.loop()
    async def future_tasks_loop(self):
        # Steps only given here, you can extrapolate from them and the code in `reminders.py`
        # if you want a working example to base this format off of.

        # 1.) Get the next task to run from your loop if there is one
        #   - If there isn't one, stop the loop and return

        # 2.) Get a datetime for when the next task needs to take place

        # 3.) Use `discord.utils.sleep_until` to sleep until when the task takes place

        # 4.) Perform your task callback(s), passing in the information they need that you have stored.
        #   - If you store enum values (e.g. "reminder" or "tempban" in this example) in your db
        #     then you can get the enum value of it using TaskType['reminder'] etc.

        # 5.) Mark your database entry as completed or delete it, depending on if you want to keep
        #     a record of the items that were completed.
        ...

    @future_tasks_loop.before_loop
    async def before_future_tasks_loop(self):
        await self.bot.wait_until_ready()

    def start_restart_task(self) -> None:
        # This function needs to be called any time something is added or removed from your loop.
        if self.future_tasks_loop.is_running():
            self.future_tasks_loop.restart()
        else:
            self.future_tasks_loop.start()


# Of course you'd need setup functions at the end if it's an extension etc.