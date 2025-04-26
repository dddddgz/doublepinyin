import os, json, random, time, re
from ttkbootstrap import *
from tkinter import messagebox as msb, filedialog as fd, Checkbutton
from itertools import product
from threading import Thread
from webbrowser import open_new_tab as OT

#########################################################
## 本 repo 中声母包含了 y、w，共 23 个                 ##
## 本 repo 中韵母不包含从不出现在声母之后的 io、ueng   ##
## 本 repo 中零声母指可以单独使用的 a、o、e 开头的韵母 ##
## 本 repo 中 zh ch sh“零韵母”情况韵母按 i 处理        ##
#########################################################

# VERSION = (1, 3, 3)                                       # 当前程序版本
VERSION_S = '1.3.3'                                         # 当前程序版本的字符串形式
BOOTSTYLES = [PRIMARY, SECONDARY, SUCCESS, INFO, WARNING, DANGER, LIGHT, DARK] # 所有可用的 Bootstyle 样式
KEYS = list('qwertyuiopasdfghjkl;zxcvbnm')                  # 所有可被程序识别的按键
SHENGS1 = list('bpmfdtnlgkhjqxzcsryw')                      # 所有单个字母的声母
C_SHENG = {'background': '#fff', 'foreground': '#00a0e0'}   # 键位图上声母的颜色
C_YUN = {'background': '#fff', 'foreground': '#808080'}     # 键位图上韵母的颜色
PASS = lambda: None                                         # 几个常用的 callable
R_TRUE = lambda: True
GP = lambda: [plan for plan in plans if plan.name == planv.get()][0]
FT = lambda fontsize: ('更纱黑体 SC', fontsize, NORMAL)
OL = lambda bootstyle: (bootstyle, OUTLINE)
PYS = lambda text: [CHARS[char] for char in text]
PY = lambda text: ''.join(map(lambda x: x[0], PYS(text)))
with open('chars.txt', encoding='utf-8') as f:
    CHARS = {}
    for line in f.readlines():
        p, cs = line.split()[:2]
        for c in cs:
            if c in CHARS:
                CHARS[c].append(p)
            else:
                CHARS[c] = [p]
with open('chars2.txt', encoding='utf-8') as f:
    PCHARS = {}
    for line in f.readlines():
        p, cs = line.split()[:2]
        [PCHARS.__setitem__(c, p) for c in cs]
del p, cs, c, line

def schedule(interval: int | float, func) -> None:
    """在 interval 秒后执行 func"""
    Thread(target=lambda: (time.sleep(interval), func()), daemon=True).start()

def make_pairs(*lists, merge: bool = False) -> list:
    """
    将所有参数中的所有元素进行搭配
    :param merge: 是否合并元素（例如 make_pairs(['1', '2'], ['3', '4'], merge=True) -> ['13', '14', '23', '24']）
    :return: 搭配结果
    """
    result = list(product(*lists))
    if merge:
        return list(map(''.join, result))
    return result

# 以便管理动画
animations = []

class Animation:
    """动画效果类"""
    def __init__(self, func, stop, on_stop, flag: str = ''):
        """
        初始化方法
        :param func: 执行动画效果的函数
        :param stop: 停止条件（callable）
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同的动画只执行最后创建的一个
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
        self.stop = R_TRUE
    
    def execute(self) -> None:
        """动画效果实际执行的方法"""
        if self.stop():
            self.kill()
            self.on_stop()
        else:
            self.func()
            self.counter += 1
            schedule(1 / 60, self.execute)

class MoveAnimation(Animation):
    """平移效果类"""
    def __init__(self, widget, target: tuple[int, int], step: tuple[int, int], flag: str = ''):
        """
        初始化方法
        :param widget: 要应用效果的组件
        :param target: 组件移动后的位置
        :param step: 每 1 / 60 秒移动的距离
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同的动画只执行最后创建的一个
        """
        super().__init__(self.move, lambda: self.widget_pos == target, PASS, flag)
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
        初始化方法
        :param widget: 要应用效果的组件
        :param text: 文字
        :param flag: 组件“标记”，默认为空，当 flag 不为空时相同的动画只执行最后创建的一个
        """
        super().__init__(lambda: widget.config(text=text[:self.counter // 2] + ' |'),
                         lambda: widget['text'][:-2] == text,
                         lambda: widget.config(text=text), flag)

def set_page(index, animation=True):
    """
    set_page() 是一个获取执行“切换到指定页面”任务的函数的函数
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
    def __init__(self, f):
        self.json = json.load(f)
        self.name = self.json.pop('name')
        self.jqxy_not_u = self.json.pop('jqxy_not_u')

    def __str__(self):
        # 通过 __str__ 让 OptionMenu 的参数可以直接使用方案而不需要提取其 name 属性
        return self.name

    def find_keys(self, pin) -> list[str]:
        """
        根据拼音寻找按键
        :param pin: 拼音
        :return: 按键列表
        """
        return pin if pin in SHENGS1 else self.json.get(pin, '').split(',')

    def find_pins(self, key) -> list[str]:
        """
        根据按键寻找拼音
        :param key: 按键
        :return: 拼音列表
        """
        return [pin for pin, keys in self.json.items() if key in keys.split(',')]

    def get_codes(self, text: str, pinyin=False, max_length=100) -> list:
        """
        获取一个/多个汉字的双拼输入方法
        :param text: 一个/多个汉字，或者一个拼音
        :param pinyin: text 是否是拼音
        :param max_length: 最多返回的数量（默认返回 100 个）
        :return: 双拼输入方法
        """
        # get_pinyins(...) -> 类似 [[a, b], # 一行代表一个字的所有读音
        #                           [c, d],
        #                           [e, f]]
        pinyins = [[text]] if pinyin else PYS(text)
        results, fks = [], GP().find_keys
        for char in pinyins:
            results.append([])
            for pinyin in char:
                p1, p2 = split_pinyin(pinyin)
                if p1:
                    # 不是零声母
                    k1s, k2s = fks(p1), fks(p2)
                    if p1 in 'jqxy' and p2 == 'ü' and not self.jqxy_not_u:
                        # 这时，ü 也可以使用 u 对应的键
                        k2s.extend(fks('u'))
                    results[-1].extend(make_pairs(k1s, k2s, merge=True))
                else:
                    # 零声母
                    results[-1].extend(self.find_keys(f'_{p2}'))
            # 现在，result[i] 代表第 (i + 1) 个（第 i 个？）字所有可能的输入方式
        return make_pairs(*results, merge=True)[:max_length]

    def draw_keys(self) -> None:
        """给键盘绘制对应的拼音"""
        # 删除以前绘制的
        [label.place_forget() for label in keylabels]
        keylabels.clear()
        # 记录每个 Label 上拼音的位置
        positions = {}
        for i in range(10):
            positions['qwertyuiop'[i]] = [i * 80 + 35, 60]
            positions['asdfghjkl;'[i]] = [i * 80 + 65, 140]
            positions['zxcvbnm   '[i]] = [i * 80 + 110, 220]
        del positions[' ']
        pinfont = '更纱黑体 SC', 12, NORMAL
        # 记录每个按键对应的韵母
        keyyuns = {k: [] for k in KEYS}
        zerol['text'] = '零声母情况：\n'
        for pin, keys_s in self.json.items():
            keys = keys_s.split(',')
            if pin[0] == '_':
                # 零声母
                zerol['text'] += f'{pin[1:]} -> {keys_s}\n'
            elif pin in ['zh', 'ch', 'sh']:
                # 声母
                for key in keys:
                    # 和其他声母一样，直接往按键上标就行了
                    x, y = positions[key]
                    label = Label(keymapf, text=pin, font=pinfont, **C_SHENG)
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
            label = Label(keymapf, text=text, font=pinfont, **C_YUN)
            label.place(x=x, y=y)
            keylabels.append(label)

def load_plans() -> None:
    """加载所有双拼方案"""
    # 并不需要 global，因为实际上并没有对 plans 进行“赋值”操作
    plans.clear()
    for file in os.listdir('plans'):
        with open(f'plans/{file}', encoding='utf-8') as f:
            plans.append(Plan(f))

plans = []
load_plans()
with open('messages.txt', encoding='utf-8') as f:
    messages = f.read().splitlines()

def split_pinyin(pinyin: str) -> tuple[str, str]:
    """
    将 pinyin 拆分为声母部分和韵母部分
    :return: (声母, 韵母)
    """
    pinyin = re.sub(r'([jqxy])u', r'\1ü', pinyin)
    if pinyin[0] in 'aoe':
        # 零声母
        return '', pinyin
    if pinyin[1] == 'h':
        # 第二个字母是 h 代表是翘舌音，以翘舌音为界即可
        return pinyin[:2], pinyin[2:]
    return pinyin[0], pinyin[1:]

def find_keys(*_) -> None:
    """根据音节寻找按键"""
    # 允许用户使用 v 代替 ü；用 list 避免 '' 或 'bp' 也被识别为第一种情况
    if result := GP().find_keys(find1v.get().replace('v', 'ü')):
        find1l['text'] = ','.join(result)
    else:
        # 找不到
        find1l['text'] = '-'

def find_pins(*_) -> None:
    """根据按键寻找音节"""
    if (key := find2e.get().lower()) in KEYS:
        find2l['text'] = ','.join(GP().find_pins(key))
    else:
        find2l['text'] = '-'

def get_codes() -> None:
    if not (value := find3e.get()):
        # 用户什么也没输入
        return
    for char in value:
        if char not in CHARS:
            msb.showerror('错误', f'无法解析 {repr(char)}')
            return
    msb.showinfo('结果', '\n'.join(GP().get_codes(value)))

def random_char() -> None:
    """显示一个随机汉字"""
    charl['text'] = random.choice(list(PCHARS))
    # 注上拼音
    pinyinl['text'] = PCHARS[charl['text']]
    if keytipv.get():
        update_key_tip()

def update_key_tip(*_) -> None:
    """给显示的随机汉字添加按键提示"""
    if ' ' in pinyinl['text']:
        # 已经有按键提示了，不需要操作
        return
    pinyinl['text'] += f' [{','.join(GP().get_codes(pinyinl['text'], True))}]'

def check_input(*_) -> None:
    """检查显示的拼音所有拼法里是否有用户输入的内容"""
    if len(value := inputv.get()) < 2:
        # 用户还没输入完
        return
    # 懒得一直加 if（或者 xxx and recordst.insert(...)）了，索性就利用 tkinter 的特性，一直禁着
    recordst.config(state=(DISABLED, NORMAL)[recordv.get()])
    # recordst 里第 2 行使用的序号使用的是 1.（第一行是表头）
    # index 仍然储存实际位置 2
    index = recordst.get(1.0, END).count('\n')
    recordst.insert(END, f'{index - 1}.\t{(pinyin := pinyinl['text'].split()[0])}\t{value}\t')
    if value in GP().get_codes(pinyin, True):
        recordst.insert(END, f'✓\n')
        recordst.tag_add('correct', float(index), float(index + 1))
        # 对了才能下一个字
        random_char()
    else:
        recordst.insert(END, f'×\n')
        recordst.tag_add('wrong', float(index), float(index + 1))
    # 添加 tag 是为了给对错两种情况分别加上绿色和红色
    # 无论用户输入对不对，都应该清空
    inputv.set('')
    # 得防着点用户
    recordst.config(state=DISABLED)
    recordst.see(END)

def new_plan() -> None:
    """创建新双拼方案功能的 command"""
    def add(title: str, height: int, x: int, y: int, bootstyle: str, texts: str) -> None:
        """
        创建一个有若干个 Label、Entry 的 Labelframe
        :param title: Labelframe 标题
        :param height: Labelframe 高度
        :param x: Labelframe 左上角 x 坐标
        :param y: Labelframe 左上角 y 坐标
        :param bootstyle: str，内容为 bootstyle
        :param texts: str
        """
        labelframe = Labelframe(top, text=title, width=240, height=height)
        for i, text in enumerate(texts.split()):
            label = Label(labelframe, text=text, font=FT(12))
            label.place(x=10, y=10 + i * 30)
            entry = Entry(labelframe, bootstyle=bootstyle)
            entry.place(x=50, y=10 + i * 30)
            widgets.append((label, entry))
        labelframe.place(x=x, y=y)
    def create() -> None:
        """创建按钮的 command"""
        if not namee.get():
            msb.showerror('错误', f'未填写方案名称。')
            return top.focus_set()
        data = {'name': namee.get()}
        for label, entry in widgets:
            # “所有 key 都是 a-z 或 ; 的按键”不满足
            if not all(map(lambda key: key in KEYS, entry.get().split(','))):
                # 没有填完
                msb.showerror('错误', f'未填写 {label['text']}。')
                return top.focus_set()
            data[label['text']] = entry.get()
        data['jqxy_not_u'] = notuv.get()
        if path := fd.asksaveasfilename(title='保存方案', filetypes=(('JSON', '*.json'),), initialdir='plans',
                                        defaultextension='.json', parent=top):
            # 因为含有“ü”，所以需要特别指出 utf-8，不然“ü”会被读取为“眉”
            with open(path, 'w', encoding='utf-8') as f:
                # ensure_ascii 需要关闭，以免 ü 被替换为 ASCII 码
                json.dump(data, f, indent=4, ensure_ascii=False)
    top = Toplevel('新方案', size=(520, 900), resizable=(False, False))
    namel = Label(top, text='名称：', font=FT(12))
    namel.place(x=10, y=10)
    namee = Entry(top, bootstyle=SECONDARY)
    namee.place(x=60, y=10)
    # 把用到的 Label 和 Entry 收集起来，方便读取并保存至 JSON
    widgets = []
    add('zh ch sh', 130, 10, 50, SUCCESS, 'zh ch sh')
    add('韵母', 850, 270, 10, INFO, 'a o e i u ü ai ei ui ao ou iu ie üe an en in un ün ang eng ing ong ia ua uo uai')
    add('韵母', 250, 10, 190, INFO, 'iao ian uan üan iang uang iong')
    add('零声母', 400, 10, 450, DANGER, '_a _o _e _ai _ei _ao _ou _er _an _en _ang _eng')
    Checkbutton(top, text='禁止 jqxy 后的 ü 使用 u', font=FT(12), variable=(notuv := BooleanVar(value=False))).place(x=120, y=860)
    createb = Button(top, text='创建', command=create, bootstyle=OL(SUCCESS))
    createb.place(x=10, y=860)
    cancelb = Button(top, text='取消', command=top.destroy, bootstyle=OL(SECONDARY))
    cancelb.place(x=68, y=860)
    top.mainloop()

def update_alpha(*_) -> None:
    """更新窗口透明度设置情况"""
    window.attributes('-alpha', (alpha := alphav.get()) / 100)
    alphal['text'] = f'透明度：{alpha}%'
    alpha1b['state'] = (NORMAL, DISABLED)[alpha >= 100]
    alpha2b['state'] = (NORMAL, DISABLED)[alpha <= 20]

def change_msg() -> None:
    """更换一个“回声洞”内容"""
    TypingAnimation(msgl, random.choice(messages), 'hsd').execute()

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
planv = StringVar()
# 'write' 表示当 Var 被修改时调用的函数，lambda 内容为找到对应的双拼方案并绘制键位图
# 这里的 lambda 函数不能直接写“GP().draw_keys”，因为这种方式每次的 GP() 其实并没有被执行
planv.trace_add('write', lambda *_: GP().draw_keys())
planv.set('小鹤双拼')
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
# 汉字 -> 对应按键
find3l = Label(keymapf, text='寻找汉字对应的按键：\n（按键可能不唯一）', font=FT(14), bootstyle=INFO)
find3l.place(x=140, y=490)
find3e = Entry(keymapf, bootstyle=INFO)
find3e.place(x=330, y=490)
find3b = Button(keymapf, text='寻找', command=get_codes, bootstyle=OL(INFO))
find3b.place(x=500, y=490)

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
recordlf = Labelframe(practicef, text='练习记录', width=400, height=310, bootstyle=SUCCESS)
recordst = ScrolledText(recordlf, width=50, height=15)
recordst.tag_config('correct', foreground='#008000')
recordst.tag_config('wrong', foreground='#ff0000')
recordst.insert(END, '序号\t拼音\t输入内容\t是否正确\n')
# 要设置 state=DISABLED 以防止用户自行更改
recordst.config(state=DISABLED)
recordst.place(x=10, y=10)
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
updateb = Button(aboutlf, text='检查更新（未完工，作者仍未放弃）', bootstyle=OL(INFO), state=DISABLED)
updateb.place(x=250, y=10)
fishcb = Button(aboutlf, text='↪ FishC', command=lambda: OT('https://fishc.com.cn/thread-249454-1-1.html'), bootstyle=OL(DANGER))
fishcb.place(x=10, y=50)
githubb = Button(aboutlf, text='↪ GitHub', command=lambda: OT('https://github.com/dddddgz/doublepinyin'), bootstyle=OL(DARK))
githubb.place(x=89, y=50)
aboutlf.place(x=10, y=330)

frames = [keymapf, practicef, settingsf]
set_page(0, False)()
window.mainloop()
