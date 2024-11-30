import sqlite3
from xmlrpc.server import SimpleXMLRPCServer
import random

PORT = 8888
DB_NAME = "users.db"  # 資料庫名稱

# 創建資料庫連接和表格
conn = sqlite3.connect(DB_NAME)
c = conn.cursor()

# 創建 users 表格來存儲玩家的資料
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        status   TEXT
    )
''')

# 創建 games 表格來存儲遊戲狀態
c.execute('''
    CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1 TEXT,
        player2 TEXT,
        current_player TEXT,
        game_status TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS board (
        game_id INTEGER ,
        board TEXT
    )
''')
conn.commit()
conn.close()

# 註冊功能：將使用者名稱和密碼儲存至資料庫
def register(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 檢查使用者名稱是否已經存在
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    if c.fetchone():
        conn.close()
        return "註冊失敗：使用者名稱已存在。"

    # 插入新的使用者資料
    c.execute('INSERT INTO users (username, password,status) VALUES (?, ?,"offline")', (username, password))
    conn.commit()
    conn.close()
    return "註冊成功！"

# 登入功能：從資料庫檢查使用者名稱和密碼
def login(username, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = c.fetchone()
    if user:
        c.execute('UPDATE users SET status = "online" where username = ?',(username,))
        conn.close()
        print('成功')
        return "登入成功！"
    else:
        conn.close()
        return "登入失敗：帳號或密碼錯誤。"
    
# 伺服器啟動時重置狀態
def reset_user_status():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET status = 'offline' WHERE status != 'offline'")
    
    conn.commit()
    conn.close()

# 開始遊戲：初始化遊戲狀態
def start_game(player1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # 檢查當前玩家的狀態
        c.execute("SELECT player1,player2 FROM games where player1 == ?",(player1,))
        if c.fetchone():
            return "遊戲已經開始"
        c.execute("SELECT status FROM users WHERE username = ?", (player1,))
        status = c.fetchone()
        if status and status[0] == "ongoing":
            c.execute("SELECT * FROM games WHERE player1 = ? OR player2 = ?", (player1, player1))
            game = c.fetchone()
            if game:
                return f"遊戲開始，{game[3]} 為黑棋"  # 獲取當前玩家
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
            c.execute("UPDATE users SET status = 'ongoing' WHERE username == ?", (player1,))
            c.execute("UPDATE users SET status = 'ongoing' WHERE username == ?", (player2,))
            # 初始化遊戲
            c.execute('INSERT INTO games (player1, player2, current_player, game_status) VALUES (?, ?, ?, ?)',
                      (player1, player2, current_player, "ongoing"))
            conn.commit()
            
            return f"遊戲開始！{current_player} 為黑棋"
        else:
            # 沒有找到對手
            return "等待中..."
    finally:
        conn.close()

def search_game_ID(player1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT game_id FROM games WHERE player1 == ? OR player2 == ?", (player1, player1))
    game = c.fetchone()
    if game:
        c.execute("INSERT INTO board (game_id,board) VALUES (?,?)",(game[0],"000000000000000000000000000OX000000XO000000000000000000000000000"))
        conn.commit()
        conn.close()
        return f'{game[0]}'  # 獲取當前玩家
    else:
        print("WTFFFFFFFFFFFFFF")
        conn.commit()
        conn.close()
        return "無法找到對手"  # debug
    
# 更新玩家輪到執行遊戲
def make_move(player, game_id, row, col):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        # 取得遊戲資料
        c.execute('SELECT * FROM games WHERE game_id = ? AND game_status = "ongoing"', (game_id,))
        game = c.fetchone()
        
        # 如果遊戲資料不存在，返回錯誤
        if not game:
            return "遊戲無效或已結束。"

        # 檢查當前玩家是否是輪到行動的玩家
        current_player = game[3]
        if current_player != player:
            return "不是你的回合！"

        # 獲取棋盤資料
        c.execute('SELECT board FROM board WHERE game_id = ?', (game_id,))
        board = c.fetchone()
        
        # 如果棋盤資料不存在，返回錯誤
        if not board:
            return "棋盤未初始化。"

        # 將棋盤字符串轉換為列表
        board_data = list(board[0])  # 假設 board 是以字符串儲存，例如 '00000000'
        
        # 檢查該位置是否已被佔用
        if board_data[row][col] != '0':  # 0表示空位
            return "該位置已被佔用。"

        # 更新棋盤資料
        board_data[row][col] = 'X' if current_player == game[1] else 'O'

        # 將棋盤列表轉回字符串並保存
        c.execute('UPDATE board SET board = ? WHERE game_id = ?', (''.join(board_data), game_id))

        # 換輪到下一位玩家
        next_player = game[2] if current_player == game[1] else game[1]
        c.execute('UPDATE games SET current_player = ? WHERE game_id = ?', (next_player, game_id))

        conn.commit()
        return f"成功執行步驟。{}"
    finally:
        conn.close()



# 初始化資料庫
reset_user_status()
with SimpleXMLRPCServer(("localhost", PORT), allow_none=True) as server:
    server.register_function(register)
    server.register_function(login)
    server.register_function(start_game)
    server.register_function(make_move)
    server.register_function(search_game_ID)
    print(f"伺服器正在 {PORT} 埠運行...")
    server.serve_forever()
