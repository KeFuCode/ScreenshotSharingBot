#!/usr/bin/env python3.8

import json
import os
import logging
import time
import requests
from api import MessageApiClient
from event import ActionReceiveEvent, MessageReceiveEvent, UrlVerificationEvent, EventManager
from flask import Flask, jsonify
from dotenv import load_dotenv, find_dotenv
from operaThread import *

# load env parameters form file named .env
load_dotenv(find_dotenv())

app = Flask(__name__)

# load from env
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
VERIFICATION_TOKEN = os.getenv("VERIFICATION_TOKEN")
ENCRYPT_KEY = os.getenv("ENCRYPT_KEY")
LARK_HOST = os.getenv("LARK_HOST")

# init service
message_api_client = MessageApiClient(APP_ID, APP_SECRET, LARK_HOST)
event_manager = EventManager()

@event_manager.register("url_verification")
def request_url_verify_handler(req_data: UrlVerificationEvent):
    # url verification, just need return challenge
    if req_data.event.token != VERIFICATION_TOKEN:
        raise Exception("VERIFICATION_TOKEN is invalid")
    return jsonify({"challenge": req_data.event.challenge})

# 发送消息卡片
@event_manager.register("im.message.receive_v1")
def message_receive_event_handler(req_data: MessageReceiveEvent):
    sender_id = req_data.event.sender.sender_id
    open_id = sender_id.open_id
    message = req_data.event.message
    
    message_receive_thread = MessageReceiveThread(message_api_client, open_id, message)
    message_receive_thread.start()
    return jsonify({})

# 消息卡片交互
@event_manager.register("action_receive")
def message_receive_event_handler(req_data: ActionReceiveEvent):
    open_id = req_data.event.open_id
    option_content = req_data.event.action.option
    
    message_receive_thread = ActionReceiveThread(message_api_client, open_id, option_content)
    message_receive_thread.start()

    return jsonify({})


@app.errorhandler
def msg_error_handler(ex):
    logging.error(ex)
    response = jsonify(message=str(ex))
    response.status_code = (
        ex.response.status_code if isinstance(ex, requests.HTTPError) else 500
    )
    return response


@app.route("/", methods=["POST"])
def callback_event_handler():
    # init callback instance and handle
    event_handler, event = event_manager.get_handler_with_event(VERIFICATION_TOKEN, ENCRYPT_KEY)

    return event_handler(event)


if __name__ == "__main__":
    # init()
    app.run(host="0.0.0.0", port=3000, debug=True)
