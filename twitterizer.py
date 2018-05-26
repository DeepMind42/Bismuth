import tweepy
import json
import options
import os
import sqlite3
import essentials
import connections
import socks
import time

config = options.Get()
config.read()
debug_level = config.debug_level_conf
ledger_path_conf = config.ledger_path_conf
full_ledger = config.full_ledger_conf
ledger_path = config.ledger_path_conf
hyper_path = config.hyper_path_conf
terminal_output=config.terminal_output
version = config.version_conf

file = open ('secret.json', 'r').read ()
parsed = json.loads (file)
consumer_key = parsed['consumer_key']
consumer_secret = parsed['consumer_secret']
access_token = parsed['access_token']
access_token_secret = parsed['access_token_secret']
auth = tweepy.OAuthHandler (consumer_key, consumer_secret)
auth.set_access_token (access_token, access_token_secret)
api = tweepy.API (auth)

key, public_key_readable, private_key_readable, encrypted, unlocked, public_key_hashed, myaddress = essentials.keys_load()

def tweet_saved(tweet):
    try:
        t.execute("SELECT * FROM tweets WHERE tweet = ?", (tweet,))
        dummy = t.fetchone()[0]
        return_value = True
    except:
        return_value = False

    print(return_value)
    return return_value

def tweet_qualify(tweet_id, exposure=10):
    open_status = api.get_status(tweet_id)
    parsed = open_status._json

    parsed_name = parsed ['user']['name'] #add this
    favorite_count = parsed ['favorite_count']
    retweet_count = parsed ['retweet_count']
    parsed_text = parsed['text']


    if "#bismuth" and "$bis" in parsed_text.lower() and retweet_count + favorite_count > exposure:
        qualifies = True
    else:
        qualifies = False

    return qualifies, parsed_text, parsed_name


if __name__ == "__main__":
    if not os.path.exists ('twitter.db'):
        # create empty mempool
        twitter = sqlite3.connect ('twitter.db')
        twitter.text_factory = str
        t = twitter.cursor()
        t.execute ("CREATE TABLE IF NOT EXISTS tweets (block_height, address, openfield, tweet)")
        twitter.commit ()
        print ("Created twitter database")
    else:
        twitter = sqlite3.connect ('twitter.db')
        twitter.text_factory = str
        t = twitter.cursor()
        print ("Connected twitter database")

    #ledger
    if full_ledger == 1:
        conn = sqlite3.connect (ledger_path)
    else:
        conn = sqlite3.connect (hyper_path)
    if "testnet" in version:  # overwrite for testnet
        conn = sqlite3.connect ("static/test.db")

    conn.text_factory = str
    c = conn.cursor()
    # ledger


    while True:
        for row in c.execute ("SELECT block_height, address, openfield FROM transactions WHERE operation = ? ORDER BY block_height DESC LIMIT 50", ("twitter",)):
            tweet_id = row[2]

            tweet_qualified = tweet_qualify (tweet_id)

            if tweet_qualified[0] and not tweet_saved(tweet_qualified[1]):
                print ("Tweet qualifies")

                recipient = row[1]
                amount = 1
                operation = "payout_tw"
                openfield = ""

                timestamp = '%.2f' % time.time ()
                tx_submit = essentials.sign_rsa(timestamp, myaddress, recipient, amount, operation, openfield, key, public_key_hashed)

                if tx_submit:
                    s = socks.socksocket ()
                    s.settimeout (0.3)
                    print(tx_submit)

                    s.connect (("127.0.0.1", int (2829)))
                    print ("Status: Connected to node")
                    while True:
                        connections.send (s, "mpinsert", 10)
                        connections.send (s, tx_submit, 10)
                        reply = connections.receive (s, 10)
                        print ("Payout result: {}".format (reply))
                        break

                    if "Mempool updated with a received transaction" in str(reply[-1]):
                        t.execute ("INSERT INTO tweets VALUES (?, ?, ?, ?)", (row[0], row[1], row[2], tweet_qualified[1]))
                        twitter.commit ()
                        print ("Tweet saved to database")
                        api.update_status ("Bismuth address {} wins giveaway of {} $BIS for https://twitter.com/i/web/status/{}".format(recipient, amount,tweet_id))

                break

        print ("Run finished, sleeping for 10 minutes")
        time.sleep(600)