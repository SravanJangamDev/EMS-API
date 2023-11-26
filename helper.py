import os
import json
from datetime import datetime
from typing import Optional
import sys


class Logger(object):
    def __init__(self, logFile: str = ""):
        if not logFile:
            logFile = os.getenv("LOG_FILE", ".log.json")

        self.logFile = logFile

    def __writeLog(self, data: dict) -> None:
        try:
            with open(self.logFile, "a") as f:
                f.write(f"{json.dumps(data)}\n")
        except Exception:
            sys.stdout.write(f"{json.dumps(data)}\n")

    def logData(self, data: dict) -> None:
        data["date"] = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        self.__writeLog(data)

    def logInfo(
        self,
        msg: str,
        statusCode: Optional[int] = None,
        excp: Optional[Exception] = None,
        family: str = "info",
    ) -> None:
        debug = os.getenv("DEBUG", "false").lower() == "true"
        if not debug:
            return

        data = {
            "type": "INFO",
            "msg": msg,
            "family": family,
            "status_code": statusCode,
            "date": datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
            "family": family,
        }
        if excp:
            data["exception"] = str(excp)

        self.__writeLog(data)

    def logError(
        self,
        msg: str,
        statusCode: Optional[int] = None,
        excp: Optional[Exception] = None,
        family: str = "error",
    ) -> None:
        data = {
            "type": "ERROR",
            "msg": msg,
            "status_code": statusCode,
            "date": datetime.now().strftime("%Y-%m-%d %H-%M-%S"),
            "family": family,
        }
        if excp:
            data["exception"] = str(excp)

        self.__writeLog(data)


class ClientException(Exception):
    logger: Optional[Logger] = None

    def __init__(
        self,
        msg: str,
        statusCode: int = 400,
        displayMsg: str = "Bad Request",
        excp: Optional[Exception] = None,
    ):
        self.msg = msg
        self.statusCode = statusCode
        self.displayMsg = displayMsg
        self.excp = excp

        if self.logger is None:
            self.logger = Logger()

        self.logger.logInfo(msg, statusCode, excp)

    def __str__(self) -> str:
        if self.excp:
            return f"{self.excp.__class__.__name__}: {self.msg}"

        else:
            return f"ClientException: {self.msg}"


class InternalException(Exception):
    logger: Optional[Logger] = None

    def __init__(
        self,
        msg: str,
        statusCode: int = 500,
        displayMsg: str = "Something went wrong. Please contact admin.",
        excp: Optional[Exception] = None,
    ):
        self.msg = msg
        self.statusCode = statusCode
        self.displayMsg = displayMsg
        self.excp = excp

        if self.logger is None:
            self.logger = Logger()

        self.logger.logError(msg, statusCode, excp)

    def __str__(self) -> str:
        if self.excp:
            return f"{self.excp.__class__.__name__}: {self.msg}"

        else:
            return f"InternalException: {self.msg}"


def createFile(folder: str, filename: str, data: dict) -> None:
    try:
        if not os.path.exists(folder):
            os.mkdir(folder)

        with open(f"{folder}/{filename}.json", "w") as f:
            json.dump(data, f)

    except Exception as e:
        raise InternalException(f"File: {filename} creation failed.", excp=e)


def updateFile(folder: str, filename: str, data: dict) -> None:
    try:
        with open(f"{folder}/{filename}.json", "w") as f:
            json.dump(data, f)

    except Exception as e:
        raise InternalException(f"File: {filename} update failed.", excp=e)


def readFile(folder: str, filename: str) -> dict:
    data = {}
    try:
        with open(f"{folder}/{filename}.json", "r") as f:
            data = json.load(f)

        return data
    except Exception as e:
        raise InternalException(f"File: {filename} read failed.", excp=e)


def deleteFile(folder: str, filename: str) -> None:
    try:
        os.remove(f"{folder}/{filename}.json")
    except Exception as e:
        raise InternalException(f"File: {filename} delete failed.", excp=e)


def isFileNotExists(folder: str, filename: str) -> bool:
    return not os.path.exists(f"{folder}/{filename}.json")


def isFileExists(folder: str, filename: str) -> bool:
    return os.path.exists(f"{folder}/{filename}.json")


def readFolder(folder: str, fileContent: bool = True) -> list:
    files = []
    try:
        files = os.listdir(folder)
        files = [f.replace(".json", "") for f in files if not f.startswith(".")]
    except Exception as e:
        raise InternalException(f"Folder: {folder} read failed.", excp=e)

    if not fileContent:
        return files

    filesData = []
    for filename in files:
        filesData.append(readFile(folder, filename))

    return filesData


class Database(object):
    def __init__(self, dbDir: str = "."):
        try:
            if not os.path.exists(dbDir):
                os.makedirs(dbDir)

        except Exception as e:
            raise InternalException("DataBase connection failed.", excp=e)

        self.dbDir = dbDir

    def insertRecord(self, table: str, filename: str, data: dict) -> None:
        if isFileExists(f"{self.dbDir}/{table}", filename):
            raise ClientException(f"{table.capitalize()} {filename} already exists.")

        createFile(f"{self.dbDir}/{table}", filename, data)

    def updateRecord(self, table: str, filename: str, data: dict) -> None:
        if isFileNotExists(f"{self.dbDir}/{table}", filename):
            raise ClientException(f"{table.capitalize()} {filename} not found.")

        prevData = readFile(f"{self.dbDir}/{table}", filename)
        updatedData = {**prevData, **data}
        updateFile(f"{self.dbDir}/{table}", filename, updatedData)

    def deleteRecord(self, table: str, filename: str) -> None:
        if isFileNotExists(f"{self.dbDir}/{table}", filename):
            raise ClientException(f"{table.capitalize()} {filename} not found.")

        deleteFile(f"{self.dbDir}/{table}", filename)

    def getRecord(self, table: str, filename: str) -> dict:
        if isFileNotExists(f"{self.dbDir}/{table}", filename):
            raise ClientException(f"{table.capitalize()} {filename} not found.")

        data = readFile(f"{self.dbDir}/{table}", filename)
        return data

    def getAllRecords(self, table: str) -> list:
        data = readFolder(f"{self.dbDir}/{table}", fileContent=True)
        return data
