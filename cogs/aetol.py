# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Aetol cog for the bot."""

import csv
import logging
import logging.handlers
import operator
from dataclasses import dataclass
from pathlib import Path

import discord
import discord.utils
import rapidfuzz

import src.fractalrhomb_globals as frg


@dataclass
class AetolParticle:
	"""Data class for an Aetol particle."""

	name: str
	meaning: str
	as_verb: str
	as_noun: str
	notes: str
	category: set[str]

	@staticmethod
	def from_list(obj: list) -> "AetolParticle":
		"""Create an AetolParticle from a list.

		Parameter must be a list with 6 strings:
		name, meaning, as_verb, as_noun, notes, category.
		Category may be a set of strings.
		"""
		name, meaning, as_verb, as_noun, notes, category = obj

		if isinstance(category, str):
			category = {category.strip()}

		return AetolParticle(
			name.strip(),
			meaning.strip(),
			as_verb.strip(),
			as_noun.strip(),
			notes.strip(),
			category,
		)

	def format(self) -> str:
		"""Return a discord formatted string."""
		return f"**{self.name}**: [{self.meaning}]\nnoun: {self.as_noun}\nverb: {self.as_verb}\n{f"_{self.notes}_\n" if self.notes else ""}[{", ".join(self.category)}]"

	def __eq__(self, other: "AetolParticle") -> bool:
		"""Return True if the particles match (ignoring category)."""
		if not isinstance(other, AetolParticle):
			return False

		return (
			self.name == other.name
			and self.meaning == other.meaning
			and self.as_verb == other.as_verb
			and self.as_noun == other.as_noun
			and self.notes == other.notes
		)

	def __hash__(self) -> int:
		"""Return a hash for this object."""
		return hash((self.name, self.meaning, self.as_verb, self.as_noun, self.notes))


@dataclass
class AetolWord:
	"""Data class for an Aetol word."""

	name: str
	meaning: str
	as_verb: str
	as_noun: str
	formation: str
	category: set[str]

	@staticmethod
	def from_list(obj: list) -> "AetolWord":
		"""Create an AetolWord from a list.

		Parameter must be a list with 6 strings:
		name, meaning, as_verb, as_noun, formation, category.
		Category may be a set of strings.
		"""
		name, meaning, as_verb, as_noun, formation, category = obj

		if isinstance(category, str):
			category = {category.strip()}

		return AetolWord(
			name.strip(),
			meaning.strip(),
			as_verb.strip(),
			as_noun.strip(),
			formation.strip(),
			category,
		)

	def format(self) -> str:
		"""Return a discord formatted string."""
		return f"**{self.name}**: [{self.meaning}]\nnoun: {self.as_noun}\nverb: {self.as_verb}\n_{self.formation}_\n[{", ".join(self.category)}]"

	def __eq__(self, other: "AetolWord") -> bool:
		"""Return True if the words match (ignoring category)."""
		if not isinstance(other, AetolWord):
			return False

		return (
			self.name == other.name
			and self.meaning == other.meaning
			and self.as_verb == other.as_verb
			and self.as_noun == other.as_noun
			and self.formation == other.formation
		)

	def __hash__(self) -> int:
		"""Return a hash for this object."""
		return hash(
			(self.name, self.meaning, self.as_verb, self.as_noun, self.formation)
		)


@dataclass
class AetolIdiom:
	"""Data class for an Aetol idiom."""

	name: str
	meaning: str

	@staticmethod
	def from_list(obj: list) -> "AetolIdiom":
		"""Create an AetolIdiom from a list.

		Parameter must be a list with 2 strings:
		name, meaning.
		"""
		name, meaning = obj

		return AetolIdiom(name.strip(), meaning.strip())

	def format(self) -> str:
		"""Return a discord formatted string."""
		return f"**{self.name}** - {self.meaning}"


class Aetol(discord.Cog):
	"""Class defining the Aetol cog."""

	def __init__(self, bot: discord.Bot) -> "Aetol":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("fractalrhomb.cogs.aetol")

		self.particles: list[AetolParticle] = []
		self.words: list[AetolWord] = []
		self.idioms: list[AetolIdiom] = []

		self.load_dictionaries()

	def load_dictionaries(self) -> None:
		"""Load Aetol dictionaries."""
		self.__load_particles()
		self.__load_words()
		self.__load_idioms()

		if len(self.particles) + len(self.words) + len(self.idioms) > 0:
			self.logger.info("Dictionaries loaded.")
			self.dictionaries_loaded = True
		else:
			self.logger.error("Could not load any dictionaries!")
			self.dictionaries_loaded = False

	def __load_particles(self) -> None:
		self.logger.info("Loading particles...")
		if Path("aetol/particle_dictionary.tsv").exists():
			with Path("aetol/particle_dictionary.tsv").open(
				encoding="utf-8"
			) as tsvfile:
				dialect = csv.Sniffer().sniff(tsvfile.read(1024), "\t")
				tsvfile.seek(0)
				reader = csv.reader(tsvfile, dialect)

				header = next(reader)
				name = header.index("name")
				meaning = header.index("meaning")
				as_verb = header.index("as verb")
				as_noun = header.index("as noun")
				notes = header.index("notes")
				category = header.index("category")

				for row in reader:
					modified_row = [
						row[name],
						row[meaning],
						row[as_verb],
						row[as_noun],
						row[notes],
						row[category],
					]
					particle = AetolParticle.from_list(modified_row)
					if not particle.name or not particle.meaning:
						continue
					if particle in self.particles:
						other = self.particles[self.particles.index(particle)]
						other.category.update(particle.category)
					else:
						self.particles.append(particle)
			self.logger.info("Particles loaded.")
		else:
			self.logger.warning('"aetol/particle_dictionary.tsv" was not found!')

	def __load_words(self) -> None:
		self.logger.info("Loading words...")
		if Path("aetol/word_dictionary.tsv").exists():
			with Path("aetol/word_dictionary.tsv").open(encoding="utf-8") as tsvfile:
				dialect = csv.Sniffer().sniff(tsvfile.read(1024), "\t")
				tsvfile.seek(0)
				reader = csv.reader(tsvfile, dialect)

				header = next(reader)
				name = header.index("name")
				meaning = header.index("meaning")
				as_verb = header.index("as verb")
				as_noun = header.index("as noun")
				formation = header.index("formation")
				category = header.index("category")

				for row in reader:
					modified_row = [
						row[name],
						row[meaning],
						row[as_verb],
						row[as_noun],
						row[formation],
						row[category],
					]
					word = AetolWord.from_list(modified_row)
					if not word.name or not word.meaning:
						continue
					if word in self.words:
						other = self.words[self.words.index(word)]
						other.category.update(word.category)
					else:
						self.words.append(word)
			self.logger.info("Words loaded.")
		else:
			self.logger.warning('"aetol/word_dictionary.tsv" was not found!')

	def __load_idioms(self) -> None:
		self.logger.info("Loading idioms...")
		if Path("aetol/idiom_dictionary.tsv").exists():
			with Path("aetol/idiom_dictionary.tsv").open(encoding="utf-8") as tsvfile:
				dialect = csv.Sniffer().sniff(tsvfile.read(1024), "\t")
				tsvfile.seek(0)
				reader = csv.reader(tsvfile, dialect)

				header = next(reader)
				name = header.index("idiom")
				meaning = header.index("meaning")

				for row in reader:
					modified_row = [row[name], row[meaning]]
					idiom = AetolIdiom.from_list(modified_row)
					if not idiom.name or not idiom.meaning:
						continue
					self.idioms.append(idiom)
			self.logger.info("Idioms loaded.")
		else:
			self.logger.warning('"aetol/idiom_dictionary.tsv" was not found!')

	aetol_group = discord.SlashCommandGroup("aetol", "Various Aetol commands")

	@aetol_group.command(name="info")
	async def show_info(self, ctx: discord.ApplicationContext) -> None:
		"""Show info about Aetol."""
		self.logger.info("Show info command used.")

		if not await frg.bot_channel_warning(ctx):
			return

		response = (
			"**aetol resources**\n"
			"[index](<https://web.archive.org/web/20231015202450/https://doughbyte.com/aut/aetol/>)\n"
			"[learn it](<https://web.archive.org/web/20231015202503/https://doughbyte.com/aut/aetol/learn/>)\n"
			"[dictionary](<https://web.archive.org/web/20231015202502/https://doughbyte.com/aut/aetol/dictionary/>)\n"
			"[sample collection](<https://web.archive.org/web/20231015202507/https://doughbyte.com/aut/aetol/samples/>)\n"
			"[handbook](<https://web.archive.org/web/20231015202505/https://doughbyte.com/aut/aetol/handbook/>)\n"
			"_disclaimer: some information may be missing, inaccurate, or incomplete. this is unlikely to change in the near future. do not bother pierce/beryl about this._\n"
		)

		await frg.send_message(ctx, response, "\n")

	@aetol_group.command(name="alphabet")
	async def show_alphabet(self, ctx: discord.ApplicationContext) -> None:
		"""Show the Aetol alphabet."""
		self.logger.info("Show alphabet command used.")

		if not await frg.bot_channel_warning(ctx):
			return

		response = (
			"vowels:\nAa - [ɑ]; Ââ (aj) - [aɪ]; Ææ (ae) - [eɪ]; Ee - [ɛ]; Ii - [ɪ]; Uu - [ə]; Yy - [i]\n\n"  # noqa: RUF001
			"consonants:\nLl - [l]; Kk - [k]; Gg - [g]; Tt - [t]; Dd - [d]; Nn - [n]; Ss - [s]; Šš (sh) - [ʃ]; Žž (zs) - [ʒ]; Ţţ (ts) - [t͡s]; Jj - [j]; Ĺĺ (lj) - [ʎ]; Łł (lh) - [ɮ] / [ɬ]; Xx - [χ]"
		)

		await frg.send_message(ctx, response, "\n")

	@aetol_group.command(name="idioms")
	async def show_idioms(self, ctx: discord.ApplicationContext) -> None:
		"""Show a list of Aetol idioms."""
		self.logger.info("Show idioms command used.")

		if not await frg.bot_channel_warning(ctx):
			return

		if len(self.idioms) > 0:
			response = "\n".join([i.format() for i in self.idioms])
		else:
			response = "no idioms were loaded"

		await frg.send_message(ctx, response, "\n")

	@aetol_group.command(name="search")
	@discord.option(
		"term",
		str,
		description="Search for this term",
	)
	@discord.option(
		"score_cutoff",
		float,
		description="How closely the term needs to match for a result to be shown (0.0 - 100.0) (default: 80.0)",
	)
	@discord.option("limit", int, description="How many results to show (default: 3)")
	@discord.option(
		"start",
		int,
		description="Where to start (negative numbers start from the end) (default: 1)",
		parameter_name="start_index",
	)
	@discord.option(
		"convert",
		bool,
		description="Auto convert certain letter combinations to Aetol letters (i.e ae -> æ) (default: Yes)",
	)
	async def search_word(
		self,
		ctx: discord.ApplicationContext,
		term: str,
		score_cutoff: float = 80.0,
		limit: int = 3,
		start_index: int = 1,
		*,
		convert: bool = True,
	) -> None:
		"""Search for Aetol words using fuzzy search."""
		self.logger.info(
			"Search word command used (term=%s, score_cutoff=%s, limit=%s, start_index=%s, convert=%s).",
			term,
			score_cutoff,
			limit,
			start_index,
			convert,
		)

		if not await frg.bot_channel_warning(ctx):
			return

		msg = f"searching aetol for `{term}`"
		await frg.send_message(ctx, msg)

		if start_index > 0:
			start_index -= 1

		term = term.lower()
		original_term = term

		if convert:
			replace_dictionary = {
				"aj": "â",
				"ae": "æ",
				"sh": "š",
				"zs": "ž",
				"ts": "ţ",
				"lj": "ĺ",
				"lh": "ł",
			}

			for i, j in replace_dictionary.items():
				term = term.replace(i, j)

		aetol_words = {i.name.lower() for i in self.particles}
		aetol_words.update({i.name.lower() for i in self.words})

		aetol_meanings = {i.meaning.lower() for i in self.particles}
		aetol_meanings.update({i.meaning.lower() for i in self.words})

		aetol_nouns = {i.as_noun.lower() for i in self.particles if i.as_noun}
		aetol_nouns.update({i.as_noun.lower() for i in self.words if i.as_noun})

		aetol_verbs = {i.as_verb.lower() for i in self.particles if i.as_verb}
		aetol_verbs.update({i.as_verb.lower() for i in self.words if i.as_verb})

		matches = []
		matches.extend(
			rapidfuzz.process.extract_iter(
				term,
				aetol_words,
				scorer=rapidfuzz.fuzz.ratio,
				score_cutoff=score_cutoff,
			)
		)
		matches.extend(
			rapidfuzz.process.extract_iter(
				original_term,
				aetol_meanings,
				scorer=rapidfuzz.fuzz.WRatio,
				score_cutoff=score_cutoff,
			)
		)
		matches.extend(
			rapidfuzz.process.extract_iter(
				original_term,
				aetol_nouns,
				scorer=rapidfuzz.fuzz.WRatio,
				score_cutoff=score_cutoff,
			)
		)
		matches.extend(
			rapidfuzz.process.extract_iter(
				original_term,
				aetol_verbs,
				scorer=rapidfuzz.fuzz.WRatio,
				score_cutoff=score_cutoff,
			)
		)

		matches.sort(key=operator.itemgetter(1), reverse=True)

		if len(matches) < 1:
			response = "nothing was found"
			await frg.send_message(ctx, response, ping_user=False)
			return

		matching_words = []
		for i in matches:
			for j in self.particles:
				if j not in {k[0] for k in matching_words} and (
					i[0] == j.name
					or i[0] == j.meaning
					or i[0] == j.as_noun
					or i[0] == j.as_verb
				):
					matching_words.append((j, i[1]))
			for j in self.words:
				if j not in {k[0] for k in matching_words} and (
					i[0] == j.name
					or i[0] == j.meaning
					or i[0] == j.as_noun
					or i[0] == j.as_verb
				):
					matching_words.append((j, i[1]))

		total_items = len(matching_words)
		matching_words = matching_words[start_index :: frg.sign(start_index)]

		if limit >= 0:
			matching_words = matching_words[:limit]

		too_many = frg.truncated_message(
			total_items, len(matching_words), limit, start_index
		)

		response = [f"({i[1]:.1f}) {i[0].format()}" for i in matching_words]

		if too_many is not None:
			response.append(too_many)

		responses = frg.split_message(response, "\n\n")

		if not await frg.message_length_warning(ctx, responses, 500):
			response_text = "the search was cancelled"
			await frg.send_message(ctx, response_text, ping_user=False)
			return

		for i in responses:
			if not await frg.send_message(ctx, i.strip(), ping_user=False):
				break


def setup(bot: discord.Bot) -> None:
	"""Set up the cog."""
	bot.add_cog(Aetol(bot))
