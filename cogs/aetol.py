# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Aetol cog for the bot."""

import csv
from dataclasses import dataclass, astuple
import asyncio
import logging
import logging.handlers
from pathlib import Path

import discord
import discord.utils
import rapidfuzz


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

		return AetolParticle(name.strip(), meaning.strip(), as_verb.strip(), as_noun.strip(), notes.strip(), category)

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

	__hash__ = None


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

		return AetolWord(name.strip(), meaning.strip(), as_verb.strip(), as_noun.strip(), formation.strip(), category)

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

	__hash__ = None


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


class Aetol(discord.Cog):
	"""Class defining the aetol cog."""

	def __init__(self, bot: discord.Bot) -> "Aetol":
		"""Initialize the cog."""
		self.bot: discord.Bot = bot
		self.logger = logging.getLogger("discord.cogs.aetol")

		self.particles: list[AetolParticle] = []
		self.words: list[AetolWord] = []
		self.idioms: list[AetolIdiom] = []

	def load_dictionaries(self) -> None:
		"""Load Aetol dictionaries."""
		with Path("aetol/particle_dictionary.tsv").open(encoding="utf-8") as tsvfile:
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
				modified_row = [row[name], row[meaning], row[as_verb], row[as_noun], row[notes], row[category]]
				particle = AetolParticle.from_list(modified_row)
				if particle in self.particles:
					other = self.particles[self.particles.index(particle)]
					other.category.update(particle.category)
				else:
					self.particles.append(particle)

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
				modified_row = [row[name], row[meaning], row[as_verb], row[as_noun], row[formation], row[category]]
				word = AetolWord.from_list(modified_row)
				if word in self.words:
					other = self.words[self.words.index(word)]
					other.category.update(word.category)
				else:
					self.words.append(word)

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
				self.idioms.append(idiom)
