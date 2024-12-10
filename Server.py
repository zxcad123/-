import sqlite3
from xmlrpc.server import SimpleXMLRPCServer
import random
import time
import socket
PORT = 8888
DB_NAME = "users.db"  # 資料庫名稱

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('', 8888))
		
# Set socket non blocking
server.setblocking(False)
server.listen(5)
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

def logout(player):
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("UPDATE users SET status = 'offline' WHERE username = ?", (player,))
        conn.commit()
        conn.close()
    except Exception as e:
        # 捕获其他未知错误
        print(f"未知錯誤：{e}")
        return None

def check_board_data(game_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            # 查询棋盘数据

            c.execute("SELECT board FROM board WHERE game_id = ?", (game_id,))
            row = c.fetchone()
            
            if row:
                # 返回棋盘数据
                return row[0]
            
            # 未找到数据
            return None
    except sqlite3.Error as e:
        # 捕获数据库异常
        print(f"資料庫錯誤：{e}")
        return None
    except Exception as e:
        # 捕获其他未知错误
        print(f"未知錯誤：{e}")
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
            if user[2] != "offline":
                return "使用者已在線上。"
            else:
                #connection, (rip, rport) = server.accept()
                #rep = "Welcome"
                #server.send(rep.encode())
                #msg = "Accept connection on port:  from (%s, %d)" %(str(rip), rport)
                #print(msg)
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
        c.execute("SELECT * FROM games WHERE (player1 = ? OR player2 = ? )and game_status == 'ongoing'", (player1, player1))
        game = c.fetchone()
        if game:
            print(player1)
            return f"{game[0]}遊戲已經開始，{game[4]} 為白棋 , 目前為{game[3]}下棋"  # 獲取當前玩家

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
            c.execute('SELECT * from games where (player1 == ? OR player2 == ?) and game_status = "ongoing"',(player1,player2))
            game = c.fetchone()
            game_id = game[0]  # Get the game ID of the new game
            c.execute("INSERT INTO board (game_id, board) VALUES (?, ?)", (game_id, "00000000000000000000R000000OXR0000RXO000000R00000000000000000000"))
            conn.commit()

            return f"{game[0]}遊戲開始！{current_player} 為白棋"
        else:
            return "等待中..."
def valid(player, game_id, board_data):
    #print(board_data)
    num = 0
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
        game = c.fetchone()
        if not game:
            return {'accept': None, 'num': 0}  # 遊戲不存在

        if player == game[4]:  # 決定玩家標誌
            flag = 0  # O 的玩家
        else:
            flag = 1  # X 的玩家

        accept = [['0'] * 8 for _ in range(8)]  # 初始化為 8x8 棋盤

        # 遍歷棋盤
        for i in range(8):
            for j in range(8):
                if flag == 1:  # X 的玩家
                    for dx, dy in [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]:
                        x, y = i, j
                        if board_data[x * 8 + y] == 'X' or board_data[x*8+y] == 'O':  # 起始點不能是自己的棋子
                            break

                        x += dx 
                        y += dy
                        if 0 <= x < 8 and 0 <= y < 8 and board_data[x * 8 + y] == 'O':
                            # 追蹤翻轉路徑
                            while 0 <= x < 8 and 0 <= y < 8:
                                x += dx
                                y += dy
                                if x < 0 or x >= 8 or y < 0 or y >= 8 or board_data[x * 8 + y] == 'R'or board_data[x * 8 + y] == '0':
                                    break
                                if board_data[x * 8 + y] == 'X':
                                    accept[i][j] = '1'
                                    x=i
                                    y=j
                                    num += 1
                                    break

                elif flag == 0:  # O 的玩家
                    for dx, dy in [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]:
                        x, y = i, j
                        if board_data[x * 8 + y] == 'O' or board_data[x * 8 + y] == 'X':  # 起始點不能是自己的棋子
                            break

                        x += dx
                        y += dy
                        if 0 <= x < 8 and 0 <= y < 8 and board_data[x * 8 + y] == 'X':
                            # 追蹤翻轉路徑
                            while 0 <= x < 8 and 0 <= y < 8:
                                x += dx
                                y += dy
                                if x < 0 or x >= 8 or y < 0 or y >= 8 or board_data[x * 8 + y] == '0' or board_data[x * 8 + y] == 'R':
                                    break
                                if board_data[x * 8 + y] == 'O':
                                    accept[i][j] = '1'
                                    x=i
                                    y=j
                                    num += 1
                                    break
        print(num)
        return {'accept': accept, 'num': num}

                
def get_curr_user(player,game_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT current_player FROM games WHERE game_id = ?", (game_id,))
        curr_user = cur.fetchone()[0]
        print(curr_user)
        cur.close
        if player == curr_user:
            return True
        else:
            return False
def kill_game(game_id):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM games where game_id = ?", (game_id,))
        game = cur.fetchone()
        if game:
            return 0
        else:
            return 1
# 更新玩家輪到執行遊戲
def make_move(player, game_id, row, col):
    #data = server.recv(1024)
    #server.send(data.decode())
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM games WHERE game_id = ? AND game_status = player1 or game_status = player2', (game_id,))
        win = c.fetchone()
        if win:
            return f"對手離開了,{win[5]}已獲勝"
        c.execute('SELECT * FROM games WHERE game_id = ? AND game_status = "ongoing"', (game_id,))
        game = c.fetchone()
        if not game:
            return "遊戲結束。"

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
        if board_data[row * 8 + col] == 'O' or board_data[row * 8 + col] =='X':  # Check if the cell is empty
            print(board_data[row * 8 + col])
            return "這個位置已經被佔用。"
        if current_player == game[4]:
            flag = 0 #O的玩家
        else:
            flag = 1 #X的玩家
        accept = 0
        
        # 更新棋盤狀態
        if flag == 1:  # X logic for flipping opponent's pieces
            for x, y in [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]:
                if (row + x) >= 0 and (row + x) < 8 and (col + y) >= 0 and (col + y) < 8:
                    if board_data[(row + x) * 8 + (col + y)] == 'O':
                        tempx, tempy = row, col
                        while True:
                            row += x
                            col += y
                            if row < 0 or row >= 8 or col < 0 or col >= 8:
                                row, col = tempx, tempy
                                break
                            if board_data[row * 8 + col] == '0':
                                row, col = tempx, tempy
                                break
                            if board_data[row * 8 + col] == 'X':
                                while True:
                                    row -= x
                                    col -= y
                                    if board_data[row * 8 + col] != 'R':
                                        board_data[row * 8 + col] = 'X'
                                    else:
                                        break
                                accept = 1
                                break
        elif flag == 0:  # O logic for flipping opponent's pieces
            for x, y in [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]:
                if (row + x) >= 0 and (row + x) < 8 and (col + y) >= 0 and (col + y) < 8:
                    if board_data[(row + x) * 8 + (col + y)] == 'X':
                        tempx, tempy = row, col
                        while True:
                            row += x
                            col += y
                            if row < 0 or row >= 8 or col < 0 or col >= 8:
                                row, col = tempx, tempy
                                break
                            if board_data[row * 8 + col] == '0':
                                row, col = tempx, tempy
                                break
                            if board_data[row * 8 + col] == 'O':
                                while True:
                                    row -= x
                                    col -= y
                                    if board_data[row * 8 + col] != 'R':
                                        board_data[row * 8 + col] = 'O'
                                    else:
                                        break
                                accept = 1
                                break
        if accept == 0:
            return "不能下這裡"
        else:
            board_data[row * 8 + col] = 'O' if flag == 0 else 'X'

        # 設定下個玩家
        next_player = game[2] if current_player == game[1] else game[1]
        c.execute('UPDATE games SET current_player = ? WHERE game_id = ?', (next_player, game_id))
        for i in range(8):
            for j in range(8):
                if board_data[i*8+j] == 'R':
                    board_data[i*8+j] = '0'
        result= valid(next_player,game_id,board_data)
        for i in range(8):
            for j in range(8):
                if result["accept"][i][j]=='1':
                    board_data[i*8+j]='R'
        # 把修改後的列表轉換回字符串
        updated_board = ''.join(board_data)

        # 更新棋盤
        c.execute('UPDATE board SET board = ? WHERE game_id = ?', (updated_board, game_id))
        conn.commit()
        c.close()
        time.sleep(0.1)
        if result["num"] == 0:
            return "遊戲結束"
        return f"成功執行步驟。{current_player}"

def opponent_win(player,game_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('SELECT player1,player2 FROM games WHERE game_id = ?', (game_id,))
            game = c.fetchone()
            if game:
                if game[0] == player:
                    c.execute('UPDATE games SET game_status = ? where game_id == ?', (game[1],game_id,))
                else:
                    c.execute('UPDATE games SET game_status = ? where game_id == ?', (game[0],game_id,))
                #c.execute('DELETE FROM board WHERE game_id = ?', (game_id,))
                #c.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
                if game[0] == player:
                    return game[1]
                else:
                    return game[0]
            else:
                return 0
    except Exception as e:
        return f"關閉遊戲時出現錯誤:{str(e)}"
def delete_game():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('DROP TABLE IF EXISTS games')
            c.execute('DROP TABLE IF EXISTS board')

            # 重新创建表
            c.execute('''CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1 TEXT,
                player2 TEXT,
                current_player TEXT,
                first TEXT,
                game_status TEXT
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS board (
                game_id INTEGER,
                board TEXT
            )''')
            conn.commit()
            c.close()
        return "GOOD"
    except Exception as e:
        return f"刪除遊戲資料時出現錯誤：{str(e)}"

def shutdown_game(current_user):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM games where player1 == ? or player2 == ?",(current_user,current_user))
            user = c.fetchone()
            if not user:
                return "未找到匹配的遊戲記錄。"
            print("akfopakfakfpakdpakfpaskmgfldsamkgodsogagmkldngmkadnmgklamgkladngoaenmfjkadngaengjkdgsnjdangmekjnoadmgjeangasnfjkewnfadnklgwenkjenm")
            print(user)
            c.execute('UPDATE users SET status = "online" where username = ?',(user[1],))
            c.execute('UPDATE users SET status = "online" where username = ?',(user[2],))
            print(user[0])
            print((user[0],))
            c.execute('DELETE FROM board WHERE game_id = ?', user[0])
            c.execute('DELETE FROM games WHERE game_id = ?', user[0])
            conn.commit()
            return "GOOD"
    except Exception as e:
        return f"關閉遊戲時出現錯誤：{str(e)}"
# 初始化資料庫
create_tables()
result = delete_game()
print(result)

reset_user_status()

# Start the XML-RPC server
with SimpleXMLRPCServer(("localhost", PORT), allow_none=True) as server:
    server.register_function(register)
    server.register_function(login)
    server.register_function(start_game)
    server.register_function(make_move)
    server.register_function(check_board_data)
    server.register_function(get_curr_user)
    server.register_function(shutdown_game)
    server.register_function(kill_game)
    server.register_function(logout)
    server.register_function(opponent_win)
    print(f"伺服器正在 {PORT} 埠運行...")
    server.serve_forever()
