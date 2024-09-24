import argparse
import collections
import multiprocessing
import re
import subprocess
from pathlib import Path
from tqdm import tqdm

appname = 'props_check'
appversion = '0.1.0'
appdesc = 'Unmessing Java *.properties files'
appauthor = 'by Filip Kriz @filak'
appusage = 'Help:   props_check.py -h \n'


def main():

    print('\n\n')
    print('*****************************************')
    print('*  ', appname, appversion)
    print('*  ', appdesc)
    print('*  ', appauthor)
    print('*****************************************\n')

    parser = argparse.ArgumentParser(description='Input files are expected to be in UTF-8 encoding.')
    subparsers = parser.add_subparsers(dest='action', help='Available commands')

    parser_clean = subparsers.add_parser('clean',
                                         help='Clean and sort *.props files',
                                         description='Using indir+output file causes merging all the props into the output file.')
    group1 = parser_clean.add_mutually_exclusive_group()
    group1.add_argument('--infile', help="Input - path to *.properties file")
    group1.add_argument('--indir', help="Input - path to directory with *.properties files")
    parser_clean.add_argument('--output', help="Output - file path Or RELATIVE sub-directory path")
    parser_clean.add_argument('--add_spaces', action='store_true', help='Add spaces around = for better readability')
    parser_clean.add_argument('--strip_comments', action='store_true', help='Strip comments')
    parser_clean.add_argument('--utf8', action='store_true', help='Convert values to UTF-8')

    parser_compare = subparsers.add_parser('compare',
                                           help='Compare keys and/or values in two props files',
                                           description='It is advisable to clean the files before comparing')
    parser_compare.add_argument('infile_a', help="Input - path to *.properties file")
    parser_compare.add_argument('infile_b', help="Input - path to *.properties file")
    parser_compare.add_argument('--values', help="Compare both keys and values")

    parser_compare = subparsers.add_parser('locate',
                                           help='Lookup and locate props keys in source code',
                                           description='You need Git installed [git grep] and a local git repository')
    parser_compare.add_argument('infile', help="Input - path to *.properties file")
    parser_compare.add_argument('repo_path', help="Repository FULL path")
    parser_compare.add_argument('--branch', help="Scope lookup to a specific branch")
    parser_compare.add_argument('--subdir', help="Scope lookup to a specific sub-directory")
    parser_compare.add_argument('--filext', help="Filter by file types extensions - comma delimited list ie: java,js,jsp,tld,xml,xsl,vm")
    parser_compare.add_argument('--multi', action='store_true', help='Use multiprocessing for lookups')

    args = parser.parse_args()

    if args.action == 'clean':
        props_clean(args)
    elif args.action == 'compare':
        props_compare(args)
    elif args.action == 'locate':
        props_locate(args)
    else:
        print('Action NOT supported !')


def props_clean(args):

    print("\n*** Properties cleaning ***\n")

    if args.infile:
        parse_file(args.infile, output=args.output,
                   strip_comments=args.strip_comments, utf8=args.utf8, add_spaces=args.add_spaces)

    elif args.indir:
        if not dir_exists(args.indir):
            print('\nERROR: Input directory NOT exists: ', args.indir, '\n')
            return

        input_dir = Path(args.indir)

        for input_file in list(input_dir.glob('*.properties')):
            parse_file(input_file, output=args.output, is_batch=True,
                       strip_comments=args.strip_comments, utf8=args.utf8, add_spaces=args.add_spaces)


def props_compare(args):

    print("\n*** Properties comparing ***\n")

    properties_a = load_properties_file(args.infile_a)
    if not properties_a:
        print('No properties found in: ', args.infile_a, '\n')
        return

    properties_b = load_properties_file(args.infile_b)
    if not properties_b:
        print('No properties found in: ', args.infile_b, '\n')
        return

    if args.values:
        differing_values = compare_dict_values(properties_a, properties_b)

        print('\n*** Different values: ')
        for key, val1, val2 in differing_values:
            print(f"{key}={val1} | {val2}")

    missing_in_dict1, missing_in_dict2 = compare_dict_keys(properties_a, properties_b)

    headers = 'Human |Key=Value'

    print('\n*** Keys missing in: ', args.infile_a)
    print(headers)
    for key in missing_in_dict1:
        value_tuple = properties_b[key][0]
        print(decode_unicode_escapes(key).replace('\\ ', ' '), '|' + key + '=' + value_tuple[0])

    print('\n*** Keys missing in: ', args.infile_b)
    print(headers)
    for key in missing_in_dict2:
        value_tuple = properties_a[key][0]
        print(decode_unicode_escapes(key).replace('\\ ', ' '), '|' + key + '=' + value_tuple[0])


def props_locate(args):

    print("\n*** Properties locating ***")

    try:
        git_version = subprocess.run(['git', '--version'], check=False, capture_output=True, text=True, timeout=5)
        if git_version:
            print('Git version: ', git_version.stdout)
    except:
        print('\nERROR: Git not found !\n')
        return

    properties = load_properties_file(args.infile)
    if not properties:
        print('No properties found in: ', args.infile, '\n')
        return

    print('Input file : ', args.infile)
    print('Repository : ', args.repo_path)
    print('Branch  : ', args.branch)
    print('Sub-dir : ', args.subdir)
    print('Files   : ', args.filext)
    print('MultiProc : ', args.multi)

    keys_raw = sorted(list(set(properties.keys())))
    keys_lookup = []

    for kr in keys_raw:
        key = kr.replace('\\ ', ' ')
        key = decode_unicode_escapes(key)
        keys_lookup.append((key, kr))

    pargs_tail = []

    if args.branch:
        pargs_tail.append(args.branch.strip())

    subdir = ''
    if args.subdir:
        subdir = args.subdir.strip().strip('/').strip() + '/'

    file_exts = None
    if args.filext:
        file_exts = args.filext.strip().split(',')

    if file_exts:
        pargs_tail.append('--')

        for ext in file_exts:
            pargs_tail.append(subdir + '*.' + ext.strip())

    elif subdir:
        pargs_tail.append('--')
        pargs_tail.append(subdir.strip('/'))

    cwd_repo = args.repo_path.strip('/')
    pargs_all = []

    # git grep -c "<key>" <branch> -- *.java *.js *.jsp *.tld *.xml *.xsl*
    # git grep -c "<key>" <branch> -- <subdir/>*.java <subdir/>*.jsp ...

    for key, kr in keys_lookup:
        pargs = ['git', 'grep', '-c']
        pargs.append('"' + key + '"')
        pargs += pargs_tail
        # print(' '.join(pargs))
        if key == kr:
            key_out = key
        else:
            key_out = kr + '|' + key
        pargs_all.append((key_out, pargs))
        pargs = None

    output = []

    if not args.multi:
        for key_out, parg in tqdm(pargs_all, desc='Progress: ', ascii=True):
            output.append(grep_repo(key_out, parg, cwd_repo))

    if args.multi:
        with multiprocessing.Pool() as pool:
            global progress_bar
            progress_bar = tqdm(total=len(pargs_all), desc='Progress: ', ascii=True)

            results = [pool.apply_async(grep_repo,
                                        (key_out, parg, cwd_repo,),
                                        callback=update_progress_bar) for key_out, parg in pargs_all]
            output = [r.get() for r in results]
            progress_bar.close()

    print('Total processed keys : ', len(keys_lookup), '- output : ', len(output))

    found = []
    missing = []

    if output:
        for is_found, key_out, pargs_out, ctx in output:
            if is_found:
                found.append((key_out, pargs_out, ctx))
            else:
                missing.append((key_out, pargs_out))

    if found:
        found_out = []
        found_cnt = 0
        for key_out, pargs_out, ctx in found:
            found_cnt += 1
            if found_cnt == 1:
                found_out.append(f"Searching command: {pargs_out}\n\n")
            found_out.append(f"{key_out}\n{ctx}\n")
        found_rep = Path(args.infile).name + '_found.txt'
        save_output(found_rep, '\n'.join(found_out))
        print('Found keys : ', found_cnt)
        print(' - report : ', found_rep)

    if missing:
        missing_out = []
        missing_cnt = 0
        for key_out, pargs_out in missing:
            missing_cnt += 1
            if missing_cnt == 1:
                missing_out.append(f"Searching command: {pargs_out}\n\n")
            missing_out.append(f"{key_out}")
        missing_rep = Path(args.infile).name + '_missing.txt'
        save_output(missing_rep, '\n'.join(missing_out))
        print('Missing keys : ', len(missing))
        print(' - report : ', missing_rep)


def grep_repo(key, pargs, cwd_repo):

    res = subprocess.run(pargs, cwd=cwd_repo, check=False, capture_output=True, text=True, timeout=20)
    pargs_out = ' '.join(pargs)
    if res:
        if res.stdout:
            return (True, key, pargs_out, res.stdout)

    return (False, key, pargs_out, None)


def update_progress_bar(result):
    progress_bar.update()


def parse_file(input_file, output=None, is_batch=False, strip_comments=False, utf8=False, add_spaces=False):

    if not file_exists(input_file):
        print('\nERROR: File not found: ', input_file, '\n')
        return

    print('Input file: ', input_file)

    properties = load_properties_file(input_file, utf8=utf8)
    if not properties:
        print('No properties found in: ', input_file, '\n')
        return

    output_file = None
    merge_output = False

    if not output:
        output_file = 'sorted_' + Path(input_file).name
    elif dir_exists(output, check_relative=True):
        output_file = str(Path(output, 'sorted_' + Path(input_file).name))
    elif str(output).endswith('.properties'):
        output_file = output
        if is_batch:
            merge_output = True

    if not output_file:
        print('\nERROR: Output file cannot be created !\n')
        return

    sorted_properties = sort_properties_by_key(properties)
    grouped_properties, grouped_comments = group_properties_by_prefix(sorted_properties)

    if strip_comments:
        grouped_comments = None

    formatted_content = format_grouped_properties(grouped_properties,
                                                  source_file=input_file,
                                                  grouped_comments=grouped_comments,
                                                  add_spaces=add_spaces)

    saved = save_output(output_file, formatted_content, append=merge_output)
    if not saved:
        print('\nERROR: Saving output file FAILED !\n')
        return
    if merge_output:
        print(f"Output appended to:  {output_file}\n")
    else:
        print(f"Output saved to:  {output_file}\n")


def load_properties_file(file_path, utf8=False):
    try:
        properties = {}
        with open(file_path, 'r', encoding='utf-8') as file:
            comments = []
            long_line = False
            for line in file:
                line = line.strip()

                # Process comment line
                if line and (line.startswith('#') or line.startswith('!')):
                    comments.append(line)
                    if line.endswith('\\'):
                        long_line = True

                # Process key=value line
                elif line and not line.startswith('#') and not line.startswith('!') and '=' in line and not long_line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    key = escape_spaces(key)
                    value = value.strip()

                    if utf8:
                        value = decode_unicode_escapes(value)

                    if comments:
                        comments_out = comments
                    else:
                        comments_out = None

                    value = (value, comments_out)

                    if properties.get(key):
                        if value not in properties.get(key):
                            properties[key].append(value)
                    else:
                        properties[key] = [value]

                    comments = []
                    long_line = False

                # Process long comment line
                elif line:
                    comments.append(line)
                    long_line = False

        return properties

    except:
        print('\nERROR: Loading this file FAILED: ')
        print(file_path)
        print('\n')
        return


def sort_properties_by_key(properties):
    return dict(sorted(properties.items()))


def group_properties_by_prefix(properties):
    grouped_properties = collections.defaultdict(lambda: collections.defaultdict(dict))
    grouped_comments = {}

    for key, value_list in properties.items():
        parts = key.split('.')
        values = []

        for value_tuple in value_list:
            xvalue, comments = value_tuple
            values.append(xvalue)

            if comments:
                if grouped_comments.get(key):
                    grouped_comments[key] += comments
                else:
                    grouped_comments[key] = comments

        if len(parts) >= 2:
            first_level = parts[0]
            second_level = parts[1]

            if grouped_properties[first_level][second_level].get(key):
                if values not in grouped_properties[first_level][second_level][key]:
                    grouped_properties[first_level][second_level][key] += values
            else:
                grouped_properties[first_level][second_level][key] = values
        else:
            if grouped_properties['_singles'][''].get(key):
                if values not in grouped_properties['_singles'][''][key]:
                    grouped_properties['_singles'][''][key] += values
            else:
                grouped_properties['_singles'][''][key] = values

    return (grouped_properties, grouped_comments)


def format_grouped_properties(grouped_properties, source_file=None, grouped_comments=None, add_spaces=False):
    formatted_lines = []
    duplicate_keys = []

    if source_file:
        formatted_lines.append('##### Source file: ' + str(source_file) + ' #####')

    for first_level, second_level_properties in sorted(grouped_properties.items()):
        formatted_lines.append(f"\n# {first_level}")
        for second_level, sub_properties in second_level_properties.items():
            if len(sub_properties) > 1:
                formatted_lines.append(f"\n## {first_level}.{second_level}")
            for key, value_list in sorted(sub_properties.items()):
                if len(value_list) > 1:
                    formatted_lines.append("### DUPLICATE KEY ###")
                    duplicate_keys.append(key)
                for value in value_list:
                    if grouped_comments:
                        for comment in grouped_comments.get(key, []):
                            if not comment.startswith('#') and not comment.startswith('!'):
                                comment = '  ' + comment
                            formatted_lines.append(comment)

                    if add_spaces:
                        formatted_lines.append(f"{key} = {value}")
                    else:
                        formatted_lines.append(f"{key}={value}")

            # if len(sub_properties) > 1:
            #     formatted_lines.append('')  # Add a blank line between groups

    if duplicate_keys:
        formatted_lines.append('\n\n### Duplicate keys ###')
        print('\nDuplicate keys: ')
        for dk in duplicate_keys:
            print(dk)
            formatted_lines.append('## ' + dk)
        print('\n')

    formatted_lines.append('\n#####\n')

    return '\n'.join(formatted_lines) + '\n\n'


def save_output(file_path, content, append=False):
    mode = 'w'
    if append:
        mode = 'a'
    try:
        with open(file_path, mode, encoding='utf-8') as file:
            file.write(content)
            return True
    except:
        return False


def decode_unicode_escapes(input_string):
    if '\\u' not in input_string:
        return input_string

    def replace_match(match):
        return chr(int(match.group(1), 16))

    return re.sub(r'\\u([0-9a-fA-F]{4})', replace_match, input_string)


def escape_spaces(input_string):
    if ' ' not in input_string:
        return input_string

    result = ''

    for i, char in enumerate(input_string):
        if char == ' ':
            if i == 0 or input_string[i - 1] != '\\':
                result += '\\ '
            else:
                result += char
        else:
            result += char

    return result


def file_exists(file_path):
    if not file_path:
        return False
    path = Path(file_path)
    return path.is_file()


def dir_exists(dir_path, check_relative=False):
    if not dir_path:
        return False
    path = Path(dir_path)

    if not path.is_dir():
        return

    if check_relative:
        current_dir = Path.cwd()
        cpath = Path(dir_path).resolve()
        test = cpath.is_relative_to(current_dir)
        return test

    return path.is_dir()


def compare_dict_keys(dict1, dict2):

    missing_in_dict1 = sorted(list(dict2.keys() - dict1.keys()))
    missing_in_dict2 = sorted(list(dict1.keys() - dict2.keys()))

    return missing_in_dict1, missing_in_dict2


def compare_dict_values(dict1, dict2):
    differing_keys = []

    for key in dict1.keys():
        if key in dict2:
            if dict1[key][0][0] != dict2[key][0][0]:
                differing_keys.append((key, dict1[key][0][0], dict2[key][0][0]))

    return sorted(differing_keys)


if __name__ == '__main__':
    main()
