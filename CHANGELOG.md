# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Nothing so far

## [0.14.0] - 2025-12-10

### Functionality

#### Changed

- Submitting a splash should now display a more helpful error message when getting a 400 bad request
- The bot should now avoid leaking who failed to submit a splash
- Message length warning for splash pages should be harder to trigger now

## [0.13.0] - 2025-11-25

### Functionality

#### Added

- Quiz functionality

#### Changed

- Splashes are no longer strictly limited to 80 characters due to emojis
- Splashes no longer filter out special characters (and formatting) when displayed
- If the bot times out on a response, it should give an appropriate response rather than a generic exception response(?)

#### Fixed

- Purging the sketch caches no longer incorrectly purges the image caches instead

### Technical

#### Added

- Anyio dependency
- Num2alpha dependency
- Check and message for command cooldown errors in `on_application_command_error`
- `src.fractalrhomb_globals.value_or_default` that returns the variable if it's not `None` or a default value otherwise

#### Changed

- Updated dependencies
- File IO in async functions is now done with anyio (instead of a mix of pathlib and aiofiles)
- Default Discord log level is now warning instead of unset
- `src.fractalrhomb_globals.split_message` can now split messages to an arbitrary length (defaulting to `MAX_MESSAGE_LENGTH`)

#### Fixed

- Bash scripts should now properly have unix line endings

#### Removed

- Aiofiles dependency

## [0.12.1] - 2025-10-28

### Technical

#### Changed

- Sending a splash now uses display name instead of global name

#### Fixed

- Splash submissions should no longer be able to send `null` as the display name and cause the server to `200 Internal Server Error`

## [0.12.0] - 2025-09-11

### Functionality

#### Changed

- Attempting to resend a splash to DMs now gives a proper error message if it fails
  - The button also turns green or red depending on whether it succeeded or failed

### Technical

#### Added

- A few optional environment variables:
  - `BOT_AUTH_URL` for a link to add the bot to a server/account
  - `BOT_ISSUE_URL` for a link to the github issues page
  - `BOT_CREATOR_ID` for the bot creator's discord ID to link to a profile

#### Fixed

- Fixed some typoes in splash logs
- Possibly fixed some issues regarding dotenv loading?

## [0.11.0] - 2025-08-05

### Functionality

#### Added

- Support for splashes!
  - This includes viewing the current splash, viewing a list of previously shown splashes, and submitting a new splash
  - Submitting a splash requires that the bot has an API key. If it doesn't, attempting to submit one will give an error message.
  - When submitting a splash, the splash text is not shown to anyone but yourself. If the bot can send messages in the channel, it will simply say "splash submitted".

#### Changed

- Domain search can now be used for sketches

### Technical

#### Added

- Support for request types besides GET
  - Trying to use an unknown request type will throw `src.fractalthorns_exceptions.UnknownRequestTypeError` when making the request
- Splash submission
  - This requires an API key to be given through `SPLASH_API_KEY` in .env

#### Changed

- Split changelog into functionality and technical sections
  - This is a retroactive change and includes previous versions mentioned in the changelog
  - Functionality refers mainly to changes the end user is likely to encounter
  - Technical refers mainly to changes that may affect a bot admin, but are unlikely to concern a typical end user
- Added missing dependencies to requirements.txt
- Logging to a non-existent directory will now create it instead of giving an error
- Symlinks to the log file are now resolved before it is modified
- Default log location is now `./bot_logs/discord.log`
- Sketches now utilize the new single_sketch endpoint
  - Various parts have been restructured to work with this
  - This includes the cache, meaning that cached sketches will fail to load
- Record and record text requests now technically support giving no arguments, but this is not currently used by the bot

#### Fixed

- Fixed slight oversight regarding logging in fractalthorns_api
  - fractalthorns_api is no longer automatically instantiated in src.fractalthorns_api
  - In this project, it is now being instantiated in main in fractalrhomb
- Fixed oversight with caching images and sketches without a name argument

## [0.10.1] - 2025-07-30

### Functionality

#### Fixed

- Image commands no longer trigger empty message errors despite sending an image

### Technical

#### Security

- Updated dependencies in requirements file (most notably aiohttp)

## [0.10.0] - 2025-06-01

### Functionality

#### Added

- Records can now show linked puzzles
  - Old caches may fail to load as a result; this is not an issue.
- Unsolved records link to linked puzzles or the discovery page by default

#### Changed

- `/chapter` now requires specifying a chapter
  - You can still put in "(latest)" to get the latest chapter
- Unsolved records now show their title (website API change)
- Text changed in a few commands

### Technical

#### Removed

- SSE support (this is a fractalthorns change)

## [0.9.2] - 2024-05-12

### Functionality

#### Changed

- Reduced most cache times and cooldowns

#### Fixed

- Requesting a chapter that doesn't exist now gives an explanation rather than having the interaction fail

### Technical

#### Fixed

- Unhandled command exceptions should now be logged properly
- Added error handling for a command attempting to send an empty message

## [0.9.1] - 2024-05-11

### Technical

#### Changed

- Record name can no longer be None (API change)
- Record formatting now checks for None rather than the record being solved

## [0.9.0] - 2024-05-03

### Functionality

#### Changed

- Images and sketches now require entering a name
  - This is so the argument is auto selected when using the command, meaning you can just enter the name
  - The latest image or sketch can still be obtained by putting in "(latest)" or "." as the name

### Technical

#### Added

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

#### Changed

- Logs for bot functions now use a "fractalrhomb" logger instead of the "discord" logger
  - Log level for the "discord" logger is now controlled with `--discord-verbose`/`-dv`, `--discord-more-verbose`/`-dvv`, and `--discord-log-level`
  - Log level for the "fractalrhomb" logger is controlled with `--bot-verbose`/`-bv`, `--bot-more-verbose`/`-bvv`, and `--bot-log-level`
  - Log level for the root logger is now controlled with `--verbose`/`-v`, `--more-verbose`/`-vv`, and `--log-level`
- Scripts should no longer modify the shell environment after being run (e.g. pwd should not change after running a script)
- Bash scripts now use `python` instead of `python3`
  - I'm not a Linux user, so this may or may not break things. But if you are a Linux user, you should be able to fix them
- Limited `/restart-notification-listener` to bot dms
- Default user agent is now `fractalrhomb/{VERSION_SHORT}`
- Slightly increased name consistency

#### Fixed

- Notifications listener should no longer get stuck waiting to reconnect for absurd amounts of time
- Several fixes regarding the restarting the notifications listener:
  - Will now force it out of waiting when trying to reconnect
  - No longer reports that the listener was restarted when nothing happened
  - No longer leaves errant resume events when a restart isn't needed
- Bash setup script checking for if `.env` _doesn't_ exist when trying to make a backup
- Bot script hanging when an invalid token is given
- Hopefully reduced cases of messages getting deferred forever due to an exception occurring

## [0.8.0] - 2024-12-01

### Functionality

#### Added

- An info command for Aetol
- The ability for the bot to work when user installed

### Technical

#### Added

- Changing the status now saves it

#### Changed

- All the `if not ctx.response.is_done(): ... else: ...` message sends are now handled by a dedicated function instead of copy pasting the same code everywhere
  - This function also handles user installs because they cannot use `ctx.send()`

#### Security

- Updated dependencies in requirements file (most notably aiohttp)

## [0.7.0] - 2024-09-29

### Functionality

#### Added
- Commands relating to aetol if an aetol dictionary is found
  - Particles and words can be searched using `/aetol search`
  - Idioms are displayed separately using `/aetol idioms`
  - Alphabet can be displayed using `/aetol alphabet`

#### Changed

- Reworked bot channel commands to also work for other channel types (currently news)
  - Command group renamed to `channel` (from `botchannel`)
  - Subcommands renamed to `set`, `clear`, and `clearall` (from `add`, `remove`, and `removeall`)

#### Fixed

- Channel parameter description on /channel commands

### Technical

#### Added

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
- Bot admin command to save and reload bot data

#### Changed

- All "bot admin" or otherwise restricted commands now use the `BOT_ADMIN_USERS` environment variable
- All mentions of the version are now sourced from `src.fractalrhomb_globals`
- Default user agent now includes the short version
- Bot data should be slightly easier to read

#### Fixed

- Logging now has proper formatting rather than using f-strings

## [0.6.2] - 2024-09-22

### Functionality

#### Fixed

- Sketch links should now properly link to the sketches

## [0.6.1] - 2024-09-05

### Functionality

#### Fixed

- Description of `/search records` and `/search text`
- Description of the `limit` parameter of `/search records` and `/search text`

## [0.6.0] - 2024-09-04

### Functionality

#### Added
- Commands for getting sketches
- Commands for a random image, record, record line
- Commands for searching images, records, record lines

#### Changed

- Increased required message length for warning for chapters
- Purge commands are now a single command
- Lowered cache duration and purge cooldown for full record contents

#### Removed

- "Taking too long" message for searches

### Technical

#### Added

- API coroutines for getting sketches
- API coroutine for searching images, records, record lines
- `Sketch` and `MatchResult` dataclasses
- `ItemsUngatheredError` and `SketchNotFoundError` exceptions
- `format_text` to `RecordLine` (removes random whitespace)

#### Changed

- Renamed `NSIRP_EMOJIS` to `NSIRP_EMOJI`

#### Fixed

- Image contents cache not being saved

## [0.5.0] - 2024-08-28

### Functionality

#### Added

- Image and record related requests now include links to the images and records

#### Fixed

- Setting the `image` parameter to `none` for `/image` no longer gives an exception

### Technical

#### Added

- Image and record related requests now include links to the images and records
  - Those will need to be passed as a parameter to `from_obj()`
  - Deleting `.apicache` is recommended as the old cache will cause errors when loading.

#### Changed

- Emojis are now used through environment variables (because they won't be the same for every bot)
- `from_obj()` methods no longer require adding arbitrary keys to the objects; those keys have been turned into parameters for `from_obj()`

## [0.4.0] - 2024-08-27

### Functionality

#### Added
- Discord status

### Technical

#### Added

- A few private commands (-say, -status)

## [0.3.1] - 2024-08-17

### Technical

#### Fixed

- The bot should no longer make a very high amount of concurrent requests, leading the server to think it's getting DDOSed (limited concurrent connections to 6 per host)
- The bot's standard exception handler should now work with exception groups correctly
- Corrected what exceptions are caught for the standard exception handler

## [0.3.0] - 2024-08-17

### Functional

#### Changed

- Search results are now grouped by records

#### Fixed

- Domain search results should no longer spit out entire records for a single search result.

### Technical

#### Added

- Logging for the fractalthorns API handler (mostly info logs regarding cache access (not part of the discord logger; require `-rv` to be logged))
- `FractalthornsAPI.save_all_caches()` method
- Some protection against redundant cache saves

#### Changed

- File IO is now done with Aiofiles
- Requests are now done with Aiohttp
- All related functions (and some others) are now async and must be awaited
- All functions that make requests now expect an aiohttp.ClientSession as the first parameter and return an async request context manager
- `FractalthornsAPI.get_cached_items()` now returns a direct copy of the cache with an added expiry time rather than just the stored items
- API cache save and load are no longer private methods
- Saving cache to disk is no longer the API handler's responsibility (to avoid saving to disk 50 times for one request)
- Functions that use API should call `FractalthornsAPI.save_cache()` for the respective cache(s)
  - However, if unsure, `FractalthornsAPI.save_all_caches()` should be fine to use
- Timeout for requests increased to 30s (to prevent high amounts of parallel async requests from timing out)
- Cache folder renamed to `.apicache` (from `__apicache__`)

#### Removed

- Requests (2.32.3) dependency

#### Fixed
- Root logger should now log properly

#### Security

- Updated `aiohttp` to 3.10.3

## [0.2.0] - 2024-08-13

### Functionality

#### Added

- Discord bot functionality
  - Includes the following fractalthorns slash commands: /news, /image, /description, /all_images, /chapter, /record, /record_text, /domain_search
  - As well as some miscellaneous slash commands: /license, /purge, /botchannel

#### Fixed

- A few discord formatting issues

### Technical

#### Added

- `DISCORD_BOT_TOKEN` to .env file (and setup)
- Retrieving cached items (`FractalthornsAPI.get_cached_items()`)
- A `CacheFetchError` if the above fails
- Title to ImageDescription objects

#### Changed

- **Replaced Discord.py (2.4.0) with Py-cord (2.6.0)**
- `NEWS_ITEMS` value is now `"news"` instead of `"news items"`
  - Clearing `/__apicache__` is recommended to avoid errors
  - Although it might fix itself eventually
- Cache metadata is now saved whenever any other cache type is saved
- Certain other cache save/load details
- Search results cache dict keys are now tuple[str, Literal]
- `FractalthornsAPI.__get_all_images()` now purges the images cache
- `FractalthornsAPI.__get_full_episodic()` now purges the chapters and records caches

#### Fixed

- Return type hinting for `FractalthornsAPI.get_single_image()`
- `FractalthornsAPI.__get_all_images()` no longer returns the `None` image
- `NewsEntry.from_obj()` making items `None` if it doesn't exist

## [0.1.0] - 2024-07-31

### Technical

#### Added

- Setup file for Linux
- This changelog
- Usage info in readme
- Dataclasses for the API handler (`fractalthorns_dataclasses`)
- Exceptions for the API handler (`fractalthorns_exceptions`)
- A persistent cache (this is mainly dev qol)
- `primary_color` and `secondary_color` from `single_image`

#### Changed

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
