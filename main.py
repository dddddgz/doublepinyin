import os, json, pypinyin, re, random, requests
from ttkbootstrap import *
from tkinter import messagebox as msb, filedialog as fd, TclError

def get_pinyins(text, tone=True):
    result = pypinyin.pinyin(text, (pypinyin.NORMAL, pypinyin.TONE)[tone], True, v_to_u=True)
    for i, char in enumerate(text):
        if char == '嗯':
            result[i] = ['én', 'ěn', 'èn'] if tone else ['en']
        if char == '哼':
            result[i] = ['hēng'] if tone else ['heng']
        if char == '噷':
            result[i] = ['hēn', 'xīn'] if tone else ['hen', 'xin']
    return result

def get_pinyin(text, tone=True):
    return ''.join(map(lambda x: x[0], get_pinyins(text, tone)))

def switch_to(index):
    """
    获取执行“切换到指定页面”任务的函数
    :param index: 页面索引
    """
    def inner():
        for i, frame in enumerate(frames):
            if i == index:
                frame.place(x=0, y=60)
            else:
                frame.place_forget()
    return inner

class Plan:
    """双拼方案类"""
    def __init__(self, f):
        self.json = json.load(f)
        # 免得 name 被当作一个韵母处理，直接使用 pop
        self.name = self.json.pop('name')

    def __str__(self):
        # 通过 __str__ 让 OptionMenu 的参数可以直接使用方案而不需要提取其 name 属性
        return self.name

    def find_key(self, pin):
        """
        根据拼音寻找按键
        :param pin: 拼音
        :return: 按键
        """
        try:
            return self.json[pin]
        except KeyError:
            # 找不到
            return None

    def find_pins(self, target):
        """
        根据按键寻找拼音
        :param pin: 按键
        :return: 拼音
        """
        return [pin for pin, key in self.json.items() if target == key]

    def get_code(self, text, max_return=None):
        """
        获取一个/多个汉字的双拼输入方法
        :param text: 一个/多个汉字
        :param max_return: 最多返回的数量
        :return: 双拼输入方法
        """
        # 如果一个 slice 的 stop 是 None，就相当于 obj[start:]
        # 这里 start 其实也是 None
        answers = list(zip(*get_pinyins(text, False)))[:max_return]
        result = []
        for answer in answers:
            each_result = ''
            for each in answer:
                # each 就是每个字的拼音
                # 分隔声母和韵母
                each = each.replace('ju', 'jü').replace('qu', 'qü').replace('xu', 'xü').replace('yu', 'yü')
                if each[0] in 'aoe':
                    # 零声母
                    sheng, yun = '', each
                elif each[1] == 'h':
                    # 不用考虑越界问题（上面也是一样一样），因为 pypinyin.pinyin() 的返回值是一个合法的拼音
                    # 第二个字母是 h 代表是翘舌音，以翘舌音为界即可
                    sheng, yun = each[:2], each[2:]
                else:
                    # 由于拼音合法，剩下的就是普通的一个字母的声母和韵母了
                    sheng, yun = each[0], each[1:]
                if sheng:
                    # 不为零声母，则需要考虑韵母按键
                    if len(sheng) == 2:
                        # zh ch sh，就要从双拼方案里找了
                        code = self.find_key(sheng)
                    else:
                        # 声母的按键就是声母本身
                        code = sheng
                    # 如果声母是 jqxy，韵母是 ü，此处它应该使用 u 键
                    if sheng in 'jqxy' and yun == 'ü':
                        yun = 'u'
                    # 还要加上韵母按键
                    code += self.find_key(yun)
                else:
                    # 零声母
                    code = self.find_key('_' + yun)
                each_result += code
            result.append(each_result)
        return result

    def draw_keys(self):
        """给键盘绘制对应的拼音"""
        # 记录每个 Label 上拼音的位置
        x = 35
        positions = {}
        # 推算 qwertyuiop 的位置
        for char in 'qwertyuiop':
            positions[char] = [x, 60]
            x += 74
        x = 65
        for char in 'asdfghjkl;':
            positions[char] = [x, 134]
            x += 74
        x = 110
        for char in 'zxcvbnm':
            positions[char] = [x, 208]
            x += 74
        # 删除以前绘制的
        for label in keylabels:
            label.place_forget()
        keylabels.clear()
        zerol['text'] = '零声母情况：\n'
        for pin, key in self.json.items():
            # 必须加上这一条判断，因为里面还有零声母（需要单独考虑）
            # 非零声母的韵母和 zh ch sh 都可以在这里找到对应键位
            if key in positions:
                x, y = positions[key]
                label = Label(keymapf, text=pin, background='#333', foreground='#fff', font=('华文细黑', 12, NORMAL))
                label.place(x=x, y=y)
                keylabels.append(label)
                # 得轮到下一个韵母使用这个键了；就算没有“下一个”也无妨
                positions[key][1] += 20
            else:
                # 接下来就要考虑零声母了
                # json 中，零声母储存时带一个下划线
                zerol['text'] += f'{pin[1:]} -> {key}\n'

def load_plans():
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

def get_current_plan():
    """
    找到目前正在使用的双拼方案
    :return: Plan
    """
    return [plan for plan in plans if plan.name == planv.get()][0]

def gfont(fontsize):
    """
    给定字体大小，获取对应的微软雅黑字体
    :param fontsize: 字体大小
    :return: 字体
    """
    return ('微软雅黑', fontsize, NORMAL)

def find_key():
    """根据拼音寻找按键"""
    # 允许用户使用 v 代替 ü
    pin = find1e.get().replace('v', 'ü')
    result = get_current_plan().find_key(pin)
    if result:
        # 找得到
        msb.showinfo('结果', f'{pin} 对应的按键是 {result}')
    else:
        # 找不到
        msb.showerror('错误', f'仅支持 zh、ch、sh 和所有韵母，不支持 {repr(pin)}。')

def find_pins():
    """
    根据按键寻找拼音
    """
    # 已经知道按键，就要根据它来寻找韵母了
    key = find2e.get().lower()
    if len(key) != 1:
        return msb.showerror('错误', '仅支持单个按键。')
    results = get_current_plan().find_pins(key)
    if results:
        msb.showinfo('结果', f'按键 {key} 对应的拼音有 {results}。')
    else:
        # 找不到的情况说明输入的不是正确的按键
        msb.showerror('错误', '仅支持 a-z/A-Z 的字母和 ;。')

def get_code():
    chars = find3e.get()
    if not re.findall(r'^[\u4e00-\u9fa5]*$', chars):
        # 不是纯中文
        msb.showerror('错误', '请输入纯中文。')
        return
    msb.showinfo('结果', '\n'.join(get_current_plan().get_code(chars)))

def random_char(*_):
    """显示一个随机字符（练习界面的功能）"""
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
    practicel['text'] = text
    # 还要给它注上拼音
    pinyinl['text'] = get_pinyin(text)

def check_input(*_):
    """检查练习界面中用户的输入"""
    value = inputv.get()
    if len(value) == 1:
        # 用户还没输入完
        return
    correct = get_current_plan().get_code(practicel['text'])[0]
    if correct == value:
        # 用户输入正确，下一个字
        random_char()
    # 无论用户输入对不对，都应该清空
    inputv.set('')

def set_theme(*_):
    """设置界面中设置主题功能的 command"""
    try:
        window.style.theme_use(themev.get())
    except TclError:
        pass

def view_plan():
    """查看当前双拼方案功能的 command"""
    msb.showinfo('', str(get_current_plan().json).replace(',', ',\n'))

def new_plan():
    """创建新双拼方案功能的 command"""
    def adds(master, bootstyle, texts):
        """
        增加若干个 Label 和相对应的 Entry
        :param master: Labelframe
        :param bootstyle: str，内容为 bootstyle
        :param texts: str
        """
        texts = texts.split()
        for i, text in enumerate(texts):
            label = Label(master, text=text, font=gfont(12))
            label.place(x=10, y=(10 + i * 30))
            entry = Entry(master, bootstyle=bootstyle)
            entry.place(x=50, y=(10 + i * 30))
            widgets.append((label, entry))
    def create():
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
        path = fd.asksaveasfilename(title='保存方案', filetypes=(('JSON', '*.json'),), initialdir='plans',
                                    defaultextension='.json', parent=top)
        if path:
            # 因为含有“ü”，所以需要特别指出 utf-8，不然“ü”会被读取为“眉”
            with open(path, 'w', encoding='utf-8') as f:
                # ensure_ascii 需要关闭，以免 ü 被替换为 ASCII 码
                json.dump(data, f, indent=4, ensure_ascii=False)
    top = Toplevel('新方案', size=(520, 900), resizable=(False, False))
    namel = Label(top, text='名称：', font=gfont(12))
    namel.place(x=10, y=10)
    namee = Entry(top, bootstyle=SECONDARY)
    namee.place(x=60, y=10)
    # 把用到的 Label 和 Entry 收集起来，方便读取它并保存至 JSON
    widgets = []
    # zh ch sh
    shenglf = Labelframe(top, text='zh ch sh', width=240, height=130)
    adds(shenglf, PRIMARY, 'zh ch sh')
    shenglf.place(x=10, y=50)
    # 韵母
    yun1lf = Labelframe(top, text='韵母', width=240, height=850)
    adds(yun1lf, WARNING, 'a o e i u ü ai ei ui ao ou iu ie üe an en in un ün ang eng ing ong ia ua uo uai')
    yun1lf.place(x=270, y=10)
    # 韵母(2)
    yun2lf = Labelframe(top, text='韵母', width=240, height=250)
    adds(yun2lf, WARNING, 'iao ian uan üan iang uang iong')
    yun2lf.place(x=10, y=190)
    # 零声母
    zerolf = Labelframe(top, text='零声母', width=240, height=400)
    adds(zerolf, DANGER, '_a _o _e _ai _ei _ao _ou _er _an _en _ang _eng')
    zerolf.place(x=10, y=450)
    # 几个按钮
    createb = Button(top, text='创建', command=create, bootstyle=SUCCESS)
    createb.place(x=10, y=860)
    cancelb = Button(top, text='取消', command=top.destroy, bootstyle=SECONDARY)
    cancelb.place(x=68, y=860)
    top.mainloop()

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

# Tkinter 是个奇葩，东西用完还得存着
trashbin = {}
window = Window('DoublePinyin 双拼练习器', size=(1000, 760), resizable=(False, False))

switchf = Frame(window, width=1000, height=50, bootstyle=SECONDARY)
keymapb = Button(switchf, text='键位图', bootstyle=INFO, command=switch_to(0))
keymapb.place(x=20, y=10)
practiceb = Button(switchf, text='练习', bootstyle=SUCCESS, command=switch_to(1))
practiceb.place(x=90, y=10)
settingsb = Button(switchf, text='设置', bootstyle=DARK, command=switch_to(2))
settingsb.place(x=150, y=10)
switchf.place(x=0, y=0)

keymapf = Frame(window, width=1000, height=700)
# 要先绘制键盘，再给按键写上对应的拼音
# 很不理解为什么网上很多人给出的解法是使用 ImageTk.PhotoImage(Image.open(...))
trashbin['keyboard'] = PhotoImage(file='keyboard.png')
keyboardl = Label(keymapf, image=trashbin['keyboard'])
keyboardl.place(x=0, y=50)
# 这些代码必须写在关于绘制功能前

# 键盘上显示的韵母都使用 Label
keylabels = []
# 专门显示零声母的解决方案
zerol = Label(keymapf, font=gfont(16))
zerol.place(x=10, y=320)
# 由于下拉选择也需要用到表示双拼方案的 StringVar，下拉选择只能写在最后
planl = Label(keymapf, text='请选择双拼方案：', font=gfont(16))
planl.place(x=10, y=0)
# 使用 StringVar 记录菜单的选项
planv = StringVar()
# 'write' 表示当 Var 被修改时调用的函数，lambda 内容为找到对应的双拼方案并绘制键位图
# 这里的 lambda 函数不能直接使用 get_now_plan().draw_keys
# 因为这种方式每次的 get_now_plan() 其实并没有被执行
planv.trace_add('write', lambda *_: get_current_plan().draw_keys())
planv.set('小鹤双拼')
# 下拉菜单（让下拉菜单永远“认准”这个 StringVar，它的数据会和 StringVar“绑定”）
plano = OptionMenu(keymapf, planv, None, *plans, bootstyle=INFO)
plano.place(x=200, y=0)

# 拼音 -> 对应按键
find1l = Label(keymapf, text='寻找拼音对应的按键：\n（零声母请在韵母前加下划线）', font=gfont(14), bootstyle=WARNING)
find1l.place(x=140, y=300)
find1e = Entry(keymapf, bootstyle=WARNING)
find1e.place(x=330, y=300)
find1b = Button(keymapf, text='寻找', command=find_key, bootstyle=WARNING)
find1b.place(x=500, y=300)

# 按键 -> 对应拼音
find2l = Label(keymapf, text='寻找按键对应的拼音：\n（仅支持一个按键）', font=gfont(14), bootstyle=SUCCESS)
find2l.place(x=140, y=400)
find2e = Entry(keymapf, bootstyle=SUCCESS)
find2e.place(x=330, y=400)
find2b = Button(keymapf, text='寻找', command=find_pins, bootstyle=SUCCESS)
find2b.place(x=500, y=400)

# 汉字 -> 对应按键
find3l = Label(keymapf, text='寻找汉字对应的按键：\n（按键可能不唯一）', font=gfont(14), bootstyle=INFO)
find3l.place(x=140, y=500)
find3e = Entry(keymapf, bootstyle=INFO)
find3e.place(x=330, y=500)
find3b = Button(keymapf, text='寻找', command=get_code, bootstyle=INFO)
find3b.place(x=500, y=500)

# 练习界面
practicef = Frame(window, width=1000, height=700)
# 创建一个用于显示拼音的 Label
pinyinl = Label(practicef, font=('华文细黑', 20, NORMAL))
pinyinl.place(x=250, y=70)
# 将汉字显示在 Label 里
practicel = Label(practicef, font=('楷体', 120, NORMAL))
practicel.place(x=200, y=100)
# 还是使用变量记录数据
practicev = StringVar()
practicev.trace_add('write', random_char)
practicev.set('模式 1（基于 Unicode，生僻字较多）')
# 给出选择随机模式 1（可离线）和随机模式 2（不可离线）的下拉菜单
practiceo = OptionMenu(practicef, practicev, None, '模式 1（基于 Unicode，生僻字较多）',
                       '模式 2（基于 Web API，生僻字较少）', bootstyle=DANGER)
practiceo.place(x=10, y=10)
# 提供输入框，并且给它绑定 StringVar，当字正确时自动下一个字
inputv = StringVar()
inputv.trace_add('write', check_input)
inpute = Entry(practicef, textvariable=inputv, bootstyle=INFO)
inpute.place(x=200, y=300)

settingsf = Frame(window, width=1000, height=700)

themelf = Labelframe(settingsf, text='主题', width=980, height=150)
# 用 StringVar 记录主题选择界面
themev = StringVar(None, 'litera')
# 当主题被“写入”就运行 set_theme
themev.trace_add('write', set_theme)
themeo = OptionMenu(themelf, themev, None, *window.style.theme_names())
themeo.place(x=10, y=10)
themel = Label(themelf, text='主题效果')
themel.place(x=10, y=50)
theme1b = Button(themelf, text=PRIMARY, bootstyle=PRIMARY)
theme1b.place(x=10, y=80)
theme2b = Button(themelf, text=SECONDARY, bootstyle=SECONDARY)
theme2b.place(x=89, y=80)
theme3b = Button(themelf, text=SUCCESS, bootstyle=SUCCESS)
theme3b.place(x=183, y=80)
theme4b = Button(themelf, text=INFO, bootstyle=INFO)
theme4b.place(x=261, y=80)
theme5b = Button(themelf, text=WARNING, bootstyle=WARNING)
theme5b.place(x=317, y=80)
theme6b = Button(themelf, text=DANGER, bootstyle=DANGER)
theme6b.place(x=397, y=80)
theme7b = Button(themelf, text=LIGHT, bootstyle=LIGHT)
theme7b.place(x=473, y=80)
theme8b = Button(themelf, text=DARK, bootstyle=DARK)
theme8b.place(x=534, y=80)
themelf.place(x=10, y=0)

planslf = Labelframe(settingsf, text='双拼方案', width=980, height=70)
reloadb = Button(planslf, text='重新加载', command=lambda: (load_plans(), plano.set_menu(None, *plans)), bootstyle=PRIMARY)
reloadb.place(x=10, y=10)
viewb = Button(planslf, text='查看当前方案', command=view_plan, bootstyle=SUCCESS)
viewb.place(x=92, y=10)
newb = Button(planslf, text='新方案', command=new_plan, bootstyle=INFO)
newb.place(x=198, y=10)
planslf.place(x=10, y=160)

attrlf = Labelframe(settingsf, text='窗口属性', width=980, height=70)
alphal = Label(attrlf, text='透明度：100%')
alphal.place(x=10, y=10)
alpha1b = Button(attrlf, text='↑', state=DISABLED, command=alpha_up, bootstyle=DANGER)
alpha1b.place(x=120, y=10)
alpha2b = Button(attrlf, text='↓', command=alpha_down, bootstyle=DANGER)
alpha2b.place(x=160, y=10)
attrlf.place(x=10, y=240)

funfactlf = Labelframe(settingsf, text='你知道吗（施工中，请等待下一个版本）', width=980, height=70)
funfactlf.place(x=10, y=320)

# versionlf = Labelframe(settingsf, text='版本相关', width=980, height=70)
# checkupdateb = Button(versionlf, text='检查更新', bootstyle=INFO)
# checkupdateb.place(x=10, y=10)
# versionlf.place(x=10, y=...)
frames = [keymapf, practicef, settingsf]
switch_to(0)()

window.mainloop()
