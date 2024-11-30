# Fractal RHOMB

A discord bot that uses the API of https://fractalthorns.com/

## Usage

To use, it is recommended to activate the venv (from `.venv\scripts` or `.venv\bin`) and run the following command in the repository's root directory.

```bat
python fractalrhomb.py
```

Make sure the `.env` file contains a valid bot token.

If successful, it should say "Logged in as [user]"

Otherwise, it likely would have given an error.

To view command line parameters, add `-h` to the end.

## Features

### Implemented:

- Access to all currently available API endpoints at https://fractalthorns.com/api/v1/docs
- Text returned by the dataclasses' `format` methods contains discord formatting
- `NewsEntry`, `Image`, and `Record` allow for customizing what information is shown
- Discord bot functionality

### To do:

- (?)

## Setup

See [Windows Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Windows-Setup) or [Linux Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Linux-Setup).

## Requirements

- [Python (3.12.4)](https://www.python.org/downloads/)
- [Aiofiles (24.1.0)](https://pypi.org/project/aiofiles/24.1.0/)
- [Aiohttp (3.11.8)](https://pypi.org/project/aiohttp/3.11.8/)
- [Aiohttp-sse-client2 (0.3.0)](https://pypi.org/project/aiohttp-sse-client2/0.3.0/)
- [Pillow (10.4.0)](https://pypi.org/project/pillow/10.4.0/)
- [Py-cord (2.6.1)](https://pypi.org/project/py-cord/2.6.0/)
- [Python-dotenv (1.0.1)](https://pypi.org/project/python-dotenv/1.0.1/)
- [RapidFuzz (3.10.1)](https://pypi.org/project/RapidFuzz/3.10.0/)
- [Visaul C++ 2019](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads)

	_(and any dependencies for the above)_

Newer versions may be used as long as they are backward compatible.

Optionally, you may install [Ruff](https://pypi.org/project/ruff/) to use for linting and/or formatting.

## Contributing

I don't have hard rules for contributing to this project, just open an issue or pull request.\
When making changes, maintaining the same or a similar style would be preferable, at least in existing files.

## Changelog

See [Changelog](CHANGELOG.md)
