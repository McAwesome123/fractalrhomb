# Fractal RHOMB

A discord bot\* that uses the API of https://fractalthorns.com/ \
\* Bot functionality has yet to be implemented.

## Usage

To use, it is recommended to activate the venv (from `.venv\scripts`) and run the following command in the repository's root directory.

```bat
python -i -m src.fractalthorns_api
```

Afterwards, access the methods provided by the `fractalthorns_api` singleton, such as:

```
news = fractalthorns_api.get_all_news()
image = fractalthorns_api.get_single_image("vertigo")
records = fractalthorns_api.get_full_episodic(display_chapters = ["i", "ii", "iii"])
```

Most of the methods return text, which can just be printed out:

```
print(news)
print(image[0])
print(records)
```

`get_single_image` is the main exception as it returns the image metadata, and an image tuple.

## Features

### Implemented:

- Access to all currently available API endpoints at https://fractalthorns.com/api/v1/docs
- Text returned by the public functions contains discord formatting
- `all_news`, `single_image`, and `single_record` allow for customizing what information is shown
- `all_news`, `all_images`, `full_episodic`, and `domain_search` allow for choosing which/how many items are shown

### To do:

- Add the discord bot
- Add useful logging
- Make the cache persistent

## Setup

See [Windows Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Windows-Setup) or [Linux Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Linux-Setup).

## Requirements

- [Python (3.12.4)](https://www.python.org/downloads/)
- [Requests (2.32.3)](https://pypi.org/project/requests/2.32.3/)
- [Discord.py (2.4.0)](https://pypi.org/project/discord.py/2.4.0/)
- [Pillow (10.4.0)](https://pypi.org/project/pillow/10.4.0/)
- [Python-dotenv (1.0.1)](https://pypi.org/project/python-dotenv/1.0.1/)

	_(and any dependencies for the above)_

Newer versions may be used as long as they are backward compatible.

## Contributing

I don't have hard rules for contributing to this project, just open an issue or pull request.\
When making changes, I ask that you maintain the same (or a similar) style, at least in already existing files.

## Changelog

See [Changelog](CHANGELOG.md)
