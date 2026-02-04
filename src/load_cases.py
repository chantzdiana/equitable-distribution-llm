"""
Load divorce case opinions from text files.
"""
# TODO: Write a function that loads all .txt files from the data folder and returns their contents.

from pathlib import Path

def load_cases():
    data_path = Path("data/raw")
    cases = []
    for file in data_path.glob("*.txt"):
        with open(file, 'r') as f:
            cases.append(f.read())
    return cases

