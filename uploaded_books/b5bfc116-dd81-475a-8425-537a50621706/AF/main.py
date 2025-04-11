import os
import json

cnt = 0
idx = 1
file = open("./save.json", "r")
file = json.loads(file.read())

path = "./"
chapters = range(1, 13)
for chapter in chapters:
    chapter = str(chapter)

    chunks = len(os.listdir(f"{path}{chapter}"))

    for chunk in range(1, chunks + 1):
        temp_path = f"{path}{chapter}/{chunk}/state.json"

        if not os.path.exists(temp_path):
            print(temp_path, "dont exist")

        with open(temp_path, "r+") as state:
            x = state.read()
            temp = json.loads(x)
            # print(temp)
            title = temp["scene_title"]

            # for idx in range(2, len(file) + 1):
            if file[idx]["description"] == title:
                temp["image"] = file[idx]["url"]
                idx += 1
            state.seek(0)  # Move to the beginning
            state.write(json.dumps(temp, indent=2))
            state.truncate()  # Remove any leftover old content
