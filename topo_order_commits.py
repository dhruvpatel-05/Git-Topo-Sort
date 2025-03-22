#!/usr/bin/env python3
'''''
Dhruv Patel CS35L

I ran strace -f python3 "topo_order_commits.py" 2>&1 | grep execve

which outputted:

execve("/w/home.26/home/dhruvpatel97/topo-ordered-commits-test-suite/venv/bin/python3", ["python3", "topo_order_commits.py"], 0x7ffcdc13c220 /* 52 vars */) = 0

Since there are no calls to execve with Git, so my implementation did not invoke Git commands
'''''

# Recommended libraries.
import copy
import os
import sys
import re
import zlib
from collections import deque

# Note: This is the class for a doubly linked list.


class CommitNode:
    def __init__(self, commit_hash):
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()

# ============================================================================
# ======================== Auxiliary Functions ===============================
# ============================================================================


def in_git_directory() -> bool:
    """
    :rtype: bool

    Checks if `topo_order_commits.py` is inside a Git repository.
    """
    return os.path.isdir('.git')


def get_branch_hash(branch_name: str) -> str:
    """
    :type branch_name: str
    :rtype: str

    Returns the commit hash of the head of a branch.
    """
    with open(branch_name, "r") as f:
        return f.readline().strip()


def decompress_git_object(commit_hash: str) -> list[str]:
    """
    :type commit_hash: str
    :rtype: list

    Decompresses the contents of a git object and returns a
    list of the decompressed contents.
    """
    git_dir = get_git_directory()
    obj_path = os.path.join(
        git_dir, "objects", commit_hash[: 2], commit_hash[2:])
    with open(obj_path, "rb") as f:
        compressed = f.read()
        decompressed = zlib.decompress(compressed)
    return decompressed.decode().splitlines()

# ============================================================================
# =================== Part 1: Discover the .git directory ====================
# ============================================================================


def get_git_directory() -> str:
    """
    :rtype: str
    Returns absolute path of `.git` directory.
    """
    current_dir = os.getcwd()
    # go until we find a .git directory
    # Stop at root directory
    while current_dir != os.path.dirname(current_dir):
        git_dir = os.path.join(current_dir, ".git")
        if os.path.isdir(git_dir):
            return git_dir
        current_dir = os.path.dirname(current_dir)
    # exit / stderr
    sys.stderr.write("Not inside a Git repository")
    sys.exit(1)

# ============================================================================
# =================== Part 2: Get the list of local branch names =============
# ============================================================================


def get_branches(path: str) -> list[(str, str)]:
    """
    :type path: str
    :rtype: list[(str, str)]

    Returns a list of tupes of branch names and the commit hash
    of the head of the branch.
    """
    heads_path = os.path.join(path, "refs", "heads")
    branches = []

    if os.path.isdir(heads_path):
        for root, _, files in os.walk(heads_path):
            for file in files:
                file_path = os.path.join(root, file)
                commit_hash = get_branch_hash(file_path)
                branch_name = os.path.relpath(
                    file_path, heads_path).replace(os.sep, "/")
                branches.append((branch_name, commit_hash))

    return branches

# ============================================================================
# =================== Part 3: Build the commit graph =========================
# ============================================================================


def build_commit_graph(branches_list: list[tuple[str, str]]) -> dict[str, CommitNode]:
    """
    :type branches_list: list[tuple[str, str]]
    :rtype: dict[str, CommitNode]

    Iteratively builds the commit graph using BFS from the branch heads and returns 
    a dictionary mapping commit hashes to CommitNode objects.
    """

    graph = {}
    visited = set()
    stack = [commit_hash for _, commit_hash in branches_list]

    while stack:
        commit_hash = stack.pop()
        if commit_hash in visited:
            continue
        visited.add(commit_hash)

        if commit_hash not in graph:
            graph[commit_hash] = CommitNode(commit_hash)

        node = graph[commit_hash]

        try:
            lines = decompress_git_object(commit_hash)
        except FileNotFoundError:
            continue

        parent_hashes = []
        for line in lines:
            if line.startswith("parent "):
                parent_hash = line.split()[1]
                parent_hashes.append(parent_hash)

        node.parents = parent_hashes

        for parent_hash in parent_hashes:
            if parent_hash not in graph:
                graph[parent_hash] = CommitNode(parent_hash)
            graph[parent_hash].children.add(commit_hash)
            stack.append(parent_hash)

    return graph

# ============================================================================
# ========= Part 4: Generate a topological ordering of the commits ===========
# ============================================================================


def topo_sort(graph: dict[str, CommitNode], branch_heads: list[str]) -> list[str]:
    """
    Performs a topological sort on the commit graph, prioritizing parents 
    to maintain a logical traversal order.

    :type graph: dict[str, CommitNode]
    :type branch_heads: list[str]
    :rtype: list[str]
    """
    in_degree = {ch: len(node.children) for ch, node in graph.items()}
    next_choices = sorted([ch for ch, deg in in_degree.items() if deg == 0])
    order = []
    current = None
    while next_choices:
        chosen = None
        if current is not None:
            node = graph.get(current)
            if node and node.parents:
                preferred = node.parents[0]
                if preferred in next_choices:
                    chosen = preferred
                    next_choices.remove(preferred)
        if chosen is None:
            chosen = next_choices.pop(0)
        order.append(chosen)
        current = chosen
        node = graph.get(chosen)
        if node:
            for parent in node.parents:
                in_degree[parent] -= 1
                if in_degree[parent] == 0:
                    next_choices.append(parent)
        next_choices.sort()
    return order

# ============================================================================
# ===================== Part 5: Print the commit hashes ======================
# ============================================================================


def ordered_print(
    commit_nodes: dict[str, CommitNode],
    topo_ordered_commits: list[str],
    head_to_branches: dict[str, list[str]]
):
    """
    :type commit_nodes: dict[str, CommitNode]
    :type topo_ordered_commits: list[str]
    :type head_to_branches: dict[str, list[str]]

    Prints the commit hashes in the the topological order from the last
    step. Also, handles sticky ends and printing the corresponding branch
    names with each commit.
    """

    for i in range(len(topo_ordered_commits)):
        commit = topo_ordered_commits[i]
        line = commit
        if commit in head_to_branches:
            line += " " + " ".join(sorted(head_to_branches[commit]))
        print(line)

        if i < len(topo_ordered_commits) - 1:
            next_commit = topo_ordered_commits[i + 1]
            node = commit_nodes.get(commit)

            if node and node.parents and next_commit not in node.parents:
                sorted_parents = sorted(node.parents)
                sticky_end = " ".join(sorted_parents) + "="
                print(sticky_end)
                print("")  # Empty line

                next_node = commit_nodes.get(next_commit)
                if next_node and next_node.children:
                    sticky_start = "=" + " ".join(sorted(next_node.children))
                else:
                    sticky_start = "="
                print(sticky_start)

# ============================================================================
# ==================== Topologically Order Commits ===========================
# ============================================================================


def topo_order_commits():
    """
    Combines everything together.
    """
    # Check if you are inside a Git repository.
    if not in_git_directory():
        sys.stderr.write("Not inside a Git repository")
        sys.exit(1)
    # Part 1: Discover the .git directory.
    git_path = get_git_directory()
    # Part 2: Get the list of local branch names.
    branches = get_branches(git_path)
    # Part 3: Build the commit graph
    commit_graph = build_commit_graph(branches)
    # Generate a list of root `CommitNode`s
    branch_heads = list({commit for _, commit in branches})
    # Part 4: Generate a topological ordering of the commits in the graph.
    order = topo_sort(commit_graph, branch_heads)
    # Generate the head_to_branches dictionary showing which
    # branches correspond to each head commit
    head_to_branches = {}
    for branch, commit in branches:
        head_to_branches.setdefault(commit, []).append(branch)
    # Part 5: Print the commit hashes in the topological order.
    ordered_print(commit_graph, order, head_to_branches)


if __name__ == "__main__":
    topo_order_commits()
