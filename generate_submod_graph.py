#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A script that creates a dependency graph of GIT submodules present in a
user-provided list of GIT repositories.

@author: lorenz
"""

import re
import subprocess
import argparse
import pathlib
from urllib.parse import urlparse
from graphviz import Digraph

git_submodule_regex = re.compile(r".+\.path=(.+)$\n.+\.url=(.+)$", re.MULTILINE)

PRINT_DEBUG = False

def parsed_uri(string):
    if urlparse(string).scheme in ('http', 'https',):
        return ['URL', string]
    else:
        return ['local', pathlib.PurePath(string).name]

def list_submodules(uri):

    # git config --blob HEAD:.gitmodules --list
    # git submodule foreach --recursive git remote get-url origin

    if urlparse(uri).scheme in ('http', 'https',):
        print("is URL")
        # TODO: test URL
    else:
        thisRepo = pathlib.PurePath(uri).name
        try:

            l = subprocess.run("git config --blob HEAD:.gitmodules --list",
                               cwd=f"{uri}",
                               check=True,
                               capture_output=True,
                               shell=True,
                               text=True).stdout


            submodules = re.findall(git_submodule_regex, l)

            if PRINT_DEBUG:
                print("Repo [{}] has: ".format(thisRepo))
                for submodule in submodules:
                    print("Submodule [{}] at location [{}]".format(submodule[0], submodule[1]))

        except subprocess.CalledProcessError as exc:
            error_msg = exc.output.splitlines()
            for line in error_msg:
                print(f"    	{line}")
            return []

        return [thisRepo, submodules]

    return []


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #Çparser.add_argument('-repos', help='List of repositories (path or URL)', type=parsed_uri, nargs='+', default='examples/repo1')
    parser.add_argument('-o', '--output', help='Path of the output file (without extension)',
                        default='out')
    parser.add_argument('-f', '--format', help='Format of the output file', default='pdf',
                        choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('-v', '--view', action='store_true', help='View the graph')

    args = parser.parse_args()

    '''
    for each repo provided
        List all submodules
        Add to dependency map / data structure
        generate dependency graph
    '''

    #submoduleLists = args.repos
    #print(submoduleLists)
    submoduleLists = []
    submoduleLists.append(list_submodules("./examples/repo1"))
    submoduleLists.append(list_submodules("./examples/repo2"))
    submoduleLists.append(list_submodules("./examples/repo3"))
    submoduleLists.append(list_submodules("./examples/repo4"))

    # Consolidate Data
    repos = []
    refRepos = {} # dict with url->name
    edges = [] # list with [from, to]
    for submoduleList in submoduleLists:
        if not submoduleList:
            continue

        repoName = submoduleList[0]
        repos.append(repoName)
        for dep in submoduleList[1]:
            subRepoName = dep[0]
            url = dep[1] # URL is unique identifier = key

            if url in refRepos:
                subRepoName = refRepos[url] # use name previously assigned
            else:
                # First name given to the referenced repo becomes the name of node on graph
                refRepos.setdefault(url, subRepoName)

            # Add connection
            edges.append([repoName, subRepoName])

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
