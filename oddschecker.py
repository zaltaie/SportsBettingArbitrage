import requests
from bs4 import BeautifulSoup

from message import message
import util as ut
from webscraping.tag import CTag

DEFAULT_HEADERS = {'User-Agent':'Mozilla/5.0'}
DEFAULT_LINK_ATTR_NAME = "href"

class CWebsite():
    def __init__(self, url, home_url, headers=DEFAULT_HEADERS, name="Website"):
        if not isinstance(url, str):
            message.logError("Given URL is not a string instance.",
                             "CWebsite::__init__")
            ut.exit(0)
        if not isinstance(home_url, str):
            message.logError("Given home URL is not a string instance.",
                             "CWebsite::__init__")
            ut.exit(0)

        response = requests.get(url, headers=headers)

        self.m_url = url
        self.m_home_url = home_url
        self.m_headers = headers
        self.m_websoup = BeautifulSoup(response.text, "html.parser")
        self.m_name = name

    def getAttrs(self, class_names, link_attr_name):
        tags = self.getClasses(class_names)
        ret = []
        for t in tags:
            if t.hasAttr(link_attr_name):
                ret.append(t.getAttr(link_attr_name))
        return ret
