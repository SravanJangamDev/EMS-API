from wsgiref.simple_server import make_server
import falcon
import json
import os
from helper import Logger, ClientException, InternalException, Database
from middlewares import LogReqResp, HandleCORS, Authenticate
from config import (
    errorFile,
    schemaFile,
    dbBaseDir,
    reqRespLogFile,
    internalErrorMsg,
    serveOnPort,
    Debug,
)

# ***** Gloabl variable declaration ****************
lastEmpID = "EMP0000000"
DB: Database
employees: dict = {}
schema: dict
logger: Logger


def readSchemaFile(filename: str) -> dict:
    data = {}
    try:
        with open(filename, "r") as f:
            data = json.load(f)

        return data
    except Exception as e:
        raise InternalException("Schema file read failed.", excp=e)


def validateReqBody(schema: dict, reqBody: dict, checkMandatroy: bool = False) -> None:
    """
    Validates request body:
    possible validations:
    1. data type
    2. string length
    3. integer range
    4. pattern matching(emails)
    ...
    """
    error_msg = []
    if checkMandatroy:
        mandatoryAttrs = [attr for attr, val in schema.items() if val.get("mandatory")]
        for attr in mandatoryAttrs:
            if attr not in reqBody:
                error_msg.append(f"{attr} is required.")

    if error_msg:
        raise ClientException("Invalid reqbody: " + " ".join(error_msg))

    for attr, value in reqBody.items():
        if attr not in schema:
            error_msg.append(f"Unknown attribute {attr}")
            continue

        actualType = type(value).__name__
        attrSchema = schema.get(attr, {})
        reqType = attrSchema.get("dataType")
        if reqType != actualType:
            error_msg.append(f"{attr} should be of type {reqType}")
            continue

        if isinstance(value, list):
            for val in value:
                validateReqBody(attrSchema.get("subType", {}), val)

        if isinstance(value, dict):
            validateReqBody(attrSchema.get("subType", {}), value)

    if error_msg:
        raise ClientException("Invalid reqbody: " + ", ".join(error_msg))


def createEmpID() -> str:
    """
    creates New employee ID for employee creation.
    """
    global lastEmpID

    count = int(lastEmpID.replace("EMP", "")) + 1
    lastEmpID = "EMP" + str(count).rjust(7, "0")
    return lastEmpID


def isDuplicate(email: str) -> bool:
    """
    checks for duplicate email ID.
    """
    global employees
    for _, emp in employees.items():
        if emp.get("email") == email:
            return True

    return False


def initialSetup() -> None:
    """
    create initial setups like db connection, ..etc.
    """
    global DB
    global employees
    global schema
    global logger
    global lastEmpID
    global Debug

    DB = Database(dbBaseDir)
    if not os.path.exists(f"{dbBaseDir}/employee"):
        os.mkdir(f"{dbBaseDir}/employee")

    if not os.path.exists(".log"):
        os.mkdir(".log")

    empIDs = []
    emps = DB.getAllRecords("employee")
    for emp in emps:
        empId = emp.get("regId")
        empIDs.append(empId)
        employees[empId] = emp

    empIDs = sorted(empIDs)
    if empIDs:
        lastEmpID = empIDs[-1]

    schema = readSchemaFile(schemaFile)
    os.environ["LOG_FILE"] = errorFile
    os.environ["REQ_RESP_LOG_FILE"] = reqRespLogFile
    if Debug:
        os.environ["DEBUG"] = "true"

    logger = Logger(errorFile)


class EmployeeResource:
    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        global DB
        global logger

        params = req.params
        regId = params.get("regId", "")
        result: list = []
        msg = "Employee details found"
        statusCode = 200
        try:
            if regId:
                result = [DB.getRecord("employee", regId)]

            else:
                result = DB.getAllRecords("employee")

            result = list(sorted(result, key=lambda x: x.get("regId"), reverse=True))

        except (ClientException, InternalException) as e:
            msg, statusCode = e.msg, e.statusCode

        except Exception as e:
            logger.logError(internalErrorMsg, 500, excp=e)
            msg, statusCode = internalErrorMsg, 500

        data = {"message": msg, "success": True}
        resp.status = statusCode
        data["employees"] = result

        resp.body = json.dumps(data)

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        global DB
        global schema
        global logger
        global employees

        msg = "Employee created successfully"
        statusCode = 200
        regId = ""
        try:
            reqBody = req.media
            empSchema = schema.get("employee", {})
            validateReqBody(empSchema, reqBody, checkMandatroy=True)
            email = reqBody.get("email")
            if isDuplicate(email):
                raise ClientException("Employee already exists.")

            regId = createEmpID()
            reqBody["regId"] = regId
            DB.insertRecord("employee", regId, reqBody)
            employees[regId] = reqBody
        except (ClientException, InternalException) as e:
            msg, statusCode = e.msg, e.statusCode

        except Exception as e:
            logger.logError(internalErrorMsg, 500, excp=e)
            msg, statusCode = internalErrorMsg, 500

        resp.status = statusCode
        data = {"message": msg, "success": True}
        if regId:
            data["regId"] = regId

        resp.body = json.dumps(data)

    def on_put(self, req: falcon.Request, resp: falcon.Response) -> None:
        global DB
        global schema
        global logger
        global employees

        msg = "Employee Updated successfully"
        statusCode = 200
        regId = ""
        try:
            reqBody = req.media
            empSchema = schema.get("employee", {})
            validateReqBody(empSchema, reqBody)
            regId = reqBody.get("regId")
            reqBody.pop("regId", None)
            DB.updateRecord("employee", regId, reqBody)
            employees[regId] = {**employees.get(regId, {}), **reqBody}
        except (ClientException, InternalException) as e:
            msg, statusCode = e.msg, e.statusCode

        except Exception as e:
            logger.logError(internalErrorMsg, 500, excp=e)
            msg, statusCode = internalErrorMsg, 500

        resp.status = statusCode
        data = {"message": msg, "success": True}
        resp.body = json.dumps(data)

    def on_delete(self, req: falcon.Request, resp: falcon.Response) -> None:
        global DB
        global schema
        global logger
        global employees

        msg = "Employee Deleted successfully"
        statusCode = 200
        regId = ""
        try:
            reqBody = req.media
            regId = reqBody.get("regId", "")
            reqBody.pop("regId", None)
            DB.deleteRecord("employee", regId)
            employees.pop(regId)
        except (ClientException, InternalException) as e:
            msg, statusCode = e.msg, e.statusCode

        except Exception as e:
            logger.logError(internalErrorMsg, 500, excp=e)
            msg, statusCode = internalErrorMsg, 500

        resp.status = statusCode
        data = {"message": msg, "success": True}
        resp.body = json.dumps(data)


# Create Initial setups
initialSetup()

app = falcon.App(middleware=[LogReqResp(), Authenticate(), HandleCORS()])

app.add_route("/api/employee", EmployeeResource())


if __name__ == "__main__":
    with make_server("", serveOnPort, app) as httpd:
        print(f"Serving on port {serveOnPort} ...")

        # Serve until process is killed
        httpd.serve_forever()
