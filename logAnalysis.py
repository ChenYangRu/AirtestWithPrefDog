import io
import json
import os
import shutil
import sys
import traceback

import six
from PIL import Image
from airtest.aircv import imread, get_resolution, compress_image
from airtest.cli.info import get_script_info
from airtest.utils.compat import script_dir_name
from airtest.utils.logger import get_logger
from six import PY3
from copy import deepcopy

PY3 = sys.version_info[0] == 3

LOGGING = get_logger(__name__)
LOGDIR = "log"

class myLogAnalysis(object):
    def __init__(self,script_root,log_root,logfile,ModelName,NeedRestPath):
        self.script_root = script_root
        self.log = []
        self.log_root = log_root
        self.logfile = os.path.join(log_root, logfile)
        self.run_start = None
        self.export_dir = None
        self.FieldNum = 0
        self.test_result = True
        self.modelName = ModelName
        self.needResetPath = NeedRestPath

    def _load(self):
        loadfile = self.logfile.encode(sys.getfilesystemencoding()) if not PY3 else self.logfile

        with io.open(loadfile,encoding="utf-8") as f:
            for line in f.readlines():
                self.log.append(json.loads(line))

    def _analysis(self):
        steps = []
        children_steps =[]
        for log in self.log:
            depth = log['depth']

            if not self.run_start:
                self.run_start = log.get('data',{}).get('start_time','') or log["time"]
            self.run_end = log["time"]

            if depth == 0:
                steps.append(log)
            elif depth == 1:
                step = deepcopy(log)
                step["__children__"] = children_steps
                steps.append(step)
            else:
                children_steps.insert(0,log)

        translated_steps = [self._translate_step(s) for s in steps]
        return translated_steps

    def _translate_step(self,step):
        name = step["data"]["name"]
        title = self._translate_title(name,step)
        code = self._translate_code(step)
        desc = self._translate_desc(step, code)
        screen = self._translate_screen(step, code)
        info = self._translate_info(step)
        assertion = self._translate_assertion(step)

        # set test failed if any traceback exists
        if info[0]:
            self.test_result = False
            self.FieldNum = self.FieldNum +1

        if self.needResetPath:
            self.resetScreen(screen,self.modelName)
        translated = {
            "title": title,
            "time": step["time"],
            "code": code,
            "screen": screen,
            "desc": desc,
            "traceback": info[0],
            "log": info[1],
            "assert": assertion,
        }
        return translated

    def _translate_title(self,name,step):
        title = {
            "touch":u"Touch",
            "swipe":u"Swipe",
            "wait":u"Wait",
            "exists": u"Exists",
            "text": u"Text",
            "keyevent": u"Keyevent",
            "sleep": u"Sleep",
            "assert_exists": u"Assert exists",
            "assert_not_exists": u"Assert not exists",
            "snapshot": u"Snapshot",
            "assert_equal": u"Assert equal",
            "assert_not_equal": u"Assert not equal",
        }

        return title.get(name,name)

    def _translate_code(self,step):
        if step["tag"] != "function":
            return None
        step_data = step["data"]
        args = []
        code = {
            "name":step_data["name"],
            "args":args,
        }
        for key,value in step_data["call_args"].items():
            args.append({
                "key":key,
                "value":value,
            })
        for k,arg in enumerate(args):
            value = arg["value"]
            if isinstance(value,dict) and value.get("__class__") == "Template":
                if self.export_dir:# all relative path
                    image_path = value['filename']
                    if not os.path.isfile(os.path.join(self.script_root,image_path)) and value['_filepath']:
                        # copy image used by using statement
                        shutil.copyfile(value['_filepath'], os.path.join(self.script_root, value['filename']))
                else:
                    image_path = os.path.abspath(value['_filepath'] or value['filename'])
                arg["image"] = image_path
                if not value['_filepath'] and not os.path.exists(value['filename']):
                    crop_img = imread(os.path.join(self.script_root,value['filename']))
                else:
                    crop_img = imread(value['_filepath'] or value['filename'])
                arg["resolution"] = get_resolution(crop_img)
        return code

    def resetScreen(self,screen,ModelName):
        screen['src'] = self.splitPath(screen['src'],ModelName)
        screen['_filepath'] = self.splitPath(screen['_filepath'], ModelName)
        screen['thumbnail'] = self.splitPath(screen['thumbnail'], ModelName)

    def splitPath(self,str,modelName):
        s = str.split(modelName)
        return str.replace(s[0], "")

    def _translate_desc(self,step,code):
        #""" 函数描述"""
        if step['tag'] != "function":
            return None
        name = step['data']['name']
        res = step['data'].get('ret')
        args = {i['key']: i["value"] for i in code["args"]}

        desc ={
            "snapshot": lambda : u"Screenshot descriptions: %s" % args.get("msg"),
            "touch": lambda: u"Touch %s" % ("target image" if isinstance(args['v'],dict) else "coordinstes %s" % args['v']),
            "swipe": u"Swipe on screen",
            "wait": u"Wait for target image to appear",
            "exists": lambda: u"Image %s exists" % ("" if res else "not"),
            "text": lambda : u"Click [%s] button" % args.get('text'),
            "keyevent": lambda: u"Click [%s] button" % args.get('keyname'),
            "sleep": lambda: u"Wait for %s seconds" % args.get('secs'),
            "assert_exists": u"Assert target image exists",
            "assert_not_exists": u"Assert target image does not exists",
        }

        # todo: 最好用js里的多语言实现
        desc_zh = {
            "snapshot": lambda: u"截图描述: %s" % args.get("msg"),
            "touch": lambda: u"点击 %s" % (u"目标图片" if isinstance(args['v'], dict) else u"屏幕坐标 %s" % args['v']),
            "swipe": u"滑动操作",
            "wait": u"等待目标图片出现",
            "exists": lambda: u"图片%s存在" % ("" if res else u"不"),
            "text": lambda: u"输入文字:%s" % args.get('text'),
            "keyevent": lambda: u"点击[%s]按键" % args.get('keyname'),
            "sleep": lambda: u"等待%s秒" % args.get('secs'),
            "assert_exists": u"断言目标图片存在",
            "assert_not_exists": u"断言目标图片不存在",
        }

        #if self.lang == "zh":
        desc = desc_zh

        ret = desc.get(name)
        if callable(ret):
            ret = ret()
        return ret


    def _translate_info(self,step):
        trace_msg,log_msg = "",""
        if "traceback" in step["data"]:
            # 若包含有traceback内容，将会认定步骤失败
            trace_msg = step["data"]["traceback"]
        if step["tag"] == "info":
            if "log" in step["data"]:
                # 普通文本log内容，仅显示
                log_msg = step["data"]["log"]
        return trace_msg,log_msg


    def _translate_assertion(self,step):
        if "assert" in step["data"]["name"] and "msg" in step["data"]["call_args"]:
            return  step["data"]["call_args"]["msg"]

    def _translate_screen(self,step,code):
        if step['tag'] not in ["function","info"] or not step.get("__children__"):
            return None
        screen = {
            "src":None,
            "rect":[],
            "pos":[],
            "vector":[],
            "confidence":None,
        }

        for item in step["__children__"]:
            if item["data"]["name"] == "try_log_screen":
                snapshot = item["data"].get("ret",None)
                if isinstance(snapshot,six.text_type):
                    src = snapshot
                elif isinstance(snapshot,dict):
                    src = snapshot['screen']
                    screen['resolution'] = snapshot['resolution']
                else:
                    continue

                if self.export_dir:
                    screen['_filepath'] = os.path.join(LOGDIR,src)
                else:
                    screen['_filepath'] = os.path.abspath(os.path.join(self.log_root,src))
                screen['src'] = screen['_filepath']
                self.get_thumbnail(os.path.join(self.log_root,src))
                screen['thumbnail'] = self.get_small_name(screen['src'])
                break

        display_pos = None

        for item in step["__children__"]:
            if item["data"]["name"] == "_cv_match" and isinstance(item["data"].get("ret"),dict):
                cv_result = item["data"]["ret"]
                pos = cv_result["result"]
                if self.is_pos(pos):
                    display_pos = [round(pos[0]),round(pos[1])]
                rect = self.div_rect(cv_result['rectangle'])
                screen['rect'].append(rect)
                screen['confidence'] = cv_result['confidence']
                break

        if step["data"]["name"] in ["touch","assert_exists","wait","exists"]:
            #将图像匹配得到的pos修正为最终pos
            if self.is_pos(step["data"].get("ret")):
                display_pos = step["data"]["ret"]
            elif self.is_pos(step["data"]["call_args"].get("v")):
                display_pos = step["data"]["call_args"]["v"]

        elif step["data"]["name"] == "swipe":
            if "ret" in step["data"]:
                screen["pos"].append(step["data"]["ret"][0])
                target_pos = step["data"]["ret"][1]
                origin_pos = step["data"]["ret"][0]
                screen["vector"].append([target_pos[0] - origin_pos[0],target_pos[1] - origin_pos[1]])

        if display_pos:
            screen["pos"].append(display_pos)
        return screen

    @classmethod
    def get_thumbnail(cls, path):
        """compress screenshot"""
        new_path = cls.get_small_name(path)
        if not os.path.isfile(new_path):
            try:
                img = Image.open(path)
                compress_image(img, new_path, 10)
            except Exception:
                LOGGING.error(traceback.format_exc())
            return new_path
        else:
            return None

    @staticmethod
    def div_rect(r):
        """count rect for js use"""
        xs = [p[0] for p in r]
        ys = [p[1] for p in r]
        left = min(xs)
        top = min(ys)
        w = max(xs) - left
        h = max(ys) - top
        return {'left': left, 'top': top, 'width': w, 'height': h}

    @classmethod
    def get_small_name(cls, filename):
        name, ext = os.path.splitext(filename)
        return "%s_small%s" % (name, ext)

    def is_pos(self, v):
        return isinstance(v, (list, tuple))

    def makeData(self):
        self._load()
        steps = self._analysis()

        path, self.script_name = script_dir_name(self.script_root)
        script_path = os.path.join(self.script_root, self.script_name)
        info = json.loads(get_script_info(script_path))

        #mpr repord
        record_list = [f for f in os.listdir(self.log_root) if f.endswith(".mp4")]
        records = [os.path.join(LOGDIR, f) if self.export_dir
                   else os.path.abspath(os.path.join(self.log_root, f)) for f in record_list]

        scriptname = self.script_name
        if self.needResetPath:
            scriptname = self.splitPath(self.script_root,self.modelName)
            info['path'] = self.splitPath(info['path'],self.modelName)

        data = {}
        data['steps'] = steps
        data['name'] = scriptname
        data['test_result'] = self.test_result
        data['field_num'] = self.FieldNum
        data['run_end'] = self.run_end
        data['run_start'] = self.run_start
        #data['static_root'] = self.static_root
        data['records'] = records
        data['info'] = info
#        data['log'] = self.get_relative_log(output_file)
#        data['console'] = self.get_console(output_file)
        # 如果带有<>符号，容易被highlight.js认为是特殊语法，有可能导致页面显示异常，尝试替换成不常用的{}
        info = json.dumps(data).replace("<", "{").replace(">", "}")
        # data['data'] = info
        return data

def MakeAllReport(ModelList, script_root, log_Root, savePath):
    reportPath = savePath + "/Report/"
    modellist = json.loads(ModelList)
    for model in modellist:
        modelName = model['modelName']
        script = os.path.join(script_root, modelName + '.air')
        logroot = os.path.join(log_Root, modelName)
        os.system("airtest report %s --log_root %s --outfile log.html --lang zh --export %s" % (script,
                                                                                                    logroot, reportPath))


def MakeAllLogData(ModelList,script_root,log_Root,savePath):

    results = [];
    mark = {}
    mark["AllPass"] = True
    mark["LastModel"] = ""
    for model in ModelList:
        modelName = model['modelName']
        mark["LastModel"] = modelName
        script = os.path.join(script_root,modelName + '.air')
        log = os.path.join(log_Root,modelName)
        if os.path.exists(log+"/log.txt"):
            sda = myLogAnalysis(script, log, "log.txt",modelName)
            ss = sda.makeData()
            data = {};
            data['name'] = modelName
            data['result'] = ss['test_result']
            data['infos'] = ss
            data['mustPass'] = model['MustPass']

            if data['mustPass'] and data['result'] == False:
                mark["AllPass"] = False
            results.append(data)
        else:
            print("not found Log File %s:" % log+"/log.txt")
            break

    datas = {}
    datas["mark"] = mark
    datas["results"] = results
        # data[model] = ss
    data = json.dumps(datas)
    saveFile = os.path.join(savePath,"data.json")
    WriteInFile(saveFile,data)

def WriteInFile(file,data):
    with open(file, 'w') as f:
        f.write(data)
    f.close()

if __name__ == "__main__":

    script_root = "C:/Work/airtest/mytest.air"
    logRoot = "C:/Work/airtestReport/Log/mytest/"
    logFile = "log.txt"

    sda = myLogAnalysis(script_root,logRoot,logFile)

    #sda._load()

    #lsl = sda._analysis()
    ss = sda.makeData();

    print("ss")
    print(ss)

