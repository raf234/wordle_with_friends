import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import pandas as pd


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])

# comment out once ngrok issue solved
#client.chat_postMessage(channel='#bot_test', text='Hello, Wordle!')

BOT_ID = client.api_call("auth.test")['user_id']

df = pd.read_csv('wordle.csv')

"""
class UserData:
    def submissions(payLoad):
        event = payLoad.get('event', {})
        channel_id = event.get('channel')
        user_id = event.get('user')
        text = event.get('text')

        if user_id != None and BOT_ID != user_id and ':large_green_square::large_green_square::large_green_square::large_green_square::large_green_square:' in text.lower():
            if user_id in submissions:
                submissions[user_id] += 1
                df.append(submissions)
            else:
                submissions[user_id] = 1
                df.append(UserData(submissions))

"""


print(df)
# users = {}
submissions = {}
# time_to_submit = {}
# guesses = {}
message_counts = {}
welcome_messages = {}

class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': (
                'Welcome to the Wordle logger! \n\n'
                '*Submit your Wordle entry by reacting to this message!*'
            )
        }
    }

    DIVIDER = {'type': 'divider'}

    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.icon_emoji = ':robot_face:'
        self.timestamp = ''
        self.completed = False

    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'username': 'Welcome, PLAYER!',
            'icon_emoji': self.icon_emoji,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }

    def _get_reaction_task(self):
        checkmark = ':white_check_mark:'
        react_message = '*Successfully submitted Wordle entry!*'
        if not self.completed:
            checkmark = ':white_large_square:'
            react_message = '*React to this message!*'
        text = f'{checkmark} {react_message}'

        return {'type': 'section', 'text': {'type': 'mrkdwn', 'text': text}}


def send_welcome_message(channel, user):
    welcome = WelcomeMessage(channel, user)
    message = welcome.get_message()
    response = client.chat_postMessage(**message)
    welcome.timestamp = response['ts']

    if channel not in welcome_messages:
        welcome_messages[channel] = {}
    welcome_messages[channel][user] = welcome

@slack_event_adapter.on('message')
def message(payLoad):
    event = payLoad.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if user_id != None and BOT_ID != user_id:
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1

        if ':large_green_square::large_green_square::large_green_square::large_green_square::large_green_square:' in text.lower():
            send_welcome_message(f'@{user_id}', user_id)


@slack_event_adapter.on('reaction_added')
def reaction(payLoad):
    event = payLoad.get('event', {})
    channel_id = event.get('item', {}).get('channel')
    user_id = event.get('user')

    if f'@{user_id}' not in welcome_messages:
        return

    welcome = welcome_messages[f'@{user_id}'][user_id]
    welcome.completed = True
    welcome.channel = channel_id
    message = welcome.get_message()
    updated_message = client.chat_update(**message)
    welcome.timestamp = updated_message['ts']

@app.route('/message-count', methods=['POST'])
def message_count():
    data = request.form
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    message_count = message_counts.get(user_id, 0)
    client.chat_postMessage(channel=channel_id, text=f"Message: {message_count}")
    return Response(), 200

if __name__ == "__main__":
    app.run(debug=True)
