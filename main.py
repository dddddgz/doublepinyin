import os, json, random, time
from ttkbootstrap import *
from tkinter import messagebox as msb, filedialog as fd, Checkbutton
from itertools import product
from threading import Thread

def schedule(interval: int | float, func) -> None:
    """在 interval 秒后执行 func"""
    Thread(target=lambda: (time.sleep(interval), func()), daemon=True).start()

get_pinyins = lambda text: [chars[char] for char in text]
get_pinyin = lambda text: ''.join(map(lambda x: x[0], get_pinyins(text)))

with open('chars.txt', encoding='utf-8') as f:
    chars = {}
    for line in f.read().splitlines():
        p, cs = line.split()
        for c in cs:
            if c in chars:
                chars[c].append(p)
            else:
                chars[c] = [p]
with open('chars2.txt', encoding='utf-8') as f:
    chars2 = {}
    for line in f.read().splitlines():
        p, cs = line.split()
        for c in cs:
            chars2[c] = p

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

del p, cs, c
# 以便灵活地管理动画
animations = []
# 定义几个常用的 callable
PASS = lambda: None
STOP_NOW = lambda: True

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
        self.stop = STOP_NOW
    
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
        info = self.widget.place_info()
        return int(info['x']), int(info['y'])
    
    def move(self) -> None:
        """平移"""
        (x, y), (tx, ty), (dx, dy) = self.widget_pos, self.target, self.step
        if x > tx:
            dx *= -1
        if y > ty:
            dy *= -1
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
        return self.json.get(pin, '').split(',')

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
        pinyins = [[text]] if pinyin else get_pinyins(text)
        results, plan = [], gplan()
        for char in pinyins:
            results.append([])
            for pinyin in char:
                p1, p2 = split_pinyin(pinyin)
                if p1:
                    # 不是零声母
                    k1s, k2s = plan.find_keys(p1) if len(p1) > 1 else [p1], plan.find_keys(p2)
                    if p1 in 'jqxy' and p2 == 'ü' and not self.jqxy_not_u:
                        # 这时，ü 也可以使用 u 对应的键
                        k2s.extend(plan.find_keys('u'))
                    results[-1].extend(make_pairs(k1s, k2s, merge=True))
                else:
                    # 零声母
                    results[-1].extend(self.find_keys(f'_{p2}'))
            # 现在，result[i] 代表第 (i + 1) 个（第 i 个？）字所有可能的输入方式
        return make_pairs(*results, merge=True)[:max_length]

    def draw_keys(self) -> None:
        """给键盘绘制对应的拼音"""
        # 删除以前绘制的
        for label in keylabels:
            label.place_forget()
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
        keyyuns = {k: [] for k in 'qwertyuiopasdfghjkl;zxcvbnm'}
        zerol['text'] = '零声母情况：\n'
        for pin, keys in self.json.items():
            if pin[0] == '_':
                # 零声母
                zerol['text'] += f'{pin[1:]} -> {keys}\n'
            else:
                # 用 ',' 分开（同一个拼音可以对应多个按键）
                for key in keys.split(','):
                    if pin in ['zh', 'ch', 'sh']:
                        # 它们和其他声母一样，直接往按键上标就行了
                        x, y = positions[key]
                        label = Label(keymapf, text=pin, background='#fff', foreground='#00a0e0', font=pinfont)
                        label.place(x=x, y=y)
                        keylabels.append(label)
                        # 轮到韵母使用这个键了
                        positions[key][1] += 22
                    else:
                        # 是韵母（要先统计出一个按键上所有的韵母）
                        keyyuns[key].append(pin)
        for key, yuns in keyyuns.items():
            x, y = positions[key]
            if len(yuns) < 3:
                # 可以一行一行显示
                text = '\n'.join(yuns)
            else:
                # 要加逗号显示
                text = f'{','.join(yuns[:2])}\n{','.join(yuns[2:])}'
            label = Label(keymapf, text=text, background='#fff', foreground='#808080', font=pinfont)
            label.place(x=x, y=y)
            keylabels.append(label)

def load_plans() -> None:
    """加载所有双拼方案"""
    # 并不需要 global，因为实际上并没有对 plans 进行“赋值”操作
    plans.clear()
    for file in os.listdir('plans'):
        # plans 文件夹下所有 .json 文件都是双拼方案
        if file.endswith('.json'):
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
    pinyin = pinyin.replace('ju', 'jü').replace('qu', 'qü').replace('xu', 'xü').replace('yu', 'yü')
    if pinyin[0] in 'aoe':
        # 零声母
        return '', pinyin
    if pinyin[1] == 'h':
        # 第二个字母是 h 代表是翘舌音，以翘舌音为界即可
        return pinyin[:2], pinyin[2:]
    return pinyin[0], pinyin[1:]

def gplan() -> Plan:
    """获取目前正在使用的双拼方案"""
    return [plan for plan in plans if plan.name == planv.get()][0]

def gfont(fontsize: int) -> tuple[str, int, str]:
    """
    给定字体大小，获取对应的微软雅黑字体
    :param fontsize: 字体大小
    :return: 字体
    """
    return ('更纱黑体 SC', fontsize, NORMAL)

def gol(bootstyle: str) -> tuple[int]:
    """获取 bootstyle 对应的 outline 样式"""
    return (bootstyle, OUTLINE)

def find_keys(*_) -> None:
    """根据音节寻找按键"""
    # 允许用户使用 v 代替 ü；用 list 避免 '' 或 'bp' 也被识别为第一种情况
    if (target := find1v.get().replace('v', 'ü')) in list('bpmfdtnlgkhjqxzcsryw'):
        # 单个字母的声母
        find1l['text'] = target
    elif result := gplan().json.get(target):
        # zh ch sh 韵母
        find1l['text'] = result
    else:
        # 找不到
        find1l['text'] = '-'

def find_pins(*_) -> None:
    """根据按键寻找音节"""
    if (key := find2e.get().lower()) in list('qwertyuiopasdfghjkl;zxcvbnm'):
        find2l['text'] = ','.join(gplan().find_pins(key))
    else:
        find2l['text'] = '-'

def get_codes() -> None:
    if not (value := find3e.get()):
        # 用户什么也没输入
        return
    for char in value:
        if char not in chars:
            msb.showerror('错误', f'无法解析 {repr(char)}')
            return
    msb.showinfo('结果', '\n'.join(gplan().get_codes(value)))

def random_char(*_) -> None:
    """显示一个随机汉字"""
    charl['text'] = random.choice(list(chars2))
    # 注上拼音
    pinyinl['text'] = chars2[charl['text']]

def check_input(*_) -> None:
    """检查显示的拼音所有拼法里是否有用户输入的内容"""
    if len(value := inputv.get()) < 2:
        # 用户还没输入完
        return
    # 懒得一直加 if（或者 xxx and recordst.insert(...)）了，索性就利用 tkinter 的特性，一直禁着
    if recordv.get():
        # 让记录变得可以使用
        recordst.config(state=NORMAL)
    index = recordst.get(1.0, END).count('\n')
    pinyin = pinyinl['text']
    # recordst 里第 2 行使用的序号使用的是 1.（第一行是表头）
    # index 仍然储存实际位置 2
    recordst.insert(END, f'{index - 1}.\t{pinyin}\t{value}\t')
    if value in gplan().get_codes(pinyin, True):
        # 用户输入对了，添加 tag
        recordst.insert(END, f'✓\n')
        recordst.tag_add('correct', float(index), float(index + 1))
        # 对了才能下一个字
        random_char()
    else:
        recordst.insert(END, f'×\n')
        # 用户输入错了，也要添加 tag
        recordst.tag_add('wrong', float(index), float(index + 1))
    # 无论用户输入对不对，都应该清空
    inputv.set('')
    # 得防着点用户
    recordst.config(state=DISABLED)
    recordst.see(END)

def set_theme(*_) -> None:
    """设置界面中设置主题功能的 command"""
    window.style.theme_use(themev.get())

def view_plan() -> None:
    """查看当前双拼方案功能的 command"""
    msb.showinfo('', str(gplan().json).replace(',', ',\n'))

def new_plan() -> None:
    """创建新双拼方案功能的 command"""
    def adds(labelframe: Labelframe, bootstyle: str, texts: str) -> Labelframe:
        """
        增加若干个 Label 和相对应的 Entry
        :param labelframe: Labelframe
        :param bootstyle: str，内容为 bootstyle
        :param texts: str
        :return: Labelframe
        """
        for i, text in enumerate(texts.split()):
            label = Label(labelframe, text=text, font=gfont(12))
            label.place(x=10, y=10 + i * 30)
            entry = Entry(labelframe, bootstyle=bootstyle)
            entry.place(x=50, y=10 + i * 30)
            widgets.append((label, entry))
        return labelframe
    def create() -> None:
        """创建按钮的 command"""
        if not namee.get():
            msb.showerror('错误', f'未填写方案名称。')
            top.focus_set()
            return
        data = {'name': namee.get()}
        for label, entry in widgets:
            if not entry.get():
                # 没有填完
                msb.showerror('错误', f'未填写 {label['text']}。')
                top.focus_set()
                return
            data[label['text']] = entry.get()
        data['jqxy_not_u'] = notuv.get()
        if path := fd.asksaveasfilename(title='保存方案', filetypes=(('JSON', '*.json'),), initialdir='plans',
                                        defaultextension='.json', parent=top):
            # 因为含有“ü”，所以需要特别指出 utf-8，不然“ü”会被读取为“眉”
            with open(path, 'w', encoding='utf-8') as f:
                # ensure_ascii 需要关闭，以免 ü 被替换为 ASCII 码
                json.dump(data, f, indent=4, ensure_ascii=False)
    top = Toplevel('新方案', size=(520, 900), resizable=(False, False))
    namel = Label(top, text='名称：', font=gfont(12))
    namel.place(x=10, y=10)
    namee = Entry(top, bootstyle=SECONDARY)
    namee.place(x=60, y=10)
    # 把用到的 Label 和 Entry 收集起来，方便读取并保存至 JSON
    widgets = []
    # zh ch sh
    adds(Labelframe(top, text='zh ch sh', width=240, height=130), SUCCESS, 'zh ch sh').place(x=10, y=50)
    # 韵母(1)
    adds(Labelframe(top, text='韵母', width=240, height=850), INFO,
         'a o e i u ü ai ei ui ao ou iu ie üe an en in un ün ang eng ing ong ia ua uo uai').place(x=270, y=10)
    # 韵母(2)
    adds(Labelframe(top, text='韵母', width=240, height=250), INFO, 'iao ian uan üan iang uang iong').place(x=10, y=190)
    # 零声母
    adds(Labelframe(top, text='零声母', width=240, height=400), DANGER,
         '_a _o _e _ai _ei _ao _ou _er _an _en _ang _eng').place(x=10, y=450)
    Checkbutton(top, text='禁止 jqxy 后的 ü 使用 u', font=gfont(12), variable=(notuv := BooleanVar(value=False))).place(x=120, y=860)
    Button(top, text='创建', command=create, bootstyle=gol(SUCCESS)).place(x=10, y=860)
    Button(top, text='取消', command=top.destroy, bootstyle=gol(SECONDARY)).place(x=68, y=860)
    top.mainloop()

def set_alpha(alpha):
    """设置窗口透明度为 alpha"""
    alphal['text'] = f'透明度：{alpha}%'
    window.attributes('-alpha', alpha / 100)
    if alpha <= 20:
        alpha1b['state'] = NORMAL
        alpha2b['state'] = DISABLED
    elif alpha >= 100:
        alpha1b['state'] = DISABLED
        alpha2b['state'] = NORMAL
    else:
        alpha1b['state'] = NORMAL
        alpha2b['state'] = NORMAL

def alpha_up():
    """调高窗口透明度"""
    set_alpha(min(100, int(alphal['text'][4:-1]) + 10))

def alpha_down():
    """调低窗口透明度"""
    set_alpha(max(20, int(alphal['text'][4:-1]) - 10))

def change_msg():
    """更换一个“回声洞”内容"""
    TypingAnimation(msgl, random.choice(messages), 'hsd').execute()

window = Window('DoublePinyin 双拼练习器', size=(1000, 760), resizable=(False, False))

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
zerol = Label(keymapf, font=gfont(16))
zerol.place(x=10, y=330)
# 由于下拉选择也需要用到表示双拼方案的 StringVar，下拉选择只能写在最后
Label(keymapf, text='请选择双拼方案：', font=gfont(16)).place(x=10, y=10)
# 使用 StringVar 记录菜单的选项
planv = StringVar()
# 'write' 表示当 Var 被修改时调用的函数，lambda 内容为找到对应的双拼方案并绘制键位图
# 这里的 lambda 函数不能直接写“gplan().draw_keys”，因为这种方式每次的 gplan() 其实并没有被执行
planv.trace_add('write', lambda *_: gplan().draw_keys())
planv.set('小鹤双拼')
# 下拉菜单（让下拉菜单永远“认准”这个 StringVar，它的数据会和 StringVar 绑定）
plano = OptionMenu(keymapf, planv, None, *plans, bootstyle=gol(WARNING))
plano.place(x=190, y=10)

find1lf = Labelframe(keymapf, text='音节 -> 按键', width=500, height=70, bootstyle=DANGER)
find1v = StringVar()
find1v.trace_add('write', find_keys)
find1e = Entry(find1lf, textvariable=find1v, bootstyle=DANGER)
find1e.place(x=10, y=10)
find1l = Label(find1lf, text='-', font=gfont(12), bootstyle=DANGER)
find1l.place(x=180, y=10)
find1lf.place(x=140, y=310)

find2lf = Labelframe(keymapf, text='按键 -> 音节', width=500, height=70, bootstyle=PRIMARY)
find2v = StringVar()
find2v.trace_add('write', find_pins)
find2e = Entry(find2lf, textvariable=find2v, bootstyle=PRIMARY)
find2e.place(x=10, y=10)
find2l = Label(find2lf, text='-', font=gfont(12), bootstyle=PRIMARY)
find2l.place(x=180, y=10)
find2lf.place(x=140, y=400)
# 汉字 -> 对应按键
find3l = Label(keymapf, text='寻找汉字对应的按键：\n（按键可能不唯一）', font=gfont(14), bootstyle=INFO)
find3l.place(x=140, y=490)
find3e = Entry(keymapf, bootstyle=INFO)
find3e.place(x=330, y=490)
find3b = Button(keymapf, text='寻找', command=get_codes, bootstyle=gol(INFO))
find3b.place(x=500, y=490)

# 练习界面
practicef = Frame(window, width=1000, height=700)
# 用于显示拼音的 Label
pinyinl = Label(practicef, font=gfont(20))
pinyinl.place(x=250, y=70)
# 用于显示汉字的 Label
charl = Label(practicef, font=('楷体', 120, NORMAL))
charl.place(x=200, y=120)
# 提供输入框，并且给它绑定 StringVar，当字正确时自动下一个字
inputv = StringVar()
inputv.trace_add('write', check_input)
inpute = Entry(practicef, textvariable=inputv, bootstyle=SUCCESS)
inpute.place(x=200, y=310)
recordcb = Checkbutton(practicef, text='启用练习记录', variable=(recordv := BooleanVar()))
recordcb.place(x=430, y=20)
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
themev = StringVar(None, 'litera')
themev.trace_add('write', set_theme)
themeo = OptionMenu(themelf, themev, None, *window.style.theme_names(), bootstyle=gol(INFO))
themeo.place(x=10, y=10)
themel = Label(themelf, text='主题效果')
themel.place(x=10, y=50)
theme1b = Button(themelf, text=PRIMARY, bootstyle=gol(PRIMARY))
theme1b.place(x=10, y=80)
theme2b = Button(themelf, text=SECONDARY, bootstyle=gol(SECONDARY))
theme2b.place(x=89, y=80)
theme3b = Button(themelf, text=SUCCESS, bootstyle=gol(SUCCESS))
theme3b.place(x=183, y=80)
theme4b = Button(themelf, text=INFO, bootstyle=gol(INFO))
theme4b.place(x=261, y=80)
theme5b = Button(themelf, text=WARNING, bootstyle=gol(WARNING))
theme5b.place(x=317, y=80)
theme6b = Button(themelf, text=DANGER, bootstyle=gol(DANGER))
theme6b.place(x=397, y=80)
theme7b = Button(themelf, text=LIGHT, bootstyle=gol(LIGHT))
theme7b.place(x=473, y=80)
theme8b = Button(themelf, text=DARK, bootstyle=gol(DARK))
theme8b.place(x=534, y=80)
themelf.place(x=10, y=10)

planslf = Labelframe(settingsf, text='双拼方案', width=980, height=70)
reloadb = Button(planslf, text='重新加载', command=lambda: (load_plans(), plano.set_menu(None, *plans)), bootstyle=gol(PRIMARY))
reloadb.place(x=10, y=10)
newplanb = Button(planslf, text='新方案', command=new_plan, bootstyle=gol(WARNING))
newplanb.place(x=92, y=10)
planslf.place(x=10, y=170)

attrlf = Labelframe(settingsf, text='窗口属性', width=980, height=70)
alphal = Label(attrlf, text='透明度：100%')
alphal.place(x=10, y=10)
alpha1b = Button(attrlf, text='↑', state=DISABLED, command=alpha_up, bootstyle=gol(INFO))
alpha1b.place(x=120, y=10)
alpha2b = Button(attrlf, text='↓', command=alpha_down, bootstyle=gol(INFO))
alpha2b.place(x=160, y=10)
attrlf.place(x=10, y=250)

msglf = Labelframe(settingsf, text='回声洞', width=980, height=70)
msgb = Button(msglf, text='↻', command=change_msg, bootstyle=gol(SUCCESS))
msgb.place(x=10, y=10)
msgl = Label(msglf, text='←Click that', font=gfont(10))
msgl.place(x=50, y=15)
msglf.place(x=10, y=330)
frames = [keymapf, practicef, settingsf]
set_page(0, False)()

window.mainloop()
