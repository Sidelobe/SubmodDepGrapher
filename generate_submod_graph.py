#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═╗┬ ┬┌┐ ┌┬┐┌─┐┌┬┐╔╦╗┌─┐┌─┐╔═╗┬─┐┌─┐┌─┐┬ ┬┌─┐┬─┐
╚═╗│ │├┴┐││││ │ ││ ║║├┤ ├─┘║ ╦├┬┘├─┤├─┘├─┤├┤ ├┬┘
╚═╝└─┘└─┘┴ ┴└─┘─┴┘═╩╝└─┘┴  ╚═╝┴└─┴ ┴┴  ┴ ┴└─┘┴└─

A script that creates a dependency graph of GIT submodules present in a
user-provided list of GIT repositories.

@author: Lorenz Bucher
@url: https://github.com/Sidelobe/SubmodDepGrapher
"""

import re
import os
import subprocess
import argparse
import pathlib
from urllib.parse import urlparse
from graphviz import Digraph

git_submodule_regex = re.compile(r".+\.?path\s?=\s?(.+)$\n.+\.?url\s?=\s?(.+)$", re.MULTILINE)

PRINT_DEBUG = False
temp_data = ".tempData" # directory to store temporary data

def list_submodules(uri, showleaves):
    # git config --blob HEAD:.gitmodules --list
    # git submodule foreach --recursive git remote get-url origin

    if urlparse(uri).scheme in ('http', 'https'):
        # Clone the repository locally into a temp folder (bare, shallow) to get the contents of the
        # gitmodules directory. Some hosts like Github do not support git archive.
        this_repo_name = uri.rsplit('/', 1)[-1] # take portion after last slash
        gitmodules_file_cat = ""
        try:
            subprocess.run("git clone --depth=1 --bare {0} {1}".format(uri, this_repo_name),
                            cwd=temp_data,
                            check=True,
                            capture_output=False,
                            shell=True,
                            text=True)

            gitmodules_file_cat = subprocess.run(r"git show HEAD:.gitmodules",
                                              cwd=os.path.join(temp_data, this_repo_name),
                                              check=True,
                                              capture_output=True,
                                              shell=True,
                                              text=True).stdout

            subprocess.run(r"rm -rf {0}".format(this_repo_name), cwd=temp_data, shell=True)

            submodules = re.findall(git_submodule_regex, gitmodules_file_cat)

        except subprocess.CalledProcessError as exc:
            if len(gitmodules_file_cat ) == 0:
                if showleaves:
                    return [this_repo_name, []]
                else:
                    return []

            print("Error in {0}: {1}".format(this_repo_name, exc.stderr))
            return []

    else:
        this_repo_name = pathlib.PurePath(uri).name
        if not os.path.exists(os.path.join(uri, ".gitmodules")):
            if showleaves:
                return [this_repo_name, []]
            else:
                return []

        try:
            l = subprocess.run("git config --file .gitmodules --list",
                               cwd=f"{uri}",
                               check=True,
                               capture_output=True,
                               shell=True,
                               text=True).stdout

            submodules = re.findall(git_submodule_regex, l)

            if PRINT_DEBUG:
                print("Repo [{}] has: ".format(this_repo_name))
                for submodule in submodules:
                    print("Submodule [{}] at location [{}]".format(submodule[0], submodule[1]))

        except subprocess.CalledProcessError as exc:
            error_msg = exc.output.splitlines()
            for line in error_msg:
                print(f"    	{exc.output}")
            print("Error in {0}: {1}".format(this_repo_name, exc.stderr))
            return []

    return [this_repo_name, submodules]


def consolidate_data():
    repos = []
    refRepos = {} # dict with uri->name
    edges = [] # list with [from, to]

    for submoduleList in submoduleLists:
        if not submoduleList:
            continue
    
        repoName = submoduleList[0]
        repos.append(repoName)
        for dep in submoduleList[1]:
            subRepoName = dep[0]
    
            # 'strip' any path prefixes, retain just the top directory
            rest, tail = os.path.split(subRepoName)
            subRepoName = tail
    
            uri = dep[1] # URI is unique identifier (= key)
    
            if urlparse(uri).scheme in ('http', 'https'):
                uri = uri.removesuffix('.git') # remove from end if present
            else:
                uri = os.path.abspath(uri) # store as absolute path to avoid
    
            if uri in refRepos:
                subRepoName = refRepos[uri] # use same name previously assigned
            elif subRepoName in refRepos.values():
                # same name has already been used, but with a different URI
                # -> modify the name to make it unique and stand out
                subRepoName = subRepoName + "*"
                refRepos.setdefault(uri, subRepoName)
            else:
                # First name given to the referenced repo becomes the name of node on graph
                refRepos.setdefault(uri, subRepoName)
    
            # Add connection
            edges.append([repoName, subRepoName])

    return [repos, refRepos, edges]

def scan_dir_for_repos(dir):
    dir = os.path.abspath(dir)
    dir_list = []
    for subdir in os.listdir(dir):
        subdir_path = os.path.join(dir, subdir)
        if os.path.isdir(subdir_path):
            try:
                is_git_repo = subprocess.run("git rev-parse --is-inside-work-tree",
                                               cwd=f"{subdir_path}",
                                               check=True,
                                               capture_output=True,
                                               shell=True,
                                               text=True).stdout

            except subprocess.CalledProcessError:
                is_git_repo = "False"

            if "true" in str.lower(is_git_repo):
                dir_list.append(subdir_path)

    return dir_list


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', help='Path of the output file (without extension)',
                        default='out')
    parser.add_argument('-f', '--format', help='Format of the output file', default='pdf',
                        choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('-v', '--view', action='store_true', help='View the graph')
    parser.add_argument('-s', '--showleaves',  action=argparse.BooleanOptionalAction, help='Also show repositories without submodules')
    parser.add_argument('-r', '--repos', help='List of repositories (path or URL), delimited by space',
                        nargs='+', type=str, default='')
    parser.add_argument('-d', '--dir', help='Base directory that will be scanned for direct subfolders with repos in them',
                        type=str, default='')

    args = parser.parse_args()

    '''
    for each repo provided
        List all submodules
        Add to dependency map / data structure
        generate dependency graph
    '''

    subprocess.run(r"mkdir -p {0}".format(temp_data), shell=True)

    repositoryList = args.repos

    # in case the directory option was used, extend the repository list with that
    if args.dir:
        # Scan directory for
        repositoryList = scan_dir_for_repos(args.dir)

    submoduleLists = []
    for repo in repositoryList:
        submoduleLists.append(list_submodules(repo, args.showleaves))

    # Get data ready for graphviz
    [repos, refRepos, edges] = consolidate_data()

    # Create graph
    graph = Digraph()
    for name in repos:
        label = name
        graph.node(name, label, shape='cylinder')
    for name in refRepos.values():
        label = name
        graph.node(name, label, shape='cylinder')
    for e in edges:
        graph.edge(e[0], e[1])

    graph.format = args.format
    graph.render(args.output, cleanup=True, view=args.view)

    subprocess.run(r"rm -rf {0}".format(temp_data), shell=True)
