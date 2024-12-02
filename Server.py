import sqlite3
from xmlrpc.server import SimpleXMLRPCServer
import random

PORT = 8888
DB_NAME = "users.db"  # 資料庫名稱

# 創建資料庫連接和表格
def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 創建 users 表格來存儲玩家的資料
    c.execute('''CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            status TEXT
        )''')

    # 創建 games 表格來存儲遊戲狀態
    c.execute('''CREATE TABLE IF NOT EXISTS games (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1 TEXT,
            player2 TEXT,
            current_player TEXT,
            first   TEXT,
            game_status TEXT
        )''')

    # 創建 board 表格來存儲棋盤狀態
    c.execute('''CREATE TABLE IF NOT EXISTS board (
            game_id INTEGER,
            board TEXT
        )''')

    conn.commit()
    conn.close()

# 檢查資料庫的board與client資料庫是否一致
def check_board_data(game_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT board FROM board WHERE game_id = ?", (game_id,))
        row = c.fetchone()
        if row:
            print(row[0])
            return row[0]
        return None

# 註冊功能：將使用者名稱和密碼儲存至資料庫
def register(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ?', (username,))
        if c.fetchone():
            return "註冊失敗：使用者名稱已存在。"
        c.execute('INSERT INTO users (username, password, status) VALUES (?, ?, "offline")', (username, password))
        conn.commit()
    return "註冊成功！"

# 登入功能：從資料庫檢查使用者名稱和密碼
def login(username, password):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = c.fetchone()
        if user:
            c.execute('UPDATE users SET status = "online" WHERE username = ?', (username,))
            conn.commit()
            return "登入成功！"
        return "登入失敗：帳號或密碼錯誤。"

# 伺服器啟動時重置狀態
def reset_user_status():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'offline' WHERE status != 'offline'")
        conn.commit()

# 開始遊戲：初始化遊戲狀態
def start_game(player1):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM games WHERE player1 = ? OR player2 = ?", (player1, player1))
        game = c.fetchone()
        if game:
            return f"{game[0]}遊戲已經開始，{game[4]} 為黑棋 , 目前為{game[3]}下棋"  # 獲取當前玩家

        # 將當前玩家狀態設為 waiting
        c.execute("UPDATE users SET status = 'waiting' WHERE username = ?", (player1,))
        conn.commit()

        # 查找其他 waiting 玩家
        c.execute('SELECT * FROM users WHERE status = "waiting" AND username != ?', (player1,))
        waiting_player = c.fetchone()
        if waiting_player:
            player2 = waiting_player[0]
            current_player = random.choice([player1, player2])

            # 更新兩個玩家的狀態為 ongoing
            c.execute("UPDATE users SET status = 'ongoing' WHERE username = ?", (player1,))
            c.execute("UPDATE users SET status = 'ongoing' WHERE username = ?", (player2,))

            # 初始化遊戲
            c.execute('INSERT INTO games (player1, player2, current_player,first, game_status) VALUES (?, ?, ?, ? , ?)',
                        (player1, player2, current_player,current_player, "ongoing"))
            conn.commit()
            game_id = c.lastrowid  # Get the game ID of the new game
            c.execute("INSERT INTO board (game_id, board) VALUES (?, ?)", (game_id, "000000000000000000000000000OX000000XO000000000000000000000000000"))
            conn.commit()

            return f"{game[0]}遊戲開始！{current_player} 為黑棋"
        else:
            return "等待中..."

# 更新玩家輪到執行遊戲
def make_move(player, game_id, row, col):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM games WHERE game_id = ? AND game_status = "ongoing"', (game_id,))
        game = c.fetchone()
        if not game:
            return "遊戲無效或已結束。"

        # 檢查當前玩家是否是輪到行動的玩家
        current_player = game[3]
        if current_player != player:
            return f"不是你的回合！{player}"

        c.execute('SELECT board FROM board WHERE game_id = ?', (game_id,))
        board = c.fetchone()

        if not board:
            return "棋盤未初始化。"

        # 將棋盤字符串轉換為列表以便修改
        board_data = list(board[0])

        # 檢查位置是否已被佔用
        if board_data[row * 8 + col] != '0':  # Check if the cell is empty
            return "這個位置已經被佔用。"
        if current_player == game[4]:
            flag = 0 #O的玩家
        else:
            flag = 1 #X的玩家
        accept = 0
        # 更新棋盤狀態
        if flag == 1:
            for x,y in [[0,1],[1,1],[1,0],[1,-1],[0,-1],[-1,-1],[-1,0],[-1,1]]:
                if (row + x) >= 0 and (row + x) < 8 and (col + y) >= 0 and (col + y) < 8:
                    if board_data[(row + x) * 8 + (col + y)] == 'O':
                        tempx = row
                        tempy = col
                        while True:
                            row += x
                            col += y
                            if row < 0 or row >= 8 or col < 0 or col >=8:
                                row = tempx
                                col = tempy
                                break
                            if board_data[row * 8 + col] == '0':
                                row = tempx
                                col = tempy
                                break
                            if board_data[row * 8 + col] == 'X':
                                while True:
                                    row -= x
                                    col -= y
                                    if board_data[row * 8 + col] != '0':
                                        board_data[row*8 + col] = 'X'
                                    elif row <= tempx and col <= tempy:
                                        break
                                    else:
                                        break
                                accept = 1
                                break
        if flag == 0:
            for x,y in [[0,1],[1,1],[1,0],[1,-1],[0,-1],[-1,-1],[-1,0],[-1,1]]:
                if (row + x) >= 0 and (row + x) < 8 and (col + y) >= 0 and (col + y) < 8:
                    if board_data[(row + x) * 8 + (col + y)] == 'X':
                        tempx = row
                        tempy = col
                        while True:
                            row += x
                            col += y
                            if row < 0 or row >= 8 or col < 0 or col >=8:
                                row = tempx
                                col = tempy
                                break
                            if board_data[row * 8 + col] == '0':
                                row = tempx
                                col = tempy
                                break
                            if board_data[row * 8 + col] == 'O':
                                while True:
                                    row -= x
                                    col -= y
                                    if board_data[row * 8 + col] != '0':
                                        board_data[row*8 + col] = 'O'
                                    elif row <= tempx and col <= tempy:
                                        break
                                    else:
                                        break
                                accept = 1
                                break
        if accept == 0:
            return "不能下這裡"
        else:
            board_data[row * 8 + col] = 'O' if flag == 0 else 'X'

        # 把修改後的列表轉換回字符串
        updated_board = ''.join(board_data)

        # 更新棋盤
        c.execute('UPDATE board SET board = ? WHERE game_id = ?', (updated_board, game_id))

        # 設定下個玩家
        next_player = game[2] if current_player == game[1] else game[1]
        c.execute('UPDATE games SET current_player = ? WHERE game_id = ?', (next_player, game_id))

        conn.commit()
        return f"成功執行步驟。{current_player}"


# 获取棋盘状态
def get_board_state(game_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT board FROM board WHERE game_id = ?', (game_id,))
        board = c.fetchone()
        if board:
            board_data = list(board[0])
            return [board_data[i:i+8] for i in range(0, 64, 8)] #轉成[' '*64]
        else:
            raise Exception(f"Game ID {game_id} not found.")

# 初始化資料庫
create_tables()
reset_user_status()

# Start the XML-RPC server
with SimpleXMLRPCServer(("localhost", PORT), allow_none=True) as server:
    server.register_function(register)
    server.register_function(login)
    server.register_function(start_game)
    server.register_function(make_move)
    server.register_function(get_board_state)
    server.register_function(check_board_data)
    print(f"伺服器正在 {PORT} 埠運行...")
    server.serve_forever()
