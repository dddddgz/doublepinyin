import os, json, pypinyin, re, random, requests
from ttkbootstrap import *
from tkinter import messagebox as msb, filedialog as fd, TclError, Checkbutton
from itertools import product
from threading import Timer

def get_pinyins(text: str, tone=True) -> list[str]:
    result = pypinyin.pinyin(text, (pypinyin.NORMAL, pypinyin.TONE)[tone], True, v_to_u=True)
    for i, char in enumerate(text):
        if char == '嗯':
            result[i] = ['én', 'ěn', 'èn'] if tone else ['en']
        elif char == '哼':
            result[i] = ['hēng'] if tone else ['heng']
        elif char == '噷':
            result[i] = ['hēn', 'xīn'] if tone else ['hen', 'xin']
        elif char == '欸':
            result[i] = ['āi', 'ǎi', 'ēi', 'éi', 'ěi', 'èi'] if tone else ['ai', 'ei']
        elif char == '诶':
            result[i] = ['ēi', 'éi', 'ěi', 'èi', 'xī'] if tone else ['ei', 'xi']
        elif char == '姆':
            result[i] = ['mǔ'] if tone else ['mu']
        elif char == '呒':
            result[i] = ['mú'] if tone else ['mu']
        elif char == '呣':
            result[i] = ['móu', 'mú', 'mù'] if tone else ['mou', 'mu']
    return result

def get_pinyin(text: str, tone=True) -> str:
    return ''.join(map(lambda x: x[0], get_pinyins(text, tone)))

def make_pairs(*lists, merge=False) -> list:
    """
    将所有参数中的所有元素进行搭配
    :param merge: 是否合并元素（例如 ['1', '2'] 和 ['3', '4']，合并后会返回 ['13', '14', '23', '24']）
    :return: 搭配结果
    """
    result = list(product(*lists))
    if merge:
        return list(map(''.join, result))
    return result

class Animation:
    """动画效果类"""
    def __init__(self, func, times: int):
        """
        初始化方法
        :param func: 执行动画效果的函数
        :param times: 执行次数
        """
        self.func = func
        self.counter = 0
        self.stop = times
    
    def execute(self) -> None:
        """动画效果实际执行的方法"""
        self.func()
        self.counter += 1
        if self.counter < self.stop:
            Timer(1 / 60, self.execute).start()

def set_page(index):
    """
    set_page() 是一个获取执行“切换到指定页面”任务的函数的函数
    :param index: 页面的索引
    :return: 执行上述任务的函数
    """
    def inner() -> None:
        for i, frame in enumerate(frames):
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

    def get_code(self, text: str, max_length=100) -> list:
        """
        获取一个/多个汉字的双拼输入方法
        :param text: 一个/多个汉字
        :param max_length: 最多返回的数量（默认返回 100 个）
        :return: 双拼输入方法
        """
        # get_pinyins(...) -> 类似 [(a, b), # 一行代表一个字的所有读音
        #                           (c, d),
        #                           (e, f)]
        pinyins = get_pinyins(text, False)
        results, plan = [], get_current_plan()
        for char in pinyins:
            # result[i] 代表第 (i + 1) 个（第 i 个？）字所有可能的输入方式
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
        return make_pairs(*results, merge=True)[:max_length]

    def draw_keys(self) -> None:
        """给键盘绘制对应的拼音"""
        # 记录每个 Label 上拼音的位置
        positions = {'q': [ 35,  57], 'w': [109,  57], 'e': [183,  57], 'r': [257,  57], 't': [331,  57],
                     'y': [405,  57], 'u': [479,  57], 'i': [553,  57], 'o': [627,  57], 'p': [701,  57],
                     'a': [ 65, 129], 's': [139, 129], 'd': [213, 129], 'f': [287, 129], 'g': [361, 129],
                     'h': [435, 129], 'j': [509, 129], 'k': [583, 129], 'l': [657, 129], ';': [731, 129],
                     'z': [110, 203], 'x': [184, 203], 'c': [258, 203], 'v': [332, 203], 'b': [406, 203],
                     'n': [480, 203], 'm': [554, 203]}
        # 删除以前绘制的
        for label in keylabels:
            label.place_forget()
        keylabels.clear()
        zerol['text'] = '零声母情况：\n'
        for pin, keys in self.json.items():
            if pin[0] == '_':
                # 零声母
                zerol['text'] += f'{pin[1:]} -> {keys}\n'
            else:
                # 用 ',' 分开，使同一个拼音可以有不同的表示方式
                for key in keys.split(','):
                    # 非零声母的韵母和 zh ch sh 都可以在这里找到对应键位
                    x, y = positions[key]
                    (label := Label(keymapf, text=pin, background='#333', foreground='#fff', font=gfont(12))).place(x=x, y=y)
                    keylabels.append(label)
                    # 轮到下一个韵母使用这个键了；就算没有“下一个”也无妨
                    positions[key][1] += 25

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

def get_current_plan() -> Plan:
    """获取目前正在使用的双拼方案"""
    return [plan for plan in plans if plan.name == planv.get()][0]

def gfont(fontsize) -> tuple[str, int, str]:
    """
    给定字体大小，获取对应的微软雅黑字体
    :param fontsize: 字体大小
    :return: 字体
    """
    return ('微软雅黑', fontsize, NORMAL)

def find_key() -> None:
    """根据拼音寻找按键"""
    # 允许用户使用 v 代替 ü
    if result := get_current_plan().json.get(pin := find1e.get().replace('v', 'ü')):
        # 找得到
        msb.showinfo('结果', f'{pin} 对应的按键是 {result}')
    else:
        # 找不到
        msb.showerror('错误', f'仅支持 zh、ch、sh 和所有韵母，不支持 {repr(pin)}。')

def find_pins() -> None:
    """根据按键寻找拼音"""
    if len(key := find2e.get().lower()) != 1:
        msb.showerror('错误', '仅支持一个按键。')
    else:
        msb.showinfo('结果', f'按键 {key} 对应的拼音有 {get_current_plan().find_pins(key)}。')

def get_code() -> None:
    if not re.findall(r'^[\u4e00-\u9fa5]*$', chars := find3e.get()):
        # 不是纯中文
        msb.showerror('错误', '请输入纯中文。')
        return
    msb.showinfo('结果', '\n'.join(get_current_plan().get_code(chars)))

def random_char(*_) -> None:
    """显示一个随机字符"""
    if '1' in practicev.get():
        # 离线
        text = chr(random.randint(0x4e00, 0x9fa5))
    else:
        # 调用 API
        try:
            text = json.loads(requests.get('https://www.mocklib.com/mock/random/char/cn').text)['char']
        except requests.exceptions.ConnectionError as ex:
            # 网络存在问题
            msb.showerror('错误', f'网络存在问题，请稍后再试。\n{repr(ex)}')
            return
    charl['text'] = text
    # 还要给它注上拼音
    pinyinl['text'] = get_pinyin(text)

def check_input(*_) -> None:
    """检查用户的输入的双拼是否可以拼出 random_char() 显示的文字"""
    if len(value := inputv.get()) < 2:
        # 用户还没输入完
        return
    plan = get_current_plan()
    (k1, k2), (p1, p2) = value[:2], split_pinyin(get_pinyin(charl['text'], False))
    if (p1 == k1 or p1 in plan.find_pins(k1)) and p2 in plan.find_pins(k2):
        # 用户输入正确，下一个字
        random_char()
    # 无论用户输入对不对，都应该清空
    inputv.set('')

def set_theme(*_) -> None:
    """设置界面中设置主题功能的 command"""
    window.style.theme_use(themev.get())

def view_plan() -> None:
    """查看当前双拼方案功能的 command"""
    msb.showinfo('', str(get_current_plan().json).replace(',', ',\n'))

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
            (label := Label(labelframe, text=text, font=gfont(12))).place(x=10, y=10 + i * 30)
            (entry := Entry(labelframe, bootstyle=bootstyle)).place(x=50, y=10 + i * 30)
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
                msb.showerror('错误', f'未填写 {label["text"]}。')
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
    Label(top, text='名称：', font=gfont(12)).place(x=10, y=10)
    (namee := Entry(top, bootstyle=SECONDARY)).place(x=60, y=10)
    # 把用到的 Label 和 Entry 收集起来，方便读取并保存至 JSON
    widgets = []
    # zh ch sh
    adds(Labelframe(top, text='zh ch sh', width=240, height=130), PRIMARY, 'zh ch sh').place(x=10, y=50)
    # 韵母(1)
    adds(Labelframe(top, text='韵母', width=240, height=850), INFO,
         'a o e i u ü ai ei ui ao ou iu ie üe an en in un ün ang eng ing ong ia ua uo uai').place(x=270, y=10)
    # 韵母(2)
    adds(Labelframe(top, text='韵母', width=240, height=250), INFO, 'iao ian uan üan iang uang iong').place(x=10, y=190)
    # 零声母
    adds(Labelframe(top, text='零声母', width=240, height=400), DANGER,
         '_a _o _e _ai _ei _ao _ou _er _an _en _ang _eng').place(x=10, y=450)
    Checkbutton(top, text='禁止 jqxy 后的 ü 使用 u', font=gfont(12), variable=(notuv := BooleanVar(value=False))).place(x=120, y=860)
    Button(top, text='创建', command=create, bootstyle=SUCCESS).place(x=10, y=860)
    Button(top, text='取消', command=top.destroy, bootstyle=SECONDARY).place(x=68, y=860)
    top.mainloop()

def change_fact():
    """更换一个“你知道吗”内容"""
    factl['text'] = random.choice(messages)

def set_alpha(alpha):
    """
    设置窗口透明度
    :param alpha: 目标透明度
    """
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

window = Window('DoublePinyin 双拼练习器', size=(1000, 760), resizable=(False, False))

switchf = Frame(window, width=1000, height=50, bootstyle=SECONDARY)
Button(switchf, text='键位图', bootstyle=INFO, command=set_page(0)).place(x=20, y=10)
Button(switchf, text='练习', bootstyle=SUCCESS, command=set_page(1)).place(x=90, y=10)
Button(switchf, text='设置', bootstyle=WARNING, command=set_page(2)).place(x=150, y=10)
switchf.place(x=0, y=0)

keymapf = Frame(window, width=1000, height=700)
# 要先绘制键盘，再给按键写上对应的拼音
# 很不理解为什么网上很多人给出的解法是使用 ImageTk.PhotoImage(Image.open(...))
(keyboardl := Label(keymapf, image=(keyboardi := PhotoImage(file='keyboard.png')))).place(x=0, y=50)
# 这些代码必须写在关于绘制的功能前

# 键盘上显示的韵母都使用 Label
keylabels = []
# 专门显示零声母的解决方案
(zerol := Label(keymapf, font=gfont(16))).place(x=10, y=330)
# 由于下拉选择也需要用到表示双拼方案的 StringVar，下拉选择只能写在最后
Label(keymapf, text='请选择双拼方案：', font=gfont(16)).place(x=10, y=10)
# 使用 StringVar 记录菜单的选项
planv = StringVar()
# 'write' 表示当 Var 被修改时调用的函数，lambda 内容为找到对应的双拼方案并绘制键位图
# 这里的 lambda 函数不能直接写“get_current_plan().draw_keys”
# 因为这种方式每次的 get_current_plan() 其实并没有被执行
planv.trace_add('write', lambda *_: get_current_plan().draw_keys())
planv.set('小鹤双拼')
# 下拉菜单（让下拉菜单永远“认准”这个 StringVar，它的数据会和 StringVar“绑定”）
(plano := OptionMenu(keymapf, planv, None, *plans, bootstyle=INFO)).place(x=200, y=10)

# 拼音 -> 对应按键
Label(keymapf, text='寻找拼音对应的按键：\n（零声母请在韵母前加下划线）', font=gfont(14), bootstyle=WARNING).place(x=140, y=310)
(find1e := Entry(keymapf, bootstyle=WARNING)).place(x=330, y=310)
Button(keymapf, text='寻找', command=find_key, bootstyle=WARNING).place(x=500, y=310)
# 按键 -> 对应拼音
Label(keymapf, text='寻找按键对应的拼音：\n（仅支持一个按键）', font=gfont(14), bootstyle=SUCCESS).place(x=140, y=400)
(find2e := Entry(keymapf, bootstyle=SUCCESS)).place(x=330, y=400)
Button(keymapf, text='寻找', command=find_pins, bootstyle=SUCCESS).place(x=500, y=400)
# 汉字 -> 对应按键
Label(keymapf, text='寻找汉字对应的按键：\n（按键可能不唯一）', font=gfont(14), bootstyle=INFO).place(x=140, y=490)
(find3e := Entry(keymapf, bootstyle=INFO)).place(x=330, y=490)
Button(keymapf, text='寻找', command=get_code, bootstyle=INFO).place(x=500, y=490)

# 练习界面
practicef = Frame(window, width=1000, height=700)
# 创建一个用于显示拼音的 Label
(pinyinl := Label(practicef, font=gfont(20))).place(x=250, y=70)
# 将汉字显示在 Label 里
(charl := Label(practicef, font=('楷体', 120, NORMAL))).place(x=200, y=120)
# 还是使用变量记录数据
practicev = StringVar()
practicev.trace_add('write', random_char)
practicev.set('模式 1（基于 Unicode，生僻字较多）')
# 给出选择随机模式 1（可离线）和随机模式 2（不可离线）的下拉菜单
(modeo := OptionMenu(practicef, practicev, None, '模式 1（基于 Unicode，生僻字较多）',
                     '模式 2（基于 Web API，生僻字较少）', bootstyle=DANGER)).place(x=10, y=20)
# 提供输入框，并且给它绑定 StringVar，当字正确时自动下一个字
(inputv := StringVar()).trace_add('write', check_input)
(inpute := Entry(practicef, textvariable=inputv, bootstyle=INFO)).place(x=200, y=310)
Label(practicef, text='''作者对拼音的一点小看法：
1. bo po mo fo 应当改为 buo puo muo fuo
2. 梦-meng/mong，风-feng/fong，翁-weng/wong，这些字应当被视为多音字
3. 注音符号不应该把 in ün ing ong iong 注作 ㄧㄣ(ien) ㄩㄣ(üen) ㄧㄥ(ieng) ㄨㄥ(ueng) ㄩㄥ(üeng)，这些发音不符合现代发音了
4. iou uei uen 应该按照实际发音拼写（不简写）''', bootstyle=SECONDARY).place(x=10, y=600)

settingsf = Frame(window, width=1000, height=700)

themelf = Labelframe(settingsf, text='主题', width=980, height=150)
# 用 StringVar 记录主题选择界面；当主题被“写入”就运行 set_theme
(themev := StringVar(None, 'litera')).trace_add('write', set_theme)
(themeo := OptionMenu(themelf, themev, None, *window.style.theme_names())).place(x=10, y=10)
Label(themelf, text='主题效果').place(x=10, y=50)
Button(themelf, text=PRIMARY  , bootstyle=PRIMARY  ).place(x=10 , y=80)
Button(themelf, text=SECONDARY, bootstyle=SECONDARY).place(x=89 , y=80)
Button(themelf, text=SUCCESS  , bootstyle=SUCCESS  ).place(x=183, y=80)
Button(themelf, text=INFO     , bootstyle=INFO     ).place(x=261, y=80)
Button(themelf, text=WARNING  , bootstyle=WARNING  ).place(x=317, y=80)
Button(themelf, text=DANGER   , bootstyle=DANGER   ).place(x=397, y=80)
Button(themelf, text=LIGHT    , bootstyle=LIGHT    ).place(x=473, y=80)
Button(themelf, text=DARK     , bootstyle=DARK     ).place(x=534, y=80)
themelf.place(x=10, y=10)

planslf = Labelframe(settingsf, text='双拼方案', width=980, height=70)
(reloadb := Button(planslf, text='重新加载', command=lambda: (load_plans(), plano.set_menu(None, *plans)),
                   bootstyle=PRIMARY)).place(x=10, y=10)
Button(planslf, text='查看当前方案', command=view_plan, bootstyle=SUCCESS).place(x=92, y=10)
Button(planslf, text='新方案', command=new_plan, bootstyle=INFO).place(x=198, y=10)
planslf.place(x=10, y=170)

attrlf = Labelframe(settingsf, text='窗口属性', width=980, height=70)
(alphal := Label(attrlf, text='透明度：100%')).place(x=10, y=10)
(alpha1b := Button(attrlf, text='↑', state=DISABLED, command=alpha_up, bootstyle=DANGER)).place(x=120, y=10)
(alpha2b := Button(attrlf, text='↓', command=alpha_down, bootstyle=DANGER)).place(x=160, y=10)
attrlf.place(x=10, y=250)

factlf = Labelframe(settingsf, text='你知道吗', width=980, height=70)
Button(factlf, text='↻', command=change_fact, bootstyle=DARK).place(x=10, y=10)
(factl := Label(factlf, text='', font=gfont(12))).place(x=60, y=10)
factlf.place(x=10, y=330)
frames = [keymapf, practicef, settingsf]
set_page(0)()

window.mainloop()
