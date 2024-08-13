# Fractal RHOMB

A discord bot that uses the API of https://fractalthorns.com/

## Usage

To use, it is recommended to activate the venv (from `.venv\scripts` or `.\venv\bin`) and run one of the following commands in the repository's root directory.

### Discord bot

```bat
python fractalrhomb.py
```

If successful, it should say "Logged in as ..."

Otherwise, it likely would have printed out an error.

### API usage

```bat
python -i -m src.fractalthorns_api
```

Afterwards, access the methods provided by the `fractalthorns_api` singleton, such as:

```py
>>> news = fractalthorns_api.get_all_news()
>>> record = fractalthorns_api.get_single_record("canopy-i")
>>> image = fractalthorns_api.get_single_image("vertigo")
```

Most of the single item methods return a dataclass and most of the multi item methods return a list of dataclasses. The dataclasses can either be printed directly or using the `format` method.

```py
>>> print(news[0])
title: an impressive background
items: ['(feat) replaced time-of-day based backgrounds', "the new backgrounds change color depending on the page you're on, and the image switches every day of the week", 'highly experimental, might delete later', '(feat) added a "primary_color" and "secondary_color" field to image objects from the api']
date: 07/28/24
version: beta.release.07-28-24.1
```

```py
>>> print(record.format())
> ## canopy i
> (_canopy-i, in 265404_)
> _chapter iii_
```

`get_single_image` is the main exception as, while it's for a single item, it actually returns a tuple

```py
>>> print(image)
(Image(name='vertigo', title='vertigo', date='2023-08-01', ordinal=92, image_url='https://fractalthorns.com/serve/image/vertigo', thumb_url='https://fractalthorns.com/serve/thumb/vertigo', canon=None, has_description=False, characters=['romal'], speedpaint_video_url=None, primary_color='#f23487', secondary_color='#9d2e9d'), (<PIL.PngImagePlugin.PngImageFile image mode=RGBA size=768x1024 at 0x1EC9C148920>, <PIL.PngImagePlugin.PngImageFile image mode=RGBA size=300x60 at 0x1EC9C148950>))
```

So you will probably want to do something like this instead

```py
>>> print(image[0].format())
> ## vertigo
> _canon: none_
> characters: romal
> no speedpaint video
```

## Features

### Implemented:

- Access to all currently available API endpoints at https://fractalthorns.com/api/v1/docs
- Text returned by the dataclasses' `format` methods contains discord formatting
- `NewsEntry`, `Image`, and `Record` allow for customizing what information is shown
- Discord bot functionality

### To do:

- Add useful logging
- Use a proper database
- Make some functions async

## Setup

See [Windows Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Windows-Setup) or [Linux Setup](https://github.com/McAwesome123/fractal-rhomb/wiki/Linux-Setup).

## Requirements

- [Python (3.12.4)](https://www.python.org/downloads/)
- [Requests (2.32.3)](https://pypi.org/project/requests/2.32.3/)
- [Py-cord (2.6.0)](https://pypi.org/project/py-cord/2.6.0/)
- [Pillow (10.4.0)](https://pypi.org/project/pillow/10.4.0/)
- [Python-dotenv (1.0.1)](https://pypi.org/project/python-dotenv/1.0.1/)

	_(and any dependencies for the above)_

Newer versions may be used as long as they are backward compatible.

## Contributing

I don't have hard rules for contributing to this project, just open an issue or pull request.\
When making changes, I ask that you maintain the same (or a similar) style, at least in already existing files.

## Changelog

See [Changelog](CHANGELOG.md)
