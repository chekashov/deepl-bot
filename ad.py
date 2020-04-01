#!/usr/local/bin/python3
# Copyright 2020 Egor Chekashov
# Auto-deploy script v0.5

import subprocess
import cgi
import random

# Prepare
# TODO: Make newline handling better, remove replace logic
def sproc(shell, replace=""):
    r = subprocess.check_output(shell, shell=True)
    r = r.decode('utf-8').replace("\n", replace)
    return r

def send_msg(msg):
# TODO: Implement raw string for better readability
    msg = msg.replace('"', '\\"').replace("'", "\'\"\'\"\'")
    sproc(f"osascript                                           \
            -e 'tell application \"Keyboard Maestro Engine\"'   \
            -e 'setvariable \"cafMessage\" to \"{msg}\"'        \
            -e 'ignoring application responses'                 \
            -e 'do script \"_cafMessage\"'                      \
            -e 'end ignoring' -e 'end tell'")

try:
    fs = cgi.FieldStorage()
except:
    fs = ""
debug = fs["debug"].value if "debug" in fs else ""

cwd = sproc("echo ${PWD##*/}")
gh = "https://github.com/chekashov" #without trailing slash
commit = ""

# HTML & CSS
br = "<br>"

styles = '''
@import url('https://fonts.googleapis.com/css\
?family=Press+Start+2P&display=swap');

html {
    font-family: 'Press Start 2P';
    font-size: 1vmax;
    color: #596275;
}

body {
    background-color: #18222D;
    color: #fff;
    padding: 2vmax;
}

h1 {
    margin: 0 0 1.5vmax 0;
    color: #f5cd79;
}

h1::before {
    content: '>';
    color: #f78fb3;
}

span {
    display: block;
    margin: 0 0 3vmax 2vmax;
    line-height: 1.5em;
}
'''.strip()

def h1(content):
    return f"<h1>{content}</h1>"

def span(content):
    return f"<span>{content}</span>"

def html_open(title):
    print("Content-type: text/html\n")
    print(f'''
<!DOCTYPE html>
<html>
<head>
<style>
{styles}
</style>
<meta name="robots" content="noindex">
<title>{title}</title>
</head>
<body>
'''.strip())

def html_close():
    print (f'''
</body>
</html>
'''.strip())

if debug == "69":
    html_open(f"Auto Update - {cwd}")

# Commands
cmd = [
    "echo ${PWD##*/}",
    "/usr/bin/git status",
    "/usr/bin/git fetch --all",
    "/usr/bin/git reset --hard origin/master"
]

# TODO: Add <br> only for debug
for i in cmd:
    output = sproc(i, br)
    if i == cmd[-1]:
        commit = output.replace("HEAD is now at ","")
    if debug == "69":
        print(h1(i))
        print(span(output))

if debug == "69":
    html_close()
else:
    print("Content-Type: application/json\n")
    print("It's alright, darling")

if "nothing to commit, working tree clean" in sproc(cmd[1]):
    mood = [
        "Fresh code!", "Sweet updates!", "Nice job!",
        "That's all you've done?", "How dare you!",
        "Special delivery!", "Copy that, sir!"
    ]
    msg = f'💾 <b><a href="{gh}/{cwd}">{cwd}</a> is deployed</b>\n'
    msg += f"{random.choice(mood)} We're here:\n"
    # TODO: Move replace inside send_msg()
    commit = commit.replace(br, "").replace(">", "").replace("<", "")
    msg += "<code>" + commit.split(' ', 1)[1] + "</code>"
    send_msg(msg)
else:
    msg = f'💾 <b><a href="{gh}/{cwd}">{cwd}</a> is not deployed</b>\n'
    msg += "Something went wrong"
    send_msg(msg)
