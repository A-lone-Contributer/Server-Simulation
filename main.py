import logging
import socket
import threading
from logging.config import fileConfig
from time import sleep

import requestsHandler
import serverExceptions

fileConfig('logging.ini')
logger = logging.getLogger('dev')


class Server:
    __server_instance = None

    @staticmethod
    def getInstance():
        """Static Access Method"""
        if Server.__server_instance is None:
            Server(host, port)
        return Server.__server_instance

    def __init__(self, host, port, retry_attempts=5, tries_delay=2):
        """Initialise server

        Args:
            host (str): host to connect 
            port (int): port to connect
            retry_attempts (int, optional): retry attempts before exit. Defaults to 5.
            tries_delay (int, optional): delay between retry attempts. Defaults to 2.

        Raises:
            Exception: Singleton class 
        """

        if Server.__server_instance is not None:
            raise Exception("This class is a singleton class!")
        else:
            Server.__server_instance = self
            self.__host = host
            self.__port = port
            self.__retry_attempts = retry_attempts
            self.__tries_delay = tries_delay
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            logging.info("[STARTING] Server is starting...")

    def connect(self, attempts=0):
        """Connect to server

        Args:
            attempts (int, optional): number of attempts before exit (defaults to 0)

        Raises:
            serverExceptions.PortAlreadyInUseException: port is already in use

        Returns:
            object: socket object
        """
        if attempts < self.__retry_attempts:
            try:
                self.socket.bind((self.__host, self.__port))
                self.socket.listen(1)
                logging.info(
                    f"[LISTENING] Server is listening on {self.__host}:{self.__port}\n")
                return self.socket
            except (OSError, PermissionError, ValueError):
                logging.warning(f"Trying connecting in {self.__tries_delay} sec...")
                sleep(self.__tries_delay)
                self.connect(attempts + 1)

        logging.error(f"{self.__port} is already in use!")
        raise serverExceptions.PortAlreadyInUseException


if __name__ == "__main__":
    host = socket.gethostbyname(socket.gethostname())
    port = 8000
    server = Server(host, port).getInstance()
    server_socket = server.connect()
    try:
        while True:
            client_socket, address = server_socket.accept()
            threading.Thread(target=requestsHandler.request_handler,
                             args=(client_socket, address),
                             daemon=True).start()

            logging.info(f"[ACTIVE CONNECTIONS] {threading.activeCount() - 1}\n")
    except Exception as e:
        logging.error("Unexpected error occurred, closing client and server...")
        server_socket.close()
        client_socket.close()
        logging.shutdown()
