
# some definations

# positions within the list
SEQ_NUM     = 0
ACK_NUM     = 1
FLAGS       = 2
MESSAGE     = 3

# flags
SYN_FLAG    = 0b0001
ACK_FLAG    = 0b0010
FIN_FLAG    = 0b0100
DATA_FLAG   = 0b1000


# create packet
def create_packet():
   packet = [0, 0, 0, 0, 0, 0]
   return packet


# set and get seq/ack numbers
def set_seq_number(packet, value):
   packet[SEQ_NUM] = value
   return packet

def set_ack_number(packet, value):
   packet[ACK_NUM] = value
   return packet

def get_seq_number(packet):
   return packet[SEQ_NUM]

def get_ack_number(packet):
   return packet[ACK_NUM]


# set and check flags
def set_syn(packet):
   # print "set syn"
   packet[FLAGS] |= SYN_FLAG
   return packet

def set_ack(packet):
   # print "set ack"
   packet[FLAGS] |= ACK_FLAG
   return packet

def set_fin(packet):
   # print "set fin"
   packet[FLAGS] |= FIN_FLAG
   return packet

def set_data(packet):
   # print "set data"
   packet[FLAGS] |= DATA_FLAG
   return packet

def check_syn(packet):
   # print "check if it is syn?"
   result = packet[FLAGS] & SYN_FLAG
   return result == SYN_FLAG

def check_ack(packet):
   # print "check if it is ack?"
   result = packet[FLAGS] & ACK_FLAG
   return result == ACK_FLAG

def check_fin(packet):
   # print "check if it is fin?"
   result = packet[FLAGS] & FIN_FLAG
   return result == FIN_FLAG

def check_data(packet):
   # print "check if it is data?"
   result = packet[FLAGS] & DATA_FLAG
   return result == DATA_FLAG

def get_flags(packet):
   flags = ""

   if (check_syn(packet)):
      flags += "S"
   if (check_ack(packet)):
      flags += "A"
   if (check_fin(packet)):
      flags += "F"
   if (check_data(packet)):
      flags += "D"

   return flags


# set and get applicaton data/message
def add_data(packet, message):
   # print "add message"
   packet[MESSAGE] = message
   return packet

def get_data(packet):
   # print "get message"
   return str(packet[MESSAGE])
