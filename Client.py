import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
import xmlrpc.client
import time

PORT = 8888
server = '127.0.0.1'
current_user = None
game_id = None  # 用來儲存當前遊戲 ID

root = tk.Tk()
colorarr = ["gray", "white", "black"]

# 修正board為二維列表
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

def register_gui():
    global server
    name = simpledialog.askstring("註冊", "輸入使用者名稱：")
    password = simpledialog.askstring("註冊", "輸入密碼：")
    result = server.register(name, password)
    messagebox.showinfo("註冊", result)

def login_gui():
    global server, current_user
    name = simpledialog.askstring("登入", "輸入使用者名稱：")
    password = simpledialog.askstring("登入", "輸入密碼：")
    result = server.login(name, password)
    if "成功" in result:
        current_user = name
        a.set("玩家:"+current_user)
    messagebox.showinfo("登入", result+":"+current_user)

def start_game_gui():
    global current_user
    if not current_user:
        messagebox.showinfo("提示", "請先登入！")
        return
    
    # 開始遊戲請求
    result = server.start_game(current_user)
    if "開始" in result:
        display_board()
        messagebox.showinfo("遊戲狀態", result)
        return
    elif "等待" in result:
        messagebox.showinfo("提示", "等待對手加入遊戲...")
        # 輪詢機制
        for _ in range(10):  # 每秒檢查一次，最多檢查 10 次
            time.sleep(1)
            result = server.start_game(current_user)
            if "開始" in result:
                display_board()
                messagebox.showinfo("遊戲狀態", result)
                return
        messagebox.showinfo("提示", "仍在等待對手...")

def display_board():
    # 設定畫布大小
    global board
    canvas_width = 400
    canvas_height = 400
    cell_size = 50  # 每個格子的大小

    root = tk.Toplevel()
    root.title("8x8 Chessboard")

    # 創建一個 8x8 按鈕格子
    buttons = [[None for _ in range(8)] for _ in range(8)]  # 用來儲存按鈕的陣列

    # 畫出棋盤格子
    while(True):
        for row in range(8):  # 修正循環範圍，應該從0到7
            for col in range(8):  # 修正循環範圍，應該從0到7
                # 定義每個按鈕的顯示區域
                x1 = col * cell_size
                y1 = row * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size
                button = tk.Button(root, width=6, height=3, command=lambda r=row, c=col: on_button_click(r, c))
                # 根據 board 的資料設定按鈕顏色
                if board[row][col] == '0':
                    button.configure(bg='gray')
                elif board[row][col] == 'O':
                    button.configure(bg='white')
                else:
                    button.configure(bg='black')

                # 定義按鈕點擊事件
                def on_button_click(r=row, c=col):
                    make_move_gui(r, c)
                    

                # 創建按鈕並配置顏色
                button.grid(row=row,column=col,padx=2,pady=2)
                buttons[row][col] = button
                # 格狀
                buttons[row][col].grid(row=row, column=col)

def make_move_gui(row, col):
    global current_user, game_id, board
    if not current_user:
        messagebox.showinfo("提示", "請先登入！")
        return
    game_id = server.search_game_ID(current_user)
    print(type(game_id))
    print(row)
    result = server.make_move(current_user, game_id, row, col)
    messagebox.showinfo("遊戲狀態", result)

    # 更新棋盤
    if "成功" in result:
        # 更新 board 列表的狀態
        if board[row][col] == '0':  # 確保位置為空
            if current_user == "Player1":
                board[row][col] = 'X'  # 或者 'O' 取決於哪位玩家的回合
            else:
                board[row][col] = 'O'
        #display_board()  # 更新棋盤顯示

def main_gui():
    global server
    if len(sys.argv) < 1:
        print("使用方法: python client.py serverIP")
        sys.exit(1)

    server_ip = server
    server = xmlrpc.client.ServerProxy(f"http://{server_ip}:{PORT}")

    root.title('黑白棋')
    root.geometry('380x400')
    root.resizable(False, False)
    txt = tk.Label(root, textvariable=a, font=('Arial', 20), anchor='nw', width=5, height=2, pady=5)
    txt.pack()
    tk.Button(root, text="註冊", command=register_gui).pack(pady=5)
    tk.Button(root, text="登入", command=login_gui).pack(pady=5)
    tk.Button(root, text="開始遊戲", command=start_game_gui).pack(pady=5)
    tk.Button(root, text="退出", command=root.quit).pack(pady=5)
    root.mainloop()

if __name__ == "__main__":
    main_gui()
