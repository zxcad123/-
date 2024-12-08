import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
import xmlrpc.client
import threading
import time
import socket
lock = threading.Lock()

PORT = 8888
server = '127.0.0.1'
current_user = None
game_id = None  # 用來儲存當前遊戲 ID
FirOrSec = "player1"
root = tk.Tk()
flag=0
kill = 0
colorarr = ["gray", "white", "black"]
buttons = [['0']*8 for _ in range(8)]
board = [['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', 'O', 'X', '0', '0', '0'],
         ['0', '0', '0', 'X', 'O', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0']]

a = tk.StringVar()
a.set("未登入")

def ask_account(prompt):
    def on_ok():
        nonlocal password,account
        account  = entry1.get()
        password = entry2.get()
        dialog.destroy()

    account = None
    password = None
    dialog = tk.Toplevel()
    dialog.title(prompt)
    dialog.geometry("300x200")
    dialog.grab_set()  # 模态窗口
    tk.Label(dialog, text="輸入帳號").pack(pady=10)
    entry1 = tk.Entry(dialog)  # 输入框，隐藏字符
    entry1.pack(pady=2)
    entry1.focus_set()  # 自动聚焦输入框
    tk.Label(dialog, text="輸入密碼").pack(pady=10)
    entry2 = tk.Entry(dialog, show='*')  # 输入框，隐藏字符
    entry2.pack(pady=2)
    entry2.focus_set()  # 自动聚焦输入框
    tk.Button(dialog, text="確定", command=on_ok).pack(pady=10)

    dialog.wait_window()  # 等待窗口关闭
    return (account,password,)
def register_gui():
    global server
    name,password = ask_account("註冊")
    try:
        result = server.register(name, password)
        messagebox.showinfo("註冊", result)
    except Exception as e:
        messagebox.showerror("錯誤", f"註冊失敗: {e}")

def login_gui():
    global server, current_user
    #logout 增加功能
    name,password = ask_account("登入")
    try:
        result = server.login(name, password)
        if "成功" in result:
            if current_user:
                server.logout(current_user)
            current_user = name
            a.set("玩家:" + current_user)
            messagebox.showinfo("登入", result + ":" + current_user)
        if "線上" in result:
            messagebox.showerror("錯誤", "此帳號已被登入")
        if "失敗" in result:
            messagebox.showerror("錯誤", result)
    except Exception as e:
        messagebox.showerror("錯誤", f"登入失敗: {e}")

# 轮询棋盘更新
def new_window_break():
    global current_user,game_id,board
    result = server.opponent_win(current_user,game_id)
    game_id = 0
    #server.shutdown_game(current_user)
    print(result)
    thread1.do_run = False
    board = [['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', 'O', 'X', '0', '0', '0'],
         ['0', '0', '0', 'X', 'O', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0'],
         ['0', '0', '0', '0', '0', '0', '0', '0']]
    new_window.destroy()

def poll_board_updates(game_id, new_window):
    global board, kill ,current_user,thread1
    thread1 = threading.current_thread()
    while getattr(thread1, "do_run", True):
        try:
            new_window.protocol("WM_DELETE_WINDOW",new_window_break)
            # 使用锁来管理并发
            with lock:
                print(f"Polling game ID: {game_id}")
                board_state = server.check_board_data(game_id)

                if board_state:
                    for i in range(8):
                        for j in range(8):
                            board[i][j] = board_state[i * 8 + j]

            # 刷新 UI
            root.after(0, refresh_board)

            # 检查是否需要终止轮询
            if kill == 1:
                new_window.destroy()
                kill = 0
                break

            # 适当延迟，避免过高的轮询频率
            time.sleep(0.3)
        except Exception as e:
            print(f"Polling failed: {e}")
            # 记录错误并决定是否继续
            if kill == 1:
                new_window.destroy()
                kill = 0
                break
            time.sleep(1)
            poll_board_updates(game_id, new_window)


# 刷新棋盘显示
def refresh_board():
    global board, buttons,current_user,game_id
    curr = server.get_curr_user(current_user,game_id)
    for row in range(8):
        for col in range(8):
            # Updating the button colors based on the current board state
            color = 'gray' if board[row][col] == '0' else 'white' if board[row][col] == 'O' else 'black' if board[row][col] == 'X' else 'red' if curr else 'gray'
            buttons[row][col].configure(bg=color)
    root.update()  # Refreshing the window display

def start_game_gui():
    global current_user, game_id,FirOrSec,new_window
    if not current_user:
        messagebox.showinfo("提示", "請先登入！")
        return
    print("偵錯點1")
    try:
        lock.acquire()
        result = server.start_game(current_user)  # Request to start the game
        lock.release()
        if current_user == result[2]:
            FirOrSec = "1"
        else:
            FirOrSec = "2"
        if "開始" in result:
            print("偵錯點2")
            game_id = result[0]
            # Starting a new window to display the game board
            new_window = tk.Toplevel()
            new_window.title("8x8 Chessboard")
            # Start the board polling in a separate thread
            thread1=threading.Thread(target=poll_board_updates, args=(game_id,new_window),daemon=True)
            thread1.start()
            display_board(new_window)  # Display the board in the new window
            messagebox.showinfo("遊戲狀態", result)
        elif "等待" in result:
            #messagebox.showinfo("提示", "等待對手加入遊戲...")
            time.sleep(2)
            start_game_gui()
    except Exception as e:
        messagebox.showerror("錯誤", f"遊戲開始失敗: {e}")

def root_break():
    global root,current_user,game_id
    print(current_user)
    print(game_id)
    if current_user:
        server.logout(current_user)
        if game_id:
            server.shutdown_game(current_user)
            new_window_break()
            game_id = 0
    current_user = None
    sys.exit(0)



def display_board(new_window):
    global buttons, board,FirOrSec
    board_frame = tk.Frame(new_window)
    board_frame.grid(row=0, column=0)
    user_info_frame = tk.Frame(new_window)
    user_info_frame.grid(row=0, column=1, padx=3)

    buttons = [[None for _ in range(8)] for _ in range(8)]

    # 从服务器获取当前棋盘状态
    try:
        lock.acquire()
        result = server.check_board_data(game_id)
        lock.release()
        if result:
            # 更新 board 数据
            board = [list(result[i:i+8]) for i in range(0, len(result), 8)]
    except Exception as e:
        print(f"获取棋盘数据失败: {e}")
        #messagebox.showerror("錯誤", "重新取得棋盤資料")
    name_label = tk.Label(user_info_frame, text="玩家"+FirOrSec+": " + current_user, width=10, height=3)
    name_label.grid(row=0, column=1)

    def on_button_click(row, col):
        make_move_gui(row, col,new_window)

    # 畫出棋盤格子
    for row in range(8):  
        for col in range(8):  
            button = tk.Button(board_frame, width=6, height=2, command=lambda r=row, c=col: on_button_click(r, c))
            button.grid(row=row, column=col, padx=2, pady=2)
            buttons[row][col] = button
    refresh_board()  # 更新棋盘显示

def kill_board(new_window):
    new_window.destroy()

def make_move_gui(row, col,new_window):
    global current_user, game_id, board,kill
    if not current_user:
        messagebox.showinfo("提示", "請先登入！")
        return
    try:
        with lock:
            result = server.make_move(current_user, game_id, row, col)
            #messagebox.showinfo("遊戲狀態", result)
            kill = server.kill_game(game_id)
        # 更新棋盘
        if "成功" in result:
            refresh_board()  # 更新棋盘显示
        elif "離開" in result:
            new_window_break()
            messagebox.showinfo("遊戲狀態", result)
            server.shutdown(current_user)
            game_id = 0
        elif "結束" not in result:
            messagebox.showinfo("遊戲狀態", result)
        if "結束" in result:
            black_num = 0
            white_num = 0
            refresh_board()
            for i in range(8):
                for j in range(8):
                    if board[i][j] == "X":
                        black_num += 1
                    elif board[i][j] == "O":
                        white_num += 1
            if black_num > white_num:
                messagebox.showinfo("遊戲結果", "黑棋勝利！")
            else:
                messagebox.showinfo("遊戲結果", "白棋勝利！")
            new_window_break()
            lock.acquire()
            server.shutdown_game(current_user)
            time.sleep(1)
            lock.release()
            game_id = 0
        if kill == 1:
            new_window.destroy()
            kill = 0
    except Exception as e:
        #messagebox.showerror("錯誤", f"落子失敗: {e}")
        #make_move_gui(row,col,new_window)
        pass

def main_gui():
    global server,current_user,game_id,new_window
    if len(sys.argv) < 1:
        print("使用方法: python client.py")
        sys.exit(1)

    server_ip = server
    server = xmlrpc.client.ServerProxy(f"http://{server_ip}:{PORT}")

    root.title('黑白棋')
    root.geometry('380x400')
    root.resizable(False, False)
    txt = tk.Label(root, textvariable=a, font=('Arial', 20), anchor='nw', width=5, height=2, pady=5,padx=20)
    txt.pack()
    tk.Button(root, text="註冊", command=register_gui).pack(pady=5)
    tk.Button(root, text="登入", command=login_gui).pack(pady=5)
    tk.Button(root, text="開始遊戲", command=start_game_gui).pack(pady=5)
    tk.Button(root, text="退出", command=root.quit).pack(pady=5)
    root.protocol("WM_DELETE_WINDOW",root_break)
    root.mainloop()
            
if __name__ == "__main__":
    main_gui()