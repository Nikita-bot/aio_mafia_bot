#from config import DATABASE_URL
import psycopg2



class Data:
    def __init__(self):
        
        #self.connection = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.connection = psycopg2.connect('postgres://qzegunvlwivsan:8d843f5c980ac3ab6a99e857ee245fa5d151883aba3cb38087ab8352444ef911@ec2-54-155-194-191.eu-west-1.compute.amazonaws.com:5432/daqkra75uanuth', sslmode='require') 
        self.cursor = self.connection.cursor()

    def show_user(self, user_id):

        self.cursor.execute(
            f"SELECT id,name,phone,city_id,role,count FROM users  WHERE id={user_id}")
        result = self.cursor.fetchone()
        return result

    def show_city(self):
        self.cursor.execute(f"SELECT id,name FROM city ORDER BY id")
        result = self.cursor.fetchall()
        return result

    def show_city_info(self, city_id):
        self.cursor.execute(f"SELECT name FROM city WHERE id ={city_id}")
        result = self.cursor.fetchall()
        return result

    def search_city(self, city_id):
        self.cursor.execute(f"SELECT name FROM city WHERE id={city_id}")
        result = self.cursor.fetchone()
        return result

    def show_place_in_city(self, city_id):
        self.cursor.execute(
            f"SELECT id, name,price,seats,city_id FROM place WHERE city_id={city_id} ORDER BY id")
        result = self.cursor.fetchall()
        return result

    def Insert_user(self, user):
        self.cursor.execute(f"INSERT INTO users (id,name,phone,city_id) VALUES ({user['id']},'{user['name']}',"
                            f"{user['phone']},{user['city_id']});")
        self.connection.commit()

    def Insert_game(self, game):
        self.cursor.execute(
            f"INSERT INTO games (city_id,place_id, date_of_games,time) VALUES ({game['city_id']},{game['place_id']},'{game['date']}','{game['time']}')")
        self.connection.commit()

    def Change_city(self, city_id, users_id, role):
        self.cursor.execute(
            f"UPDATE users set(city_id,role)=({city_id},{role}) WHERE id={users_id}")
        self.connection.commit()

    def Change_nickName(self, users_id, nick):
        self.cursor.execute(
            f"UPDATE users set name = '{nick}' where id={users_id}")
        self.connection.commit()

    def Insert_city(self, name):
        self.cursor.execute(f"INSERT INTO city (name) VALUES ('{name}')")
        self.connection.commit()

    def show_game(self, city_id):
        self.cursor.execute(
            f"select g.id, p.name,g.date_of_games,g.time,p.seats,p.price,g.definitely,p.id,p.prepayment FROM games g,place p WHERE g.city_id= {city_id} and g.place_id = p.id ORDER BY g.date_of_games")
        result = self.cursor.fetchall()
        return result

    def show_info_game(self, game_id):
        self.cursor.execute(
            f"SELECT city_id, place_id, date_of_games FROM games where id={game_id}")
        result = self.cursor.fetchall()
        return result

    def Insert_prereg_game(self, game_id, user_id, count):
        self.cursor.execute(
            f"INSERT INTO pre_reg (game_id,user_id,count) VALUES ({game_id},{user_id},{count})")
        self.connection.commit()

    def show_prereg_game(self, user_id):
        self.cursor.execute(
            f"SELECT game_id,user_id FROM pre_reg WHERE user_id={user_id}  ORDER BY game_id")
        result = self.cursor.fetchall()
        return result

    def show_who_goes(self, game_id, parametr):
        self.cursor.execute(
            f"SELECT u.name, u.id FROM users u , pre_reg pr WHERE pr.game_id = {game_id} AND pr.user_id = u.id AND pr.prepayment = {parametr} AND pr.come=0")
        result = self.cursor.fetchall()
        return result

    def show_count_prereg_game(self, game_id):
        self.cursor.execute(
            f"SELECT SUM(count) FROM pre_reg WHERE game_id={game_id}")
        result = self.cursor.fetchall()
        return result

    def change_role(self, name, role):
        self.cursor.execute(
            f"UPDATE users SET role={role} WHERE name='{name}'")
        self.connection.commit()

    def change_game(self, parametr, settings, game_id):
        self.cursor.execute(
            f"UPDATE games SET {settings}='{parametr}' WHERE id={game_id}")
        self.connection.commit()

    def show_all_users(self, parametr):
        self.cursor.execute(
            f"SELECT id,name,role,count FROM users WHERE city_id={parametr}")
        result = self.cursor.fetchall()
        return result

    def del_game(self, game_id):
        self.cursor.execute(f"DELETE FROM games WHERE id = {game_id}")
        self.connection.commit()

    def del_prereg(self,game_id):
        self.cursor.execute(f"DELETE FROM pre_reg WHERE game_id = {game_id}")
        self.connection.commit()

    def del_place(self, place_id):
        self.cursor.execute(f"select id FROM games WHERE place_id= {place_id}")
        result = self.cursor.fetchall()
        for i in result:
            self.cursor.execute(f"DELETE FROM pre_reg WHERE game_id = {i[0]}")
            self.connection.commit()
            self.cursor.execute(f"DELETE FROM games WHERE id = {i[0]}")
            self.connection.commit()
        self.cursor.execute(f"DELETE FROM place WHERE id = {place_id}")
        self.connection.commit()

    def del_city(self, city_id):

        self.cursor.execute(f"DELETE FROM city WHERE id = {city_id}")
        self.connection.commit()

    def show_game_in_place(self ,place_id):
        self.cursor.execute(f"select id FROM games WHERE place_id= {place_id}")
        result = self.cursor.fetchall()
        return result

    def find_admin(self, city_id):
        self.cursor.execute(
            f"SELECT id, phone, name FROM users WHERE (role=1 or role=2) and city_id={city_id} ORDER BY role")
        result = self.cursor.fetchone()
        return result

    def find_main(self):
        self.cursor.execute(
            f"SELECT id, phone, name FROM users WHERE role = 2")
        result = self.cursor.fetchone()
        return result

    def insert_place(self, place_info):  # city_id,name,price,seats,preprice
        self.cursor.execute(
            f"INSERT INTO place (city_id,name,price,seats,prepayment) VALUES ({place_info['city_id']},'{place_info['name']}',{place_info['price']},{place_info['seats']},{place_info['prepay']})")
        self.connection.commit()

    def update_prepayment(self, user_id, game_id):
        self.cursor.execute(
            f"update  pre_reg  set prepayment = 1 where user_id = {user_id} and game_id={game_id}")
        self.cursor.execute(
            f"update  games set definitely = definitely+(select count from pre_reg where user_id ={user_id} and game_id={game_id}) where id ={game_id}")
        self.connection.commit()

    def update_count(self, user_id,game_id):
        self.cursor.execute(
            f"UPDATE users SET count =count + 1 WHERE id={user_id}")
        self.cursor.execute(
            f"update  pre_reg  set come = 1 where user_id = {user_id} and game_id={game_id}")
        self.connection.commit()

    def __del__(self):
        self.connection.close()
