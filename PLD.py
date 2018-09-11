
import logger, random, socket


# global defines

HOST_SENDR        = 0
HOST_RECVR        = 1

DIR_SENT          = 0
DIR_RECV          = 1
DIR_DROP          = 2


# handle the loss of package in the transfer
def handle(receiver, packet, current_time, receiver_host, receiver_port, seed, pdrop):

   random.seed(seed)
   random_num = random.random()

   if (random_num > pdrop):

      # send packet
      receiver.sendto(str(packet), (receiver_host, receiver_port))
      logger.log(HOST_SENDR, current_time, DIR_SENT, packet)

   else:
      
      # drop packet
      logger.log(HOST_SENDR, current_time, DIR_DROP, packet)
