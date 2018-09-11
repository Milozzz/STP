# Usage: python receiver.py <receiver port> <filename>


import sys, socket, logger, time, os, glob, datetime
from packet import *


# globals/psuedo "#defines"
STATE_INACTIVE       = 0
STATE_INIT           = 1
STATE_CONNECTED      = 2
STATE_TEARDOWN       = 3

HOST_SENDR           = 0
HOST_RECVR           = 1

DIR_SENT             = 0
DIR_RECV             = 1
DIR_DROP             = 2

# global variables
receiver_state       = STATE_INACTIVE
receiver_start_time  = 0
host                 = HOST_RECVR


def main():

   global receiver_state
   global host
   global receiver_start_time


   # defensive programming-- validating arguments
   if (len(sys.argv) != 3):
      sys.exit("usage: python receiver.py receiver_port filename.txt")

   if (not sys.argv[1].isdigit()):
      sys.exit("usage: python receiver.py receiver_port filename.txt")
   # set command line arguments
   receiver_host        = "localhost"
   receiver_port        = int(sys.argv[1])
   receiver_filename    = sys.argv[2]




   receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   receiver.bind((receiver_host, receiver_port))  # bind address and port


   receiver_seq_acc = 0
   receiver_ack_acc = 0

   while True:
      data, sender = receiver.recvfrom(receiver_port)
      pack = eval(data)  # transfer byte to list
   
      if (receiver_state == STATE_INACTIVE):
         receiver_start_time = time.time()

      logger.log(host, current_time(), DIR_RECV, pack)


      sender_host = sender[0]
      sender_port = sender[1]



      if (receiver_state == STATE_INACTIVE):
         # receive first handshake packet, send response

         if (check_syn(pack) and get_seq_number(pack) == 0 and get_ack_number(pack) == 0):

            pack = create_packet()
            pack = set_syn(pack)
            pack = set_ack(pack)
            pack = set_seq_number(pack, 0)
            pack = set_ack_number(pack, 1)

            receiver.sendto(str(pack).encode(), (sender_host, sender_port))
            logger.log(host, current_time(), DIR_SENT, pack)

            receiver_state = STATE_INIT
            print(" New incoming connection!")


      elif (receiver_state == STATE_INIT):
         # received 3rd and last handshake packet
         # state is now considered "connected"

         if (check_ack(pack) and get_seq_number(pack) == 1 and get_ack_number(pack) == 1):
            receiver_state = STATE_CONNECTED

            receiver_seq_num = 0
            receiver_ack_num = 0

            check_existing_file(receiver_filename)

            print(" Connected to " + sender_host + ":" + str(sender_port))

      elif (receiver_state == STATE_CONNECTED):
   
         if (check_data(pack)):
            # get data out of packet
            # write to file
            # send ACK

            buffer = get_data(pack)
            seq_num = get_seq_number(pack)

            if (seq_num == receiver_ack_num):
               # packet arrived is next in order
               pack = create_packet()
               pack = set_ack(pack)
               pack = set_ack_number(pack, seq_num + len(buffer))

               receiver.sendto(str(pack).encode(), (sender_host, sender_port))
               logger.log(host, current_time(), DIR_SENT, pack)

               receiver_ack_num = seq_num + len(buffer)

               append_to_file(receiver_filename, buffer)


            else:
               # packet arrived and is out of order
               pack = create_packet()
               pack = set_ack(pack)
               pack = set_ack_number(pack, receiver_ack_num)

               receiver.sendto(str(pack).encode(), (sender_host, sender_port))
               logger.log(host, current_time(), DIR_SENT, pack)


         if (check_fin(pack)):
            print(" Teardown received from sender")
            
            # send ACK packet
            pack = create_packet()
            pack = set_ack(pack)

            receiver.sendto(str(pack).encode(), (sender_host, sender_port))
            logger.log(host, current_time(), DIR_SENT, pack)

            receiver_state = STATE_TEARDOWN

            # send FIN packet
            pack = create_packet()
            pack = set_fin(pack)

            receiver.sendto(str(pack).encode(), (sender_host, sender_port))
            logger.log(host, current_time(), DIR_SENT, pack)

      elif (receiver_state == STATE_TEARDOWN):

         if (check_ack(pack)):
            # teardown complete
            receiver_state = STATE_INACTIVE

            # rdt finish, generate statistics
            logger.do_stats_recvr()

            print(" Connection terminated\n")


## helper functions


# append buffer to file
def append_to_file(filename, buffer):
   try:
      file_descriptor = open(filename, "a")
      file_descriptor.write(buffer)
      file_descriptor.close()
   except:
      sys.exit("[*] fatal: append to file " + filename + " exception")

   return buffer


# get current time elapsed
def current_time():
   diff = (time.time() - receiver_start_time) * 1000
   return int(diff)


# check if an existing file already exists
def check_existing_file(filename):
   result = glob.glob(filename)

   if (len(result) > 0):
      print(" Previous output file detected. Backing up..")

      for f in result:
         mtime = os.path.getctime(f)
         mtime_readable = datetime.datetime.fromtimestamp(mtime)   
         filename_split = f.split('.', 2)
         new_filename = str(filename_split[0]) + " " + str(mtime_readable) + ".txt"
         print("\t" + f.ljust(20) + " -> ".ljust(7) + new_filename)
         os.rename(f, new_filename)
      
      print("")


main()
