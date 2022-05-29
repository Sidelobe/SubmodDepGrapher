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

git_submodule_regex = re.compile(r".+\.path=(.+)$\n.+\.url=(.+)$", re.MULTILINE)

PRINT_DEBUG = True

def list_submodules(uri):
    # git config --blob HEAD:.gitmodules --list
    # git submodule foreach --recursive git remote get-url origin

    if urlparse(uri).scheme in ('http', 'https'):
        print("is URL")
        raise ValueError("Not implemented yet!")
        # TODO: test URL
    else:
        thisRepoName= pathlib.PurePath(uri).name
        try:
            l = subprocess.run("git config --file .gitmodules --list",
                               cwd=f"{uri}",
                               check=True,
                               capture_output=True,
                               shell=True,
                               text=True).stdout

            submodules = re.findall(git_submodule_regex, l)

            if PRINT_DEBUG:
                print("Repo [{}] has: ".format(thisRepoName))
                for submodule in submodules:
                    print("Submodule [{}] at location [{}]".format(submodule[0], submodule[1]))

        except subprocess.CalledProcessError as exc:
            error_msg = exc.output.splitlines()
            for line in error_msg:
                print(f"    	{line}")
            return []

        return [thisRepoName, submodules]

    return []


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

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', help='Path of the output file (without extension)',
                        default='out')
    parser.add_argument('-f', '--format', help='Format of the output file', default='pdf',
                        choices=['bmp', 'gif', 'jpg', 'png', 'pdf', 'svg'])
    parser.add_argument('-v', '--view', action='store_true', help='View the graph')
    parser.add_argument('-r', '--repos', help='List of repositories (path or URL), delimited by space',
                        nargs='+', type=str, default='')

    args = parser.parse_args()

    '''
    for each repo provided
        List all submodules
        Add to dependency map / data structure
        generate dependency graph
    '''

    submoduleLists = []
    for repo in args.repos:
        submoduleLists.append(list_submodules(repo))

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
