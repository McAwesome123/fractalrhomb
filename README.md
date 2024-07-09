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

**Note!** The below instructions assume your Python installation can be found under `PATH`.
If it is not, open a command prompt and use this before following the instructions below (if the location of your Python install is different, you will need to change the paths):

```bat
set PATH=C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%PATH%
```

```bash
export PATH=/usr/bin/python3:/usr/lib/python3:$PATH
```

Afterwards, run the script and/or commands using this command prompt window. If you close it, you will need to enter the above command again.\
Before following the below instructions, verify that your version of Python is at least 3.12.4 by using:

```bat
python -V
```

```bash
python3 -V
```

(Linux note: The commands listed below may or may not be incorrect. I am not a Linux user.)

### Option 1 (Automatic, Windows Only):

1. Run the `setup.bat`
2. Verify there are no errors

Note: The script will not clear an existing `.venv`. If a `.env` file already exists, it will attempt to rename it to `.env.bak`. If that file already exists, you will be prompted to overwrite it. Choosing no will not stop it from overwriting the `.env` file.

### Option 2 (Manual):

(The below commands assume you are running them from the repository's root directory. If you are not, change the paths to lead to the directory.)

1. Create a virtual environment
	(Windows)

	```bat
	python -m venv .venv
	```

	(Linux)
 
 	```bash
  	python3 -m venv .venv
	```
2. Activate the virtual environment
	(Windows)

	```bat
	.venv\Scripts\activate.bat
	```

	(Linux)
 
	```bash
	source .venv/bin/activate
	```
3. Install the required packages
	```bat
	pip install -r requirements.txt
	```
 
	**OR**
   
	```bat
	pip install [package from the requirements list below]==[required version]
	```
 
	_(Note: Python does not need to be installed using pip)_

4. Create a `.env` file containing the following:
	- `FRACTALTHORNS_USER_AGENT`: The user agent to display when making requests (e.g: `"Fractal-RHOMB"`).

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
