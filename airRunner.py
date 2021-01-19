#! /usr/bin/env python3.6
#coding=utf-8

import json
from enum import Enum
from time import sleep

from airtest.cli.runner import AirtestCase, run_script
from argparse import *

from airtest.core.api import stop_app, start_app, connect_device
from airtest.core.helper import G
from .logAnalysis import myLogAnalysis, MakeAllLogData, getModelAir
import os
import shutil

from .startService import PerfdogService, SaveFormat
from .MakePrefData import MakeReportData


class PlatForm(Enum):
    Android = 1,
    IOS = 2

class airRunner(AirtestCase):
    def setUp(self):
        print("My setUp")
        super(airRunner,self).setUp()

    def tearDown(self):
        print("My testDown")
        super(airRunner, self).setUp()

    def stopApp(self,package,device):
        if G.DEVICE == None:
            connect_device(device)
        stop_app(package)


    def startApp(self,package,device):
        if G.DEVICE == None:
            connect_device(device)
        print("start_app(package)")
        print(start_app(package))

    def getUnrunCase(self,nowIndex,CaseList):
        if nowIndex >= len(CaseList):
            return None
        else :
            unrunList = []
            for case in CaseList[nowIndex:]:
                unrunList.append(case)
            return unrunList

    def makeUnrunData(self,unrunlist):
        unRunData = []
        if unrunlist != None and len(unrunlist) > 0:
            for case in unrunlist:
                caseName = case['caseName']
                model = ""
                case = caseName
                if '/' in caseName:
                    caseinfo = caseName.split('/')
                    model = caseinfo[0]
                    case = caseinfo[1]
                data = {'model':model,'case':case}
                unRunData.append(data)
        return unRunData



    def run_air(self,root_script,log_root,CaseList,device,prefObj = None,runPref = False,resetpath = False):
        # param  root_dir  脚本集合根目录
        # param  device    设备列表

        #结果集合
        results = []
        #日志目录
        #root_log = root_dir+'\\'+'log'
        root_log = log_root
        if os.path.exists(root_log):
            if os.path.isdir(root_log):
                shutil.rmtree(root_log)
        #     else:
        #         os.makedirs(root_log)
        #         print(str(root_log) + 'is created')
        #
        # os.makedirs(root_log)
        # print(str(root_log) + 'is created')
        mark = {}
        mark["AllPass"] = True
        mark["LastCase"] = ""
        args = None
        indx = 0
        for case in CaseList:
            caseName = case['caseName']
            if '/' in caseName:
                caseName = caseName.split('/')[1]

            if '.air' in caseName:
                caseName = caseName.replace('.air','')

            mark["LastCase"] = caseName
            print("CaseName: ",caseName)
            f,UpModel = getModelAir(caseName,root_script)

            if runPref and prefObj:
                prefObj.setlabel(caseName)

            airName = f
            airPath = f
            if UpModel != None:
                airPath = os.path.join(UpModel,f)

            script = os.path.join(root_script,airPath)

            log = os.path.join(log_root,airName.replace('.air',''))
            if os.path.isdir(log):
                shutil.rmtree(log)
            else:
                os.makedirs(log)
                print(str(log) + ' is created')

            if args == None:
                args = Namespace(device=device,log = log,recording=None,script=script,compress =10)
            else:
                args = Namespace(device=None, log=log, recording=None, script=script, compress=10)

            try:
                run_script(args,AirtestCase)
            except:
                pass
            finally:
                mylog = myLogAnalysis(script,log,"log.txt",caseName,resetpath)
                datas = mylog.makeData()
                result = {}
                if UpModel != None:
                    result['Modelname'] = UpModel
                result['Casename'] = airName.replace('.air','')
                result['result'] = datas['test_result']
                result['infos'] = datas
                result['mustPass'] = case['mustPass']
                results.append(result)
                print("Result :  ",result['result'])
                indx = indx + 1
                if case['mustPass'] == True and result['result'] == False :
                    print("当前用例 【%s】 未通过 后续用例不执行" % caseName)
                    mark["AllPass"] = False
                    print("UnrunCase list :")
                    unrun = self.makeUnrunData(self.getUnrunCase(indx, CaseList))
                    mark["unrun"] = unrun
                    data = {}
                    data["mark"] = mark
                    data["results"] = results
                    return data,True;



        print("UnrunCase list :")
        unrun = self.makeUnrunData(self.getUnrunCase(indx, CaseList))
        mark["unrun"] = unrun
        data = {}
        data["mark"] = mark
        data["results"] = results
        return data,False;



class myAirRunner():
    package = ""
    PerfToolPath = ""
    token = ""
    device = ""
    deviceUUid = ""
    perfDogLogPath = ""
    caseList = []
    airtestLogRoot = ""
    airtestScriptRoot = ""
    resetPath = False
    perfObj = None

    def __init__(self,package,platform,device,airtestLogRoot,airtestScriptRoot,perftool ="",perfToken ="",perfDogLogPath = "",resetpath = False):
        """
        :param package: 测试项目的包名
        :param platform: 所需测试的设备平台
        :param device: 所需测试的设备号
        :param airtestLogRoot: airtest测试Log日志文件保存位置
        :param airtestScriptRoot: airtest测试脚本根目录
        :param perftool: 性能狗Service 所在本地目录
        :param perfToken: 性能狗Service 令牌
        :param perfDogLogPath: 性能狗 数据日志保存目录
        :param resetpath: 重新配置路径，去掉绝对路径部分
        """
        self.package = package
        self.PerfToolPath = perftool
        self.token = perfToken
        self.perfDogLogPath = perfDogLogPath
        self.airtestLogRoot = airtestLogRoot
        self.airtestScriptRoot = airtestScriptRoot
        self.deviceUUid = device
        self.resetPath = resetpath


        if platform == PlatForm.Android:
            self.device = "Android:" + device
        elif platform == PlatForm.IOS:
            self.device = "iOS:" + device

    def CheckPrefInit(self):
        if self.token == None or self.token == "":
            return "PrefDog 初始化验证失败：Token信息缺失"
        if self.package == None or self.package == "":
            return "PrefDog 初始化验证失败：package信息缺失"
        if self.PerfToolPath == None or self.PerfToolPath == "":
            return "PrefDog 初始化验证失败：PrefToolPath信息缺失"
        if self.deviceUUid == None or self.deviceUUid == "":
            return "PrefDog 初始化验证失败：deviceUUid信息缺失"
        if self.perfDogLogPath == None or self.perfDogLogPath == "":
            return "PrefDog 初始化验证失败：prefDogLogPath信息缺失"

        return ""

    def RunAirWithCaseList(self,CaseList,PerfTestName,SaveLogFile ,runPerf,perfdogSaveFormat=SaveFormat.ALL,perfDogUploadServer = True):
        """
        :param CaseList: 需要运行的测试模块JSON 数据
        :param PerfTestName: 性能测试的测试名称
        :param SaveLogFile: 是否需要保存airtest 测试文本数据
        :param runPerf: 是否运行性能狗测试
        :param perfdogSaveFormat: 性能狗测试数据保存格式
        :param perfDogUploadServer: 性能狗测试数据是否上传性能狗网站
        """
        self.caseList = json.loads(CaseList)

        if runPerf:
            err = self.CheckPrefInit()
            if err == "":
                self.perfObj = PerfdogService(self.package,self.PerfToolPath,self.token,self.deviceUUid,self.perfDogLogPath,PerfTestName,perfdogSaveFormat,perfDogUploadServer)
                self.perfObj.initService()
                self.perfObj.startPerf()
            else:
                raise Exception("无法进行性能测试 ："+err)

        Runner = airRunner()
        Runner.stopApp(self.package,self.device)
        sleep(3)
        Runner.startApp(self.package,self.device)

        results,ErrOut = Runner.run_air(self.airtestScriptRoot,self.airtestLogRoot,self.caseList,self.device,self.perfObj,runPerf,self.resetPath)
        if runPerf:
            self.perfObj.StopPerf()
            saveJsonPath = os.path.abspath(os.path.join(os.path.dirname(self.perfDogLogPath), "ReportResult.json"))
            PerFDogLogFile = os.path.abspath(os.path.join(self.perfDogLogPath,PerfTestName+".json"))
            print("RepostResult.json path : ", saveJsonPath)
            MakeReportData(PerFDogLogFile, saveJsonPath)

        data = json.dumps(results)
        if SaveLogFile:
            saveFile = os.path.join(self.airtestLogRoot, "Resultdata.json")
            with open(saveFile, 'w') as f:
                f.write(data)
            f.close()
            print("AirtestLogPath: ",self.airtestLogRoot)
        if runPerf:
            print("prefDogLogPath: ", self.perfDogLogPath)

        print("Test Over")
        print("ErrOut :  ",ErrOut)
        Runner.stopApp(self.package,self.device)


if __name__ == "__main__":
    package = "com.ztgame.fangzhidalu"
    path = "C:/Work/PerfDog/PerfDogService(v4.3.200927-Win)/PerfDogService.exe"
    token = "e8e5734ad2f74176b368c956173c9bfbb3a85bd1ec676cbef4b90435234786c1"
    device = "UQG5T20409008785"
    prefDogLogPath = "C:/Work/airtest/MytestReport/"

    airtestLogRoot = "C:/Work/airtest/MytestReport/"
    airtestScriptRoot ="C:/Work/airtest/fangzhidalu/"
    CaseList = ['Login', 'runChallenge', 'stopGame']

    # myRunner = myAirRunner(package,device,airtestLogRoot,airtestScriptRoot,True,path,token,prefDogLogPath)
    # myRunner.RunAirWithCaseList(CaseList,"MyAirtestName")


    MakeAllLogData(CaseList, airtestScriptRoot, airtestLogRoot, airtestLogRoot)

