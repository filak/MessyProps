# MessyProps
UnMessing Java *.properties files

Java properties files can get messy. Using this script you can clean, sort, merge, compare the props files.

The script might be useful for:
- checking local config files when upgrading to a new version
- checking messages*.properties for new/obsolete translations

## Installation

> You need Python 3.12+ and Git

1. Download the script into a directory
2. Install requirements - currently only: tqdm  

     $ pip install -r requirements.txt

3. Run the script - show help

     $ py props_check.py -h

## Usage

There are 3 commands/actions available

     $ py props_check.py clean -h
     $ py props_check.py compare -h
     $ py props_check.py locate -h

## Examples

### Clean and sort several props files

     $ py props_check.py clean --indir /messy_project/configs

### Compare two i18n files

     $ py props_check.py compare messages_en.properties messages_cs.properties

### Locate keys in a git repository

     $ py props_check.py locate messages_en.properties /messy_project --branch main --subdir src --filext java,jsp,vm
