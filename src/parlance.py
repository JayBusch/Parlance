# [[file:parlance.org::*Imports][Imports:1]]
import os
import time
import re
import uuid
import unittest
import random
import array
import logging
import sys
import multiprocessing
from multiprocessing import Process, Queue, Manager
import argparse
import asyncore
import asynchat
import socket
from enum import Enum
# Imports:1 ends here

# [[file:parlance.org::*Unit%20Tests][Unit\ Tests:1]]
class UserTest(unittest.TestCase):
    """User TestCase"""

class RoomTest(unittest.TestCase):
    """Room TestCase"""

class ParlanceServerTest(unittest.TestCase):
    """ParlanceServer TestCase"""

    testParlanceServer = None

    def setUp(self):
        self.testParlanceServer = ParlanceServer(('localhost', 12345))
     
    def tearDown(self):
        self.testParlanceServer.server_shutDown()
        
    def test_ParlanceServer___init__(self):
        self.assertTrue(self.testParlanceServer != None)
# Unit\ Tests:1 ends here

# [[file:parlance.org::*Main%20Class%20Body][Main\ Class\ Body:1]]
mp = multiprocessing.get_context('forkserver')

logging.basicConfig(level=logging.INFO, format="%(created)-15s %(levelname)8s %(thread)d %(name)s %(message)s")
log                     = logging.getLogger(__name__)

ansi_escape = re.compile(r'\x1b[^m]*m')

termCodes = {
    "UP_ONE_LINE": b'\033[1A',
    "DEL_LEFT" : b'\033[1K',
    "DEL_LINE" : b'\033[2K',
    "CLR_SCR": b'\033[2J',
    "MOV_BEG_LINE" : b'\033[0G',
    "MOV_TOP_LEFT" : b'\033[1;1H',
    "SLOW_BLINK": b'\033[5m',
    "BLINK_OFF": b'\033[25m',
    "BOLD": b'\033[1m',
    "SET_FG_COLOR": b'\033[0;',
    "SET_FG_COLOR_TERM": b'm',
    "RESET_FG_COLOR": b'\033[0m',
    "ERASE_PROMPT" : b'\033[2K\033[1A\033[2K'
}

parlanceLogo = b'' + \
               b'__________              ' + termCodes["SLOW_BLINK"] + b'.' + termCodes["BLINK_OFF"] + \
               b'__            \n' + \
               b'\______   \_____ _______|  | _____    ____   ____  ____  \n' + \
               b' |     ___/\__  \\\_  __ \  | \__  \  /    \_/ ___\/ __ \ \n' + \
               b' |    |     / __ \|  | \/  |__/ __ \|   |  \  \__\  ___/ \n' + \
               b' |____|    (____  /__|  |____(____  /___|  /\___  >___  >\n' + \
               b'                \/                \/     \/     \/    \/ \n'

parlanceAcronym = b'a ' + termCodes["BOLD"] + b'P' + termCodes["RESET_FG_COLOR"] + b'ython ' \
                  + termCodes["BOLD"] + b'A' + termCodes["RESET_FG_COLOR"] + \
                  b'synchronous '+ termCodes["BOLD"] + b'R' + termCodes["RESET_FG_COLOR"] \
                  + b'e' + termCodes["BOLD"] + b'L' + termCodes["RESET_FG_COLOR"] + b'ay ' \
                  + termCodes["BOLD"] + b'AN' + termCodes["RESET_FG_COLOR"] + b'd ' + \
                  termCodes["BOLD"] + b'C' + termCodes["RESET_FG_COLOR"] + b'hat ' + \
                  termCodes["BOLD"] + b'E' + termCodes["RESET_FG_COLOR"] + b'xperience'

class ServerLocation(Enum):
    notLoggedIn = 0
    loggedIn = 1
    inRoom = 2
    inGame = 3

def suite():
    """
        Gather all the tests from this module in a test suite.
    """
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(ParlanceServerTest))
    return test_suite
# Main\ Class\ Body:1 ends here

# [[file:parlance.org::*User%20Class][User\ Class:1]]
class User():

    locationOnServer = None
    currentRoom = None
    currentColor = None
    userId = None
    userName = None
    
    def __init__(self):    
        self.userId = str(uuid.uuid4())
        self.locationOnServer = ServerLocation.notLoggedIn

    def setCurrentColor(self):
        self.currentColor = random.randrange(30, 37)

    def userNameInColor(self):
        return termCodes["SET_FG_COLOR"] + str(self.currentColor).encode() + \
            termCodes["SET_FG_COLOR_TERM"] + self.userName.encode() + termCodes["RESET_FG_COLOR"]

    def prompt(self):
        if(self.locationOnServer == ServerLocation.inRoom):
            return b'Parlance(? for help)['+ self.currentRoom.name.encode() + b']<'+ termCodes["BOLD"] + \
                self.userNameInColor() + termCodes["RESET_FG_COLOR"] + b'>' + termCodes["SLOW_BLINK"] + \
                b':' + termCodes["BLINK_OFF"]
        else:
            return b'Parlance(? for help)<'+ termCodes["BOLD"] + self.userName.encode() + \
                termCodes["RESET_FG_COLOR"] + b'>' + termCodes["SLOW_BLINK"] + b':' + termCodes["BLINK_OFF"]
# User\ Class:1 ends here

# [[file:parlance.org::*Room%20Class][Room\ Class:1]]
class Room():
    name = None
    users = None

    def __init__(self, newRoomName):
        self.users = ParlanceServer.manager.list()
        self.name = newRoomName
# Room\ Class:1 ends here

# [[file:parlance.org::*Action%20Class][Action\ Class:1]]
class Action(object):
    users = None
    userSockets = None
    rooms = None
    userId = None
    handler = None
    
    def __init__(self, newUserId):
        self.userId = str(newUserId.decode())

    def execute(self, userSockets, users, rooms):
        self.users = users
        self.rooms = rooms
        newHandler = userSockets[self.userId]
        self.handler = newHandler
# Action\ Class:1 ends here

# [[file:parlance.org::*LoginAction%20Class][LoginAction\ Class:1]]
class LoginAction(Action):
    def __init__(self, newUserId, newUserName):
        Action.__init__(self, newUserId)
        self.userName = str(newUserName.decode())
        
    def execute(self, userSockets, users, rooms):
        super(LoginAction, self).execute(userSockets, users, rooms)

        for otherUser in users.values():
            if(otherUser.userName == self.userName):
                self.handler.send(b'Sorry, that name is taken.\n')
                self.handler.send(b'What is your name?:')
                return

        user = users[self.userId]
        user.locationOnServer = ServerLocation.loggedIn
        user.userName = self.userName
        users[self.userId] = user
        self.handler.send(b'Logged In As: ' + self.userName.encode() + b'\n' + user.prompt())
# LoginAction\ Class:1 ends here

# [[file:parlance.org::*ListRoomsAction%20Class][ListRoomsAction\ Class:1]]
class ListRoomsAction(Action):
    def __init__(self, newUserId):
        Action.__init__(self, newUserId)

    def execute(self, userSockets, users, rooms):
        super(ListRoomsAction, self).execute(userSockets, users, rooms)
        self.handler.send(termCodes["ERASE_PROMPT"])
        self.handler.send(b'List of Rooms:\n')
        for roomName, room in rooms.items():
            self.handler.send(b'\t' + roomName.encode() + b'(' + str(len(room.users)).encode() + b')\n')
        self.handler.send(users[self.userId].prompt())
# ListRoomsAction\ Class:1 ends here

# [[file:parlance.org::*CreateRoomAction%20Class][CreateRoomAction\ Class:1]]
class CreateRoomAction(Action):
    roomName = None

    def __init__(self, newUserId, newRoomName):
        Action.__init__(self, newUserId)
        self.roomName = newRoomName

    def execute(self, userSockets, users, rooms):
        super(CreateRoomAction, self).execute(userSockets, users, rooms)
        self.handler.send(termCodes["ERASE_PROMPT"] + b'Creating New Room ' + self.roomName + b'\n')
        rooms[self.roomName.decode()] = Room(self.roomName.decode())
        self.handler.send(users[self.userId].prompt())
# CreateRoomAction\ Class:1 ends here

# [[file:parlance.org::*JoinRoomAction%20Class][JoinRoomAction\ Class:1]]
class JoinRoomAction(Action):
    roomName = None

    def __init__(self, newUserId, newRoomName):
        Action.__init__(self, newUserId)
        self.roomName = newRoomName

    def execute(self, userSockets, users, rooms):
        super(JoinRoomAction, self).execute(userSockets, users, rooms)

        self.handler.send(termCodes["ERASE_PROMPT"])
        user = users[self.userId]

        badInput = False
        if (self.roomName == None or self.roomName == ""):
            badInput = True
        try:
            rooms[self.roomName.decode()].users.append(self.userId)
        except:
            badInput = True
        if(badInput == True):
            self.handler.send(b'NO ROOM WITH THAT NAME\n' + user.prompt())
            return
            
        user.locationOnServer = ServerLocation.inRoom
        user.setCurrentColor()
#        rooms[self.roomName.decode()].users.append(self.userId)
        user.currentRoom = rooms[self.roomName.decode()]
        users[self.userId] = user

        self.handler.send(b'Joining Room ' + self.roomName + b'\n')
        self.handler.send(b'Room Users: \n')
        for otherUserId in rooms[self.roomName.decode()].users:
            if (otherUserId == self.userId):
                self.handler.send(b'\t' + users[otherUserId].userNameInColor() + b' *<--(this is you)\n')
            else:
                otherUserHandler = userSockets[otherUserId]
                otherUserHandler.send(termCodes["DEL_LEFT"] + termCodes["MOV_BEG_LINE"] +
                                      user.userNameInColor() + b' has joined the room\n' + users[otherUserId].prompt())
                self.handler.send(b'\t' + users[otherUserId].userNameInColor() + b'\n')
        self.handler.send(user.prompt())
# JoinRoomAction\ Class:1 ends here

# [[file:parlance.org::*LeaveRoomAction%20Class][LeaveRoomAction\ Class:1]]
class LeaveRoomAction(Action):

    def __init__(self, newUserId):
        Action.__init__(self, newUserId)

    def execute(self, userSockets, users, rooms):
        super(LeaveRoomAction, self).execute(userSockets, users, rooms)

        roomName = users[self.userId].currentRoom.name

        user = users[self.userId]
        user.locationOnServer = ServerLocation.loggedIn
        rooms[roomName].users.remove(self.userId)


        for otherUserId in rooms[roomName].users:
            if(otherUserId != self.userId):
                otherUserHandler = userSockets[otherUserId]
                otherUserHandler.send(termCodes["DEL_LEFT"] + termCodes["MOV_BEG_LINE"] +
                                      user.userName.encode() + b' has left the room\n' + users[otherUserId].prompt())

        user.currentRoom = None
        users[self.userId] = user
            
        self.handler.send(termCodes["ERASE_PROMPT"] + termCodes["MOV_BEG_LINE"] +
                          b'You have left the room\n' + user.prompt())
# LeaveRoomAction\ Class:1 ends here

# [[file:parlance.org::*ListUsersAction%20Class][ListUsersAction\ Class:1]]
class ListUsersAction(Action):

    def __init__(self, newUserId):
        Action.__init__(self, newUserId)

    def execute(self, userSockets, users, rooms):
        super(ListUsersAction, self).execute(userSockets, users, rooms)

        roomName = users[self.userId].currentRoom.name
        self.handler.send(termCodes["ERASE_PROMPT"] + b'Room Users: \n')
        for otherUserId in rooms[roomName].users:
            if (otherUserId == self.userId):
                self.handler.send(b'\t' + users[otherUserId].userNameInColor() + b' *<--(this is you)\n')
            else:
                self.handler.send(b'\t' + users[otherUserId].userNameInColor() + b'\n')
        self.handler.send(users[self.userId].prompt())
# ListUsersAction\ Class:1 ends here

# [[file:parlance.org::*NewColorAction%20Class][NewColorAction\ Class:1]]
class NewColorAction(Action):

    def __init__(self, newUserId):
        Action.__init__(self, newUserId)

    def execute(self, userSockets, users, rooms):
        super(NewColorAction, self).execute(userSockets, users, rooms)

        user = users[self.userId]
        roomName = user.currentRoom.name
        user.setCurrentColor()
        users[self.userId] = user
        
        for otherUserId in rooms[roomName].users:
            if(otherUserId != self.userId):
                otherHandler = userSockets[otherUserId]
                otherHandler.send( termCodes["DEL_LEFT"] + termCodes["MOV_BEG_LINE"] + user.userNameInColor() +
                                   b' has changed color\n' + users[otherUserId].prompt())
            else:
                self.handler.send(termCodes["ERASE_PROMPT"] + users[otherUserId].userNameInColor() +
                                   b' has changed color\n' + user.prompt())
# NewColorAction\ Class:1 ends here

# [[file:parlance.org::*QuitChatAction%20Class][QuitChatAction\ Class:1]]
class QuitChatAction(Action):

    def __init__(self, newUserId):
        Action.__init__(self, newUserId)

    def execute(self, userSockets, users, rooms):
        super(QuitChatAction, self).execute(userSockets, users, rooms)
        users.pop(self.userId)
        self.handler.send(b'Bye!!!! Come back soon!!!\n')
        self.handler.shutdown(socket.SHUT_RDWR)
        self.handler.close()
# QuitChatAction\ Class:1 ends here

# [[file:parlance.org::*MessageAction%20Class][MessageAction\ Class:1]]
class MessageAction(Action):

    message = None

    def __init__(self, newUserId, newMessage):
        Action.__init__(self, newUserId)
        self.message = newMessage

    def execute(self, userSockets, users, rooms):
        super(MessageAction, self).execute(userSockets, users, rooms)
        for otherUserId in users[self.userId].currentRoom.users:
            if(otherUserId != self.userId):
                otherUserHandler = userSockets[otherUserId]
                otherUserHandler.send( termCodes["DEL_LEFT"] + termCodes["MOV_BEG_LINE"] +
                                       users[self.userId].userNameInColor() + b'>>' + self.message +
                                       b'\n' + users[otherUserId].prompt())
            else:
                self.handler.send(termCodes["ERASE_PROMPT"] + termCodes["MOV_BEG_LINE"] +
                                       users[self.userId].userNameInColor() + b'>>' + self.message +
                                       b'\n' + users[self.userId].prompt())
# MessageAction\ Class:1 ends here

# [[file:parlance.org::*CommandParser%20Class][CommandParser\ Class:1]]
class CommandParser():

    commandTreeOuterCopy = None
    commandData = None
    userId = None

    helpBanner = b'\n<<----------------------?!? HELP ?!?---------------------->>\n'
    helpBannerEnd = b'\n<<-------------------------------------------------------->>\n\n'

    def __init__(self):
        pass
        
    def message(self):
        messageAction = MessageAction(self.userId.encode(), self.commandData.encode())
        ParlanceServer.actionQueue.put(messageAction)

    def loginUser(self):
        loginAction = LoginAction(self.userId.encode(), self.commandData.encode())
        ParlanceServer.actionQueue.put(loginAction)

    def loggedInNoCommand(self):
        ParlanceServer.userSockets[self.userId].send(termCodes["ERASE_PROMPT"] +
                                                     b'SORRY - COMMAND NOT RECOGNIZED\n' +
                                                     ParlanceServer.users[self.userId].prompt())

    def generalHelp(self):
        ParlanceServer.userSockets[self.userId].send(termCodes["ERASE_PROMPT"] +
                                                     self.helpBanner + b'Available commands are:\n')
        for command in self.commandTreeOuterCopy[ParlanceServer.users[self.userId].locationOnServer]['/'].keys():
            if (command != 9999):
                ParlanceServer.userSockets[self.userId].send(b'\t\t\t/' + command.encode() + b'\n')
        ParlanceServer.userSockets[self.userId].send(b'\nFor help on a specific command, \n\t' +
                                                     b'replace the "/" command character with "?" ' +
                                                     b'\nfor example:\n\t"?JOIN" prints the help for '+
                                                     b'the command "/JOIN"' + self.helpBannerEnd)
        ParlanceServer.userSockets[self.userId].send(ParlanceServer.users[self.userId].prompt())

    def commandHelpHeader(self):
        ParlanceServer.userSockets[self.userId].send(termCodes["ERASE_PROMPT"] + self.helpBanner)
        
    def commandHelpFooter(self):
        ParlanceServer.userSockets[self.userId].send(self.helpBannerEnd +
                                                     ParlanceServer.users[self.userId].prompt())

    def inRoomNoCommand(self):
        if(self.commandData[0] == "/"):
            ParlanceServer.userSockets[self.userId].send(termCodes["ERASE_PROMPT"] +
                                                         b'SORRY - COMMAND NOT RECOGNIZED\n' +
                                                         ParlanceServer.users[self.userId].prompt())
            return
        self.message()
        
    def joinRoom(self):
        if(self.commandData == None):
            self.commandData = ""
        joinRoomAction = JoinRoomAction(self.userId.encode(), self.commandData.encode())
        ParlanceServer.actionQueue.put(joinRoomAction)

    def joinRoomHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'JOIN - used to join a chat room,\n\tfor example '+
                                                     b'"/JOIN FunChat"')
        self.commandHelpFooter()

    def listRooms(self):
        listRoomsAction = ListRoomsAction(self.userId.encode())
        ParlanceServer.actionQueue.put(listRoomsAction)

    def listRoomsHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'LIST - used to list all available chat rooms\n')
        ParlanceServer.userSockets[self.userId].send(b'\t ROOMS is a synonym for LIST')
        self.commandHelpFooter()

    def createRoom(self):
        if(self.commandData == None):
            ParlanceServer.userSockets[self.userId].send(termCodes["ERASE_PROMPT"] +
                                                         b'Please provide a name for the new room.\n' +
                                                         ParlanceServer.users[self.userId].prompt())
            return
        createRoomAction = CreateRoomAction(self.userId.encode(), self.commandData.encode())
        ParlanceServer.actionQueue.put(createRoomAction)

    def createRoomHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'/CREATE - used to create a new chat room,\n\t' +
                                                     b'for example "/CREATE FunChat".\nRooms must be one ' +
                                                     b'word with no special characters.')
        self.commandHelpFooter()

    def leaveRoom(self):
        leaveRoomAction = LeaveRoomAction(self.userId.encode())
        ParlanceServer.actionQueue.put(leaveRoomAction)

    def leaveRoomHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'/LEAVE - used to leave this chat room')
        self.commandHelpFooter()

    def quitChat(self):
        quitChatAction = QuitChatAction(self.userId.encode())
        ParlanceServer.actionQueue.put(quitChatAction)

    def quitChatHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'/QUIT - used to disconnect from Parlance.')
        self.commandHelpFooter()

    def listUsers(self):
        listUsersAction = ListUsersAction(self.userId.encode())
        ParlanceServer.actionQueue.put(listUsersAction)
        
    def listUsersHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'/LIST - lists all users in this chat room.')
        self.commandHelpFooter()

    def newColor(self):
        newColorAction = NewColorAction(self.userId.encode())
        ParlanceServer.actionQueue.put(newColorAction)

    def newColorHelp(self):
        self.commandHelpHeader()
        ParlanceServer.userSockets[self.userId].send(b'/NEWCOLOR - selects a new color at random for your user')
        self.commandHelpFooter()
       
    def parse(self, handler, userId, command):

        self.userId = userId

        commandTree = {
            ServerLocation.notLoggedIn : self.loginUser,
            ServerLocation.loggedIn : {
                '/' : {
                    'JOIN' : self.joinRoom,
                    'LIST' : self.listRooms,
                    'ROOMS' : self.listRooms,
                    'CREATE' : self.createRoom,
                    'QUIT' : self.quitChat,
                    9999 : self.loggedInNoCommand
                },
                '?' : {
                    'JOIN' : self.joinRoomHelp,
                    'LIST' : self.listRoomsHelp,
                    'ROOMS' : self.listRoomsHelp,
                    'CREATE' : self.createRoomHelp,
                    'QUIT' : self.quitChatHelp,
                    9999 : self.generalHelp
                },
                9999 : self.loggedInNoCommand
            },
            ServerLocation.inRoom : {
                '/' : {
                    'LIST' : self.listUsers,
                    'LEAVE' : self.leaveRoom,
                    'NEWCOLOR' : self.newColor,
                    9999 : self.inRoomNoCommand
                },
                '?' : {
                    'LIST' : self.listUsersHelp,
                    'LEAVE' : self.leaveRoomHelp,
                    'NEWCOLOR' : self.newColorHelp,
                    9999 : self.generalHelp
                },
                9999 : self.inRoomNoCommand
            }
        }

        self.commandTreeOuterCopy = commandTree
        
        commandFunction = commandTree[ParlanceServer.users[userId].locationOnServer]
        commandString = ansi_escape.sub('', b''.join(command).decode())
        if(commandString == ''):
            ParlanceServer.userSockets[self.userId].send(ParlanceServer.users[self.userId].prompt())
            return

        if (not hasattr(commandFunction, '__call__')):
            try:
                try:
                    self.commandData = commandString.split()[1]
                except IndexError:
                    self.commandData = None
                commandFunction = commandFunction[commandString[0]]
                commandFunction = commandFunction[commandString.split()[0].upper()[1:]]
            except KeyError:
                self.commandData = commandString
                commandFunction = commandFunction[9999]
        else:
            self.commandData = commandString

        commandFunction()
# CommandParser\ Class:1 ends here

# [[file:parlance.org::*ProcessActionQueue%20Global%20Function][ProcessActionQueue\ Global\ Function:1]]
def ProcessActionQueue(actionQueueToProcess, userSockets, users, rooms):
    while True:
        action = actionQueueToProcess.get()
        action.execute(userSockets, users, rooms)
# ProcessActionQueue\ Global\ Function:1 ends here

# [[file:parlance.org::*ParlanceHandler%20Class][ParlanceHandler\ Class:1]]
class ParlanceHandler(asynchat.async_chat):

    LINE_TERMINATOR     = b'\r\n'
    commandParser = CommandParser()
    userId = None

    def __init__(self, userId, conn_sock, client_address, server):
        asynchat.async_chat.__init__(self, conn_sock)

        self.server             = server
        self.client_address     = client_address
        self.ibuffer            = []

        self.set_terminator(self.LINE_TERMINATOR)
        self.userId = userId
        self.send(termCodes["CLR_SCR"] + termCodes["MOV_TOP_LEFT"] + parlanceLogo + b'\n\t' + parlanceAcronym)
        self.send(b'\n\nWelome to Parlance\nWhat is your name?:')

    def collect_incoming_data(self, data):
        log.debug("collect_incoming_data: [%s]" % data)
        self.ibuffer = []
        self.ibuffer.append(data)

    def found_terminator(self):
        log.debug("found_terminator")        
        ParlanceServer.userSockets[self.userId] = self.socket
        self.commandParser.parse(self, self.userId, self.ibuffer)

    def handle_close(self):
        log.info("conn_closed: client_address=%s:%s" % \
                     (self.client_address[0],
                      self.client_address[1]))

        asynchat.async_chat.handle_close(self)
# ParlanceHandler\ Class:1 ends here

# [[file:parlance.org::*ParlanceServer%20Class][ParlanceServer\ Class:1]]
class ParlanceServer(asyncore.dispatcher):

        manager = Manager()

        actionQueue = manager.Queue()

        rooms = manager.dict()
        users = manager.dict()
        userSockets = manager.dict()

        allow_reuse_address         = True
        request_queue_size          = 5
        address_family              = socket.AF_INET
        socket_type                 = socket.SOCK_STREAM


        def __init__(self, address, cpus, handlerClass=ParlanceHandler):
            self.address = address
            self.handlerClass       = handlerClass

            asyncore.dispatcher.__init__(self)

            self.create_socket(self.address_family,
                               self.socket_type)

            self.server_bind()
            self.server_activate()


        def server_bind(self):
            if self.allow_reuse_address:
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.bind(self.address)
            log.debug("bind: address=%s:%s" , self.address[0], self.address[1])


        def server_activate(self):
            self.listen(self.request_queue_size)
            log.debug("listen: backlog=%d" , self.request_queue_size)

                
        def fileno(self):
            return self.socket.fileno()


        def serve_forever(self):
            for cpuNum in range(min(cpus,multiprocessing.cpu_count())):
                processActionQueue_Process = mp.Process(target=ProcessActionQueue, 
                                                        args=(self.actionQueue,self.userSockets,
                                                              self.users, self.rooms))
                processActionQueue_Process.daemon = True
                processActionQueue_Process.start()
                log.info("server_proc_started: pid=%d" , processActionQueue_Process.pid)
            asyncore.loop()


        def handle_accepted(self, sock, addr):
            user = User()
            self.users[user.userId] = user
            if self.verify_request(sock, addr):
                self.process_request(user.userId, sock, addr)


        def verify_request(self, conn_sock, client_address):
            return True


        def process_request(self, userId, conn_sock, client_address):
            log.info("conn_made: client_address=%s:%s" , \
                     client_address[0],
                     client_address[1])
            self.handlerClass(userId, conn_sock, client_address, self)


        def handle_close(self):
            self.close()    


        def server_shutDown(self):
            self.close()
# ParlanceServer\ Class:1 ends here

# [[file:parlance.org::*Main%20Application/Module%20Entrypoint][Main\ Application/Module\ Entrypoint:1]]
if __name__ == "__main__":
     parser = argparse.ArgumentParser()
     #parser.add_argument("-t", "--tests", action="count", help="run unittests")
     parser.add_argument("-c", "--cpus", help="maximum CPUs to use, otherwise all CPUs are used")
     parser.add_argument("-a", "--address", help="IP address or hostname to serve on")
     parser.add_argument("-p", "--port", help="IP port to serve on")
     parser.add_argument("-m", "--mpdebug", action = "count", help="Enable debug level logging of multiprocessing code")
     args = parser.parse_args()

     cpus = 9999
     address = 'localhost'
     port = 12345
     
     #if(args.tests != None):
     #     unittest.TextTestRunner().run(suite())
     #else:
     if(args.cpus != None):
          cpus = int(args.cpus)
     if(args.address != None):
          address = args.address
     if(args.port != None):
          port = int(args.port)
     if(args.mpdebug != None):
          logger = multiprocessing.log_to_stderr()
          logger.setLevel(multiprocessing.SUBDEBUG)

     parlanceServer = ParlanceServer((address, port), cpus)
     parlanceServer.serve_forever()    
# Main\ Application/Module\ Entrypoint:1 ends here
