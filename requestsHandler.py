import threading
from wsgiref.handlers import format_date_time
from datetime import datetime, timedelta
from time import mktime, sleep
import logging
from logging.config import fileConfig
import utils

fileConfig('logging.ini')
logger = logging.getLogger('dev')

# create a re-entrant lock
lock = threading.RLock()
thread_pool = {}

ENCODING_FORMAT = 'utf-8'
RESPONSE_FORMAT = 'application/json'


def request_handler(client_connection, address):
    """Handle all the incoming requests to the server

    Args:
        client_connection (Socket): client's socket connection object
        address (tuple): client's address
    """
    try:
        logging.info(f"[NEW CONNECTION] {address} connected.")

        global lock
        global thread_pool

        request_data = utils.receive_data(client_connection)

        print("HTTP REQUEST HEADERS")
        print("=" * 20)
        logging.info(request_data)

        request_method, request_uri, request_protocol = utils.get_request_components(request_data)
        url_dict = utils.process_request_data(request_data, request_method, request_protocol)

        is_request_valid = utils.request_validator(url_dict)

        if not is_request_valid:
            response_data = utils.get_response(response={'stat': 'route_not_found'},
                                               status=404,
                                               msg="NOT FOUND ")
            sendResponseToClient(client_connection, **response_data)
            return

        # Handling '/sleep' endpoints
        if url_dict['type'] == "v1/sleep" and url_dict['args']:
            sleepRouteHandler(url_dict, client_connection)

        # Handling '/server-status' endpoints
        elif url_dict['type'] == "v1/server-status":
            serverStatusRouteHandler(client_connection)

        # handling '/kill' endpoint
        elif url_dict['type'] == "v1/kill" and url_dict['args']:
            if request_method == 'POST':
                killConnectionRouteHandler(url_dict, client_connection)
            else:
                response_data = utils.get_response(response={'stat': 'Use the POST method instead'},
                                                   status=404,
                                                   msg="NOT FOUND ")
                sendResponseToClient(client_connection, **response_data)


        # handling unknown routes
        else:
            response_data = utils.get_response(response={'stat': 'route_not_found'},
                                               status=404,
                                               msg="NOT FOUND ")
            sendResponseToClient(client_connection, **response_data)

    except Exception as e:
        logging.error("Something went wrong!")
        response_data = utils.get_response(response={'stat': 'failed'},
                                           status=500,
                                           msg="Internal Server Error ")
        sendResponseToClient(client_connection, **response_data)


def serverStatusRouteHandler(client_connection):
    now = datetime.now()

    lock.acquire()
    server_status = {}
    for connection_id in thread_pool:
        server_status[connection_id] = {}
        server_status[connection_id]['remaining_time'] = int(
            thread_pool[connection_id]['timeout'] - (now - thread_pool[connection_id]['end_time']).seconds)
    lock.release()

    response_data = utils.get_response(server_status)
    sendResponseToClient(client_connection, **response_data)


def sleepRouteHandler(url_dict, client_connection):
    lock.acquire()
    if url_dict['args']['connid'] in thread_pool.keys():
        lock.release()
        return
    else:
        connection_id = url_dict['args']['connid']
        timeout = int(url_dict['args']["timeout"])

        thread_pool[connection_id] = {}
        thread_pool[connection_id]['threadID'] = threading.current_thread()
        thread_pool[connection_id]['start_time'] = datetime.now()
        thread_pool[connection_id]['timeout'] = timeout
        thread_pool[connection_id]['end_time'] = thread_pool[connection_id]['start_time'] + timedelta(
            milliseconds=timeout)
        thread_pool[connection_id]['client'] = client_connection
        lock.release()

        logging.info(f"Sleeping for {str(timeout)} seconds\n")
        sleep(timeout)

        logging.info(f"Deleting entry from thread pool for connection id: {connection_id}\n")

        lock.acquire()
        if connection_id in thread_pool.keys():
            del thread_pool[connection_id]
        else:
            logging.error("Connection ID doesn't exist!")
        lock.release()

        response_data = utils.get_response({'stat': 'ok'})
        sendResponseToClient(client_connection, **response_data)


def killConnectionRouteHandler(url_dict, client_connection):
    lock.acquire()

    connection_id = url_dict['args']['connid']
    if connection_id in thread_pool.keys():
        # send killed status to connection we are closing
        response_data = utils.get_response({'stat': 'killed'})
        sendResponseToClient(thread_pool[connection_id]['client'], **response_data)

        # delete the connection
        del thread_pool[connection_id]

        # send response to kill thread
        logging.info(f"Closed connection with id: {connection_id}")
        response_data = utils.get_response({'stat': 'ok'})
        sendResponseToClient(client_connection, **response_data)

    else:
        logging.warning("Connection ID doesn't exist!")
        response_data = utils.get_response({'stat': 'connection_not_found'})
        sendResponseToClient(client_connection, **response_data)

    lock.release()


def sendResponseToClient(client, **response_data):
    """Send response to the client address

    Args:
        client (Socket): client's socket connection object
    """

    response_body_raw = response_data['data']
    response_headers = {
        'Content-Type': f'{RESPONSE_FORMAT}; encoding={ENCODING_FORMAT}',
        'Content-Length': len(response_body_raw),
        "Date": format_date_time(mktime(datetime.now().timetuple())),
        "Server": "Simulated Server v1",
        'Connection': 'close'
    }

    try:
        response_headers_raw = ''.join('%s: %s\n' % (k, v)
                                       for k, v in response_headers.items())

        # Send responses to client
        client.send(f'{response_data["protocol"]} {response_data["status"]} {response_data["status_text"]}'
                    .encode(ENCODING_FORMAT))
        client.send(response_headers_raw.encode(ENCODING_FORMAT))
        # newline to separate headers from body
        client.send('\n'.encode(ENCODING_FORMAT))
        client.send(response_body_raw.encode(ENCODING_FORMAT))

        logging.info("Sent response to client\n")
    except Exception as e:
        print(e)
        logging.error("Failed to send response!")
        return
