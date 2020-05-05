import numpy as np
from fractions import Fraction

from webscraping.website import CWebsite
from util.message import message
import util.utilities as ut
from templates.HTML_template_elements import make_html

default_link_name = 'href'
oddschecker_home = 'https://www.oddschecker.com/'

bet_amount = input('Insert your bet amount: ')

inplay = False
min_opp = 1.05
max_opp = 1.25

'''
ignore = [
    "Half Time Winning Margin",
    "To Score 2 Or More Goals",
    "To Score A Hat-Trick.",
    "Last Goalscorer",
    "To Score 3+ Goals",
    "To Score 4+ Goals",
    "Score After 6 Games",
    "To Win Set 1 And Win",
    "Not To Win A Set",
    "Set 1 Score Groups",
    "Score After 2 Games"
    ]
'''

class WebCrawler(object):
    def __init__(self, name="Oddschecker WebCrawler"):
        self.m_name = name
        self.all_result = []
        self.m_homepage = CWebsite(oddschecker_home, oddschecker_home, name="oddschecker_home")

    def run(self):
