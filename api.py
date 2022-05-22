#! /usr/bin/env python3.8
import json
import os
import logging
from webbrowser import get
import requests
from html2image import Html2Image
from requests_toolbelt import MultipartEncoder
from cherrypy import expose
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")

# const
TENANT_ACCESS_TOKEN_URI = "/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URI = "/open-apis/im/v1/messages"
GET_USER_URI = "/open-apis/contact/v3/users"
IMAGE_URI = "/open-apis/im/v1/images"

class MessageApiClient(object):
    def __init__(self, app_id, app_secret, lark_host):
        self._app_id = app_id
        self._app_secret = app_secret
        self._lark_host = lark_host
        self._tenant_access_token = ""

    @property
    def tenant_access_token(self):
        return self._tenant_access_token

    def get_user_with_user_id(self, user_id):
        return self.get("open_id", user_id)

    def get(self, user_id_type, user_id):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}/{}?user_id_type={}".format(
            self._lark_host, GET_USER_URI, user_id, user_id_type
        )
        headers = {
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        resp = requests.get(url=url, headers=headers)
        MessageApiClient._check_error_response(resp)

        data = resp.json().get('data')

        name = data.get('user').get('name')
        avatar = data.get('user').get('avatar').get('avatar_72')

        return name, avatar

    def get_html_width_height(self, html_path):
        options = webdriver.ChromeOptions()
        options.add_argument("disable-gpu")
        options.add_argument("headless")
        options.add_argument("no-default-browser-check")
        options.add_argument("no-first-run")
        options.add_argument("no-sandbox")
        options.add_argument('lang=zh_CN.UTF-8')
        options.add_argument('--start-maximized')

        chrome_driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)

        html_local_path = os.getcwd() + '//' + html_path
        chrome_driver.get("file:///" + html_local_path)
        
        # width = chrome_driver.execute_script("return document.getElementById('root').clientWidth;")
        height = chrome_driver.execute_script("return document.getElementById('root').clientHeight;")
   
        chrome_driver.quit()
        chrome_driver.service.stop()
        
        return height

    @expose
    def message_var_to_html(self, html_path, user_name, user_avatar, message_content, chat_name, chat_url):
        file = open(html_path, encoding='UTF-8')
        
        path_prefix = os.getcwd()
        bgBottom, bgTop, card, icon, logo1, logo2 = self.html_config_file_path(path_prefix)
        
        chat_url = self.get_local_file_path(chat_url)

        html_file = file.read().format(bgBottom=bgBottom, bgTop=bgTop, card=card, icon=icon, logo1=logo1, logo2=logo2, name=user_name, avatar=user_avatar, content=message_content, chat=chat_name, share=chat_url)
        return html_file

    def html_config_file_path(self, path_prefix):
        bgBottom = self.get_file_path(path_prefix, 'bgBottom.svg')
        bgTop = self.get_file_path(path_prefix, 'bgTop.svg')
        card = self.get_file_path(path_prefix, 'card.svg')
        icon = self.get_file_path(path_prefix, 'icon.png')
        logo1 = self.get_file_path(path_prefix, 'logo1.png')
        logo2 = self.get_file_path(path_prefix, 'logo2.png')
        return bgBottom, bgTop, card, icon, logo1, logo2

    def get_file_path(self, path_prefix, file_name):
        path_prefix = path_prefix + '//feshu//'
        file_path = path_prefix + file_name
        return file_path

    def get_local_file_path(self, path):
        path = os.getcwd() + '//' + path
        return path

    def write_file_to_path(self, new_file, file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_file)

    def html_to_image(self, html_file, output_path, image_name, image_size):
        hti = Html2Image(browser='chrome', output_path=output_path)

        hti.screenshot(html_str=html_file, save_as=image_name, size=image_size)

    def upload_image(self, image_type, image_path):
        self._authorize_tenant_access_token()
        url = "{}{}".format(
            self._lark_host, IMAGE_URI
        )
        
        form = {
            'image_type': image_type,
            'image': (open(image_path, 'rb'))
        }
        multi_form = MultipartEncoder(form)
        
        headers = {
            'Content-Type': multi_form.content_type,
            'Authorization': "Bearer " + self.tenant_access_token,
        }

        resp = requests.post(url=url, headers=headers, data=multi_form)

        data = resp.json().get('data')

        MessageApiClient._check_error_response(resp)

        return data

    def get_message_image(self, message_id, image_key):
        self._authorize_tenant_access_token()

        url = "	https://open.feishu.cn/open-apis/im/v1/messages/{}/resources/{}".format(
            message_id, image_key
        )
        
        headers = {
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        params = {
            "type": "image",
        }

        # url = 'https://open.feishu.cn/open-apis/im/v1/messages/om_aa0944122e2ec23545d9a93df0ceec02/resources/img_v2_98f3923d-3351-4017-8156-ee34d92196bj?type=image'
        # url = 'https://open.feishu.cn/open-apis/im/v1/messages/:message_id/resources/:file_key?message_id=om_0448e5d43a4e00d9dc6a566eac496679&file_key=img_v2_5cc842fe-4b2b-488d-a65c-8ac5cdbfb25g&type=image'

        resp = requests.get(url=url, params=params, headers=headers)
        
        # print(resp.content)
        with open('feshu/tempImage.png', 'wb') as f:
            f.write(resp.content)

    def send_card_with_open_id(self, open_id, content):
        self.send("open_id", open_id, "interactive", content)

    def send_image_with_open_id(self, open_id, content):
        self.send("open_id", open_id, "image", content)

    def text_to_card(self, content):
        with open("chatCard.json", "r", encoding="utf-8") as load_file:
            card_content = json.load(load_file)

        # card_content['elements'][1]['content'] = card_content['elements'][1]['content'].format(content)
        card_content['elements'][1]['content'] = content
        card_content = json.dumps(card_content)

        return card_content

    def image_to_card(self, content):
        with open("chatImageCard.json", "r", encoding="utf-8") as load_file:
            card_content = json.load(load_file)

        card_content['i18n_elements']['zh_cn'][1]['img_key'] = card_content['i18n_elements']['zh_cn'][1]['img_key'].format(content)
        card_content = json.dumps(card_content)

        return card_content

    def send_text_with_open_id(self, open_id, content):
        self.send("open_id", open_id, "text", content)

    def send(self, receive_id_type, receive_id, msg_type, content):
        # send message to user, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/im-v1/message/create
        self._authorize_tenant_access_token()
        url = "{}{}?receive_id_type={}".format(
            self._lark_host, MESSAGE_URI, receive_id_type
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.tenant_access_token,
        }

        req_body = {
            "receive_id": receive_id,
            "content": content,
            "msg_type": msg_type,
        }

        resp = requests.post(url=url, headers=headers, json=req_body)
        MessageApiClient._check_error_response(resp)

    def send_ok(self, open_id, content):
        self.send("open_id", open_id, "text", content)

    def _authorize_tenant_access_token(self):
        # get tenant_access_token and set, implemented based on Feishu open api capability. doc link: https://open.feishu.cn/document/ukTMukTMukTM/ukDNz4SO0MjL5QzM/auth-v3/auth/tenant_access_token_internal
        url = "{}{}".format(self._lark_host, TENANT_ACCESS_TOKEN_URI)
        req_body = {"app_id": self._app_id, "app_secret": self._app_secret}
        response = requests.post(url, req_body)
        MessageApiClient._check_error_response(response)
        self._tenant_access_token = response.json().get("tenant_access_token")

    @staticmethod
    def _check_error_response(resp):
        # check if the response contains error information
        if resp.status_code != 200:
            resp.raise_for_status()
        response_dict = resp.json()
        code = response_dict.get("code", -1)
        if code != 0:
            logging.error(response_dict)
            raise LarkException(code=code, msg=response_dict.get("msg"))


class LarkException(Exception):
    def __init__(self, code=0, msg=None):
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return "{}:{}".format(self.code, self.msg)

    __repr__ = __str__
