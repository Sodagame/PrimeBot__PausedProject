#  -*- coding: utf-8 -*-
import os
import pkgutil
import sys
import traceback
from enum import Enum
from io import BytesIO

import disnake
from disnake.ext import commands
from disnake.ext.commands import Param


class Action(str, Enum):
    """
    Enum for the different actions that can be taken by the developer cog.
    """

    Enable = "enable"
    Disable = "disable"
    Reload = "reload"
    Remove = "remove"

    def __str__(self):
        return self.value


async def cog_autocomp(interaction: disnake.ApplicationCommandInteraction, user_input: str):
    """
    Autocomplete for the developer cog.

    Parameters
    -----------
    interaction : disnake.ApplicationCommandInteraction
        The command interaction object. This is not used.

    user_input : str
        The data entered by the user.

    Returns
    -------
    list
        A list of possible completions according to the user input.
    """
    cog_names = []
    for pkg in pkgutil.iter_modules(["cogs"]):
        cog_names.append(pkg.name)
    return [item for item in cog_names if user_input.lower() in item]


class Owner(commands.Cog, name="Developer"):
    """
    Commands specifically made for Bot developers and owners.
    """

    def __init__(self, bot):
        self.bot = bot

    async def cog_slash_command_error(
        self, interaction: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        """
        Handles errors raised by commands in the cog.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        error : Exception
            The error that was raised.
        """
        if interaction.response.is_done():
            safe_send = interaction.followup.send
        else:
            safe_send = interaction.response.send_message

        if isinstance(error, commands.NotOwner):
            await safe_send(
                embed=disnake.Embed(
                    description=f"{self.bot.icons['redtick']} You are not the owner of this bot.",
                    color=disnake.Colour.random(),
                ),
                ephemeral=True,
            )

            # ignore all other exception types, but print them to stderr
        else:
            error_msg = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            await safe_send(
                embed=disnake.Embed(
                    description=f"**Error invoked by: {str(interaction.author)}**\n"
                    f"Command: {interaction.application_command.name}\nError: "
                    f"```py\n{error_msg}```",
                    color=disnake.Colour.random(),
                )
            )

            print(
                f"Ignoring exception in command {interaction.application_command}: ",
                file=sys.stderr,
            )
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    @commands.slash_command(
        description="Commands that handle Bot commands and Cogs",
        invoke_without_command=True,
    )
    @commands.is_owner()
    async def botconfig(self, interaction: disnake.ApplicationCommandInteraction):
        pass

    @botconfig.sub_command(description="Cog manager")
    @commands.is_owner()
    async def cog(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        action: str = Param(autocomplete=Action),
        cog: str = Param(autocomplete=cog_autocomp),
    ):
        """
        This command manages the cogs of the bot. It can enable, disable, reload, and remove cogs.
        Only Bot owners can use this command.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        action : str
            The action to perform on the cog.

        cog : str
            The name of the cog to perform the action on.

        Examples
        --------
        `/botconfig cog action: enable cog: Developer_`
        """

        if action.lower() == "disable":

            try:
                self.bot.unload_extension(f"cogs.{cog}")
            except Exception as e:
                return await interaction.response.send_message(
                    embed=disnake.Embed(
                        description=f"Cog **{cog}** is not loaded.\nError:\n```py\n{e}\n```",
                        color=disnake.Colour.random(),
                    ),
                    ephemeral=True,
                )

            await interaction.response.send_message(
                embed=disnake.Embed(
                    description=f"Cog **{cog}** has stopped running.",
                    color=disnake.Colour.random(),
                ),
                ephemeral=True,
            )

        elif action.lower() == "enable":

            try:
                self.bot.load_extension(f"cogs.{cog}")
            except Exception as error:
                with BytesIO() as file:
                    trace = __import__("traceback").format_exception(
                        etype=type(error), value=error, tb=error.__traceback__
                    )
                    file.write(bytes("".join(trace).encode("ascii")))
                    file.seek(0)

                    error_file = disnake.File(fp=file, filename="error.log")

                return await interaction.response.send_message(
                    f"{self.bot.icons['info']} This cog has an error located in it. ",
                    file=error_file,
                    ephemeral=True,
                )

            await interaction.response.send_message(
                f"Cog **{cog}** is now running.", ephemeral=True
            )

        elif action.lower() == "reload":

            try:
                self.bot.reload_extension(f"cogs.{cog}")
            except Exception as error:
                with BytesIO() as file:
                    trace = __import__("traceback").format_exception(
                        etype=type(error), value=error, tb=error.__traceback__
                    )
                    file.write(bytes("".join(trace).encode("ascii")))
                    file.seek(0)

                    error_file = disnake.File(fp=file, filename="error.log")

                return await interaction.response.send_message(
                    f"{self.bot.icons['info']} This cog has an error located in it. ",
                    file=error_file,
                    ephemeral=True,
                )

            await interaction.response.send_message(
                f"Cog **{cog}** has been reloaded.", ephemeral=True
            )

    @botconfig.sub_command(description="Shows cog information")
    async def coginfo(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This command shows information about the cogs of the bot.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/coginfo`
        """
        loaded_cogs = []
        for cog in self.bot.extensions.keys():
            cog_name = cog.split(".")
            try:
                loaded_cogs.append(f"{cog_name[1] + '.py'}")
            except IndexError:
                continue
        print(loaded_cogs)
        unloaded = []
        cogs = 0
        for file in os.listdir("./cogs"):
            if file != "__pycache__":
                cogs += 1
                if file not in loaded_cogs:
                    unloaded.append(file)

        embed = disnake.Embed(
            title="Loaded Cogs & Commands:", colour=disnake.Colour.random()
        )
        embed.add_field(
            name="Cogs:",
            value=f"**Total:** `{cogs}`\n**Loaded:** `{len(loaded_cogs)}`"
            f"\n**Unloaded:** `{', '.join(unloaded) or 'None!'}`",
        )
        enabled, disabled, _commands = 0, 0, []
        for command in self.bot.all_slash_commands:
            cmd = self.bot.get_slash_command(command)
            _commands.append(cmd.name)
        embed.add_field(
            name="Commands:",
            value=f"**Total commands:** `{len(self.bot.all_slash_commands)}`",
            inline=False,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.slash_command(description="Purge bot messages.")
    @commands.is_owner()
    async def cleanup(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        amount: int = Param(description="Amount of messages", default=10),
    ):
        """
        This command purges messages from the channel.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        amount : int
            The amount of messages to purge.

        Examples
        --------
        `/cleanup amount: 15`
        """
        await interaction.response.send_message(
            f"Deleting {amount} messages now...", ephemeral=True
        )
        deleted = []
        messages = []
        async with interaction.channel.typing():
            async for m in interaction.channel.history(limit=amount):
                messages.append(m)
                if m.author == self.bot.user:
                    try:
                        await m.delete()
                    except Exception as error:
                        self.bot.logger.error(error)
                        pass
                    else:
                        deleted.append(m)

    @commands.slash_command(
        name="setstatus",
        description="Sets the bot status.",
        invoke_without_command=True,
    )
    @commands.is_owner()
    async def status(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This command sets the bot status. Only Bot Owner can use this command.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/setstatus watching game: disnake`
        """
        pass

    @status.sub_command(description="Set Streaming Status.")
    async def streaming(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        url: str = Param(description="Stream url"),
        game: str = Param(description="Your game name here"),
    ):
        """
        This subcommand sets the bot status to streaming.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        url : str
            The url of the stream.
        game : str
            The game you are playing.

        Examples
        --------
        `/setstatus streaming url: https://www.twitch.tv/disnake game: disnake`
        """
        game = game.replace("{users}", str(len(self.bot.users))).replace(
            "{guilds}", str(len(self.bot.guilds))
        )
        await self.bot.change_presence(
            activity=disnake.Streaming(
                name=str(game), url=f"https://www.twitch.tv/{url}"
            )
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Streaming status set to **{game}**",
                colour=disnake.Colour.random(),
            ),
            ephemeral=True,
        )

    @status.sub_command(description="Set Playing Status.")
    async def playing(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        game: str = Param(description="Your game name here"),
    ):
        """
        This subcommand sets the bot status to playing.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.
        game : str
            The game you are playing.

        Examples
        --------
        `/setstatus playing game: disnake`
        """

        game = game.replace("{users}", str(len(self.bot.users))).replace(
            "{guilds}", str(len(self.bot.guilds))
        )
        await self.bot.change_presence(activity=disnake.Game(name=game))
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Playing status set to **{game}**",
                colour=disnake.Colour.random(),
            ),
            ephemeral=True,
        )

    @status.sub_command(description="Set Watching Status.")
    async def watching(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        game: str = Param(description="Your game name here"),
    ):
        """
        This subcommand sets the bot status to watching.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        game : str
            The game you are watching.

        Examples
        --------
        `/setstatus watching game: disnake`
        """

        game = game.replace("{users}", str(len(self.bot.users))).replace(
            "{guilds}", str(len(self.bot.guilds))
        )
        await self.bot.change_presence(
            activity=disnake.Activity(name=f"{game}", type=3)
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Watching status set to **{game}**",
                colour=disnake.Colour.random(),
            ),
            ephemeral=True,
        )

    @status.sub_command(description="Set Listening Status.")
    async def listening(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        game: str = Param(description="Your game name here"),
    ):
        """
        This subcommand sets the bot status to listening.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        game : str
            The game you are listening to.

        Examples
        --------
        `/setstatus listening game: disnake`
        """

        game = game.replace("{users}", str(len(self.bot.users))).replace(
            "{guilds}", str(len(self.bot.guilds))
        )
        await self.bot.change_presence(
            activity=disnake.Activity(name=f"{game}", type=2)
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Listening status set to **{game}**",
                colour=disnake.Colour.random(),
            ),
            ephemeral=True,
        )

    @status.sub_command(description="Set Competing Status.")
    async def competing(
        self,
        interaction: disnake.ApplicationCommandInteraction,
        game: str = Param(description="Your game name here"),
    ):
        """
        This subcommand sets the bot status to competing.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        game : str
            The game you are competing in.

        Examples
        --------
        `/setstatus competing game: disnake`
        """

        game = game.replace("{users}", str(len(self.bot.users))).replace(
            "{guilds}", str(len(self.bot.guilds))
        )
        await self.bot.change_presence(
            activity=disnake.Activity(name=f"{game}", type=5)
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Competing status set to **{game}**",
                colour=disnake.Colour.random(),
            ),
            ephemeral=True,
        )

    @status.sub_command(description="Set Original Bot Status.")
    async def reset(self, interaction: disnake.ApplicationCommandInteraction):
        """
        This subcommand resets the bot status to the original status.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The Interaction of the command.

        Examples
        --------
        `/setstatus reset`
        """

        await self.bot.change_presence(
            activity=disnake.Game(
                f"{len(self.bot.guilds)} guilds & {len(self.bot.users)} users"
            )
        )
        await interaction.response.send_message(
            embed=disnake.Embed(
                description=f"Bot status resetted", colour=disnake.Colour.random()
            ),
            ephemeral=True,
        )


def setup(bot):
    bot.add_cog(Owner(bot))
