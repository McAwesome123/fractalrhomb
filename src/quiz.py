# Copyright (C) 2024 McAwesome (https://github.com/McAwesome123)
# This script is licensed under the GNU Affero General Public License version 3 or later.
# For more information, view the LICENSE file provided with this project
# or visit: https://www.gnu.org/licenses/agpl-3.0.en.html

# fractalthorns is a website created by Pierce Smith (https://github.com/pierce-smith1).
# View it here: https://fractalthorns.com

"""Quiz parser that can build a quiz from json."""

import argparse
import contextlib
import enum
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

from PIL import Image


class MissingRequiredQuestionError(Exception):
	"""Required question is not answered."""


@dataclass
class Requirement:
	"""A requirement for a result."""

	class Type(Enum):
		"""Types of requirements."""

		ALWAYS_YES = enum.auto()
		ALWAYS_NO = enum.auto()

		VARIABLES = enum.auto()

		COUNT = enum.auto()

		NOT = enum.auto()
		AND = enum.auto()
		NAND = enum.auto()
		OR = enum.auto()
		NOR = enum.auto()
		XOR = enum.auto()
		XNOR = enum.auto()

	class Comparison(Enum):
		"""Types of comparisons."""

		EQUAL = enum.auto()
		NOT_EQUAL = enum.auto()
		GREATER = enum.auto()
		GREATER_EQUAL = enum.auto()
		LESS = enum.auto()
		LESS_EQUAL = enum.auto()

	__type: Type
	__comparison: Comparison | None

	__variable_left: str | float | None
	__variable_right: str | float | None

	__requirements: list["Requirement"] | None
	__count: int | None

	type RequirementType = dict[
		Literal[
			"type",
			"comparison",
			"variable_left",
			"variable_right",
			"requirements",
			"count",
		],
		str | float | RequirementType | int,
	]

	def __init__(
		self,
		type_: str | Type,
		*,
		comparison: str | Comparison | None = None,
		variable_left: str | float | None = None,
		variable_right: str | float | None = None,
		requirements: list["Requirement"] | None = None,
		count: int | None = None,
	) -> "Requirement":
		"""Initialize a requirement."""
		if isinstance(type_, self.Type):
			self.__type = type_
		else:
			self.__type = self.Type[type_]

		if isinstance(comparison, self.Comparison):
			self.__comparison = comparison
		elif comparison is None:
			self.__comparison = None
		else:
			self.__comparison = self.Comparison[comparison]

		self.__variable_left = variable_left
		self.__variable_right = variable_right
		self.__requirements = requirements
		self.__count = count

		if self.__type is self.Type.VARIABLES and (
			self.__comparison is None
			or self.__variable_left is None
			or self.__variable_right is None
		):
			msg = f"Missing variable_left and variable_right for requirement type {self.__type.name}"
			raise ValueError(msg)

		if self.__type is self.Type.COUNT and (
			self.__comparison is None
			or self.__requirements is None
			or self.__count is None
		):
			msg = f"Missing comparison, requirements, and count for requirement type {self.__type.name}"
			raise ValueError(msg)

		if (
			self.__type is self.Type.NOT
			or self.__type is self.Type.AND
			or self.__type is self.Type.NAND
			or self.__type is self.Type.OR
			or self.__type is self.Type.NOR
			or self.__type is self.Type.XOR
			or self.__type is self.Type.XNOR
		) and self.__requirements is None:
			msg = f"Missing requirements for requirement type {self.__type.name}"
			raise ValueError(msg)

	@staticmethod
	def build_requirement(
		input_dict: RequirementType,
		logger: logging.Logger,
		context: str,
	) -> tuple["Requirement | None", int, int]:
		"""Build a requirement from a dictionary.

		Returns a tuple containing:
		The requirement (if successful) or None (if one or more errors occurred),
		The number of errors,
		The number of warnings.
		"""
		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = f"Requirement format is invalid ({context})"
			logger.error(msg)
			num_errors += 1
			return (None, num_errors, num_warnings)

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		type_ = input_dict.get("type")
		comparison = input_dict.get("comparison")
		variable_left = input_dict.get("variable_left")
		variable_right = input_dict.get("variable_right")
		requirements_raw = input_dict.get("requirements")
		count = input_dict.get("count")

		if type_ is None:
			msg = f"Missing requirement type ({context})"
			logger.error(msg)
			num_errors += 1
		else:
			try:
				type_ = Requirement.Type[type_.upper()]
			except (KeyError, AttributeError):
				msg = f"Unknown requirement type {type_} (expected: {', '.join(i.name for i in Requirement.Type)}) ({context})"
				logger.error(  # noqa: TRY400 # (shut the fuck up)
					msg,
				)
				num_errors += 1

		if type_ in {Requirement.Type.VARIABLES, Requirement.Type.COUNT}:
			if comparison is None:
				msg = (
					f"Missing comparison type for requirement type {type_} ({context})"
				)
				logger.error(msg)
				num_errors += 1
			else:
				try:
					comparison = Requirement.Comparison[comparison.upper()]
				except (KeyError, AttributeError):
					msg = f"Unknown comparison type {comparison} (expected: {', '.join(i.name for i in Requirement.Comparison)}) ({context})"
					logger.error(  # noqa: TRY400 # (shut the fuck up)
						msg,
					)
					num_errors += 1
		elif comparison is not None:
			msg = f"Comparison type is unused with requirement type {type_} ({context})"
			logger.warning(msg)
			num_warnings += 1
			comparison = None

		if type_ is Requirement.Type.VARIABLES:
			if variable_left is None:
				msg = f"Missing left variable with requirement type {type_} ({context})"
				logger.error(msg)
				num_errors += 1
			elif not isinstance(variable_left, (str, int, float)):
				try:
					variable_left = float(variable_left)
					msg = f"Left variable is not a number or a string ({context})"
					logger.warning(msg)
					num_warnings += 1
				except ValueError:
					msg = f"Could not convert left variable to a number ({context})"
					logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
					num_errors += 1
			if variable_right is None:
				msg = (
					f"Missing right variable with requirement type {type_} ({context})"
				)
				logger.error(msg)
				num_errors += 1
			elif not isinstance(variable_right, (str, int, float)):
				try:
					variable_right = float(variable_right)
					msg = f"Right variable is not a number or a string ({context})"
					logger.warning(msg)
					num_warnings += 1
				except ValueError:
					msg = f"Could not convert right variable to a number ({context})"
					logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
					num_errors += 1
		else:
			if variable_left is not None:
				msg = (
					f"Left variable is unused with requirement type {type_} ({context})"
				)
				logger.warning(msg)
				num_warnings += 1
				variable_left = None
			if variable_right is not None:
				msg = f"Right variable is unused with requirement type {type_} ({context})"
				logger.warning(msg)
				num_warnings += 1
				variable_right = None

		requirements = None
		if type_ not in {
			Requirement.Type.ALWAYS_YES,
			Requirement.Type.ALWAYS_NO,
			Requirement.Type.VARIABLES,
		}:
			requirements = []
			if requirements_raw is None:
				msg = f"Missing requirements with requirement type {type_} ({context})"
				logger.error(msg)
				num_errors += 1
			elif not isinstance(requirements_raw, (list, tuple)):
				msg = f"Requirement requirements is not a list ({context})"
				logger.error(msg)
				num_errors += 1
			else:
				for requirement_num, requirement_raw in enumerate(
					requirements_raw, start=1
				):
					requirement = Requirement.build_requirement(
						requirement_raw,
						logger,
						context + f", requirement {requirement_num}",
					)
					if requirement[0] is not None:
						requirements.append(requirement[0])
					num_errors += requirement[1]
					num_warnings += requirement[2]

				if len(requirements) < 1:
					msg = f"No requirements with requirement type {type_} ({context})"
					logger.warning(msg)
					num_warnings += 1
				elif type_ is Requirement.Type.NOT and len(requirements > 1):
					msg = f"More than one requirement with requirement type {type_} ({context})"
					logger.warning(msg)
					num_warnings += 1
				elif type_ is not Requirement.Type.NOT and len(requirements == 1):
					msg = f"Only one requirement with requirement type {type_} ({context})"
					logger.warning(msg)
					num_warnings += 1
		elif requirements_raw is not None:
			msg = f"Requirements is unused with requirement type {type_} ({context})"
			logger.warning(msg)
			num_warnings += 1

		if type_ is Requirement.Type.COUNT:
			if count is None:
				msg = f"Missing count with requirement type {type_} ({context})"
				logger.error(msg)
				num_errors += 1
			elif not isinstance(count, int):
				try:
					count = int(count)
					msg = f"Count is not an integer ({context})"
					logger.warning(msg)
					num_warnings += 1
				except ValueError:
					msg = f"Could not convert count to an integer ({context})"
					logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
					num_errors += 1
		elif count is not None:
			msg = f"Count is unused with requirement type {type_} ({context})"
			logger.warning(msg)
			num_warnings += 1
			count = None

		for i in input_dict:
			if i not in {
				"type",
				"comparison",
				"variable_left",
				"variable_right",
				"requirements",
				"count",
			}:
				msg = f"Unknown requirement parameter '{i}' ({context})"
				logger.warning(msg)
				num_warnings += 1

		if num_errors > 0:
			return (None, num_errors, num_warnings)

		requirement = None
		try:
			requirement = Requirement(
				type_,
				comparison=comparison,
				variable_left=variable_left,
				variable_right=variable_right,
				requirements=requirements,
				count=count,
			)
		except Exception:
			msg = f"Could not create requirement ({context})"
			logger.exception(msg)
			num_errors += 1
		else:
			msg = f"Created requirement {requirement!r} ({context})"
			logger.debug(msg)

		return (requirement, num_errors, num_warnings)

	def is_met(self, variables: dict[str, float]) -> bool:
		"""Check if the requirement is met."""
		match self.__type:
			case self.Type.ALWAYS_YES:
				return True
			case self.Type.ALWAYS_NO:
				return False

			case self.Type.VARIABLES:
				variable_left = self.__variable_left
				variable_right = self.__variable_right
				if isinstance(variable_left, str):
					variable_left = variables.get(variable_left, 0)
				if isinstance(variable_right, str):
					variable_right = variables.get(variable_right, 0)

				match self.__comparison:
					case self.Comparison.EQUAL:
						return variable_left == variable_right
					case self.Comparison.NOT_EQUAL:
						return variable_left != variable_right
					case self.Comparison.GREATER:
						return variable_left > variable_right
					case self.Comparison.GREATER_EQUAL:
						return variable_left >= variable_right
					case self.Comparison.LESS:
						return variable_left < variable_right
					case self.Comparison.LESS_EQUAL:
						return variable_left <= variable_right

			case self.Type.COUNT:
				count_true = 0
				remaining = len(self.__requirements)

				for req in self.__requirements:
					remaining -= 1
					if req.is_met(variables):
						count_true += 1

					match self.__comparison:
						case self.Comparison.NOT_EQUAL:
							if count_true > self.__count:
								return True
						case self.Comparison.GREATER:
							if count_true > self.__count:
								return True
						case self.Comparison.GREATER_EQUAL:
							if count_true >= self.__count:
								return True
						case self.Comparison.LESS:
							if count_true + remaining < self.__count:
								return True
						case self.Comparison.LESS_EQUAL:
							if count_true + remaining <= self.__count:
								return True

				match self.__comparison:
					case self.Comparison.EQUAL:
						return count_true == self.__count
					case self.Comparison.NOT_EQUAL:
						return count_true != self.__count

				return False

			case self.Type.NOT:
				for req in self.__requirements:
					return not req.is_met(variables)

			case self.Type.AND:
				return all(req.is_met(variables) for req in self.__requirements)

			case self.Type.NAND:
				return not all(req.is_met(variables) for req in self.__requirements)

			case self.Type.OR:
				return any(req.is_met(variables) for req in self.__requirements)

			case self.Type.NOR:
				return not any(req.is_met(variables) for req in self.__requirements)

			case self.Type.XOR:
				count_true = 0
				for req in self.__requirements:
					if req.is_met(variables) is True:
						count_true += 1
				return count_true % 2 == 1

			case self.Type.XNOR:
				count_true = 0
				for req in self.__requirements:
					if req.is_met(variables) is True:
						count_true += 1
				return count_true % 2 == 0

		msg = f"Could not determine if a requirement is met: {self!r}"
		raise RuntimeError(msg)


@dataclass
class Effect:
	"""An effect that changes a variable."""

	class Type(Enum):
		"""An enum with effect operations."""

		ADD = enum.auto()
		SUB = enum.auto()
		MULT = enum.auto()
		DIV = enum.auto()
		EXP = enum.auto()
		ROOT = enum.auto()
		SET = enum.auto()

	__type: Type
	__variable: str
	__value: float | str
	__requirements: list[Requirement]

	priority: int

	type EffectType = dict[
		Literal["type", "variable", "value", "requirements", "priority"],
		str | float | list[Requirement.RequirementType] | int,
	]

	def __init__(
		self,
		type_: str | Type,
		variable: str,
		value: float,
		requirements: list[Requirement],
		priority: int = 0,
	) -> "Effect":
		"""Initialize an effect."""
		if isinstance(type_, self.Type):
			self.__type = type_
		else:
			self.__type = self.Type[str(type_).upper()]

		self.__variable = variable
		self.__value = value
		self.__requirements = requirements

		self.priority = priority

		if self.__value == 0:
			if self.__type is self.Type.DIV:
				msg = "Cannot divide by zero"
				raise ZeroDivisionError(msg)
			if self.__type is self.Type.ROOT:
				msg = "Cannot extract a 0th root"
				raise ZeroDivisionError(msg)

	@staticmethod
	def build_effect(
		input_dict: EffectType, logger: logging.Logger, context: str
	) -> tuple["Effect | None", int, int]:
		"""Build an effect from a dictionary.

		Returns a tuple containing:
		The effect (if successful) or None (if one or more errors occurred),
		The number of errors,
		The number of warnings.
		"""
		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = f"Effect format is invalid ({context})"
			logger.error(msg)
			num_errors += 1
			return (None, num_errors, num_warnings)

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		type_ = input_dict.get("type")
		variable = input_dict.get("variable")
		value = input_dict.get("value")
		requirements_raw = input_dict.get("requirements")
		priority = input_dict.get("priority")

		if type_ is None:
			type_ = Effect.Type.ADD
		else:
			try:
				type_ = Effect.Type[type_.upper()]
			except (KeyError, AttributeError):
				msg = f"Unknown effect type {type_} (expected: {', '.join(i.name for i in Effect.Type)}) ({context})"
				logger.error(  # noqa: TRY400 # (shut the fuck up)
					msg
				)
				num_errors += 1

		if variable is None:
			msg = f"Missing effect variable ({context})"
			logger.error(msg)
			num_errors += 1
		elif not isinstance(variable, str):
			try:
				variable = str(variable)
				msg = f"Effect variable is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert variable to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if value is None:
			msg = f"Missing effect value ({context})"
			logger.error(msg)
			num_errors += 1
		elif not isinstance(value, (int, float)):
			try:
				value = float(value)
				msg = f"Effect value is not a number ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert value to a number ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		requirements = []
		if requirements_raw is not None:
			if not isinstance(requirements_raw, (list, tuple)):
				msg = f"Effect requirements is not a list ({context})"
				logger.error(msg)
				num_errors += 1
			elif requirements_raw is not None:
				for requirement_num, requirement_raw in enumerate(
					requirements_raw, start=1
				):
					requirement = Requirement.build_requirement(
						requirement_raw,
						logger,
						context + f", requirement {requirement_num}",
					)
					if requirement[0] is not None:
						requirements.append(requirement[0])
					num_errors += requirement[1]
					num_warnings += requirement[2]

		if priority is not None and not isinstance(priority, int):
			try:
				priority = int(priority)
				msg = f"Effect priority is not an integer ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert priority to integer ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		for i in input_dict:
			if i not in {"type", "variable", "value", "requirements", "priority"}:
				msg = f"Unknown effect parameter '{i}' ({context})"
				logger.warning(msg)
				num_warnings += 1

		if num_errors > 0:
			return (None, num_errors, num_warnings)

		effect = None
		try:
			if priority is None:
				effect = Effect(type_, variable, value, requirements)
			else:
				effect = Effect(type_, variable, value, requirements, priority)
		except Exception:
			msg = f"Could not create effect ({context})"
			logger.exception(msg)
			num_errors += 1
		else:
			msg = f"Created effect {effect!r} ({context})"
			logger.debug(msg)

		return (effect, num_errors, num_warnings)

	def run(self, variables: dict[str, float]) -> None:
		"""Run the effect if the requirements are met."""
		for req in self.__requirements:
			if req.is_met(variables) is False:
				return

		if self.__variable not in variables:
			variables.update({self.__variable: 0})

		value = self.__value
		if isinstance(value, str):
			if value not in variables:
				variables.update({value: 0})

			value = variables[value]

		match self.__type:
			case self.Type.ADD:
				variables[self.__variable] += value
			case self.Type.SUB:
				variables[self.__variable] -= value
			case self.Type.MULT:
				variables[self.__variable] *= value
			case self.Type.DIV:
				variables[self.__variable] /= value
			case self.Type.EXP:
				variables[self.__variable] **= value
			case self.Type.ROOT:
				variables[self.__variable] **= 1 / value
			case self.Type.SET:
				variables[self.__variable] = value


@dataclass
class Option:
	"""An option for a question."""

	text: str
	effects: list[Effect]

	type OptionType = dict[Literal["text", "effects"], str | list[Effect.EffectType]]

	@staticmethod
	def build_option(
		input_dict: OptionType, logger: logging.Logger, context: str
	) -> tuple["Option | None", int, int]:
		"""Build an option from a dictionary.

		Returns a tuple containing:
		The option (if successful) or None (if one or more errors occurred),
		The number of errors,
		The number of warnings.
		"""
		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = f"Option format is invalid ({context})"
			logger.error(msg)
			num_errors += 1
			return (None, num_errors, num_warnings)

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		text = input_dict.get("text")
		effects_raw = input_dict.get("effects")

		if text is None:
			msg = f"Missing option text ({context})"
			logger.warning(msg)
			num_warnings += 1
			text = ""
		elif not isinstance(text, str):
			try:
				text = str(text)
				msg = f"Option text is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert option text to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		effects = []
		if effects_raw is not None:
			if not isinstance(effects_raw, (list, tuple)):
				msg = f"Option effects is not a list ({context})"
				logger.error(msg)
				num_errors += 1
			elif effects_raw is not None:
				for effect_num, effect_raw in enumerate(effects_raw, start=1):
					effect = Effect.build_effect(
						effect_raw,
						logger,
						context + f", effect {effect_num}",
					)
					if effect[0] is not None:
						effects.append(effect[0])
					num_errors += effect[1]
					num_warnings += effect[2]

		for i in input_dict:
			if i not in {"text", "effects"}:
				msg = f"Unknown option parameter '{i}' ({context})"
				logger.warning(msg)
				num_warnings += 1

		if num_errors > 0:
			return (None, num_errors, num_warnings)

		option = None
		try:
			option = Option(text, effects)
		except Exception:
			msg = f"Could not create option ({context})"
			logger.exception(msg)
			num_errors += 1
		else:
			msg = f"Created option {option!r} ({context})"
			logger.debug(msg)

		return (option, num_errors, num_warnings)

	def format(self, option_num: str | None = None) -> str:
		"""Format the option into text."""
		if option_num is None:
			return self.text

		return f"{option_num}) {self.text}"


@dataclass
class Question:
	"""A question in a quiz."""

	prompt: str
	options: list[Option]
	required: bool

	type QuestionType = dict[
		Literal["prompt", "options", "required"], str | list[Option.OptionType] | bool
	]

	def __init__(
		self, prompt: str, options: list[Option], *, required: bool = False
	) -> "Question":
		"""Initialize a question."""
		self.prompt = prompt
		self.options = options
		self.required = required

		if len(self.options) < 1:
			msg = "Question must have at least 1 option"
			raise ValueError(msg)

	@staticmethod
	def build_question(
		input_dict: QuestionType,
		logger: logging.Logger,
		context: str,
	) -> tuple["Question | None", int, int]:
		"""Build a question from a dictionary.

		Returns a tuple containing:
		The question (if successful) or None (if one or more errors occurred),
		The number of errors,
		The number of warnings.
		"""
		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = f"Question format is invalid ({context})"
			logger.error(msg)
			num_errors += 1
			return (None, num_errors, num_warnings)

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		prompt = input_dict.get("prompt")
		options_raw = input_dict.get("options")
		required = input_dict.get("required")

		if prompt is None:
			msg = f"Missing question prompt ({context})"
			logger.warning(msg)
			num_warnings += 1
			prompt = ""
		elif not isinstance(prompt, str):
			try:
				prompt = str(prompt)
				msg = f"Question prompt is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert question prompt to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		options = []
		if not isinstance(options_raw, (list, tuple)):
			msg = f"Question options is not a list ({context})"
			logger.error(msg)
			num_errors += 1
		elif options_raw is not None:
			for option_num, option_raw in enumerate(options_raw, start=1):
				option = Option.build_option(
					option_raw,
					logger,
					context + f", option {option_num}",
				)
				if option[0] is not None:
					options.append(option[0])
				num_errors += option[1]
				num_warnings += option[2]

		if len(options) < 1:
			msg = f"Missing question options ({context})"
			logger.error(msg)
			num_errors += 1

		if required is not None:
			if isinstance(required, str):
				if required.lower() in {"true", "yes", "yuh"}:
					required = True
				elif required.lower() in {"false", "no", "nuh"}:
					required = False
				else:
					msg = f"Unexpected value for question required ({context})"
					logger.error(msg)
					num_errors += 1
			elif not isinstance(required, bool):
				msg = f"Question required is not a boolean ({context})"
				logger.error(msg)
				num_errors += 1

		for i in input_dict:
			if i not in {"prompt", "options", "required"}:
				msg = f"Unknown question parameter '{i}' ({context})"
				logger.warning(msg)
				num_warnings += 1

		if num_errors > 0:
			return (None, num_errors, num_warnings)

		question = None
		try:
			if required is None:
				question = Question(prompt, options)
			else:
				question = Question(prompt, options, required=required)
		except Exception:
			msg = f"Could not create question ({context})"
			logger.exception(msg)
			num_errors += 1
		else:
			msg = f"Created question {question!r} ({context})"
			logger.debug(msg)

		return (question, num_errors, num_warnings)

	def format(self, question_num: int | None = None) -> str:
		"""Format the question into text."""
		if question_num is None:
			return self.prompt

		return f"{question_num}. {self.prompt}"


@dataclass
class Result:
	"""A result for a quiz."""

	name: str
	description: str
	image: str | None
	show_variables: list[str] | bool
	__requirements: list[Requirement]

	type ResultType = dict[
		Literal["name", "description", "image", "show_variables", "requirements"],
		str | list[Requirement.RequirementType],
	]

	@staticmethod
	def build_result(
		input_dict: ResultType, logger: logging.Logger, context: str
	) -> tuple["Result | None", int, int]:
		"""Build a result from a dictionary.

		Returns a tuple containing:
		The result (if successful) or None (if one or more errors occurred),
		The number of errors,
		The number of warnings.
		"""
		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = f"Result format is invalid ({context})"
			logger.error(msg)
			num_errors += 1
			return (None, num_errors, num_warnings)

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		name = input_dict.get("name")
		description = input_dict.get("description")
		image = input_dict.get("image")
		show_variables_raw = input_dict.get("show_variables")
		requirements_raw = input_dict.get("requirements")

		if name is None:
			msg = f"Missing result name ({context})"
			logger.warning(msg)
			num_warnings += 1
			name = ""
		elif not isinstance(name, str):
			try:
				name = str(name)
				msg = f"Result name is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert result name to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if description is None:
			msg = f"Missing result description ({context})"
			logger.warning(msg)
			num_warnings += 1
			description = ""
		elif not isinstance(description, str):
			try:
				description = str(description)
				msg = f"Result description is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert result description to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if image is not None and not isinstance(image, str):
			try:
				image = str(image)
				msg = f"Result image is not a string ({context})"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = f"Could not convert result image to string ({context})"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		show_variables = True
		if show_variables_raw is not None:
			if isinstance(show_variables_raw, str):
				if show_variables_raw.lower() in {"true", "yes", "yuh"}:
					show_variables = True
				elif show_variables_raw.lower() in {"false", "no", "nuh"}:
					show_variables = False
				else:
					msg = (
						f"Result show variables is not a list or a boolean ({context})"
					)
					logger.error(msg)
					num_errors += 1
			elif isinstance(show_variables_raw, bool):
				show_variables = show_variables_raw
			elif isinstance(show_variables_raw, list):
				show_variables = []
				for var_num, var in enumerate(show_variables_raw):
					if not isinstance(var, str):
						try:
							show_variables.append(str(var))
							msg = f"Result variable name is not a string (variable {var_num}, {context})"
							logger.warning(msg)
							num_warnings += 1
						except ValueError:
							msg = f"Could not convert result variable name to a string (variable {var_num}, {context})"
							logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
							num_errors += 1
					else:
						show_variables.append(var)
			else:
				msg = f"Result show variables is not a list or a boolean ({context})"
				logger.error(msg)
				num_errors += 1

		requirements = []
		if not isinstance(requirements_raw, (list, tuple)):
			msg = f"Result requirements is not a list ({context})"
			logger.error(msg)
			num_errors += 1
		elif requirements_raw is not None:
			for requirement_num, requirement_raw in enumerate(
				requirements_raw, start=1
			):
				requirement = Requirement.build_requirement(
					requirement_raw,
					logger,
					context + f", requirement {requirement_num}",
				)
				if requirement[0] is not None:
					requirements.append(requirement[0])
				num_errors += requirement[1]
				num_warnings += requirement[2]

		for i in input_dict:
			if i not in {
				"name",
				"description",
				"image",
				"show_variables",
				"requirements",
			}:
				msg = f"Unknown result parameter '{i}' ({context})"
				logger.warning(msg)
				num_warnings += 1

		if num_errors > 0:
			return (None, num_errors, num_warnings)

		result = None
		try:
			result = Result(name, description, image, show_variables, requirements)
		except Exception:
			msg = f"Could not create result ({context})"
			logger.exception(msg)
			num_errors += 1
		else:
			msg = f"Created result {result!r} ({context})"
			logger.debug(msg)

		return (result, num_errors, num_warnings)

	def requirements_met(self, variables: dict[str, float]) -> bool:
		"""Check if requirements are met for the result."""
		return all(req.is_met(variables) for req in self.__requirements)

	def format(
		self, *, name: bool = True, description: bool = True, image: bool = True
	) -> tuple[str | None, str | None, Image.Image | None]:
		"""Format the result into a name, description, and/or image."""
		name_text = None
		description_text = None
		image_content = None

		if name:
			name_text = f"**{self.name}**"

		if description:
			description_text = f"_{self.description}_"

		if image and self.image is not None:
			image_path = Path(self.image).resolve()
			image_content = Image.open(image_path.read_bytes())

		return (name_text, description_text, image_content)


@dataclass
class Quiz:
	"""A quiz containing multiple questions, answers, and results."""

	name: str
	description: str
	questions: list[Question]
	results: list[Result]
	variables: dict[str, float]
	show_variables: list[str] | bool
	submit_text: str | None
	results_title: str | None
	results_subtitle: str | None
	selected_answers: dict[int, Option] = field(default_factory=dict)

	type QuizType = dict[
		Literal[
			"name",
			"description",
			"questions",
			"results",
			"variables",
			"show_variables",
			"submit_text",
			"results_title",
			"results_subtitle",
		],
		str
		| list[Question.QuestionType]
		| list[Result.ResultType]
		| dict[str, float]
		| list[str],
	]

	def get_num_questions(self) -> int:
		"""Get the amount of questions."""
		return len(self.questions)

	def get_question(self, which: int) -> Question:
		"""Get a question."""
		return self.questions[which]

	def get_question_answers(self, which: int) -> list[Option]:
		"""Get the answers of a question."""
		return self.questions[which].options

	def pick_answer(self, question: int, answer: int) -> None:
		"""Select an answer for a question."""
		self.selected_answers.update(
			{question: self.questions[question].options[answer]}
		)

	def clear_answer(self, question: int) -> None:
		"""Clear the selected answer for a question."""
		self.selected_answers.pop(question, None)

	def finish(self) -> list[tuple[Result, dict[str, float]]]:
		"""Finish the current quiz."""
		effects: list[Effect] = []
		for i in range(len(self.questions)):
			if self.questions[i].required and i not in self.selected_answers:
				raise MissingRequiredQuestionError

			if i in self.selected_answers:
				effects.extend(self.selected_answers[i].effects)

		effects.sort(key=lambda effect: effect.priority)

		for effect in effects:
			effect.run(self.variables)

		shown_variables = None
		if self.show_variables is not False:
			variables = {}
			if self.show_variables is not True:
				for i in self.show_variables:
					variables.update({i: self.variables.get(i, 0)})

		results_raw = [
			result for result in self.results if result.requirements_met(self.variables)
		]

		results = []

		for result in results_raw:
			if self.show_variables is not False and result.show_variables is not False:
				if self.show_variables is True and result.show_variables is True:
					shown_variables = self.variables.copy()
				else:
					shown_variables = variables.copy()
					for variable in result.show_variables:
						if variable not in shown_variables:
							shown_variables.update(
								{variable: self.variables.get(variable, 0)}
							)

			results.append((result, shown_variables))

		return results

	@staticmethod
	def build_quiz(
		input_dict: QuizType, logger: logging.Logger | None = None
	) -> "Quiz | None":
		"""Build a quiz from a dictionary."""
		if logger is None:
			logger = logging.getLogger("quiz_builder")

		num_errors = 0
		num_warnings = 0

		if not isinstance(input_dict, dict):
			msg = "Quiz format is invalid"
			logger.error(msg)
			num_errors += 1
			return None

		formatted_dict = {}
		with contextlib.suppress(AttributeError):
			for i in input_dict:
				formatted_dict.update({i.lower(): input_dict[i]})
		input_dict = formatted_dict

		name = input_dict.get("name")
		description = input_dict.get("description")
		questions_raw = input_dict.get("questions")
		results_raw = input_dict.get("results")
		variables_raw = input_dict.get("variables")
		show_variables_raw = input_dict.get("show_variables")
		submit_text = input_dict.get("submit_text")
		results_title = input_dict.get("results_title")
		results_subtitle = input_dict.get("results_subtitle")

		if name is None:
			msg = "Missing quiz name"
			logger.warning(msg)
			num_warnings += 1
			name = ""
		elif not isinstance(name, str):
			try:
				name = str(name)
				msg = "Quiz name is not a string"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = "Could not convert quiz name to string"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if description is None:
			msg = "Missing quiz description"
			logger.warning(msg)
			num_warnings += 1
			description = ""
		elif not isinstance(description, str):
			try:
				description = str(description)
				msg = "Quiz description is not a string"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = "Could not convert quiz description to string"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		questions = []
		if not isinstance(questions_raw, (list, tuple)):
			msg = "Quiz questions is not a list"
			logger.error(msg)
			num_errors += 1
		elif questions_raw is not None:
			for question_num, question_raw in enumerate(questions_raw, start=1):
				question = Question.build_question(
					question_raw,
					logger,
					f"question {question_num}",
				)
				if question[0] is not None:
					questions.append(question[0])
				num_errors += question[1]
				num_warnings += question[2]

		if len(questions) < 1:
			msg = "Missing quiz questions"
			logger.error(msg)
			num_errors += 1

		results = []
		if not isinstance(results_raw, (list, tuple)):
			msg = "Quiz results is not a list"
			logger.error(msg)
			num_errors += 1
		elif results_raw is not None:
			for result_num, result_raw in enumerate(results_raw, start=1):
				result = Result.build_result(
					result_raw,
					logger,
					f"result {result_num}",
				)
				if result[0] is not None:
					results.append(result[0])
				num_errors += result[1]
				num_warnings += result[2]

		if len(results) < 1:
			msg = "Missing quiz results"
			logger.error(msg)
			num_errors += 1

		variables = {}
		if variables_raw is not None:
			if not isinstance(variables_raw, dict):
				msg = "Quiz variables is not a dictionary"
				logger.error(msg)
				num_errors += 1
			else:
				for var_num, var, val in enumerate(variables_raw.items()):
					new_var = None
					new_val = None
					if not isinstance(var, str):
						try:
							new_var = str(var)
							msg = f"Quiz variable name is not a string (variable {var_num})"
							logger.warning(msg)
							num_warnings += 1
						except ValueError:
							msg = f"Could not convert quiz variable name to a string (variable {var_num})"
							logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
							num_errors += 1
					else:
						new_var = var

					if not isinstance(val, (int, float)):
						try:
							new_val = float(val)
							msg = f"Quiz variable value is not a number (variable {var_num})"
							logger.warning(msg)
							num_warnings += 1
						except ValueError:
							msg = f"Could not convert quiz variable value to a number (variable {var_num})"
							logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
							num_errors += 1
					else:
						new_val = val

					if new_var is not None and new_val is not None:
						variables.update({new_var: new_val})

		show_variables = False
		if show_variables_raw is not None:
			if isinstance(show_variables_raw, str):
				if show_variables_raw.lower() in {"true", "yes", "yuh"}:
					show_variables = True
				elif show_variables_raw.lower() in {"false", "no", "nuh"}:
					show_variables = False
				else:
					msg = "Quiz show variables is not a list or a boolean"
					logger.error(msg)
					num_errors += 1
			elif isinstance(show_variables_raw, bool):
				show_variables = show_variables_raw
			elif isinstance(show_variables_raw, list):
				show_variables = []
				for var_num, var in enumerate(show_variables_raw):
					if not isinstance(var, str):
						try:
							show_variables.append(str(var))
							msg = f"Quiz variable name is not a string (variable {var_num})"
							logger.warning(msg)
							num_warnings += 1
						except ValueError:
							msg = f"Could not convert quiz variable name to a string (variable {var_num})"
							logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
							num_errors += 1
					else:
						show_variables.append(var)
			else:
				msg = "Quiz show variables is not a list or a boolean"
				logger.error(msg)
				num_errors += 1

		if submit_text is not None and not isinstance(submit_text, str):
			try:
				submit_text = str(submit_text)
				msg = "Quiz submit text is not a string"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = "Could not convert quiz submit text to string"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if results_title is not None and not isinstance(results_title, str):
			try:
				results_title = str(results_title)
				msg = "Quiz results title is not a string"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = "Could not convert quiz results title to string"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		if results_subtitle is not None and not isinstance(results_subtitle, str):
			try:
				results_subtitle = str(results_subtitle)
				msg = "Quiz results subtitle is not a string"
				logger.warning(msg)
				num_warnings += 1
			except ValueError:
				msg = "Could not convert quiz results subtitle to string"
				logger.error(msg)  # noqa: TRY400 # (shut the fuck up)
				num_errors += 1

		for i in input_dict:
			if i not in {
				"name",
				"description",
				"questions",
				"results",
				"variables",
				"show_variables",
				"submit_text",
				"results_title",
				"results_subtitle",
			}:
				msg = f"Unknown quiz parameter '{i}'"
				logger.warning(msg)
				num_warnings += 1

		quiz = None
		if num_errors < 1:
			try:
				quiz = Quiz(
					name,
					description,
					questions,
					results,
					variables,
					show_variables,
					submit_text,
					results_title,
					results_subtitle,
				)
			except Exception:
				msg = "Could not create quiz"
				logger.exception(msg)
				num_errors += 1
			else:
				msg = f"Created quiz {quiz!r}"
				logger.debug(msg)

		if quiz is None:
			logger.error(
				"Quiz build failed with %s errors and %s warnings",
				num_errors,
				num_warnings,
			)
		else:
			logger.info(
				"Quiz build succeeded with %s errors and %s warnings",
				num_errors,
				num_warnings,
			)

		return quiz

	def format_result(
		self, results: list[tuple[Result, dict[str, float]]]
	) -> tuple[str, Image.Image]:
		"""Format the given quiz result into text and an image."""
		text_lines = []
		result = None
		if len(results) > 0:
			result = results[0]

		if self.results_title is None:
			text_lines.append("## Quiz Results:")
		else:
			text_lines.append(f"## {self.results_title}")

		result_image = None
		if result is not None:
			result_contents = result[0].format()
			result_text = ""
			if self.results_subtitle is not None:
				result_text = f"{self.results_subtitle}"
			result_text = f"{result_text}{result_contents[0]}"
			text_lines.extend((result_text, result_contents[1]))
			result_image = result_contents[2]

			variables = result[1]
			if variables is not None:
				text_lines.append(f"-# {variables!s}")
		else:
			text_lines.append("Unfortunately, no valid result was found.")

		return ("\n".join(text_lines), result_image)


def main() -> None:
	"""Try to build a quiz using the specified file.

	Logs warnings and errors if something is wrong.
	"""
	parser = argparse.ArgumentParser(
		prog="Quiz Verifier",
		description="Verify a quiz builds successfully",
		epilog="Input a json file",
	)
	parser.add_argument("filename")
	parser.add_argument("-v", "--verbose", action="store_true")
	parser.add_argument("-r", "--run", action="store_true", help="Run the quiz")

	args = parser.parse_args()

	dt_fmt = "%Y-%m-%d %H:%M:%S"
	log_formatter = logging.Formatter(
		"[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
	)

	log_stream_handler = logging.StreamHandler()
	log_stream_handler.setFormatter(log_formatter)
	root_logger = logging.getLogger()
	root_logger.addHandler(log_stream_handler)
	root_logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

	quiz_file = Path(args.filename)
	quiz_contents = json.load(quiz_file.open("r", encoding="utf-8"))

	quiz = Quiz.build_quiz(quiz_contents)


if __name__ == "__main__":
	main()
