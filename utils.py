from typing import Optional
import json
import ast


## Pretty Printers


def printl(ls: list, space: int = 1) -> None:
    line_breaks = "\n"
    for _ in range(space):
        line_breaks += "\n"

    for i in ls:
        print(i, end=line_breaks)


def printd(dir: dict, space: int = 1) -> None:
    scape = "\n"
    for _ in range(space):
        scape += "\n"
    for key, value in dir.items():
        print(f"{key} : {value}", end=scape)


def printt(tou: tuple) -> None:
    for i in tou:
        print("---------------------------" + i[0] + "---------------------------")
        print(i[1])


###------------------------------------------------------------------------------------


## Readers


def read_json(raw_json: str) -> Optional[dict]:
    try:
        data = json.loads(raw_json)
        return data
    except json.JSONDecodeError as e:
        print(f"Error: {e}")
        print("\n\n\n" + raw_json)


def read_list(raw_text: str) -> Optional[list]:
    try:
        lst = ast.literal_eval(raw_text)
        return lst
    except ValueError as e:
        print(f"Error: {e}")
        print("\n\n\n" + raw_text)
        return None
