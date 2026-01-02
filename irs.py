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
    MAIN = f'<p>Click <a herf={url_for("index")}>here</a> to main menu.'
    html = 'Database is reset successfully.' + MAIN
    return html

