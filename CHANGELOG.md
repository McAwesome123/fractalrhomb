# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Replaced Requests (2.32.3) with Aiohttp (3.10.3)

### Security

- Updated `aiohttp` to 3.10.3

## [0.2.0] - 2024-08-13

### Added

- Discord bot functionality
  - Includes the following fractalthorns slash commands: /news, /image, /description, /all_images, /chapter, /record, /record_text, /domain_search
  - As well as some miscellaneous slash commands: /license, /purge, /botchannel
- `DISCORD_BOT_TOKEN` to .env file (and setup)
- Retrieving cached items (`FractalthornsAPI.get_cached_items()`)
- A `CacheFetchError` if the above fails
- Title to ImageDescription objects

### Changed

- **Replaced Discord.py (2.4.0) with Py-cord (2.6.0)**
- `NEWS_ITEMS` value is now `"news"` instead of `"news items"`
  - Clearing `/__apicache__` is recommended to avoid errors
  - Although it might fix itself eventually
- Cache metadata is now saved whenever any other cache type is saved
- Certain other cache save/load details
- Search results cache dict keys are now tuple[str, Literal]
- `FractalthornsAPI.__get_all_images()` now purges the images cache
- `FractalthornsAPI.__get_full_episodic()` now purges the chapters and records caches

### Fixed

- Return type hinting for `FractalthornsAPI.get_single_image()`
- `FractalthornsAPI.__get_all_images()` no longer returns the `None` image
- `NewsEntry.from_obj()` making items `None` if it doesn't exist
- A few discord formatting issues

## [0.1.0] - 2024-07-31

### Added

- Setup file for Linux
- This changelog
- Usage info in readme
- Dataclasses for the API handler (`fractalthorns_dataclasses`)
- Exceptions for the API handler (`fractalthorns_exceptions`)
- A persistent cache (this is mainly dev qol)
- `primary_color` and `secondary_color` from `single_image`

### Changed

- Moved .env out of src
- Moved some parts of the readme to wiki
- Massively rewrote parts of the API handler
  - All of the public functions now return a dataclass in some way (e.g. by itself, in a list, in a tuple) instead of a string
  - A string can be obtained by using the `__str__`, `format`, or `format_inline` methods of the dataclass
    - `__str__` returns a newline-separated description of the class' contents
    - `format` returns a string with discord style formatting (some allow for customizing output by giving a dictionary to `formatting`)
    - `format_inline` returns a string with discord style formatting but without line breaks (only available for a select few dataclasses)
  - All exceptions directly raised by the API handler now inherit from `fractalthorns_exceptions.APIError`
- How the cache timestamp is tracked (moved the duration from the timestamp itself to the check)
- Cache duration and purge cooldown constants
- Some changes may have been missed (sorry!)

## [0.0.0] - 2024-07-08

First Public Release
