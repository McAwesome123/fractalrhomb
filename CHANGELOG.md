# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Nothing so far

## [0.1.0] - 2024-07-31

### Added

- Setup file for Linux
- This changelog
- Usage info in readme
- Dataclasses for the API handler (`fractalthorns_dataclasses`)
- Exceptions for the API handler (`fractalthorns_exceptions`)
- A persistent cache (this is mainly dev qol)
- `primary_color` and `secondary_color` from `single_image`
- Various new bugs probably (tell me if you find any!)

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
