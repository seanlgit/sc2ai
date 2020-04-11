# sc2-sharpy
Python framework for rapid development of Starcraft 2 AI bots

Sharpy uses [python-sc2](https://github.com/BurnySc2/python-sc2) and it is the framework used by [Sharpened Edge](https://ai-arena.net/bots/40/).

**Build statuses**

Master branch ![](https://github.com/DrInfy/sharpy-sc2/workflows/Python%20actions/badge.svg?branch=master)

Develop branch ![](https://github.com/DrInfy/sharpy-sc2/workflows/Python%20actions/badge.svg?branch=develop)

## Work in progress
The framework has all the necessary components to run the dummy bots that are used for testing against Sharpened Edge.
The folder structure is subject to change.

## Requirements
Python 3.7 (>=3.8 is not supported yet)

## Ladder Dummy Bots
To build dummy bot for ladder, run ladder_zip.py. Bots will appear as individual zip files in publish folder.

## Getting started

Read the [getting started](https://github.com/DrInfy/sharpy-sc2/wiki/1.-Getting-Started) guide in wiki.

## Contributing

To contribute to sharpy-sc2 source code, please create a pull request.

We also appreciate well written issues, comments and improvements to project wiki.

### Pull Request Process

* Keep pull requests small and atomic. Change only one logical thing at a time.
* All Github actions checks for the PR must pass before it will be reviewed.
    * Make sure that the source code is formatted according to rules (see below)
    * Make sure that the source code passes linting
    * Make sure that all tests pass

## Developing sharpy-sc2

### Using Virtual Environment

#### Windows

Virtual Environments (venv) can be used to isolate this project's Python dependencies from other projects.

You can create a virtual environment for this project with

```
venv-create.bat
```

And activate it with

```
venv-activate.bat
```

Venv needs to be activated for every new console window, so it may be helpful to create an alias such as
```
doskey sharpy=cd C:\Dev\sharpy-sc2 $T venv-activate.bat
```

More information about virtual environments can be found from the [documentation.](https://docs.python.org/3.6/tutorial/venv.html)

#### Other operating systems

You may replicate the commands used by the above bat scripts to work on your own operating system. 

### Installing Depedencies

To install all dependencies required to run the bots, use

```
pip install -r requirements.txt
```

To install all development dependencies, use

```
pip install -r requirements.dev.txt
```

### Code Formatting

sharpy-sc2 uses [Black](https://pypi.org/project/black/) for automatic Python source code formatting.

to format code automatically, run 

```
> py -m black .
All done! ✨ � ✨
272 files left unchanged.
```

Black can also be integrated to your favorite editor. See Editor Integration section in [Black](https://pypi.org/project/black/#editor-integration) readme.

### Linting

sharpy-sc2 uses [flake8](https://pypi.org/project/flake8/) for source code linting.

To run flake8 linting, use

```
> py -m flake8
0
```

### Running Tests

Tests are written using [pytest framework](https://docs.pytest.org/en/latest/getting-started.html).

To run the tests, use

```
pytest
```

pytest follows standard test discovery rules and will run all tests in the current directory and its subdirectories.

For new tests, make sure that...
1. file name follows the naming pattern of `*_test.py`
1. the test class name starts with `Test*`
1. all test methods start with `test_*`.
