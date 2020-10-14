from framegram import *
from os.path import dirname, realpath
import json


EXAMPLE_FILE=f"{dirname(realpath(__file__))}/example_diagram.json"
ETHERNET_HEADER_SIZE=8*18


def test_loading_struct_from_file():
    _, root = read_struct_from_file_path(EXAMPLE_FILE)
    structs = root.children

    assert structs[0].name == "Ethernet Frame"
    assert structs[0].num_bits() == ETHERNET_HEADER_SIZE
    assert structs[0].children[2].children[1].children[0].name == "PCP"
    assert structs[0].children[2].children[1].children[0].num_bits() == 3

def test_output_filename():
    assert output_filename("example_diagram.txt") == "example_diagram.png"
    assert output_filename("a/example_diagram.txt") == "a/example_diagram.png"
    assert output_filename("a/b/c/d/example_diagram.txt") == "a/b/c/d/example_diagram.png"
    assert output_filename("a/b/c/d/example_diagram.txt.txt.txt") == "a/b/c/d/example_diagram.txt.txt.png"

def test_leafvals():
    _, root = read_struct_from_file_path(EXAMPLE_FILE)

    expected = [
        ["DE", "AD", "BE", "EF", "CC", "DD"],
        ["DE", "AD", "BE", "EF", "CC", "DD"],
        [],
        [],
        [],
        [],
        [],
    ]

    shares = [
        1/3,
        1/3,
        1/9,
    ]

    assert len(expected) == len(root.leafvals())

    for a, b in zip(expected, root.leafvals()):
        assert a == b

    for a, b in zip(shares, root.leafshares()):
        assert a == b

    assert sum(root.leafshares()) == 1.0

