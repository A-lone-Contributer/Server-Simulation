"""
This file contains custom server exceptions
"""


class ServerException(Exception):
    """ Base class for user defined exceptions """
    pass


class PortAlreadyInUseException(ServerException):
    def __init__(self, message="This port is already in use\n"):
        self.message = message
        super().__init__(self.message)


class ConnectionNotExist(ServerException):
    def __init__(self, connection_id, message="does not exist."):
        self.message = message
        self.connection_id = connection_id
        super().__init__(self.message)

    def __str__(self):
        return f'Connection ID: {self.connection_id} {self.message}\n'


class RequestParsingException(ServerException):
    def __init__(self, message="There was some error in parsing the request\n"):
        self.message = message
        super().__init__(self.message)
