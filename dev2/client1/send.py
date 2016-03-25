import time
import ast
import hashlib
import socket
import re
import sqlite3
import os
import sys

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto import Random

if os.path.isfile("keys.pem") is True:
    print "keys.pem found"

else:   
    #generate key pair and an address
    random_generator = Random.new().read
    key = RSA.generate(1024, random_generator)
    public_key = key.publickey()

    private_key_readable = str(key.exportKey())
    public_key_readable = str(key.publickey().exportKey())
    address = hashlib.sha224(public_key_readable).hexdigest() #hashed public key
    #generate key pair and an address

    print "Your address: "+ str(address)
    print "Your private key:\n "+ str(private_key_readable)
    print "Your public key:\n "+ str(public_key_readable)

    pem_file = open("keys.pem", 'a')
    pem_file.write(str(private_key_readable)+"\n"+str(public_key_readable) + "\n\n")
    pem_file.close()
    address_file = open ("address.txt", 'a')
    address_file.write(str(address)+"\n")
    address_file.close()


# import keys
key_file = open('keys.pem','r')
key = RSA.importKey(key_file.read())
public_key = key.publickey()
private_key_readable = str(key.exportKey())
public_key_readable = str(key.publickey().exportKey())
address = hashlib.sha224(public_key_readable).hexdigest()

print "Your address: "+ str(address)
#print "Your private key:\n "+ str(private_key_readable)
#print "Your public key:\n "+ str(public_key_readable)
# import keys


#open peerlist and connect
with open ("peers.txt", "r") as peer_list:
    peers=peer_list.read()
    peer_tuples = re.findall ("'([\d\.]+)', '([\d]+)'",peers)
    print peer_tuples

for tuple in peer_tuples:
    HOST = tuple[0]
    #print HOST
    PORT = int(tuple[1])
    #print PORT

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.settimeout(5)
        s.connect((HOST, PORT))
        print "Connected to "+str(HOST)+" "+str(PORT)
        #network client program

        s.sendall('Hello, server')

        peer = s.getpeername()
        data = s.recv(1024) #receive data
        print 'Received data from '+ str(peer) +"\n"+ str(data)

        #get remote peers into tuples
        server_peer_tuples = re.findall ("'([\d\.]+)', '([\d]+)'",data)
        print server_peer_tuples
        print len(server_peer_tuples)
        #get remote peers into tuples

        #get local peers into tuples
        peer_file = open("peers.txt", 'r')
        peer_tuples = []
        for line in peer_file:
            extension = re.findall ("'([\d\.]+)', '([\d]+)'",line)
            peer_tuples.extend(extension)
        peer_file.close()
        print peer_tuples
        #get local peers into tuples

        for x in server_peer_tuples:
            if x not in peer_tuples:
                print str(x)+" is a new peer, saving."

                peer_list_file = open("peers.txt", 'a')
                peer_list_file.write(str(x)+"\n")
                peer_list_file.close()        
                
            else:
                print str(x)+" is not a new peer, skipping."

        #broadcast
                
        #send tx
        to_address = str(raw_input ("Send to address: "))
        amount = str(raw_input ("How much to send: "))
            

        while data != "No new blocks here":
            conn = sqlite3.connect('ledger.db')
            c = conn.cursor()                
            c.execute('SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1')
            db_txhash = c.fetchone()[0] #get latest txhash
            conn.close()
            
            print "txhash to send: " +str(db_txhash)

            #s.sendall ("Latest txhash")
            s.sendall(db_txhash) #send latest txhash
            
            data = s.recv(1024) #receive either "Block not found" or start receiving new txs
            if data == "Block not found":
                i = i + 1
                print "Node didn't find the block, sending previous one"



                #do
            if data == "Block found":
                print "Node has the block" #node should start sending txs in this step

                data = s.recv(1024)
                #verify
                sync_list = ast.literal_eval(data) #this is great, need to add it to client -> node sync
                received_block_height = sync_list[0]
                received_address = sync_list[1]
                received_to_address = sync_list[2]
                received_amount = sync_list [3]
                received_signature = sync_list[4]
                received_public_key_readable = sync_list[5]
                received_public_key = RSA.importKey(sync_list[5])
                received_txhash = sync_list[6]
                received_transaction = str(received_block_height) +":"+ str(received_address) +":"+ str(received_to_address) +":"+ str(received_amount) #todo: why not have bare list instead of converting?
                received_signature_tuple = ast.literal_eval(received_signature) #converting to tuple

                #txhash validation start

                conn = sqlite3.connect('ledger.db')
                c = conn.cursor()
                c.execute("SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1;")
                txhash_db = c.fetchone()[0]
                conn.close()
                
                print "Last db txhash: "+str(txhash_db)
                print "Received txhash: "+str(received_txhash)
                print "Received transaction: "+str(received_transaction)

                txhash_valid = 0
                if received_txhash == hashlib.sha224(str(received_transaction) + str(received_signature) +str(txhash_db)).hexdigest(): #new hash = new tx + new sig + old txhash
                    print "txhash valid"
                    txhash_valid = 1
                else:
                    print "txhash invalid"
                    #rollback start
                    s.sendall("Invalid txhash")
                    s.sendall(txhash) #this is my last txhash, please send me a followup; if node informs it was not found, send previous
                    #rollback end
                    
               
                #txhash validation end


                conn = sqlite3.connect('ledger.db')
                c = conn.cursor()
                c.execute("SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1;")
                txhash = c.fetchone()[0]
                conn.close()
                
        
        transaction = str(address) +":"+ str(to_address) +":"+ str(amount)
        signature = key.sign(transaction, '')
        print "Signature: "+str(signature)

        if public_key.verify(transaction, signature) == True:

 
            conn = sqlite3.connect('ledger.db')
            c = conn.cursor()
            c.execute("SELECT txhash FROM transactions ORDER BY block_height DESC LIMIT 1;")
            txhash = str(c.fetchone()[0])
            txhash_new = hashlib.sha224(str(transaction) + str(signature) + str(txhash)).hexdigest() #define new tx hash based on previous #fix asap
            print "New txhash to go with your transaction: "+txhash_new
            conn.close()
               
            print "The signature and control txhash is valid, proceeding to send transaction, signature, new txhash and the public key"
            s.sendall("Transaction")
            s.sendall(transaction+";"+str(signature)+";"+public_key_readable+";"+str(txhash_new)) #todo send list

            
        else:
            print "Invalid signature"
        #send tx


            
        #broadcast
        s.close()

        #network client program


    except Exception as e:
        print e
        print "Cannot connect to "+str(HOST)+" "+str(PORT)
        raise

