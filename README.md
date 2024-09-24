# MessyProps
Unmessing Java *.properties files

Java properties files can get messy. With **props_check.py** script you can check the properties files.

The script might be useful for:
- checking local config files for new/obsolete keys - ie when upgrading to a new version
- checking messages*.properties for new/obsolete keys - -dtto-

## Installation

> Prerequisites - You need to have installed: **Python 3.12+** and **Git** [with git grep]

1. Download the script into a directory
2. Install requirements - currently only: **tqdm** - run:

       $ pip install -r requirements.txt

3. Check - run the script to show help:

       $ py props_check.py -h

## Usage

There are 3 commands/actions available:

     $ py props_check.py clean -h
     $ py props_check.py compare -h
     $ py props_check.py locate -h

## Examples

### Deduplicate, sort and merge several config *.properties files

     $ py props_check.py clean --indir /messy_project/configs --output merged_configs.properties

### Compare two messages_*.properties files 

- for differing keys:

       $ py props_check.py compare messages_en.properties messages_cs.properties

- for differing keys and values:

       $ py props_check.py compare new/messages_en.properties old/messages_en.properties --values 

### Locate keys from a props file in a git repository

     $ py props_check.py locate config.properties /messy_project/repo --branch main --subdir src --filext java,jsp,vm

> A key is currently being located using **git grep** command - ie:

     $ git grep -c "<key>" <branch> -- *.java *.vm 
     $ git grep -c "<key>" <branch> -- <subdir/>*.java <subdir/>*.vm
