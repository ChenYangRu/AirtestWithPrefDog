import json
from enum import Enum

from airtest.cli.runner import AirtestCase, run_script
from argparse import *

from airtest.core.api import stop_app, start_app, connect_device

from .logAnalysis import myLogAnalysis, MakeAllLogData
import os
import shutil

from .startService import PerfdogService, SaveFormat


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

    def getModelAir(self,modelName,root_dir):
        for f in os.listdir(root_dir):
            if f.endswith(".air"):
                temp = f.split('.')
                if(temp[0] == modelName):
                    return f
    def stopApp(self,package,device):
        from airtest.core.helper import G
        if G.DEVICE == None:
            connect_device(device)
        stop_app(package)

    def startApp(self,package,device):
        from airtest.core.helper import G
        if G.DEVICE == None:
            connect_device(device)
        start_app(package)

    def run_air(self,root_script,log_root,ModelList,device,prefObj = None,runPref = False):
        # param  root_dir  脚本集合根目录
        # param  device    设备列表

        #结果集合
        results = []
        #日志目录
        #root_log = root_dir+'\\'+'log'
        root_log = log_root
        if os.path.isdir(root_log):
            shutil.rmtree(root_log)
        else:
            os.makedirs(root_log)
            print(str(root_log) + 'is created')

        mark = {}
        mark["AllPass"] = True
        mark["LastModel"] = ""

        args = None
        for model in ModelList:
            print("model : ",model)
            modelName = model['modelName']
            mark["LastModel"] = modelName
            f = self.getModelAir(modelName,root_script)
            if runPref and prefObj:
                prefObj.setlabel(modelName)

            airName = f
            script = os.path.join(root_script,f)

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
                mylog = myLogAnalysis(script,log,"log.txt",modelName)
                datas = mylog.makeData()
                result = {}
                result['name'] = airName.replace('.air','')
                result['result'] = datas['test_result']
                result['infos'] = datas
                result['mustPass'] = model['MustPass']
                results.append(result)
                print("Result :  ",result['result'])
                if model['MustPass'] == True and result['result'] == False :
                    print("当前模块 【%s】 未通过 后续模块不执行" % modelName)
                    mark["AllPass"] = False
                    data = {}
                    data["mark"] = mark
                    data["results"] = results
                    return data,True;
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
    modelList = []
    airtestLogRoot = ""
    airtestScriptRoot = ""

    perfObj = None

    def __init__(self,package,platform,device,airtestLogRoot,airtestScriptRoot,perftool ="",perfToken ="",perfDogLogPath = ""):
        """
        :param package: 测试项目的包名
        :param platform: 所需测试的设备平台
        :param device: 所需测试的设备号
        :param airtestLogRoot: airtest测试Log日志文件保存位置
        :param airtestScriptRoot: airtest测试脚本根目录
        :param perftool: 性能狗Service 所在本地目录
        :param perfToken: 性能狗Service 令牌
        :param perfDogLogPath: 性能狗 数据日志保存目录
        """
        self.package = package
        self.PerfToolPath = perftool
        self.token = perfToken
        self.perfDogLogPath = perfDogLogPath
        self.airtestLogRoot = airtestLogRoot
        self.airtestScriptRoot = airtestScriptRoot
        self.deviceUUid = device

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

    def RunAirWithModelList(self,ModelList,PerfTestName,SaveLogFile ,runPerf,perfdogSaveFormat=SaveFormat.ALL,perfDogUploadServer = True):
        """
        :param ModelList: 需要运行的测试模块JSON 数据
        :param PerfTestName: 性能测试的测试名称
        :param SaveLogFile: 是否需要保存airtest 测试文本数据
        :param runPerf: 是否运行性能狗测试
        :param perfdogSaveFormat: 性能狗测试数据保存格式
        :param perfDogUploadServer: 性能狗测试数据是否上传性能狗网站
        """
        self.modelList = json.loads(ModelList)

        if runPerf:
            err = self.CheckPrefInit()
            if err == "":
                self.perfObj = PerfdogService(self.package,self.PerfToolPath,self.token,self.deviceUUid,self.perfDogLogPath,PerfTestName,perfdogSaveFormat,perfDogUploadServer)
                self.perfObj.initService()
                self.perfObj.startPerf()
            else:
                raise "无法进行性能测试 ："+err

        Runner = airRunner()
        Runner.stopApp(self.package,self.device)
        Runner.startApp(self.package,self.device)

        results,ErrOut = Runner.run_air(self.airtestScriptRoot,self.airtestLogRoot,self.modelList,self.device,self.perfObj,runPerf)
        if runPerf:
            self.perfObj.StopPerf()
        data = json.dumps(results)
        if SaveLogFile:
            saveFile = os.path.join(self.airtestLogRoot, "Resultdata.json")
            with open(saveFile, 'w') as f:
                f.write(data)
            f.close()

            #MakeAllLogData(self.modelList, self.airtestScriptRoot, self.airtestLogRoot,self.airtestLogRoot)
            print("AirtestLogPath: ",self.airtestLogRoot)

        if runPerf:
            print("prefDogLogPath: ", self.perfDogLogPath)

        print("Test Over")
        print("ErrOut :  ",ErrOut)

        if ErrOut:
            Runner.stopApp(self.package,self.device)


if __name__ == "__main__":
    package = "com.ztgame.fangzhidalu"
    path = "C:/Work/PerfDog/PerfDogService(v4.3.200927-Win)/PerfDogService.exe"
    token = "e8e5734ad2f74176b368c956173c9bfbb3a85bd1ec676cbef4b90435234786c1"
    device = "UQG5T20409008785"
    prefDogLogPath = "C:/Work/airtest/MytestReport/"

    airtestLogRoot = "C:/Work/airtest/MytestReport/"
    airtestScriptRoot ="C:/Work/airtest/fangzhidalu/"
    ModelList = ['Login', 'runChallenge', 'stopGame']

    # myRunner = myAirRunner(package,device,airtestLogRoot,airtestScriptRoot,True,path,token,prefDogLogPath)
    # myRunner.RunAirWithModelList(ModelList,"MyAirtestName")


    MakeAllLogData(ModelList, airtestScriptRoot, airtestLogRoot, airtestLogRoot)

