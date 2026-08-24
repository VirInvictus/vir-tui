import re
with open("src/vir_tui/__init__.py", "r") as f:
    text = f.read()

text = re.sub(r'# for backwards compatibility', '', text)

with open("src/vir_tui/__init__.py", "w") as f:
    f.write(text)

