from flask import Flask, request, abort, render_template, url_for
import os
import json
import sqlite3

app = Flask(__name__)
DB_FILENAME = 'irs.db'

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
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
    return render_template('index.html')

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

@app.route('/listStudent')
def listStudent():
    conn = sqlite3.connect(DB_FILENAME)
    cursor = conn.cursor()
    stmt = "SELECT * FROM Student"
    cursor.execute(stmt)
    html = '''<table border>\n
        <tr><th>stuId <th>stuName <th>stuEmail <th>nickname <th>photoUrl\n'''
    for row in cursor.fetchall():
        stuId,stuName,stuEmail,lineId,nickname,photoUrl = row
        html += f'<tr><td>{stuId} <td>{stuName} <td>{stuEmail}' \
                f'<td>{nickname} <td><img src={photoUrl} width=50>\n'
    html += '</table>\n'
    return html
