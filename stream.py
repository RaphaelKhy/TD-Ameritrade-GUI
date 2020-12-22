from tda.auth import easy_client
from tda.client import Client
from tda.streaming import StreamClient
import sys
import fileinput
import asyncio
import json
import config
import get_token
import pandas as pd
import csv
from tkinter import *
import threading
import random
import queue

my_stock = ['TSLA']

my_fields=[StreamClient.LevelOneEquityFields.SYMBOL,
    StreamClient.LevelOneEquityFields.BID_PRICE,
    StreamClient.LevelOneEquityFields.BID_SIZE,
    StreamClient.LevelOneEquityFields.ASK_PRICE,
    StreamClient.LevelOneEquityFields.ASK_SIZE,
    StreamClient.LevelOneEquityFields.LAST_PRICE]

client = easy_client(
    api_key=config.API_KEY,
    redirect_uri=config.REDIRECT_URI,
    token_path=config.TOKEN_PATH)
stream_client = StreamClient(client, account_id=config.ACCOUNT_ID)

class AsyncioThread(threading.Thread):
    def __init__(self, the_queue):   
        self.asyncio_loop = asyncio.get_event_loop()
        self.the_queue = the_queue
        threading.Thread.__init__(self)

    def run(self):
        self.asyncio_loop.run_until_complete(self.read_stream())

    async def read_stream(self):
        await stream_client.login()
        await stream_client.quality_of_service(StreamClient.QOSLevel.EXPRESS)
        await stream_client.level_one_equity_subs(my_stock,fields=my_fields)
        stream_client.add_level_one_equity_handler(self.level_one_handler)
        while(True):
            await stream_client.handle_message()

    # adds streamed data into the queue
    def level_one_handler(self, msg):
        content_dictionary = msg.get('content')[0] 
        self.the_queue.put(content_dictionary)
        print(content_dictionary)


class GUI:
    def __init__(self):
        # thread-safe data storage
        self.the_queue = queue.Queue()

        # the GUI main object
        self.root = Tk()
        self.root.geometry('230x300') 

        self.symbol = StringVar(value = 'Symbol')
        self.bid_price = StringVar(value = 'Bid Price')
        self.ask_price = StringVar(value = 'Ask Price')
        self.last_price = StringVar(value = 'Last Price')

        # Data Labels
        Label(master=self.root, width=12, height=3, textvariable = self.symbol).grid(row=1, column = 0 , pady = 1, sticky=W+E)
        Label(master=self.root, width=12, height=3, textvariable = self.last_price).grid(row=1, column = 1 , pady = 1, sticky=W+E)
        Label(master=self.root, width=12, height=3, text = 'BID').grid(row=3, column = 0, pady = 1, sticky=W+E)
        Label(master=self.root, width=12, textvariable = self.bid_price).grid(row=4, column = 0, pady = 1, sticky=W+E)
        Label(master=self.root, width=12, height=3, text = 'ASK').grid(row=3, column = 1, pady = 1, sticky=W+E)
        Label(master=self.root, width=12, textvariable = self.ask_price).grid(row=4, column = 1, pady = 1, sticky=W+E)
        
        # starting the asyncio web streaming in a separate thread.
        self.thread = AsyncioThread(self.the_queue)
        self.root.after(100, self.refresh_data)
        self.thread.start()


    def refresh_data(self):
        # do nothing if the aysyncio thread is dead
        # and no more data in the queue
        if not self.thread.is_alive() and self.the_queue.empty():
            print('thread is not alive or queue is empty')
            return

        # refresh the GUI with new data from the queue
        while not self.the_queue.empty():
            content_dictionary = self.the_queue.get()
            if 'key' in content_dictionary:
                self.symbol.set(content_dictionary.get('key'))
                print('symbol refresh')
            if 'LAST_PRICE' in content_dictionary:
                self.last_price.set(content_dictionary.get('LAST_PRICE'))
                print('last price refresh')
            if 'BID_PRICE' in content_dictionary:
                self.bid_price.set(content_dictionary.get('BID_PRICE'))
                print('bid refresh')
            if 'ASK_PRICE' in content_dictionary:
                self.ask_price.set(content_dictionary.get('ASK_PRICE'))
                print('ask refresh')

        #  timer to refresh the gui with data from the asyncio thread
        self.root.after(100, self.refresh_data)  # called only once!


if __name__ == '__main__':
    window = GUI()
    window.root.mainloop()