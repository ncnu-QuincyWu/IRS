# Interactive Response System
from flask import Flask, request, abort, render_template
from flask import make_response, url_for, redirect
from cryptography.fernet import Fernet
import os
import json
import sqlite3

app = Flask(__name__)
VERSION = 'v0.3'
DB_FILENAME = 'irs.db'
key = b'GrCPlx9BTpiCdU2bacCk5Ml7aX7fYxEPD9ceNAEFdrY='
fernet = Fernet(key)
currentQuestion = 0
firstNote = {}

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, PostbackEvent, TextMessage, ImageMessage,
    TextSendMessage, ImageSendMessage, FlexSendMessage,
)

# Channel access token
CHANNEL_ACCESS_TOKEN=os.getenv('CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
# Channel Secret
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    return 'OK'

@handler.add(PostbackEvent)
def handle_postback(event):
    ''' Postback allows you to send data to your Flask program
        without starting a web browser. '''
    postback_data = event.postback.data  # ← Here: "sid=123&answer=no"
    # Parse the data (e.g., as query parameters)
    import urllib.parse
    params = urllib.parse.parse_qs(postback_data)
    sid = params.get('sid', [''])[0]
    answer = params.get('answer', [''])[0] 
    print(sid, answer)
    #reply_text = f"Received postback: {postback_data}"
    #print(reply_text)
    #line_bot_api.reply_message(
    #    event.reply_token,
    #    TextSendMessage(text=reply_text)
    #)

# Slash Commands
SLASH_COMMANDS = ['/HELP - Show this message',
    '/VERSION - Show version',
    '/ENROLL stuid nickname - Enroll to the class',
    '/ENROLLNEW stuId stuName stuEmail nickname - If you are not on the pre-enroll list',
    '/DISENROLL stuId - Disenroll from that stuId',
    '/LIST - List enrolled students',
    '/MYNOTE - Show the notes which I took',
    '/WHOAMI - Show my stuId, StuName, and nickname',
    ]

def slashList(user_id):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'SELECT stuId, stuName, lineId, nickname FROM Student ' \
           f'WHERE length(lineId) > 0'
    cursor.execute(stmt)
    rows = cursor.fetchall()
    if len(rows) == 0:
        result = 'No student enrolled yet.'
    else:
        print('[DEBUG]', rows[0][2], user_id, rows[0][2]==user_id)
        #result = '\n'.join(list(map(lambda x: f'{x[0]} {x[1]} {x[3]}', rows)))
        result = '\n'.join(list(map(lambda x: \
            f'{x[0]} {x[1]} {x[3]} (you)' if x[2] == user_id \
            else f'{x[0]} {x[1]} {x[3]}', rows)))
    cursor.close()
    conn.close()
    return result

def slashWhoami(user_id):
    return "Not implemented yet."

def slashHelp(user_id):
    return '\n'.join(SLASH_COMMANDS)

def slashVersion(user_id):
    return VERSION

def slashMynote(user_id):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'SELECT time, content FROM Answer WHERE lineId = "{user_id}" ' \
           f'AND qid = 0 AND date = DATE("NOW")'
    cursor.execute(stmt)
    rows = cursor.fetchall()
    result = '\n'.join(list(map(lambda x: f'{x[0]} {x[1]}', rows)))
    cursor.close()
    conn.close()
    return result

def slashEnroll(user_id, stuId, nickname):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'SELECT * FROM Student WHERE lineId = "{user_id}" ' \
           f' AND stuId != "{stuId}"'
    cursor.execute(stmt)
    rows = cursor.fetchall()
    if len(rows) > 0:   # That lineId has enrolled
        result = f'You have enrolled with stuId "{rows[0][0]}". ' \
            'If that was a mistake, please "/DISENROLL stuId".'
    else:
        stmt = 'SELECT stuId, stuName, stuEmail, lineId FROM Student ' \
              f'WHERE stuId = "{stuId}"'
        cursor.execute(stmt)
        row = cursor.fetchone()
        if row is None:
            result = f'No such stuId ({stuId}). ' \
                'If you want to register a new student not on the list, ' \
                'use "/ENROLLNEW stuId stuName stuEmail nickname".'
        else: # stdId is on the roster
            stuId,stuName,stuEmail,lineId = row
            if lineId is None or lineId == '':
                # This lineId is not associated yet.
                stmt = f'UPDATE Student SET lineId = "{user_id}", ' \
                       f'nickname = "{nickname}" WHERE stuId = "{stuId}"'
                cursor.execute(stmt)
                conn.commit()
                result =  f"{stuId} {stuName} enrolled."
            else: # Update his nickname
                if lineId == user_id:
                    stmt = f'UPDATE Student SET ' \
                           f'nickname = "{nickname}" WHERE stuId = "{stuId}"'
                    cursor.execute(stmt)
                    conn.commit()
                    result =  f"{stuId} {stuName} updated with nickname {nickname}."
                else:
                    result = f'[Error] The student ID {stuId} was enrolled ' \
                              'by someone else.'
    cursor.close()
    conn.close()
    return result

def slashEnrollnew(user_id, stuId, stuName, stuEmail, nickname):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'SELECT * FROM Student WHERE lineId = "{user_id}"' 
    cursor.execute(stmt)
    row = cursor.fetchone()
    if row is not None:
        result = f'You have enrolled with stuId "{row[0]}".'
    else:
        stmt = f'SELECT * FROM Student WHERE stuId = "{stuId}"'
        row = cursor.fetchone()
        if row is not None:
            result = f'The stuid "{stuId}" exists. ' \
                f'Please use "/ENROLL stuid nickname".'
        else: # Insert a new record
           stmt = f'INSERT INTO ' \
               'Student(stuId, stuName, stuEmail, lineId, nickname)' \
               f'VALUES("{stuId}", "{stuName}", ' \
               f'"{stuEmail}", "{user_id}", "{nickname}")'
           cursor.execute(stmt)
           conn.commit()
           result = f'Create a new entry for {stuId} {stuName}.'
    cursor.close()
    conn.close()
    return result

def slashDisenroll(user_id, stuId):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'SELECT * FROM Student WHERE lineId = "{user_id}"' 
    cursor.execute(stmt)
    row = cursor.fetchone()
    if row is None:
        result = "You haven't enrolled yet."
    else:
        stmt = f'SELECT * FROM Student WHERE lineId = "{user_id}" ' \
           f'AND stuId = "{stuId}"'
        cursor.execute(stmt)
        row = cursor.fetchone()
        if row is None:
            result = 'You cannot disenroll for other people.'
        else: # Correct lineId and stuId
            stuName = row[1]
            stmt = f'UPDATE Student SET lineId = "", nickname="" ' \
                   f'WHERE stuId = "{stuId}"'
            print('[DEBUG]', stmt)
            cursor.execute(stmt)
            conn.commit()
            result = f"{stuId} {stuName} disenrolled."
    cursor.close()
    conn.close()
    return result
    
def unknownCommand():
    return 'Unknown command.\n' \
        'Please use "/HELP" to see available slash commands.'

def parseSlashCommand(line):
    #print('DEBUG: line=', line)
    line = line.split('-')[0] # delete remarks
    cmd, *args = line.split()
    functionName = 'slash' + cmd.capitalize()
    return {cmd: { "arguments": args, "function": eval(functionName) } }
    
def parseCommands(lines):
    d = {}
    for line in lines:
        d = {**d, **parseSlashCommand(line[1:])}
    return d

dSlashCommands = parseCommands(SLASH_COMMANDS)

def handleSlashCommand(user_id, s):
    ' This handles the command typed by the user, with the leading / removed. '
    cmd, *args = s[1:].split()
    #print('[DEBUG] cmd=', cmd)
    cmd = cmd.upper()
    if cmd in dSlashCommands:
        if len(args) == len(dSlashCommands[cmd]['arguments']):
            result = dSlashCommands[cmd]['function'](user_id, *args)
        else:
            result = 'Incorrect syntax.  Please use "/HELP" ' \
                f'to see the number of arguments of /{cmd}.'
    else:
        result = unknownCommand()
    return result

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    user_id = event.source.user_id
    global currentQuestion
    global firstNote
    # TODO: logger.debug(user_id, msg)
    if msg[0] == '/':
        result = handleSlashCommand(user_id, msg)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=result))
    else:
        if firstNote.get(user_id, True):
            if currentQuestion == 0:
                result = '[Reminder] It is not a quick poll right now. ' \
                    'Messages which you write outside sessions of quick ' \
                    'polls will saved as your personal notes. ' \
                    'You can retrieve them by "/MYNOTE". ' \
                    'Your are encouraged to take notes on important ' \
                    'keywords, ideas, or your doubts any time in the class.'
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=result))
                firstNote[user_id] = False
        # Store the msg into TABLE Answer
        conn = sqlite3.connect(DB_FILENAME)
        cursor = conn.cursor()
        stmt = f'INSERT INTO Answer VALUES({currentQuestion}, "{user_id}", date("now"), time("now","localtime"), "{msg}")'
        cursor.execute(stmt)
        conn.commit()
        cursor.close()
        conn.close()
        # Silently take notes without returning any message
    return # Function Ends here

def broadcast_flex():
    flex_json_string = r'''{
      "type": "bubble", 
      "footer": {
        "type": "box",
        "layout": "vertical",
        "contents": [
          {
            "type": "button",
            "style": "primary",
            "action": {
              "type": "postback",
              "label": "YES",
              "data": "sid=123&answer=yes",
              "displayText": "Yes"
            }
          },
          {
            "type": "button",
            "style": "secondary",
            "action": {
              "type": "postback",
              "label": "NO",
              "data": "sid=123&answer=no",
              "displayText": "No"
            }
          }
        ]
      }
    }'''
    flex_msg = FlexSendMessage(
        alt_text='Flex Message',
        contents=json.loads(flex_json_string))
    line_bot_api.reply_message(
            event.reply_token,
            flex_msg)

@app.route('/')
def index():
    userId = request.cookies.get('userId', '')
    print('[DEBUG]', userId)
    if userId != '' and authenticated(userId):  # short-cuircuit
        return render_template('index.html')
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        html = '''<form method=post><table>
        <tr><td>Username</td> 
            <td><input type=text name=username></td></tr>
        <tr><td>Password</td>
            <td><input type=password name=password></td></tr>
        <tr><td></td><td><input type=submit></td></tr>
        </table>
        </form>'''
        return html
    else:       # POST
        pw = request.values.get('password', '') # username doesn't matter
        resp = make_response(redirect(url_for('index')))
        resp.set_cookie('userId', fernet.encrypt(pw.encode()).decode())
        return resp

def authenticated(userId):
    USERID = b'gAAAAABpZyCJXeOHnIOVLujp0tiqnM2g4AA6v06Eg7kRZtIHHs6avKR340EH7gSHM8yBOsuxG3RSF1DLNuKDE1p0z-xmYwWp4Q==' # 'ncnu2026'
    # Same text will be encrypted into different ciphertexts.
    c = fernet.decrypt(USERID).decode()
    if c == fernet.decrypt(userId).decode():
        return True
    else:
        return False

@app.route('/reset')
def reset():
    with open('init.sql') as f:
        commands = f.read()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    for stmt in commands.split(';'):
        cursor.execute(stmt)
    cursor.close()
    conn.close()
    MAIN = f'<p>Click <a href={url_for("index")}>here</a> to main menu.'
    html = 'Database is reset successfully.' + MAIN
    return html

@app.route('/inputStudent')
def inputStudent():
    html = '''<form method=post action=importStudent>
    <textarea name=studentList rows=10 cols=50></textarea>
    <input type=submit>
    <ol>
    <li>Please list students in CSV format.
    <li>Each line consists of three fields: (1) student_id (2) name (3) email,
    separated by commas <font color=red>(not blanks)</font>.
    <li>e.g., "114001,Alice,alice@ms2.kghs.kg.edu.tw"
    </ol>'''
    return html

@app.route('/insertStudent', methods=['POST'])
def insertStudent():
    students = request.values['studentList'].split()
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    for student in students:
        sid, name, email = student.split(',')
        stmt = 'INSERT INTO Student(stuId, stuName, stuEmail) ' \
            f'VALUES("{sid}", "{name}", "{email}")'
        print(stmt)
        cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()
    MAIN = f'<p>Click <a href={url_for("index")}>here</a> to main menu.'
    html = 'Students are imported successfully.' + MAIN
    return html

@app.route('/listStudents')
def listStudents():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = "SELECT * FROM Student"
    cursor.execute(stmt)
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('listStudents.html', students=students)

@app.route('/question/list')
def listQuestions():
    ' List all questions'
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = "SELECT * FROM Question"
    cursor.execute(stmt)
    questions = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('question.html', questions=questions,
        qid=currentQuestion)

@app.route('/question/add', methods=['POST'])
def addQuestion():
    content = request.values['question']
    print('[DEBUG]', content)
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = 'INSERT INTO Question(content, status) ' \
          f'VALUES("{content}", 0)'
    cursor.execute(stmt)
    conn.commit()
    cursor.close
    conn.close()
    return redirect(url_for('listQuestions'))

@app.route('/question/delete/<int:n>')
def delQuestion(n):
    ' Delete a question '
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = f'DELETE FROM Question WHERE qid = {n}'
    cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('listQuestions'))

@app.route('/question/edit/<int:n>')
def editQuestion(n):
    ' [TODO] Edit a question'
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = "SELECT * FROM Question"
    cursor.execute(stmt)
    cursor.close()
    conn.close()
    return ' [TODO] Edit a question'

@app.route('/question/open/<int:n>')
def openQuestion(n):
    ' TODO: broadcast the question to all students '
    global currentQuestion
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = 'UPDATE Question SET status = 1, startTime = datetime("now") ' \
          f'WHERE qid = {n}'
    print('[DEBUG]', stmt)
    cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()
    currentQuestion = n
    return redirect(url_for('listQuestions'))

@app.route('/question/close/<int:n>')
def closeQuestion(n):
    global currentQuestion
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = 'UPDATE Question SET status = 2, endTime = datetime("now") ' \
          f'WHERE qid = {n}'
    print('[DEBUG]', stmt)
    cursor.execute(stmt)
    conn.commit()
    cursor.close()
    conn.close()
    currentQuestion = 0
    return redirect(url_for('listQuestions'))

@app.route('/question/view/<int:n>')
def viewQuestion(n):
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = 'SELECT content FROM Question ' \
          f'WHERE qid = {n}'
    #print('[DEBUG]', stmt)
    cursor.execute(stmt)
    question = cursor.fetchone()[0]
    stmt = 'SELECT content, lineId FROM Answer ' \
          f'WHERE qid = {n}'
    cursor.execute(stmt)
    answers = cursor.fetchall()
    html = f'<h1>Quick Poll: {question}</h1>\n'
    html += '<table border>\n'
    html += '<tr><th>Answer</th> <th>No Response Yet</th></tr>\n'
    html += '<tr><td><ul>\n'
    provideAnswer = {}
    for content, user_id in answers:
        html += f'<li>{content}</li>\n'
        provideAnswer[user_id] = True
    html += '</ul></td><td><ol>\n'
    stmt = 'SELECT stuId, stuName, lineId FROM Student ' \
           'WHERE length(lineId) > 0'
    cursor.execute(stmt)
    students = cursor.fetchall()
    for student in students:
        lineId = student[2]
        if lineId not in provideAnswer:
            html += f'<li>{student[0]} {student[1]}</li>\n'
    html += '</ol></td></tr>\n'
    html += '</table>\n'
    cursor.close()
    conn.close()
    #raise ValueError('[DEBUG]')
    return html

