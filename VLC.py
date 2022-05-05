__author__ = '07896'

#!/usr/local/bin/python
import sys
import os
import re
import optparse
import operator
import inspect
import math
import random
from queue import Queue
from Cache import *
from Inst import *
from Request import *
from GlobalVar import *
from PCTracer import *
from Transaction import *

dbg_put_queue = Queue()
dbg_ONGO_queue = Queue()
dbg_del_queue = Queue()
dbg_flush_queue = Queue()
INITIAL  = -1
ONGO     = -2 

#--------------------------------------------
# class VLC
#--------------------------------------------
class VLC:

  #*************staticmethod*****************


  stateVLCre        = [ "VLC_NOT_NEXT_INST"
                      , "VLC_NEXT_INST_HIT"
                      , "VLC_NEXT_INST_PARTIAL_MISS"
                      , "VLC_NEXT_INST_WHOLE_MISS" ]
  configlist        = [ "depth"
                      , "entrysize"
                      , "outsdng" 
                      , "Trace_idx"]
  attributelist     = [ "MissCount"
                      , "AccessCount"
                      , "HitCount"
                      , "VLC_FIFO_EMPTY"
                      , "VLC_FIFO_EMPTY_AVG" ]
  

  @staticmethod
  def isVLCreState(inputState):
    assert (inputState in VLC.stateVLCre), ("Error: %s is not in VLC stateVLCre list" % inputState)
    return inputState

  @staticmethod
  def convertByteAddrToSubblockAddr(byte_addr, subblocksize):
    return int(byte_addr/(subblocksize))

    
  def getCfgByName(self, input_name):
    return self.config[input_name]

  def setCfgByName(self, input_name, input_var):
    print("Warning: you should not use \"setCfgByName\"!")
    self.config[input_name] = input_var

  def parseConfig(self):
    for VLC_root in GlobalVar.allcontents_conf.iter('VLC'):
      for defult_tag in VLC_root.iter('defult'):
        for sub_tag in defult_tag:
    
          assert(sub_tag.tag in VLC.configlist), ("%s is not in VLC.configlist " % sub_tag.tag)

          try:
            self.config[sub_tag.tag] = int(sub_tag.attrib["value"])
          except ValueError:
            tempstr = sub_tag.attrib["value"]
            self.config[sub_tag.tag] = int(re.search("([\d]*)\*", tempstr).group(1)) * int(re.search("\*([\d]*)", tempstr).group(1))
          except:
            print("VLC parseConfig Error\n")
            exit(-1)
    
    for my_name_root in GlobalVar.allcontents_conf.iter(self.node_ptr.node_name):
      for sub_tag in my_name_root:
        assert(sub_tag.tag in VLC.configlist), ("%s is not in VLC.configlist " % sub_tag.tag)

        try:
          self.config[sub_tag.tag] = int(sub_tag.attrib["value"])
        except ValueError:
          tempstr = sub_tag.attrib["value"]
          self.config[sub_tag.tag] = int(re.search("([\d]*)\*", tempstr).group(1)) * int(re.search("\*([\d]*)", tempstr).group(1))
        except:
          print("ConfigError\n")
          exit(-1)
    
    
    # user specify
    for icfg in VLC.configlist:
      user_cfg_str = "user_" + icfg
      if (not GlobalVar.options.__dict__[user_cfg_str] == None):
        try:
          self.config[icfg] = int(GlobalVar.options.__dict__[user_cfg_str])
        except ValueError:
          self.config[icfg] = str(GlobalVar.options.__dict__[user_cfg_str])
        except:
          print("VLC user_ConfigError\n")
          exit(-1)

  # def checkConfig():
    # # CheckConfig the relation between VLC and VLC
    # if (not int((self.getCfgByName("entrysize") == Cache.getCfgByName("subblocksize")))):
      # print("ICache Error: entrysize != subblocksize")
      # exit(-1)

  def getAtrByName(self, input_name):
    return self.attribute[input_name]

  def incAtrByName(self, input_name):
    self.attribute[input_name] += 1

  def initAttribute(self):
    for iattri in self.attributelist:
      self.attribute[iattri] = 0

  def printAttributeInfo(self):
    self.printVLCInfo()
  def printVLCInfo(self):
    print("======== [ %s ] %s Report =======" %(self.node_ptr.node_name, self.node_ptr.node_class))
    print("#Access   =  %8d"% (self.getAtrByName("AccessCount")))
    print("#Hit      =  %8d  (%f %%)"% (self.getAtrByName("HitCount")
                                     ,  int(self.getAtrByName("HitCount"))/int(self.getAtrByName("AccessCount")) * 100.0 ))
    print("#Miss     =  %8d  (%f %%)"% (self.getAtrByName("MissCount")
                                                 , int(self.getAtrByName("MissCount"))/int(self.getAtrByName("AccessCount")) * 100.0))
    print("")
  def initInstList(self, input_asm):
  
    for subblocksize_root in GlobalVar.allcontents_conf.iter('subblocksize'):
      subblocksize_value = int(subblocksize_root.attrib["value"])
  
    # print(input_asm)
    start_point = input_asm.replace(re.search("([\w\s\.\-\:\[\]\n]*)start:", input_asm).group(1), "")
    # print(start_point)


    # instlist create
    asmlistall = start_point.split("\n")
    instnum    = 0
    addrlen    = 0
    nowtag     = ""
    tagnum     = 0
    nowaddr    = 0
    nowasm     = ""
    for inlist in asmlistall:
      if (not re.search("[\w\d\.\_]*:", inlist) == None):
        nowtag       = re.search("([\w\d\.\_]*):", inlist).group(1)

        # print("%s:" %(nowtag))
      elif (not re.search("^[\da-z]+", inlist) == None):

        nowaddr_16   = re.search("(^[\da-z]+)", inlist).group(1)
        nowaddr      = int(nowaddr_16, 16)
        machine_code = re.search("^[\da-z]+[\s]+([\w ]+)   ", inlist).group(1)
        nowasm       = re.search("^[\da-z]+[\s]+[\w ]+   ([\w\d\.\-\:\[\]\| \t\-\,\_]*)", inlist).group(1)
        # addrlen      = int(machine_code.count(' ') + 1)
        addrlen      = int(len(re.findall("[0-9A-Za-z]+", machine_code)))
        subaddr      = self.convertByteAddrToSubblockAddr(nowaddr, subblocksize_value)

        self.instbyteaddr2listindex[nowaddr] = instnum
        self.instList.append((Inst(instnum, addrlen, nowaddr, machine_code, nowtag, tagnum, nowasm, subaddr)))

        tagnum       += 1
        instnum      += 1
        # print("%s   %21s   %s" %(nowaddr, machine_code, nowasm))

    # subblocklist handle
    subblock = 0
    subblocksize = subblocksize_value
    iinst = 0
    while (iinst < len(self.instList)):
      while (subblocksize > 0 and iinst < len(self.instList)):
        subblocksize -= self.instList[iinst].length
        self.instList[iinst].subblocklist.append(subblock)
        # if subblocksize >= 0:
        #   self.instList[iinst].subblocklist.append(self.instList[iinst].length)
        # else:
        #   self.instList[iinst].subblocklist.append(self.instList[iinst].length + subblocksize)
        iinst += 1
      subblock += 1
      if (subblocksize < 0):
        self.instList[iinst-1].subblocklist.append(subblock)
        # self.instList[iinst-1].subblocklist.append(int(subblocksize*-1))
        subblocksize = subblocksize_value +  subblocksize
      else:
        subblocksize = subblocksize_value

  def compareNextInst(self, input_nextinst):
    re = ""
    # happened in the beginning
    if (self.instptr == -1):
      re = "VLC_NOT_NEXT_INST"
    # print("self.instptr", self.instptr, "=", self.instList[self.instptr])

    predictnextinst = self.instList[self.instptr]
    realnextinst    = self.instList[self.instbyteaddr2listindex[input_nextinst]]

    # VLC predict miss
    if (not predictnextinst == realnextinst):
      re = "VLC_NOT_NEXT_INST"
    # VLC predict hit in the inst head
    # check the total inst len
    else:
      inst_total_part = len(predictnextinst.subblocklist)
      inst_found_part = 0
      for iinstsubblock in predictnextinst.subblocklist:
        if (iinstsubblock in self.vlcEntry):
          inst_found_part += 1
      # print(inst_total_part, inst_found_part, predictnextinst.subblocklist, self.vlcEntry)

      if (not inst_found_part == inst_total_part):
        # print("There are some part of NextInst is not in VLC = ", self.instptr, ":", iinstpart)
        if (not inst_total_part == 1 and not inst_found_part == 0):
          re = "VLC_NEXT_INST_PARTIAL_MISS"
        else:
          re = "VLC_NEXT_INST_WHOLE_MISS"
      else:
        re = "VLC_NEXT_INST_HIT"
    return re

  def resetEntryBySubblock(self, input_subblock):
    for ientry in range(0, len(self.vlcEntry)):
      if (self.vlcEntry[ientry] == input_subblock):
        self.vlcEntry[ientry] = -1
        return True
    return False

  def consumeEntryAndInstptr(self):
    # print("consumeEntry")
    if (self.instptr < len(self.instList) - 1):
      if (not self.instList[self.instptr].subblockaddr == self.instList[self.instptr+1].subblockaddr):
        dbg_del_queue.put(self.instList[self.instptr].subblockaddr)
        re_resetEntryBySubblock = self.resetEntryBySubblock(self.instList[self.instptr].subblockaddr)
        assert(re_resetEntryBySubblock)
        ### prefetch the next subblockaddr (VLC prefetch) ###
        self.subblock_queue.put(self.instList[self.instptr].subblockaddr + self.getCfgByName("depth"))
        dbg_put_queue.put(self.instList[self.instptr].subblockaddr + self.getCfgByName("depth"))
      ### self.instptr incre ###
      self.instptr      += 1

  def findFreeEntryandFill(self):
    ''' find a free Entry, if not just return with nothing
        occupy a outsdnglist in VLC, if not just return with nothing
    '''

    ### find free Entry###
    free_Entry = -1
    for ientry in self.vlcEntry:
      if(ientry == INITIAL):
        free_Entry = self.vlcEntry.index(ientry)
        break
    ### return, if found no free Entry ###
    if(free_Entry == -1):
      return

    ### occupy a outsdnglist in VLC ###
    free_outsdng = -1
    for ioutsdnglist in self.outsdnglist:
      if(ioutsdnglist.state == Request.isRequestState("INITIAL")):
        free_outsdng = self.outsdnglist.index(ioutsdnglist)
        break
    ### return, if can not occupy a outsdnglist in VLC ###
    if(free_outsdng == -1):
      return

    if(not self.subblock_queue.qsize() == 0):
      item_subblock = self.subblock_queue.get()
      dbg_ONGO_queue.put(item_subblock)
      ### vlcEntry = -2 meaning this entry is ONGO, waiting for response ###
      self.vlcEntry[free_Entry]                   = -2
      self.outsdnglist[free_outsdng].resetAttribute()
      self.outsdnglist[free_outsdng].ID           = free_Entry
      self.outsdnglist[free_outsdng].state        = Request.isRequestState("WAIT")
      self.outsdnglist[free_outsdng].subblockaddr = item_subblock
      self.outsdnglist[free_outsdng].source_node  = self.node_ptr

  def fillVLC(self, input_addr):
    pass

  def resetvlcEntry(self):
    for ientry in range(0, len(self.vlcEntry)):
      if(self.vlcEntry[ientry] > -1):dbg_flush_queue.put(self.vlcEntry[ientry])
      self.vlcEntry[ientry] = -1

  def flushVLC(self, input_addr):
    wanted_insthead  = self.instList[self.instbyteaddr2listindex[input_addr]].subblockaddr
    self.instptr     = self.instList[self.instbyteaddr2listindex[input_addr]].ID
		
    # reset VLC fifo
    self.resetvlcEntry()
    
    ### set reqs in outsdnglist as FLUSHED ###
    for i_outsdnglist in self.outsdnglist:
      if( not i_outsdnglist.state == Request.isRequestState("INITIAL")):
        i_outsdnglist.flushed = True

    self.subblock_queue.queue.clear()

    for i_outsdnglist in self.outsdnglist:
      ### fill subblock_queue the flush num ###
      self.subblock_queue.put(wanted_insthead + self.outsdnglist.index(i_outsdnglist))
      dbg_put_queue.put(wanted_insthead + self.outsdnglist.index(i_outsdnglist))
    return

  def calStallTime(self):
    myPCTracer = self.PCTracer_ptr
    try_abstime, try_clock, try_PC = myPCTracer.nextPC()
    return (int(try_clock) - int(self.cur_clock) - 1)

  def print_dbg_info(self):
    pass
    
  def initialize(self):
    input_asm = GlobalVar.allcontents_asm
    
    self.parseConfig()
    self.initAttribute()
    self.initInstList(input_asm)
    # create association of VLC
    for ientry in range(self.getCfgByName("depth")):
      self.vlcEntry.append(-1)

    for ioutsdnglist in range(self.getCfgByName("outsdng")):
      self.outsdnglist.append(Request())

    self.subblock_queue = Queue()

    # for every VLC there is a PCTracker
    self.PCTracer_ptr = PCTracer()
    self.PCTracer_ptr.VLC_ptr = self
    self.PCTracer_ptr.initialize(int(self.getCfgByName("Trace_idx")))

  def __init__(self):
  
    self.config = {}
    ### pointer back to Node obj ###
    self.node_ptr = None

    self.PCTracer_ptr = None
    self.attribute = {}

    ### inst list ###
    self.instList = []
    ### inst list pointer ###
    self.instptr = -1                 
    ###? ###
    self.instbyteaddr2listindex = {}  
    
    ### entry list, store the sub-block addr, represent it is in the VLC ###
    ### -1: INITIAL -2: ONGO ###
    self.vlcEntry = []
    ### outstanding list #outsdng list, req that has "been" issue ###
    self.outsdnglist = []
    ### subblock list, req that is "waiting" for issue ###
    self.subblock_queue   = None

    ### for self.PCTracer_ptr.nextPC(), may be is useless? ###
    self.cur_abstime = 0
    self.cur_clock = 0
    self.cur_PC = 0

    self.VLC_state = 0

  def initial_cycle(self):
    myPCTracer = self.PCTracer_ptr
    myPCTracer.transPCTracerNextState("PCTracer_ASSIGN_PC")

  
    
  '''
  VLC pre_cycle
  receive transaction from port_BN_trans
  
  '''
  def pre_cycle(self):
    myPCTracer = self.PCTracer_ptr
    # for VLC input PClist check
    if (myPCTracer.PCpointer >= len(myPCTracer.PClist)):
      return
    ### receive from PBUS Port ###
    for key, value in self.node_ptr.node_port_dist.items():
      if( len(value.port_BN_trans) > 0):
        ### there should be only one item in port_BN_trans of each port ###
        assert (len(value.port_BN_trans) == 1), ("len(value.port_BN_trans) == ", len(value.port_BN_trans))
        ### get the transaction ###
        cur_transaction = value.port_BN_trans[TOPPEST]
        del value.port_BN_trans[TOPPEST]
        ### set all transaction in bus_port_arbitor counter to exact value ###
        myreq = cur_transaction.source_req
        assert (myreq.state == Request.isRequestState("OUTSTANDING")), ("fatal error myreq.state == %s" % myreq.state)
        if(not myreq.flushed == True):
          assert (self.vlcEntry[myreq.ID] == ONGO), ("self.vlcEntry[myreq.ID] != ONGO(-2) = %s" %self.vlcEntry[myreq.ID])
          self.vlcEntry[myreq.ID] = myreq.subblockaddr
        else:
          dbg_flush_queue.put(myreq.subblockaddr)
        ### reaet the outstdng item ###
        myreq.resetAttribute()
        
  def cur_cycle(self):
    myPCTracer = self.PCTracer_ptr
    # for VLC input PClist check
    if (myPCTracer.PCpointer >= len(myPCTracer.PClist)):
      return

    #PCTracer_state state machine transmit
    myPCTracer.PCTracer_state = myPCTracer.PCTracer_nextState

    self.cur_abstime, self.cur_clock, self.cur_PC = myPCTracer.nextPC()
    self.VLC_state = VLC.isVLCreState(self.compareNextInst(self.cur_PC))


    PCTracerNextState = ""
    if (myPCTracer.PCTracer_state == PCTracer.isPCTracer_state("PCTracer_CORE_STALL")):
      if (self.PCTracer_counter == 0):
        PCTracerNextState = ("PCTracer_ASSIGN_PC")
      else:
        self.PCTracer_counter -= 1
        PCTracerNextState = ("PCTracer_CORE_STALL")

    elif (myPCTracer.PCTracer_state == PCTracer.isPCTracer_state("PCTracer_PENDING_BY_VLC")):

      if (self.VLC_state == VLC.isVLCreState("VLC_NEXT_INST_HIT")):
        self.consumeEntryAndInstptr()
        self.incAtrByName("HitCount")# #####################################
        if (not myPCTracer.consumePC() == "PCend"):
          self.PCTracer_counter = self.calStallTime()
          if (self.PCTracer_counter > 0):
            PCTracerNextState = ("PCTracer_CORE_STALL")
          else:
            PCTracerNextState = ("PCTracer_ASSIGN_PC")
        else:
          PCTracerNextState = ("PCTracer_CORE_STALL")
      else:
        # self.flushVLC(self.cur_PC)
        PCTracerNextState = ("PCTracer_PENDING_BY_VLC")

    elif (myPCTracer.PCTracer_state == PCTracer.isPCTracer_state("PCTracer_ASSIGN_PC")):
      self.incAtrByName("AccessCount")# #####################################
      if   (self.VLC_state == VLC.isVLCreState("VLC_NEXT_INST_HIT")):
        self.consumeEntryAndInstptr()
        self.incAtrByName("HitCount")# #####################################
        if (not myPCTracer.consumePC() == "PCend"):
          self.PCTracer_counter = self.calStallTime()
          if (self.PCTracer_counter > 0):
            PCTracerNextState = ("PCTracer_CORE_STALL")
          else:
            PCTracerNextState = ("PCTracer_ASSIGN_PC")
        else:
          PCTracerNextState = ("PCTracer_CORE_STALL")
      elif (self.VLC_state == VLC.isVLCreState("VLC_NOT_NEXT_INST")):
        self.flushVLC(self.cur_PC)
        PCTracerNextState = ("PCTracer_PENDING_BY_VLC")
        self.incAtrByName("MissCount")  # #####################################
      elif (self.VLC_state == VLC.isVLCreState("VLC_NEXT_INST_PARTIAL_MISS")):
        PCTracerNextState = ("PCTracer_PENDING_BY_VLC")
        self.incAtrByName("MissCount")  # #####################################
      elif (self.VLC_state == VLC.isVLCreState("VLC_NEXT_INST_WHOLE_MISS")):
        PCTracerNextState = ("PCTracer_PENDING_BY_VLC")
        self.incAtrByName("MissCount")  # #####################################

    myPCTracer.transPCTracerNextState(PCTracerNextState)
    self.findFreeEntryandFill()

    # reset "COMMITTED" req
    for ireq in self.outsdnglist:
      if (ireq.state == Request.isRequestState("COMMITTED")):
        ireq.resetAttribute()

  def pos_cycle(self):
    myPCTracer = self.PCTracer_ptr
    # for VLC input PClist check
    if (myPCTracer.PCpointer >= len(myPCTracer.PClist)):
      return
    ### find the "WAITTING" one in outsdnglist, make a transaction
    for ioutsdnglist in range(self.getCfgByName("outsdng")):
      if(self.outsdnglist[ioutsdnglist].state == Request.isRequestState("WAIT")):
        assert(not self.node_ptr.node_lower_bus == "None"), ("%s node_lower_bus = %s" %(self.node_ptr.node_name, self.node_ptr.node_lower_bus))
        ### mark this req in outsdnglist as OUTSTANDING state ###
        self.outsdnglist[ioutsdnglist].state = Request.isRequestState("OUTSTANDING")
        ### turn req to a new transaction ###
        tmp_transaction = Transaction()
        tmp_transaction.source_node = self.node_ptr
        tmp_transaction.destination_list.append(GlobalVar.topology_ptr.node_dist[self.node_ptr.node_lower_node])
        tmp_transaction.duration_list.append(self.node_ptr)
        tmp_transaction.source_req = self.outsdnglist[ioutsdnglist]
        tmp_transaction.subblockaddr = self.outsdnglist[ioutsdnglist].subblockaddr
        
        self.node_ptr.node_port_dist[self.node_ptr.node_name + "_" + self.node_ptr.node_lower_bus ].port_NB_trans.append(tmp_transaction)


