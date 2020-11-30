import subprocess
import threading
import time
import traceback

import grpc

from prefDog import perfdog_pb2, perfdog_pb2_grpc


class PerfdogService():
    packageName = ''
    PerfdogPath = ''
    Token = ''
    stub = None
    device = None
    caseName = ''
    deviceUuid = ''
    saveJsonPath = './perfdog_service_output'

    def __init__(self,packageName,perfdogPath,token,casename,deviceuuid,saveJsonPath='./perfdog_service_output'):
        self.packageName = packageName
        self.PerfdogPath = perfdogPath
        self.Token = token
        self.caseName = casename
        self.deviceUuid = deviceuuid
        self.saveJsonPath = saveJsonPath


    def initService(self):
        try:
            print("0 启动PerfDogService")
            # 填入PerfDogService的路径
            perfDogService = subprocess.Popen(self.PerfdogPath)
            # 等待PerfDogService启动完毕
            time.sleep(5)
            print("1.通过ip和端口连接到PerfDog Service")
            options = [('grpc.max_receive_message_length', 100 * 1024 * 1024)]
            channel = grpc.insecure_channel('127.0.0.1:23456', options=options)
            print("2.新建一个stub,通过这个stub对象可以调用所有服务器提供的接口")
            self.stub = perfdog_pb2_grpc.PerfDogServiceStub(channel)
            print("3.通过令牌登录，令牌可以在官网申请")
            userInfo = self.stub.loginWithToken(
                perfdog_pb2.Token(token=self.Token))
            print("UserInfo:\n", userInfo)
            print("4.启动设备监听器监听设备,每当设备插入和移除时会收到一个DeviceEvent")
            deviceEventIterator = self.stub.startDeviceMonitor(perfdog_pb2.Empty())
            for deviceEvent in deviceEventIterator:
                # 从DeviceEvent中获取到device对象，device对象会在后面的接口中用到
                self.device = deviceEvent.device
                if deviceEvent.eventType == perfdog_pb2.ADD:
                    print("设备[%s:%s]插入\n" % (self.device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(self.device.conType)))
                    # 每台手机会返回两个conType不同的设备对象(USB的和WIFI的),如果是测有线，取其中的USB对象
                    if self.device.conType == perfdog_pb2.USB:
                        if self.device.uid == self.deviceUuid:
                            print("5.初始化设备[%s:%s]\n" % (self.device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(self.device.conType)))
                            self.stub.initDevice(self.device)
                            print("5.初始化设备 完成\n" )
                            break
                elif deviceEvent.eventType == perfdog_pb2.REMOVE:
                    print("设备[%s:%s]移除\n" % (self.device.uid, perfdog_pb2.DEVICE_CONTYPE.Name(self.device.conType)))
        except Exception as e:
            traceback.print_exc()

    def startPerf(self):
        try:
            print("6.获取app列表")
            appList = self.stub.getAppList(self.device)
            apps = appList.app
            app = self.selectApp(apps)

            print("7.获取设备的详细信息")
            deviceInfo = self.stub.getDeviceInfo(self.device)
            print("8.开启性能数据项")
            self.stub.enablePerfDataType(
                perfdog_pb2.EnablePerfDataTypeReq(device=self.device, type=perfdog_pb2.NETWORK_USAGE))
            print("9.开始收集[%s:%s]的性能数据\n" % (app.label, app.packageName))

            print(self.stub.startTestApp(perfdog_pb2.StartTestAppReq(device=self.device, app=app)))

            req = perfdog_pb2.OpenPerfDataStreamReq(device=self.device)
            perfDataIterator = self.stub.openPerfDataStream(req)

            # def perf_data_process():
            #     for perfData in perfDataIterator:
            #         print(perfData)
            #
            # threading.Thread(target=perf_data_process).start()
            threading.Thread().start()
        except Exception as e:
            traceback.print_exc()



    def setlabel(self,label):
        try:
            print("  添加label :" + label)
            self.stub.setLabel(perfdog_pb2.SetLabelReq(device=self.device, label=label))
        except Exception as e:
            traceback.print_exc()

    def setNote(self,note):
        try:
            print("   添加批注 :"+note)
            self.stub.addNote(perfdog_pb2.AddNoteReq(device=self.device, time=5000, note=note))
        except Exception as e:
            traceback.print_exc()

    def SaveJSON(self):
        try:
            print("12.上传和导出所有数据")
            saveResult = self.stub.saveData(perfdog_pb2.SaveDataReq(
                device=self.device,
                caseName=self.caseName,  # web上case和excel的名字
                uploadToServer=True,  # 上传到perfdog服务器
                exportToFile=True,  # 保存到本地
                outputDirectory=self.saveJsonPath,
                dataExportFormat=perfdog_pb2.EXPORT_TO_JSON
            ))
            print("保存结果:\n", saveResult)
            print("12.上传和导出所有数据")
            saveResult = self.stub.saveData(perfdog_pb2.SaveDataReq(
                device=self.device,
                caseName=self.caseName,  # web上case和excel的名字
                uploadToServer=True,  # 上传到perfdog服务器
                exportToFile=True,  # 保存到本地
                outputDirectory=self.saveJsonPath,
                dataExportFormat=perfdog_pb2.EXPORT_TO_PROTOBUF
            ))
            print("保存结果:\n", saveResult)
        except Exception as e:
            traceback.print_exc()

    def StopPerf(self):
        try:
            self.SaveJSON()
            print("13.停止测试")
            self.stub.stopTest(perfdog_pb2.StopTestReq(device=self.device))
            print("over")
        except Exception as e:
            traceback.print_exc()

    def selectApp(self,Apps):
        for app in Apps:
            print("find :",self.packageName,"  With  ",app.packageName)
            if app.packageName == self.packageName:
                return app;
        return None;

if __name__ == '__main__':
    package = "com.ztgame.fangzhidalu"
    path = "C:/Work/PerfDog/PerfDogService(v4.3.200927-Win)/PerfDogService.exe"
    token = "e8e5734ad2f74176b368c956173c9bfbb3a85bd1ec676cbef4b90435234786c1"
    uuid = ""
    pref = PerfdogService(package,path,token,"Test",uuid)
    print(pref)

    pref.StopPerf()
