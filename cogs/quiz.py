# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Quiz cog for the bot."""

import asyncio
import contextlib
import json
import logging
from copy import deepcopy

import anyio
import discord

import src.quiz as qb
from src.fractalrhomb_globals import value_or_default


class LoadedQuizzes:
	"""Class for storing loaded quizzes."""

	quizzes: dict[str, qb.Quiz]

	def __init__(self) -> "LoadedQuizzes":
		"""Initialize the class."""
		self.quizzes = {}


_loaded_quizzes: LoadedQuizzes = LoadedQuizzes()


class QuizCog(discord.Cog):
	"""Class defining the quiz cog."""

	class QuizView(discord.ui.View):
		"""View for quizzes."""

		logger: logging.Logger
		quiz: qb.Quiz
		current_question: int
		answered_questions: dict[int, int | None]
		answered_required_questions: dict[int, bool]

		selection: discord.ui.Select
		prev_button: discord.ui.Button
		prev_button_disabled: discord.ui.Button
		next_button: discord.ui.Button
		next_button_disabled: discord.ui.Button
		clear_button: discord.ui.Button
		clear_button_disabled: discord.ui.Button
		submit_button: discord.ui.Button
		submit_button_disabled: discord.ui.Button

		def __init__(
			self,
			logger: logging.Logger,
			quiz: qb.Quiz,
			quiz_message: discord.Interaction | discord.WebhookMessage,
		) -> "QuizCog.QuizView":
			"""Initialize the quiz view, including copying the quiz and setting up buttons."""
			self.logger = logger
			self.quiz = deepcopy(quiz)
			super().__init__(timeout=1800.0, disable_on_timeout=True)

			self.current_question = 0
			self.answered_questions = dict.fromkeys(range(len(self.quiz.questions)))
			self.answered_required_questions = {
				i: False for i, j in enumerate(self.quiz.questions) if j.required
			}

			self.logger.debug("Loading quiz %s", self.quiz.name)
			self.logger.debug(
				"%s questions, %s required",
				len(self.answered_questions),
				len(self.answered_required_questions),
			)

			prev_text = value_or_default(self.quiz.prev_text, "Previous")
			next_text = value_or_default(self.quiz.next_text, "Next")
			clear_text = value_or_default(self.quiz.clear_text, "Clear Answer")
			submit_text = value_or_default(self.quiz.submit_text, "Submit")

			self.prev_button = discord.ui.Button(label=prev_text, emoji="◀️", row=1)
			self.prev_button_disabled = discord.ui.Button(
				label=prev_text, emoji="◀️", row=1, disabled=True
			)
			self.next_button = discord.ui.Button(label=next_text, emoji="▶️", row=1)
			self.next_button_disabled = discord.ui.Button(
				label=next_text, emoji="▶️", row=1, disabled=True
			)
			self.clear_button = discord.ui.Button(label=clear_text, row=1)
			self.clear_button_disabled = discord.ui.Button(
				label=clear_text, row=1, disabled=True
			)
			self.submit_button = discord.ui.Button(
				style=discord.ButtonStyle.primary, label=submit_text, row=2
			)
			self.submit_button_disabled = discord.ui.Button(
				style=discord.ButtonStyle.primary,
				label=submit_text,
				row=2,
				disabled=True,
			)

			self.prev_button.callback = self.previous_question
			self.prev_button_disabled.callback = self.previous_question
			self.next_button.callback = self.next_question
			self.next_button_disabled.callback = self.next_question
			self.clear_button.callback = self.clear_answer
			self.clear_button_disabled.callback = self.clear_answer
			self.submit_button.callback = self.submit_quiz
			self.submit_button_disabled.callback = self.submit_quiz

			asyncio.get_event_loop().create_task(self.refresh_view(quiz_message))

		async def refresh_view(
			self, interaction: discord.Interaction | discord.WebhookMessage
		) -> None:
			"""Refresh the view to add new answers."""
			self.logger.debug("Refreshing quiz view!")

			self.clear_items()

			selection_options = []
			for answer_num, answer in enumerate(
				self.quiz.get_question_options(self.current_question)
			):
				selection_options.append(
					discord.SelectOption(
						label=f"{answer_num + 1}.",
						value=str(answer_num),
						description=answer.text,
					)
				)
			self.selection = discord.ui.Select(row=0, options=selection_options)
			self.selection.callback = self.make_selection

			self.add_item(self.selection)
			self.add_item(self.prev_button)
			self.add_item(self.next_button)

			if (
				self.current_question in self.answered_required_questions
				or self.answered_questions[self.current_question] is None
			):
				self.logger.debug(
					"No clearing the answer! %r, %r",
					self.answered_required_questions,
					self.answered_questions,
				)
				self.add_item(self.clear_button_disabled)
			else:
				self.logger.debug(
					"Can clear the answer! %r, %r",
					self.answered_required_questions,
					self.answered_questions,
				)
				self.add_item(self.clear_button)

			if not all(self.answered_required_questions.values()):
				self.logger.debug(
					"Can't submit the quiz! %r", self.answered_required_questions
				)
				self.add_item(self.submit_button_disabled)
			else:
				self.logger.debug(
					"Can submit the quiz! %r", self.answered_required_questions
				)
				self.add_item(self.submit_button)

			question = self.quiz.get_question(self.current_question)
			response_text = question.format(self.current_question + 1)
			selected_answer = self.answered_questions[self.current_question]
			if selected_answer is not None:
				response_text += f"\n\n(selected answer: {selected_answer + 1}. {question.options[selected_answer].format()})"
			await interaction.edit(content=response_text, view=self)

		async def make_selection(self, interaction: discord.Interaction) -> None:
			"""Select an answer on the current question."""
			self.logger.debug("Made selection, selection object: %r", self.selection)

			answer = int(self.selection.values[0])
			self.quiz.pick_answer(self.current_question, answer)
			self.answered_questions[self.current_question] = answer

			if self.current_question in self.answered_required_questions:
				self.answered_required_questions[self.current_question] = True

			await self.refresh_view(interaction)

		async def next_question(self, interaction: discord.Interaction) -> None:
			"""Go to the next question."""
			self.current_question = (
				self.current_question + 1
			) % self.quiz.get_num_questions()
			self.logger.debug("Next question! %s", self.current_question)

			await self.refresh_view(interaction)

		async def previous_question(self, interaction: discord.Interaction) -> None:
			"""Go to the previous question."""
			self.current_question = (
				self.current_question - 1
			) % self.quiz.get_num_questions()
			self.logger.debug("Previous question! %s", self.current_question)

			await self.refresh_view(interaction)

		async def clear_answer(self, interaction: discord.Interaction) -> None:
			"""Clear the answer on the current question."""
			self.logger.debug("Clearing answer! %s", self.current_question)

			self.quiz.clear_answer(self.current_question)
			self.answered_questions[self.current_question] = None

			if self.current_question in self.answered_required_questions:
				self.answered_required_questions[self.current_question] = False

			await self.refresh_view(interaction)

		async def submit_quiz(self, interaction: discord.Interaction) -> None:
			"""Submit the quiz."""
			self.logger.debug("Trying to submit quiz")
			quiz_result = self.quiz.finish()
			self.logger.debug("Got results! %r", quiz_result)
			result_message, result_image = self.quiz.format_result(quiz_result)

			self.children[-1].style = discord.ButtonStyle.success
			self.disable_all_items()
			await interaction.edit(view=self)

			if result_image is not None:
				await interaction.respond(
					result_message, ephemeral=True, file=discord.File(result_image)
				)
			else:
				await interaction.respond(result_message, ephemeral=True)

	class StartQuizView(discord.ui.View):
		"""View for starting a quiz."""

		def __init__(self, logger: logging.Logger, quiz: qb.Quiz) -> "QuizCog.QuizView":
			"""Initialize the view for starting a quiz."""
			self.logger = logger
			self.quiz = quiz
			super().__init__(disable_on_timeout=True)

		@discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
		async def start_button_callback(
			self, _button: discord.ui.Button, interaction: discord.Interaction
		) -> None:
			"""Start the quiz."""
			quiz_message = await interaction.respond(
				"initializing quiz...", ephemeral=True
			)
			QuizCog.QuizView(self.logger, self.quiz, quiz_message)

	def __init__(self, bot: discord.Bot) -> "QuizCog":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("fractalrhomb.cogs.quiz")

		asyncio.get_event_loop().create_task(self.load_quizzes())

	async def load_quizzes(self) -> int:
		"""Load quizzes located in the 'quiz' subdirectory.

		Returns the number of quizzes successfully loaded.
		"""
		quizzes: list[qb.Quiz] = []

		async for dirpath, _foldernames, filenames in anyio.Path("quiz").walk(
			follow_symlinks=True
		):
			for filename in filenames:
				file_path = dirpath.joinpath(filename)
				quiz_contents = None
				async with await file_path.open(encoding="utf-8") as file:
					with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
						quiz_contents = json.loads(await file.read())

				if quiz_contents is None:
					continue

				image_base = file_path.with_suffix("")
				quiz = qb.Quiz.build_quiz(quiz_contents, image_base=image_base)

				if quiz is not None:
					quizzes.append(quiz)

		_loaded_quizzes.quizzes = {i.name: i for i in quizzes}

		num_quizzes = len(_loaded_quizzes.quizzes)
		self.logger.info(
			"Loaded %i quiz%s", num_quizzes, "" if num_quizzes == 1 else "zes"
		)

		return num_quizzes

	quiz_group: discord.SlashCommandGroup = discord.SlashCommandGroup(
		"quiz", "Quiz commands"
	)

	@quiz_group.command(name="reload", contexts={discord.InteractionContextType.bot_dm})
	async def reload_quizzes(self, ctx: discord.ApplicationContext) -> None:
		"""Reload all quizzes."""
		self.logger.info("Reload quizzes command used")

		await ctx.defer()

		num_loaded = await self.load_quizzes()

		msg = f"Loaded {num_loaded} quiz{'' if num_loaded == 1 else 'zes'}"
		await ctx.respond(msg)

	@staticmethod
	async def available_quizzes(_: discord.AutocompleteContext) -> list[str]:
		"""Give available quiz names."""
		return list(_loaded_quizzes.quizzes.keys())

	@quiz_group.command(name="start")
	@discord.option(
		"name",
		str,
		description="The name of the quiz",
		autocomplete=discord.utils.basic_autocomplete(available_quizzes),
	)
	async def start_quiz(self, ctx: discord.ApplicationContext, name: str) -> None:
		"""Start a quiz."""
		self.logger.info("Start quiz command used")

		await ctx.defer(ephemeral=True)

		quiz = _loaded_quizzes.quizzes.get(name)

		if quiz is None:
			await ctx.respond("Not a valid quiz")
			return

		msg = quiz.format_title()
		view = self.StartQuizView(self.logger, quiz)

		await ctx.respond(msg, view=view, ephemeral=True)


def setup(bot: discord.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(QuizCog(bot))
