# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Nothing so far

## [0.10.1] - 2025-07-30

### Fixed
- Image commands no longer trigger empty message errors despite sending an image

## [0.10.0] - 2025-06-01

### Added
- Records can now show linked puzzles
  - Old caches may fail to load as a result; this is not an issue.
- Unsolved records link to linked puzzles or the discovery page by default

### Changed
- `/chapter` now requires specifying a chapter
  - You can still put in "(latest)" to get the latest chapter
- Unsolved records now show their title (website API change)
- Text changed in a few commands

### Removed
- SSE support (this is a fractalthorns change)

## [0.9.2] - 2024-05-12

### Changed
- Reduced most cache times and cooldowns

### Fixed
- Requesting a chapter that doesn't exist now gives an explanation rather than having the interaction fail
- Unhandled command exceptions should now be logged properly
- Added error handling for a command attempting to send an empty message

## [0.9.1] - 2024-05-11

### Changed
- Record name can no longer be None (API change)
- Record formatting now checks for None rather than the record being solved

## [0.9.0] - 2024-05-03

### Added
- Some scripts for starting the bot (don't worry, you can still make your own)
  - Any command line arguments given to the provided script will be passed to the bot
  - Note for making your own script: the logging library will create log files in the **current working directory** (which may not be the same as where the script is located)
- PowerShell scripts since not everyone uses command prompt anymore
- Customization for the file logger via .env
  - `LOG_FILE_NAME` for the file name to be used (default: "discord.log")
  - `LOG_FILE_WHEN` for the type of interval to be used (must be one of the following: "S", "M", "H", "D", "W0" - "W6", "midnight", refer to [this page](https://docs.python.org/3/library/logging.handlers.html#logging.handlers.TimedRotatingFileHandler) for more info) (default: "midnight")
  - `LOG_FILE_INTERVAL` for the interval between roll over (default: 1)
  - `LOG_FILE_BACKUP_COUNT` for how many old logs to keep (default: 7)
  - `LOG_FILE_AT_TIME` for when to roll over if the interval type is a weekday or midnight, in ISO 8601 format (with Z for UTC time or no Z for local time) (default: 00:00:00Z)
- Error logs are now also outputted to console (stderr)
  - This can be disabled with `--no-log-console`
  - Log level outputted to console can be changed with `--console-log-level`
- Can disable outputting logs to file with `--no-log-file`
  - Log level outputted to file can be changed with `--file-log-level`
- An admin command to manually make a news post to news channels
- Logging for if an exception kills the bot

### Changed
- Logs for bot functions now use a "fractalrhomb" logger instead of the "discord" logger
  - Log level for the "discord" logger is now controlled with `--discord-verbose`/`-dv`, `--discord-more-verbose`/`-dvv`, and `--discord-log-level`
  - Log level for the "fractalrhomb" logger is controlled with `--bot-verbose`/`-bv`, `--bot-more-verbose`/`-bvv`, and `--bot-log-level`
  - Log level for the root logger is now controlled with `--verbose`/`-v`, `--more-verbose`/`-vv`, and `--log-level`
- Scripts should no longer modify the shell environment after being run (e.g. pwd should not change after running a script)
- Bash scripts now use `python` instead of `python3`
  - I'm not a Linux user, so this may or may not break things. But if you are a Linux user, you should be able to fix them
- Limited `/restart-notification-listener` to bot dms
- Images and sketches now require entering a name
  - This is so the argument is auto selected when using the command, meaning you can just enter the name
  - The latest image or sketch can still be obtained by putting in "(latest)" or "." as the name
- Default user agent is now `fractalrhomb/{VERSION_SHORT}`
- Slightly increased name consistency

### Fixed
- Notifications listener should no longer get stuck waiting to reconnect for absurd amounts of time
- Several fixes regarding the restarting the notifications listener:
  - Will now force it out of waiting when trying to reconnect
  - No longer reports that the listener was restarted when nothing happened
  - No longer leaves errant resume events when a restart isn't needed
- Bash setup script checking for if `.env` _doesn't_ exist when trying to make a backup
- Bot script hanging when an invalid token is given
- Hopefully reduced cases of messages getting deferred forever due to an exception occurring

## [0.8.0] - 2024-12-01

### Added

- An info command for Aetol
- Changing the status now saves it
- The ability for the bot to work when user installed

### Changed

- All the `if not ctx.response.is_done(): ... else: ...` message sends are now handled by a dedicated function instead of copy pasting the same code everywhere
  - This function also handles user installs because they cannot use `ctx.send()`

### Security

- Updated dependencies in requirements file (most notably aiohttp)

## [0.7.0] - 2024-09-29

### Added

- aiohttp-sse-client2 (0.3.0) and RapidFuzz (3.10.0) as dependencies
  - RapidFuzz requires Visual C++ 2019 (:cvheadache:)
- SSE notification listening (Special Thanks: BerylRose/pierce-smith1)
  - Currently handles `news_update` notifications from `https://fractalthorns.com/notifications`
  - Sends a message in specified news channels upon receiving such a notification
  - Can be restarted by bot admin users
- User agent can have `{VERSION_SHORT}`, `{VERSION_LONG}`, or `{VERSION_FULL}` to serve as a placeholder for the current version
- Ability to load an Aetol dictionary
  - Requires: `aetol/particle_dictionary.tsv` or `aetol/word_dictionary.tsv`; Also supports `aetol/idiom_dictionary.tsv`
    - Expected particle format: `name`, `meaning`, `as verb`, `as noun`, `notes`, `category`
    - Expected word format: `name`, `meaning`, `as verb`, `as noun`, `formation`, `category`
    - Expected idiom format: `name`, `meaning`
    - Dictionaries not included at this time(?)
  - Particles and words can be searched using `/aetol search`
  - Idioms are displayed separately using `/aetol idioms`
  - Alphabet can be displayed using `/aetol alphabet`
- Bot admin command to save and reload bot data

### Changed
- Reworked bot channel commands to also work for other channel types (currently news)
  - Command group renamed to `channel` (from `botchannel`)
  - Subcommands renamed to `set`, `clear`, and `clearall` (from `add`, `remove`, and `removeall`)
- All "bot admin" or otherwise restricted commands now use the `BOT_ADMIN_USERS` environment variable
- All mentions of the version are now sourced from `src.fractalrhomb_globals`
- Default user agent now includes the short version
- Bot data should be slightly easier to read

### Fixed
- Channel parameter description on /channel commands
- Logging now has proper formatting rather than using f-strings

## [0.6.2] - 2024-09-22

### Fixed

- Sketch links should now properly link to the sketches

## [0.6.1] - 2024-09-05

### Fixed

- Description of `/search records` and `/search text`
- Description of the `limit` parameter of `/search records` and `/search text`

## [0.6.0] - 2024-09-04

### Added

- API coroutines for getting sketches
- API coroutine for searching images, records, record lines
- `Sketch` and `MatchResult` dataclasses
- `ItemsUngatheredError` and `SketchNotFoundError` exceptions
- `format_text` to `RecordLine` (removes random whitespace)
- Commands for getting sketches
- Commands for a random image, record, record line
- Commands for searching images, records, record lines

### Changed

- Increased required message length for warning for chapters
- Purge commands are now a single command
- Lowered cache duration and purge cooldown for full record contents
- Renamed `NSIRP_EMOJIS` to `NSIRP_EMOJI`

### Removed

- "Taking too long" message for searches

### Fixed

- Image contents cache not being saved

## [0.5.0] - 2024-08-28

### Added

- Image and record related requests now include links to the images and records
  - Those will need to be passed as a parameter to `from_obj()`
  - Deleting `.apicache` is recommended as the old cache will cause errors when loading.

### Changed

- Emojis are now used through environment variables (because they won't be the same for every bot)
- `from_obj()` methods no longer require adding arbitrary keys to the objects; those keys have been turned into parameters for `from_obj()`

### Fixed

- Setting the `image` parameter to `none` for `/image` no longer gives an exception

## [0.4.0] - 2024-08-27

### Added

- A few private commands (-say, -status)
- Discord status

## [0.3.1] - 2024-08-17

### Fixed

- The bot should no longer make a very high amount of concurrent requests, leading the server to think it's getting DDOSed (limited concurrent connections to 6 per host)
- The bot's standard exception handler should now work with exception groups correctly
- Corrected what exceptions are caught for the standard exception handler

## [0.3.0] - 2024-08-17

### Added

- Logging for the fractalthorns API handler (mostly info logs regarding cache access (not part of the discord logger; require `-rv` to be logged))
- `FractalthornsAPI.save_all_caches()` method
- Some protection against redundant cache saves

### Changed

- File IO is now done with Aiofiles
- Requests are now done with Aiohttp
- All related functions (and some others) are now async and must be awaited
- All functions that make requests now expect an aiohttp.ClientSession as the first parameter and return an async request context manager
- `FractalthornsAPI.get_cached_items()` now returns a direct copy of the cache with an added expiry time rather than just the stored items
- Search results can now be grouped by records
- API cache save and load are no longer private methods
- Saving cache to disk is no longer the API handler's responsibility (to avoid saving to disk 50 times for one request)
- Functions that use API should call `FractalthornsAPI.save_cache()` for the respective cache(s)
  - However, if unsure, `FractalthornsAPI.save_all_caches()` should be fine to use
- Timeout for requests increased to 30s (to prevent high amounts of parallel async requests from timing out)
- Cache folder renamed to `.apicache` (from `__apicache__`)

### Removed

- Requests (2.32.3) dependency

### Fixed

- Domain search results should no longer spit out entire records for a single search result.
- Root logger should now log properly

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
