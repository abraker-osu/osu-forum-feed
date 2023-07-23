import requests
import logging
import json


class DiscordClient():

    session = requests.session()

    REQUEST_NOP           = 0
    REQUEST_COMMENT_EVENT = 1
    REQUEST_POST_EVENT    = 2

    logger = logging.getLogger(__name__)

    @staticmethod
    def request(port: int, route: str, data: dict):
        try: response = DiscordClient.session.post(f'http://127.0.0.1:{port}/{route}', json=data)
        except requests.exceptions.ConnectionError as e:
            DiscordClient.logger.error(e)
            return

        #status = DbClient.validate_response(response)
        data = json.loads(response.text)
        DiscordClient.logger.debug(data)


    ''' TODO
    @staticmethod
    def validate_response(response):
        status_code = response.status_code

        if response.status_code == 200: return 200  # Ok
        if response.status_code == 400: raise Exception(SessionMgr._logger, 'Error 400: Unable to process request')
        if response.status_code == 401: return 401  # Need to log in
        if response.status_code == 403: return 403  # Forbidden
        if response.status_code == 404: return 404  # Resource not found
        if response.status_code == 405: raise Exception(SessionMgr._logger, 'Error 405: Method not allowed')
        if response.status_code == 407: raise Exception(SessionMgr._logger, 'Error 407: Proxy authentication required')
        if response.status_code == 408: raise Exception(SessionMgr._logger, 'Error 408: Request timeout')
        if response.status_code == 429: return 429  # Too many requests
        if response.status_code == 500: raise Exception(SessionMgr._logger, 'Error 500: Internal server error')
        if response.status_code == 502: raise Exception(SessionMgr._logger, 'Error 502: Bad Gateway')
        if response.status_code == 503: raise Exception(SessionMgr._logger, 'Error 503: Service unavailable')
        if response.status_code == 504: raise Exception(SessionMgr._logger, 'Error 504: Gateway timeout')
    '''
