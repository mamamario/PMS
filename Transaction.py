__author__ = '07896'

class Transaction:
  stateTransaction = ["INITIAL"       #initial state
                    , "WAIT"          #wait for trigger, wait for (counter == 0)
                    , "OUTSTANDING"   #OUTSTANDING
                    , "COMMITTED"     #wait for reset
                      ]

  @staticmethod
  def isTransactionState(inputState):
    assert (inputState in Transaction.stateTransaction), ("Error: %s is not in stateTransaction list" % inputState)
    return inputState

  def resetAttribute(self):
    self.state             = Transaction.isTransactionState("INITIAL")
    self.counter           = -1
    self.subblockaddr      = -1
    self.wrap              = -1
    self.last              = -1
    self.source_req        = None
    
    self.source_node       = None #source node
    self.destination_list  = [] #destination node list
    self.duration_list     = [] #duration node list

  def __init__(self):
    self.state             = Transaction.isTransactionState("INITIAL")
    self.counter           = -1
    self.subblockaddr      = -1
    self.wrap              = -1
    self.source_req        = None
    
    self.source_node       = None #source node
    self.destination_list  = [] #destination node list
    self.duration_list     = [] #duration node list
    
    self.resetAttribute()