class Game: 
    def __init__(self,city_id ):
        self.city_id = city_id

        keys = ['place_id', 'date_games','time']
        for key in keys:
            self.key = None

            #date year-moonth-