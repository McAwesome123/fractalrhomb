# Fractalrhomb

A discord bot that uses the API of https://fractalthorns.com/

## Setup

See [Windows Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Windows-Setup) or [Linux Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Linux-Setup).

## Usage

> [!IMPORTANT]\
> Make sure the `.env` file contains a valid bot token before running or the bot will fail to start.

To use, you may run one of the provided `start_bot` scripts. To start it manually, it is recommended to activate the venv (from `.venv\Scripts` on Windows or `.venv\bin` on Unix) and run the python script. For example:

```bat
.venv\Scripts\activate.bat
python fractalrhomb.py
```
```bash
source .venv/bin/activate
python3 fractalrhomb.py
```

> [!NOTE]\
> By default, the logging library will try to create a log file in the *current working directory*. Make sure it is correct when running the python script directly or making your own launch script to avoid polluting random folders with log files.

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

## Requirements

- [Python (3.12.4)](https://www.python.org/downloads/)
- [Aiohttp (3.13.2)](https://pypi.org/project/aiohttp/3.13.2/)
- [Anyio (4.11.0)](https://pypi.org/project/anyio/4.11.0/)
- [Pillow (12.0.0)](https://pypi.org/project/pillow/12.0.0/)
- [Py-cord (2.6.1)](https://pypi.org/project/py-cord/2.6.1/)
- [Python-dotenv (1.2.1)](https://pypi.org/project/python-dotenv/1.2.1/)
- [RapidFuzz (3.14.3)](https://pypi.org/project/RapidFuzz/3.14.3/)
- [Visual C++ 2019](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads)

	_(and any dependencies for the above)_

Newer versions may be used as long as they are backward compatible.

Optionally, you may install [Ruff](https://pypi.org/project/ruff/) to use for linting and/or formatting.

## Contributing

I don't have hard rules for contributing to this project, just open an issue or pull request.\
When making changes, maintaining the same or a similar style would be preferable, at least in existing files.

## Changelog

See [Changelog](CHANGELOG.md)
