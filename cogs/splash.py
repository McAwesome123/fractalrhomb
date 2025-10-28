# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Splash cog for the bot."""

import asyncio
import datetime as dt
import logging
from math import ceil

import aiohttp.client_exceptions as client_exc
import discord
from aiohttp.web import HTTPForbidden, HTTPTooManyRequests, HTTPUnauthorized

import src.fractalrhomb_globals as frg
import src.fractalthorns_dataclasses as ftd
from src.fractalthorns_api import fractalthorns_api


class Splash(discord.Cog):
	"""Class defining the splash cog."""

	def __init__(self, bot: discord.Bot) -> "Splash":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("fractalrhomb.cogs.splash")

	class ResendSplashView(discord.ui.View):
		"""A view for resending the submitted splash."""

		def __init__(self) -> "Splash.ResendSplashView":
			"""Create a resend splash view."""
			super().__init__(disable_on_timeout=True)
			self.value = False

		async def finish_callback(
			self, button: discord.ui.Button, interaction: discord.Interaction
		) -> None:
			"""Finish a callback after pressing a button."""
			button.style = discord.ButtonStyle.secondary

			self.disable_all_items()
			await interaction.response.edit_message(view=self)

			self.stop()

		@discord.ui.button(
			emoji="📝", label="Send to DMs", style=discord.ButtonStyle.primary
		)
		async def confirm_button_callback(
			self, button: discord.ui.Button, interaction: discord.Interaction
		) -> None:
			"""Give True if the button is clicked."""
			self.value = True

			await self.finish_callback(button, interaction)

	splash_group: discord.SlashCommandGroup = discord.SlashCommandGroup(
		"splash", "Fractalthorns splash commands"
	)

	@splash_group.command(name="view")
	async def current_splash(self, ctx: discord.ApplicationContext) -> None:
		"""Show the current splash."""
		self.logger.info("Current splash command used")

		if not await frg.bot_channel_warning(ctx):
			return

		try:
			response = await fractalthorns_api.get_current_splash(frg.session)

			response = response.format(include_ordinal=False)

			await frg.send_message(ctx, response, "\n")

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.CURRENT_SPLASH
					)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Splash.current_splash"
			)

	@splash_group.command(name="page")
	@discord.option(
		"page",
		int,
		description="Which page to view (1 is newest)",
	)
	async def paged_splashes(self, ctx: discord.ApplicationContext, page: int) -> None:
		"""Show a page of splashes."""
		self.logger.info("Paged splashes command used (page=%s)", page)

		if not await frg.bot_channel_warning(ctx):
			return

		try:
			response = await fractalthorns_api.get_paged_splashes(frg.session, page)

			response = response.format()
			responses = frg.split_message([response], "")

			if not await frg.message_length_warning(ctx, responses, 1000):
				return

			ping_user = True
			for i in responses:
				if not await frg.send_message(ctx, i, "\n", ping_user=ping_user):
					break
				ping_user = False

			tasks = set()
			async with asyncio.TaskGroup() as tg:
				task = tg.create_task(
					fractalthorns_api.save_cache(
						fractalthorns_api.CacheTypes.SPLASH_PAGES
					)
				)
				tasks.add(task)
				task.add_done_callback(tasks.discard)

		except* (TimeoutError, client_exc.ClientError) as exc:
			await frg.standard_exception_handler(
				ctx, self.logger, exc, "Splash.paged_splashes"
			)

	async def resend_splash(
		self,
		ctx: discord.ApplicationContext,
		splash: ftd.Splash,
		resend_splash: ResendSplashView,
		resend_message: discord.Interaction | discord.WebhookMessage,
		attempt: int,
	) -> None:
		"""Resend a splash to a user."""
		max_attempts = 5

		await resend_splash.wait()

		if resend_splash.value:
			try:
				await ctx.author.send(f"splash submitted:\n{splash.format()}")
			except discord.errors.Forbidden as exc:
				retry_resend = False

				if exc.code == frg.CANNOT_SEND_MESSAGE_TO_USER_ERROR_CODE:
					add_bot_to_account = "add the bot to your account"
					if frg.BOT_AUTH_URL is not None:
						add_bot_to_account = (
							f"{add_bot_to_account} (<{frg.BOT_AUTH_URL}>)"
						)

					response = (
						"could not resend splash because you do not allow receiving messages from the bot (or have blocked it)\n"
						f"allow direct messages from server members or {add_bot_to_account}"
					)

					if attempt < max_attempts:
						retry_resend = True
						response += " and try again"
						new_resend_splash = self.ResendSplashView()

				else:
					self.logger.exception(
						"An error occurred when resending a splash message"
					)

					report_issue = "report this"
					bot_creator = "the bot creator"
					if frg.BOT_ISSUE_URL is not None:
						report_issue = f"[{report_issue}](<{frg.BOT_ISSUE_URL}>)"
					if frg.BOT_CREATOR_ID is not None:
						bot_creator = f"[{bot_creator}](<{frg.DISCORD_PROFILE_LINK}{frg.BOT_CREATOR_ID}>)"

					response = f"could not resend splash due to an unknown error. please {report_issue} to {bot_creator}"

				resend_splash.children[0].style = discord.ButtonStyle.red
				await resend_message.edit(view=resend_splash)

				if retry_resend:
					new_resend_message = await ctx.respond(
						response, view=new_resend_splash, ephemeral=True
					)
					await self.resend_splash(
						ctx, splash, new_resend_splash, new_resend_message, attempt + 1
					)
				else:
					await ctx.respond(response, ephemeral=True)

			else:
				resend_splash.children[0].style = discord.ButtonStyle.success
				await resend_message.edit(view=resend_splash)

	@splash_group.command(
		name="submit", description="Submit a splash to fractalthorns (24h cooldown)."
	)
	@discord.option(
		"splash",
		str,
		description="The splash text (max 80 characters)",
		min_length=1,
		max_length=80,
		parameter_name="splash_text",
	)
	async def submit_splash(
		self, ctx: discord.ApplicationContext, splash_text: str
	) -> None:
		"""Submit a splash to fractalthorns."""
		self.logger.info("Submit splash command used")

		user_name = ctx.author.global_name
		user_id = str(ctx.author.id)

		splash = ftd.Splash(splash_text, None)

		try:
			try:
				await fractalthorns_api.post_submit_discord_splash(
					frg.session, splash_text, user_name, user_id
				)

			except* client_exc.ClientResponseError as exc:
				await ctx.respond(
					f"could not submit splash:\n{splash.format()}", ephemeral=True
				)

				max_loop = 1000

				while isinstance(exc, ExceptionGroup):
					max_loop -= 1
					if max_loop < 0:
						self.logger.warning(
							"Loop running for too long.", stack_info=True
						)
						break

					exc = exc.exceptions[0]

				if isinstance(exc, client_exc.ClientResponseError):
					if exc.status == HTTPTooManyRequests.status_code:
						retry_after = float(exc.headers["Retry-After"])
						time = dt.datetime.now(dt.UTC).timestamp()
						retry_time = ceil(time + retry_after)

						try:
							await ctx.send(
								f"you're sending splashes too quickly. try again <t:{retry_time}:R>"
							)
						except discord.errors.Forbidden:
							await ctx.respond(
								f"you're sending splashes too quickly. try again <t:{retry_time}:R>",
								ephemeral=True,
							)
					elif exc.status == HTTPUnauthorized.status_code:
						try:
							await ctx.send(
								"cannot submit a splash. bot is missing an api key"
							)
						except discord.errors.Forbidden:
							await ctx.respond(
								"cannot submit a splash. bot is missing an api key",
								ephemeral=True,
							)
					elif exc.status == HTTPForbidden.status_code:
						try:
							await ctx.send(
								"cannot submit a splash. bot has an invalid api key"
							)
						except discord.errors.Forbidden:
							await ctx.respond(
								"cannot submit a splash. bot has an invalid api key",
								ephemeral=True,
							)
					else:
						raise
				else:
					raise

			else:
				resend_splash = self.ResendSplashView()
				resend_message = await ctx.respond(
					f"splash submitted:\n{splash.format()}",
					view=resend_splash,
					ephemeral=True,
				)

				try:
					await ctx.send("splash submitted")
				except discord.errors.Forbidden:
					await ctx.respond("splash submitted", ephemeral=True)

				await self.resend_splash(ctx, splash, resend_splash, resend_message, 0)

		except* (TimeoutError, client_exc.ClientError) as exc:
			await ctx.respond(
				f"could not submit splash:\n{splash.format()}", ephemeral=True
			)
			await frg.standard_exception_handler(
				ctx,
				self.logger,
				exc,
				"Splash.submit_splash",
			)


def setup(bot: discord.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(Splash(bot))
