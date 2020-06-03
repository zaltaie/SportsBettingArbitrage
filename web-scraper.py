import numpy as np
from fractions import Fraction

from oddschecker import CWebsite
from message import message
import util as ut
#from templates.HTML_template_elements import make_html

DEFAULT_LINK_NAME = 'href'
ODDSCHECKER_HOME = 'https://www.oddschecker.com/'

BET_AMOUNT = input('Insert your bet amount: ')

INPLAY = False
MIN_OPP = 1.05
MAX_OPP = 1.25

'''
IGNORE = [
    "Half Time Winning Margin",
    "To Score 2 Or More Goals",
    "To Score A Hat-Trick.",
    "Last Goalscorer",
    "To Score 3+ Goals",
    "To Score 4+ Goals",
    "Score After 6 Games",
    "To Win Set 1 And Win",
    "Not Tgit inito Win A Set",
    "Set 1 Score Groups",
    "Score After 2 Games"
    ]
'''

class WebCrawler(object):
    def __init__(self, name="Oddschecker WebCrawler"):
        self.m_name = name
        self.all_result = []
        self.m_homepage = CWebsite(ODDSCHECKER_HOME, ODDSCHECKER_HOME, name="oddschecker_home")

    def run(self):
        print('test') 
