import time
from typing import Any, Tuple
import falcon
from falcon.http_status import HTTPStatus  # type: ignore
import uuid
import os
from helper import Logger
from datetime import datetime


# ***************** Handle cors middleware
class HandleCORS(object):
    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        resp.set_header("Access-Control-Allow-Origin", "*")
        resp.set_header("Access-Control-Allow-Methods", "*")
        resp.set_header("Access-Control-Allow-Headers", "*")
        resp.set_header("Access-Control-Allow-Credentials", True)
        resp.set_header("Access-Control-Max-Age", 1728000)  # 20 days
        if req.method == "OPTIONS":
            raise HTTPStatus(falcon.HTTP_200, body="\n")


# *********** LogRequest middleware ***************************


class LogReqResp(object):
    def __init__(self):
        reqRespLogFile = os.getenv("REQ_RESP_LOG_FILE", ".req_resp_log.json")
        self.logger = Logger(reqRespLogFile)

    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        trackerId = uuid.uuid4().hex
        resp.append_header("tracker_id", trackerId)
        resp.append_header("arrived_at", time.time())

        data = {
            "type": "REQUEST",
            "tracker_id": trackerId,
            "remote_addr": req.remote_addr,
            "params": req.params,
            "path": req.path,
            "method": req.method,
            "headers": req.headers,
            "time_stamp": str(datetime.now()),
        }
        if req.method in ["POST", "PATCH", "PU"]:
            data["body"] = req.media

        self.logger.logData(data)

    def process_response(
        self: Any,
        req: falcon.Request,
        resp: falcon.Response,
        resource: Any,
        req_succeeded: Any,
    ) -> None:
        from datetime import datetime

        responseTime = time.time() - float(resp.get_header("arrived_at", 0))
        data = {
            "type": "RESPONSE",
            "tracker_id": resp.get_header("tracker_id", 0),
            "status": resp.status,
            "headers": resp.headers,
            "body": resp.body,
            "time_stamp": str(datetime.now()),
            "response_time": responseTime,
        }
        self.logger.logData(data)


# ***************** Authentication middleware **********************
class Authenticate(object):
    def process_request(self, req: falcon.Request, resp: falcon.Response) -> None:
        pass

    def process_response(
        self: Any,
        req: falcon.Request,
        resp: falcon.Response,
        resource: Any,
        req_succeeded: Any,
    ) -> None:
        pass
