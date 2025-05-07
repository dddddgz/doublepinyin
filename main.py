###########################################################
## 本 repo 中声母包含了 y、w，共 23 个                   ##
## 本 repo 中韵母不包含从不出现在声母之后的 io、ueng、er ##
## 本 repo 中零声母指可以单独使用的以 a、o、e 开头的韵母 ##
## 本 repo 中 zhi/chi/shi/ri/zi/ci/si 韵母按 i 处理      ##
###########################################################

import json, re, sys
from os import mkdir, listdir
from os.path import isdir
from time import strftime, sleep
from ttkbootstrap import *
from tkinter.filedialog import asksaveasfilename as ask_save
from tkinter import Checkbutton
from logging import getLogger, basicConfig
from itertools import product
from threading import Thread
from random import choice
from webbrowser import open_new_tab as OT

def exit() -> None:
    window.destroy()
    logf.close()
    print('程序意外终止，请进入 logs 文件夹查看日志。')
    sys.exit()

if not isdir('logs'):
    # 用于存放日志
    mkdir('logs')
logf = open(strftime('logs/%Y-%m-%d_%H_%M_%S.log'), 'w', encoding='utf-8')
# 每次都往这个文件里写东西
basicConfig(level=0, format='%(message)s', stream=logf)
logger = getLogger()

def read(file: str) -> str:
    """读取一个文本文件（如果不存在就在终端输出并终止程序）

    :param file: 文件路径
    :return: 文件内容
    """
    try:
        with open(file, encoding='utf-8') as f:
            logger.debug(f'已读取 {file}')
            return f.read()
    except FileNotFoundError:
        logger.error(f'找不到程序所需的文件 {file}')
        exit()

VERSION_S = '1.5.0'                                         # 当前程序版本（字符串形式）
BOOTSTYLES = [PRIMARY, SECONDARY, SUCCESS, INFO, WARNING, DANGER, LIGHT, DARK]  # 所有可用的 Bootstyle 样式
KEYS = set('qwertyuiopasdfghjkl;zxcvbnm')                   # 所有可被程序识别的按键
SHENGS1 = set('bpmfdtnlgkhjqxzcsryw')                       # 所有单个字母的声母
C_SHENG = {'background': '#fff', 'foreground': '#00a0e0'}   # 键位图上声母的颜色
C_YUN = {'background': '#fff', 'foreground': '#808080'}     # 键位图上韵母的颜色
PL = lambda: [plan for plan in plans if plan.name == planv.get()][0]
FT = lambda fontsize: ('更纱黑体 SC', fontsize, NORMAL)
OL = lambda bootstyle: (bootstyle, OUTLINE)
# 文件里的每行储存方式：<拼音> <汉字 1><汉字 2>...
# CHARS -> {<汉字>: <拼音>}
CHARS = {}
for line in read('chars.txt').splitlines():
    p, cs = line.split()
    for c in cs:
        CHARS[c] = p
MSGS = read('messages.txt').splitlines()
# 以便管理动画
animations = []
del p, cs, line

class Animation:
    """动画效果类"""
    def __init__(self, func, stop, on_stop, flag: str = ''):
        """
        :param func: 执行动画效果的函数
        :param stop: 停止条件（callable）
        :param on_stop: 动画停止时执行的条件
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同 flag 的动画只执行最后创建的一个
        """
        if flag:
            need_remove = []
            for animation in animations:
                if animation.flag == flag or animation.stop():
                    # 这个动画应被停止
                    animation.kill()
                    need_remove.append(animation)
            for each in need_remove:
                # 删除已停止的动画
                animations.remove(each)
        self.func = func
        self.stop = stop
        self.on_stop = on_stop
        self.flag = flag
        self.counter = 0
        animations.append(self)

    def kill(self) -> None:
        """提前终止动画"""
        self.stop = lambda: True
    
    def execute(self) -> None:
        """动画效果实际执行的方法"""
        if self.stop():
            self.kill()
            self.on_stop()
        else:
            self.func()
            self.counter += 1
            Thread(target=lambda: (sleep(1 / 60), self.execute()), daemon=True).start()

class MoveAnimation(Animation):
    """平移效果类"""
    def __init__(self, widget, target: tuple[int, int], step: tuple[int, int], flag: str = ''):
        """
        :param widget: 要应用效果的组件
        :param target: 组件移动后的位置
        :param step: 每 1 / 60 秒移动的距离
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同 flag 的动画只执行最后创建的一个
        """
        super().__init__(self.move, lambda: self.widget_pos == target, lambda: None, flag)
        self.widget = widget
        self.step = step
        self.target = target
    
    @property
    def widget_pos(self) -> tuple[int, int]:
        return int((info := self.widget.place_info())['x']), int(info['y'])
    
    def move(self) -> None:
        """平移"""
        (x, y), (tx, ty), (dx, dy) = self.widget_pos, self.target, self.step
        dx, dy = abs(dx) * pow(-1, x > tx), abs(dy) * pow(-1, y > ty)
        self.widget.place(x=x + dx, y=y + dy)

class TypingAnimation(Animation):
    """打字机效果类"""
    def __init__(self, widget, text: str, flag: str = ''):
        """
        :param widget: 要应用效果的组件
        :param text: 文字
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同 flag 的动画只执行最后创建的一个
        """
        super().__init__(lambda: widget.config(text=text[:self.counter // 2] + ' |'),
                         lambda: widget['text'][:-2] == text,
                         lambda: widget.config(text=text), flag)

def set_page(index, animation=True):
    """获取切换到指定页面的函数

    :param index: 页面的索引
    :param animation: 是否播放动画
    :return: 执行上述任务的函数
    """
    def inner() -> None:
        for i, frame in enumerate(frames):
            if animation:
                MoveAnimation(frame, ((i - index) * 1000, 50), (100, 0), f'frame{i}').execute()
            else:
                frame.place(x=(i - index) * 1000, y=50)
    return inner

class Plan:
    """双拼方案类"""
    def __init__(self, content: str):
        self.json = json.loads(content)
        self.name = self.json.pop('name')
        self.flags = self.json.pop('flags').split()

    def __str__(self):
        # 通过 __str__ 让 OptionMenu 的参数可以直接使用方案而不需要提取其 name 属性
        return self.name

    def find_keys(self, pin: str) -> list[str]:
        """根据拼音寻找按键

        :param pin: 拼音
        :return: 按键列表
        """
        if pin in SHENGS1:
            return [pin]
        if (value := self.json.get(pin, '')):
            return value.split(',')
        return []

    def find_pins(self, key) -> list[str]:
        """根据按键寻找拼音

        :param key: 按键
        :return: 拼音列表
        """
        return [pin for pin, keys in self.json.items() if key in keys.split(',')]

    def get_codes(self, pin: str) -> list[str]:
        """获取一个拼音 pin 的双拼输入按键

        :return: 双拼输入按键
        """
        if pin in {'hm', 'hng', 'ng'}:
            return [pin[0] + pin[-1]]
        fks, (p1, p2) = self.find_keys, split_pinyin(pin)
        if p1:
            # 不是零声母
            k1s, k2s = fks(p1), fks(p2)
            if p2 == 'ü' and p1 in 'jqxy' and 'jqxy_not_u' not in self.flags:
                # 这时，ü 也可以使用 u 对应的键
                k2s.extend(fks('u'))
            return list(map(''.join, product(k1s, k2s)))
        # 零声母
        return fks(f'_{p2}')

    def draw_keys(self) -> None:
        """给键盘绘制对应的拼音"""
        # 删除以前绘制的
        while keylabels and (keylabels.pop().destroy(),):
            pass
        # 记录每个 Label 上拼音的位置
        positions = {}
        for i in range(10):
            positions['qwertyuiop'[i]] = [i * 80 + 35, 60]
            positions['asdfghjkl;'[i]] = [i * 80 + 70, 140]
            positions['zxcvbnm   '[i]] = [i * 80 + 105, 220]
        del positions[' ']
        # 记录每个按键对应的韵母
        keyyuns = {k: [] for k in KEYS}
        zerol['text'] = '零声母情况：\n'
        for pin, keys_s in self.json.items():
            keys = keys_s.split(',')
            if pin[0] == '_':
                # 零声母
                zerol['text'] += f'{pin[1:]} -> {keys_s}\n'
            elif pin in {'zh', 'ch', 'sh'}:
                # 声母
                for key in keys:
                    # 和其他声母一样，直接往按键上标就行了
                    x, y = positions[key]
                    label = Label(keymapf, text=pin, font=FT(12), **C_SHENG)
                    label.place(x=x, y=y)
                    keylabels.append(label)
                    # 轮到韵母使用这个键了
                    positions[key][1] += 22
            else:
                # 要先统计出一个按键上所有的韵母
                [keyyuns[key].append(pin) for key in keys]
        for key, yuns in keyyuns.items():
            x, y = positions[key]
            if len(yuns) < 3:
                # 可以一行一行显示
                text = '\n'.join(yuns)
            else:
                # 要加逗号显示
                text = f'{','.join(yuns[:2])}\n{','.join(yuns[2:])}'
            label = Label(keymapf, text=text, font=FT(12), **C_YUN)
            label.place(x=x, y=y)
            keylabels.append(label)
    
    def apply(self) -> None:
        """设为当前双拼方案"""
        self.draw_keys()
        keytipcb.toggle()
        keytipcb.toggle()

def is_valid_pinyin(pin: str) -> bool:
    """检查 pin 是不是一个合法的拼音（不检查是否能拼得出来；“边缘拼音”只认 hm/hng/ng）
    
    :return: True/False
    """
    if not (pin := re.sub(r'([jqxy])u', r'\1ü', pin.replace('v', 'ü'))):
        # 拼音为空
        return False
    if pin in 'a o e ai ei ao ou er an en ang eng hm hng ng'.split():
        return True
    if pin[0] in 'iuü':
        # 拼音以 i/u/ü 开头
        return False
    if pin[0] in SHENGS1:
        # 不是零声母
        if len(pin) < 2:
            # 没有韵母
            return False
        # 提取韵母，接下来只要判断韵母就行了
        if pin[1] == 'h':
            # 翘舌音，不要前两个字母
            yun = pin[2:]
        else:
            # 单字母的声母，不要第一个字母
            yun = pin[1:]
        # 只要判断韵母是否正常就行了
        return yun in 'a o e i u ü ai ei ui ao ou iu ie üe an en in un ün \
ang eng ing ong ia ua uo uai iao ian uan üan iang uang iong'.split()
    # 很难想象哪个拼音能通过这么多关卡来到这里
    return False

def split_pinyin(pin: str) -> tuple[str, str]:
    """将 pin 拆分为声母部分和韵母部分

    :return: (声母, 韵母)
    """
    pin = re.sub(r'([jqxy])u', r'\1ü', pin.replace('v', 'ü'))
    # 零声母
    if pin[0] in 'aoe':
        return '', pin
    # 第二个字母是 h 代表是翘舌音，以翘舌音为界即可
    if pin[1] == 'h':
        return pin[:2], pin[2:]
    return pin[0], pin[1:]

def find_keys(*_) -> None:
    """根据音节寻找按键"""
    # 允许用户使用 v 代替 ü
    if (results := PL().find_keys(find1v.get().replace('v', 'ü'))):
        find1l['text'] = ','.join(results)
    else:
        find1l['text'] = '-'

def find_pins(*_) -> None:
    """根据按键寻找音节"""
    if (key := find2e.get().lower()) in KEYS and (result := PL().find_pins(key)):
        find2l['text'] = ','.join(result)
    else:
        find2l['text'] = '-'

def get_codes(*_) -> None:
    """根据拼音寻找可用的双拼输入按键"""
    if (value := find3e.get()) and is_valid_pinyin(value):
        find3l['text'] = ','.join(PL().get_codes(value))
    else:
        find3l['text'] = '-'

def random_char() -> None:
    """显示一个随机汉字"""
    # 用 list 获取键（即汉字）
    charl['text'] = choice(list(CHARS))
    # 注上拼音
    pinyinl['text'] = CHARS[charl['text']]
    keytipv.get() and update_key_tip()

def update_key_tip(*_) -> None:
    """给显示的随机汉字添加按键提示"""
    if keytipv.get():
        # 目标是想办法加上提示
        if ' ' not in pinyinl['text']:
            # 还没有提示
            pinyinl['text'] += f' [{','.join(PL().get_codes(pinyinl['text']))}]'
    else:
        # 目标是去掉提示
        pinyinl['text'] = pinyinl['text'].split()[0]

def check_input(*_) -> None:
    """检查显示的拼音所有拼法里是否有用户输入的内容"""
    global correct, total
    if len(value := inputv.get()) < 2:
        # 用户还没输入完
        return
    # 懒得一直加 if 了，索性就利用 tkinter 的特性，一直禁着
    recordst['state'] = (DISABLED, NORMAL)[count := recordv.get()]
    # recordst 里第 2 行使用的序号使用的是 1.（第一行是表头）
    # index 仍然储存实际位置 2
    index = recordst.get(1.0, END).count('\n')
    recordst.insert(END, f'{index - 1}.\t{(pinyin := pinyinl['text'].split()[0])}\t{value}\t')
    if value in PL().get_codes(pinyin):
        recordst.insert(END, f'✓\n')
        recordst.tag_add('correct', float(index), float(index + 1))
        correct += count
        random_char()
    else:
        recordst.insert(END, f'×\n')
        recordst.tag_add('wrong', float(index), float(index + 1))
    total += count
    if total:
        statics['text'] = f'正确率 {correct / total * 100:.1f}% ({correct} / {total})'
    else:
        statics['text'] = f'正确率 0.0% (0 / 0)'
    # 添加 tag 是为了给对错两种情况分别加上绿色和红色
    # 无论用户输入对不对，都应该清空
    inputv.set('')
    # 得防着点用户
    recordst['state'] = DISABLED
    recordst.see(END)

def load_plans() -> None:
    """加载所有双拼方案"""
    # 并不需要 global，因为实际上并没有对 plans 进行“赋值”操作
    if not isdir('plans'):
        logger.error("找不到文件夹 'plans'")
        exit()
    if not (filenames := listdir('plans')):
        logger.error("文件夹 'plans' 下没有文件")
        exit()
    plans[:] = [Plan(read(f'plans/{filename}')) for filename in filenames]

plans = []
load_plans()

def new_plan() -> None:
    """创建新双拼方案功能的 command"""
    def add(title: str, height: int, x: int, y: int, bootstyle: str, texts: str) -> None:
        """创建一个有若干个 Label、Entry 的 Labelframe

        :param title: Labelframe 标题
        :param height: Labelframe 高度
        :param x: Labelframe 左上角 x 坐标
        :param y: Labelframe 左上角 y 坐标
        :param bootstyle: str，内容为 bootstyle
        :param texts: str
        """
        labelframe = Labelframe(top, text=title, width=160, height=height, bootstyle=bootstyle)
        for i, text in enumerate(texts.split()):
            label = Label(labelframe, text=text, font=FT(12))
            label.place(x=10, y=10 + i * 30)
            entry = Entry(labelframe, width=12, textvariable=(var := StringVar()), bootstyle=bootstyle)
            entry.place(x=50, y=10 + i * 30)
            widgets.append((label, var))
        labelframe.place(x=x, y=y)
    def create() -> None:
        """创建按钮的 command"""
        if not (name := namee.get()):
            statusl['text'] = '未填写方案名称。'
            return
        data = {'name': name}
        for label, var in widgets:
            if not all(map(lambda key: key in KEYS, var.get().split(','))):
                # 满足“所有 key 都是 a-z 或 ; 的按键”
                data[label['text']] = var.get()
            else:
                # 没有填完
                return statusl.config(text=f'{label['text']} 填写错误。')
        data['flags'] = 'jqxy_not_u' * notuv.get()
        # 既然程序能运行到这里，那说明什么异常也没有发生
        statusl['text'] = ''
        if path := ask_save(title='保存方案', filetypes=(('JSON', '*.json'),), initialdir='plans', defaultextension='.json', parent=top):
            # 因为含有“ü”，所以需要特别指出 utf-8，不然“ü”会被读取为“眉”
            with open(path, 'w', encoding='utf-8') as f:
                # ensure_ascii 需要关闭，以免 ü 被替换为 ASCII 码
                json.dump(data, f, indent=4, ensure_ascii=False)
    def clear() -> None:
        """清空此前输入的所有内容"""
        for _, var in widgets:
            var.set('')
    top = Toplevel('新方案', size=(900, 480), resizable=(False, False))
    namel = Label(top, text='名称：', font=FT(12))
    namel.place(x=10, y=10)
    namee = Entry(top, bootstyle=SECONDARY, width=12)
    namee.place(x=60, y=10)
    # 把用到的 Label 和 StringVar 收集起来，方便读取并保存至 JSON
    widgets = []
    add('zh ch sh', 130, 10, 50, SUCCESS, 'zh ch sh')
    add('韵母', 250, 10, 190, PRIMARY, 'a o e i u ü ai')
    add('韵母', 430, 180, 10, PRIMARY, 'iao ian uan üan iang uang iong ei ui ao ou iu ie')
    add('韵母', 460, 350, 10, PRIMARY, 'üe an en in un ün ang eng ing ong ia ua uo uai')
    add('零声母', 400, 520, 10, DANGER, '_a _o _e _ai _ei _ao _ou _er _an _en _ang _eng')
    notuv = BooleanVar(value=False)
    notucb = Checkbutton(top, text='禁止 jqxy 后的 ü 使用 u', font=FT(12), variable=notuv)
    notucb.place(x=520, y=430)
    createb = Button(top, text='保存', command=create, bootstyle=OL(SUCCESS))
    createb.place(x=690, y=10)
    clearb = Button(top, text='清空', command=clear, bootstyle=OL(SECONDARY))
    clearb.place(x=690, y=50)
    # 专门记录发生的异常情况（目前只有一种）
    statusl = Label(top, font=FT(12), bootstyle=DANGER)
    statusl.place(x=750, y=10)
    top.mainloop()

def update_alpha(*_) -> None:
    """更新窗口透明度设置情况"""
    window.attributes('-alpha', (alpha := alphav.get()) / 100)
    alphal['text'] = f'透明度：{alpha}%'
    alpha1b['state'] = (NORMAL, DISABLED)[alpha >= 100]
    alpha2b['state'] = (NORMAL, DISABLED)[alpha <= 20]

def change_msg() -> None:
    """更换一个“回声洞”内容"""
    TypingAnimation(msgl, choice(MSGS), 'hsd').execute()

window = Window(f'DoublePinyin Trainer / 双拼练习器 V{VERSION_S}', size=(1000, 760), resizable=(False, False))
switchf = Frame(window, width=1000, height=50, bootstyle=SECONDARY)
keymapb = Button(switchf, text='键位图', bootstyle=INFO, command=set_page(0))
keymapb.place(x=20, y=10)
practiceb = Button(switchf, text='练习', bootstyle=SUCCESS, command=set_page(1))
practiceb.place(x=90, y=10)
settingsb = Button(switchf, text='设置', bootstyle=DARK, command=set_page(2))
settingsb.place(x=150, y=10)
switchf.place(x=0, y=0)

keymapf = Frame(window, width=1000, height=700)
# 要先绘制键盘，再给按键写上对应的拼音
# 很不理解为什么网上很多人给出的解法是使用 ImageTk.PhotoImage(Image.open(...))
keyboardl = Label(keymapf, image=(keyboardi := PhotoImage(file='keyboard.png')))
keyboardl.place(x=0, y=50)
# 这些代码必须写在关于绘制的功能前

# 键盘上显示的韵母都使用 Label
keylabels = []
# 专门显示零声母的解决方案
zerol = Label(keymapf, font=FT(16))
zerol.place(x=10, y=330)
# 由于下拉选择也需要用到表示双拼方案的 StringVar，下拉选择只能写在最后
Label(keymapf, text='请选择双拼方案：', font=FT(16)).place(x=10, y=10)
# 使用 StringVar 记录菜单的选项
planv = StringVar(value='小鹤双拼')
# 'write' 表示当 Var 被修改时调用的函数，lambda 内容为找到对应的双拼方案并绘制键位图
planv.trace_add('write', lambda *_: PL().apply())
PL().draw_keys()
# 下拉菜单（让下拉菜单永远“认准”这个 StringVar，它的数据会和 StringVar 绑定）
plano = OptionMenu(keymapf, planv, None, *plans, bootstyle=OL(WARNING))
plano.place(x=190, y=10)

find1lf = Labelframe(keymapf, text='音节 -> 按键', width=500, height=70, bootstyle=DANGER)
find1v = StringVar()
find1v.trace_add('write', find_keys)
find1e = Entry(find1lf, textvariable=find1v, bootstyle=DANGER)
find1e.place(x=10, y=10)
find1l = Label(find1lf, text='-', font=FT(12), bootstyle=DANGER)
find1l.place(x=180, y=10)
find1lf.place(x=140, y=310)

find2lf = Labelframe(keymapf, text='按键 -> 音节', width=500, height=70, bootstyle=PRIMARY)
find2v = StringVar()
find2v.trace_add('write', find_pins)
find2e = Entry(find2lf, textvariable=find2v, bootstyle=PRIMARY)
find2e.place(x=10, y=10)
find2l = Label(find2lf, text='-', font=FT(12), bootstyle=PRIMARY)
find2l.place(x=180, y=10)
find2lf.place(x=140, y=400)
find3lf = Labelframe(keymapf, text='拼音 -> 按键', width=500, height=70, bootstyle=SUCCESS)
find3v = StringVar()
find3v.trace_add('write', get_codes)
find3e = Entry(find3lf, textvariable=find3v, bootstyle=SUCCESS)
find3e.place(x=10, y=10)
find3l = Label(find3lf, text='-', font=FT(12), bootstyle=SUCCESS)
find3l.place(x=180, y=10)
find3lf.place(x=140, y=490)

# 练习界面
practicef = Frame(window, width=1000, height=700)
# 用于显示拼音的 Label
pinyinl = Label(practicef, font=FT(20))
pinyinl.place(x=250, y=70)
# 用于显示汉字的 Label
charl = Label(practicef, font=('楷体', 120, NORMAL))
charl.place(x=200, y=120)
# 提供输入框，并且给它绑定 StringVar，当字正确时自动下一个字
inputv = StringVar()
inputv.trace_add('write', check_input)
inpute = Entry(practicef, textvariable=inputv, bootstyle=SUCCESS)
inpute.place(x=200, y=310)
keytipv = BooleanVar()
keytipv.trace_add('write', update_key_tip)
keytipcb = Checkbutton(practicef, text='按键提示', variable=keytipv)
keytipcb.place(x=430, y=20)
recordcb = Checkbutton(practicef, text='启用练习记录', variable=(recordv := BooleanVar()))
recordcb.place(x=510, y=20)
recordlf = Labelframe(practicef, text='练习记录', width=400, height=330, bootstyle=SUCCESS)
# 设置 state=DISABLED 以防止用户自行更改
recordst = ScrolledText(recordlf, width=50, height=15, state=DISABLED)
recordst.tag_config('correct', foreground='#008000')
recordst.tag_config('wrong', foreground='#ff0000')
recordst.insert(END, '序号\t拼音\t输入内容\t是否正确\n')
recordst.place(x=10, y=10)
total = correct = 0
statics = Label(recordlf, text='正确率 0.0% (0 / 0)', bootstyle=SUCCESS)
statics.place(x=10, y=290)
recordlf.place(x=430, y=50)
random_char()

settingsf = Frame(window, width=1000, height=700)

themelf = Labelframe(settingsf, text='主题', width=980, height=150)
# 用 StringVar 记录主题选择界面；当主题被“写入”就运行 set_theme
themev = StringVar(value='litera')
themev.trace_add('write', lambda *_: window.style.theme_use(themev.get()))
themeo = OptionMenu(themelf, themev, None, *window.style.theme_names(), bootstyle=OL(INFO))
themeo.place(x=10, y=10)
themel = Label(themelf, text='主题效果')
themel.place(x=10, y=50)
x = 10
for bootstyle in BOOTSTYLES:
    button = Button(themelf, text=bootstyle, bootstyle=OL(bootstyle), width=10)
    button.place(x=x, y=80)
    x += 100
themelf.place(x=10, y=10)

planslf = Labelframe(settingsf, text='双拼方案', width=485, height=70)
reloadb = Button(planslf, text='重新加载', command=lambda: (load_plans(), plano.set_menu(None, *plans)), bootstyle=OL(PRIMARY))
reloadb.place(x=10, y=10)
newplanb = Button(planslf, text='新方案', command=new_plan, bootstyle=OL(WARNING))
newplanb.place(x=92, y=10)
planslf.place(x=10, y=170)

attrlf = Labelframe(settingsf, text='窗口属性', width=485, height=70)
alphav = IntVar(value=100)
alphav.trace_add('write', update_alpha)
alphal = Label(attrlf, text='透明度：100%', font=FT(11))
alphal.place(x=10, y=10)
alpha1b = Button(attrlf, text='↑', state=DISABLED, command=lambda: alphav.set(alphav.get() + 10), bootstyle=OL(INFO))
alpha1b.place(x=130, y=10)
alpha2b = Button(attrlf, text='↓', command=lambda: alphav.set(alphav.get() - 10), bootstyle=OL(INFO))
alpha2b.place(x=170, y=10)
attrlf.place(x=505, y=170)

msglf = Labelframe(settingsf, text='回声洞', width=980, height=70)
msgb = Button(msglf, text='↻', command=change_msg, bootstyle=OL(SUCCESS))
msgb.place(x=10, y=10)
msgl = Label(msglf, text='←Click that', font=FT(11))
msgl.place(x=50, y=15)
msglf.place(x=10, y=250)

aboutlf = Labelframe(settingsf, text='关于程序', width=980, height=110)
versionl = Label(aboutlf, text=f'DoublePinyin Trainer V{VERSION_S}', font=FT(12))
versionl.place(x=10, y=10)
updateb = Button(aboutlf, text='检查更新（未完工）', bootstyle=OL(INFO), state=DISABLED)
updateb.place(x=250, y=10)
fishcb = Button(aboutlf, text='↪ FishC', command=lambda: OT('https://fishc.com.cn/thread-249454-1-1.html'), bootstyle=OL(DANGER))
fishcb.place(x=10, y=50)
githubb = Button(aboutlf, text='↪ GitHub', command=lambda: OT('https://github.com/dddddgz/doublepinyin'), bootstyle=OL(DARK))
githubb.place(x=89, y=50)
aboutlf.place(x=10, y=330)

frames = [keymapf, practicef, settingsf]
set_page(0, False)()
window.mainloop()
logf.close()
