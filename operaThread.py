from cgitb import text
import json
import logging
import os
import threading
import time
from flask import Flask, jsonify
from utils import Obj
from api import MessageApiClient

class MessageReceiveThread(threading.Thread):
    def __init__(self, message_api_client: MessageApiClient, open_id: str, message: Obj):
        threading.Thread.__init__(self)
        self.message_api_client = message_api_client
        self.open_id = open_id
        self.message = message
    
    def run(self):
        text_content = self.message.content
        msg_text = json.loads(text_content)
        print('msg text: ',msg_text)
        print(type(msg_text))
        print(msg_text.get('text'))

        if self.message.message_type == "text":
            with open('tempMessage.json', 'w', encoding='utf-8') as f:
                f.write(text_content)

            card_content = self.message_api_client.text_to_card(msg_text.get('text'))
            print('card_content: ',card_content)
            self.message_api_client.send_card_with_open_id(self.open_id, card_content)
        elif self.message.message_type == "post":
            with open('tempMessage.json', 'w', encoding='utf-8') as f:
                f.write(text_content)

            content_post = msg_text.get('text')
            if msg_text.get('text') == None:
                data = msg_text.get('content')
                str = ''
                for i in range(0, len(data)):
                    for j in range(0, len(data[i])):
                        if data[i][j].get('tag') == 'text':
                            str += data[i][j].get('text') + '\n'
                        elif data[i][j].get('tag') == 'a':
                            str += '[{}]'.format(data[i][j].get('text')) + '({})'.format(data[i][j].get('href')) + '\n' 
                        elif data[i][j].get('tag') == 'at':
                            str += data[i][j].get('user_id') + '\n' 
                print('str is: ' + str[:-2])
                content_post = str[:-2]

            card_content = self.message_api_client.text_to_card(content_post)
            print('card_content: ',card_content)
            self.message_api_client.send_card_with_open_id(self.open_id, card_content)
        elif self.message.message_type == "image":
            self.message_api_client.get_message_image(self.message.message_id, msg_text.get('image_key'))

            with open('tempMessage.json', 'w', encoding='utf-8') as f:
                f.write(text_content)

            card_content = self.message_api_client.image_to_card(msg_text.get('image_key'))

            self.message_api_client.send_card_with_open_id(self.open_id, card_content)        
        else:
            logging.warn("Other types of messages have not been processed yet")        


class ActionReceiveThread(threading.Thread):
    def __init__(self, message_api_client: MessageApiClient, open_id: str, option_content):
        threading.Thread.__init__(self)
        self.message_api_client = message_api_client
        self.open_id = open_id
        self.option_content = option_content

    def run(self):
        name, avatar = self.message_api_client.get_user_with_user_id(self.open_id)

        text_file = open('tempMessage.json', mode='r', encoding='utf-8')
        text_json = json.load(text_file)
        text = text_json.get('text')
        print(text)
        print(type(text))
        image_key = text_json.get('image_key')

        if text != None:
            html_path = 'feshu/card.html'

            chat_file = open('chatList.json', encoding='utf-8')
            chat = json.load(chat_file)['chat_list'][int(self.option_content)-1]
            chat_name = chat['chat_name']
            chat_url = chat['chat_url']

            html_file = self.message_api_client.message_var_to_html(html_path, name, avatar, text, chat_name, chat_url)

            temp_html_path = 'tempJson//card.html'
            self.message_api_client.write_file_to_path(html_file, temp_html_path)

            # get image width and height
            height = self.message_api_client.get_html_width_height(temp_html_path)

            # html to image
            output_path = 'images'
            image_name = '{}'.format(int(time.time())) + '.png'
            self.message_api_client.html_to_image(html_file, output_path, image_name, (375, height))

            # upload image to feishu
            image_path = output_path + '//' + image_name
            image_data = self.message_api_client.upload_image("message", image_path)
            print('image_data: ', image_data)

            # json serialization： dict to string
            image_content = json.dumps(image_data)
            print('image_content: ', image_content)

            # send image to user
            self.message_api_client.send_image_with_open_id(self.open_id, image_content)

            # delete temp image which used
            os.unlink(image_path)
        elif image_key != None:
            html_path = 'feshu/image.html'

            chat_file = open('chatList.json', encoding='utf-8')
            chat = json.load(chat_file)['chat_list'][int(self.option_content)-1]
            chat_name = chat['chat_name']
            chat_url = chat['chat_url']

            message_image_path = self.message_api_client.get_file_path(os.getcwd(), 'tempImage.png')

            html_file = self.message_api_client.message_var_to_html(html_path, name, avatar, message_image_path, chat_name, chat_url)

            temp_html_path = 'tempJson//image.html'
            self.message_api_client.write_file_to_path(html_file, temp_html_path)

            # get image width and height
            height = self.message_api_client.get_html_width_height(temp_html_path)

            # html to image
            output_path = 'images'
            image_name = '{}'.format(int(time.time())) + '.png'
            self.message_api_client.html_to_image(html_file, output_path, image_name, (375, height))

            # upload image to feishu
            image_path = output_path + '//' + image_name
            image_data = self.message_api_client.upload_image("message", image_path)
            print('image_data: ', image_data)

            # json serialization： dict to string
            image_content = json.dumps(image_data)
            print('image_content: ', image_content)

            # send image to user
            self.message_api_client.send_image_with_open_id(self.open_id, image_content)

            # delete temp image which used
            os.unlink(image_path)
        else:
            content_post = text_json.get('text')
            if text_json.get('text') == None:
                data = text_json.get('content')
                str = ''
                for i in range(0, len(data)):
                    for j in range(0, len(data[i])):
                        if data[i][j].get('tag') == 'text':
                            str += data[i][j].get('text') + '\n'
                        elif data[i][j].get('tag') == 'a':
                            str += '[{}]'.format(data[i][j].get('text')) + '({})'.format(data[i][j].get('href')) + '\n' 
                        elif data[i][j].get('tag') == 'at':
                            str += data[i][j].get('user_id') + '\n' 
                print('str is: ' + str[:-2])
                content_post = str[:-2]

            print(content_post)
            print(type(content_post))

            html_path = 'feshu/card.html'

            chat_file = open('chatList.json', encoding='utf-8')
            chat = json.load(chat_file)['chat_list'][int(self.option_content)-1]
            chat_name = chat['chat_name']
            chat_url = chat['chat_url']

            html_file = self.message_api_client.message_var_to_html(html_path, name, avatar, content_post, chat_name, chat_url)

            temp_html_path = 'tempJson//card.html'
            self.message_api_client.write_file_to_path(html_file, temp_html_path)

            # get image width and height
            height = self.message_api_client.get_html_width_height(temp_html_path)

            # html to image
            output_path = 'images'
            image_name = '{}'.format(int(time.time())) + '.png'
            self.message_api_client.html_to_image(html_file, output_path, image_name, (375, height))

            # upload image to feishu
            image_path = output_path + '//' + image_name
            image_data = self.message_api_client.upload_image("message", image_path)
            print('image_data: ', image_data)

            # json serialization： dict to string
            image_content = json.dumps(image_data)
            print('image_content: ', image_content)

            # send image to user
            self.message_api_client.send_image_with_open_id(self.open_id, image_content)

            # delete temp image which used
            os.unlink(image_path)
