import re
import json
import logging
from logging.config import fileConfig

import serverExceptions

fileConfig('logging.ini')
logger = logging.getLogger('dev')

MAX_PACKET = 1024
FORMAT = 'utf-8'


def receive_data(socket):
    """Receive all incoming data from socket

    Args:
        socket (Socket): socket object

    Returns:
        str: request data
    """

    request_data = ""
    while True:
        msg = socket.recv(MAX_PACKET).decode(FORMAT)
        request_data += msg
        logging.info("Received all the request data from stream\n")
        return request_data


def get_request_components(request_data):
    """Get request components such as method, uri and protocol

    Args:
        request_data (string): client's request data

    Returns:
        list: request method, uri and protocol
    """
    request_head, request_body = request_data.split('\n', 1)
    request_method, request_uri, request_protocol = request_head.split(' ', 3)
    return request_method, request_uri, request_protocol


def process_request_data(data, method, protocol):
    """Process all the request data and query strings

    Args:
        data (str): request data
        method (str): request method
        protocol (str): request protocol

    Returns:
        dict: map of request endpoint type and query params
    """
    try:
        request_type = None
        query_params = {}

        pattern = re.compile(f"{method} (.*) {protocol}")
        m = re.search(pattern, data)

        if m is not None:
            url_data = m.group(1)
            if '?' in url_data:
                pattern = re.compile("^/(.*)[?](.*)")
                m2 = re.search(pattern, url_data)
                if m2 is not None:
                    request_type = m2.group(1)
                    arg_list = m2.group(2).split("&")
                    for elem in arg_list:
                        l1 = elem.split('=')
                        query_params[l1[0]] = l1[1]
            else:
                pattern = re.compile("^/(.*)")
                m2 = re.search(pattern, url_data)
                if m2 is not None:
                    request_type = m2.group(1)

        return {'type': request_type, 'args': query_params}

    except serverExceptions.RequestParsingException:
        logger.error("There was an error while parsing request data")


def request_validator(url_dict):
    parameters = url_dict['args'].keys()

    for parameter in parameters:
        if parameter not in ['timeout', 'connid']:
            return False

    return True


def get_response(response, protocol="HTTP/1.1", status=200, msg="OK "):
    response_data = {
        "protocol": protocol,
        "status": status,
        "status_text": msg,
        "data": json.dumps(response, indent=4, sort_keys=True)
    }

    return response_data
