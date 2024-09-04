# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Nothing so far

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
