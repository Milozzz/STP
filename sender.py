
# usage: python sender.py receiver_host_ip receiver_port file.txt MWS MSS timeout pdrop seed


# Python+custom modules
import sys, time, timeit, socket, random, collections
import logger, PLD
from packet import *


# globals/psuedo "#defines"
STATE_FINISHED    = -1
STATE_INACTIVE    = 0
STATE_INIT        = 1
STATE_CONNECTED   = 2
STATE_TEARDOWN    = 3

HOST_SENDR        = 0
HOST_RECVR        = 1

DIR_SENT          = 0
DIR_RECV          = 1
DIR_DROP          = 2

# global variables
sender_state      = STATE_INACTIVE
sender_start_time = 0
host              = HOST_SENDR


def main():
   
   global sender_start_time
   global host

   # validating command line arguments
   if (len(sys.argv) != 9):
      sys.exit("usage: python sender.py receiver_host_ip receiver_port file.txt MWS MSS timeout pdrop seed")

   if (not sys.argv[2].isdigit()) or (not sys.argv[2].isdigit()) or (not sys.argv[2].isdigit()) or (not sys.argv[2].isdigit()) or (not sys.argv[2].isdigit()):
      sys.exit("usage: python sender.py receiver_host_ip receiver_port file.txt MWS MSS timeout pdrop seed")

   receiver_host	   = sys.argv[1]
   receiver_port	   = int(sys.argv[2])
   sender_filename	= sys.argv[3]
   sender_mws	      = int(sys.argv[4])
   sender_mss	      = int(sys.argv[5])
   sender_timeout	   = float(sys.argv[6])
   sender_pdrop	   = float(sys.argv[7])
   sender_seed	      = int(sys.argv[8])


   # seed
   random_seed = random.seed(sender_seed)


   # get current time
   sender_start_time = time.time()


   # initialise log files
   logger.create_new()
   

   # create socket
   receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   receiver.settimeout(sender_timeout)


   # perform handshake
   handshake(receiver, receiver_host, receiver_port, sender_timeout)
   check_state(STATE_CONNECTED, "could not handshake")


   # read file, perform rdt
   buffer = read_file(sender_filename)
   rdt(receiver, receiver_host, receiver_port, buffer, sender_mss, sender_mws, sender_timeout, random_seed, sender_pdrop)


   # teardown connection
   teardown(receiver, receiver_host, receiver_port)
   check_state(STATE_FINISHED, "could not teardown")


   # generate final statistics
   logger.do_stats_sendr()

   print("\nTransfer succeed.")


# perform three-way handshake
def handshake(receiver, receiver_host, receiver_port, sender_timeout):
   global sender_state

   check_state(STATE_INACTIVE, "trying to connect when state != inactive")

   # create packet
   pack = create_packet()
   pack = set_syn(pack)

   # send SYN packet
   receiver.sendto(str(pack).encode(), (receiver_host, receiver_port))
   logger.log(host, current_time(), DIR_SENT, pack)
   sender_state = STATE_INIT


   try:
      response, addr = receiver.recvfrom(1024)
      pack = eval(response)  # transfer byte to list
      logger.log(host, current_time(), DIR_RECV, pack)


      if (check_syn(pack) and check_ack(pack) and get_seq_number(pack) == 0 and get_ack_number(pack) == 1):
         pack = create_packet()
         pack = set_ack(pack)
         pack = set_seq_number(pack, 1)
         pack = set_ack_number(pack, 1)

         # send 3rd packet: ACK (with no payload data)
         receiver.sendto(str(pack).encode(), (receiver_host, receiver_port))
         logger.log(host, current_time(), DIR_SENT, pack)
         sender_state = STATE_CONNECTED

         print(" Connected to " + receiver_host + ":" + str(receiver_port))

      else:
         print(" Handshake error, response: " + response)
         sys.exit()

   except socket.timeout:
      print(" Timed out. could not connect to " + receiver_host + ":" + str(receiver_port))
      sys.exit()




# perform reliable data transfer
def rdt(receiver, receiver_host, receiver_port, buffer, sender_mss, 
   sender_mws, sender_timeout, seed, sender_pdrop):

   global debug
   file_sent      = False
   window         = []
   window_base    = 0
   next_segment   = 0
   acks_recvd     = []

   while (file_sent == False):
      # fill window, send packets
      # wait for responses
      # receive ACKs, remove from window, inc window base

      # fill window up to MWS, send packets
      while (len(window) < sender_mws) and (next_segment < len(buffer)):

         next_segment = window_base + (sender_mss * len(window))

         if (next_segment < len(buffer)):
            window.append(next_segment)

            # send packet
            pack = new_data_packet(buffer, next_segment, sender_mss)
            PLD.handle(receiver, pack, current_time(), receiver_host, receiver_port, seed, sender_pdrop)

      
      # wait for ACKs
      try:

         response, addr = receiver.recvfrom(1024)
         pack = eval(response)
         logger.log(host, current_time(), DIR_RECV, pack)

         # get ACK num, remove from window
         if (check_ack(pack)):
            ack_num = get_ack_number(pack)

            if (ack_num >= len(buffer)):
               file_sent = True
            else:
               i = 0

               # remove any predecessing packets from window
               while (i < len(window)):
                  if (window[i] < ack_num):
                     del window[i]
                  i += 1

               # get new base
               if (len(window)):
                  window_base = window[0]

               # keep track of ACK number, check if fast retransmit triggered
               acks_recvd.append(ack_num)
               count = collections.Counter(acks_recvd)
               if (count[ack_num] == 4):
                  # fast retransmit triggered
                  pack = new_data_packet(buffer, ack_num, sender_mss)
                  PLD.handle(receiver, pack, current_time(), receiver_host, receiver_port, seed, sender_pdrop)


         else:
            print("Error: received non-ack packet during rdt")


      except socket.timeout:

         print("Timed out, resend window to " + receiver_host + ":" + str(receiver_port))

         i = 0

         # resend all packets in the window
         while (i < len(window)):
            pack = new_data_packet(buffer, window[i], sender_mss)
            PLD.handle(receiver, pack, current_time(), receiver_host, receiver_port, seed, sender_pdrop)
            i += 1

      else:
         # break out after receiving a packet
         pass


# teardown connection
def teardown(receiver, receiver_host, receiver_port):
   global sender_state

   sender_seq_acc = 0
   sender_ack_acc = 0

   check_state(STATE_CONNECTED, "trying to teardown when state != connected")

   pack = create_packet()
   pack = set_fin(pack)
   pack = set_seq_number(pack, sender_seq_acc)
   pack = set_ack_number(pack, sender_ack_acc)

   # send FIN packet
   receiver.sendto(str(pack).encode(), (receiver_host, receiver_port))
   logger.log(host, current_time(), DIR_SENT, pack)
   sender_state = STATE_TEARDOWN

   print("Teardown connection...")

   while (sender_state != STATE_FINISHED):
      
      try:
         response, addr = receiver.recvfrom(1024)
         pack = eval(response)
         logger.log(host, current_time(), DIR_RECV, pack)


         # receive ACK packet from sender
         # no response to be given. wait for sender's FIN packet
         if (sender_state == STATE_TEARDOWN and check_ack(pack) and
            not check_syn(pack) and not check_fin(pack) and not check_data(pack)):

            sender_state = STATE_INACTIVE
            

         # received FIN packet from sender
         # send ACK, move state to STATE_FINISHED
         elif (sender_state == STATE_INACTIVE and check_fin(pack) and
            not check_syn(pack) and not check_ack(pack) and not check_data(pack)):

            pack = create_packet()
            pack = set_ack(pack)
            pack = set_seq_number(pack, sender_seq_acc)
            pack = set_ack_number(pack, sender_ack_acc)

            receiver.sendto(str(pack).encode(), (receiver_host, receiver_port))
            logger.log(host, current_time(), DIR_SENT, pack)
            sender_state = STATE_FINISHED

            print("Teardown complete, connection terminated. " + receiver_host + ":" + str(receiver_port))
            
         else:
            print("Teardown error. state: " + str(sender_state) + ", response: " + response.decode())
            sys.exit()

      except socket.timeout:
         print("Timed out, could not teardown connection to " + receiver_host + ":" + str(receiver_port))
         sys.exit()


# helper functions

# open/read file
def read_file(filename):
    # read file
   try:
      file_descriptor = open(filename, "r")
      buffer = file_descriptor.read()
      file_descriptor.close()
   except:
      sys.exit("fatal: no such file " + filename)  # if no such file exists, raise exception

   return buffer

# get current time elapsed
def current_time():
   diff = (time.time() - sender_start_time) * 1000
   return int(diff)


# check current state against expected state
def check_state(state, error_msg):
   if (sender_state != state):
      print(" Error: sender state != " + str(state) + ". " + error_msg)
      sys.exit()


# create new data packet
def new_data_packet(buffer, next_segment, mss):
   pack = create_packet()
   pack = set_seq_number(pack, next_segment)
   pack = set_data(pack)

   if ((next_segment + mss) < len(buffer)):
      pack = add_data(pack, buffer[next_segment:next_segment+mss])
   else:
      pack = add_data(pack, buffer[next_segment:])

   return pack


# call main
main()
