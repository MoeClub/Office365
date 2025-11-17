#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Author:  MoeClub.org
from sys import flags

# pip3 install aiohttp aiohttp-socks
from aiohttp import client
from aiohttp_socks import ProxyConnector, ProxyType
from urllib import parse
import argparse
import asyncio
import base64
import time
import json
import random
import os


class Utils:
    @staticmethod
    async def http(method, url, headers=None, cookies=None, data=None, redirect=True, Proxy=None, timeout=30, loop=None):
        method = str(method).strip().upper()
        assert method in ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"], "HTTP Method Not Allowed [{}].".format(method)
        if headers:
            Headers = {str(key).strip(): str(value).strip() for (key, value) in headers.items()}
        else:
            Headers = {"User-Agent": "Mozilla/5.0", "Accept-Encoding": ""}
        respData = {"code": 555, "data": b"", "headers": None, "cookies": None, "url": None, "req": None, "err": ""}
        resp = None
        Connector = client.TCPConnector(ssl=False, force_close=True, enable_cleanup_closed=True, use_dns_cache=False)
        if Proxy is not None or str(Proxy).strip() != "":
            proxyParsed = parse.urlparse(str(Proxy).strip())
            if proxyParsed.scheme in ["socks5"]:
                proxyType = ProxyType.SOCKS5
            elif proxyParsed.scheme in ["socks4"]:
                proxyType = ProxyType.SOCKS4
            elif proxyParsed.scheme in ["http", "https"]:
                proxyType = ProxyType.HTTP
            else:
                proxyType = None
            if proxyType is not None:
                try:
                    username, password = (parse.unquote(proxyParsed.username), parse.unquote(proxyParsed.password))
                except:
                    username, password = ('', '')
                Connector = ProxyConnector(proxy_type=proxyType, host=proxyParsed.hostname, port=proxyParsed.port, username=username, password=password, rdns=None, ssl=False, force_close=True, enable_cleanup_closed=True, use_dns_cache=False)
        try:
            async with client.request(method=method, url=url, headers=Headers, cookies=cookies, data=data, timeout=client.ClientTimeout(total=timeout), allow_redirects=redirect, raise_for_status=False, connector=Connector, loop=loop) as resp:
                respData["data"] = await resp.read()
                respData["code"] = resp.status
                respData["headers"] = resp.headers
                respData["cookies"] = resp.cookies
                # respData["url"] = resp.url
                # respData["req"] = resp.request_info
        except Exception as e:
            if respData["code"] is None:
                respData["code"] = 555
            if respData["data"] is None:
                respData["data"] = b""
            respData["err"] = str(e)
        if Connector is not None and Connector.closed is False:
            await Connector.close()
        if resp is not None and resp.closed is False:
            resp.close()
        return respData

    @staticmethod
    def uniRand(x=3, y=3, t="l"):
        # z, n, l, u, h, H, o, j, k
        r, s = [], ""
        for c in t:
            if c in ["z"]:
                # g = ("4E00", "9FCB")
                g = [("4E00", "9FA5")]
            elif c in ["n"]:
                g = [("30", "39")]
            elif c in ["l"]:
                g = [("61", "7A")]
            elif c in ["u"]:
                g = [("41", "5A")]
            elif c in ["h"]:
                g = [("30", "39"), ("61", "66")]
            elif c in ["H"]:
                g = [("30", "39"), ("41", "46")]
            elif c in ["o"]:
                g = [("30", "37")]
            elif c in ["j"]:
                g = [("3041", "3096"), ("30A0", "30FF"), ("31F0", "31FF")]
            elif c in ["k"]:
                g = [("AC00", "D7A3")]
            else:
                g = []
            r += g
        if len(r) > 0:
            rand = random.Random()
            n = rand.randint(min(x, y), max(x, y))
            for _ in range(n):
                v = rand.sample(r, 1)[0]
                s += '\\u{:04X}'.format(rand.randint(int(v[0], 16), int(v[1], 16))).encode().decode("unicode_escape")
        return s



class MS365:
    def __init__(self, tenantId, clientId, clientSecret, apiVersion = "v1.0"):
        self.apiVersion = apiVersion
        self.clientId = clientId
        self.clientSecret = clientSecret
        self.tenantId = tenantId
        self.userStatus = False
        self.userToken = {"expires": 0, "access_token": ""}
        self.userDomain = None
        self.userDomainDefault = None
        self.userDomainList = list()
        self.userLic = dict()
        self.urlToken = "https://login.microsoftonline.com/{}/oauth2/token"
        # self.urlSource = "https://graph.windows.net"
        self.urlSource = "https://graph.microsoft.com"
        self.roleMap = {}

    def headers(self, **kwargs):
        hdr = {
            "User-Agent": "ADAL/{}".format(self.apiVersion),
            "Accept": "application/json",
            "Accept-Encoding": "",
        }
        if "access_token" in self.userToken and "expires" in self.userToken and self.userToken["expires"] > int(time.time()):
            hdr["Authorization"] = str("Bearer {}").format(self.userToken["access_token"])
        for key in kwargs:
            hdr[key] = kwargs[key]
        return hdr

    def readJWT(self, jwt=None):
        try:
            jwtArray = str(jwt).split('.')
            assert len(jwtArray) == 3, "Is Not JWT."
            jwt = json.loads(base64.b64decode(jwtArray[1] + '=' * (4 - len(jwtArray[1]) % 4)).decode())
            if "roles" in jwt and len(jwt["roles"]) > 0:
                print("Roles: {}".format(",".join(sorted(jwt["roles"]))), flush=True)
        except Exception as e:
            jwt = {}
        return jwt

    async def login(self, domain=None):
        try:
            headers = self.headers(**{"Content-Type": "application/x-www-form-urlencoded"})
            url = self.urlToken.format(self.tenantId)
            raw = {
                "grant_type": "client_credentials",
                # "tenant": self.tenantId,
                "client_id": self.clientId,
                "client_secret": self.clientSecret,
                "resource": self.urlSource,
            }
            data = "&".join([str("{}={}").format(parse.quote_plus(str(item).strip()),parse.quote_plus(str(raw[item]).strip())) for item in raw])
            resp = await Utils.http("POST", url=url, headers=headers, data=data)
            assert resp["code"] == 200, "HTTP_{}".format(resp["code"])
            respData = json.loads(resp["data"].decode())
            assert "access_token" in respData, "Login Fail"
            self.userToken["expires"] = int(respData["expires_on"])
            self.userToken["access_token"] = respData["access_token"]
            jwt = self.readJWT(jwt=respData["access_token"])
            self.userStatus = True
            await self.getDomain(domain=domain)
            await self.getLicense()
            await self.getRole()
            await self.getAdmin()
            # asyncio.ensure_future(cls.getDomain(DefaultDomian=cls.userDomain), loop=loop)
            # asyncio.ensure_future(cls.getLicense(), loop=loop)
        except Exception as e:
            self.userStatus = False
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return self.userStatus

    async def getAdmin(self, name=True):
        adminUnit = {}
        try:
            assert self.userStatus, "No Login"
            reqString = "roleManagement/directory/roleAssignments?$expand=principal"
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            headers = self.headers(**{"Content-Type": "application/json"})
            resp = await Utils.http("GET", url, headers, data=None)
            assert resp["code"] in [200, 201], "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            for item in respJson["value"]:
                if 'principalId' in item and 'roleDefinitionId' in item and "principal" in item:
                    roleName = item["roleDefinitionId"] if name is not True else self.roleMap.get(item["roleDefinitionId"], item["roleDefinitionId"])
                    if roleName not in adminUnit:
                        adminUnit[roleName] = []
                    meta = str(item["principal"]['@odata.type']).split(".")[-1].lower()
                    if meta == "user":
                        adminUnit[roleName].append({
                            "meta": "user",
                            'enable': item["principal"]['accountEnabled'],
                            "name": item["principal"]['displayName'],
                            "id": item["principal"]["id"],
                            'user': item["principal"]["userPrincipalName"],
                            "licenses": [] if 'assignedLicenses' not in item["principal"] else [lic['skuId'] for lic in item["principal"]['assignedLicenses'] if 'skuId' in lic],
                            'created': item["principal"]["createdDateTime"],
                        })
                    elif meta == "serviceprincipal":
                        adminUnit[roleName].append({
                            "meta": "app",
                            'enable': item["principal"]['accountEnabled'],
                            "name": item["principal"]['displayName'],
                            "id": item["principal"]["id"],
                            'user': item["principal"]['appId'],
                            "licenses": [] if 'assignedLicenses' not in item["principal"] else [lic['skuId'] for lic in item["principal"]['assignedLicenses'] if 'skuId' in lic],
                            'created': item["principal"]["createdDateTime"],
                        })
            print("\n".join([str("{}: {}").format(adminName, ",".join([str("[{}]{}").format(user["meta"], user["user"]) for user in adminUnit[adminName]])) for adminName in adminUnit]), flush=True)
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return adminUnit

    async def getRole(self):
        try:
            assert self.userStatus, "No Login"
            reqString = "roleManagement/directory/roleDefinitions"
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            resp = await Utils.http("GET", url=url, headers=self.headers())
            assert resp["code"] == 200, "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            if "value" in respJson:
                for item in respJson["value"]:
                    if "isEnabled" in item and item["isEnabled"] is True:
                        # self.roleMap[item["displayName"]] = item["id"]
                        self.roleMap[item["id"]] = item["displayName"]
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return self.roleMap

    async def getDomain(self, domain=None):
        try:
            assert self.userStatus, "No Login"
            self.userDomainList = list()
            reqString = "domains"
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            resp = await Utils.http("GET", url=url, headers=self.headers())
            assert resp["code"] == 200, "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            if "value" in respJson:
                for item in respJson["value"]:
                    if item["isVerified"]:
                        self.userDomainList.append(item["id"])
                    if item["isDefault"]:
                        self.userDomainDefault = item["id"]
            if len(self.userDomainList) > 0:
                print("Domains: {}".format(",".join(self.userDomainList)), flush=True)
            if domain and domain in self.userDomainList:
                self.userDomain = domain
            else:
                self.userDomain = self.userDomainDefault
        except Exception as e:
            self.userDomain = None
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return self.userDomain

    async def getLicense(self):
        try:
            assert self.userStatus, "No Login"
            self.userLic = dict()
            reqString = "subscribedSkus"
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            resp = await Utils.http("GET", url=url, headers=self.headers())
            assert resp["code"] == 200, "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            if "value" in respJson:
                for item in respJson["value"]:
                    if item["capabilityStatus"] == "Enabled":
                        if item["skuId"] in self.userLic:
                            self.userLic[item["skuId"]]["Units"] += self.userLic[item["skuId"]]["Units"]
                            self.userLic[item["skuId"]]["Used"] += self.userLic[item["skuId"]]["Used"]
                        else:
                            self.userLic[item["skuId"]] = {
                                "Units": item["prepaidUnits"]["enabled"],
                                "Used": item["consumedUnits"],
                                "skuName": item["skuPartNumber"],
                                "skuId": item["skuId"],
                            }
            if len(self.userLic) > 0:
                print("Licenses: {}".format("; ".join([str("({}/{}) {}").format(self.userLic[item]["Used"], self.userLic[item]["Units"], self.userLic[item]["skuId"]) for item in self.userLic])), flush=True)
        except Exception as e:
            self.userLic = dict()
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return self.userLic

    async def getUser(self, user=None, nextLink=None):
        result = list()
        try:
            reqString = "users{}?$select=accountEnabled,id,displayName,userPrincipalName,assignedLicenses,createdDateTime".format("" if user is None or user == "" else "/{}".format(user))
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            if nextLink is not None and "skiptoken=" in nextLink:
                url = nextLink
            headers = self.headers()
            headers["Content-type"] = "application/json"
            resp = await Utils.http("GET", url, headers, data=None)
            assert resp["code"] in [200, 201], "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            if "value" in respJson:
                for item in respJson["value"]:
                    user = {
                        "enable": item["accountEnabled"],
                        "name": item['displayName'],
                        "id": item["id"],
                        "user": item['userPrincipalName'],
                        # "password": None,
                        "licenses": [] if 'assignedLicenses' not in item else [lic['skuId'] for lic in item['assignedLicenses'] if 'skuId' in lic],
                        "created": item['createdDateTime'] if 'createdDateTime' in item else None,
                    }
                    result.append(user)
            else:
                user = {
                    "enable": respJson["accountEnabled"],
                    "name": respJson['displayName'],
                    "id": respJson["id"],
                    "user": respJson['userPrincipalName'],
                    # "password": None,
                    "licenses": [] if 'assignedLicenses' not in respJson else [lic['skuId'] for lic in respJson['assignedLicenses'] if 'skuId' in lic],
                    "created": respJson['createdDateTime'] if 'createdDateTime' in respJson else None,
                }
                result.append(user)
            if '@odata.nextLink' in respJson:
                result += await self.getUser(user=user, nextLink=respJson['@odata.nextLink'])
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return result

    async def addUser(self, newUser=None, newPasswd=None, nickName=None, domain=None, licenses=None, roles=None):
        if newUser is None or newUser == "":
            newUser = Utils.uniRand(7, 7, "l")
        if newPasswd is None or newPasswd == "":
            newPasswd = Utils.uniRand(5, 5, "lun") + Utils.uniRand(1, 2, "n") + Utils.uniRand(1, 2, "u") + Utils.uniRand(1, 2, "l")
        if "@" in newUser:
            newUserArray = str(newUser).rsplit("@", 1)
            domain = newUserArray[-1]
            newUser = newUserArray[0]
        if domain and domain not in self.userDomainList:
            domain = None
        if domain is None:
            domain = self.userDomain
        if nickName is None or nickName == "":
            nickName = newUser
        newUserName = str("{}@{}").format(newUser, domain)
        userDetails = {
            "accountEnabled": True,
            "userPrincipalName": "{}".format(newUserName),
            "displayName": nickName,
            "mailNickname": nickName,
            "usageLocation": "HK",
            "passwordPolicies": "DisableStrongPassword, DisablePasswordExpiration",
            "passwordProfile": {
                "forceChangePasswordNextSignIn": False,
                "password": newPasswd,
            }
        }
        reqString = "users"
        url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
        headers = self.headers()
        headers["Content-type"] = "application/json"
        resp = await Utils.http("POST", url, headers, data=json.dumps(userDetails, ensure_ascii=False))
        assert resp["code"] in [200, 201], "HTTP_{}".format(resp["code"])
        respJson = json.loads(resp["data"].decode())
        user = {
            "name": respJson['displayName'],
            "id": respJson["id"],
            "user": respJson['userPrincipalName'],
            "password": newPasswd,
            "licenses": [],
            "roles": [],
        }
        if licenses is not None and licenses != "":
            user["licenses"] += await self.assignLic(userId=respJson["id"], license=licenses)
        if roles is not None and roles != "":
            await asyncio.sleep(10)
            for role in str(roles).split(","):
                if len(role) != 36:
                    role = self.roleMap.get(role, "")
                if len(role) != 36:
                    continue
                user["roles"] += await self.assignRole(userId=respJson["id"], roleId=role)
        return user

    async def delUser(self, user):
        try:
            reqString = "users/{}".format(user)
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            headers = self.headers()
            headers["Content-type"] = "application/json"
            resp = await Utils.http("DELETE", url, headers, data=None)
            assert resp["code"] in [200, 201, 204], "HTTP_{}".format(resp["code"])
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
            return False
        return True

    async def addUsers(self, num=1, prefix=None, newPasswd=None, licenses=None, domain=None, co=12):
        result = list()
        try:
            assert self.userStatus, "No Login"
            assert len(self.userLic) > 0, "No Licenses"
            ok, at = 0, 0
            task, task2 = set(), set()
            # lic = ",".join(self.userLic.keys())
            while ok < num:
                if len(task) < co and at < num:
                    newUser = (str(prefix).strip() if prefix is not None and prefix != "" else Utils.uniRand(3, 3 , "l")) + Utils.uniRand(5, 5, "n")
                    task.add(asyncio.ensure_future(self.addUser(newUser=newUser, newPasswd=newPasswd, licenses=licenses, domain=domain)))
                    at += 1
                    continue
                done, task = await asyncio.wait(task, return_when=asyncio.FIRST_COMPLETED)
                for item in done:
                    r = item.result()
                    if isinstance(r, dict) and "licenses" in r and len(r["licenses"]) > 0:
                        ok += 1
                        print(str("{};{}").format(r["user"], r["password"]), flush=True)
                        result.append(r)
                    else:
                        at -= 1
                        if isinstance(r, dict) and "id" in r and len(r["id"]) > 0:
                            task2.add(asyncio.ensure_future(self.delUser(user=r["id"])))
            if len(task2) > 0:
                await asyncio.wait(task2)
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return result

    async def assignRole(self, userId, roleId=None, name=True, delay=0):
        userRole = list()
        try:
            assert self.userStatus, "No Login"
            assert isinstance(roleId, str) and len(roleId) == 36, "Invalid Role"
            assert isinstance(userId, str) and (len(userId) == 36 or "@" in userId), "Invalid UserId"
            if "@" in userId:
                users= await self.getUser(user=userId)
                assert len(users) == 1, "Invalid User"
                userId = users[0].get("id", None)
                assert isinstance(roleId, str) and len(roleId) == 36, "Invalid UserId"
            if delay > 0:
                await asyncio.sleep(delay=delay)
            data = {"directoryScopeId": "/", "roleDefinitionId": roleId, "principalId": userId}
            reqString = "roleManagement/directory/roleAssignments"
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            headers = self.headers()
            headers["Content-type"] = "application/json"
            resp = await Utils.http("POST", url, headers, data=json.dumps(data, ensure_ascii=False))
            assert resp["code"] in [200, 201], "HTTP_{}".format(resp["code"])
            respJson = json.loads(resp["data"].decode())
            if "roleDefinitionId" in respJson:
                userRole.append(respJson["roleDefinitionId"] if name is not True else self.roleMap.get(respJson["roleDefinitionId"], respJson["roleDefinitionId"]))
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return userRole

    async def assignLic(self, userId, license=None, delay=0):
        userLic = list()
        try:
            assert self.userStatus, "No Login"
            if delay > 0:
                await asyncio.sleep(delay=delay)
            data = {"addLicenses": [], "removeLicenses": []}
            if license is not None:
                userLic = [str(item).strip() for item in str(license).split(",") if str(item).strip() != "" and str(item).strip() in self.userLic]
                for item in userLic:
                    data["addLicenses"].append({"disabledPlans": [], "skuId": item})
            assert len(data["addLicenses"]) > 0, "No Licenses"
            reqString = "users/{}/assignLicense".format(userId)
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            headers = self.headers()
            headers["Content-type"] = "application/json"
            resp = await Utils.http("POST", url, headers, data=json.dumps(data, ensure_ascii=False))
            assert resp["code"] in [200, 201], "HTTP_{}".format(resp["code"])
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return userLic

    async def resetPassword(self, user, newPasswd=None):
        try:
            if newPasswd is None or newPasswd == "":
                newPasswd = Utils.uniRand(5, 5, "lun") + Utils.uniRand(1, 2, "n") + Utils.uniRand(1, 2,"u") + Utils.uniRand(1, 2, "l")
            reqString = "users/{}".format(user)
            url = str("{}/{}/{}").format(self.urlSource, self.apiVersion, reqString)
            headers = self.headers()
            headers["Content-type"] = "application/json"
            data = {
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": False,
                    "password": newPasswd,
                }
            }
            resp = await Utils.http("PATCH", url, headers, data=json.dumps(data, ensure_ascii=False))
            assert resp["code"] in [200, 201, 204], "HTTP_{}".format(resp["code"])
            return newPasswd
        except Exception as e:
            print(str("{}: {}").format(os.sys._getframe().f_code.co_name, e), flush=True)
        return None


class Task:
    @staticmethod
    async def do(**kwargs):
        st = time.time()
        result = None
        ms = MS365(tenantId=kwargs["tenantId"], clientId=kwargs["clientId"], clientSecret=kwargs["clientSecret"])
        assert await ms.login(domain=kwargs["domain"]), "Login Failed"
        if kwargs["delete"] is None:
            lic = sorted([(ms.userLic[lic]["skuId"], (ms.userLic[lic]["Units"] - ms.userLic[lic]["Used"])) for lic in ms.userLic], key=lambda l: l[1])
            if kwargs["num"] < 1:
                pass
            elif kwargs["num"] == 1:
                result = await ms.addUser(newUser=kwargs["newUser"], newPasswd=kwargs["newPasswd"], domain=ms.userDomain, licenses=lic[0][0] if len(lic) > 0 else None)
                print(json.dumps(result, indent=4, ensure_ascii=False), flush=True)
            else:
                result = await ms.addUsers(num=kwargs["num"], prefix=kwargs["prefix"], newPasswd=kwargs["newPasswd"], domain=ms.userDomain, licenses=lic[0][0] if len(lic) > 0 else None)
        else:
            results = []
            if kwargs["delete"] == "_ALL_":
                users = await ms.getUser()
                print("User Count: {}".format(len(users)), flush=True)
                for user in users:
                    status = await ms.delUser(user=user["id"])
                    print(str("DELETE[{}]: {}").format(user["user"], status), flush=True)
                    results.append(status)
            else:
                status = await ms.delUser(user=kwargs["delete"])
                print(str("DELETE[{}]: {}").format(kwargs["delete"], status), flush=True)
                results.append(status)
            result = True if False not in results else False
        print("Time: %.02fs" % (time.time() - st), flush=True)
        return result


if __name__ == "__main__":
    st = time.time()
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--tenantId", type=str, default=None, help="Tenant Id")
    parser.add_argument("-c", "--clientId", type=str, default=None, help="Client Id")
    parser.add_argument("-s", "--clientSecret", type=str, default=None, help="Client Secret")
    parser.add_argument("-n", "--num", type=int, default=0, help="User Number")
    parser.add_argument("-u", "--newUser", type=str, default=None, help="User Name")
    parser.add_argument("-p", "--newPasswd", type=str, default=None, help="User Password")
    parser.add_argument("-d", "--domain", type=str, default=None, help="Use Domain")
    parser.add_argument("-prefix", type=str, default=None, help="User Prefix")
    parser.add_argument("-del", "--delete", type=str, default=None, help="Delete User")
    args = parser.parse_args()
    argsResetLength = len([setattr(args, kv[0], parser.get_default(kv[0])) for kv in args._get_kwargs() if kv[1] == ""])
    loop.run_until_complete(Task.do(**args.__dict__))
