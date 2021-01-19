import json


def openJSON(jsonPath):
    with open(jsonPath, 'r', encoding='utf-8') as fp:
        jsonData = json.load(fp)
    return jsonData

def GetPerfData(JsonData):
    LabelList = JsonData["LabelList"]
    DataList = JsonData["DataList"]
    PerfData = {}
    for v in LabelList:
        startTime = int(v["StartTime"])
        endTime = int(v["EndTime"])
        Text = v["Text"]
        fps = []
        jank = []
        bigjank = []
        timeStamp = []
        AppCPU = []  # AppUsage
        TotalCPU = []  # TotalUsage
        NormalAppCPU = []
        NormalTotalCPU = []
        CPUTemperature = []  # CTemp
        frameTime = []
        Memory = []
        SwapMemory = []
        VirtualMemory = []

        ScreenShot = []
        UpSpeed = []
        DownSpeed = []

        isDelete = []

        for data in DataList:
            TimeStamp = int(data["TimeStamp"])
            if TimeStamp >= startTime and TimeStamp < endTime:
                tempfps = '%.1f' % data["AndroidFps"]["fps"]
                tempjank = data["AndroidFps"]["Jank"]
                tempBigJank = data["BigJank"]["BigJank"]
                # frameTime 数据内容需要 在商议
                frametime = []
                if data.get("FrameDetails") != None and data["FrameDetails"].get("FrameTimes") != None:
                    t0 = data["FrameDetails"]["FrameTimes"]
                    for t in t0:
                        frametime.append('%.1f' % t)

                frameTime.append(frametime)
                timeStamp.append(TimeStamp)
                fps.append(tempfps)
                jank.append(tempjank)
                bigjank.append(tempBigJank)

                # CPU
                tempAppCPU = '%.1f' % float(data["CpuUsage"]["AppUsage"])
                tempTotalCPU = '%.1f' % float(data["CpuUsage"]["TotalUsage"])
                tempNormalAppCPU = '%.1f' % float(data["NormalizedCpuUsage"]["AppUsage"])
                tempNormalTotalCPU = '%.1f' % float(data["NormalizedCpuUsage"]["TotalUsage"])
                tempCPUTemp = '%.1f' % float(data["CpuTemperature"]["CpuTemperature"])
                AppCPU.append(tempAppCPU)
                TotalCPU.append(tempTotalCPU)
                NormalAppCPU.append(tempNormalAppCPU)
                NormalTotalCPU.append(tempNormalTotalCPU)
                CPUTemperature.append(tempCPUTemp)

                # Memory
                tempMemory = data["AndroidMemoryUsage"]["Memory"]
                tempSwapMemory = data["AndroidMemoryUsage"]["SwapMemory"]
                tempVirtualMemory = data["VirtualMemory"]["VirtualMemory"]
                Memory.append(tempMemory)
                SwapMemory.append(tempSwapMemory)
                VirtualMemory.append(tempVirtualMemory)

                # screenShot
                tempScreenShot = ""
                if data.get("ScreenShot") != None and data["ScreenShot"].get("FileName") != None:
                    tempScreenShot = data["ScreenShot"]["FileName"]
                ScreenShot.append(tempScreenShot)

                # Network
                tempUpSpeed = '%.5f' % data["NetworkUsage"]["UpSpeed"]
                tempDownSpeed = '%.5f' % data["NetworkUsage"]["DownSpeed"]
                UpSpeed.append(tempUpSpeed)
                DownSpeed.append(tempDownSpeed)

                tempIsDelete = data["IsDelete"]
                isDelete.append(tempIsDelete)

        PerfData[Text] = {"startTime": startTime,
                          "endTime": endTime,
                          "TimeStamp": timeStamp,
                          "fps": fps,
                          "jank": jank,
                          "bigjank": bigjank,
                          "frameTime": frameTime,
                          "AppCPU": AppCPU,
                          "TotalCPU": TotalCPU,
                          "NormalAppCPU": NormalAppCPU,
                          "NormalTotalCPU": NormalTotalCPU,
                          "CTemp": CPUTemperature,
                          "Memory": Memory,
                          "SwapMemory": SwapMemory,
                          "VirtualMemory": VirtualMemory,
                          "ScreenShot": ScreenShot,
                          "UpSpeed": UpSpeed,
                          "DownSpeed": DownSpeed,
                          "IsDelete": isDelete
                          }
    return PerfData

def GetAPPInfo(JsonData):

    DeviceModel = JsonData["DeviceModel"]
    OSType = JsonData["OSType"]
    OSVersion = JsonData["OSVersion"]
    AppDisplayName = JsonData["AppDisplayName"]
    AppVersion = JsonData["AppVersion"]
    AppPackageName = JsonData["AppPackageName"]
    CaseName = JsonData["CaseName"]
    RamSize = JsonData["RamSize"]
    CpuType = JsonData["CpuType"]
    GpuType = JsonData["GpuType"]
    DeviceDetailList = JsonData["DeviceDetailList"]["DeviceDetailList"]
    ClientVersion = JsonData["ClientVersion"]
    AbsDataStartTime = JsonData["AbsDataStartTime"]
    DataSource = JsonData["DataSource"]
    StatisticSetting = JsonData["StatisticSetting"]
    AppSubVersion = JsonData["AppSubVersion"]

    AppInfo = {
        "DeviceModel":DeviceModel,
        "OSType":OSType,
        "OSVersion":OSVersion,
        "AppDisplayName":AppDisplayName,
        "AppVersion":AppVersion,
        "AppPackageName":AppPackageName,
        "CaseName":CaseName,
        "RamSize":RamSize,
        "CpuType":CpuType,
        "GpuType":GpuType,
        "DeviceDetailList":DeviceDetailList,
        "ClientVersion":ClientVersion,
        "AbsDataStartTime":AbsDataStartTime,
        "DataSource":DataSource,
        "StatisticSetting":StatisticSetting,
        "AppSubVersion":AppSubVersion
    }
    return AppInfo

def MakeReportData(jsonPath,outFilePath):
    jsondata = openJSON(jsonPath)

    AppInfo = GetAPPInfo(jsondata)
    PerfData = GetPerfData(jsondata)
    ReportData = {
        "AppInfo":AppInfo,
        "PerfData":PerfData
    }
    jsonsss = json.dumps(ReportData)

    WriteInFile(outFilePath,jsonsss)

def WriteInFile(file,data):
    with open(file, 'w',encoding="utf-8") as f:
        f.write(data)
    f.close()



if __name__ == '__main__':
    MakeReportData("C:/Work/QA/dapbatu/daobatuautotestscript/AutoTestReport/prefDogLog/MyAirtestName.json","C:/Work/QA/dapbatu/daobatuautotestscript/AutoTestReport/prefDogLog/ReportResult.json")
    # t = openJSON("Temp.json")

    # print(t['AppInfo'])